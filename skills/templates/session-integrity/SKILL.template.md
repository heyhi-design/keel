---
name: "session-integrity"
# Keep name == this skill's folder name == its registry id. A firm prefix
# (like "acme-session-integrity") is fine only if the folder and registry id use it too.
description: >-
  [End-of-session review: check this session's own output for consistency, catch what it
  missed, and propagate changes to anything else that depends on them. Use at the end of any
  substantial work session, and offer it proactively after one even if not asked. Include at
  least three colloquial phrasings: see skills/README.md's colloquial-trigger rule.]
---

# [Your Firm] Session Integrity

The check that keeps your operating system honest: reviews what a session actually did, catches
inconsistencies before they compound, and makes sure a change in one place propagates to
everything else that depends on it. This is the mechanism that makes session ten more reliable
than session one, instead of just as reliable.

---

**Exit Gate.** This skill's own output is the reference implementation of the Exit Gate defined in
`os/session-rules.md`. Every section below maps to one of that gate's required slots.

---

## Phase 0: What did this session actually touch?

Establish the footprint before reviewing anything. Use whatever methods are available: a diff
against the last commit, a list of files written or edited this session, a note of what was read
but not changed. Don't rely on memory of what happened; check.

## Phase 1: Load your corrections memory

Read your active corrections registry (`os/corrections/corrections-registry.yaml` once
filled in) before auditing anything. You're checking this session's work against what you've
already learned to watch for, not against a generic quality bar.

## Phase 2: Consistency audit

Cross-reference everything touched this session against `references/review-checklist.md`.
Produce a real, structured list of findings, not a summary judgment. Categories worth checking, at
minimum:

- **Stale references.** Does anything touched this session reference a fact, count, or state that
  changed elsewhere and wasn't updated here?
- **Contradictions.** Does anything written this session conflict with something already true
  elsewhere in the project?
- **Propagation gaps.** Did a change that should ripple to another file actually ripple there?
- **Voice drift.** If this session produced any external-facing writing, does it hold to your
  voice skill's rules?

A pass that finds nothing is worth a second look before you trust it. Session reviews that always
come back clean usually aren't looking hard enough.

## Phase 3: Correction capture

For anything wrong that isn't a one-off mistake (a pattern likely to recur), write it to your
corrections registry. Decide the write authority per entry: some corrections you can log
immediately and trust; others (anything that changes a binding rule, not just a habit) should wait
for your own review before they're treated as settled. Name this split explicitly in
`os/corrections/LIFECYCLE.md` rather than deciding it ad hoc each time.

## Phase 4: Smoke test

Run whatever deterministic checks exist for what this session touched: a linter, a test suite, a
schema validator, a link checker. A session's own self-review should never be the only check on
its own work.

## Phase 5: Forward propagation scan

Extract what's new or changed from this session. Search the rest of the project for anything that
references the old state and hasn't been updated. Classify what you find by how visible the
staleness would be to someone reading it cold, and fix or flag accordingly. If there's more
propagation work than this session can finish, write a clear handoff for the next one rather than
leaving it implicit.

## Phase 6: Backward reconciliation

The inverse of Phase 5: does anything this session *read* but didn't itself write contradict what
it just produced? A forward scan alone misses drift that was already present before this session
started; this phase catches it.

## Phase 7: Decision log and commit coverage

- If this session made a decision worth a permanent record, append it to
  `os/decision-log.md`. Read the last few entries first to avoid restating or
  contradicting something already logged.
- Confirm every substantive change has a corresponding commit, and every commit corresponds to a
  real, intentional change. Orphans in either direction are a sign something got missed or
  something unintended got included.

## Phase 7.5 (optional: larger or multi-tool operations)

If your practice uses an external tracker separate from this repository (an issue tracker, a
project board), reconcile against it here: verify state from more than one source before writing
an update, and never write to an external tracker without your own explicit approval first. Skip
this phase entirely, on purpose, if you don't run one.

## Phase 8: The report

Produce a structured report with these sections, matching the Exit Gate's required slots:

- **Fixes Applied**: what you corrected in place, one line per fix.
- **Smoke Test**: what you actually ran, and the result.
- **Findings Integration**: what Phases 2, 5, and 6 found and what happened to each finding.
- **Session Integrity**: a one-line verdict: clean, or what remains open.
- **Next Session Prompt**: what the next session should pick up first.

An empty section here is a visible failure, not a pass. If a section has nothing to report, say so
explicitly ("no fixes needed this session, verified by X") rather than leaving it blank.

## Phase 9: Close

Apply any approved fixes. If you're running Tier 2 or 3 memory (see `docs/memory.md`), save
whatever this session produced that's worth recalling later. Then hand this report to The Session
Close Sequence in `os/session-rules.md` (the `session-end` skill runs it): it writes the report to
the operator's handoff file or the pull request body and commits by the instance's close mode.
This skill reviews; it does not decide where the report or the work goes.

## Related files

- `references/review-checklist.md` : the consistency-audit checklist Phase 2 runs against.
- `os/session-rules.md` : the Exit Gate this skill implements.
- `os/corrections/LIFECYCLE.md` : the write-authority tiers referenced in Phase 3.

---

**Exit Gate reminder:** this skill's Phase 8 report *is* the Exit Gate close-out. Don't skip it
even when the session felt uneventful.
