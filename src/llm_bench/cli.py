"""Command-line interface: run, report, list-models.

    python -m llm_bench.cli run --models mock:frontier-sim,mock:mid-sim,mock:budget-sim --suite all
    python -m llm_bench.cli report --results data/results/demo_results.json --output web/dashboard.html
    python -m llm_bench.cli list-models
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .providers import MOCK_PERSONAS, get_provider
from .report import write_dashboard
from .runner import run_benchmark, summarize
from .storage import save_results
from .tasks import DEFAULT_TASKS_DIR, load_suites

load_dotenv()


def _judge_fn(judge_model: str | None):
    if not judge_model:
        return None
    provider = get_provider(judge_model)

    def _fn(prompt: str) -> str:
        return provider.generate(prompt).text

    return _fn


def cmd_run(args: argparse.Namespace) -> None:
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    suites = [s.strip() for s in args.suite.split(",") if s.strip()]
    tasks = load_suites(suites, tasks_dir=Path(args.tasks_dir))

    judge_model = args.judge_model or os.getenv("JUDGE_MODEL") or None
    results = run_benchmark(models, tasks, judge_fn=_judge_fn(judge_model))

    output = Path(args.output)
    save_results(results, output, models=models, suites=suites)

    print(f"{len(results)} sonuç kaydedildi -> {output}\n")
    for s in summarize(results):
        print(f"  {s.model_id:<24} doğruluk={s.accuracy:6.1%}  gecikme={s.avg_latency_ms:7.1f}ms  "
              f"maliyet=${s.total_cost_usd:.4f}  (n={s.num_tasks})")


def cmd_report(args: argparse.Namespace) -> None:
    write_dashboard(Path(args.results), Path(args.output))
    print(f"Dashboard yazıldı -> {args.output}")


def cmd_list_models(_: argparse.Namespace) -> None:
    print("mock:* (API anahtarı gerekmez):")
    for name, persona in MOCK_PERSONAS.items():
        print(f"  mock:{name:<14} skill~{persona.skill:.2f}  base_latency~{persona.base_latency_ms:.0f}ms")
    print("\nopenai:<model>      (OPENAI_API_KEY gerekir, örn. openai:gpt-4o-mini)")
    print("anthropic:<model>   (ANTHROPIC_API_KEY gerekir, örn. anthropic:claude-3-5-haiku-latest)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="llm-bench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a benchmark and save results as JSON")
    run_parser.add_argument("--models", required=True, help="Comma-separated model ids, e.g. mock:frontier-sim,mock:mid-sim")
    run_parser.add_argument("--suite", default="all", help="Comma-separated suite names or 'all' (default)")
    run_parser.add_argument("--tasks-dir", default=str(DEFAULT_TASKS_DIR))
    run_parser.add_argument("--output", default="data/results/latest.json")
    run_parser.add_argument("--judge-model", default=None, help="Model id used for llm_judge-scored tasks")
    run_parser.set_defaults(func=cmd_run)

    report_parser = subparsers.add_parser("report", help="Render a results JSON file as a static HTML dashboard")
    report_parser.add_argument("--results", default="data/results/demo_results.json")
    report_parser.add_argument("--output", default="web/dashboard.html")
    report_parser.set_defaults(func=cmd_report)

    list_parser = subparsers.add_parser("list-models", help="List available model ids")
    list_parser.set_defaults(func=cmd_list_models)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
