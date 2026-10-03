import { QUESTION_COUNT } from './model.js';

const stages = {
  queued: 'Задание в очереди…',
  generating_baseline: 'Готовим вопросы по вашим материалам…',
  summarizing: 'Анализируем описание задачи…',
  embedding: 'Подготавливаем поиск похожих кейсов…',
  retrieving: 'Ищем похожие кейсы…',
  filtering: 'Отбираем релевантные кейсы…',
  generating_enriched: 'Готовим вопросы с учётом похожих кейсов…',
  completed: 'Получаем готовые вопросы…',
};

function apiError(response, payload) {
  const detail = payload?.detail;
  const message = typeof detail === 'string' ? detail
    : Array.isArray(detail) ? detail.map(item => item.msg).filter(Boolean).join('; ')
      : detail?.message;
  const error = new Error(response.status === 401
    ? 'Неверный логин или пароль. Исправьте данные доступа и повторите попытку.'
    : `Ошибка сервера (${response.status}). ${message || 'Повторите попытку позже.'}`);
  error.status = response.status;
  return error;
}

/** Uses the existing multipart/job API. Credentials and process ID stay in this tab. */
export async function analyzeDocument({ text, files, username, password, processId = null, onCreated = () => {}, onProgress = () => {} }) {
  if (!username || !password || username.includes(':') || !/^[\x20-\x7e]+$/.test(username + password)) {
    const error = new Error('Введите логин и пароль сервера латинскими буквами, цифрами или символами ASCII. Логин не должен содержать двоеточие.');
    error.processId = processId;
    throw error;
  }
  const headers = { Authorization: `Basic ${btoa(`${username}:${password}`)}` };
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetch(`/api${path}`, {
        ...options, headers, credentials: 'omit', cache: 'no-store', redirect: 'error',
        signal: AbortSignal.timeout(120_000),
      });
    } catch (cause) {
      throw new Error('Связь с сервером прервалась. Повторите попытку.'
        + (processId ? ' Уже созданное задание будет использовано повторно.' : ' Если отправка уже началась, задание могло быть создано на сервере.'), { cause });
    }
    let payload;
    try {
      payload = await response.json();
    } catch (cause) {
      throw new Error(`Сервер вернул нечитаемый ответ (${response.status}).`, { cause });
    }
    if (!response.ok) throw apiError(response, payload);
    return { response, payload };
  }

  try {
    if (!processId) {
      const body = new FormData();
      body.append('text', text);
      for (const file of files) body.append('files', file, file.name);
      body.append('question_count', String(QUESTION_COUNT));
      body.append('language', 'Russian');
      onProgress('Отправляем материалы и проверяем документы…');
      const { response, payload } = await request('/start_process', { method: 'POST', body });
      if (response.status !== 202 || typeof payload?.process_id !== 'string' || !/^[a-zA-Z0-9-]+$/.test(payload.process_id)) {
        throw new Error('Сервер не вернул корректный идентификатор задания.');
      }
      processId = payload.process_id;
      onCreated(processId);
    }
    const id = encodeURIComponent(processId);
    while (true) {
      const { response, payload } = await request(`/get_progress/${id}`);
      if (response.status !== 200 || !payload || typeof payload.status !== 'string') {
        throw new Error('Сервер вернул некорректный прогресс задания.');
      }
      if (payload.status === 'failed' || payload.status === 'deletion_requested') {
        processId = null;
        throw new Error(payload.status === 'failed'
          ? `Анализ завершился ошибкой. ${payload.error?.message || 'Сервер не сообщил подробности.'}`
          : 'Задание удаляется на сервере. Запустите новый анализ.');
      }
      if (!stages[payload.status]) throw new Error(`Неизвестный статус задания: ${payload.status}`);
      onProgress(stages[payload.status], payload.progress);
      if (payload.status === 'completed') {
        const result = await request(`/get_questions/${id}?mode=both`);
        if (result.response.status === 200) return { ...result.payload, kind: 'case-finder' };
        if (result.response.status !== 202) throw new Error('Сервер вернул некорректный статус результата.');
      }
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  } catch (error) {
    error.processId = [404, 409].includes(error.status) ? null : processId;
    throw error;
  }
}

export const serviceNotice = 'Материалы отправляются на сервер Case Finder, сохраняются там и передаются в OpenAI для анализа. Сервер возвращает два набора вопросов; резюме, подсистемы и пояснения в текущем API отсутствуют. Демопример не отправляет ваши материалы.';
