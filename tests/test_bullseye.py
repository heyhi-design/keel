"""
The bullseye harness: every registered skill's own first trigger phrase must route to it.

This is the one instrument in the suite that tests a REAL registry rather than an
invented fixture. The rest of the suite proves the scoring code behaves in the abstract;
this proves the code and the data you actually maintain still agree with each other. Both
layers matter, and it is the second one whose absence is easy to miss: a fixture suite
that is internally consistent says nothing about whether your own registry, edited by
hand over time, still routes the way you think it does.

It loads your own `skill-registry.yaml` if you have renamed the template and started
filling it in, and falls back to the shipped `skill-registry.template.yaml` otherwise --
so this test passes clean on a fresh checkout, before you have written a single skill of
your own, and keeps working once you have replaced every entry with real ones.

Why the FIRST trigger phrase: it is the one a skill's author chose to lead with, so it is
the strongest claim the registry makes on that skill's behalf. If a skill cannot win on
its own opening phrase, typed verbatim, a softer paraphrase will not do better.

The bar is rank-1, not "appears somewhere in the results." Ranking second behind an
unrelated skill is a routing failure an agent following this scaffold's own routing rule
("load the clear top result") would act on -- it would load the wrong skill.
"""

from pathlib import Path

import pytest

from conftest import REPO_ROOT, TEMPLATE_REGISTRY, sr

_LIVE_REGISTRY = REPO_ROOT / "skills" / "registry" / "skill-registry.yaml"
_REGISTRY_PATH = _LIVE_REGISTRY if _LIVE_REGISTRY.exists() else TEMPLATE_REGISTRY

_REGISTRY = sr.load_registry(_REGISTRY_PATH)
_SKILLS = [c for c in _REGISTRY if c.type == "skill"]


# ── known misses ──────────────────────────────────────────────────────────────
#
# Empty by design, and it should stay that way on a clean registry. An entry here exempts
# a skill from the bullseye -- it is a debt marker, not a resting place. `strict=True`
# means a fixed entry reports XPASS(strict) and reddens the suite until the exemption is
# removed, so a stale exemption cannot silently hide a real fix or, worse, a real
# regression that later reintroduces the same miss.
#
# If your own registry adds an entry here, say why in the value: which skill it is,
# which other skill is currently winning its first trigger, and what you tried before
# reaching for the exemption (rewording the trigger, tightening a not_for clause on the
# skill that's winning). See skills/registry/README.md's `not_for` section for the
# authoring checklist before writing a clause to fix this.
KNOWN_MISSES = {}


def _bullseye_params():
    params = []
    for cap in _SKILLS:
        if not cap.trigger_patterns:
            params.append(
                pytest.param(
                    cap,
                    marks=pytest.mark.skip(reason=f"{cap.id} declares no trigger_patterns"),
                    id=cap.id,
                )
            )
            continue
        marks = []
        if cap.id in KNOWN_MISSES:
            marks.append(pytest.mark.xfail(strict=True, reason=KNOWN_MISSES[cap.id]))
        params.append(pytest.param(cap, marks=marks, id=cap.id))
    return params


@pytest.mark.parametrize("cap", _bullseye_params())
def test_a_skills_first_trigger_phrase_routes_to_that_skill(cap):
    query = cap.trigger_patterns[0]
    results = sr.search(query, _REGISTRY, top_k=3)

    assert results, f"{query!r} matched nothing at all"

    ranked = [f"{m.id} ({m.relevance_score})" for m in results]
    assert results[0].id == cap.id, (
        f"{cap.id} declares {query!r} as its first trigger, but that query ranks "
        f"{results[0].id} first.\n"
        f"  top 3: {', '.join(ranked)}\n"
        f"If this routing change was intended, move {cap.id} into KNOWN_MISSES with the "
        f"reason; if it was not, the trigger or not_for edit that caused it is the bug."
    )


# ── the harness's own guard rails ────────────────────────────────────────────


def test_the_harness_covers_every_registered_skill():
    """
    The harness is worthless if it silently stops covering skills -- a parametrize over
    an empty list still passes. Pin the count against the registry's own count of `type:
    skill` entries, computed independently of the parametrize list above, so a skill
    added to the registry but never picked up here would fail this instead of vanishing.
    """
    all_caps = sr.load_registry(_REGISTRY_PATH)
    skills_in_registry = [c for c in all_caps if c.type == "skill"]

    assert len(_SKILLS) == len(skills_in_registry)
    assert len(_SKILLS) > 0, (
        f"no skills found in {_REGISTRY_PATH} -- the bullseye harness has nothing to check"
    )


def test_the_known_miss_list_has_not_rotted():
    """
    Every KNOWN_MISSES entry must name a skill that still exists in the registry being
    tested. A stale entry would exempt nothing while reading as a live exception, and the
    xfail above would never run -- meaning the defect it documents could return and go
    unnoticed.

    While KNOWN_MISSES is empty this test is dormant, not load-bearing: `set() - ids` is
    empty whatever `ids` holds. It earns its keep the moment an entry is added. The `ids`
    assertion below is the one thing here that can fail today, on an empty or misloaded
    registry.
    """
    ids = {c.id for c in _SKILLS}
    assert ids, "no skills loaded -- the registry fixture is empty, so this test is vacuous"
    stale = sorted(set(KNOWN_MISSES) - ids)
    assert not stale, f"KNOWN_MISSES names skills that are no longer in the registry: {stale}"
