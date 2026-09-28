import { extension, fileSize, validateFile, normalizeResult, mergePartialResult, selectedText, selectAll } from './model.js';
import { analyzeDocument, serviceNotice } from './analysis.js';
import { demoResult } from './demo.js';

const byId = id => document.getElementById(id);
const copyButtons = [...document.querySelectorAll('.copy')];
const state = {
  files: [], reading: false, running: false, result: null,
  selected: new Set(), mode: null, replacementId: null, run: 0,
};

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function updateForm() {
  const locked = state.reading || state.running;
  const ready = Boolean(byId('description').value.trim() || state.files.length);
  byId('analyze').disabled = locked || !ready;
  byId('example').disabled = locked;
  byId('files').disabled = locked;
  byId('replacement').disabled = locked;
  byId('description').disabled = locked;
  byId('dropzone').setAttribute('aria-disabled', String(locked));
  document.querySelectorAll('.file-actions button').forEach(button => { button.disabled = locked; });
  byId('ready-status').textContent = state.reading ? 'Проверяем выбранные файлы…'
    : ready ? 'Материалы готовы к отправке на анализ.' : 'Добавьте текст или хотя бы один документ.';
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
      const error = await validateFile(file);
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
  byId('select-all').disabled = questions.length === 0 || state.selected.size === questions.length;
  byId('clear').disabled = state.selected.size === 0;
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
    toggle.setAttribute('aria-label', `Выделить вопрос ${index + 1}`);
    toggle.setAttribute('aria-pressed', 'false');
    toggle.addEventListener('click', () => {
      if (state.selected.has(question.id)) state.selected.delete(question.id);
      else state.selected.add(question.id);
      updateSelection();
    });
    controlCell.append(toggle);
    const questionCell = element('td');
    const title = element('h3', undefined, 'question-title');
    title.append(element('span', `${String(index + 1).padStart(2, '0')}. `, 'question-number'), document.createTextNode(question.text));
    questionCell.append(title, element('span', question.subsystem || 'Подсистема не указана', 'subsystem'));
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

function acceptResult(payload, partial = false) {
  const result = normalizeResult(payload);
  state.result = partial || result.status === 'partial'
    ? mergePartialResult(state.result, result) : result;
  renderResult();
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

async function startAnalysis(mode) {
  if (state.running || state.reading) return;
  if (mode !== 'demo' && !byId('description').value.trim() && !state.files.length) return;
  const run = ++state.run;
  const input = { text: byId('description').value.trim(), files: state.files.map(entry => entry.file) };
  state.mode = mode;
  state.running = true;
  state.result = null;
  state.selected.clear();
  byId('input-screen').hidden = true;
  byId('analysis-screen').hidden = false;
  byId('summary-section').hidden = true;
  byId('questions-section').hidden = true;
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
  byId('source-label').textContent = mode === 'demo' ? 'Пример ТЗ: портал закупок'
    : [...input.files.map(file => file.name), ...(input.text ? ['Текстовое описание задачи'] : [])].join(' · ');
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
        onProgress(message) {
          if (run === state.run && state.running && typeof message === 'string') byId('progress-description').textContent = message;
        },
        onPartial(payload) {
          if (run === state.run && state.running) acceptResult(payload, true);
        },
      });
      if (run !== state.run) return;
      acceptResult(result);
    }
    setStatus(state.result.status);
    if (state.result.status === 'partial') {
      showError('Получен частичный результат', state.result.message || 'Часть данных не получена. Доступные вопросы можно выбрать и скопировать. Повторите обработку, чтобы получить полный результат.');
    }
  } catch (error) {
    if (run !== state.run) return;
    console.error('Анализ не завершён.', error);
    const partial = Boolean(state.result);
    setStatus(partial ? 'partial' : 'error');
    showError(partial ? 'Обработка прервалась. Частичный результат сохранён.' : 'Не удалось выполнить анализ', error instanceof Error ? error.message : 'Произошла ошибка. Повторите обработку.');
  } finally {
    if (run === state.run) {
      state.running = false;
      byId('progress-panel').hidden = true;
      byId('retry').hidden = mode === 'demo';
      byId('revise').hidden = false;
      setStep(state.result ? 'results' : 'processing');
      updateForm();
    }
  }
}

async function copyQuestions() {
  if (!state.selected.size || !state.result) return;
  const text = selectedText(state.result.questions, state.selected);
  const count = state.selected.size;
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard API недоступен.');
    await navigator.clipboard.writeText(text);
    byId('copy-message').textContent = `Скопировано вопросов: ${count}. Включено текущее понимание по каждому вопросу.`;
  } catch (error) {
    console.warn('Автоматическое копирование недоступно.', error);
    byId('copy-message').textContent = 'Браузер не разрешил копирование. Скопируйте подготовленный текст вручную.';
    byId('copy-fallback').hidden = false;
    byId('copy-text').value = text;
    byId('copy-text').focus();
    byId('copy-text').select();
  }
}

byId('service-note').textContent = serviceNotice;
byId('description').addEventListener('input', updateForm);
byId('analysis-form').addEventListener('submit', event => { event.preventDefault(); void startAnalysis('service'); });
byId('example').addEventListener('click', () => void startAnalysis('demo'));
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
  state.selected = selectAll(state.result?.questions || []);
  updateSelection();
});
byId('clear').addEventListener('click', () => { state.selected.clear(); updateSelection(); });
copyButtons.forEach(button => button.addEventListener('click', () => void copyQuestions()));
byId('revise').addEventListener('click', () => {
  if (state.running) return;
  ++state.run;
  state.files = [];
  state.result = null;
  state.selected.clear();
  byId('analysis-form').reset();
  byId('file-errors').hidden = true;
  byId('analysis-screen').hidden = true;
  byId('input-screen').hidden = false;
  setStep('input');
  renderFiles();
  byId('description').focus();
});
updateForm();
