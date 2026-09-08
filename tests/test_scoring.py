from llm_bench.scoring import score, score_exact_match, score_keywords, score_regex


def test_exact_match_case_and_whitespace_insensitive():
    result = score_exact_match("  Mehmet  ", {"expected": "mehmet"})
    assert result.correct


def test_exact_match_strips_trailing_punctuation():
    result = score_exact_match("O(n).", {"expected": "O(n)"})
    assert result.correct


def test_exact_match_rejects_wrong_answer():
    result = score_exact_match("24", {"expected": "32"})
    assert not result.correct


def test_keywords_mode_all_requires_every_keyword():
    scorer = {"mode": "all", "keywords": ["for", "range", "fizz"]}
    assert score_keywords("for i in range(1,6): print('Fizz')", scorer).correct
    assert not score_keywords("for i in range(1,6): pass", scorer).correct


def test_keywords_mode_any_requires_one_keyword():
    scorer = {"mode": "any", "keywords": [":", "colon"]}
    assert score_keywords("eksik olan colon karakteri", scorer).correct
    assert not score_keywords("hiçbir şey", scorer).correct


def test_regex_scorer():
    scorer = {"pattern": "@"}
    assert score_regex("a@b.com", scorer).correct
    assert not score_regex("no at sign here", scorer).correct


def test_score_dispatches_by_type():
    assert score("102", {"type": "exact_match", "expected": "102"}).correct
    assert score("contains @", {"type": "regex", "pattern": "@"}).correct
    assert score("has fizz here", {"type": "keywords", "mode": "any", "keywords": ["fizz"]}).correct


def test_score_llm_judge_without_judge_fn_is_incorrect_not_crash():
    result = score("anything", {"type": "llm_judge", "rubric": "is it good?"})
    assert not result.correct


def test_score_llm_judge_uses_judge_fn():
    result = score(
        "some answer",
        {"type": "llm_judge", "rubric": "always say yes"},
        judge_fn=lambda prompt: "YES, satisfies rubric",
    )
    assert result.correct
