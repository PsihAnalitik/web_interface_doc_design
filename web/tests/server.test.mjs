import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { createWebServer } from '../server.mjs';

async function listen(t, server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => {
    server.close(resolve);
    server.closeAllConnections();
  }));
  return `http://127.0.0.1:${server.address().port}`;
}

function cookieOf(response) {
  const list = typeof response.headers.getSetCookie === 'function' ? response.headers.getSetCookie() : [];
  return list.map(value => value.split(';')[0]).join('; ');
}

async function login(url, username = 'alice', password = 'secret') {
  const response = await fetch(`${url}/api/session`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  assert.equal(response.status, 200, await response.clone().text());
  const cookie = cookieOf(response);
  assert.match(cookie, /^sid=/);
  assert.match(response.headers.get('set-cookie'), /HttpOnly/i);
  assert.match(response.headers.get('set-cookie'), /SameSite=Strict/i);
  return cookie;
}

function answerWhoami(request, response) {
  if (new URL(request.url, 'http://localhost').pathname !== '/whoami') return false;
  response.writeHead(200, { 'content-type': 'application/json' });
  response.end(JSON.stringify({ username: 'tester' }));
  return true;
}

test('proxy forwards multipart files and session authorization without changing API responses', async t => {
  const calls = [];
  const apiUrl = await listen(t, createServer(async (request, response) => {
    if (answerWhoami(request, response)) return;
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    calls.push({ url: request.url, method: request.method, headers: request.headers, body: Buffer.concat(chunks).toString() });
    response.writeHead(202, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ process_id: 'test-job', status: 'queued' }));
  }));
  const url = await listen(t, createWebServer({ apiUrl }));
  const cookie = await login(url, 'test', 'password');
  const body = new FormData();
  body.append('text', 'Требования');
  body.append('files', new File(['document content'], 'task.md'));
  body.append('question_count', '10');
  const response = await fetch(`${url}/api/start_process`, { method: 'POST', headers: { cookie }, body });
  assert.equal(response.status, 202);
  assert.deepEqual(await response.json(), { process_id: 'test-job', status: 'queued' });
  assert.equal(calls[0].url, '/start_process');
  assert.equal(calls[0].method, 'POST');
  assert.equal(calls[0].headers.authorization, basic('test', 'password'));
  assert.match(calls[0].headers['content-type'], /^multipart\/form-data; boundary=/);
  assert.match(calls[0].body, /filename="task.md"/);
  assert.match(calls[0].body, /document content/);
  assert.match(calls[0].body, /Требования/);
  await fetch(`${url}/api/get_questions/test-job?mode=both`, { headers: { cookie } });
  assert.equal(calls[1].url, '/get_questions/test-job?mode=both');
  await fetch(`${url}/api/get_input/test-job`, { headers: { cookie } });
  assert.equal(calls[2].url, '/get_input/test-job');
});

test('proxy preserves API errors without a browser Basic challenge', async t => {
  const apiUrl = await listen(t, createServer((request, response) => {
    if (answerWhoami(request, response)) return;
    const status = Number(new URL(request.url, 'http://localhost').searchParams.get('status'));
    response.writeHead(status, { 'Content-Type': 'application/json', 'WWW-Authenticate': 'Basic' });
    response.end(JSON.stringify({ detail: 'API error' }));
  }));
  const url = await listen(t, createWebServer({ apiUrl }));
  const cookie = await login(url);
  assert.equal((await fetch(`${url}/api/get_progress/test-job`)).status, 401);
  for (const status of [401, 404, 409, 413, 422, 500]) {
    const response = await fetch(`${url}/api/get_progress/test-job?status=${status}`, { headers: { cookie } });
    assert.equal(response.status, status);
    assert.equal(response.headers.get('www-authenticate'), null);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.deepEqual(await response.json(), { detail: 'API error' });
  }
});

test('unavailable API returns an explicit 502 response', async t => {
  t.mock.method(console, 'error', () => {});
  const upstream = createServer();
  const apiUrl = await listen(t, upstream);
  await new Promise(resolve => upstream.close(resolve));
  const url = await listen(t, createWebServer({ apiUrl }));
  const response = await fetch(`${url}/api/session`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username: 'alice', password: 'secret' }),
  });
  assert.equal(response.status, 502);
  assert.match((await response.json()).detail, /недоступен/);
});

test('static allowlist and API method restrictions remain enforced', async t => {
  const url = await listen(t, createWebServer());
  assert.equal((await fetch(url)).status, 200);
  const design = await fetch(`${url}/document_design.md`);
  assert.equal(design.status, 200);
  assert.match(design.headers.get('content-type'), /text\/markdown/);
  assert.match(await design.text(), /# AI Solution Copilot/);
  const head = await fetch(`${url}/app.js`, { method: 'HEAD' });
  assert.equal(head.status, 200);
  assert.equal(await head.text(), '');
  assert.match(head.headers.get('content-security-policy'), /connect-src 'self'/);
  for (const path of ['/server.mjs', '/tests/server.test.mjs', '/.env', '/api/docs', '/api/delete_job/test-job']) {
    assert.equal((await fetch(url + path)).status, 404);
  }
  assert.equal((await fetch(`${url}/api/start_process`)).status, 405);
  assert.equal((await fetch(`${url}/api/get_progress/test-job`, { method: 'POST' })).status, 405);
  assert.equal((await fetch(url, { method: 'POST' })).status, 405);
});

test('factory proxy uses its own upstream and preserves the legacy routes', async t => {
  const calls = [];
  const backend = kind => createServer((request, response) => {
    if (answerWhoami(request, response)) return;
    calls.push({ kind, path: request.url, auth: request.headers.authorization });
    response.writeHead(200, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ kind }));
  });
  const apiUrl = await listen(t, backend('legacy'));
  const factoryApiUrl = await listen(t, backend('factory'));
  const url = await listen(t, createWebServer({ apiUrl, factoryApiUrl }));
  const cookie = await login(url, 'fixture', 'secret');
  const response = await fetch(`${url}/api/factory/get_result/test-job`, { headers: { cookie } });
  assert.deepEqual(await response.json(), { kind: 'factory' });
  assert.deepEqual(calls[0], { kind: 'factory', path: '/get_result/test-job', auth: basic('fixture', 'secret') });
  await fetch(`${url}/api/get_questions/test-job?mode=both`, { headers: { cookie } });
  assert.equal(calls[1].kind, 'legacy');
  assert.equal((await fetch(`${url}/api/factory/start_process`)).status, 405);
  assert.equal((await fetch(`${url}/api/factory/get_questions/test-job`)).status, 404);
  assert.equal((await fetch(`${url}/api/factory/.env`)).status, 404);
});

test('factory upstream rejects credentials and paths', () => {
  for (const factoryApiUrl of ['http://user:secret@localhost', 'http://localhost/internal', 'file:///etc/passwd']) {
    assert.throws(() => createWebServer({ factoryApiUrl }), /HTTP\(S\)/);
  }
});

const MAX_EVENT_BODY = 256 * 1024;

function basic(username, password) {
  return `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`;
}

function progressBackend(t, calls) {
  return listen(t, createServer((request, response) => {
    if (answerWhoami(request, response)) return;
    calls.push(request.url);
    const denied = request.url.includes('denied');
    const missing = request.url.includes('missing');
    const status = denied ? 401 : missing ? 404 : 200;
    const headers = { 'Content-Type': 'application/json' };
    if (status === 401) headers['WWW-Authenticate'] = 'Basic';
    response.writeHead(status, headers);
    response.end(JSON.stringify({ status: 'completed' }));
  }));
}

test('question events record stars and the current selection', async t => {
  const calls = [];
  const apiUrl = await progressBackend(t, calls);
  const factoryCalls = [];
  const factoryApiUrl = await progressBackend(t, factoryCalls);
  const eventsDb = join(mkdtempSync(join(tmpdir(), 'events-')), 'events.sqlite');
  const url = await listen(t, createWebServer({ apiUrl, factoryApiUrl, eventsDb }));
  const headers = { cookie: await login(url), 'content-type': 'application/json' };
  const post = body => fetch(`${url}/api/question_events`, { method: 'POST', headers, body: JSON.stringify(body) });
  const star = { engine: 'case-finder', process_id: 'job-1', action: 'star', questions: [{ id: 'baseline-1', text: 'Первый?' }], source_names: 'brief.md' };
  assert.equal((await post(star)).status, 204);
  assert.equal((await post({ ...star, action: 'unstar' })).status, 204);
  assert.equal((await post({
    ...star,
    action: 'select_all',
    questions: [{ id: 'baseline-1', text: 'Первый?' }, { id: 'baseline-2', text: 'Второй?' }],
  })).status, 204);
  assert.equal((await post({ ...star, action: 'copy', questions: [{ id: 'baseline-1', text: 'Первый?' }], details: { count: 1, placement: 'toolbar' } })).status, 204);
  assert.deepEqual(calls, ['/get_progress/job-1', '/get_progress/job-1', '/get_progress/job-1', '/get_progress/job-1']);
  const db = new DatabaseSync(eventsDb);
  t.after(() => db.close());
  assert.equal(db.prepare('select count(*) as n from events').get().n, 4);
  assert.deepEqual(
    db.prepare('select question_id from selections order by question_id').all().map(row => row.question_id),
    ['baseline-1', 'baseline-2'],
  );
  assert.equal(db.prepare('select source_names from runs').get().source_names, 'brief.md');
  assert.equal((await post({ ...star, engine: 'factory', process_id: 'factory-job' })).status, 204);
  assert.deepEqual(factoryCalls, ['/get_progress/factory-job']);
});

test('question events are rejected when the job is not accessible', async t => {
  const apiUrl = await progressBackend(t, []);
  const eventsDb = join(mkdtempSync(join(tmpdir(), 'events-')), 'events.sqlite');
  const url = await listen(t, createWebServer({ apiUrl, eventsDb }));
  const headers = { cookie: await login(url), 'content-type': 'application/json' };
  const denied = await fetch(`${url}/api/question_events`, {
    method: 'POST', headers,
    body: JSON.stringify({ engine: 'case-finder', process_id: 'denied-job', action: 'star', questions: [{ id: 'q', text: 'Вопрос?' }] }),
  });
  assert.equal(denied.status, 401);
  assert.equal(denied.headers.get('www-authenticate'), null);
  const missing = await fetch(`${url}/api/question_events/case-finder/missing-job`, { headers });
  assert.equal(missing.status, 404);
  const db = new DatabaseSync(eventsDb);
  t.after(() => db.close());
  assert.equal(db.prepare('select count(*) as n from events').get().n, 0);
});

test('question events reject malformed and oversized requests before calling the API', async t => {
  const calls = [];
  const apiUrl = await progressBackend(t, calls);
  const eventsDb = join(mkdtempSync(join(tmpdir(), 'events-')), 'events.sqlite');
  const url = await listen(t, createWebServer({ apiUrl, eventsDb }));
  const headers = { cookie: await login(url), 'content-type': 'application/json' };
  const post = body => fetch(`${url}/api/question_events`, { method: 'POST', headers, body });
  assert.equal((await post(JSON.stringify({ engine: 'case-finder', process_id: 'job-1', action: 'nope', questions: [] }))).status, 400);
  assert.equal((await post(JSON.stringify({ engine: 'case-finder', process_id: 'bad id', action: 'star', questions: [{ id: 'q', text: 'Вопрос?' }] }))).status, 400);
  assert.equal((await post('{"questions":')).status, 400);
  const oversized = await post(JSON.stringify({
    engine: 'case-finder', process_id: 'job-1', action: 'star',
    questions: [{ id: 'q', text: 'x'.repeat(MAX_EVENT_BODY) }],
  }));
  assert.equal(oversized.status, 413);
  assert.deepEqual(calls, []);
  const db = new DatabaseSync(eventsDb);
  t.after(() => db.close());
  assert.equal(db.prepare('select count(*) as n from events').get().n, 0);
});

test('question event selection is restored only for the same user', async t => {
  const apiUrl = await progressBackend(t, []);
  const eventsDb = join(mkdtempSync(join(tmpdir(), 'events-')), 'events.sqlite');
  const url = await listen(t, createWebServer({ apiUrl, eventsDb }));
  const aliceCookie = await login(url, 'alice');
  const bobCookie = await login(url, 'bob');
  const post = (cookie, text) => fetch(`${url}/api/question_events`, {
    method: 'POST',
    headers: { cookie, 'content-type': 'application/json' },
    body: JSON.stringify({
      engine: 'case-finder', process_id: 'job-1', action: 'star', questions: [{ id: text, text: `${text}?` }],
    }),
  });
  assert.equal((await post(aliceCookie, 'a')).status, 204);
  assert.equal((await post(bobCookie, 'b')).status, 204);
  const alice = await fetch(`${url}/api/question_events/case-finder/job-1`, { headers: { cookie: aliceCookie } });
  assert.equal(alice.status, 200);
  assert.deepEqual(await alice.json(), { questions: [{ id: 'a', text: 'a?' }] });
  const bob = await fetch(`${url}/api/question_events/case-finder/job-1`, { headers: { cookie: bobCookie } });
  assert.deepEqual(await bob.json(), { questions: [{ id: 'b', text: 'b?' }] });
});

test('question order is shuffled once and confirmation locks later edits', async t => {
  const apiUrl = await progressBackend(t, []);
  const eventsDb = join(mkdtempSync(join(tmpdir(), 'events-')), 'events.sqlite');
  const url = await listen(t, createWebServer({ apiUrl, eventsDb }));
  const cookie = await login(url);
  const headers = { cookie, 'content-type': 'application/json' };
  const questions = ['baseline-1', 'baseline-2', 'enriched-1', 'enriched-2'].map(id => ({ id, text: `${id}?`, group: id.split('-')[0] }));
  const put = () => fetch(`${url}/api/state`, {
    method: 'PUT', headers, body: JSON.stringify({ engine: 'case-finder', process_id: 'job-1', source_names: 'brief.md', questions }),
  });
  const first = await put();
  assert.equal(first.status, 200);
  const saved = await first.json();
  assert.deepEqual([...saved.question_order].sort(), questions.map(question => question.id).sort());
  const second = await (await put()).json();
  assert.deepEqual(second.question_order, saved.question_order);
  assert.equal(second.confirmed_at, null);
  const confirmed = await fetch(`${url}/api/question_events`, {
    method: 'POST', headers,
    body: JSON.stringify({
      engine: 'case-finder', process_id: 'job-1', action: 'confirm',
      questions: [{ id: 'baseline-1', text: 'baseline-1?' }], source_names: 'brief.md', details: { count: 1 },
    }),
  });
  assert.equal(confirmed.status, 204);
  const state = await (await fetch(`${url}/api/state`, { headers: { cookie } })).json();
  assert.ok(state.confirmed_at);
  assert.deepEqual(state.question_order, saved.question_order);
  const locked = await fetch(`${url}/api/question_events`, {
    method: 'POST', headers,
    body: JSON.stringify({ engine: 'case-finder', process_id: 'job-1', action: 'star', questions: [{ id: 'enriched-1', text: 'enriched-1?' }] }),
  });
  assert.equal(locked.status, 409);
  const cleared = await (await fetch(`${url}/api/state`, {
    method: 'PUT', headers, body: JSON.stringify({ engine: 'case-finder', process_id: null }),
  })).json();
  assert.equal(cleared.process_id, null);
});
