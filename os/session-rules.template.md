<!--
KEEL · CONFIGURATION TEMPLATE
File: os/session-rules.template.md

What this is: the operational patterns that govern HOW work happens during an agent session.
  Operating principles govern WHAT to produce; these govern how to produce it. The mechanisms
  here (verify-before-claim, the Exit Gate, propagation discipline, commit envelopes) are
  general-purpose. Fill the [BRACKETED SLOTS] with your own tool names and paths.
When it loads: at session start, and referenced by your integrity and scanner routines.
How to fill it: keep the mechanisms; swap [bracketed] references for your own tools, files,
  and issue tracker. Delete the italic authoring notes and this comment block when done.
-->

# Session Workflow Rules

Operational patterns that complement the constraints in operating-principles. Those govern
*what* to produce; these govern *how*.

---

## Task Execution

Apply reversible changes directly. Do not ask permission before a file edit that an Edit or
Write call could undo. When the operator requests a task that ends in file changes, the request
is the permission. Report what was done, not what you propose to do.

Ask first only for: irreversible actions (deleting files, pushing, sending external messages),
genuinely ambiguous scope, or a single instruction that admits more than one materially
different reading on a client-facing artifact. The test: can this be undone with one edit? If
yes, do it.

---

## Task-Level Verification

Before marking any non-trivial task complete, verify three things: (1) the output matches the
stated intent, not just the literal instruction; (2) no applicable constraint or correction was
violated; (3) the work propagates to everything it affects. Point 3 has two signatures.
*Modifying* an existing file means checking that files which reference it are still accurate.
*Creating* a new file means finding which existing indexes should now point to it and updating
them in the same task.

For reusable artifacts (prompts, configs, templates, scripts), point 1 requires a smoke test:
run the artifact against a few concrete inputs that span its range, and report the outcomes in
the response rather than asserting success. Pure proofreading misses pattern-level errors that
smoke testing catches.

**Recompute computable values.** Any value a delivered artifact states that a machine could
recompute (a count, a ratio, a version, a derived value) must be verified by running the
computation, not asserted from estimate. A count that describes a set is a computable value too:
count the set.

---

## Verify-Before-Claim

Every claim in a handoff that asserts a verifiable state ("tests pass," "the file was created,"
"the count reconciles," "all references resolve") must either name the exact command that was
run and quote its result, or be marked `[judgment]` so the next reader knows it was not verified
mechanically. A bare assertion without either is a defect: the handoff is the contract, and an
unverified claim propagates as truth into the next session.

What counts as verifiable: anything a grep, a file check, a one-line script, or a parse could
resolve. What does not: taste calls, positioning, design critique. Mark those `[judgment]`.

Findings returned by a sub-agent, a reviewer, or the operator's own report of an action they
took ("I merged it," "I deployed it") are leads, not facts. When the effect is mechanically
checkable, confirm it against ground truth before building on it.

---

## Commit Envelope Convention

Every agent-generated commit carries a structured footer connecting the change to the decision
record, so history can be read without cross-referencing two systems by hand.

```
[scope] Verb + subject line

Decision-log: YYYY-MM-DD · Entry title   (omit if no matching entry)
Files: key files changed                 (omit if obvious from the diff)
Notes: anything that does not fit above   (omit if none)
```

*Authoring note: define your own `[scope]` values (e.g. `[brand]`, `[engineering]`, `[client]`,
`[ops]`). Keep them stable so history stays parseable.*

---

## Planning Artifact Convention

Every planning artifact (any `*-plan.md`, `*-spec.md`, `*-brief.md`, or next-session prompt)
carries a `status:` frontmatter field and, if you track work in an issue system, a link to the
tracking issue. The status field is what lets a scanner tell done work from open work.

**Status vocabulary:** `pending` (not started), `partial` (some items done), `done` (complete),
`archived` (superseded). Flipping this field when work completes is a required close-out action
(see the Exit Gate). An unflipped status is a stale trigger the next session re-fires on.

---

## Propagation Tier Discipline

Not all propagation has the same urgency.

**Tier 1 - Index updates. Must happen in-task.** Some documents are indexes of what exists
(folder READMEs, a skills table, a registry). When you create a new thing, the index that should
point to it is *wrong* until you update it. Do it before marking the task complete, not at
session end. The test: if someone opened the index right now, would they know this new thing
exists?

**Tier 2 - Consistency updates. Catch at session integrity.** When you modify an existing file,
documents that *reference* it may go slightly stale (a count off by one, a description no longer
exact). These can wait for an end-of-session integrity pass.

The distinction: creating a new file makes an index wrong (Tier 1, fix now). Modifying a file
makes references stale (Tier 2, catch at the end).

---

## The Exit Gate

Every session that produces a document, artifact, plan, or decision record exits through this
gate. The handoff cannot be emitted without it. Each item below requires a concrete artifact
under a named header, not a claim that the work was done. An empty header is a visible failure;
advisory prose ("I checked for bugs") is not.

Two flavors. Use **Flavor A** by default. Use **Flavor B** when the session reads, writes, or
advances a planning artifact.

**Flavor A - three required headers:**

- `## Fixes Applied` - defect sweep. Apply fixes until clean: bugs, inconsistencies, stale
  citations, advisory language masquerading as procedure. One line per fix.
- `## Smoke Test` - verification ran. For code: typecheck, lint, or trace one full path with the
  expected output stated. For writing: re-read as a skeptical first-time reader and test one
  counterexample. For a visual artifact: render it to an image and view it, do not inspect only
  the source. State what was run and the result.
- `## Next Session Prompt` - a copy-pasteable paragraph. What to load, where to start, the first
  concrete action, written so a fresh agent with no memory of this session can resume.

**Flavor B - five required headers.** The three above, plus:

- `## Findings Integration` - every finding integrated into the active plan, not just noted.
- `## Session Integrity` - a lightweight check that the integrated plan still holds against its
  original intent and that new entries propagated to the plan's own index.

**Why structural, not advisory.** Advisory closing language gets skipped under session pressure.
An empty `## Fixes Applied` block is a finding the next reader catches; a missing "I checked for
bugs" is invisible. Required headers with required artifacts make the gate visible.

---

## Craft Check

Before finalizing any technical output (a schema, an architecture decision, a script), ask: is
this the minimal, clear implementation, or did I take a shortcut? If an approach feels like a
workaround, build the proper one instead. Skip this for trivial fixes. This is the technical
sibling of the voice rules: the voice rules force a better word; the craft check forces a better
structure.

---

*Fill the pointers below with your own files and tools, then delete this note:*
*Operating principles: [path] · Decision log: [path] · Integrity routine: [tool/skill]*
