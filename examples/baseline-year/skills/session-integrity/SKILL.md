---
name: "session-integrity"
description: >-
  End-of-session review: check this session's own output for consistency, catch what it missed,
  and propagate changes into anything that depends on them. Use at the end of any substantial
  work session and offer it proactively after one. Also for "tidy up before we stop", "did we
  miss anything", "close this out properly", or "check my work before I send it".
---

# Baseline Year Session Integrity

> **Worked example — this firm does not exist.** "Baseline Year" and Sam Oyelaran are invented.
> This is `skills/templates/session-integrity/SKILL.template.md` filled in. Copy the template,
> not this file, and do not deploy this skill: its `name:` collides with the real one you will
> deploy. See [`examples/README.md`](../../../README.md).

The check that keeps this practice honest with itself. Reviews what a session actually did,
catches inconsistencies before they compound, and makes sure a change in one place reaches
everything downstream of it. In a reporting practice the downstream problem is the whole problem:
a figure that changes in the model and does not change in the report is exactly the defect this
firm sells the fix for, and it is embarrassing to ship it internally.

---

**Exit Gate.** This skill's own output is the reference implementation of the Exit Gate defined
in `os/session-rules.md`. Every section below maps to one of that gate's required slots.

---

## Phase 0: What did this session actually touch?

List the files written or edited, the client model or workbook touched, and anything read but not
changed. Check rather than remember. If a client workbook was edited, note which tab and which
cells — "updated the inventory" is not a footprint.

## Phase 1: Load the corrections registry

Read the three active entries in `os/corrections/corrections-registry.yaml` before auditing
anything. Two of them describe figures losing their qualifications while moving between
documents, which is the failure mode most likely to be present in whatever this session just
produced.

## Phase 2: Consistency audit

Cross-reference everything touched against `references/review-checklist.md`. Produce a structured
findings list rather than an overall verdict. At minimum:

- **Figure drift.** Does every number in prose still match the model it came from? Check the
  actual cell, not the last email about it.
- **Tier stripping.** Did any estimate lose its data-quality tier while moving between documents?
  This is `estimated-figure-presented-as-measured`, and it fires most often during a session that
  builds a summary from a longer draft.
- **Boundary changes.** If anything moved a client's boundary this session, was the recalculation
  threshold checked, and is the check recorded with its date?
- **Stale references.** Does anything touched cite a factor, a regulation, or a client fact that
  changed elsewhere and was not updated here?
- **Voice drift.** Any client-facing prose produced this session, held against the `voice` skill's
  final scan.

A pass that finds nothing deserves a second look. Reviews that always come back clean are usually
not looking at the model.

## Phase 3: Correction capture

Anything wrong that looks likely to recur goes to the corrections registry. The bar is two
occurrences, not one — a single stumble is a mistake, and logging every mistake makes a registry
nobody reads. Write it immediately if it is a habit; hold it for review if it would change a
binding rule rather than a habit. `os/corrections/LIFECYCLE.md` carries the split.

## Phase 4: Smoke test

Run the deterministic checks for whatever this session touched:

- Inventory model: totals reconcile across tabs; every figure in the summary traces to a row in
  the source map; no hardcoded number where a formula belongs.
- Any YAML in the OS: parses.
- Client-facing prose: the `voice` skill's final scan, actually run.
- Boundary log: an entry exists for every boundary change discussed this session.

A session's own self-review is never the only check on its own work.

## Phase 5: Forward propagation scan

Take what changed this session and search for anything that references the old state. In this
practice the usual chain runs: model → source map → report prose → summary slide → whatever went
to the client by email. The further down that chain, the more likely it is stale and the more
visible the staleness is to somebody outside the firm. Fix or flag accordingly, and write a
handoff rather than leaving unfinished propagation implicit.

## Phase 6: Backward reconciliation

Does anything this session *read* but did not write contradict what it just produced? Inherited
client material is the common case: a methodology note written by a previous consultant, still
sitting in the folder, still describing a method this session just changed.

## Phase 7: Decision log and commit coverage

- A decision worth a permanent record goes to `os/decision-log.md`. Read the last few entries
  first. Declining work, changing what an offering includes, and any ruling about what this
  practice will not do all qualify. Finishing a task does not.
- Confirm every substantive change has a commit and every commit is intentional. Client data
  never enters version control; a commit containing a client name, a site location, or an
  unpublished figure stops the close-out until it is removed.

## Phase 7.5: External tracker

Not used. This practice runs on the repository, a calendar, and a boundary log per client.
Skipped deliberately rather than by omission.

## Phase 8: The report

Produce a structured report with these sections:

- **Fixes Applied**: what was corrected in place, one line per fix.
- **Smoke Test**: what was actually run, and the result.
- **Findings Integration**: what Phases 2, 5, and 6 found and what happened to each.
- **Session Integrity**: one line — clean, or what remains open.
- **Next Session Prompt**: what to pick up first.

An empty section is a visible failure, not a pass. If there is nothing to report, say so and say
how that was verified.

## Phase 9: Close

Apply approved fixes. Draft the commit message. If a client engagement moved today, update the
boundary log before closing; it is the one record that is painful to reconstruct later.

## Related files

- `references/review-checklist.md` : the consistency-audit checklist Phase 2 runs against.
- `os/session-rules.md` : the Exit Gate this skill implements.
- `os/corrections/LIFECYCLE.md` : the write-authority split referenced in Phase 3.

---

**Exit Gate reminder:** Phase 8's report *is* the Exit Gate close-out. Don't skip it because the
session felt uneventful.
