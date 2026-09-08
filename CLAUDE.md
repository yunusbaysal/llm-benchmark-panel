# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install          # or: make install

# Run offline demo (no API keys needed)
llm-bench run --models mock:frontier-sim,mock:mid-sim,mock:budget-sim --suite all \
  --output data/results/demo_results.json
llm-bench report --results data/results/demo_results.json --output web/dashboard.html

# Run with real providers (requires OPENAI_API_KEY / ANTHROPIC_API_KEY in .env)
llm-bench run --models openai:gpt-4o-mini,anthropic:claude-3-5-haiku-latest --suite reasoning,coding

# List available models
llm-bench list-models

# Lint, format, test
make lint      # ruff check src tests
make fmt       # ruff format src tests
make test      # pytest --cov=llm_bench --cov-fail-under=80

# Run a single test file
pytest tests/test_scoring.py

# Regenerate committed demo artifacts (run after changing tasks or providers)
make demo      # python scripts/regenerate_demo.py
```

## Architecture

**Data flow:** Task JSON files → `tasks.py` loader → `runner.py` core loop → `providers.py` (one call per model×task) → `scoring.py` → `storage.py` (JSON, atomic write) → `report.py` (static HTML dashboard).

### Key modules (`src/llm_bench/`)

| Module | Role |
|---|---|
| `cli.py` | Entry point; `run`, `report`, `list-models` subcommands; `--verbose/-v` flag |
| `runner.py` | Iterates all (model, task) pairs; per-task `try/except` so one failure never aborts the run |
| `providers.py` | Registry dispatched by `"provider:name"` prefix; `MockProvider`, `OpenAIProvider`, `AnthropicProvider`; configurable via `LLM_BENCH_TIMEOUT` / `LLM_BENCH_MAX_TOKENS` env vars |
| `tasks.py` | Loads `tasks/*.json`, validates required keys, enforces globally unique task IDs |
| `scoring.py` | Pluggable scorers: `exact_match`, `keywords`, `regex` (catches `re.error`), `llm_judge` |
| `cost.py` | Illustrative $/1K-token pricing table; wired into `runner.py` |
| `storage.py` | Atomic serialize/deserialize `TaskResult[]` to/from JSON (`tempfile` + `os.replace`) |
| `report.py` | Generates `web/dashboard.html` with embedded data + Chart.js charts |
| `__init__.py` | Public API surface; defines `__all__` — all key symbols importable from `llm_bench` directly |

### Task suites (`tasks/*.json`)

Three suites: `reasoning`, `coding`, `turkish`. Each task specifies `id`, `category`, `prompt`, and a `scorer` dict (type + config). Task IDs must be globally unique across all suites.

**`tasks/turkish.json` must never be translated** — it is an intentional Turkish-language benchmark suite testing multilingual model capability. All other user-facing content is in English.

### Mock providers

`mock:frontier-sim`, `mock:mid-sim`, `mock:budget-sim` use a seeded RNG keyed on `(model_id, task_id)` so demo runs are fully deterministic without any API keys. After adding a new task suite, add its task ids to `_MOCK_CORRECT_ANSWERS` and `_MOCK_WRONG_ANSWERS` in `providers.py`, then run `make demo`.

### Environment variables (`.env`)

```
OPENAI_API_KEY=          # Required for openai:* models
ANTHROPIC_API_KEY=       # Required for anthropic:* models
JUDGE_MODEL=             # Model ID for llm_judge-scored tasks
LLM_BENCH_TIMEOUT=60     # HTTP timeout in seconds (real providers only)
LLM_BENCH_MAX_TOKENS=1024  # Max tokens per request (real providers only)
```

### Committed artifacts

`data/results/demo_results.json` and `web/dashboard.html` are intentionally committed. CI regenerates them to verify harness integrity. The dashboard is a self-contained static file — no server required.

### Error handling behaviour

- **runner.py**: A single task failure is caught, logged as `WARNING`, and recorded as `TaskResult(correct=False, score_detail="error: …", latency_ms=0.0, …)`. It never aborts the full run.
- **cli.py**: `ValueError`, `FileNotFoundError`, `OSError` from any subcommand print `"Error: …"` to stderr and exit with code 1 instead of showing a traceback.
- **scoring.py**: An invalid regex pattern returns `ScoreResult(correct=False)` instead of raising `re.error`.
- **storage.py**: Writes are atomic — partial writes cannot corrupt an existing results file.

### Key constants

- `providers.ANTHROPIC_API_VERSION` — Anthropic Messages API version string; update here when Anthropic releases a new version.
