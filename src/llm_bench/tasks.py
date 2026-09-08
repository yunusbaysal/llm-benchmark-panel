"""Task suite loading.

A task suite is a JSON file: a list of tasks, each with an ``id``,
``category``, ``prompt``, and a ``scorer`` spec consumed by ``scoring.py``.
See ``tasks/*.json`` for the bundled suites (reasoning, coding, turkish).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASKS_DIR = PROJECT_ROOT / "tasks"


@dataclass
class Task:
    id: str
    category: str
    prompt: str
    scorer: dict


def load_suite(path: Path) -> list[Task]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    tasks = [Task(id=t["id"], category=t["category"], prompt=t["prompt"], scorer=t["scorer"]) for t in raw]
    _validate_unique_ids(tasks)
    return tasks


def load_suites(names: list[str], tasks_dir: Path | None = None) -> list[Task]:
    """``names`` are suite file stems (e.g. "reasoning") or "all" to load every
    ``*.json`` file in the tasks directory."""
    tasks_dir = tasks_dir or DEFAULT_TASKS_DIR
    if names == ["all"]:
        paths = sorted(tasks_dir.glob("*.json"))
    else:
        paths = [tasks_dir / f"{name}.json" for name in names]
        missing = [p for p in paths if not p.exists()]
        if missing:
            raise FileNotFoundError(f"Task suite file(s) not found: {missing}")

    all_tasks: list[Task] = []
    for path in paths:
        all_tasks.extend(load_suite(path))
    _validate_unique_ids(all_tasks)
    return all_tasks


def _validate_unique_ids(tasks: list[Task]) -> None:
    seen = set()
    for t in tasks:
        if t.id in seen:
            raise ValueError(f"Duplicate task id across suites: {t.id!r}")
        seen.add(t.id)
