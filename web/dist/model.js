export const MAX_FILE_SIZE = 30 * 1024 * 1024;
export const QUESTION_COUNT = 20;
export const QUESTION_GROUPS = {
  baseline: 'По вашим материалам',
  enriched: 'С учётом похожих кейсов',
};
const ALLOWED_EXTENSIONS = new Set(['md', 'docx', 'pdf', 'txt']);

export function extension(name) {
  return name.split('.').pop().toLowerCase();
}

export function fileSize(bytes) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.ceil(bytes / 1024))} КБ`
    : `${(bytes / (1024 * 1024)).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} МБ`;
}

// This is a client-side preflight. PDF/DOCX parsing and scan detection belong to the analysis service.
export async function validateFile(file, engine = 'case-finder') {
  const format = extension(file.name);
  if (engine === 'factory' && format !== 'md') return 'Фабрика принимает только Markdown-файлы (.md).';
  if (!ALLOWED_EXTENSIONS.has(format)) return 'Поддерживаются только MD, DOCX, PDF и TXT.';
  if (file.size === 0) return 'Файл пуст. Выберите документ с содержимым.';
  if (file.size > MAX_FILE_SIZE) return 'Размер файла превышает 30 МБ.';
  try {
    if (format === 'txt' || format === 'md') {
      if (!(await file.text()).trim()) return 'Документ не содержит текста.';
    } else {
      await file.slice(0, 8).arrayBuffer();
    }
  } catch (error) {
    console.warn('Не удалось прочитать выбранный файл.', error);
    return 'Файл недоступен для чтения. Выберите его заново.';
  }
  return null;
}

/** Preserve displayable fields of an incomplete response without inventing content. */
export function normalizeResult(payload) {
  if (!payload || typeof payload !== 'object') throw new Error('Сервис вернул некорректный результат. Повторите обработку.');
  if (payload.kind === 'factory') {
    const summary = Array.isArray(payload.summary) ? payload.summary.filter(item => typeof item === 'string' && item.trim()) : [];
    const questions = [];
    const seen = new Set();
    let valid = Array.isArray(payload.questions) && Array.isArray(payload.summary);
    for (const item of Array.isArray(payload.questions) ? payload.questions : []) {
      if (!item || typeof item.id !== 'string' || !item.id.trim() || seen.has(item.id) || typeof item.text !== 'string' || !item.text.trim()) {
        valid = false;
        continue;
      }
      seen.add(item.id);
      const question = { id: item.id, text: item.text };
      for (const key of ['subsystem', 'understanding', 'importance', 'severity']) question[key] = typeof item[key] === 'string' ? item[key] : '';
      question.evidence = (Array.isArray(item.evidence) ? item.evidence : []).filter(ref => ref && typeof ref.source_id === 'string'
        && Number.isInteger(ref.start_line) && ref.start_line > 0 && Number.isInteger(ref.end_line) && ref.end_line >= ref.start_line && typeof ref.text === 'string');
      question.affected_fields = (Array.isArray(item.affected_fields) ? item.affected_fields : []).filter(value => typeof value === 'string');
      questions.push(question);
    }
    if (!valid && !summary.length && !questions.length) throw new Error('В ответе нет доступных результатов. Повторите обработку.');
    return {
      kind: 'factory', title: typeof payload.title === 'string' ? payload.title : 'Анализ агентской фабрики',
      summary, questions, status: payload.status === 'complete' && valid ? 'complete' : 'partial',
      maturity: (Array.isArray(payload.maturity) ? payload.maturity : []).filter(item => item && ['component', 'level', 'reason'].every(key => typeof item[key] === 'string')),
      message: typeof payload.message === 'string' ? payload.message : '',
    };
  }
  if (payload.kind === 'case-finder') {
    const questions = [];
    let complete = true;
    for (const group of Object.keys(QUESTION_GROUPS)) {
      const items = payload[group];
      if (!Array.isArray(items) || items.length !== QUESTION_COUNT) complete = false;
      for (const [index, text] of (Array.isArray(items) ? items : []).entries()) {
        if (typeof text !== 'string' || !text.trim()) { complete = false; continue; }
        questions.push({ id: `${group}-${index + 1}`, group, text, subsystem: '', understanding: '', importance: '' });
      }
    }
    if (!questions.length) throw new Error('В ответе нет доступных вопросов. Повторите обработку.');
    return {
      kind: 'case-finder', title: 'Вопросы к техническому заданию', summary: [], questions,
      status: complete ? 'complete' : 'partial',
      message: complete ? '' : 'Сервер вернул неполные наборы вопросов. Доступные вопросы можно выбрать и скопировать.',
    };
  }
  const summary = Array.isArray(payload.summary)
    ? payload.summary.filter(text => typeof text === 'string' && text.trim())
    : [];
  const questions = [];
  const seen = new Set();
  let invalid = !Array.isArray(payload.questions);
  for (const item of Array.isArray(payload.questions) ? payload.questions : []) {
    if (!item || typeof item.id !== 'string' || !item.id.trim() || seen.has(item.id)
      || typeof item.text !== 'string' || !item.text.trim()) {
      invalid = true;
      continue;
    }
    seen.add(item.id);
    const question = { id: item.id, text: item.text };
    for (const key of ['subsystem', 'understanding', 'importance']) {
      question[key] = typeof item[key] === 'string' && item[key].trim() ? item[key] : '';
      if (!question[key]) invalid = true;
    }
    questions.push(question);
  }
  if (!summary.length && !questions.length) throw new Error('В ответе нет доступных результатов. Повторите обработку.');
  const complete = payload.status === 'complete' && !invalid
    && questions.length === QUESTION_COUNT && summary.length >= 2 && summary.length <= 3;
  return {
    title: typeof payload.title === 'string' && payload.title.trim() ? payload.title : 'Анализ технического задания',
    summary, questions, status: complete ? 'complete' : 'partial',
    message: typeof payload.message === 'string' ? payload.message : '',
  };
}

export function selectedText(questions, selected) {
  return questions.filter(question => selected.has(question.id))
    .map((question, index) => `${index + 1}. ${question.text}${question.group ? `\nНабор: ${QUESTION_GROUPS[question.group]}` : ''}\nТекущее понимание: ${question.understanding || (question.group ? 'Не предоставляется текущим API.' : 'Не получено от сервиса.')}`)
    .join('\n\n');
}

export function mergePartialResult(previous, incoming) {
  if (!previous) return { ...incoming, status: 'partial' };
  const questions = new Map(previous.questions.map(question => [question.id, question]));
  for (const update of incoming.questions) {
    const current = questions.get(update.id);
    const merged = { ...update };
    for (const field of ['subsystem', 'understanding', 'importance']) {
      if (!merged[field] && current?.[field]) merged[field] = current[field];
    }
    questions.set(update.id, merged);
  }
  return {
    ...incoming,
    status: 'partial',
    title: incoming.title === 'Анализ технического задания' ? previous.title : incoming.title,
    summary: incoming.summary.length ? incoming.summary : previous.summary,
    questions: [...questions.values()],
  };
}

export function selectAll(questions) {
  return new Set(questions.map(question => question.id));
}
