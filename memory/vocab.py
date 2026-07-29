"""Write-time contract normalization — the guard that keeps the graph and the
diary canonical at insert time.

This is the single source of truth for the closed knowledge-graph vocabulary
and the diary's agent/wing canonicalization. Two properties matter:

  * ONE definition. ``PREDICATES`` and ``OBJECT_MAX`` live HERE. Any offline
    tooling you build (a periodic normalizer, an extractor) should import them
    from this module rather than keeping a second copy that can drift.
  * RIGHT direction. Offline tools depend on this package, never the reverse:
    the package must never import an offline tool onto the write path.

Entity canonicalization is NOT reimplemented here — it stays in ``canon.py``.
This module imports ``canon``; it never forks its alias map.

Why a CLOSED predicate vocabulary at all: a knowledge graph whose edges are
free-form sentences ("was recently migrated over to") is not queryable — every
synonym is a new predicate. Constraining edges to a small, fixed set keeps the
graph answerable ("what is X gated on?") and keeps write-time cost near zero.
The set below is a sensible starting vocabulary for a solo operating history;
add or remove predicates to fit how you actually reason about your own work,
but keep the set SMALL and closed.
"""
from __future__ import annotations

import re

from . import canon

# The closed knowledge-graph predicate vocabulary. Keep it small; an edge whose
# predicate is not in this set is refused at write time rather than stored, so a
# caller has to fold the detail into a 'status' object instead of inventing a
# one-off predicate. Tune this set to your own work.
PREDICATES = frozenset({
    "merged_to_main_as", "status", "superseded_by", "migrated_from",
    "migrated_to", "gated_on", "deployed_to", "shipped_in", "runs_on",
})

# Keep the edge terse — the relationship, not the story. Detail belongs in an
# entry (memory_write), where it is searchable. An object longer than this is
# refused at write time, not silently truncated.
OBJECT_MAX = 128

# Predicates whose OBJECT is itself an entity (a graph node), so it is
# canonicalized like the subject. For every other predicate the object is prose
# (a status phrase, a date, a blocker) and is stored verbatim.
ENTITY_OBJECT_PREDICATES = frozenset({"superseded_by", "migrated_from", "migrated_to"})

# Clean tense/preposition variants that resolve to one vocabulary predicate.
# Mechanical normalization (lowercase, separators -> "_") runs first, so only
# genuine morphological variants need listing. Semantically ambiguous remaps
# (e.g. "supersedes", which also inverts subject/object) are deliberately
# absent: the write path rejects those and lets the caller choose, rather than
# silently changing what a relation means.
PREDICATE_REMAP = {
    "merged_to": "merged_to_main_as",
    "was_merged_to_main_as": "merged_to_main_as",
    "is_now_on_main_as": "merged_to_main_as",
    "migrating_from": "migrated_from",
    "migrating_to": "migrated_to",
    "remains_gated_on": "gated_on",
    "gated_behind": "gated_on",
    "deployed_at": "deployed_to",
}


def normalize_predicate(pred: str | None) -> str:
    """Mechanical fold (lowercase, whitespace/hyphens -> "_", edges trimmed)
    then a curated remap. The result MAY still be off-vocabulary — the caller
    checks membership in PREDICATES and decides."""
    p = re.sub(r"[\s\-]+", "_", (pred or "").strip().lower())
    p = re.sub(r"_+", "_", p).strip("_")
    return PREDICATE_REMAP.get(p, p)


def prepare_relation(subject: str | None, predicate: str | None,
                     object: str | None) -> tuple:
    """Canonicalize + validate a KG triple for the write path.

    Returns ``(subject, predicate, object, error)``. On success ``error`` is
    None and the three values are the canonical forms to store. On failure the
    first three are None and ``error`` is a caller-facing message; the relation
    must not be written. Rejection (not truncation, not silent folding) is the
    contract: an off-vocabulary predicate, an over-long object, or an empty
    field is surfaced so the caller fixes it, which is what stops the store
    from re-accumulating mess an offline normalizer would otherwise clean up."""
    s_raw = (subject or "").strip()
    p_raw = (predicate or "").strip()
    o_raw = (object or "").strip()
    if not s_raw:
        return None, None, None, "subject is empty"
    if not p_raw:
        return None, None, None, "predicate is empty"
    if not o_raw:
        return None, None, None, "object is empty"
    if len(o_raw) > OBJECT_MAX:
        return None, None, None, (
            f"object is {len(o_raw)} chars (>{OBJECT_MAX}); keep the edge terse "
            f"and put the detail in an entry (memory_write)")
    pred = normalize_predicate(p_raw)
    if pred not in PREDICATES:
        return None, None, None, (
            f"predicate {p_raw!r} is not in the closed vocabulary "
            f"({', '.join(sorted(PREDICATES))}); fold the detail into a "
            f"'status' object instead")
    subj = canon.canonical(s_raw)
    obj = canon.canonical(o_raw) if pred in ENTITY_OBJECT_PREDICATES else o_raw
    if not subj:
        return None, None, None, f"subject {s_raw!r} canonicalizes to empty"
    if not obj:
        return None, None, None, f"object {o_raw!r} canonicalizes to empty"
    return subj, pred, obj, None


# --- diary agent / wing canonicalization -------------------------------------
# The diary is keyed by agent; a spelling variant strands a session's summary
# out of the readable stream. Canonicalizing at write AND read time keeps the
# stream whole.
#
# DEFAULT_AGENT is the fallback identity for a diary write that names no agent.
# Set it to whatever you call your own agent. AGENT_ALIASES folds known spelling
# variants of a single agent's name to one canonical form; it ships empty
# because the right entries are specific to your setup. Example, if your agent
# is written three ways:
#
#     DEFAULT_AGENT = "my-agent"
#     AGENT_ALIASES = {"my agent": DEFAULT_AGENT, "myagent": DEFAULT_AGENT}
#
# (keys are separators-unified-to-single-spaces; see _agent_key).
DEFAULT_AGENT = "default-agent"
AGENT_CANONICAL = DEFAULT_AGENT  # back-compat alias for the fallback name

AGENT_ALIASES: dict[str, str] = {}


def _agent_key(agent: str | None) -> str:
    return re.sub(r"[\s\-_]+", " ", (agent or "").strip().lower()).strip()


def canonical_agent(agent: str | None) -> str:
    """Canonical diary agent name. Empty -> DEFAULT_AGENT. A known spelling
    variant folds to its canonical; an UNKNOWN agent keeps its identity
    (lowercased, separators unified to hyphens) rather than being merged away —
    distinct agents must stay distinct. Idempotent."""
    key = _agent_key(agent)
    if not key:
        return DEFAULT_AGENT
    return AGENT_ALIASES.get(key, key.replace(" ", "-"))


def canonical_wing(wing: str | None) -> str:
    """Lowercase + underscore a diary wing so 'Work' and 'work' cannot split
    into two. This preserves the caller's wing intent (it does not force the
    entry into the agent stream — re-homing existing rows is a data-hygiene
    pass, not a write-time behavior); it only removes the case/whitespace split."""
    return re.sub(r"\s+", "_", (wing or "").strip().lower()).strip("_")
