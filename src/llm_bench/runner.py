"""Runs a set of models against a set of tasks and scores every response."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass

from .cost import estimate_cost_usd
from .providers import get_provider
from .scoring import score
from .tasks import Task

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    model_id: str
    task_id: str
    category: str
    prompt: str
    response_text: str
    correct: bool
    score_detail: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float

    def to_dict(self) -> dict:
        return asdict(self)


def run_benchmark(
    models: list[str],
    tasks: list[Task],
    judge_fn: Callable[[str], str] | None = None,
) -> list[TaskResult]:
    """Run every (model, task) combination and return a flat list of results.

    A single failing task does not abort the run — it is recorded with
    ``correct=False`` and a ``score_detail`` that starts with ``"error:"``.

    Args:
        models: List of model ids in ``"<provider>:<name>"`` format.
        tasks: List of :class:`Task` objects to evaluate against.
        judge_fn: Optional callable used for ``llm_judge``-scored tasks.
            Receives the judge prompt and returns the model's verdict string.

    Returns:
        One :class:`TaskResult` per (model, task) pair, in iteration order.
    """
    results: list[TaskResult] = []
    total = len(models) * len(tasks)
    logger.info(
        "Starting benchmark: %d model(s) × %d task(s) = %d combinations",
        len(models),
        len(tasks),
        total,
    )

    for model_id in models:
        provider = get_provider(model_id)
        for task in tasks:
            try:
                response = provider.generate(task.prompt, task_id=task.id)
                score_result = score(response.text, task.scorer, judge_fn=judge_fn)
                cost = estimate_cost_usd(model_id, response.input_tokens, response.output_tokens)
                results.append(
                    TaskResult(
                        model_id=model_id,
                        task_id=task.id,
                        category=task.category,
                        prompt=task.prompt,
                        response_text=response.text,
                        correct=score_result.correct,
                        score_detail=score_result.detail,
                        latency_ms=response.latency_ms,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        cost_usd=cost,
                    )
                )
                logger.debug(
                    "  %s / %s -> correct=%s latency=%.0fms",
                    model_id,
                    task.id,
                    score_result.correct,
                    response.latency_ms,
                )
            except Exception as exc:
                logger.warning("  %s / %s -> FAILED: %s", model_id, task.id, exc)
                results.append(
                    TaskResult(
                        model_id=model_id,
                        task_id=task.id,
                        category=task.category,
                        prompt=task.prompt,
                        response_text="",
                        correct=False,
                        score_detail=f"error: {exc}",
                        latency_ms=0.0,
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=0.0,
                    )
                )

    return results


@dataclass
class ModelSummary:
    model_id: str
    accuracy: float
    avg_latency_ms: float
    total_cost_usd: float
    num_tasks: int

    def to_dict(self) -> dict:
        return asdict(self)


def summarize(results: list[TaskResult]) -> list[ModelSummary]:
    """Aggregate per-task results into per-model summary statistics.

    Args:
        results: Flat list of :class:`TaskResult` objects (may span multiple models).

    Returns:
        One :class:`ModelSummary` per model, sorted by accuracy descending.
    """
    by_model: dict[str, list[TaskResult]] = {}
    for r in results:
        by_model.setdefault(r.model_id, []).append(r)

    summaries = []
    for model_id, rows in by_model.items():
        n = len(rows)
        summaries.append(
            ModelSummary(
                model_id=model_id,
                accuracy=sum(r.correct for r in rows) / n,
                avg_latency_ms=sum(r.latency_ms for r in rows) / n,
                total_cost_usd=sum(r.cost_usd for r in rows),
                num_tasks=n,
            )
        )
    summaries.sort(key=lambda s: s.accuracy, reverse=True)
    return summaries
