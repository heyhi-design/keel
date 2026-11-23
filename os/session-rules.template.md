<!--
KEEL · CONFIGURATION TEMPLATE
File: os/session-rules.template.md

What this is: the operational patterns that govern HOW work happens during an agent session.
  Operating principles govern WHAT to produce; these govern how to produce it. The mechanisms
  here (verify-before-claim, the Exit Gate, propagation discipline, commit envelopes) are
  general-purpose. Fill the [BRACKETED SLOTS] with your own tool names and paths.
When it loads: on demand, at session close (the session-end skill) and when your integrity and
  scanner routines run. The Start Sequence lives in os/session-start.md, which loads every session.
How to fill it: keep the mechanisms; swap [bracketed] references for your own tools, files,
  and issue tracker. Delete the italic authoring notes and this comment block when done.
-->

# Session Workflow Rules

Operational patterns that complement the constraints in operating-principles. Those govern
*what* to produce; these govern *how*.

A session runs in four movements: the Start Sequence orients it, the Framing and Entry gates
open a scoped piece of work, the Exit Gate closes that work, and the Close Sequence persists the
result and hands off. The Start Sequence lives in its own small file, `os/session-start.md`,
because it runs every session; everything else here loads when a session needs it. The
`session-start` and `session-end` skills are thin triggers for the first and last movements, so
each procedure has one copy to keep current.

---

## The Framing Gate

Before an agent starts a scoped piece of work, commit to the outcome it is meant to produce. A
build or execution planning artifact carries a `framing:` block in its frontmatter. Keep it to
three lines, never more (an outcome statement capped at three sub-fields, plus a falsifiable
success signal, so "did it work" stops being a subjective debate):

```yaml
framing:
  who: "<the user or segment this work serves>"
  what: "<the capability or behavior sought>"
  signal: "<a falsifiable 'we will know we are right when…' sentence>"
```

**Pass condition** (machine-checkable, not "someone approves"): all three sub-fields non-empty,
resolvable by a one-line frontmatter parse. Scope it to build/execution artifacts; a pure
research or audit note that produces no work product for a later step to act on does not need
its own gate.

*Authoring note: keep this a `framing:` block, not a body section, so the three-line cap is
structural. If a success signal needs more than one sentence, point it at whatever measurability
scaffold your instance uses rather than overloading the line.*

---

## The Entry Gate

Before execution starts on a scoped piece of work, file a three-line `entry_gate:` block once.
This is sized shaping, not a per-item checklist:

```yaml
entry_gate:
  scope: "<a named effort/appetite size, e.g. 'a session' or 'a multi-session arc'; never 'TBD'>"
  consumer: "<who or what consumes the finished work>"
  blocking_unknowns: "<named, or the literal string 'none'>"
```

**Pass condition:** all three sub-fields present and non-empty (the literal `none` counts). Keep
it a guideline fired once per scoped chunk, never a gate that blocks a work item until every box
is ticked. A readiness check taken that far becomes a waterfall step in agile's clothing. The
failure mode is the missing field, not the unknown; `shaping incomplete` is itself a valid,
recorded value.

*Authoring note: this is the opening bracket of the session lifecycle; the Exit Gate below is the
closing one. Delete this note when done.*

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

## Tools by Capability

Name the capability a step needs, never the server or connector that happens to provide it
today. "Read the open items from your issue tracker" survives a connector rename, a second
operator's different setup, and a move to another agent runtime; "call the tracker server's
search tool" breaks on all three. In skills, rules, and prompts:

- **State the capability:** issue tracker (read or write), memory store, design tool, browser,
  shell, version control host.
- **Check before relying on it:** the Start Sequence confirms at session start that something
  provides it.
- **Name the fallback:** what the step does when nothing does, usually a file in this
  repository (your handoff file, `os/project-state.yaml`). A step with no fallback says it will
  stop and ask.

Your instance's own list of capabilities and fallbacks lives in `os/session-start.md`, where the
Start Sequence checks it.

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

**Scale verification to blast radius, before the build and after it.** One rule, one ladder, so
plan checks and post-build checks never become two parallel procedures that drift apart.

*Before building,* verify the plan against the tree. Every count, path, version, status, and
"already done" or "not done yet" a plan asserts is a claim: re-derive each with the command that
would prove it, and classify every plan item as still open, already done, superseded, or
unverifiable before work starts. A plan written last week describes last week's tree.

*After building,* climb as far as the change warrants. When you build a new tool or logic module
(an extractor, a classifier, a normalizer, an adapter change), a passing seeded smoke is the
first rung, not the last. Second: run it against real or production-shaped data and read the
output for junk, since seeded tests prove the logic you imagined and real data reveals the cases
you did not. Third: an adversarial pass (malformed input, empty input, flag interactions, an
idempotent re-run), where every probe failure becomes a permanent test, not just a fix. Fourth,
for multi-file work: a fresh-context reviewer that did not write the change reads the diff
against the plan, tries to break it, and reproduces every numeric claim from its own runs before
the change is called done. Its findings are fixed in the same change, and each one is listed
under Fixes Applied. A one-line mechanical edit needs none of these; scale the ladder to what a
mistake would cost.

**Report the instrument, not just the number.** When a claim is a metric (a coverage ratio, a
benchmark score, a count over a set), name the harness, method, and sample that produced it, not
the number alone. A number without its instrument cannot be checked and reads as false precision.
This matters most when your instance authors its own eval or benchmark claims, where the
discipline is part of their credibility.

---

## Failure Recovery

When something in the operating layer itself goes wrong mid-session, stop the task, recover the
layer, then resume. Commits are the save points: commit before any risky step, so recovery is
returning to a known state rather than reconstructing one.

- **A file is corrupted or half-written** (a truncated YAML, a duplicated section, an edit that
  landed in the wrong place). Do not patch forward. Compare against the last commit, restore the
  file's last good content by editing it back, re-apply only the intended change, and re-run
  whatever parses or checks that file.
- **Two corrections contradict each other.** Do not pick one silently. Follow the one whose
  trigger matches the task more specifically, name the conflict to the operator, and record it
  for review so the registry gets fixed rather than worked around.
- **A skill produced bad output.** Discard the output, not the skill. Note what was wrong and
  which step produced it, finish the task by hand or by the procedure in the skill's own file,
  and record the failure where skill changes get reviewed. Never edit a skill mid-task to make
  its own output pass.
- **The session's own state is in doubt** (you are unsure which branch you are on, whether a
  step ran, or whether a file is yours). Stop and re-run steps 1 and 4 of the Start Sequence
  (`os/session-start.md`) before doing anything else.

In every case, the recovery itself goes under `## Fixes Applied` in the Exit Gate report.

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
`python3 os/status_lint.py` checks every artifact's status against this vocabulary, and
`python3 os/gen_index.py` generates a folder's index from the same frontmatter (`--check` fails on
a stale index), so no one hand-maintains an index that rots.

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

**Persist the report.** A report that lives only in the chat is gone when the chat is. Write it
where the next session will find it, every session:

- **Commit mode:** the newest entry of your handoff file, `os/handoff/<operator-id>.md`, under a
  `## YYYY-MM-DD · <title>` heading, with the slots as level-3 headings.
- **PR mode:** the pull request's body, with the slots as level-2 headings. Open the pull request
  first, then add a handoff entry whose body is the pull request's full link on its own line (one
  line per pull request when the session opened more than one), so the link is real when you
  write it.

Either way the slot names are exactly the ones above, so a check can find them by name. An entry
that carries `Findings Integration` or `Session Integrity` is read as Flavor B and must carry all
five; any other entry must carry the three Flavor A slots. `python3 keelson/close_check.py` checks
a persisted report's slots (`--pr-body` for a pull request body).

---

## The Session Close Sequence

The Exit Gate decides what the report says; this sequence decides where the work and the report
go. Run it in order at the end of every session that changed a tracked file.

1. **Review.** For a substantial session, run your integrity routine; for a small one, fill the
   Exit Gate slots directly.
2. **Persist.** Write the Exit Gate report as described above. The newest entry's Next Session
   Prompt is where your next session starts.
3. **Rotate.** If your handoff file now holds more than `operating_mode.handoff.keep_newest`
   entries (in `os/project-state.yaml`), move the oldest ones, unchanged and in order, to the
   top of the archive file the handoff names, so the archive stays newest first too. Write the
   archive before removing anything from the handoff. Move, never delete.
   `python3 os/handoff_rotate.py` reports what would move; `--apply` moves it.
4. **Close by mode.** Read `operating_mode.close_mode`:
   - `commit` (the default for a firm of one): commit the session's work with its envelope, the
     handoff entry included.
   - `pr` (opt-in PR-only close): commit on the session's own branch, push it, and open a pull
     request whose body is the Exit Gate report. Nothing is committed straight to the default
     branch. A change to a methodology-layer file (a skill, a rule, a protocol) goes in its own
     pull request for its approver, separate from engagement work, so it can be reviewed and
     reverted on its own.

   **In `pr` mode the order changes,** because the handoff entry links a pull request that has to
   exist first: (a) commit the session's work on its own branch and push it; (b) open the pull
   request, or one per approver when methodology and engagement work are split, each body
   carrying the Exit Gate report; (c) on the first pull request's branch, add one handoff entry
   whose body is the full link to each pull request, one per line; (d) rotate (step 3); (e) commit
   that entry and push it to the same branch. Until that pull request merges, the entry exists
   only on its branch, which is why the Start Sequence also reads your newest open pull request.
   Where nothing in the session can reach the version-control host, put the full Exit Gate report
   in the handoff entry instead of a link (the fallback Tools by Capability asks for).
5. **Leave no branch stranded.** A branch holding commits that are not on the remote default
   branch ends the session in one of three states: a pull request is open, the branch is pushed
   as a backup, or it is explicitly abandoned. Local-only commits are never an end state.

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
*Start Sequence: os/session-start.md · Handoffs: os/handoff/ · Operator profiles: os/operators/*
