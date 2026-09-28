// Local-only visual fixtures. This server is never included in web/dist or deployment artifacts.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';

const publicFiles = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/model.js', ['model.js', 'text/javascript; charset=utf-8']],
  ['/demo.js', ['demo.js', 'text/javascript; charset=utf-8']],
]);
const fixtureAdapter = `
import { demoResult } from './demo.js';
export const serviceNotice = 'Тестовый стенд для снимков интерфейса. Используются только демонстрационные данные; документы никуда не отправляются.';
export async function analyzeDocument({ onProgress, onPartial }) {
  const scenario = new URL(location.href).searchParams.get('scenario');
  onProgress('Проверяем полноту требований и формируем уточняющие вопросы.');
  if (scenario === 'processing') return new Promise(() => {});
  if (scenario === 'error') throw new Error('Сервис анализа временно недоступен. Проверьте соединение и повторите обработку.');
  if (scenario === 'partial') {
    onPartial({ ...demoResult, status: 'partial', questions: demoResult.questions.slice(0, 8) });
    throw new Error('Соединение с сервисом прервалось. Полученные 8 вопросов сохранены и доступны для копирования.');
  }
  return demoResult;
}
`;

const server = createServer(async (request, response) => {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    response.writeHead(405, { Allow: 'GET, HEAD' }).end();
    return;
  }
  const path = new URL(request.url, 'http://localhost').pathname;
  try {
    const asset = publicFiles.get(path);
    if (path !== '/analysis.js' && !asset) {
      response.writeHead(404).end('Not found');
      return;
    }
    const body = path === '/analysis.js' ? fixtureAdapter : await readFile(new URL(`../dist/${asset[0]}`, import.meta.url));
    response.writeHead(200, {
      'Content-Type': path === '/analysis.js' ? 'text/javascript; charset=utf-8' : asset[1],
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
    });
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch (error) {
    console.error('Visual fixture server failed.', error);
    response.writeHead(500).end('Fixture server error');
  }
});
server.on('error', error => { console.error(error); process.exitCode = 1; });
server.listen(4174, '127.0.0.1', () => console.log('Visual fixtures: http://127.0.0.1:4174/?scenario=complete'));
