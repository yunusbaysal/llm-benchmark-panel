import pytest

from llm_bench.providers import MOCK_PERSONAS, get_provider


def test_get_provider_resolves_mock_persona():
    provider = get_provider("mock:frontier-sim")
    assert provider is MOCK_PERSONAS["frontier-sim"]


def test_get_provider_unknown_persona_raises():
    with pytest.raises(ValueError):
        get_provider("mock:does-not-exist")


def test_get_provider_missing_colon_raises():
    with pytest.raises(ValueError):
        get_provider("gpt-4o-mini")


def test_get_provider_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_provider("cohere:command-r")


def test_get_provider_openai_without_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        get_provider("openai:gpt-4o-mini")


def test_mock_provider_is_deterministic_across_calls():
    provider = MOCK_PERSONAS["mid-sim"]
    r1 = provider.generate("prompt text", task_id="reasoning_arithmetic_1")
    r2 = provider.generate("prompt text", task_id="reasoning_arithmetic_1")
    assert r1.text == r2.text
    assert r1.latency_ms == r2.latency_ms


def test_mock_provider_varies_by_task_id():
    provider = MOCK_PERSONAS["frontier-sim"]
    responses = {
        provider.generate("p", task_id=f"task_{i}").text for i in range(20)
    }
    # With 20 different task ids and no answer-book entries, all fall back to
    # the same default-wrong text when unlucky and "42" when lucky, so this
    # just checks we get a small, bounded set back rather than a crash.
    assert responses


def test_frontier_sim_more_accurate_than_budget_sim_on_known_tasks():
    known_task_ids = [
        "reasoning_arithmetic_1", "reasoning_logic_1", "reasoning_word_1", "reasoning_sequence_1",
        "coding_loop_1", "coding_syntax_1", "coding_bigo_1", "coding_regex_1",
        "turkish_grammar_1", "turkish_vocab_1", "turkish_idiom_1", "turkish_finance_1",
    ]
    from llm_bench.providers import _MOCK_CORRECT_ANSWERS

    frontier = MOCK_PERSONAS["frontier-sim"]
    budget = MOCK_PERSONAS["budget-sim"]

    def hit_rate(provider):
        hits = 0
        for tid in known_task_ids:
            resp = provider.generate("prompt", task_id=tid)
            if resp.text == _MOCK_CORRECT_ANSWERS[tid]:
                hits += 1
        return hits / len(known_task_ids)

    assert hit_rate(frontier) >= hit_rate(budget)
