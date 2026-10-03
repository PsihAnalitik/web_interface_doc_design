import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeDocument } from '../dist/analysis.js';

const input = { text: 'Мой проект', files: [], username: 'tester', password: 'test-password' };
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const started = () => json({ process_id: 'job-123', status: 'queued' }, 202);
const done = () => json({ status: 'completed', progress: 100 });
const questions = () => json({ baseline: ['Какие данные?'], enriched: ['Как измерить качество?'] });

function mockFetch(t, responses) {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ url, options });
    assert.ok(responses.length, `Unexpected request: ${url}`);
    const next = responses.shift();
    if (next instanceof Error) throw next;
    return next;
  });
  return calls;
}

test('adapter uploads original files, requests 20 Russian questions and reads both sets', async t => {
  const calls = mockFetch(t, [started(), done(), questions()]);
  const file = new File(['Текст документа'], 'task.md');
  const ids = [];
  const progress = [];
  const result = await analyzeDocument({ ...input, files: [file], onCreated: id => ids.push(id), onProgress: (...args) => progress.push(args) });
  assert.deepEqual(ids, ['job-123']);
  assert.deepEqual(calls.map(call => call.url), ['/api/start_process', '/api/get_progress/job-123', '/api/get_questions/job-123?mode=both']);
  const form = calls[0].options.body;
  assert.equal(form.get('text'), input.text);
  assert.equal(form.get('question_count'), '20');
  assert.equal(form.get('language'), 'Russian');
  assert.equal(form.get('files').name, 'task.md');
  assert.equal(await form.get('files').text(), 'Текст документа');
  for (const { options } of calls) {
    assert.equal(options.headers.Authorization, `Basic ${btoa('tester:test-password')}`);
    assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error');
    assert.equal(options.headers['Content-Type'], undefined);
  }
  assert.equal(progress.at(-1)[1], 100);
  assert.deepEqual(result, { kind: 'case-finder', baseline: ['Какие данные?'], enriched: ['Как измерить качество?'] });
});

test('adapter polls pending stages and a pending questions response', async t => {
  const calls = mockFetch(t, [started(), json({ status: 'generating_baseline', progress: 10 }), done(), json({ status: 'queued', progress: 0 }, 202), done(), questions()]);
  const delays = [];
  t.mock.method(globalThis, 'setTimeout', (callback, delay) => { delays.push(delay); queueMicrotask(callback); });
  const progress = [];
  await analyzeDocument({ ...input, onProgress: (message, value) => progress.push(value) });
  assert.deepEqual(delays, [2000, 2000]);
  assert.ok(progress.includes(10));
  assert.equal(calls.filter(call => call.options.method === 'POST').length, 1);
});

test('network interruption preserves job ID; resuming makes no second POST', async t => {
  const cause = new TypeError('network down');
  const calls = mockFetch(t, [started(), cause, done(), questions()]);
  let failed;
  await assert.rejects(analyzeDocument(input), error => {
    failed = error;
    assert.equal(error.processId, 'job-123');
    assert.equal(error.cause, cause);
    return true;
  });
  await analyzeDocument({ ...input, processId: failed.processId });
  assert.equal(calls.filter(call => call.options.method === 'POST').length, 1);
});

test('failed or deleted job stops polling and allows a fresh run', async t => {
  for (const status of ['failed', 'deletion_requested']) {
    const calls = mockFetch(t, [started(), json({ status, error: { code: 'generation_failed', message: 'Model unavailable' } })]);
    await assert.rejects(analyzeDocument(input), error => {
      assert.equal(error.processId, null);
      assert.match(error.message, status === 'failed' ? /Model unavailable/ : /удаляется/);
      return true;
    });
    assert.equal(calls.length, 2);
  }
});

test('API validation, authentication and worker errors remain errors, never demo results', async t => {
  for (const [status, detail, match] of [
    [401, 'Invalid credentials', /Неверный логин/],
    [413, 'File exceeds limit', /File exceeds limit/],
    [422, [{ msg: 'Unreadable document' }], /Unreadable document/],
    [409, { code: 'failed', message: 'Generation error' }, /Generation error/],
    [502, 'API unavailable', /API unavailable/],
  ]) {
    const calls = mockFetch(t, [json({ detail }, status)]);
    await assert.rejects(analyzeDocument(input), match);
    assert.equal(calls.length, 1);
  }
});

test('missing credentials and unsupported characters fail before upload', async t => {
  const calls = mockFetch(t, []);
  for (const override of [{ password: '' }, { username: 'логин' }, { username: 'user:name' }]) {
    await assert.rejects(analyzeDocument({ ...input, ...override }), /Введите логин/);
  }
  assert.equal(calls.length, 0);
});

test('correcting invalid credentials while resuming retains the known job', async t => {
  const calls = mockFetch(t, [done(), questions()]);
  let processId = 'known-job';
  await assert.rejects(analyzeDocument({ ...input, processId, password: 'пароль' }), error => {
    processId = error.processId || null;
    assert.equal(processId, 'known-job');
    return true;
  });
  assert.equal(calls.length, 0);
  await analyzeDocument({ ...input, processId });
  assert.deepEqual(calls.map(call => call.url), ['/api/get_progress/known-job', '/api/get_questions/known-job?mode=both']);
});

test('malformed JSON and invalid job status are explicit errors', async t => {
  mockFetch(t, [new Response('<html>bad gateway</html>', { status: 502 })]);
  await assert.rejects(analyzeDocument(input), /нечитаемый ответ/);
  mockFetch(t, [json({ process_id: '../wrong' }, 202)]);
  await assert.rejects(analyzeDocument(input), /идентификатор/);
  mockFetch(t, [started(), json({ status: 'unknown' })]);
  await assert.rejects(analyzeDocument(input), /Неизвестный статус/);
});
