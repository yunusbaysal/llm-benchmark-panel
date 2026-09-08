"""Persist and load benchmark run results as JSON."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .runner import TaskResult


def save_results(results: list[TaskResult], path: Path, models: list[str], suites: list[str]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
        "suites": suites,
        "results": [r.to_dict() for r in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_results(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
