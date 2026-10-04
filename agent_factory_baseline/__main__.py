"""CLI entrypoint; use run.sh with the existing workflow_ai environment."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from dotenv import dotenv_values
from workshop.models import LLMParams

from .inputs import load_sources
from .runtime import PACKAGE, ReplayLLM, execute

ENV_FILE = PACKAGE / ".env"


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Паспорт проекта: цеха на workflow_ai, вход только .md")
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("plan", "run", "demo"):
        item = sub.add_parser(command, help={"plan": "Сохранить граф и входы без LLM",
                                             "run": "Запустить LLM-анализ",
                                             "demo": "Офлайн-сценарий на примере CRM"}[command])
        item.add_argument("--output", type=Path, help="Новая директория прогона (не должна существовать)")
        item.add_argument("--wiki-dir", type=Path, help="Корень предметной wiki; по умолчанию wiki/ этого baseline")
        if command != "demo":
            item.add_argument("--document", type=Path, action="append", required=True,
                              help="Документ заказчика .md, можно повторить")
            for role in ("team", "rules", "case"):
                item.add_argument(f"--{role}", type=Path, action="append", default=[])
            item.add_argument("--model", default=os.environ.get("BASELINE_MODEL"))
            item.add_argument("--verdict-model", help="Модель заключений и synthesis; по умолчанию --model")
            item.add_argument("--reasoning-effort", help="Уровень рассуждения для всех этапов; none отключает его у поддерживающего провайдера")
            item.add_argument("--max-tokens", type=int, default=8192)
            item.add_argument("--max-iterations", type=int, default=3)
            item.add_argument("--timeout", type=float, default=300.0)
    return root


def main(argv=None) -> int:
    for key, value in dotenv_values(ENV_FILE, interpolate=False).items():
        if key in {"OPENAI_API_KEY", "OPENAI_BASE_URL", "BASELINE_MODEL"} and value:
            os.environ.setdefault(key, value)
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if args.command == "run" and not args.model:
        command_parser.error("Для run укажите --model или BASELINE_MODEL")
    if args.command != "demo" and (args.max_tokens < 1 or args.max_iterations < 1 or args.timeout <= 0):
        command_parser.error("max-tokens, max-iterations и timeout должны быть положительными")
    if args.command == "run" and not os.environ.get("OPENAI_API_KEY", "").strip():
        command_parser.error("Для run задайте OPENAI_API_KEY в agent_factory_baseline/.env или окружении")
    output = args.output or PACKAGE / "runs" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    try:
        if args.command == "demo":
            sources = load_sources([("customer", PACKAGE / "examples/customer.md"),
                                    ("team", PACKAGE / "examples/team.md")])
            llm = ReplayLLM(json.loads((PACKAGE / "examples/replay.json").read_text(encoding="utf-8")))
            result = execute(sources, output, LLMParams(provider="openai", model="scripted-demo"),
                             llm, mode="replay", wiki_root=args.wiki_dir)
        else:
            entries = [("customer", path) for path in args.document]
            entries += [(role, path) for role in ("team", "rules", "case") for path in getattr(args, role)]
            sources = load_sources(entries)
            params = LLMParams(provider="openai", model=args.model or "not-configured",
                               max_tokens=args.max_tokens, temperature=0, timeout_s=args.timeout,
                               reasoning_effort=args.reasoning_effort)
            verdict_params = params.model_copy(update={"model": args.verdict_model}) if args.verdict_model else None
            llm = None
            if args.command == "run":
                from .transport import ObservedOpenAILLM
                llm = ObservedOpenAILLM(timeout_s=args.timeout)
            try:
                result = execute(sources, output, params, llm,
                                 mode="plan" if args.command == "plan" else "live",
                                 max_iterations=args.max_iterations, verdict_params=verdict_params,
                                 wiki_root=args.wiki_dir)
            finally:
                if llm is not None:
                    llm.close()
    except (OSError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"], "mode": result["mode"],
                      "output": str(output.resolve()), "error": result.get("error")}, ensure_ascii=False))
    return 0 if result["status"] in {"completed", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
