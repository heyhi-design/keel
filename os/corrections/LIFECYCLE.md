<!--
KEEL · CONFIGURATION TEMPLATE
File: os/corrections/LIFECYCLE.md
What this is: how a correction moves from a one-off note to a hard rule, and how it retires.
When it loads: on demand, when you are curating your registry.
How to fill it: this is a mechanism doc, not a template with slots. Adjust the thresholds to
  your own cadence, then delete this comment block.
-->

# Corrections Lifecycle

The corrections registry turns a repeated mistake into a rule. This file describes the
mechanism: the statuses, the promotion thresholds, and the human standard that keeps the
registry trustworthy.

The whole point is compounding institutional memory. A mistake caught once is a note. The same
mistake caught a third time is a pattern worth encoding so no future session pays for it again.

---

## The three statuses

A correction is always in exactly one state.

| Status | Meaning |
|---|---|
| **active** | This correction is in force. Agents load it at session start and must honor it. |
| **superseded** | A stronger mechanism now covers this pattern (usually a hard rule you promoted). The entry stays in the registry for provenance but no longer loads as active guidance. It carries a `superseded_by` field pointing at the rule that replaced it. |
| **retired** | The pattern no longer applies (the tool changed, the workflow is gone). Kept for the record, not loaded. |

Note: **promoted** is an *action*, not a status. When a correction fires often enough to earn a
permanent rule, you promote it (write the rule into your session rules or operating principles)
and then mark the original entry `superseded`, pointing `superseded_by` at the rule's new home.

The two superseded seeds in `seed-corrections.yaml` are a worked example: they point at the
Verify-Before-Claim rule at `os/session-rules.md`, the file you rename
`os/session-rules.template.md` to when you fill it in. Once you adopt that rule, those specific
patterns are covered by it, so they load as history, not as active guidance.

---

## Promotion thresholds

A correction earns promotion to a hard rule when it keeps firing despite being in the registry.
A reasonable default trigger:

> **5 or more total fires, OR the same pattern across 3 or more separate sessions.**

The first number is a lifetime count, not a rolling window. The schema stores a running
`times_fired` total and a single `last_fired` date, so it can answer "how many times in all" but
not "how many in the last 30 days." Treat `times_fired` as a floor on the number of sessions a
pattern has already cost you, count it honestly, and the two triggers mostly agree.

When either fires, the advisory correction is no longer doing its job as a soft note. Promote it:
write it into your session rules or operating principles as a non-negotiable, then supersede the
registry entry. Tune these numbers to your own cadence; the principle is what matters, not the
exact count.

---

## The close-out protocol

When you promote a correction, do all three in the same pass so the registry never lies:

1. Write the new hard rule into its permanent home.
2. Set the original entry's `status` to `superseded` and `superseded_by` to the rule's location.
3. Recompute the registry `meta` counts (active, superseded, retired, total).

A correction left `active` after its rule shipped keeps firing on something already enforced, so
the signal degrades. A promoted-but-not-superseded entry is a common source of registry rot.

---

## The human standard

The registry is curated, not auto-generated. An agent may *observe* a recurring pattern and
propose a correction, but a human decides what enters the registry and what gets promoted to a
rule. Unreviewed entries must never reach agent context, because the registry's value depends
entirely on its trustworthiness: the moment it contains noise, agents learn to ignore it.

Keep the intake and the live registry separate. Proposed patterns sit in a staging area a human
reviews; only promoted entries load into sessions.
