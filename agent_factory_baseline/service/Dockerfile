FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.20 /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/vendor/workflow_ai:/app/case-finder-main/server \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/service/.venv/bin:$PATH"
WORKDIR /app/service
COPY agent_factory_baseline/service/pyproject.toml agent_factory_baseline/service/uv.lock ./
RUN uv sync --locked --no-dev --no-cache
WORKDIR /app
COPY vendor/workflow_ai ./vendor/workflow_ai
COPY agent_factory_baseline ./agent_factory_baseline
COPY case-finder-main/server/app ./case-finder-main/server/app
RUN useradd --create-home --uid 10001 factory \
    && mkdir -p /app/factory-storage \
    && chown factory:factory /app/factory-storage
USER factory
CMD ["uvicorn", "agent_factory_baseline.web_api:app", "--host", "0.0.0.0", "--port", "8002"]
