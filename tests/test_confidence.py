"""
The confidence gate and the score-gap log.

The gate is the part of this module a routing layer actually acts on: "confident" means
load the skill, "ambiguous" means ask the operator which one, "insufficient" means say
that nothing matched rather than guessing. The boundary cases are where a routing bug
would live, so they are tested at the threshold, one step above it, and one step below.
"""

import json

from conftest import sr


def _matches(*scores):
    """Result lists are the gate's only input, so build them directly rather than via search()."""
    return [
        sr.CapabilityMatch(
            id=f"cap-{i}",
            name=f"Capability {i}",
            type="skill",
            description="",
            relevance_score=score,
            load_cost_tokens=100,
            location="",
            dependencies=[],
        )
        for i, score in enumerate(scores)
    ]


# ── assess_confidence: the three states ──────────────────────────────────────


def test_no_results_is_insufficient():
    assert sr.assess_confidence([]) == "insufficient"


def test_a_top_score_below_the_ambiguous_floor_is_insufficient():
    below = round(sr.AMBIGUOUS_MIN_SCORE - 0.01, 3)
    assert sr.assess_confidence(_matches(below)) == "insufficient"


def test_a_top_score_exactly_at_the_ambiguous_floor_is_not_insufficient():
    """The floor is inclusive. A result sitting exactly on it still routes."""
    assert sr.assess_confidence(_matches(sr.AMBIGUOUS_MIN_SCORE)) != "insufficient"


def test_a_lone_result_clearing_the_score_threshold_is_confident():
    assert sr.assess_confidence(_matches(sr.CONFIDENCE_SCORE_THRESHOLD)) == "confident"


def test_a_lone_result_below_the_score_threshold_is_ambiguous():
    below = round(sr.CONFIDENCE_SCORE_THRESHOLD - 0.01, 3)
    assert sr.assess_confidence(_matches(below)) == "ambiguous"


def test_a_narrow_gap_is_ambiguous_however_high_the_top_score():
    """Two strong candidates a hair apart is the case a human has to break, not the scorer."""
    top = sr.CONFIDENCE_SCORE_THRESHOLD + 2.0
    runner_up = round(top - (sr.CONFIDENCE_GAP_THRESHOLD - 0.01), 3)
    assert sr.assess_confidence(_matches(top, runner_up)) == "ambiguous"


def test_a_gap_exactly_at_the_threshold_is_confident():
    top = sr.CONFIDENCE_SCORE_THRESHOLD
    runner_up = round(top - sr.CONFIDENCE_GAP_THRESHOLD, 3)
    assert sr.assess_confidence(_matches(top, runner_up)) == "confident"


def test_a_clear_gap_routes_even_when_the_top_score_is_only_moderate():
    """
    Documented rule 6: a moderate top score that nonetheless pulls clearly ahead of the
    field still routes. The gate is about separation, not just absolute strength.
    """
    top = round((sr.AMBIGUOUS_MIN_SCORE + sr.CONFIDENCE_SCORE_THRESHOLD) / 2, 3)
    assert top < sr.CONFIDENCE_SCORE_THRESHOLD
    runner_up = round(top - sr.CONFIDENCE_GAP_THRESHOLD - 0.01, 3)
    assert sr.assess_confidence(_matches(top, runner_up)) == "confident"


# ── search_with_confidence ───────────────────────────────────────────────────


def test_search_with_confidence_reports_the_gap_between_the_top_two(sample_registry):
    response = sr.search_with_confidence("invoice", sample_registry, top_k=5, min_score=0.0)

    assert len(response.results) >= 2
    expected = round(
        response.results[0].relevance_score - response.results[1].relevance_score, 3
    )
    assert response.score_gap == expected
    assert response.top_score == response.results[0].relevance_score


def test_score_gap_is_none_when_fewer_than_two_results_come_back(sample_registry):
    response = sr.search_with_confidence("invoice", sample_registry, top_k=1, min_score=0.0)
    assert len(response.results) == 1
    assert response.score_gap is None


def test_a_query_matching_nothing_is_insufficient_with_no_results(sample_registry):
    response = sr.search_with_confidence("zzzznonexistentqueryzzzz", sample_registry)
    assert response.results == []
    assert response.confidence == "insufficient"
    assert response.top_score == 0.0
    assert response.score_gap is None


# ── confidence vs. token-budget filtering ────────────────────────────────────


def test_confidence_is_assessed_before_budget_filtering_drops_a_near_tie(cap_factory):
    """
    Regression for F-FO-08(c). A max_tokens budget can price the true runner-up out of
    `results` entirely, leaving a much-lower-scoring capability as the new apparent #2.
    Judged against that survivor, the gap looks wide and the call reads "confident" --
    even though the real #2, the one the budget dropped, was a near-tie with #1. The
    confidence gate has to see the full field before the budget narrows it.
    """
    top = cap_factory(
        id="top",
        trigger_patterns=["draft an invoice"],
        description="draft an invoice",
        load_cost_tokens=100,
    )
    near_tie_but_pricey = cap_factory(
        id="near-tie-but-pricey",
        trigger_patterns=["draft an invoice"],
        load_cost_tokens=5000,
    )
    distant_and_cheap = cap_factory(
        id="distant-and-cheap",
        description="invoice",
        load_cost_tokens=100,
    )
    registry = [top, near_tie_but_pricey, distant_and_cheap]

    # Sanity: unbudgeted, the near-tie really is within the gap threshold of #1.
    unbudgeted = sr.search("draft an invoice", registry, top_k=5, min_score=0.0)
    assert [m.id for m in unbudgeted] == ["top", "near-tie-but-pricey", "distant-and-cheap"]
    assert unbudgeted[0].relevance_score - unbudgeted[1].relevance_score < sr.CONFIDENCE_GAP_THRESHOLD

    response = sr.search_with_confidence(
        "draft an invoice", registry, top_k=5, max_tokens=250, min_score=0.0
    )

    # The budget still does its job: the pricey near-tie is not one of the results.
    assert [m.id for m in response.results] == ["top", "distant-and-cheap"]
    # But the classification is judged against the full field, not the survivors.
    assert response.confidence == "ambiguous"


def test_top_score_can_exceed_the_top_returned_results_score_under_a_budget(cap_factory):
    """
    The documented side effect of the fix above: top_score reflects the unbudgeted #1,
    which is not necessarily results[0] once a budget is in play.
    """
    top = cap_factory(id="top", trigger_patterns=["draft an invoice"], load_cost_tokens=5000)
    affordable = cap_factory(id="affordable", description="invoice", load_cost_tokens=100)

    response = sr.search_with_confidence(
        "draft an invoice", [top, affordable], top_k=5, max_tokens=200, min_score=0.0
    )

    assert [m.id for m in response.results] == ["affordable"]
    assert response.top_score == sr.WEIGHT_TRIGGER_PHRASE
    assert response.top_score > response.results[0].relevance_score


# ── log_score_gap ────────────────────────────────────────────────────────────


def test_logging_appends_one_json_record_per_call(tmp_path, sample_registry):
    log = tmp_path / "score-gap-log.jsonl"

    sr.search_with_confidence(
        "draft an invoice", sample_registry, log_gaps=True, log_path=log
    )
    sr.search_with_confidence(
        "plan the greenhouse", sample_registry, log_gaps=True, log_path=log
    )

    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert records[0]["query"] == "draft an invoice"
    assert records[0]["top_id"] == "invoice-drafter"
    assert set(records[0]) == {
        "ts", "query", "confidence", "top_score", "gap", "top_id", "second_id",
    }


def test_nothing_is_logged_unless_logging_is_asked_for(tmp_path, sample_registry):
    log = tmp_path / "score-gap-log.jsonl"
    sr.search_with_confidence("draft an invoice", sample_registry, log_path=log)
    assert not log.exists()


def test_an_unwritable_log_path_never_breaks_the_search_path(sample_registry, tmp_path):
    """
    Logging is best-effort by design: an operator whose log directory has gone away should
    still get their routing decision, not a stack trace on the way to it.
    """
    unwritable = tmp_path / "no-such-directory" / "log.jsonl"

    response = sr.search_with_confidence(
        "draft an invoice", sample_registry, log_gaps=True, log_path=unwritable
    )

    assert response.results
    assert not unwritable.exists()
