"""Persist and load benchmark run results as JSON."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .runner import TaskResult

logger = logging.getLogger(__name__)


def save_results(
    results: list[TaskResult], path: Path, models: list[str], suites: list[str]
) -> None:
    """Serialise a benchmark run to JSON using an atomic write.

    The write is atomic: data is written to a sibling temp file first, then
    renamed over the target path so a partial write never corrupts an existing
    file.

    Args:
        results: List of :class:`~llm_bench.runner.TaskResult` objects to persist.
        path: Destination file path. Parent directories are created if absent.
        models: Model ids that were benchmarked (stored in metadata).
        suites: Suite names that were run (stored in metadata).

    Raises:
        OSError: If the file cannot be written (e.g. permission denied).
    """
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "models": models,
        "suites": suites,
        "results": [r.to_dict() for r in results],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp_path = tmp.name
            json.dump(payload, tmp, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
        logger.debug("Results saved to %s (%d entries)", path, len(results))
    except OSError as exc:
        logger.error("Failed to write results to %s: %s", path, exc)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def load_results(path: Path) -> dict:
    """Load a previously saved benchmark run from JSON.

    Args:
        path: Path to the JSON results file.

    Returns:
        The parsed results dict (keys: ``generated_at``, ``models``,
        ``suites``, ``results``).

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If the file cannot be read.
    """
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        logger.error("Failed to read results from %s: %s", path, exc)
        raise
