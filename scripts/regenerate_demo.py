#!/usr/bin/env python3
"""Regenerates data/results/demo_results.json and web/dashboard.html by
actually running the mock:* personas through the real harness. Run this
after changing a task suite, a mock persona, or the report template, so the
committed demo data stays honest (a real run's output, not hand-edited)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_bench.report import write_dashboard  # noqa: E402
from llm_bench.runner import run_benchmark, summarize  # noqa: E402
from llm_bench.storage import save_results  # noqa: E402
from llm_bench.tasks import load_suites  # noqa: E402

MODELS = ["mock:frontier-sim", "mock:mid-sim", "mock:budget-sim"]
RESULTS_PATH = ROOT / "data" / "results" / "demo_results.json"
DASHBOARD_PATH = ROOT / "web" / "dashboard.html"


def main() -> None:
    tasks = load_suites(["all"])
    results = run_benchmark(MODELS, tasks)
    save_results(results, RESULTS_PATH, models=MODELS, suites=["all"])
    write_dashboard(RESULTS_PATH, DASHBOARD_PATH)

    print(f"{len(results)} results -> {RESULTS_PATH}")
    print(f"dashboard -> {DASHBOARD_PATH}\n")
    for s in summarize(results):
        print(f"  {s.model_id:<20} acc={s.accuracy:6.1%}  latency={s.avg_latency_ms:7.1f}ms  "
              f"cost=${s.total_cost_usd:.4f}")


if __name__ == "__main__":
    main()
