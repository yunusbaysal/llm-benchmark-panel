from llm_bench.cost import estimate_cost_usd


def test_known_model_uses_its_table_rate():
    cost = estimate_cost_usd("openai:gpt-4o-mini", input_tokens=1000, output_tokens=1000)
    assert round(cost, 6) == round(0.00015 + 0.0006, 6)


def test_unknown_model_falls_back_to_default_pricing():
    cost = estimate_cost_usd("someprovider:unknown-model", input_tokens=1000, output_tokens=1000)
    assert cost == 0.001 + 0.002


def test_zero_tokens_costs_nothing():
    assert estimate_cost_usd("openai:gpt-4o", input_tokens=0, output_tokens=0) == 0.0
