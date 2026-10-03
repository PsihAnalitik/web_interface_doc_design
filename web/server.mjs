import { createServer, request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const assets = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/model.js', ['model.js', 'text/javascript; charset=utf-8']],
  ['/analysis.js', ['analysis.js', 'text/javascript; charset=utf-8']],
  ['/demo.js', ['demo.js', 'text/javascript; charset=utf-8']],
]);
export function createWebServer({ apiUrl = process.env.API_URL || 'http://127.0.0.1:8000' } = {}) {
  const upstream = new URL(apiUrl);
  if (!['http:', 'https:'].includes(upstream.protocol) || upstream.username || upstream.password
    || upstream.pathname !== '/' || upstream.search || upstream.hash) {
    throw new Error('API_URL must be an HTTP(S) origin without credentials or a path.');
  }
  return createServer(async (request, response) => {
  const url = new URL(request.url, 'http://localhost');
  if (url.pathname.startsWith('/api/')) {
    const path = url.pathname.slice(4);
    const allowedMethod = path === '/start_process' ? 'POST'
      : /^\/(get_progress|get_questions)\/[a-zA-Z0-9-]+$/.test(path) ? 'GET' : null;
    if (!allowedMethod) {
      response.writeHead(404).end('Not found');
      return;
    }
    if (request.method !== allowedMethod) {
      response.writeHead(405, { Allow: allowedMethod }).end('Method not allowed');
      return;
    }
    const headers = {};
    for (const name of ['authorization', 'content-type', 'content-length', 'accept']) {
      if (request.headers[name]) headers[name] = request.headers[name];
    }
    const forward = upstream.protocol === 'https:' ? httpsRequest : httpRequest;
    const proxy = forward(new URL(path + url.search, upstream), {
      method: request.method, headers,
    }, incoming => {
      const responseHeaders = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
      for (const name of ['content-type', 'www-authenticate']) {
        if (incoming.headers[name]) responseHeaders[name] = incoming.headers[name];
      }
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
