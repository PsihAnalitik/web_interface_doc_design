import { randomInt } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

export const defaultEventsDb = fileURLToPath(new URL('./data/question-events.sqlite', import.meta.url));

const ACTIONS = new Set(['star', 'unstar', 'select_all', 'clear', 'copy', 'copy_manual', 'confirm']);
const ADDING = new Set(['star', 'select_all']);
const LOCKED = new Set(['star', 'unstar', 'select_all', 'clear']);
const MAX_QUESTIONS = 500;
const MAX_ID = 200;
const MAX_TEXT = 8000;
const MAX_SOURCE = 2000;

const SCHEMA = `
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  username TEXT NOT NULL,
  engine TEXT NOT NULL,
  process_id TEXT NOT NULL,
  action TEXT NOT NULL,
  questions TEXT NOT NULL,
  details TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS selections (
  engine TEXT NOT NULL,
  process_id TEXT NOT NULL,
  username TEXT NOT NULL,
  question_id TEXT NOT NULL,
  question_text TEXT NOT NULL,
  selected_at TEXT NOT NULL,
  PRIMARY KEY (engine, process_id, username, question_id)
);
CREATE TABLE IF NOT EXISTS runs (
  engine TEXT NOT NULL,
  process_id TEXT NOT NULL,
  source_names TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  PRIMARY KEY (engine, process_id)
);
CREATE TABLE IF NOT EXISTS sessions (
  sid TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_state (
  username TEXT PRIMARY KEY,
  engine TEXT NOT NULL,
  process_id TEXT,
  source_names TEXT NOT NULL,
  question_order TEXT,
  questions TEXT,
  confirmed_at TEXT,
  updated_at TEXT NOT NULL
);
`;

export class StateConflict extends Error {
  constructor(message) {
    super(message);
    this.name = 'StateConflict';
  }
}

export function shuffleIds(ids) {
  const order = [...ids];
  for (let index = order.length - 1; index > 0; index -= 1) {
    const swap = randomInt(index + 1);
    [order[index], order[swap]] = [order[swap], order[index]];
  }
  return order;
}

function sameIdSet(order, ids) {
  if (!Array.isArray(order) || order.length !== ids.length) return false;
  const left = [...order].sort();
  const right = [...ids].sort();
  return left.every((id, index) => id === right[index]);
}

export function parseEvent(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { error: 'Тело запроса должно быть JSON-объектом.' };
  }
  if (body.engine !== 'case-finder' && body.engine !== 'factory') {
    return { error: 'Неизвестный способ анализа.' };
  }
  if (typeof body.process_id !== 'string' || !/^[a-zA-Z0-9-]+$/.test(body.process_id)) {
    return { error: 'Некорректный идентификатор задания.' };
  }
  if (!ACTIONS.has(body.action)) return { error: 'Неизвестное действие.' };
  if (!Array.isArray(body.questions) || body.questions.length > MAX_QUESTIONS) {
    return { error: 'Список вопросов некорректен.' };
  }
  const questions = [];
  for (const item of body.questions) {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      return { error: 'Вопрос должен содержать id и text.' };
    }
    if (typeof item.id !== 'string' || !item.id.trim() || item.id.length > MAX_ID) {
      return { error: 'Некорректный id вопроса.' };
    }
    if (typeof item.text !== 'string' || !item.text.trim() || item.text.length > MAX_TEXT) {
      return { error: 'Некорректный текст вопроса.' };
    }
    questions.push({ id: item.id, text: item.text });
  }
  if (body.details !== undefined && (!body.details || typeof body.details !== 'object' || Array.isArray(body.details))) {
    return { error: 'Поле details должно быть объектом.' };
  }
  if (body.source_names !== undefined && (typeof body.source_names !== 'string' || body.source_names.length > MAX_SOURCE)) {
    return { error: 'Некорректное имя источника.' };
  }
  return {
    event: {
      engine: body.engine,
      processId: body.process_id,
      action: body.action,
      questions,
      details: body.details ?? {},
      sourceNames: body.source_names ?? '',
    },
  };
}

function questionRecord(item) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) return 'Вопрос должен содержать id и text.';
  if (typeof item.id !== 'string' || !item.id.trim() || item.id.length > MAX_ID) return 'Некорректный id вопроса.';
  if (typeof item.text !== 'string' || !item.text.trim() || item.text.length > MAX_TEXT) return 'Некорректный текст вопроса.';
  const question = { id: item.id, text: item.text };
  for (const key of ['group', 'understanding', 'importance']) {
    if (item[key] !== undefined && (typeof item[key] !== 'string' || item[key].length > MAX_TEXT)) {
      return 'Некорректное поле вопроса.';
    }
    question[key] = typeof item[key] === 'string' ? item[key] : '';
  }
  return question;
}

export function parseState(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { error: 'Тело запроса должно быть JSON-объектом.' };
  }
  if (body.engine !== 'case-finder' && body.engine !== 'factory') {
    return { error: 'Неизвестный способ анализа.' };
  }
  if (body.source_names !== undefined && (typeof body.source_names !== 'string' || body.source_names.length > MAX_SOURCE)) {
    return { error: 'Некорректное имя источника.' };
  }
  const sourceNames = body.source_names ?? '';
  if (body.process_id === null || body.process_id === '') {
    return { state: { engine: body.engine, processId: null, sourceNames, questions: null } };
  }
  if (typeof body.process_id !== 'string' || !/^[a-zA-Z0-9-]+$/.test(body.process_id)) {
    return { error: 'Некорректный идентификатор задания.' };
  }
  let questions = null;
  if (body.questions !== undefined && body.questions !== null) {
    if (!Array.isArray(body.questions) || body.questions.length > MAX_QUESTIONS) {
      return { error: 'Список вопросов некорректен.' };
    }
    questions = [];
    const seen = new Set();
    for (const item of body.questions) {
      const question = questionRecord(item);
      if (typeof question === 'string') return { error: question };
      if (seen.has(question.id)) return { error: 'Повторяющийся id вопроса.' };
      seen.add(question.id);
      questions.push(question);
    }
  }
  return { state: { engine: body.engine, processId: body.process_id, sourceNames, questions } };
}

function publicState(username, row, engine = null) {
  if (!row) {
    return {
      username, engine, process_id: null, source_names: '', question_order: null, confirmed_at: null,
    };
  }
  return {
    username,
    engine: row.engine,
    process_id: row.process_id,
    source_names: row.source_names,
    question_order: row.question_order ? JSON.parse(row.question_order) : null,
    confirmed_at: row.confirmed_at,
  };
}

export function openEventsStore(filePath) {
  mkdirSync(dirname(filePath), { recursive: true });
  const db = new DatabaseSync(filePath);
  db.exec('PRAGMA journal_mode = WAL');
  db.exec('PRAGMA busy_timeout = 5000');
  db.exec(SCHEMA);
  const insertEvent = db.prepare(`
    INSERT INTO events (created_at, username, engine, process_id, action, questions, details)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  const upsertSelection = db.prepare(`
    INSERT INTO selections (engine, process_id, username, question_id, question_text, selected_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT (engine, process_id, username, question_id) DO UPDATE SET
      question_text = excluded.question_text,
      selected_at = excluded.selected_at
  `);
  const deleteSelection = db.prepare(`
    DELETE FROM selections
    WHERE engine = ? AND process_id = ? AND username = ? AND question_id = ?
  `);
  const clearSelections = db.prepare(`
    DELETE FROM selections WHERE engine = ? AND process_id = ? AND username = ?
  `);
  const insertRun = db.prepare(`
    INSERT INTO runs (engine, process_id, source_names, first_seen)
    VALUES (?, ?, ?, ?)
    ON CONFLICT (engine, process_id) DO NOTHING
  `);
  const selectCurrent = db.prepare(`
    SELECT question_id, question_text FROM selections
    WHERE engine = ? AND process_id = ? AND username = ?
    ORDER BY selected_at, question_id
  `);
  const insertSession = db.prepare(`
    INSERT INTO sessions (sid, username, created_at) VALUES (?, ?, ?)
  `);
  const deleteSession = db.prepare('DELETE FROM sessions WHERE sid = ?');
  const selectState = db.prepare('SELECT * FROM user_state WHERE username = ?');
  const deleteState = db.prepare('DELETE FROM user_state WHERE username = ?');
  const upsertState = db.prepare(`
    INSERT INTO user_state (
      username, engine, process_id, source_names, question_order, questions, confirmed_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (username) DO UPDATE SET
      engine = excluded.engine,
      process_id = excluded.process_id,
      source_names = excluded.source_names,
      question_order = excluded.question_order,
      questions = excluded.questions,
      confirmed_at = excluded.confirmed_at,
      updated_at = excluded.updated_at
  `);
  const confirmState = db.prepare(`
    UPDATE user_state SET confirmed_at = ?, updated_at = ? WHERE username = ?
  `);

  return {
    record(event) {
      const createdAt = new Date().toISOString();
      db.exec('BEGIN IMMEDIATE');
      try {
        const current = selectState.get(event.username);
        const confirmed = Boolean(
          current?.confirmed_at && current.process_id === event.processId && current.engine === event.engine,
        );
        if (confirmed && LOCKED.has(event.action)) throw new StateConflict('Разметка уже подтверждена.');
        let details = event.details;
        if (event.action === 'confirm') {
          if (!current || current.process_id !== event.processId || current.engine !== event.engine) {
            throw new StateConflict('Нет сохранённого задания для подтверждения.');
          }
          if (current.confirmed_at) throw new StateConflict('Разметка уже подтверждена.');
          if (!current.question_order) throw new StateConflict('Порядок вопросов ещё не сохранён.');
          details = { ...details, order: JSON.parse(current.question_order) };
        }
        insertEvent.run(
          createdAt, event.username, event.engine, event.processId, event.action,
          JSON.stringify(event.questions), JSON.stringify(details),
        );
        if (ADDING.has(event.action)) {
          for (const question of event.questions) {
            upsertSelection.run(event.engine, event.processId, event.username, question.id, question.text, createdAt);
          }
        } else if (event.action === 'unstar') {
          for (const question of event.questions) {
            deleteSelection.run(event.engine, event.processId, event.username, question.id);
          }
        } else if (event.action === 'clear') {
          clearSelections.run(event.engine, event.processId, event.username);
        } else if (event.action === 'confirm') {
          confirmState.run(createdAt, createdAt, event.username);
        }
        insertRun.run(event.engine, event.processId, event.sourceNames, createdAt);
        db.exec('COMMIT');
      } catch (error) {
        db.exec('ROLLBACK');
        throw error;
      }
    },
    selection(username, engine, processId) {
      return selectCurrent.all(engine, processId, username).map(row => ({
        id: row.question_id,
        text: row.question_text,
      }));
    },
    createSession(sid, username) {
      insertSession.run(sid, username, new Date().toISOString());
    },
    deleteSession(sid) {
      deleteSession.run(sid);
    },
    state(username) {
      return publicState(username, selectState.get(username));
    },
    saveState(username, input) {
      const updatedAt = new Date().toISOString();
      db.exec('BEGIN IMMEDIATE');
      try {
        if (!input.processId) {
          deleteState.run(username);
          db.exec('COMMIT');
          return publicState(username, null, input.engine);
        }
        const existing = selectState.get(username);
        const sameJob = Boolean(
          existing && existing.engine === input.engine && existing.process_id === input.processId,
        );
        let order = sameJob && existing.question_order ? JSON.parse(existing.question_order) : null;
        let questions = sameJob && existing.questions ? JSON.parse(existing.questions) : null;
        let confirmedAt = sameJob ? existing.confirmed_at : null;
        const sourceNames = input.sourceNames || (sameJob ? existing.source_names : '');
        if (input.questions) {
          const ids = input.questions.map(question => question.id);
          if (!sameIdSet(order, ids)) {
            order = shuffleIds(ids);
            confirmedAt = null;
          }
          questions = input.questions;
        }
        const row = {
          engine: input.engine,
          process_id: input.processId,
          source_names: sourceNames,
          question_order: order ? JSON.stringify(order) : null,
          confirmed_at: confirmedAt,
        };
        upsertState.run(
          username, row.engine, row.process_id, row.source_names, row.question_order,
          questions ? JSON.stringify(questions) : null, row.confirmed_at, updatedAt,
        );
        db.exec('COMMIT');
        return publicState(username, row);
      } catch (error) {
        db.exec('ROLLBACK');
        throw error;
      }
    },
    close() {
      db.close();
    },
  };
}
