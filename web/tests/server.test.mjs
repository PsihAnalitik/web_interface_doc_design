import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
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

test('proxy forwards multipart files and authorization without changing API responses', async t => {
  const calls = [];
  const apiUrl = await listen(t, createServer(async (request, response) => {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    calls.push({ url: request.url, method: request.method, headers: request.headers, body: Buffer.concat(chunks).toString() });
    response.writeHead(202, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ process_id: 'test-job', status: 'queued' }));
  }));
  const url = await listen(t, createWebServer({ apiUrl }));
  const body = new FormData();
  body.append('text', 'Требования');
  body.append('files', new File(['document content'], 'task.md'));
  body.append('question_count', '20');
  const authorization = `Basic ${Buffer.from('test:password').toString('base64')}`;
  const response = await fetch(`${url}/api/start_process`, { method: 'POST', headers: { authorization }, body });
  assert.equal(response.status, 202);
  assert.deepEqual(await response.json(), { process_id: 'test-job', status: 'queued' });
  assert.equal(calls[0].url, '/start_process');
  assert.equal(calls[0].method, 'POST');
  assert.equal(calls[0].headers.authorization, authorization);
  assert.match(calls[0].headers['content-type'], /^multipart\/form-data; boundary=/);
  assert.match(calls[0].body, /filename="task.md"/);
  assert.match(calls[0].body, /document content/);
  assert.match(calls[0].body, /Требования/);
  await fetch(`${url}/api/get_questions/test-job?mode=both`);
  assert.equal(calls[1].url, '/get_questions/test-job?mode=both');
});

test('proxy preserves API errors including Basic challenge', async t => {
  const apiUrl = await listen(t, createServer((request, response) => {
    const status = Number(new URL(request.url, 'http://localhost').searchParams.get('status'));
    response.writeHead(status, { 'Content-Type': 'application/json', 'WWW-Authenticate': 'Basic' });
    response.end(JSON.stringify({ detail: 'API error' }));
  }));
  const url = await listen(t, createWebServer({ apiUrl }));
  for (const status of [401, 404, 409, 413, 422, 500]) {
    const response = await fetch(`${url}/api/get_progress/test-job?status=${status}`);
    assert.equal(response.status, status);
    assert.equal(response.headers.get('www-authenticate'), 'Basic');
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
  const response = await fetch(`${url}/api/get_progress/test-job`);
  assert.equal(response.status, 502);
  assert.match((await response.json()).detail, /недоступен/);
});

test('static allowlist and API method restrictions remain enforced', async t => {
  const url = await listen(t, createWebServer());
  assert.equal((await fetch(url)).status, 200);
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
