# Contributing to LLM Benchmark Panel

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

## Running Tests

```bash
pytest --cov=llm_bench           # full suite with coverage
pytest tests/test_scoring.py     # single file
pytest -v                        # verbose output
```

All tests run against `mock:*` providers — no API keys required.

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
make lint   # ruff check src tests
make fmt    # ruff format src tests
```

Pre-commit hooks run both automatically on every `git commit` after `make install`.

## Adding a Task Suite

1. Create `tasks/<name>.json` — a JSON array of task objects:
   ```json
   [
     {
       "id": "my_suite_task_1",
       "category": "my_suite",
       "prompt": "Your prompt here.",
       "scorer": { "type": "exact_match", "expected": "expected answer" }
     }
   ]
   ```
2. Task `id` values must be globally unique across all suite files.
3. Add corresponding entries to `_MOCK_CORRECT_ANSWERS` and `_MOCK_WRONG_ANSWERS`
   in `src/llm_bench/providers.py` so mock personas produce meaningful scores.
4. Run `make demo` to update `data/results/demo_results.json` and `web/dashboard.html`.
5. Add tests covering the new suite's loading and scoring.

## Scorer Types

| Type          | Required keys             | Description                                      |
|---------------|---------------------------|--------------------------------------------------|
| `exact_match` | `expected`                | Normalised string equality                       |
| `keywords`    | `keywords`, `mode`        | All/any keywords present (case-insensitive)      |
| `regex`       | `pattern`                 | `re.search` match (case-insensitive by default)  |
| `llm_judge`   | `rubric`                  | LLM grades the response; requires `--judge-model`|

## Updating Mock Personas

The `MockProvider` is seeded by `hash(persona_name, task_id)` for reproducibility.
After adding new tasks, verify that the overall accuracy ranking remains sensible
(`frontier-sim` > `mid-sim` > `budget-sim`) before committing.

## Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/) prefixes:
`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`.
