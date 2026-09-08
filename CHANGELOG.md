# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- All user-facing strings, task prompts (reasoning and coding suites), HTML dashboard,
  and CLI output translated from Turkish to English.
- `tasks/turkish.json` intentionally retained in Turkish (multilingual benchmark suite).
- `Dockerfile`: changed `pip install -e .` to non-editable install for production correctness;
  added `--no-cache-dir`; added non-root user `benchuser`.
- `docker-compose.yml`: added explicit `restart: "no"` and resource limits.
- CI: added `--no-cache-dir`, `ruff format --check`, coverage threshold (`--cov-fail-under=80`),
  artifact upload for coverage XML report.

### Added
- Per-task error handling in `runner.py`: a single failing task no longer aborts the entire run;
  it is recorded with `correct=False` and `score_detail` prefixed with `"error:"`.
- Logging via the standard `logging` module throughout all modules (`runner`, `providers`,
  `scoring`, `storage`, `tasks`, `cli`).
- `--verbose / -v` flag on the `llm-bench` CLI to enable debug-level logging.
- Atomic file writes in `storage.py` (write to temp file, then `os.replace`).
- Input validation and `re.error` handling in `scoring.py`.
- `FileNotFoundError` / `JSONDecodeError` handling and required-key validation in `tasks.py`.
- Configurable `timeout` and `max_tokens` for real API providers via `LLM_BENCH_TIMEOUT`
  and `LLM_BENCH_MAX_TOKENS` environment variables.
- `ANTHROPIC_API_VERSION` module constant in `providers.py`.
- Public API exports (`__all__`) in `src/llm_bench/__init__.py`.
- ARIA labels on dashboard `<canvas>` elements and leaderboard `<table>`.
- CDN failure guard in the dashboard HTML.
- `BUBBLE_COST_SCALE` named constant replacing the magic number in the bubble chart.
- `<meta name="description">` in dashboard `<head>`.
- `LICENSE` file (MIT).
- `CHANGELOG.md` (this file).
- `CONTRIBUTING.md` with development setup and contribution guidelines.
- `.pre-commit-config.yaml` for local code quality enforcement.
- `Makefile` with common development targets (`install`, `lint`, `fmt`, `test`, `demo`, `clean`).
- `pyproject.toml`: classifiers, keywords, project URLs, `[tool.ruff.lint]`,
  `[tool.coverage.run]`, `[tool.coverage.report]`.
- CLI integration tests in `tests/test_cli.py`.
- Error-handling tests in `test_runner.py`, `test_scoring.py`, `test_storage.py`, `test_tasks.py`.

## [0.1.0] - 2026-09-08

### Added
- Initial release: mock personas, OpenAI and Anthropic providers, task suites
  (reasoning, coding, turkish), rule-based scoring, cost estimation, static HTML dashboard.
