"""llm_bench: multi-provider LLM benchmarking harness."""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "run_benchmark",
    "summarize",
    "TaskResult",
    "ModelSummary",
    "load_suites",
    "score",
    "get_provider",
    "save_results",
    "load_results",
    "generate_dashboard_html",
    "write_dashboard",
    "estimate_cost_usd",
]

from .cost import estimate_cost_usd
from .providers import get_provider
from .report import generate_dashboard_html, write_dashboard
from .runner import ModelSummary, TaskResult, run_benchmark, summarize
from .scoring import score
from .storage import load_results, save_results
from .tasks import load_suites
