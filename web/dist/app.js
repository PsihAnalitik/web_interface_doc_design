import { extension, fileSize, validateFile, normalizeResult, mergePartialResult, selectedText, selectAll } from './model.js';
import { analyzeDocument, serviceNotice, factoryNotice, factoryErrorHeading } from './analysis.js';
import { demoResult } from './demo.js';

const byId = id => document.getElementById(id);
const copyButtons = [...document.querySelectorAll('.copy')];
const state = {
  files: [], reading: false, running: false, result: null,
  selected: new Set(), mode: null, replacementId: null, run: 0, processId: null, resultId: null, engine: 'case-finder',
  username: null, confirmed: false, questionOrder: null,
};
const confirmButtons = [byId('confirm'), byId('confirm-bottom')];
let eventQueue = Promise.resolve();
let stateQueue = Promise.resolve();

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function updateForm() {
  const locked = state.reading || state.running;
  const factory = state.engine === 'factory';
  byId('factory-scope').hidden = !factory;
  byId('factory-design-document').hidden = !factory;
  const ready = factory ? state.files.length > 0 && state.files.every(entry => extension(entry.file.name) === 'md') : Boolean(byId('description').value.trim() || state.files.length);
  byId('engine').disabled = locked || Boolean(state.processId);
  byId('files').accept = byId('replacement').accept = factory ? '.md' : '.md,.docx,.pdf,.txt';
  byId('service-note').textContent = factory ? factoryNotice : serviceNotice;
  byId('engine-description').textContent = factory ? 'Загрузите Markdown-документы: фабрика проверит разделы паспорта, их связи и подготовит замечания с основаниями.' : 'Добавьте описание задачи или документы. Отметьте звёздочками важные вопросы и подтвердите разметку.';
  byId('file-hint').textContent = factory ? 'Только MD · до 30 МБ на файл в браузере. Лимиты сервера проверяются при загрузке. PDF и DOCX предварительно переведите в Markdown.' : 'MD, DOCX, PDF, TXT · до 30 МБ на файл в браузере. Сервер по умолчанию: 10 файлов, 20 МБ на файл, 100 МБ суммарно. PDF с текстовым слоем, без сканов.';
  byId('analyze').disabled = locked || !ready || !state.username;
  byId('example').disabled = locked;
  byId('files').disabled = locked;
  byId('replacement').disabled = locked;
  byId('description').disabled = locked || factory;
  byId('dropzone').setAttribute('aria-disabled', String(locked));
  document.querySelectorAll('.file-actions button').forEach(button => { button.disabled = locked; });
  byId('ready-status').textContent = state.reading ? 'Проверяем выбранные файлы…'
    : !state.username ? 'Войдите, чтобы отправить материалы на анализ. Демопример доступен без входа.'
    : ready ? 'Материалы готовы к отправке на анализ.' : factory ? 'Загрузите документы об AI-агентах в формате .md.' : 'Добавьте текст или хотя бы один документ.';
}

function renderFiles() {
  const list = byId('file-list');
  list.replaceChildren();
  for (const entry of state.files) {
    const item = element('li', undefined, 'file-item');
    const info = element('div', undefined, 'file-info');
    const details = element('div');
    details.append(element('span', entry.file.name, 'file-name'), element('span', fileSize(entry.file.size), 'file-size'));
    info.append(element('span', extension(entry.file.name).toUpperCase(), 'file-format'), details);
    const actions = element('div', undefined, 'file-actions');
    const replace = element('button', 'Заменить', 'button quiet');
    replace.type = 'button';
    replace.setAttribute('aria-label', `Заменить ${entry.file.name}`);
    replace.addEventListener('click', () => {
      if (state.reading || state.running) return;
      state.replacementId = entry.id;
      byId('replacement').click();
    });
    const remove = element('button', 'Удалить', 'button quiet');
    remove.type = 'button';
    remove.setAttribute('aria-label', `Удалить ${entry.file.name}`);
    remove.addEventListener('click', () => {
      if (state.reading || state.running) return;
      state.files = state.files.filter(file => file.id !== entry.id);
      renderFiles();
    });
    actions.append(replace, remove);
    item.append(info, actions);
    list.append(item);
  }
  updateForm();
}

async function addFiles(files, replacementId = null) {
  if (state.reading || state.running) return;
  state.reading = true;
  updateForm();
  const errors = [];
  try {
    for (const file of files) {
      const error = await validateFile(file, state.engine);
      if (error) { errors.push(`${file.name}: ${error}`); continue; }
      const entry = { id: crypto.randomUUID(), file };
      if (replacementId) {
        const index = state.files.findIndex(item => item.id === replacementId);
        if (index >= 0) state.files[index] = entry;
      } else {
        state.files.push(entry);
      }
    }
  } finally {
    state.reading = false;
    const panel = byId('file-errors');
    panel.replaceChildren();
    panel.hidden = errors.length === 0;
    if (errors.length) {
      const list = element('ul');
      errors.forEach(error => list.append(element('li', error)));
      panel.append(list);
    }
    renderFiles();
  }
}

function setStep(name) {
  for (const step of ['input', 'processing', 'results']) {
    const node = byId(`step-${step}`);
    if (step === name) node.setAttribute('aria-current', 'step');
    else node.removeAttribute('aria-current');
  }
}

function updateSelection() {
  const questions = state.result?.questions || [];
  document.querySelectorAll('#questions tr').forEach(row => {
    const selected = state.selected.has(row.dataset.id);
    row.classList.toggle('selected', selected);
    const button = row.querySelector('button');
    button.setAttribute('aria-pressed', String(selected));
    button.textContent = selected ? '★' : '☆';
  });
  byId('selection-count').textContent = `Выбрано: ${state.selected.size} из ${questions.length}`;
  const labelingLocked = state.confirmed && state.result?.kind === 'case-finder';
  byId('select-all').disabled = labelingLocked || questions.length === 0 || state.selected.size === questions.length;
  byId('clear').disabled = labelingLocked || state.selected.size === 0;
  confirmButtons.forEach(button => {
    button.hidden = state.result?.kind !== 'case-finder';
    button.disabled = labelingLocked || state.selected.size === 0;
  });
  copyButtons.forEach(button => { button.disabled = state.selected.size === 0; });
  byId('copy-message').textContent = '';
  byId('copy-fallback').hidden = true;
}

function renderResult() {
  const result = state.result;
  if (!result) return;
  byId('analysis-title').textContent = result.title;
  byId('summary-section').hidden = !result.summary.length;
  byId('summary-text').replaceChildren(...result.summary.map(text => element('p', text)));
  byId('result-note').hidden = result.kind !== 'case-finder';
  byId('question-column').textContent = result.kind === 'case-finder' ? 'Вопрос' : 'Вопрос / подсистема';
  if (result.kind === 'case-finder') {
    byId('result-note').textContent = state.confirmed
      ? 'Разметка сохранена. Отмеченные вопросы больше нельзя изменить.'
      : 'Отметьте звёздочкой вопросы, которые важно задать заказчику, и нажмите «Подтвердить».';
  }
  if (result.kind === 'factory') {
    byId('result-note').hidden = false;
    byId('result-note').textContent = result.questions.length ? `Фабрика: ${result.questions.length} замечаний. Количество определяется анализом документа.` : result.status === 'complete' ? 'Анализ завершён: замечаний не сформировано.' : 'Частичный результат: итоговые замечания пока не сформированы.';
  }
  byId('maturity-section').hidden = !result.maturity?.length;
  byId('maturity-list').replaceChildren(...(result.maturity || []).map(item => {
    const block = element('p');
    const level = { repeat_deployment: 'Повторное внедрение', known_approach: 'Известный подход', experiment: 'Эксперимент', research: 'Исследование', undetermined: 'Не определено' }[item.level] || item.level;
    block.append(element('strong', `${item.component} — ${level}. `), document.createTextNode(item.reason));
    return block;
  }));
  byId('questions-section').hidden = !result.questions.length;
  byId('question-count').textContent = result.questions.length;
  const body = byId('questions');
  body.replaceChildren();
  result.questions.forEach((question, index) => {
    const row = element('tr');
    row.dataset.id = question.id;
    const controlCell = element('td');
    const toggle = element('button', '☆', 'like');
    toggle.type = 'button';
    toggle.disabled = state.confirmed && result.kind === 'case-finder';
    toggle.setAttribute('aria-label', `Выделить вопрос ${index + 1}`);
    toggle.setAttribute('aria-pressed', 'false');
    toggle.addEventListener('click', () => {
      if (state.confirmed && result.kind === 'case-finder') return;
      const marked = state.selected.has(question.id);
      if (marked) state.selected.delete(question.id);
      else state.selected.add(question.id);
      updateSelection();
      logEvent(marked ? 'unstar' : 'star', [question]);
    });
    controlCell.append(toggle);
    const questionCell = element('td');
    const title = element('h3', undefined, 'question-title');
    title.append(element('span', `${String(index + 1).padStart(2, '0')}. `, 'question-number'), document.createTextNode(question.text));
    questionCell.append(title);
    if (result.kind !== 'case-finder') questionCell.append(element('span', question.subsystem || 'Подсистема не указана', 'subsystem'));
    if (question.severity) questionCell.append(element('p', `Важность: ${{ critical: 'Критическая', major: 'Высокая', minor: 'Низкая' }[question.severity] || question.severity}`, 'severity'));
    if (question.affected_fields?.length) questionCell.append(element('p', `Влияет на: ${question.affected_fields.join(', ')}`, 'small'));
    if (question.evidence?.length) {
      const details = element('details', undefined, 'evidence');
      details.append(element('summary', `Основания в документе (${question.evidence.length})`));
      for (const ref of question.evidence) {
        details.append(element('p', `${ref.source_id}, строки ${ref.start_line}–${ref.end_line}`), element('blockquote', ref.text));
      }
      questionCell.append(details);
    }
    row.append(controlCell, questionCell);
    for (const [label, value] of [['ТЕКУЩЕЕ ПОНИМАНИЕ', question.understanding], ['ПОЧЕМУ ЭТО ВАЖНО', question.importance]]) {
      const cell = element('td', undefined, 'detail-cell');
      cell.append(element('span', label, 'mobile-label'), document.createTextNode(value || 'Не получено от сервиса.'));
      row.append(cell);
    }
    body.append(row);
  });
  state.selected = new Set([...state.selected].filter(id => result.questions.some(question => question.id === id)));
  updateSelection();
}

function acceptResult(payload, partial = false, render = true) {
  const result = normalizeResult(payload);
  state.result = partial || result.status === 'partial'
    ? mergePartialResult(state.result, result) : result;
  if (render) renderResult();
}

function showError(title, message) {
  byId('error-title').textContent = title;
  byId('error-message').textContent = message;
  byId('analysis-error').hidden = false;
}

function setStatus(name) {
  const labels = { processing: '◌ Обработка…', complete: '✓ Анализ завершён', partial: '◐ Частичный результат', error: '! Ошибка анализа' };
  byId('status-badge').textContent = labels[name];
  byId('status-badge').dataset.state = name;
}

function logEvent(action, questions, details = {}) {
  if (state.mode === 'demo' || !state.resultId) return Promise.resolve();
  const body = JSON.stringify({
    engine: state.engine,
    process_id: state.resultId,
    action,
    questions: questions.map(question => ({ id: question.id, text: question.text })),
    source_names: byId('source-label').textContent,
    details,
  });
  const task = eventQueue.then(async () => {
    const response = await fetch('/api/question_events', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body, credentials: 'same-origin', cache: 'no-store',
    });
    if (!response.ok) throw new Error(`Не удалось сохранить действие (${response.status}).`);
  });
  eventQueue = task.catch(error => {
    console.warn('Действие с вопросами не записано.', error);
  });
  return task;
}

function scheduleRestore(run) {
  if (state.mode === 'demo' || !state.resultId || !state.result) return;
  const snapshot = state.selected.size;
  eventQueue = eventQueue.then(async () => {
    if (run !== state.run || state.selected.size !== snapshot) return;
    const response = await fetch(`/api/question_events/${state.engine}/${encodeURIComponent(state.resultId)}`, {
      credentials: 'same-origin', cache: 'no-store',
    });
    if (!response.ok || run !== state.run || state.selected.size !== snapshot) return;
    const payload = await response.json();
    if (run !== state.run || !state.result || state.selected.size !== snapshot) return;
    const known = new Set(state.result.questions.map(question => question.id));
    state.selected = new Set((Array.isArray(payload.questions) ? payload.questions : [])
      .map(question => question?.id)
      .filter(id => known.has(id)));
    updateSelection();
  }).catch(error => {
    console.warn('Не удалось восстановить отметки.', error);
  });
}

function applyOrder(order) {
  if (!state.result || !Array.isArray(order) || !order.length) return;
  const byId = new Map(state.result.questions.map(question => [question.id, question]));
  const ordered = [];
  const seen = new Set();
  for (const id of order) {
    const question = byId.get(id);
    if (!question || seen.has(id)) continue;
    ordered.push(question);
    seen.add(id);
  }
  for (const question of state.result.questions) {
    if (!seen.has(question.id)) ordered.push(question);
  }
  state.result = { ...state.result, questions: ordered };
}

function persistState(payload) {
  const task = stateQueue.then(async () => {
    const response = await fetch('/api/state', {
      method: 'PUT',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Не удалось сохранить состояние (${response.status}).`);
    return response.json();
  });
  stateQueue = task.catch(error => {
    console.warn('Состояние анализа не сохранено.', error);
  });
  return task;
}

async function loadBrief(processId) {
  const panel = byId('tz-panel');
  if (!processId || state.mode === 'demo' || state.engine !== 'case-finder') {
    panel.hidden = true;
    return;
  }
  try {
    const response = await fetch(`/api/get_input/${encodeURIComponent(processId)}`, {
      credentials: 'same-origin', cache: 'no-store',
    });
    if (!response.ok) return;
    const payload = await response.json();
    byId('tz-files').textContent = (Array.isArray(payload.files) ? payload.files : []).map(file => file.original_name).filter(Boolean).join(' · ');
    byId('tz-text').textContent = typeof payload.text === 'string' ? payload.text : '';
    panel.hidden = false;
    panel.open = true;
  } catch (error) {
    console.warn('Не удалось показать техническое задание.', error);
  }
}

async function rememberQuestions() {
  if (state.mode === 'demo' || !state.resultId || state.result?.kind !== 'case-finder') return null;
  try {
    const saved = await persistState({
      engine: state.engine,
      process_id: state.resultId,
      source_names: byId('source-label').textContent,
      questions: state.result.questions.map(question => ({
        id: question.id,
        text: question.text,
        group: question.group || '',
        understanding: question.understanding || '',
        importance: question.importance || '',
      })),
    });
    if (saved?.question_order) {
      state.questionOrder = saved.question_order;
      state.confirmed = Boolean(saved.confirmed_at);
      applyOrder(saved.question_order);
    }
    return saved;
  } catch (error) {
    console.warn('Порядок вопросов не сохранён.', error);
    return null;
  }
}

function setAccount(username) {
  state.username = username;
  byId('login-toggle').hidden = Boolean(username);
  byId('login-form').hidden = true;
  byId('account-bar').hidden = !username;
  byId('account-name').textContent = username || '';
  byId('login-error').hidden = true;
  updateForm();
}

async function restoreSavedAnalysis() {
  const response = await fetch('/api/state', { credentials: 'same-origin', cache: 'no-store' });
  if (!response.ok) return;
  const saved = await response.json();
  if (!saved?.process_id) return;
  state.engine = saved.engine === 'factory' ? 'factory' : 'case-finder';
  byId('engine').value = state.engine;
  state.processId = saved.process_id;
  state.resultId = saved.process_id;
  state.questionOrder = Array.isArray(saved.question_order) ? saved.question_order : null;
  state.confirmed = Boolean(saved.confirmed_at);
  byId('source-label').textContent = saved.source_names || '';
  await startAnalysis('service', { resume: true });
}

async function confirmSelection() {
  if (state.confirmed || state.result?.kind !== 'case-finder' || !state.selected.size) return;
  if (!window.confirm('Отправить разметку? Изменить выбор после подтверждения будет нельзя.')) return;
  const questions = state.result.questions.filter(question => state.selected.has(question.id));
  try {
    await logEvent('confirm', questions, {
      count: questions.length,
      order: state.result.questions.map(question => question.id),
    });
  } catch (error) {
    console.warn('Разметка не подтверждена.', error);
    byId('confirm-message').textContent = 'Не удалось сохранить разметку. Повторите попытку.';
    return;
  }
  state.confirmed = true;
  byId('confirm-message').textContent = 'Разметка сохранена.';
  byId('revise').textContent = 'Новое ТЗ';
  renderResult();
}

async function startAnalysis(mode, { resume = false } = {}) {
  if (state.running || state.reading) return;
  if (mode !== 'demo' && !resume && !state.username) return;
  if (mode !== 'demo' && !resume && !byId('description').value.trim() && !state.files.length) return;
  if (mode !== 'demo' && !resume && state.engine === 'factory' && (!state.files.length || state.files.some(entry => extension(entry.file.name) !== 'md'))) {
    byId('file-errors').textContent = 'Для фабрики загрузите только Markdown-файлы (.md).';
    byId('file-errors').hidden = false;
    return;
  }
  const run = ++state.run;
  if (!resume) {
    state.confirmed = false;
    state.questionOrder = null;
    byId('confirm-message').textContent = '';
    byId('revise').textContent = 'Загрузить исправленное ТЗ';
    byId('tz-panel').hidden = true;
  }
  state.resultId = state.processId;
  const input = { text: state.engine === 'factory' ? '' : byId('description').value.trim(), files: state.files.map(entry => entry.file) };
  state.mode = mode;
  state.running = true;
  state.result = null;
  state.selected.clear();
  byId('input-screen').hidden = true;
  byId('analysis-screen').hidden = false;
  byId('summary-section').hidden = true;
  byId('maturity-section').hidden = true;
  byId('questions-section').hidden = true;
  byId('result-note').hidden = true;
  byId('analysis-error').hidden = true;
  byId('retry').hidden = true;
  byId('revise').hidden = true;
  byId('copy-message').textContent = '';
  byId('copy-fallback').hidden = true;
  byId('analysis-title').textContent = 'Анализ технического задания';
  byId('progress-panel').hidden = false;
  byId('analysis-progress').removeAttribute('value');
  byId('progress-description').textContent = mode === 'demo'
    ? 'Открываем готовый пример. Ваши материалы не анализируются и никуда не отправляются.'
    : 'Изучаем материалы и готовим уточняющие вопросы.';
  byId('demo-label').hidden = mode !== 'demo';
  if (!(resume && byId('source-label').textContent)) {
    byId('source-label').textContent = mode === 'demo' ? 'Пример ТЗ: портал закупок'
      : [...input.files.map(file => file.name), ...(input.text ? ['Текстовое описание задачи'] : [])].join(' · ');
  }
  setStep('processing');
  setStatus('processing');
  updateForm();
  window.scrollTo({ top: 0, behavior: 'instant' });
  try {
    if (mode === 'demo') {
      await new Promise(resolve => setTimeout(resolve, 450));
      if (run !== state.run) return;
      acceptResult(demoResult);
    } else {
      const result = await analyzeDocument({
        ...input,
        engine: state.engine,
        processId: state.processId,
        onCreated(id) {
          state.processId = id;
          state.resultId = id;
          void persistState({
            engine: state.engine,
            process_id: id,
            source_names: byId('source-label').textContent,
            questions: null,
          });
        },
        onProgress(message, progress) {
          if (run !== state.run || !state.running) return;
          if (typeof message === 'string') byId('progress-description').textContent = message;
          if (Number.isFinite(progress)) byId('analysis-progress').value = Math.max(0, Math.min(100, progress));
        },
        onPartial(payload) {
          if (run === state.run && state.running) acceptResult(payload, true);
        },
      });
      if (run !== state.run) return;
      acceptResult(result, false, false);
      state.resultId = state.processId || state.resultId;
      state.processId = null;
      await rememberQuestions();
      await loadBrief(state.resultId);
      renderResult();
    }
    setStatus(state.result.status);
    if (state.result.status === 'partial') {
      showError(factoryErrorHeading(state.result.error?.code) || 'Получен частичный результат', state.result.message || 'Часть данных не получена. Доступные вопросы можно выбрать и скопировать. Повторите обработку, чтобы получить полный результат.');
    }
  } catch (error) {
    if (run !== state.run) return;
    console.error('Анализ не завершён.', error);
    const partial = Boolean(state.result);
    state.processId = error.processId || null;
    if (state.processId) state.resultId = state.processId;
    setStatus(partial ? 'partial' : 'error');
    const fallback = partial ? 'Обработка прервалась. Частичный результат сохранён.' : 'Не удалось выполнить анализ';
    showError(factoryErrorHeading(error.code) || fallback, error instanceof Error ? error.message : 'Произошла ошибка. Повторите обработку.');
  } finally {
    if (run === state.run) {
      state.running = false;
      byId('progress-panel').hidden = true;
      byId('retry').hidden = mode === 'demo';
      byId('retry').textContent = state.processId ? 'Продолжить получение результата' : 'Повторить обработку';
      byId('revise').hidden = false;
      if (state.confirmed) {
        byId('confirm-message').textContent = 'Разметка сохранена.';
        byId('revise').textContent = 'Новое ТЗ';
      }
      setStep(state.result ? 'results' : 'processing');
      updateForm();
      scheduleRestore(run);
    }
  }
}

async function copyQuestions(button, placement) {
  if (!state.selected.size || !state.result) return;
  const questions = state.result.questions.filter(question => state.selected.has(question.id));
  const text = selectedText(state.result.questions, state.selected);
  const count = state.selected.size;
  const details = { count, button: button.textContent.trim(), placement };
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard API недоступен.');
    await navigator.clipboard.writeText(text);
    byId('copy-message').textContent = `Скопировано вопросов: ${count}. Включены текущее понимание и пояснение, почему вопрос важен.`;
    logEvent('copy', questions, details);
  } catch (error) {
    console.warn('Автоматическое копирование недоступно.', error);
    byId('copy-message').textContent = 'Браузер не разрешил копирование. Скопируйте подготовленный текст вручную.';
    byId('copy-fallback').hidden = false;
    byId('copy-text').value = text;
    byId('copy-text').focus();
    byId('copy-text').select();
    logEvent('copy_manual', questions, details);
  }
}

byId('service-note').textContent = serviceNotice;
byId('login-toggle').addEventListener('click', () => {
  byId('login-form').hidden = !byId('login-form').hidden;
  if (!byId('login-form').hidden) byId('api-username').focus();
});
byId('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  byId('login-error').hidden = true;
  let response;
  try {
    response = await fetch('/api/session', {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: byId('api-username').value, password: byId('api-password').value }),
    });
  } catch (error) {
    console.warn('Вход не выполнен.', error);
    byId('login-error').hidden = false;
    byId('login-error').textContent = 'Не удалось войти. Проверьте соединение и повторите попытку.';
    return;
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    byId('login-error').hidden = false;
    byId('login-error').textContent = payload.detail || 'Не удалось войти.';
    return;
  }
  byId('api-password').value = '';
  setAccount(payload.username);
  await restoreSavedAnalysis();
});
byId('logout').addEventListener('click', async () => {
  await fetch('/api/session', { method: 'DELETE', credentials: 'same-origin', cache: 'no-store' }).catch(() => {});
  ++state.run;
  state.running = false;
  state.result = null;
  state.processId = null;
  state.resultId = null;
  state.confirmed = false;
  state.questionOrder = null;
  byId('analysis-screen').hidden = true;
  byId('input-screen').hidden = false;
  byId('tz-panel').hidden = true;
  setStep('input');
  setAccount(null);
});
confirmButtons.forEach(button => button.addEventListener('click', () => void confirmSelection()));
byId('description').addEventListener('input', updateForm);
byId('analysis-form').addEventListener('submit', event => { event.preventDefault(); void startAnalysis('service'); });
byId('example').addEventListener('click', () => void startAnalysis('demo'));
byId('engine').addEventListener('change', () => {
  if (state.running || state.reading || state.processId) { byId('engine').value = state.engine; return; }
  state.engine = byId('engine').value;
  updateForm();
});
byId('retry').addEventListener('click', () => void startAnalysis(state.mode));
byId('files').addEventListener('change', event => {
  void addFiles([...event.target.files]);
  event.target.value = '';
});
byId('replacement').addEventListener('change', event => {
  void addFiles([...event.target.files], state.replacementId);
  event.target.value = '';
  state.replacementId = null;
});
const dropzone = byId('dropzone');
dropzone.addEventListener('dragover', event => { event.preventDefault(); if (!state.reading && !state.running) dropzone.classList.add('drag-over'); });
dropzone.addEventListener('dragleave', event => { if (!dropzone.contains(event.relatedTarget)) dropzone.classList.remove('drag-over'); });
dropzone.addEventListener('drop', event => {
  event.preventDefault();
  dropzone.classList.remove('drag-over');
  void addFiles([...event.dataTransfer.files]);
});
byId('select-all').addEventListener('click', () => {
  if (state.confirmed && state.result?.kind === 'case-finder') return;
  const questions = state.result?.questions || [];
  state.selected = selectAll(questions);
  updateSelection();
  logEvent('select_all', questions);
});
byId('clear').addEventListener('click', () => {
  if (state.confirmed && state.result?.kind === 'case-finder') return;
  const questions = (state.result?.questions || []).filter(question => state.selected.has(question.id));
  state.selected.clear();
  updateSelection();
  logEvent('clear', questions);
});
copyButtons.forEach((button, index) => button.addEventListener('click', () => void copyQuestions(button, index === 0 ? 'toolbar' : 'footer')));
byId('revise').addEventListener('click', () => {
  if (state.running) return;
  ++state.run;
  state.files = [];
  state.result = null;
  state.processId = null;
  state.resultId = null;
  state.confirmed = false;
  state.questionOrder = null;
  state.selected.clear();
  byId('confirm-message').textContent = '';
  byId('tz-panel').hidden = true;
  byId('revise').textContent = 'Загрузить исправленное ТЗ';
  void persistState({ engine: state.engine, process_id: null, source_names: '', questions: null });
  byId('analysis-form').reset();
  byId('engine').value = state.engine;
  byId('file-errors').hidden = true;
  byId('analysis-screen').hidden = true;
  byId('input-screen').hidden = false;
  setStep('input');
  renderFiles();
  byId('description').focus();
});
updateForm();
void (async () => {
  try {
    const response = await fetch('/api/session', { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) return;
    const payload = await response.json();
    setAccount(payload.username);
    await restoreSavedAnalysis();
  } catch (error) {
    console.warn('Не удалось восстановить сессию.', error);
  }
})();
