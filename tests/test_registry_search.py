"""
Scoring behavior: trigger matching, the partial-trigger cap, tag matching, description
overlap, not_for negative scoring, and the result filters.

Every assertion here is written against the TUNING constants by name, never against a
literal number. Re-tune a weight and these tests still hold; they are about the shape of
the scoring model, not about one particular calibration of it.
"""

import dataclasses

from conftest import sr


# ── trigger matching ─────────────────────────────────────────────────────────


def test_full_trigger_phrase_in_the_query_scores_the_phrase_weight(cap_factory):
    cap = cap_factory(trigger_patterns=["draft an invoice"])
    (match,) = sr.search("please draft an invoice today", [cap])
    assert match.relevance_score == sr.WEIGHT_TRIGGER_PHRASE


def test_a_partial_trigger_word_scores_less_than_the_full_phrase(cap_factory):
    cap = cap_factory(trigger_patterns=["draft an invoice"])

    (full,) = sr.search("draft an invoice", [cap])
    (partial,) = sr.search("invoice", [cap])

    assert partial.relevance_score == sr.WEIGHT_TRIGGER_WORD
    assert partial.relevance_score < full.relevance_score


def test_a_trigger_phrase_does_not_match_as_a_substring_of_an_unrelated_word(cap_factory):
    """
    Regression for F-FO-11. Aligns with the sibling repo's word-boundary anchoring: a
    short trigger phrase must not fire just because its characters happen to appear
    inside a longer, unrelated word.
    """
    cap = cap_factory(trigger_patterns=["cat"])
    assert sr.search("the concatenated log file", [cap]) == []


def test_partial_trigger_hits_are_capped_per_capability(cap_factory):
    """
    A capability with many triggers sharing a common word must not out-score a
    genuinely-matching one just by owning more triggers. Four triggers match here; only
    TRIGGER_WORD_CAP of them may count.
    """
    cap = cap_factory(
        trigger_patterns=[
            "alpha report",
            "bravo report",
            "charlie report",
            "delta report",
        ]
    )
    (match,) = sr.search("alpha bravo charlie delta", [cap])

    # Rounded to match the score as stored: the scorer rounds to 3 places, and binary
    # floats being what they are, 3 * 0.4 is not 1.2 until something rounds it.
    assert match.relevance_score == round(sr.TRIGGER_WORD_CAP * sr.WEIGHT_TRIGGER_WORD, 3)
    assert match.relevance_score < 4 * sr.WEIGHT_TRIGGER_WORD


# ── tag and description matching ─────────────────────────────────────────────


def test_a_full_tag_phrase_outscores_a_single_overlapping_tag_term(cap_factory):
    cap = cap_factory(semantic_tags=["seasonal planning"])

    (phrase,) = sr.search("help me with seasonal planning", [cap])
    (term,) = sr.search("seasonal", [cap])

    assert phrase.relevance_score == sr.WEIGHT_TAG_PHRASE
    assert term.relevance_score == sr.WEIGHT_TAG_TERM
    assert phrase.relevance_score > term.relevance_score


def test_description_overlap_scales_with_the_fraction_of_query_terms_matched(cap_factory):
    cap = cap_factory(description="Draft a client invoice from a timesheet.")

    # Every meaningful query term appears in the description: a full-ratio overlap.
    (full,) = sr.search("draft invoice timesheet", [cap])
    # One of three meaningful terms appears: a one-third-ratio overlap.
    (partial,) = sr.search("invoice greenhouse bicycle", [cap])

    assert full.relevance_score == round(sr.WEIGHT_DESC_OVERLAP, 3)
    assert partial.relevance_score == round(sr.WEIGHT_DESC_OVERLAP / 3, 3)


def test_short_query_words_do_not_count_as_description_overlap(cap_factory):
    """Stop words ("the", "a", "of") must not manufacture a score against any description."""
    cap = cap_factory(description="Plan the schedule of a greenhouse.")
    assert sr.search("the a of", [cap]) == []


# ── not_for negative scoring ─────────────────────────────────────────────────


def test_a_not_for_clause_suppresses_an_otherwise_matching_capability(sample_registry):
    """
    "invoice-auditor" matches this query on vocabulary alone (it owns three "invoice"
    triggers). Its not_for clause names this exact request, and that is what has to keep
    it out of the results.
    """
    query = "draft a brand new invoice from scratch"

    ids = [m.id for m in sr.search(query, sample_registry, top_k=5)]
    assert "invoice-drafter" in ids
    assert "invoice-auditor" not in ids

    # Control: the same capability with the clause removed does surface. Without this,
    # the assertion above could be passing for some unrelated reason.
    auditor = next(c for c in sample_registry if c.id == "invoice-auditor")
    declawed = [
        dataclasses.replace(auditor, not_for=[]) if c.id == "invoice-auditor" else c
        for c in sample_registry
    ]
    assert "invoice-auditor" in [m.id for m in sr.search(query, declawed, top_k=5)]


def test_the_not_for_guard_requires_the_clauses_leading_term_to_be_present(cap_factory):
    """
    Shared domain vocabulary alone must not trigger a penalty. The action verb has to
    match too, and the guard on the clause's leading term is what enforces that.

    The fixture has to be built with care, or this test proves nothing. The penalty needs
    NOT_FOR_MATCH_THRESHOLD matching terms to fire at all, so if only one query term ever
    reaches the clause, the threshold alone suppresses the penalty and the guard is never
    exercised -- the test passes whether the guard exists or not. So: TWO query terms here
    ("design", "system") match the clause, which is enough to fire the penalty on its own.
    Only the leading term ("Building" vs. a query about auditing) holds it back.
    """
    auditor = cap_factory(
        description="Audit a design system.",
        not_for=["Building UI in a client's design system (use ui-builder)"],
    )

    (survivor,) = sr.search("audit the design system", [auditor])
    assert survivor.relevance_score > 0, "the not_for clause fired on a query it should ignore"


def test_a_routing_hint_in_a_not_for_clause_never_affects_scoring(cap_factory):
    """
    A not_for clause may end with a "(use other-skill ...)" routing hint. That hint is
    documentation for the reader; it must be stripped before the clause is matched.

    If it were not stripped, the hint's own words would join the clause's term set, and a
    query about those words would penalize the capability -- the exact opposite of what a
    hint pointing *toward* another skill should do. Here the hint mentions "the rate
    card" and the query is about the rate card, so an unstripped clause would score this
    capability into oblivion.
    """
    hinted = cap_factory(
        description="Update the rate card.",
        not_for=["Drafting a new invoice (use invoice-drafter, which reviews the rate card first)"],
    )
    bare = cap_factory(
        description="Update the rate card.",
        not_for=["Drafting a new invoice"],
    )

    (with_hint,) = sr.search("drafting the rate card", [hinted])
    (without_hint,) = sr.search("drafting the rate card", [bare])

    assert with_hint.relevance_score == without_hint.relevance_score
    assert with_hint.relevance_score > 0


def test_a_stemming_variant_triggers_the_penalty(cap_factory):
    """Term matching prefix-matches, so "evaluate" reaches a clause written about "evaluating"."""
    stemmed = cap_factory(
        description="Vendor contract work.",
        not_for=["Evaluating a vendor contract (use vendor-review)"],
    )
    assert sr.search("evaluate the vendor contract", [stemmed]) == []


def test_a_near_miss_root_does_not_trigger_the_penalty(cap_factory):
    """
    The prefix has to be long enough to stop at genuine stems. "component" and
    "composition" share four characters and are unrelated words; a clause about one must
    not suppress a query about the other.

    As with the guard test above, the fixture is load-bearing. The penalty needs
    NOT_FOR_MATCH_THRESHOLD matching terms, so a fixture where only ONE term can possibly
    match tests the threshold, not the prefix length -- it passes at any prefix length and
    proves nothing. Here BOTH query terms reach the clause under a four-character prefix
    ("component"/"composition" and "design"/"designer"), which is enough to fire the
    penalty. Only the longer prefix on the first pair holds it back.
    """
    near_miss = cap_factory(
        description="Component design work.",
        not_for=["Composition instructions for a designer (use type-setter)"],
    )

    (survivor,) = sr.search("component design", [near_miss])
    assert survivor.relevance_score > 0, (
        "a clause about 'composition' suppressed a query about 'component': the term "
        "prefix is too short to tell the two roots apart"
    )


# ── filters ──────────────────────────────────────────────────────────────────


def test_type_filter_restricts_results_to_one_capability_type(sample_registry):
    skills = sr.search("invoice", sample_registry, top_k=5, capability_type="skill")
    assert skills and all(m.type == "skill" for m in skills)

    references = sr.search("greenhouse", sample_registry, top_k=5, capability_type="reference")
    assert references and all(m.type == "reference" for m in references)


def test_max_tokens_admits_the_top_match_when_the_budget_exactly_covers_it(sample_registry):
    unbudgeted = sr.search("invoice", sample_registry, top_k=5)
    top = unbudgeted[0]

    assert sr.search("invoice", sample_registry, top_k=5, max_tokens=top.load_cost_tokens) == [top]


def test_max_tokens_skips_an_unaffordable_top_match_and_takes_what_fits(cap_factory):
    """
    The budget filter is greedy, not all-or-nothing: it walks the ranked list and takes
    whatever still fits. So a budget too small for the best match does NOT return empty --
    it returns a cheaper, worse one.

    Worth pinning down, because the intuitive reading is the opposite, and a caller who
    assumes "too small a budget means no answer" will silently route to the wrong skill.
    """
    expensive_best = cap_factory(
        id="best", trigger_patterns=["draft an invoice"], load_cost_tokens=5000
    )
    cheap_worse = cap_factory(id="worse", description="invoice", load_cost_tokens=100)
    registry = [expensive_best, cheap_worse]

    ranked = sr.search("draft an invoice", registry, top_k=5)
    assert [m.id for m in ranked] == ["best", "worse"]

    squeezed = sr.search("draft an invoice", registry, top_k=5, max_tokens=200)
    assert [m.id for m in squeezed] == ["worse"]


def test_max_tokens_returns_nothing_when_not_even_the_cheapest_match_fits(sample_registry):
    cheapest = min(m.load_cost_tokens for m in sr.search("invoice", sample_registry, top_k=5))
    assert sr.search("invoice", sample_registry, top_k=5, max_tokens=cheapest - 1) == []


def test_min_score_trims_the_tail_without_reranking(sample_registry):
    unfiltered = sr.search("invoice", sample_registry, top_k=5)
    assert len(unfiltered) >= 2

    floor = unfiltered[0].relevance_score
    filtered = sr.search("invoice", sample_registry, top_k=5, min_score=floor)

    assert [m.id for m in filtered] == [unfiltered[0].id]


def test_top_k_bounds_the_result_count(sample_registry):
    assert len(sr.search("invoice", sample_registry, top_k=1)) == 1


def test_an_empty_query_returns_no_results(sample_registry):
    assert sr.search("", sample_registry) == []
    assert sr.search("   ", sample_registry) == []


def test_a_query_matching_nothing_returns_no_results(sample_registry):
    assert sr.search("zzzznonexistentqueryzzzz", sample_registry) == []


# ── normalize ────────────────────────────────────────────────────────────────


def test_normalize_lowercases_strips_punctuation_and_collapses_whitespace():
    assert sr.normalize("  Draft   an INVOICE, please!  ") == "draft an invoice please"
