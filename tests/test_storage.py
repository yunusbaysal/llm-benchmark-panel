from pathlib import Path

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
