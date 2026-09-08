from llm_bench.runner import run_benchmark, summarize
from llm_bench.tasks import load_suites


def test_run_benchmark_produces_one_result_per_model_per_task():
    tasks = load_suites(["reasoning"])
    results = run_benchmark(["mock:frontier-sim", "mock:budget-sim"], tasks)
    assert len(results) == len(tasks) * 2


def test_run_benchmark_results_have_cost_and_latency():
    tasks = load_suites(["reasoning"])
    results = run_benchmark(["mock:mid-sim"], tasks)
    for r in results:
        assert r.latency_ms > 0
        assert r.cost_usd >= 0
        assert r.input_tokens > 0
        assert r.output_tokens > 0


def test_summarize_groups_by_model_and_sorts_by_accuracy():
    tasks = load_suites(["all"])
    results = run_benchmark(["mock:frontier-sim", "mock:budget-sim"], tasks)
    summaries = summarize(results)
    assert {s.model_id for s in summaries} == {"mock:frontier-sim", "mock:budget-sim"}
    assert summaries[0].accuracy >= summaries[1].accuracy
    for s in summaries:
        assert s.num_tasks == len(tasks)


def test_run_benchmark_tolerates_per_task_exception(monkeypatch):
    """A provider that raises on the first task should not abort the entire run."""
    from llm_bench.providers import MOCK_PERSONAS

    call_count = 0
    original_generate = MOCK_PERSONAS["mid-sim"].generate

    def flaky_generate(prompt, task_id=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated transient failure")
        return original_generate(prompt, task_id=task_id)

    monkeypatch.setattr(MOCK_PERSONAS["mid-sim"], "generate", flaky_generate)
    tasks = load_suites(["reasoning"])
    results = run_benchmark(["mock:mid-sim"], tasks)

    # All tasks still produce a result — the failed one has correct=False
    assert len(results) == len(tasks)
    failed = [r for r in results if r.score_detail.startswith("error:")]
    assert len(failed) == 1
    assert not failed[0].correct
    assert failed[0].latency_ms == 0.0
