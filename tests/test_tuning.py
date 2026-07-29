"""
The TUNING block is the contract this module makes with an operator: every number that
shapes a routing decision is a named knob at the top of the file, and re-tuning a knob is
supposed to be the whole edit.

Two things have to be true for that contract to hold, and neither is guaranteed by the
code merely compiling:

  1. The constants have to be *live* -- actually read by search(), not decorative
     leftovers next to hardcoded values buried in the function body.
  2. The prose has to *cite* them rather than restate them. A docstring that spells out
     "0.5" instead of naming the weight goes stale the first time the weight changes,
     and it goes stale silently, because nothing executes a docstring.

The second one is not hypothetical. This module shipped with a scoring docstring whose
six numbers had drifted from the constants directly above it, and the drift was invisible
until someone compared them by hand. This file is what makes that comparison automatic.

This guard is deliberately narrow, not a general "no numbers in a docstring" linter: it
targets bare decimals (with or without a leading zero) and the two integer knobs' exact
values, and it does not -- and cannot cheaply -- catch a coincidental restatement that
reads as something else entirely: a rank/ordinal reference like "#N", a numbered-list
marker like "N.", or a value spelled out in words. Anything outside that shape still
relies on a human noticing at review time.
"""

import re

from conftest import sr

TUNING_CONSTANTS = (
    "WEIGHT_TRIGGER_PHRASE",
    "WEIGHT_TRIGGER_WORD",
    "TRIGGER_WORD_CAP",
    "WEIGHT_TAG_PHRASE",
    "WEIGHT_TAG_TERM",
    "WEIGHT_DESC_OVERLAP",
    "NOT_FOR_PENALTY",
    "NOT_FOR_MATCH_THRESHOLD",
)

# Every function whose prose describes a tunable number. A bare decimal in any of these
# is a value that can drift from the constant it claims to describe, and -- the reason
# this list exists at all -- a value that survives a re-tuning pass which only edited the
# code. The first sweep of this module missed log_score_gap and search_with_confidence
# entirely, and a stale threshold sat in both.
DOCUMENTED_FUNCTIONS = ("search", "search_with_confidence", "assess_confidence", "log_score_gap")


def _scoring_block(doc: str) -> str:
    """The part of search()'s docstring that describes the scoring model."""
    start = doc.index("Scoring is additive")
    end = doc.index("Args:", start)
    return doc[start:end]


_DECIMAL_RE = re.compile(r"(?<![\w.])-?\d*\.\d+")


def _decimal_hits(text: str) -> list[str]:
    """
    Bare decimals that could be a knob restatement, with or without a leading zero (a
    weight written as ".7" is just as stale-prone as one written "0.7"). Excluded when
    immediately preceded by a word character or another dot, so this never fires on a
    piece of a larger number.
    """
    return _DECIMAL_RE.findall(text)


INTEGER_TUNING_CONSTANTS = ("TRIGGER_WORD_CAP", "NOT_FOR_MATCH_THRESHOLD")


def _bare_integer_hits(text: str, value: int) -> list[str]:
    """
    A bare digit token equal to an integer knob's value -- minus the two shapes that read
    as something else entirely: a rank/ordinal reference (log_score_gap's "gap to #"
    followed by a candidate's position means "the next candidate," not this constant) and
    a numbered-list marker (assess_confidence's own rule numbering).
    """
    pattern = r"(?<![\w.#])" + re.escape(str(value)) + r"(?!\.)\b"
    return re.findall(pattern, text)


# ── the constants are live ───────────────────────────────────────────────────


def test_every_tuning_constant_exists_and_is_a_number():
    for name in TUNING_CONSTANTS:
        value = getattr(sr, name)
        assert isinstance(value, (int, float)), f"{name} is not a number"


def test_retuning_a_weight_actually_changes_the_score(monkeypatch, cap_factory):
    """
    Proves WEIGHT_TRIGGER_PHRASE is read at scoring time. If search() had a hardcoded
    literal in the function body instead, this would pass unchanged and the TUNING block
    would be a comforting lie.
    """
    cap = cap_factory(trigger_patterns=["draft an invoice"])

    (before,) = sr.search("draft an invoice", [cap])
    monkeypatch.setattr(sr, "WEIGHT_TRIGGER_PHRASE", sr.WEIGHT_TRIGGER_PHRASE + 5.0)
    (after,) = sr.search("draft an invoice", [cap])

    assert after.relevance_score == before.relevance_score + 5.0


def test_retuning_the_not_for_penalty_actually_changes_the_score(monkeypatch, sample_registry):
    """Same proof for the one negative weight: raise the penalty, and the suppression deepens."""
    query = "draft a brand new invoice from scratch"

    monkeypatch.setattr(sr, "NOT_FOR_PENALTY", 0.0)
    unpenalized = [m.id for m in sr.search(query, sample_registry, top_k=5)]
    assert "invoice-auditor" in unpenalized

    monkeypatch.setattr(sr, "NOT_FOR_PENALTY", 99.0)
    crushed = [m.id for m in sr.search(query, sample_registry, top_k=5)]
    assert "invoice-auditor" not in crushed


# ── the prose cites the constants instead of restating them ──────────────────


def test_the_scoring_docstring_names_every_weight_it_describes():
    block = _scoring_block(sr.search.__doc__)
    for name in TUNING_CONSTANTS:
        assert name in block, f"search()'s scoring docstring never mentions {name}"


def test_the_scoring_docstring_hardcodes_no_weight_values():
    """
    The guard. Any bare decimal in the scoring docstring is a value that can drift away
    from the constant it claims to describe, so none are allowed: cite the name and let
    the reader look up the number in one place.
    """
    block = _scoring_block(sr.search.__doc__)
    hardcoded = _decimal_hits(block)

    assert not hardcoded, (
        f"search()'s scoring docstring hardcodes the weight value(s) {hardcoded}. "
        "Name the TUNING constant instead -- a number written here drifts silently the "
        "next time the constant is re-tuned."
    )


def test_the_confidence_docstring_names_its_thresholds_instead_of_restating_them():
    """The confidence gate carries the same risk and is held to the same rule."""
    doc = sr.assess_confidence.__doc__

    for name in ("AMBIGUOUS_MIN_SCORE", "CONFIDENCE_SCORE_THRESHOLD", "CONFIDENCE_GAP_THRESHOLD"):
        assert name in doc

    rules = doc[doc.index("Rules (in order)") : doc.index("Called by")]
    assert not _decimal_hits(rules)


def test_no_documented_function_hardcodes_a_tunable_number_anywhere_in_its_prose():
    """
    The same rule as above, swept across every function whose docstring talks about
    thresholds, rather than only the two that were checked first.

    A bare decimal is allowed only where it is genuinely not a knob: 0.0 (the "filter
    nothing" sentinel) and 1.0 (the unit anchor of an additive scale, and the ceiling of
    a ratio). Everything else has to be a name.
    """
    NOT_KNOBS = {"0.0", "1.0"}

    offenders = {}
    for func_name in DOCUMENTED_FUNCTIONS:
        doc = getattr(sr, func_name).__doc__ or ""
        found = [n for n in _decimal_hits(doc) if n not in NOT_KNOBS]
        if found:
            offenders[func_name] = found

    assert not offenders, (
        f"These docstrings hardcode tunable values: {offenders}. Name the constant "
        "instead. A number written into prose survives a re-tuning pass that only edits "
        "the code, and then it is quietly describing a scale the code no longer uses."
    )


def test_no_documented_function_hardcodes_an_integer_knobs_bare_value():
    """
    The integer-valued half of the guard above. TRIGGER_WORD_CAP and
    NOT_FOR_MATCH_THRESHOLD are the two TUNING knobs typed as int; a docstring that spells
    out their value in bare digits instead of citing the name is exactly as stale-prone as
    a hardcoded decimal, so it gets the same rule -- with the two narrow exceptions the
    module docstring above names.
    """
    offenders = {}
    for const_name in INTEGER_TUNING_CONSTANTS:
        value = getattr(sr, const_name)
        for func_name in DOCUMENTED_FUNCTIONS:
            doc = getattr(sr, func_name).__doc__ or ""
            if _bare_integer_hits(doc, value):
                offenders.setdefault(func_name, []).append(const_name)

    assert not offenders, (
        f"These docstrings hardcode an integer knob's bare value instead of citing its "
        f"name: {offenders}. Name the constant instead."
    )


# ── the routing floor and the gate's floor stay in step ──────────────────────


def test_the_default_filter_never_sits_above_the_confidence_gates_floor():
    """
    DEFAULT_MIN_SCORE filters the result list; AMBIGUOUS_MIN_SCORE is the floor the gate
    uses to decide whether a top result is worth surfacing at all. They are two names for
    one idea, and the filter must never be the stricter of the two.

    If it is, matches the gate would have called "ambiguous" get discarded before it ever
    sees them, and search_with_confidence() reports "insufficient" for a match that
    cleared the gate's own documented bar. That is exactly what happened here: every other
    weight in this module was re-scaled and the filter's default was left behind on the
    old scale, one step above the floor.
    """
    assert sr.DEFAULT_MIN_SCORE <= sr.AMBIGUOUS_MIN_SCORE, (
        f"DEFAULT_MIN_SCORE ({sr.DEFAULT_MIN_SCORE}) is stricter than AMBIGUOUS_MIN_SCORE "
        f"({sr.AMBIGUOUS_MIN_SCORE}), so the confidence gate can never return 'ambiguous' "
        "for a real match: the filter removed those matches first."
    )


def test_a_match_at_the_gates_floor_survives_the_default_filter(cap_factory):
    """The behavioral half of the invariant above, proven end to end rather than asserted."""
    cap = cap_factory(trigger_patterns=["draft an invoice"])

    # A lone partial-trigger hit scores exactly WEIGHT_TRIGGER_WORD.
    (raw,) = sr.search("invoice", [cap])
    assert raw.relevance_score >= sr.AMBIGUOUS_MIN_SCORE  # it clears the gate's floor

    response = sr.search_with_confidence("invoice", [cap])
    assert response.results, (
        "a match that clears the confidence gate's floor was filtered out before the gate "
        "could see it"
    )
    assert response.confidence != "insufficient"
