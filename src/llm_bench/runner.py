"""Runs a set of models against a set of tasks and scores every response."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .cost import estimate_cost_usd
from .providers import get_provider
from .scoring import score
from .tasks import Task


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


def run_benchmark(models: list[str], tasks: list[Task], judge_fn=None) -> list[TaskResult]:
    results: list[TaskResult] = []
    for model_id in models:
        provider = get_provider(model_id)
        for task in tasks:
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
