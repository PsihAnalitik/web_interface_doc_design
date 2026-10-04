#!/usr/bin/env bash
set -euo pipefail

BASELINE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BASELINE_REPO="$(dirname -- "$BASELINE_DIR")"
FACTORY_DIR="${WORKFLOW_AI_PATH:-$(dirname -- "$BASELINE_REPO")/workflow_ai}"
FACTORY_PYTHON="${WORKFLOW_AI_PYTHON:-$FACTORY_DIR/.venv/bin/python}"
if [[ ! -f "$FACTORY_DIR/workshop/orchestrator.py" || ! -x "$FACTORY_PYTHON" ]]; then
  echo "Нужен checkout workflow_ai и его Python >=3.14. Задайте WORKFLOW_AI_PATH и при необходимости WORKFLOW_AI_PYTHON." >&2
  exit 2
fi
export PYTHONPATH="$BASELINE_REPO:$FACTORY_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec "$FACTORY_PYTHON" -m agent_factory_baseline "$@"
