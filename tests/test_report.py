import json
from pathlib import Path

from llm_bench.report import generate_dashboard_html, write_dashboard
from llm_bench.runner import run_benchmark
from llm_bench.storage import save_results
from llm_bench.tasks import load_suites


def _sample_data() -> dict:
    tasks = load_suites(["reasoning"])
    results = run_benchmark(["mock:frontier-sim", "mock:budget-sim"], tasks)
    return {
        "generated_at": "2025-01-01T00:00:00+00:00",
        "models": ["mock:frontier-sim", "mock:budget-sim"],
        "suites": ["reasoning"],
        "results": [r.to_dict() for r in results],
    }


def test_generate_dashboard_html_embeds_data_and_chartjs():
    html = generate_dashboard_html(_sample_data())
    assert "<canvas" in html
    assert "Chart.js" in html or "chart.umd" in html
    assert "mock:frontier-sim" in html
    assert "<!doctype html>" in html.lower()


def test_write_dashboard_creates_valid_file(tmp_path: Path):
    tasks = load_suites(["reasoning"])
    results = run_benchmark(["mock:mid-sim"], tasks)
    results_path = tmp_path / "results.json"
    save_results(results, results_path, models=["mock:mid-sim"], suites=["reasoning"])

    output_path = tmp_path / "dashboard.html"
    write_dashboard(results_path, output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "mock:mid-sim" in content


def test_dashboard_embedded_json_is_valid():
    html = generate_dashboard_html(_sample_data())
    start = html.index("const DATA = ") + len("const DATA = ")
    end = html.index(";\n", start)
    payload = json.loads(html[start:end])
    assert "results" in payload and "summaries" in payload
