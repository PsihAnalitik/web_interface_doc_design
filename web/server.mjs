import { randomBytes } from 'node:crypto';
import { createServer, request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { defaultEventsDb, openEventsStore, parseEvent, parseState, StateConflict } from './events.mjs';

const MAX_EVENT_BODY = 256 * 1024;
const SESSION_MAX_AGE = 60 * 60 * 24 * 7;
const EVENT_PATH = /^\/api\/question_events\/(case-finder|factory)\/([a-zA-Z0-9-]+)$/;

const assets = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/model.js', ['model.js', 'text/javascript; charset=utf-8']],
  ['/analysis.js', ['analysis.js', 'text/javascript; charset=utf-8']],
  ['/demo.js', ['demo.js', 'text/javascript; charset=utf-8']],
  ['/document_design.md', ['../../docs/document_design.md', 'text/markdown; charset=utf-8']],
]);
function sendJson(response, status, body, extraHeaders = {}) {
  const headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    ...extraHeaders,
  };
  response.writeHead(status, headers);
  response.end(body === undefined ? undefined : JSON.stringify(body));
}

function readCookie(header, name) {
  if (typeof header !== 'string') return null;
  for (const part of header.split(';')) {
    const separator = part.indexOf('=');
    if (separator <= 0) continue;
    if (part.slice(0, separator).trim() !== name) continue;
    try {
      return decodeURIComponent(part.slice(separator + 1).trim());
    } catch {
      return null;
    }
  }
  return null;
}

function sessionCookie(sid) {
  const value = sid ? `sid=${encodeURIComponent(sid)}` : 'sid=';
  const maxAge = sid ? SESSION_MAX_AGE : 0;
  return `${value}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${maxAge}`;
}

function basicAuthorization(username, password) {
  return `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`;
}

async function readLimited(request) {
  const declared = Number(request.headers['content-length'] || 0);
  if (Number.isFinite(declared) && declared > MAX_EVENT_BODY) return { status: 413 };
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_EVENT_BODY) return { status: 413 };
    chunks.push(chunk);
  }
  return { raw: Buffer.concat(chunks).toString('utf8') };
}

export function createWebServer({
  apiUrl = process.env.API_URL || 'http://127.0.0.1:8000',
  factoryApiUrl = process.env.FACTORY_API_URL || 'http://127.0.0.1:8002',
  eventsDb = process.env.QUESTION_EVENTS_DB || defaultEventsDb,
} = {}) {
  const origins = { legacy: new URL(apiUrl), factory: new URL(factoryApiUrl) };
  for (const upstream of Object.values(origins)) {
    if (!['http:', 'https:'].includes(upstream.protocol) || upstream.username || upstream.password
      || upstream.pathname !== '/' || upstream.search || upstream.hash) {
      throw new Error('API_URL and FACTORY_API_URL must be HTTP(S) origins without credentials or a path.');
    }
  }
  const sessions = new Map();
  let store;
  function eventsStore() {
    if (!store) store = openEventsStore(eventsDb);
    return store;
  }
  function currentSession(request) {
    const sid = readCookie(request.headers.cookie, 'sid');
    if (!sid) return null;
    return sessions.get(sid) || null;
  }
  async function verifyCredentials(authorization) {
    for (const upstream of Object.values(origins)) {
      try {
        const incoming = await fetch(new URL('/whoami', upstream), {
          headers: { authorization },
          redirect: 'error',
          signal: AbortSignal.timeout(30_000),
        });
        await incoming.arrayBuffer().catch(() => {});
        if (incoming.status === 200) return { ok: true };
        if (incoming.status === 401 || incoming.status === 403) return { ok: false, status: 401 };
      } catch (error) {
        console.error('API недоступен.', error);
      }
    }
    return { ok: false, status: 502 };
  }
  async function confirmJob(engine, processId, authorization) {
    const upstream = engine === 'factory' ? origins.factory : origins.legacy;
    try {
      const incoming = await fetch(new URL(`/get_progress/${processId}`, upstream), {
        headers: authorization ? { authorization } : {},
        redirect: 'error',
        signal: AbortSignal.timeout(30_000),
      });
      await incoming.arrayBuffer().catch(() => {});
      return { status: incoming.status };
    } catch (error) {
      console.error('API недоступен.', error);
      return { status: 502 };
    }
  }
  function rejectAccess(response, access) {
    if (access.status === 502) {
      sendJson(response, 502, { detail: 'Сервер анализа недоступен. Проверьте запуск API.' });
      return;
    }
    sendJson(response, access.status, { detail: 'Задание недоступно.' });
  }
  function requireSession(request, response) {
    const session = currentSession(request);
    if (session) return session;
    sendJson(response, 401, { detail: 'Войдите, чтобы продолжить.' });
    return null;
  }
  const server = createServer(async (request, response) => {
  const url = new URL(request.url, 'http://localhost');
  if (url.pathname === '/api/session') {
    if (request.method === 'GET') {
      const session = currentSession(request);
      if (!session) {
        sendJson(response, 401, { detail: 'Войдите, чтобы продолжить.' });
        return;
      }
      sendJson(response, 200, { username: session.username });
      return;
    }
    if (request.method === 'DELETE') {
      const sid = readCookie(request.headers.cookie, 'sid');
      if (sid) {
        sessions.delete(sid);
        try {
          eventsStore().deleteSession(sid);
        } catch (error) {
          console.error('Не удалось завершить сессию.', error);
        }
      }
      sendJson(response, 204, undefined, { 'Set-Cookie': sessionCookie('') });
      return;
    }
    if (request.method !== 'POST') {
      response.writeHead(405, { Allow: 'GET, POST, DELETE' }).end('Method not allowed');
      return;
    }
    const body = await readLimited(request);
    if (body.status) {
      sendJson(response, body.status, { detail: 'Тело запроса слишком большое.' });
      return;
    }
    let payload;
    try {
      payload = JSON.parse(body.raw);
    } catch {
      sendJson(response, 400, { detail: 'Тело запроса должно быть JSON-объектом.' });
      return;
    }
    const username = payload?.username;
    const password = payload?.password;
    if (typeof username !== 'string' || typeof password !== 'string' || !username || !password
      || username.length > 200 || password.length > 200 || username.includes(':')) {
      sendJson(response, 400, { detail: 'Укажите логин и пароль. Логин не должен содержать двоеточие.' });
      return;
    }
    const authorization = basicAuthorization(username, password);
    const verified = await verifyCredentials(authorization);
    if (!verified.ok) {
      const detail = verified.status === 401
        ? 'Неверный логин или пароль.'
        : 'Сервер анализа недоступен. Проверьте запуск API.';
      sendJson(response, verified.status, { detail });
      return;
    }
    const sid = randomBytes(32).toString('base64url');
    sessions.set(sid, { username, authorization });
    try {
      eventsStore().createSession(sid, username);
    } catch (error) {
      sessions.delete(sid);
      console.error('Не удалось сохранить сессию.', error);
      sendJson(response, 500, { detail: 'Не удалось сохранить сессию.' });
      return;
    }
    sendJson(response, 200, { username }, { 'Set-Cookie': sessionCookie(sid) });
    return;
  }
  if (url.pathname === '/api/state') {
    const session = requireSession(request, response);
    if (!session) return;
    if (request.method === 'GET') {
      try {
        sendJson(response, 200, eventsStore().state(session.username));
      } catch (error) {
        console.error('Не удалось прочитать состояние.', error);
        sendJson(response, 500, { detail: 'Не удалось прочитать состояние.' });
      }
      return;
    }
    if (request.method !== 'PUT') {
      response.writeHead(405, { Allow: 'GET, PUT' }).end('Method not allowed');
      return;
    }
    const body = await readLimited(request);
    if (body.status) {
      sendJson(response, body.status, { detail: 'Тело запроса слишком большое.' });
      return;
    }
    let payload;
    try {
      payload = JSON.parse(body.raw);
    } catch {
      sendJson(response, 400, { detail: 'Тело запроса должно быть JSON-объектом.' });
      return;
    }
    const parsed = parseState(payload);
    if (parsed.error) {
      sendJson(response, 400, { detail: parsed.error });
      return;
    }
    try {
      sendJson(response, 200, eventsStore().saveState(session.username, parsed.state));
    } catch (error) {
      console.error('Не удалось сохранить состояние.', error);
      sendJson(response, 500, { detail: 'Не удалось сохранить состояние.' });
    }
    return;
  }
  if (url.pathname === '/api/question_events' || EVENT_PATH.test(url.pathname)) {
    const session = requireSession(request, response);
    if (!session) return;
    const listed = url.pathname === '/api/question_events';
    if (listed) {
      if (request.method !== 'POST') {
        response.writeHead(405, { Allow: 'POST' }).end('Method not allowed');
        return;
      }
      const body = await readLimited(request);
      if (body.status) {
        sendJson(response, body.status, { detail: 'Тело запроса слишком большое.' });
        return;
      }
      let payload;
      try {
        payload = JSON.parse(body.raw);
      } catch {
        sendJson(response, 400, { detail: 'Тело запроса должно быть JSON-объектом.' });
        return;
      }
      const parsed = parseEvent(payload);
      if (parsed.error) {
        sendJson(response, 400, { detail: parsed.error });
        return;
      }
      const access = await confirmJob(parsed.event.engine, parsed.event.processId, session.authorization);
      if (access.status !== 200) {
        rejectAccess(response, access);
        return;
      }
      try {
        eventsStore().record({ ...parsed.event, username: session.username });
      } catch (error) {
        if (error instanceof StateConflict) {
          sendJson(response, 409, { detail: error.message });
          return;
        }
        console.error('Не удалось записать действие с вопросами.', error);
        sendJson(response, 500, { detail: 'Не удалось записать действие.' });
        return;
      }
      response.writeHead(204, { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' }).end();
      return;
    }
    if (request.method !== 'GET') {
      response.writeHead(405, { Allow: 'GET' }).end('Method not allowed');
      return;
    }
    const match = EVENT_PATH.exec(url.pathname);
    const access = await confirmJob(match[1], match[2], session.authorization);
    if (access.status !== 200) {
      rejectAccess(response, access);
      return;
    }
    try {
      sendJson(response, 200, { questions: eventsStore().selection(session.username, match[1], match[2]) });
    } catch (error) {
      console.error('Не удалось прочитать отметки вопросов.', error);
      sendJson(response, 500, { detail: 'Не удалось прочитать отметки.' });
    }
    return;
  }
  if (url.pathname.startsWith('/api/')) {
    const factory = url.pathname.startsWith('/api/factory/');
    const upstream = factory ? origins.factory : origins.legacy;
    const path = url.pathname.slice(factory ? '/api/factory'.length : 4);
    const resultRoute = factory ? /^\/(get_progress|get_result)\/[a-zA-Z0-9-]+$/
      : /^\/(get_progress|get_questions|get_input)\/[a-zA-Z0-9-]+$/;
    const allowedMethod = path === '/start_process' ? 'POST'
      : resultRoute.test(path) ? 'GET' : null;
    if (!allowedMethod) {
      response.writeHead(404).end('Not found');
      return;
    }
    if (request.method !== allowedMethod) {
      response.writeHead(405, { Allow: allowedMethod }).end('Method not allowed');
      return;
    }
    const session = requireSession(request, response);
    if (!session) return;
    const headers = { authorization: session.authorization };
    for (const name of ['content-type', 'content-length', 'accept']) {
      if (request.headers[name]) headers[name] = request.headers[name];
    }
    const forward = upstream.protocol === 'https:' ? httpsRequest : httpRequest;
    const proxy = forward(new URL(path + url.search, upstream), {
      method: request.method, headers,
    }, incoming => {
      const responseHeaders = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
      if (incoming.headers['content-type']) responseHeaders['content-type'] = incoming.headers['content-type'];
      response.writeHead(incoming.statusCode, responseHeaders);
      incoming.on('error', error => {
        console.error('Ответ API прерван.', error);
        response.destroy(error);
      });
      incoming.pipe(response);
    });
    proxy.setTimeout(120_000, () => proxy.destroy(new Error('API request timed out')));
    proxy.on('error', error => {
      console.error('API недоступен.', error);
      if (response.destroyed) return;
      if (response.headersSent) response.destroy(error);
      else response.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' })
        .end(JSON.stringify({ detail: 'Сервер анализа недоступен. Проверьте запуск API.' }));
    });
    request.on('aborted', () => proxy.destroy());
    response.on('close', () => { if (!response.writableEnded) proxy.destroy(); });
    request.pipe(proxy);
    return;
  }
  if (!['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(405, { Allow: 'GET, HEAD' }).end('Method not allowed');
    return;
  }
  const asset = assets.get(url.pathname);
  if (!asset) {
    response.writeHead(404).end('Not found');
    return;
  }
  try {
    const body = await readFile(new URL(`./dist/${asset[0]}`, import.meta.url));
    response.writeHead(200, {
      'Content-Type': asset[1],
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'no-referrer',
      'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'",
    });
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch (error) {
    console.error('Не удалось отдать ресурс.', error);
    response.writeHead(500).end('Internal server error');
  }
  });
  server.on('close', () => store?.close());
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
const port = Number(process.env.PORT || 4173);
const host = process.env.HOST || '127.0.0.1';
const server = createWebServer();
server.on('error', error => {
  console.error('Не удалось запустить локальный сервер.', error);
  process.exitCode = 1;
});
server.listen(port, host, () => console.log(`Listening: http://${host}:${port}`));
}
