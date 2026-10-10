import { QUESTION_COUNT } from './model.js';

const factoryErrorTitles = {
  document_rejected: 'Документ не подходит',
  model_unavailable: 'Модель провайдера недоступна',
  provider_quota: 'Закончился баланс провайдера',
  pipeline_failed: 'Ошибка анализа',
  interrupted: 'Анализ прерван',
};

export function factoryErrorHeading(code) {
  return factoryErrorTitles[code] || '';
}

function codedDetail(detail) {
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) return null;
  if (typeof detail.code !== 'string' || typeof detail.message !== 'string' || !detail.message.trim()) return null;
  if (!Object.hasOwn(factoryErrorTitles, detail.code)) return null;
  return detail;
}

const stages = {
  queued: 'Задание в очереди…',
  running: 'Фабрика проверяет разделы паспорта и связи между ними…',
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
  const coded = codedDetail(detail);
  if (coded) {
    const error = new Error(coded.message);
    error.code = coded.code;
    error.status = response.status;
    return error;
  }
  const message = typeof detail === 'string' ? detail
    : Array.isArray(detail) ? detail.map(item => item.msg).filter(Boolean).join('; ')
      : detail?.message;
  const error = new Error(response.status === 401
    ? 'Неверный логин или пароль. Войдите снова и повторите попытку.'
    : `Ошибка сервера (${response.status}). ${message || 'Повторите попытку позже.'}`);
  error.status = response.status;
  return error;
}

/** Uses the existing multipart/job API. The server session cookie authorizes every request. */
export async function analyzeDocument({ text, files, processId = null, engine = 'case-finder', onCreated = () => {}, onProgress = () => {} }) {
  const factory = engine === 'factory';
  if (!['case-finder', 'factory'].includes(engine)) throw new Error('Неизвестный способ анализа.');
  if (factory && !processId && (text.trim() || !files.length || files.some(file => !file.name.toLowerCase().endsWith('.md')))) {
    throw new Error('Для фабрики загрузите только Markdown-файлы (.md), без текста в поле описания.');
  }
  const prefix = factory ? '/factory' : '';
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetch(`/api${prefix}${path}`, {
        ...options, credentials: 'same-origin', cache: 'no-store', redirect: 'error',
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
      if (!factory) body.append('text', text);
      for (const file of files) body.append('files', file, file.name);
      if (!factory) {
        body.append('question_count', String(QUESTION_COUNT));
        body.append('language', 'Russian');
      }
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
      if (factory && payload.status === 'failed') {
        try {
          const result = await request(`/get_result/${id}`);
          if (result.response.status !== 200) throw new Error('Сервер не вернул частичный результат.');
          return { ...result.payload, kind: 'factory', status: 'partial' };
        } catch (error) {
          const progress = codedDetail(payload.error);
          if (!error.code && progress) {
            const classified = new Error(progress.message);
            classified.code = progress.code;
            classified.status = error.status ?? 409;
            throw classified;
          }
          throw error;
        }
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
        const result = await request(factory ? `/get_result/${id}` : `/get_questions/${id}?mode=both`);
        if (result.response.status === 200) return { ...result.payload, kind: factory ? 'factory' : 'case-finder' };
        if (result.response.status !== 202) throw new Error('Сервер вернул некорректный статус результата.');
      }
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  } catch (error) {
    error.processId = [404, 409].includes(error.status) ? null : processId;
    throw error;
  }
}

export const serviceNotice = 'Материалы отправляются на сервер Case Finder, сохраняются в архиве документов и передаются в OpenAI. Вопросы показываются одним списком, без подписи набора. Демопример не отправляет ваши материалы.';

export const factoryNotice = 'Фабрика принимает только Markdown-файлы (.md) по тематике LLM-ассистентов и AI-агентских систем. Материалы сохраняются на сервере и передаются настроенному провайдеру моделей. Число замечаний определяется документом; фиксированной квоты вопросов нет.';
