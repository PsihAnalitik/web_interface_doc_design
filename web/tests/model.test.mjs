import test from 'node:test';
import assert from 'node:assert/strict';
import { MAX_FILE_SIZE, validateFile, normalizeResult, mergePartialResult, selectAll, selectedText } from '../dist/model.js';
import { demoResult } from '../dist/demo.js';
import { analyzeDocument } from '../dist/analysis.js';

test('client preflight accepts supported files and the 30 MB boundary', async () => {
  for (const name of ['task.md', 'TASK.TXT', 'task.pdf', 'task.docx']) {
    assert.equal(await validateFile(new File(['some content'], name)), null);
  }
  assert.equal(await validateFile({ name: 'task.pdf', size: MAX_FILE_SIZE, slice: () => new Blob(['PDF']) }), null);
});

test('client preflight rejects wrong format, empty, whitespace and oversized files', async () => {
  assert.match(await validateFile(new File(['content'], 'task.exe')), /Поддерживаются/);
  assert.match(await validateFile(new File([], 'task.pdf')), /пуст/);
  assert.match(await validateFile(new File([' \n\t'], 'task.md')), /не содержит текста/);
  assert.match(await validateFile({ name: 'task.pdf', size: MAX_FILE_SIZE + 1 }), /30 МБ/);
});

test('unreadable file is reported, rather than accepted', async t => {
  t.mock.method(console, 'warn', () => {});
  assert.match(await validateFile({ name: 'task.txt', size: 10, text: async () => { throw new Error('read failed'); } }), /недоступен/);
});

test('complete response requires 20 questions with all fields and 2–3 summary paragraphs', () => {
  assert.equal(normalizeResult(demoResult).status, 'complete');
  assert.equal(normalizeResult({ ...demoResult, questions: demoResult.questions.slice(0, 8) }).status, 'partial');
  assert.equal(normalizeResult({ ...demoResult, summary: [] }).status, 'partial');
  assert.equal(normalizeResult({ ...demoResult, status: 'partial' }).status, 'partial');
});

test('malformed and duplicate questions do not discard valid partial content', () => {
  const good = demoResult.questions[0];
  const missing = { id: 'missing-fields', text: 'Что уточнить?' };
  const result = normalizeResult({ ...demoResult, questions: [null, good, good, missing, { id: 'blank', text: ' ' }] });
  assert.equal(result.status, 'partial');
  assert.deepEqual(result.questions.map(question => question.id), [good.id, 'missing-fields']);
  assert.equal(result.questions[1].understanding, '');
  assert.deepEqual(result.summary, demoResult.summary);
});

test('unusable response is an error, not an empty success', () => {
  for (const value of [null, undefined, 'bad', {}, { summary: [], questions: [null] }]) {
    assert.throws(() => normalizeResult(value));
  }
});

test('select all and copying retain displayed order and current understanding', () => {
  const questions = normalizeResult(demoResult).questions;
  const all = selectAll(questions);
  assert.equal(all.size, 20);
  const text = selectedText(questions, all);
  assert.equal(text.split('\n\n').length, 20);
  assert.ok(text.startsWith(`1. ${questions[0].text}`));
  assert.ok(text.includes(`20. ${questions[19].text}`));
  assert.equal((text.match(/Текущее понимание:/g) || []).length, 20);
  const reversed = new Set([questions[3].id, questions[0].id]);
  assert.ok(selectedText(questions, reversed).startsWith(`1. ${questions[0].text}`));
  all.clear();
  assert.equal(selectedText(questions, all), '');
});

test('partial result selects and copies only its available questions', () => {
  const questions = demoResult.questions.slice(0, 8);
  const selected = selectAll(questions);
  assert.equal(selected.size, 8);
  assert.equal(selectedText(questions, selected).split('\n\n').length, 8);
});

test('unconnected service never substitutes demonstration results', async () => {
  await assert.rejects(analyzeDocument({ text: 'Мой проект', files: [] }), /пока не подключён/);
});

test('partial final response retains previously streamed questions', () => {
  const previous = normalizeResult({ ...demoResult, status: 'partial', questions: demoResult.questions.slice(0, 8) });
  const final = normalizeResult({ status: 'partial', summary: ['Итоговое понимание'], questions: [] });
  const result = mergePartialResult(previous, final);
  assert.equal(result.questions.length, 8);
  assert.equal(result.title, demoResult.title);
  assert.deepEqual(result.summary, ['Итоговое понимание']);
  assert.equal(result.status, 'partial');
});

test('incomplete update does not erase already received question fields', () => {
  const previous = normalizeResult(demoResult);
  const update = normalizeResult({ status: 'partial', questions: [{ id: 'demo-1', text: 'Уточнённый вопрос?' }] });
  const result = mergePartialResult(previous, update);
  assert.equal(result.questions.length, 20);
  assert.equal(result.questions[0].text, 'Уточнённый вопрос?');
  assert.equal(result.questions[0].understanding, previous.questions[0].understanding);
  assert.equal(result.questions[0].importance, previous.questions[0].importance);
  assert.deepEqual(result.summary, previous.summary);
});
