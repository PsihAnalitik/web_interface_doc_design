// FACTORY_PYTHON=<factory service venv>/bin/python node --test tests/factory-api-integration.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir, mkdtemp, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createWebServer } from '../server.mjs';
import { analyzeDocument } from '../dist/analysis.js';
import { normalizeResult, selectedText, selectAll } from '../dist/model.js';

test('factory adapter → proxy → real API → worker with deterministic execution', { timeout: 30000 }, async t => {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  await mkdir(`${root}.agent/factory-api-integration`, { recursive: true });
  const storage = await mkdtemp(`${root}.agent/factory-api-integration/run-`);
  const api = spawn(process.env.FACTORY_PYTHON || 'python3', [fileURLToPath(new URL('./factory-api-fixture.py', import.meta.url))], {
    cwd: root,
    env: { ...process.env, FACTORY_STORAGE_PATH: storage, API_USERS: JSON.stringify({ 'fixture-user': 'fixture-password' }), FIXTURE_PORT: '0' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(async () => {
    if (api.exitCode !== null) return;
    const stopped = once(api, 'exit');
    api.kill();
    await stopped;
  });
  const factoryApiUrl = await new Promise((resolve, reject) => {
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
  const web = createWebServer({ factoryApiUrl });
  web.listen(0, '127.0.0.1');
  await once(web, 'listening');
  t.after(() => new Promise(resolve => { web.close(resolve); web.closeAllConnections(); }));
  const origin = `http://127.0.0.1:${web.address().port}`;
  const realFetch = globalThis.fetch;
  t.mock.method(globalThis, 'fetch', (url, options) => realFetch(new URL(url, origin), options));
  const input = { engine: 'factory', username: 'fixture-user', password: 'fixture-password', text: '', files: [new File(['# Fixture\nOriginal uploaded requirement THREE'], 'task.md')] };
  let id;
  const result = normalizeResult(await analyzeDocument({ ...input, onCreated: value => { id = value; } }));
  assert.equal(result.kind, 'factory');
  assert.equal(result.status, 'complete');
  assert.equal(result.questions.length, 3);
  assert.equal(result.questions[0].text, 'Which role 0?');
  assert.equal(result.questions[0].evidence[0].text, 'Original uploaded requirement THREE');
  assert.equal(result.questions[0].evidence[0].start_line, 2);
  assert.equal(result.questions[0].importance, 'Integration access is unclear');
  assert.equal(result.maturity[0].level, 'experiment');
  assert.equal(selectedText(result.questions, selectAll(result.questions)).split('\n\n').length, 3);
  assert.equal(await readFile(`${storage}/jobs/${id}/input/original/001.md`, 'utf8'), '# Fixture\nOriginal uploaded requirement THREE');
  const resume = normalizeResult(await analyzeDocument({ ...input, processId: id }));
  assert.deepEqual(resume, result);

  const single = normalizeResult(await analyzeDocument({ ...input, files: [new File(['# Fixture\nOne requirement'], 'one.md')] }));
  assert.equal(single.status, 'complete');
  assert.equal(single.questions.length, 1);
  const partial = normalizeResult(await analyzeDocument({ ...input, files: [new File(['# Fixture\nPARTIAL requirement'], 'partial.md')] }));
  assert.equal(partial.status, 'partial');
  assert.equal(partial.questions.length, 1);
  assert.equal(partial.questions[0].evidence[0].text, 'PARTIAL requirement');
  assert.ok(partial.message);

  await assert.rejects(analyzeDocument({ ...input, password: 'wrong-password' }), /Неверный логин/);
  await assert.rejects(analyzeDocument({ ...input, files: [new File(['broken'], 'broken.pdf')] }), /Markdown/);
  await assert.rejects(analyzeDocument({ ...input, files: [new File(['  '], 'empty.md')] }), /422/);
  await assert.rejects(analyzeDocument({ ...input, files: [new File([new Uint8Array([255])], 'invalid.md')] }), /422/);
  const body = new FormData();
  body.append('files', new File(['not markdown'], 'bypass.pdf'));
  const invalid = await realFetch(`${origin}/api/factory/start_process`, {
    method: 'POST', headers: { Authorization: `Basic ${btoa('fixture-user:fixture-password')}` }, body,
  });
  assert.equal(invalid.status, 422, 'server validates file type even if client preflight is bypassed');
});
