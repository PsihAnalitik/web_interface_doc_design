FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.20 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/server \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/server/.venv/bin:$PATH"

WORKDIR /app/server

COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --locked --no-dev --no-cache

COPY server/app ./app
COPY data/train /app/data/train

RUN useradd --create-home --uid 10001 casefinder \
    && mkdir -p /app/storage /app/documents \
    && chown -R casefinder:casefinder /app/storage /app/documents

USER casefinder

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
