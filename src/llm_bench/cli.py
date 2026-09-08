"""Command-line interface: run, report, list-models.

python -m llm_bench.cli run --models mock:frontier-sim,mock:mid-sim,mock:budget-sim --suite all
python -m llm_bench.cli report --results data/results/demo_results.json --output web/dashboard.html
python -m llm_bench.cli list-models
"""

from __future__ import annotations

import argparse
import logging
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
    """Return a callable that queries *judge_model* for LLM-as-judge scoring.

    Returns ``None`` when no judge model is configured, which causes
    ``llm_judge``-scored tasks to be marked incorrect rather than crashing.
    """
    if not judge_model:
        return None
    provider = get_provider(judge_model)

    def _fn(prompt: str) -> str:
        return provider.generate(prompt).text

    return _fn


def cmd_run(args: argparse.Namespace) -> None:
    """Execute a benchmark run and write results to a JSON file."""
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    suites = [s.strip() for s in args.suite.split(",") if s.strip()]
    tasks = load_suites(suites, tasks_dir=Path(args.tasks_dir))

    judge_model = args.judge_model or os.getenv("JUDGE_MODEL") or None
    results = run_benchmark(models, tasks, judge_fn=_judge_fn(judge_model))

    output = Path(args.output)
    save_results(results, output, models=models, suites=suites)

    print(f"{len(results)} results saved -> {output}\n")
    for s in summarize(results):
        print(
            f"  {s.model_id:<24} accuracy={s.accuracy:6.1%}  latency={s.avg_latency_ms:7.1f}ms  "
            f"cost=${s.total_cost_usd:.4f}  (n={s.num_tasks})"
        )


def cmd_report(args: argparse.Namespace) -> None:
    """Render a results JSON file as a static HTML dashboard."""
    write_dashboard(Path(args.results), Path(args.output))
    print(f"Dashboard written -> {args.output}")


def cmd_list_models(_: argparse.Namespace) -> None:
    """Print all available model ids and their configuration requirements."""
    print("mock:* (no API key required):")
    for name, persona in MOCK_PERSONAS.items():
        print(
            f"  mock:{name:<14} skill~{persona.skill:.2f}  base_latency~{persona.base_latency_ms:.0f}ms"
        )
    print("\nopenai:<model>      (requires OPENAI_API_KEY, e.g. openai:gpt-4o-mini)")
    print(
        "anthropic:<model>   (requires ANTHROPIC_API_KEY, e.g. anthropic:claude-3-5-haiku-latest)"
    )


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``llm-bench`` CLI."""
    parser = argparse.ArgumentParser(prog="llm-bench")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging (per-task results, provider calls)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a benchmark and save results as JSON")
    run_parser.add_argument(
        "--models",
        required=True,
        help="Comma-separated model ids, e.g. mock:frontier-sim,mock:mid-sim",
    )
    run_parser.add_argument(
        "--suite", default="all", help="Comma-separated suite names or 'all' (default)"
    )
    run_parser.add_argument("--tasks-dir", default=str(DEFAULT_TASKS_DIR))
    run_parser.add_argument("--output", default="data/results/latest.json")
    run_parser.add_argument(
        "--judge-model", default=None, help="Model id used for llm_judge-scored tasks"
    )
    run_parser.set_defaults(func=cmd_run)

    report_parser = subparsers.add_parser(
        "report", help="Render a results JSON file as a static HTML dashboard"
    )
    report_parser.add_argument("--results", default="data/results/demo_results.json")
    report_parser.add_argument("--output", default="web/dashboard.html")
    report_parser.set_defaults(func=cmd_report)

    list_parser = subparsers.add_parser("list-models", help="List available model ids")
    list_parser.set_defaults(func=cmd_list_models)

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        args.func(args)
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
