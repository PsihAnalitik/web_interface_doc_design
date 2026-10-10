// Explicit integration suite: CASE_FINDER_PYTHON=<server venv>/bin/python node --test tests/api-integration.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir, mkdtemp, readFile } from 'node:fs/promises';
import { access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createWebServer } from '../server.mjs';
import { analyzeDocument } from '../dist/analysis.js';
import { normalizeResult, selectedText, selectAll } from '../dist/model.js';

test('frontend adapter → proxy → real FastAPI → worker with FakeOpenAI', { timeout: 30000 }, async t => {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  await mkdir(`${root}.agent/api-integration`, { recursive: true });
  const storage = await mkdtemp(`${root}.agent/api-integration/run-`);
  const api = spawn(process.env.CASE_FINDER_PYTHON || 'python3', [fileURLToPath(new URL('./api-fixture.py', import.meta.url))], {
    cwd: root,
    env: {
      ...process.env, STORAGE_PATH: storage, DOCUMENTS_ARCHIVE_PATH: `${storage}/archive`,
      API_USERS: JSON.stringify({ 'fixture-user': 'fixture-password' }), FIXTURE_PORT: '0',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(async () => {
    if (api.exitCode !== null) return;
    const stopped = once(api, 'exit');
    api.kill();
    await stopped;
  });
  const apiUrl = await new Promise((resolve, reject) => {
    let output = '';
    api.on('error', reject);
    api.on('exit', code => reject(new Error(`API fixture exited ${code}: ${output}`)));
    api.stderr.on('data', chunk => {
      output += chunk.toString();
      const match = output.match(/Uvicorn running on (http:\/\/127\.0\.0\.1:\d+)/);
      if (match) resolve(match[1]);
    });
    api.stdout.resume();
  });
  const web = createWebServer({ apiUrl });
  web.listen(0, '127.0.0.1');
  await once(web, 'listening');
  t.after(() => new Promise(resolve => { web.close(resolve); web.closeAllConnections(); }));
  const origin = `http://127.0.0.1:${web.address().port}`;
  const realFetch = globalThis.fetch;
  const login = await realFetch(`${origin}/api/session`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username: 'fixture-user', password: 'fixture-password' }),
  });
  assert.equal(login.status, 200, await login.clone().text());
  const cookie = (typeof login.headers.getSetCookie === 'function' ? login.headers.getSetCookie() : [])
    .map(value => value.split(';')[0]).join('; ');
  t.mock.method(globalThis, 'fetch', (url, options = {}) => {
    const headers = new Headers(options.headers || {});
    headers.set('cookie', cookie);
    return realFetch(new URL(url, origin), { ...options, headers });
  });
  const input = { text: 'Классификация обращений', files: [new File(['Требования из файла'], 'task.md')] };

  let id;
  const result = normalizeResult(await analyzeDocument({ ...input, onCreated: value => { id = value; } }));
  assert.equal(result.status, 'complete');
  assert.equal(result.questions.length, 20);
  assert.equal(result.questions[0].text, 'baseline-0-Russian');
  assert.equal(result.questions[0].understanding, 'baseline-understanding-0');
  assert.equal(result.questions[10].text, 'enriched-0-Russian');
  assert.equal(selectedText(result.questions, selectAll(result.questions)).split('\n\n').length, 20);
  assert.equal(selectedText(result.questions, selectAll(result.questions)).includes('Набор:'), false);
  const request = JSON.parse(await readFile(`${storage}/jobs/${id}/request.json`, 'utf8'));
  assert.equal(request.question_count, 10);
  assert.equal(request.language, 'Russian');
  assert.equal(request.username, 'fixture-user');
  await access(`${storage}/archive/${id}/meta.json`);
  const combined = await readFile(`${storage}/jobs/${id}/input/combined.txt`, 'utf8');
  assert.match(combined, /Классификация обращений/);
  assert.match(combined, /Требования из файла/);

  const wrong = await realFetch(`${origin}/api/session`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username: 'fixture-user', password: 'wrong-password' }),
  });
  assert.equal(wrong.status, 401);
  await assert.rejects(analyzeDocument({ ...input, text: '', files: [new File(['not pdf'], 'broken.pdf')] }), /422/);
  await assert.rejects(analyzeDocument({ ...input, text: '', files: [] }), /422/);
});
