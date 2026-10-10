import { DatabaseSync } from 'node:sqlite';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';

function groupOf(id) {
  if (typeof id !== 'string') return '';
  if (id.startsWith('baseline')) return 'baseline';
  if (id.startsWith('enriched')) return 'enriched';
  return '';
}

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

export function collectRecords(db, archiveRoot) {
  const states = db.prepare(`
    SELECT username, engine, process_id, source_names, question_order, questions, confirmed_at
    FROM user_state WHERE confirmed_at IS NOT NULL
    ORDER BY confirmed_at, username
  `).all();
  const confirmEvent = db.prepare(`
    SELECT questions FROM events
    WHERE username = ? AND engine = ? AND process_id = ? AND action = 'confirm'
    ORDER BY id DESC LIMIT 1
  `);
  const records = [];
  for (const state of states) {
    const questions = state.questions ? JSON.parse(state.questions) : [];
    const order = state.question_order ? JSON.parse(state.question_order) : questions.map(question => question.id);
    const confirmed = confirmEvent.get(state.username, state.engine, state.process_id);
    const starred = new Set((confirmed ? JSON.parse(confirmed.questions) : []).map(question => question.id));
    const position = new Map(order.map((id, index) => [id, index + 1]));
    const archiveDir = join(archiveRoot, state.process_id);
    const metaPath = join(archiveDir, 'meta.json');
    const meta = existsSync(metaPath) ? readJson(metaPath) : null;
    const combinedPath = join(archiveDir, 'input', 'combined.txt');
    const labeled = questions.map(question => ({
      id: question.id,
      group: groupOf(question.id) || question.group || '',
      text: question.text,
      understanding: question.understanding || '',
      importance: question.importance || '',
      shown_position: position.get(question.id) ?? null,
      starred: starred.has(question.id),
    })).sort((left, right) => (left.shown_position ?? 9999) - (right.shown_position ?? 9999));
    const count = (group, onlyStarred) => labeled.filter(question => question.group === group && (!onlyStarred || question.starred)).length;
    records.push({
      username: state.username,
      engine: state.engine,
      process_id: state.process_id,
      source_names: state.source_names,
      confirmed_at: state.confirmed_at,
      combined_text: existsSync(combinedPath) ? readFileSync(combinedPath, 'utf8') : '',
      documents: (meta?.files || []).map(file => {
        const stem = String(file.stored_name || '').replace(/\.[^.]+$/, '');
        const parsedPath = join(archiveDir, 'input', 'parsed', `${stem}.txt`);
        return {
          original_name: file.original_name,
          stored_name: file.stored_name,
          sha256: file.sha256,
          archive_path: join(state.process_id, 'input', 'original', file.stored_name),
          parsed_text: existsSync(parsedPath) ? readFileSync(parsedPath, 'utf8') : '',
        };
      }),
      questions: labeled,
      starred_baseline: count('baseline', true),
      starred_enriched: count('enriched', true),
      baseline_count: count('baseline', false),
      enriched_count: count('enriched', false),
    });
  }
  return records;
}

export function summarize(records) {
  const byUser = new Map();
  for (const record of records) {
    const current = byUser.get(record.username) || {
      username: record.username, documents: 0, starred_baseline: 0, starred_enriched: 0, baseline_count: 0, enriched_count: 0,
    };
    current.documents += 1;
    current.starred_baseline += record.starred_baseline;
    current.starred_enriched += record.starred_enriched;
    current.baseline_count += record.baseline_count;
    current.enriched_count += record.enriched_count;
    byUser.set(record.username, current);
  }
  const rate = (part, total) => (total ? part / total : 0);
  const users = [...byUser.values()].map(user => ({
    ...user,
    baseline_rate: rate(user.starred_baseline, user.baseline_count),
    enriched_rate: rate(user.starred_enriched, user.enriched_count),
  }));
  const totals = users.reduce((sum, user) => {
    sum.documents += user.documents;
    sum.starred_baseline += user.starred_baseline;
    sum.starred_enriched += user.starred_enriched;
    sum.baseline_count += user.baseline_count;
    sum.enriched_count += user.enriched_count;
    return sum;
  }, { documents: 0, starred_baseline: 0, starred_enriched: 0, baseline_count: 0, enriched_count: 0 });
  totals.baseline_rate = rate(totals.starred_baseline, totals.baseline_count);
  totals.enriched_rate = rate(totals.starred_enriched, totals.enriched_count);
  return { users, totals };
}

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`Нужен аргумент ${name}`);
  return process.argv[index + 1];
}

export function writeExport(dbPath, archiveRoot, outPath) {
  const db = new DatabaseSync(dbPath, { readOnly: true });
  try {
    const records = collectRecords(db, archiveRoot);
    const summary = summarize(records);
    mkdirSync(dirname(outPath), { recursive: true });
    writeFileSync(outPath, records.map(record => JSON.stringify(record)).join('\n') + (records.length ? '\n' : ''), 'utf8');
    const summaryPath = outPath.replace(/\.jsonl$/, '') + '-summary.json';
    writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
    return { records, summary, summaryPath };
  } finally {
    db.close();
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { records, summary, summaryPath } = writeExport(argument('--db'), argument('--archive'), argument('--out'));
  console.log(`Подтверждено разметок: ${records.length}. Сводка: ${summaryPath}`);
  console.log(JSON.stringify(summary.totals));
}
