"""Task suite loading.

A task suite is a JSON file: a list of tasks, each with an ``id``,
``category``, ``prompt``, and a ``scorer`` spec consumed by ``scoring.py``.
See ``tasks/*.json`` for the bundled suites (reasoning, coding, turkish).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASKS_DIR = PROJECT_ROOT / "tasks"

_REQUIRED_TASK_KEYS = ("id", "category", "prompt", "scorer")


@dataclass
class Task:
    """A single benchmark task."""

    id: str
    category: str
    prompt: str
    scorer: dict


def load_suite(path: Path) -> list[Task]:
    """Load a single task suite JSON file and return its tasks.

    Args:
        path: Path to a ``.json`` file containing a list of task objects.

    Returns:
        List of :class:`Task` objects parsed from the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid JSON or a task is missing required keys.
    """
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Task suite file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in task suite {path}: {exc}") from exc

    tasks = []
    for i, t in enumerate(raw):
        for key in _REQUIRED_TASK_KEYS:
            if key not in t:
                raise ValueError(
                    f"Task at index {i} in {path} is missing required key {key!r}: {t!r}"
                )
        tasks.append(
            Task(id=t["id"], category=t["category"], prompt=t["prompt"], scorer=t["scorer"])
        )

    _validate_unique_ids(tasks)
    logger.debug("Loaded %d tasks from %s", len(tasks), path)
    return tasks


def load_suites(names: list[str], tasks_dir: Path | None = None) -> list[Task]:
    """Load one or more task suites by name and return a flat task list.

    Args:
        names: Suite file stems (e.g. ``["reasoning", "coding"]``) or
            ``["all"]`` to load every ``*.json`` file in *tasks_dir*.
        tasks_dir: Directory containing suite JSON files. Defaults to the
            project-level ``tasks/`` directory.

    Returns:
        Flat list of :class:`Task` objects with globally unique ids.

    Raises:
        FileNotFoundError: If any named suite file is missing.
        ValueError: If task ids are duplicated across suites.
    """
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
    """Raise ValueError if any task id appears more than once in *tasks*."""
    seen: set[str] = set()
    for t in tasks:
        if t.id in seen:
            raise ValueError(f"Duplicate task id across suites: {t.id!r}")
        seen.add(t.id)
