"""Illustrative per-token pricing used to estimate run cost.

These numbers are **placeholders for demo purposes** — provider pricing
changes over time and by tier. Before relying on cost figures for a real
decision, replace ``PRICING_USD_PER_1K`` with current numbers from each
provider's pricing page. Anything not in the table falls back to
``DEFAULT_PRICING``.
"""
from __future__ import annotations

PRICING_USD_PER_1K: dict[str, tuple[float, float]] = {
    # model_id -> (input $/1K tokens, output $/1K tokens)
    "openai:gpt-4o-mini": (0.00015, 0.0006),
    "openai:gpt-4o": (0.0025, 0.01),
    "anthropic:claude-3-5-haiku-latest": (0.0008, 0.004),
    "anthropic:claude-3-5-sonnet-latest": (0.003, 0.015),
    # simulated personas — priced to sit near the real tier they stand in for
    "mock:frontier-sim": (0.003, 0.015),
    "mock:mid-sim": (0.0006, 0.0024),
    "mock:budget-sim": (0.00015, 0.0006),
}

DEFAULT_PRICING = (0.001, 0.002)


def estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    input_rate, output_rate = PRICING_USD_PER_1K.get(model_id, DEFAULT_PRICING)
    return (input_tokens / 1000) * input_rate + (output_tokens / 1000) * output_rate
