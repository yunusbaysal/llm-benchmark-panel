"""Pluggable model providers.

Model ids are ``"<provider>:<name>"`` (e.g. ``"openai:gpt-4o-mini"``,
``"mock:frontier-sim"``). ``get_provider`` is the registry lookup the rest of
the harness goes through — real API providers need a key, ``mock:*``
personas never do, which is what makes the bundled demo dashboard runnable
with zero configuration.
"""

from __future__ import annotations

import hashlib
import logging
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Current Anthropic Messages API version — check https://docs.anthropic.com/en/api/versioning
ANTHROPIC_API_VERSION = "2023-06-01"


@dataclass
class ProviderResponse:
    text: str
    latency_ms: float
    input_tokens: int
    output_tokens: int


class Provider(ABC):
    @abstractmethod
    def generate(self, prompt: str, task_id: str | None = None) -> ProviderResponse: ...


def _approx_tokens(text: str) -> int:
    # Whitespace-based approximation, not a real tokenizer — fine for the
    # illustrative cost estimate this feeds into.
    return max(1, len(text.split()))


# --- deterministic mock provider ------------------------------------------------

# Correct completions per task id: crafted so each one satisfies that task's
# scorer (see tasks/*.json). This is what a "skilled" persona returns.
_MOCK_CORRECT_ANSWERS: dict[str, str] = {
    "reasoning_arithmetic_1": "102",
    "reasoning_logic_1": "Mehmet",
    "reasoning_word_1": "patik",
    "reasoning_sequence_1": "32",
    "coding_loop_1": "for i in range(1, 6):\n    print('Fizz' if i % 3 == 0 else i)",
    "coding_syntax_1": "The colon (:) is missing at the end of the function definition.",
    "coding_bigo_1": "O(n)",
    "coding_regex_1": r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$",
    "turkish_grammar_1": "gittim",
    "turkish_vocab_1": "inflation",
    "turkish_idiom_1": "Bir şey gerçekleşmeden önce, henüz olmadan tedbir almak anlamına gelir.",
    "turkish_finance_1": "BIST100, Borsa İstanbul'da işlem gören en büyük 100 şirketin performansını izleyen endekstir.",
}

# Plausible-but-wrong completions: guaranteed not to satisfy the scorer,
# because a persona that misses a question should genuinely fail it, not
# accidentally pass on unrelated keyword overlap.
_MOCK_WRONG_ANSWERS: dict[str, str] = {
    "reasoning_arithmetic_1": "Around 90 or so, I'm not entirely sure.",
    "reasoning_logic_1": "Ali",
    "reasoning_word_1": "tapik",
    "reasoning_sequence_1": "24",
    "coding_loop_1": "print(list(range(1, 6)))",
    "coding_syntax_1": "There might be a variable naming issue.",
    "coding_bigo_1": "O(log n)",
    "coding_regex_1": "[A-Za-z]+",
    "turkish_grammar_1": "gidiyorum",
    "turkish_vocab_1": "recession",
    "turkish_idiom_1": "Bir işi çok dikkatli ve özenli yapmak anlamına gelir.",
    "turkish_finance_1": "Bir şirketin hisse başına kârını gösteren bir tablodur.",
}

_DEFAULT_WRONG = "I cannot answer this question right now."


class MockProvider(Provider):
    """A deterministic, network-free simulated model.

    ``skill`` is the probability (per task, seeded by model name + task id so
    re-runs are reproducible) that this persona answers correctly. Exists so
    the whole harness — runner, scoring, cost estimation, dashboard — is
    demonstrable with `llm-bench run --models mock:frontier-sim,...` and no
    API keys, and so ``data/results/demo_results.json`` can be committed and
    regenerated deterministically.
    """

    def __init__(self, name: str, skill: float, base_latency_ms: float, jitter_ms: float = 120):
        self.name = name
        self.skill = skill
        self.base_latency_ms = base_latency_ms
        self.jitter_ms = jitter_ms

    def _rng_for(self, task_id: str) -> random.Random:
        seed_material = f"{self.name}:{task_id}".encode()
        seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
        return random.Random(seed)

    def generate(self, prompt: str, task_id: str | None = None) -> ProviderResponse:
        task_id = task_id or "unknown"
        rng = self._rng_for(task_id)

        is_correct = rng.random() < self.skill
        text = (
            _MOCK_CORRECT_ANSWERS.get(task_id, "42")
            if is_correct
            else _MOCK_WRONG_ANSWERS.get(task_id, _DEFAULT_WRONG)
        )

        latency = max(20.0, self.base_latency_ms + rng.uniform(-self.jitter_ms, self.jitter_ms))
        return ProviderResponse(
            text=text,
            latency_ms=latency,
            input_tokens=_approx_tokens(prompt),
            output_tokens=_approx_tokens(text),
        )


MOCK_PERSONAS: dict[str, MockProvider] = {
    "frontier-sim": MockProvider("frontier-sim", skill=0.92, base_latency_ms=950),
    "mid-sim": MockProvider("mid-sim", skill=0.75, base_latency_ms=480),
    "budget-sim": MockProvider("budget-sim", skill=0.55, base_latency_ms=190),
}


# --- real API providers -----------------------------------------------------


class OpenAIProvider(Provider):
    """Provider for OpenAI chat-completion models.

    Requires ``OPENAI_API_KEY`` to be set in the environment (or ``.env``).
    Temperature is fixed at 0 for reproducible benchmark results.
    """

    def __init__(self, model: str, api_key: str, timeout: float = 60.0, max_tokens: int = 1024):
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens

    def generate(self, prompt: str, task_id: str | None = None) -> ProviderResponse:
        import time

        import httpx

        logger.debug("OpenAI request: model=%s task_id=%s", self.model, task_id)
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": self.max_tokens,
                },
            )
        latency_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ProviderResponse(
            text=text,
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens", _approx_tokens(prompt)),
            output_tokens=usage.get("completion_tokens", _approx_tokens(text)),
        )


class AnthropicProvider(Provider):
    """Provider for Anthropic Claude models via the Messages API.

    Requires ``ANTHROPIC_API_KEY`` to be set in the environment (or ``.env``).
    Temperature is fixed at 0 for reproducible benchmark results.
    """

    def __init__(self, model: str, api_key: str, timeout: float = 60.0, max_tokens: int = 1024):
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens

    def generate(self, prompt: str, task_id: str | None = None) -> ProviderResponse:
        import time

        import httpx

        logger.debug("Anthropic request: model=%s task_id=%s", self.model, task_id)
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": ANTHROPIC_API_VERSION},
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        latency_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        data = resp.json()
        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        return ProviderResponse(
            text=text,
            latency_ms=latency_ms,
            input_tokens=usage.get("input_tokens", _approx_tokens(prompt)),
            output_tokens=usage.get("output_tokens", _approx_tokens(text)),
        )


def get_provider(model_id: str) -> Provider:
    """Resolve a ``"<provider>:<name>"`` model id to a :class:`Provider` instance.

    Supported prefixes:
    - ``mock:<persona>`` — deterministic simulation, no API key required.
    - ``openai:<model>`` — OpenAI chat completions; requires ``OPENAI_API_KEY``.
    - ``anthropic:<model>`` — Anthropic Messages API; requires ``ANTHROPIC_API_KEY``.

    Timeout and max-tokens for real providers are read from environment variables
    ``LLM_BENCH_TIMEOUT`` (seconds, default 60) and ``LLM_BENCH_MAX_TOKENS`` (default 1024).

    Raises:
        ValueError: If the model id format is invalid or the provider/persona is unknown.
    """
    if ":" not in model_id:
        raise ValueError(f"model id must be '<provider>:<name>', got {model_id!r}")
    provider_name, name = model_id.split(":", 1)

    logger.debug("Resolving provider for %r", model_id)

    if provider_name == "mock":
        if name not in MOCK_PERSONAS:
            raise ValueError(f"Unknown mock persona {name!r}. Options: {list(MOCK_PERSONAS)}")
        return MOCK_PERSONAS[name]

    timeout = float(os.getenv("LLM_BENCH_TIMEOUT", "60"))
    max_tokens = int(os.getenv("LLM_BENCH_MAX_TOKENS", "1024"))

    if provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("openai:* models require OPENAI_API_KEY to be set")
        return OpenAIProvider(model=name, api_key=api_key, timeout=timeout, max_tokens=max_tokens)

    if provider_name == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("anthropic:* models require ANTHROPIC_API_KEY to be set")
        return AnthropicProvider(
            model=name, api_key=api_key, timeout=timeout, max_tokens=max_tokens
        )

    raise ValueError(f"Unknown provider {provider_name!r} (expected mock/openai/anthropic)")
