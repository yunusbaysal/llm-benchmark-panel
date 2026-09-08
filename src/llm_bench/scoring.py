"""Rule-based scorers, plus an optional LLM-as-judge scorer for subjective
tasks a keyword/regex check can't grade fairly.

Every scorer takes the raw response text and a scorer spec (the task's
``scorer`` dict) and returns a ``ScoreResult``. Rule-based scorers are
deterministic and free to run in CI; the judge scorer costs an LLM call and
is opt-in (only invoked when a ``judge_fn`` is supplied to ``score``).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScoreResult:
    """Result of scoring a single model response against a task's scorer spec."""

    correct: bool
    detail: str


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split()).rstrip(".!?")


def score_exact_match(response: str, scorer: dict) -> ScoreResult:
    """Return correct if the normalised response exactly equals the expected string.

    Args:
        response: Raw model response text.
        scorer: Scorer spec dict; must contain ``"expected"`` key.

    Raises:
        KeyError: If ``"expected"`` is absent from the scorer spec.
    """
    if "expected" not in scorer:
        raise KeyError(f"exact_match scorer is missing required key 'expected': {scorer!r}")
    expected = _normalize(scorer["expected"])
    got = _normalize(response)
    return ScoreResult(correct=got == expected, detail=f"expected={expected!r} got={got!r}")


def score_keywords(response: str, scorer: dict) -> ScoreResult:
    """Return correct if the response contains the required keywords.

    Args:
        response: Raw model response text.
        scorer: Scorer spec dict; must contain ``"keywords"`` key (list of strings).
            Optional ``"mode"`` key (``"all"`` or ``"any"``; default ``"all"``).

    Raises:
        KeyError: If ``"keywords"`` is absent from the scorer spec.
    """
    if "keywords" not in scorer:
        raise KeyError(f"keywords scorer is missing required key 'keywords': {scorer!r}")
    text = response.lower()
    mode = scorer.get("mode", "all")  # "all" or "any"
    keywords = [k.lower() for k in scorer["keywords"]]
    hits = [k for k in keywords if k in text]
    correct = len(hits) == len(keywords) if mode == "all" else len(hits) > 0
    return ScoreResult(correct=correct, detail=f"mode={mode} matched={hits} of {keywords}")


def score_regex(response: str, scorer: dict) -> ScoreResult:
    """Return correct if the response matches the given regular expression.

    Args:
        response: Raw model response text.
        scorer: Scorer spec dict; must contain ``"pattern"`` key (regex string).
            Optional ``"ignore_case"`` key (bool; default ``True``).

    Returns:
        A :class:`ScoreResult` with ``correct=False`` and a descriptive detail
        if the pattern is an invalid regex — it never raises ``re.error``.
    """
    pattern = scorer["pattern"]
    flags = re.IGNORECASE if scorer.get("ignore_case", True) else 0
    try:
        match = re.search(pattern, response, flags)
    except re.error as exc:
        logger.warning("Invalid regex pattern %r: %s", pattern, exc)
        return ScoreResult(correct=False, detail=f"invalid regex pattern {pattern!r}: {exc}")
    return ScoreResult(
        correct=match is not None, detail=f"pattern={pattern!r} matched={bool(match)}"
    )


_JUDGE_PROMPT = """You are grading a model's answer against a rubric. Reply with only \
"YES" or "NO" — YES if the answer satisfies the rubric, NO otherwise.

Rubric: {rubric}

Answer to grade:
{response}
"""


def score_llm_judge(
    response: str,
    scorer: dict,
    judge_fn: Callable[[str], str] | None,
) -> ScoreResult:
    """Grade a response using an LLM judge.

    Args:
        response: Raw model response text.
        scorer: Scorer spec dict; must contain ``"rubric"`` key.
        judge_fn: Callable that sends a prompt to the judge model and returns
            its text response. If ``None``, the task is marked incorrect.
    """
    if judge_fn is None:
        return ScoreResult(correct=False, detail="no judge_fn configured; treated as incorrect")
    prompt = _JUDGE_PROMPT.format(rubric=scorer["rubric"], response=response)
    verdict = judge_fn(prompt).strip().upper()
    return ScoreResult(correct=verdict.startswith("YES"), detail=f"judge verdict={verdict!r}")


_SCORERS = {
    "exact_match": score_exact_match,
    "keywords": score_keywords,
    "regex": score_regex,
}


def score(
    response: str,
    scorer: dict,
    judge_fn: Callable[[str], str] | None = None,
) -> ScoreResult:
    """Dispatch to the appropriate scorer based on ``scorer["type"]``.

    Args:
        response: Raw model response text.
        scorer: Scorer spec dict with at minimum a ``"type"`` key.
        judge_fn: Required only for ``llm_judge`` scorer type.

    Raises:
        ValueError: If ``scorer["type"]`` is not a known scorer type.
    """
    scorer_type = scorer["type"]
    if scorer_type == "llm_judge":
        return score_llm_judge(response, scorer, judge_fn)
    if scorer_type not in _SCORERS:
        raise ValueError(f"Unknown scorer type: {scorer_type!r}")
    return _SCORERS[scorer_type](response, scorer)
