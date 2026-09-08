"""Integration tests for the llm-bench CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_bench.cli import main


def test_cli_run_mock_produces_results(tmp_path: Path):
    output = tmp_path / "results.json"
    main(
        [
            "run",
            "--models",
            "mock:frontier-sim,mock:budget-sim",
            "--suite",
            "reasoning",
            "--output",
            str(output),
        ]
    )
    assert output.exists()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert len(data["results"]) == 8  # 2 models × 4 tasks
    assert data["models"] == ["mock:frontier-sim", "mock:budget-sim"]
    assert data["suites"] == ["reasoning"]


def test_cli_report_produces_html(tmp_path: Path):
    results_path = tmp_path / "results.json"
    main(
        [
            "run",
            "--models",
            "mock:mid-sim",
            "--suite",
            "coding",
            "--output",
            str(results_path),
        ]
    )
    output_html = tmp_path / "out.html"
    main(["report", "--results", str(results_path), "--output", str(output_html)])
    assert output_html.exists()
    content = output_html.read_text(encoding="utf-8")
    assert "mock:mid-sim" in content
    assert "Leaderboard" in content
    assert 'lang="en"' in content


def test_cli_list_models_runs_without_error(capsys):
    main(["list-models"])
    out = capsys.readouterr().out
    assert "mock:" in out
    assert "frontier-sim" in out
    assert "no API key required" in out


def test_cli_run_invalid_model_exits_with_code_1():
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "run",
                "--models",
                "mock:does-not-exist",
                "--suite",
                "reasoning",
                "--output",
                "/tmp/irrelevant.json",
            ]
        )
    assert exc_info.value.code == 1


def test_cli_verbose_flag_is_accepted(tmp_path: Path):
    """--verbose should not raise; it enables debug logging."""
    output = tmp_path / "results.json"
    main(
        [
            "--verbose",
            "run",
            "--models",
            "mock:mid-sim",
            "--suite",
            "reasoning",
            "--output",
            str(output),
        ]
    )
    assert output.exists()
