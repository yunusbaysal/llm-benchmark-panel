from pathlib import Path

import pytest

from llm_bench.runner import run_benchmark
from llm_bench.storage import load_results, save_results
from llm_bench.tasks import load_suites


def test_save_and_load_results_roundtrip(tmp_path: Path):
    tasks = load_suites(["reasoning"])
    results = run_benchmark(["mock:mid-sim"], tasks)
    path = tmp_path / "run.json"

    save_results(results, path, models=["mock:mid-sim"], suites=["reasoning"])
    loaded = load_results(path)

    assert loaded["models"] == ["mock:mid-sim"]
    assert loaded["suites"] == ["reasoning"]
    assert len(loaded["results"]) == len(results)
    assert "generated_at" in loaded


def test_load_results_missing_file_raises(tmp_path: Path):
    with pytest.raises((FileNotFoundError, OSError)):
        load_results(tmp_path / "nonexistent.json")


def test_save_results_creates_nested_parent_directories(tmp_path: Path):
    tasks = load_suites(["reasoning"])
    results = run_benchmark(["mock:mid-sim"], tasks)
    deep_path = tmp_path / "a" / "b" / "c" / "run.json"
    save_results(results, deep_path, models=["mock:mid-sim"], suites=["reasoning"])
    assert deep_path.exists()
