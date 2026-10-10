import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { openEventsStore } from '../events.mjs';
import { writeExport } from '../scripts/export-labels.mjs';

test('confirmed labels export questions, stars and archived document text', () => {
  const root = mkdtempSync(join(tmpdir(), 'labels-'));
  const dbPath = join(root, 'events.sqlite');
  const archive = join(root, 'archive');
  const processId = 'job-1';
  const store = openEventsStore(dbPath);
  const questions = [
    { id: 'baseline-1', text: 'Какие данные?', group: 'baseline', understanding: 'Не сказано.', importance: 'Без данных нельзя оценить.' },
    { id: 'enriched-1', text: 'Как измерять качество?', group: 'enriched', understanding: 'Метрики не заданы.', importance: 'Иначе нет приёмки.' },
  ];
  store.saveState('alice', { engine: 'case-finder', processId, sourceNames: 'brief.md', questions });
  store.record({
    username: 'alice', engine: 'case-finder', processId, action: 'confirm',
    questions: [{ id: 'enriched-1', text: 'Как измерять качество?' }],
    details: {}, sourceNames: 'brief.md',
  });
  store.close();
  const job = join(archive, processId);
  mkdirSync(join(job, 'input', 'original'), { recursive: true });
  mkdirSync(join(job, 'input', 'parsed'), { recursive: true });
  writeFileSync(join(job, 'input', 'combined.txt'), 'Текст ТЗ');
  writeFileSync(join(job, 'input', 'parsed', '001.txt'), 'Текст файла');
  writeFileSync(join(job, 'input', 'original', '001.md'), '# ТЗ');
  writeFileSync(join(job, 'meta.json'), JSON.stringify({
    username: 'alice', process_id: processId, files: [{ original_name: 'brief.md', stored_name: '001.md', sha256: 'abc' }],
  }));
  const out = join(root, 'labels.jsonl');
  const { records, summary } = writeExport(dbPath, archive, out);
  assert.equal(records.length, 1);
  assert.equal(records[0].combined_text, 'Текст ТЗ');
  assert.equal(records[0].documents[0].parsed_text, 'Текст файла');
  assert.equal(records[0].starred_enriched, 1);
  assert.equal(records[0].starred_baseline, 0);
  assert.equal(records[0].questions.find(question => question.id === 'enriched-1').starred, true);
  assert.equal(summary.totals.enriched_rate, 1);
  assert.equal(summary.totals.baseline_rate, 0);
});
