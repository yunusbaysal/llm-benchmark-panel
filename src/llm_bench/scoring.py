"""Rule-based scorers, plus an optional LLM-as-judge scorer for subjective
tasks a keyword/regex check can't grade fairly.

Every scorer takes the raw response text and a scorer spec (the task's
``scorer`` dict) and returns a ``ScoreResult``. Rule-based scorers are
deterministic and free to run in CI; the judge scorer costs an LLM call and
is opt-in (only invoked when a ``judge_fn`` is supplied to ``score``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ScoreResult:
    correct: bool
    detail: str


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split()).rstrip(".!?")


def score_exact_match(response: str, scorer: dict) -> ScoreResult:
    expected = _normalize(scorer["expected"])
    got = _normalize(response)
    return ScoreResult(correct=got == expected, detail=f"expected={expected!r} got={got!r}")


def score_keywords(response: str, scorer: dict) -> ScoreResult:
    text = response.lower()
    mode = scorer.get("mode", "all")  # "all" or "any"
    keywords = [k.lower() for k in scorer["keywords"]]
    hits = [k for k in keywords if k in text]
    correct = len(hits) == len(keywords) if mode == "all" else len(hits) > 0
    return ScoreResult(correct=correct, detail=f"mode={mode} matched={hits} of {keywords}")


def score_regex(response: str, scorer: dict) -> ScoreResult:
    pattern = scorer["pattern"]
    flags = re.IGNORECASE if scorer.get("ignore_case", True) else 0
    match = re.search(pattern, response, flags)
    return ScoreResult(correct=match is not None, detail=f"pattern={pattern!r} matched={bool(match)}")


_JUDGE_PROMPT = """You are grading a model's answer against a rubric. Reply with only \
"YES" or "NO" — YES if the answer satisfies the rubric, NO otherwise.

Rubric: {rubric}

Answer to grade:
{response}
"""


def score_llm_judge(response: str, scorer: dict, judge_fn) -> ScoreResult:
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


def score(response: str, scorer: dict, judge_fn=None) -> ScoreResult:
    scorer_type = scorer["type"]
    if scorer_type == "llm_judge":
        return score_llm_judge(response, scorer, judge_fn)
    if scorer_type not in _SCORERS:
        raise ValueError(f"Unknown scorer type: {scorer_type!r}")
    return _SCORERS[scorer_type](response, scorer)
