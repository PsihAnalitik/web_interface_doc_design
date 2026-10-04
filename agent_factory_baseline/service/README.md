# Фабрика в веб-интерфейсе

В форме выберите **Агентская фабрика** и загрузите проверенные UTF-8 `.md`.
Старый **Case Finder** остаётся отдельным режимом с двумя наборами вопросов.
Фабрика ограничена доменом LLM-ассистентов и AI-агентских систем. В интерфейсе
есть ссылка для скачивания дизайн-документа проекта и пробной загрузки.
Для сравнения загрузите одинаковый Markdown в обеих вкладках. Новый анализ
запускается в отдельной вкладке; результаты и выделение вопросов не смешиваются.

## Сервер

Из корня репозитория:

```bash
make init
# Настройте case-finder-main/server/.env (или прежний ENV_FILE).
make up
```

Один `.env` обслуживает оба решения. Нужны `API_USERS`, `OPENAI_API_KEY` и,
если используется совместимый провайдер, `OPENAI_BASE_URL`. Ключи не попадают
в образ или браузер. Настройки моделей независимы:

```dotenv
# Старое решение — оставьте свою прежнюю модель:
OPENAI_LLM_MODEL=gpt-4.1-mini
# Фабрика:
FACTORY_MODEL=qwen3.7-plus
FACTORY_VERDICT_MODEL=qwen3.7-plus
```

Провайдер должен поддерживать выбранные модели. Фабрика передаёт reasoning `none`,
лимит генерации 32768 и использует wiki, чек-листы и паспорт из этого репозитория.
`agent_factory_baseline/.env` используется локальным CLI, **не Docker Compose**.
Если общий `.env` уже существует, `make init` его не перезаписывает: при
необходимости добавьте новые настройки в него вручную.

Compose запускает пять сервисов: прежние `api`, `worker`, `web` и новые
`factory-api`, `factory-worker`. Python 3.14 и снимок `workflow_ai` включены в
образ; соседний checkout на сервере не нужен. API фабрики доступен только внутри
Compose-сети через веб-прокси `/api/factory/`. Общий внешний сайт должен работать
через HTTPS, как и старый режим с Basic Auth.

Результаты фабрики находятся в отдельном volume `factory_storage` по пути
`/app/factory-storage/jobs/<id>/run`; приватные логи — рядом в `worker.log`.
В браузер возвращаются заключения, исходные фрагменты, приоритеты и зрелость,
но не внутренние логи/пути. Снимки источников и wiki остаются на сервере.
Запускайте **один** `factory-worker`: очередь исполняется последовательно.
Прогресс показывает очередь, исполнение и завершение, а не процент готовности
отдельных цехов. Анализ может занимать несколько минут.

Если synthesis не завершился, доступные локальные замечания показываются как
частичный результат. Ноль итоговых замечаний при успешном анализе — полный
результат. После рестарта worker прерванное задание получает `failed`, без
автоматического повторного расходования токенов. Новый анализ запускает человек.

## Без Docker

```bash
uv sync --locked --project agent_factory_baseline/service
export PYTHONPATH="$PWD:$PWD/vendor/workflow_ai:$PWD/case-finder-main/server"
export FACTORY_STORAGE_PATH="$PWD/agent_factory_baseline/.checks/web-storage"
# Экспортируйте API_USERS, OPENAI_API_KEY, OPENAI_BASE_URL из своей конфигурации.
agent_factory_baseline/service/.venv/bin/uvicorn agent_factory_baseline.web_api:app --host 127.0.0.1 --port 8002
# В другом терминале с тем же окружением:
agent_factory_baseline/service/.venv/bin/python -m agent_factory_baseline.web_worker
# В третьем:
cd web && FACTORY_API_URL=http://127.0.0.1:8002 npm start
```

Старые API/worker запускаются по прежней инструкции, если нужен режим Case Finder.

## Проверки и откат

```bash
PYTHONPATH="$PWD:$PWD/vendor/workflow_ai:$PWD/case-finder-main/server" \
  agent_factory_baseline/service/.venv/bin/python -m pytest agent_factory_baseline/tests
(cd web && npm run check && npm test)
docker build -f agent_factory_baseline/service/Dockerfile -t copilot-factory .
FACTORY_PYTHON="$PWD/agent_factory_baseline/service/.venv/bin/python" \
  node --test web/tests/factory-api-integration.mjs
```

Новая очередь не меняет формат и содержимое старого volume: миграции не нужны.
Для отката верните предыдущую версию репозитория и выполните `make up`.
Либо остановите только `factory-api`/`factory-worker` и используйте Case Finder.
Не удаляйте volumes: остановка сама по себе сохраняет документы и результаты.
