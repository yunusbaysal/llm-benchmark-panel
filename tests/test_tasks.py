from pathlib import Path

import pytest

from llm_bench.tasks import DEFAULT_TASKS_DIR, load_suite, load_suites


def test_load_suite_reasoning():
    tasks = load_suite(DEFAULT_TASKS_DIR / "reasoning.json")
    assert len(tasks) == 4
    assert all(t.category == "reasoning" for t in tasks)


def test_load_suites_all_has_unique_ids():
    tasks = load_suites(["all"])
    ids = [t.id for t in tasks]
    assert len(ids) == len(set(ids))
    assert len(tasks) >= 10


def test_load_suites_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_suites(["does_not_exist"])


def test_load_suite_from_temp_file_validates_duplicates(tmp_path: Path):
    path = tmp_path / "dupes.json"
    path.write_text(
        '[{"id":"a","category":"x","prompt":"p","scorer":{"type":"exact_match","expected":"1"}},'
        '{"id":"a","category":"x","prompt":"p2","scorer":{"type":"exact_match","expected":"2"}}]',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_suite(path)
