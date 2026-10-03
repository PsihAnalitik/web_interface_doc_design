# Case Finder API

FastAPI-сервис принимает описание ML/AI-кейса и документы, сохраняет оригиналы и
извлечённый текст, а затем в отдельном worker-контейнере генерирует два набора
вопросов:

- `baseline` — только по загруженной информации;
- `enriched` — по загруженной информации и релевантным кейсам из статической базы.

Состояние заданий и все артефакты хранятся в Docker volume в виде файлов. База
референсных кейсов и её готовый embedding-индекс включаются в image при сборке.

## Требования

- Docker Engine;
- Docker Compose v2;
- действующий OpenAI API key;
- внешний reverse proxy с HTTPS для production. Сам Compose публикует HTTP.

## Запуск

Из каталога `server`:

```bash
cp .env.example .env
```

Заполните `OPENAI_API_KEY` и замените пароль в `API_USERS`. Значение `API_USERS`
является JSON-объектом и поддерживает несколько пользователей, например:

```dotenv
API_USERS={"alice":"strong-password-1","bob":"strong-password-2"}
```

Если ключ выдан AITUNNEL, укажите его адрес отдельно от названия модели:

```dotenv
OPENAI_BASE_URL=https://api.aitunnel.ru/v1/
OPENAI_LLM_MODEL=gpt-4.1-mini
```

Для прямого доступа к OpenAI не задавайте `OPENAI_BASE_URL`. SDK читает эту
переменную из окружения. В `OPENAI_LLM_MODEL` всегда должен быть ID модели,
а не URL. Ключ должен принадлежать провайдеру, чей адрес указан в настройках.
После изменения `.env` выполните `make up` из корня проекта (или команду
Compose ниже): контейнеры получат новое окружение. Обычный `docker compose restart`
не применяет изменения `.env`.

Запустите API и worker:

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f api worker
```

Задания сохраняются в named volume `case_finder_storage` и переживают обычные
`docker compose down` и последующий `up`. Команда `docker compose down -v` удаляет
volume и все задания без возможности восстановления.

## Локальная разработка и тесты через uv

Требуются Python 3.12 и [uv](https://docs.astral.sh/uv/getting-started/installation/)
версии `>=0.12.20,<0.13`. Выполняйте из каталога `server`:

```bash
uv sync --locked
uv run --locked pytest -q
```

`pyproject.toml` — единственный список зависимостей сервера, `uv.lock` фиксирует
их точные версии. Оба файла хранятся в Git. Группа `dev` устанавливается по
умолчанию; Docker использует тот же lock-файл с `--no-dev`. Старые серверные
`requirements*.txt` заменены этими файлами; `../requirements.txt` относится
к ноутбукам и не используется сервером.

FastAPI ограничен диапазоном `<0.129.1`, чтобы сохранить существующий контракт
OpenAPI для файлов (`format: binary`). Начиная с 0.129.1 библиотека использует
`contentMediaType`; это [изменение FastAPI](https://fastapi.tiangolo.com/release-notes/#01291)
требует отдельного пересмотра контракта и его проверки, а не автоматического
обновления окружения. Тест схемы не изменён.

Для запуска без Docker сначала настройте `.env`, как описано выше, и добавьте
локальные пути (в Docker используются пути из контейнера):

```dotenv
STORAGE_PATH=./storage
TRAIN_CASES_PATH=../data/train/files
TRAIN_INDEX_PATH=../data/train/train_index.csv
```

Затем запустите в двух терминалах из `server`:

```bash
uv run --locked --env-file .env uvicorn app.main:app --host 127.0.0.1 --port 8000
uv run --locked --env-file .env python -m app.worker
```

Изменение зависимостей: `uv add <package>` или редактирование `pyproject.toml`
и `uv lock`. Для намеренного обновления версий используйте `uv lock --upgrade`,
затем `uv sync --locked` и повторите тесты. Обычный запуск с `--locked` не
обновляет lock-файл и выдаёт ошибку, если он расходится с описанием проекта.

Сквозной тест интерфейса с настоящими API и worker, но без внешних OpenAI-вызовов,
описан в [web/README.md](../../web/README.md).

## Swagger / OpenAPI

После запуска Swagger UI доступен по адресу:

```text
http://localhost:8000/docs
```

Альтернативная документация ReDoc: `http://localhost:8000/redoc`, JSON-схема:
`http://localhost:8000/openapi.json`. В Swagger нажмите **Authorize**, введите имя
пользователя и пароль из `API_USERS`, после чего можно выполнять запросы прямо из UI.

## API

Все четыре бизнес-эндпоинта защищены HTTP Basic Auth. В production Basic Auth
необходимо использовать только через HTTPS.

### Создать задание

`POST /start_process` принимает `multipart/form-data`:

- `text` — необязательный текст;
- `files` — до 10 файлов `.txt`, `.md`, `.docx` или `.pdf`; `.doc` не поддерживается;
- `question_count` — число вопросов, по умолчанию 7, максимум 50;
- `language` — язык итоговых вопросов, по умолчанию `English`.

PDF обрабатывается без OCR. У сканированного PDF без текстового слоя текст не
извлечётся. Если общий результат из `text` и всех файлов пуст, API возвращает `422`.
Ограничения по умолчанию: 20 MiB на файл и 100 MiB суммарно; они настраиваются в `.env`.

```bash
curl -u 'admin:replace-with-a-strong-password' \
  -X POST http://localhost:8000/start_process \
  -F 'text=Нужно классифицировать обращения клиентов' \
  -F 'files=@requirements.docx' \
  -F 'question_count=10' \
  -F 'language=Russian'
```

Ответ `202 Accepted`:

```json
{"process_id":"550e8400-e29b-41d4-a716-446655440000","status":"queued"}
```

Парсинг загруженных документов выполняется до ответа, чтобы API мог сразу вернуть
`422` для пустого или нечитаемого входа. Долгие OpenAI-вызовы выполняются worker-ом.

### Получить прогресс

```bash
curl -u 'admin:replace-with-a-strong-password' \
  http://localhost:8000/get_progress/550e8400-e29b-41d4-a716-446655440000
```

Статусы: `queued`, `generating_baseline`, `summarizing`, `embedding`, `retrieving`,
`filtering`, `generating_enriched`, `completed`, `failed`, `deletion_requested`.
Прогресс является стадийной оценкой от 0 до 100, а не процентом выполнения запроса OpenAI.

### Получить вопросы

Параметр `mode` принимает `baseline`, `enriched` или `both` (значение по умолчанию):

```bash
curl -u 'admin:replace-with-a-strong-password' \
  'http://localhost:8000/get_questions/550e8400-e29b-41d4-a716-446655440000?mode=both'
```

- `200` — результат готов;
- `202` — обработка ещё идёт;
- `409` — задание завершилось ошибкой, подробность ошибки возвращается клиенту;
- `404` — ID не найден.

### Удалить задание

```bash
curl -u 'admin:replace-with-a-strong-password' \
  -X DELETE http://localhost:8000/delete_job/550e8400-e29b-41d4-a716-446655440000
```

Для задания в очереди или завершённого задания файлы удаляются сразу. Если worker уже
обрабатывает задание, API выставляет `deletion_requested`; worker удалит оригиналы и
все результаты на следующей границе стадии.

## Хранимые данные

Для каждого задания volume содержит:

```text
jobs/<process_id>/
├── request.json
├── status.json
├── input/
│   ├── original/       # оригинальные файлы
│   ├── parsed/         # plain text каждого файла
│   └── combined.txt    # общий вход LLM
├── retrieval/
│   ├── summary.txt
│   ├── candidates.json
│   └── relevant_cases.json
├── baseline_questions.json
└── enriched_questions.json
```

Текст документов передаётся в OpenAI. Перед production-деплоем проверьте требования
организации к приватности, срокам хранения и обработке чувствительной информации.

## Обновление статической базы кейсов

Измените `data/train/files` и перестройте `data/train/train_index.csv` корневым
ноутбуком `prepare-train-data.ipynb`, затем пересоберите образы:

```bash
docker compose build --no-cache
docker compose up -d
```

После смены `OPENAI_EMBEDDING_MODEL` индекс обязательно нужно перестроить той же моделью.

## Логи и остановка

API и worker пишут структурированные JSON-логи в stdout/stderr:

```bash
docker compose logs -f --tail=200 api worker
docker compose down
```

Внешний reverse proxy должен добавлять TLS, ограничивать размер request body не ниже
настроенного лимита API и по возможности передавать `X-Request-ID`.
