import test from 'node:test';
import assert from 'node:assert/strict';
import { MAX_FILE_SIZE, validateFile, normalizeResult, mergePartialResult, selectAll, selectedText } from '../dist/model.js';
import { demoResult } from '../dist/demo.js';

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

test('complete response requires 10 questions with all fields and 2–3 summary paragraphs', () => {
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
  assert.equal(all.size, 10);
  const text = selectedText(questions, all);
  assert.equal(text.split('\n\n').length, 10);
  assert.ok(text.startsWith(`1. ${questions[0].text}`));
  assert.ok(text.includes(`10. ${questions[9].text}`));
  assert.equal((text.match(/Текущее понимание:/g) || []).length, 10);
  assert.equal((text.match(/Почему это важно:/g) || []).length, 10);
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
  assert.equal(result.questions.length, 10);
  assert.equal(result.questions[0].text, 'Уточнённый вопрос?');
  assert.equal(result.questions[0].understanding, previous.questions[0].understanding);
  assert.equal(result.questions[0].importance, previous.questions[0].importance);
  assert.deepEqual(result.summary, previous.summary);
});

function explained(text, index) {
  return { question: text, understanding: `Понимание ${index}`, importance: `Важно ${index}` };
}

const apiResult = {
  kind: 'case-finder',
  baseline: Array.from({ length: 10 }, (_, i) => explained(`Базовый вопрос ${i + 1}?`, i + 1)),
  enriched: Array.from({ length: 10 }, (_, i) => explained(`Вопрос по кейсам ${i + 1}?`, i + 1)),
};

test('Case Finder complete result keeps both groups but copied text hides the set', () => {
  const result = normalizeResult(apiResult);
  assert.equal(result.status, 'complete');
  assert.equal(result.questions.length, 20);
  assert.equal(new Set(result.questions.map(item => item.id)).size, 20);
  assert.deepEqual(result.summary, []);
  assert.deepEqual(result.questions[0], {
    id: 'baseline-1', group: 'baseline', text: 'Базовый вопрос 1?',
    subsystem: '', understanding: 'Понимание 1', importance: 'Важно 1',
  });
  assert.equal(result.questions[10].group, 'enriched');
  const text = selectedText(result.questions, new Set(['enriched-1', 'baseline-1']));
  assert.ok(text.startsWith('1. Базовый вопрос 1?\nТекущее понимание: Понимание 1\nПочему это важно: Важно 1'));
  assert.match(text, /2\. Вопрос по кейсам 1\?\nТекущее понимание: Понимание 1/);
  assert.equal(text.includes('Набор:'), false);
  assert.equal(selectAll(result.questions).size, 20);
});

test('Case Finder string questions stay available but incomplete without explanations', () => {
  const result = normalizeResult({
    kind: 'case-finder',
    baseline: ['Только вопрос?'],
    enriched: [],
  });
  assert.equal(result.status, 'partial');
  assert.equal(result.questions[0].understanding, '');
  assert.match(selectedText(result.questions, selectAll(result.questions)), /Не получено от сервиса/);
});

test('Case Finder partial and malformed arrays preserve only available questions', () => {
  const result = normalizeResult({ ...apiResult, baseline: ['Первый?', null, ' ', 'Последний?'], enriched: null });
  assert.equal(result.status, 'partial');
  assert.deepEqual(result.questions.map(item => item.id), ['baseline-1', 'baseline-4']);
  assert.match(result.message, /неполные/);
  assert.equal(normalizeResult({ ...apiResult, enriched: [] }).status, 'partial');
  assert.throws(() => normalizeResult({ kind: 'case-finder', baseline: [], enriched: [' '] }), /нет доступных/);
});

test('factory accepts zero and variable findings without the legacy quota', () => {
  const base = { kind: 'factory', status: 'complete', summary: ['Обзор'], questions: [] };
  assert.equal(normalizeResult(base).status, 'complete');
  const question = { id: 'f1', text: 'Что уточнить?', subsystem: 'Данные', understanding: 'Не определено', importance: 'Влияет на решение', severity: 'major', affected_fields: ['deployment'], evidence: [{ source_id: 'S1', start_line: 1, end_line: 2, text: '<script>literal</script>' }] };
  const result = normalizeResult({ ...base, questions: [question], maturity: [{ component: 'Поиск', level: 'experiment', reason: 'Нет оценки' }] });
  assert.equal(result.status, 'complete');
  assert.deepEqual(result.questions[0], question);
  assert.equal(result.maturity[0].level, 'experiment');
  assert.equal(normalizeResult({ ...base, status: 'partial' }).status, 'partial');
  const failed = normalizeResult({ ...base, status: 'partial', message: 'Баланс закончился', error: { code: 'provider_quota', message: 'Баланс закончился' } });
  assert.deepEqual(failed.error, { code: 'provider_quota', message: 'Баланс закончился' });
});

test('factory retains valid findings but marks duplicate and malformed findings partial', () => {
  const item = { id: 'f1', text: 'Вопрос?' };
  const result = normalizeResult({ kind: 'factory', status: 'complete', summary: [], questions: [item, item, null] });
  assert.equal(result.status, 'partial');
  assert.equal(result.questions.length, 1);
  assert.throws(() => normalizeResult({ kind: 'factory', status: 'complete' }), /нет доступных/);
});

test('factory file preflight restricts inputs to Markdown', async () => {
  assert.equal(await validateFile(new File(['# Doc'], 'TASK.MD'), 'factory'), null);
  for (const name of ['task.txt', 'task.pdf', 'task.docx']) assert.match(await validateFile(new File(['text'], name), 'factory'), /Markdown/);
});
