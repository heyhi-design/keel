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
3. Recompute the registry `meta` counts (active, superseded, retired, total), by deriving them
   from the entries rather than editing numbers by hand (see "Counts are derived, not trusted").

A correction left `active` after its rule shipped keeps firing on something already enforced, so
the signal degrades. A promoted-but-not-superseded entry is a common source of registry rot.

---

## One entry at a time

Change the registry by adding, merging or retiring **one entry at a time**, never by rewriting the
whole file. A wholesale rewrite, by a person or an agent, tends to shorten every entry, drop the
reasons, reflow hand-written text and lose comments, and a reviewer cannot see which lesson changed.
An itemized change is small enough to review and to revert.

The commands below, from the standalone `agent-corrections` CLI, all work this way. Each one edits
only the lines it must change, re-reads the file to confirm nothing else moved, and refuses (writing
nothing) when the file's layout makes that unsafe. keel ships the mechanism; the CLI is optional.

## Recording a fire

When a known pattern recurs, increment the entry you already have. Do not add a second entry for
the same lesson: a sibling entry resets the count to one, so the promotion threshold never trips.

```bash
corrections_cli.py fire <id>            # times_fired +1, last_fired stamped today
corrections_cli.py fire <id> --date YYYY-MM-DD
```

Deciding *whether* a pattern recurred stays a human judgment. `fire` only records the decision.

## Retiring: a validity window, not a deletion

An entry that stops applying is stamped, never deleted. Its validity window runs from `origin_date`
to `valid_until`, and `retired_reason` says why it closed.

```bash
corrections_cli.py retire <id> --reason "the tool it described is gone"
corrections_cli.py retire <id> --reason "promoted" --superseded-by "os/session-rules.md § Review"
```

The second form is the promotion close-out: status `superseded`, `superseded_by` set, window closed.
Retiring a behavioral entry asks for the same human sign-off as adding one.

## Counts are derived, not trusted

Hand-maintained `meta` counts drift. Derive them instead:

```bash
corrections_cli.py audit --recount            # prints stated vs. derived; exits 1 on drift
corrections_cli.py audit --recount --write    # fixes the drifted count lines in place
```

If you keep an archive file (below), pass it with `--archive <file>`: the live file's counts cover
both files, and the CLI will not write counts while an archive it was not told about sits beside
the registry.

## Active and archive

A registry that loads every session should hold what is in force. Once retired and superseded
entries pile up, move them into an archive file, verbatim:

```bash
corrections_cli.py split --archive corrections-registry-archive.yaml
corrections_cli.py split --archive corrections-registry-archive.yaml --verify
```

The live file's `meta` keeps the whole-registry counts across both files; check them with
`audit --recount --archive <archive file>`. The verify step checks that the two files share no
id, the live file holds only active entries, the archive only retired and superseded ones, and the
stated counts agree. When loading corrections into a session, `inject --max N` caps the block,
behavioral entries first, then the most-fired.

## Optional fields that read better

| Field | What it holds |
|---|---|
| `mistake` | the concrete mistake that happened |
| `why` | why the correction holds, the reason behind the rule |
| `supersedes` | the id of an earlier entry whose claim this one corrects. It points back; `superseded_by` points forward at the rule a promoted entry became. Retire the corrected entry once the new one lands; an audit lists corrected entries that are still active |
| `assumes_rule` | on a seed: the rule it assumes your instance has adopted, as `path/to/file.md § Section` |

**Seeds and the rules they assume.** A framework seed is often written on the assumption that a
rule already exists in your instance. If it does not, the seed either stays active forever with
nobody asking why, or, worse, ships `superseded` by a rule you never adopted and silently stops
loading. `assumes_rule` makes the coupling checkable: an audit flags any seed whose assumed file or
section is absent (`--rules-root` sets where paths resolve). The two superseded seeds in
`seed-corrections.yaml` carry it, pointing at `os/session-rules.md § Verify-Before-Claim`.

## Comparing two registries

Two instances, or a template and an instance, learn some lessons twice. `compare <a> <b>` reports
likely duplicates by trigger overlap and entries that share an id. It is a report only: which lesson
to keep, merge or retire stays a human call.

---

## The human standard

The registry is curated, not auto-generated. An agent may *observe* a recurring pattern and
propose a correction, but a human decides what enters the registry and what gets promoted to a
rule. Unreviewed entries must never reach agent context, because the registry's value depends
entirely on its trustworthiness: the moment it contains noise, agents learn to ignore it.

Keep the intake and the live registry separate. Proposed patterns sit in a staging area a human
reviews; only promoted entries load into sessions.
