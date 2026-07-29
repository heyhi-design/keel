---
name: "intelligence-processor"
description: >-
  Take in something new — a regulatory update, a revised emission factor, a standard-setter
  decision, a finding from a client engagement — and work out what it means for what's already
  written down, without silently rewriting anything. Also for "the new factors are out, what
  does that touch", "does this change anything for our clients", or "process this guidance".
---

# Baseline Year Intelligence Processor

> **Worked example — this firm does not exist.** "Baseline Year" and Sam Oyelaran are invented.
> This is `skills/templates/intelligence-processor/SKILL.template.md` filled in. Copy the
> template, not this file, and do not deploy this skill: its `name:` collides with the real one
> you will deploy. See [`examples/README.md`](../../../README.md).

Takes something new and works out what it implies for what is already written down, across the
practice's own documents and every live engagement. In a reporting practice this runs constantly:
factors get republished, guidance gets clarified, and a client's boundary changes without anyone
sending a notification. Missing the news is rarely the problem; reading it and never tracing it
to the four documents it invalidates is where this actually goes wrong.

See `reference.md` for the document-relationship map and the proposal template.

---

**Exit Gate.** Closes through `os/session-rules.md`'s Exit Gate: fixes applied (the changes
actually made once approved), a smoke test (does every touched document still reconcile), and
what's next.

---

> **Non-negotiable:** never change a figure, a methodology note, or a client-facing document on
> the strength of new information without a reviewed proposal first. The single exception is
> adding a brand-new document that contradicts nothing, and even then, say so before doing it.
> This is stricter than it sounds and it is the point: a factor update silently applied is
> indistinguishable, six months later, from an error.

## Step 1: Identify what kind of input this is

- **A regulatory or standards change**: a directive update, a new guidance note, a sector
  supplement, a change in what has to be disclosed or assured.
- **A data change**: republished grid factors, a revised emission factor, a corrected
  supplier-specific figure.
- **A finding from this practice's own work**: something learned in an engagement that
  generalizes past the client it came from.
- **A market development**: a competitor's approach, a tooling change, an assurance provider
  changing what they ask for.

The type matters because the blast radius differs. A data change touches every model; a
standards change usually touches methodology notes and one section of every report.

## Step 2: Check what it touches

Load `os/dependency-graph.json` (once you have filled it in) to find the related documents. If it
does not yet cover the area, search directly across the practice files and every live engagement
folder. Engagement folders
are outside version control, so a repository-only search is structurally blind to exactly the
documents most affected — search both, every time.

## Step 3: Classify the impact, per document

- **Contradicts**: conflicts with what is written; needs correction.
- **Extends**: adds without conflicting; needs an addition.
- **Confirms**: supports what is already there; no change, but note where the confirming evidence
  was recorded.
- **Obsoletes**: makes the document no longer relevant; mark superseded, never delete. Superseded
  methodology notes are evidence of what was believed at the time a figure was published, and
  that is exactly what gets asked about in an assurance window.

For a data change, add one more question per client: does this cross the recalculation threshold?
That answer decides whether this is an update or a restatement, and they are not the same
conversation.

## Step 4: Write the proposal

Generate a dated Change Proposal covering every document from Step 3. Per document: what would
change, why, and which classification applies. For anything client-facing, include what the
client has to be told and when — a change the client learns about from their assurance provider
rather than from here is a failure of this step regardless of how correct the change was.

If nothing is impacted, say so explicitly ("reviewed against N documents and 3 engagements, no
changes proposed") rather than leaving no trace this input was processed.

## Step 5: Review

1. Does every proposed change accurately reflect the new information, read from the primary
   source rather than a summary of it?
2. Does anything proposed contradict a constraint in the operating principles?
3. Is this the smallest change that addresses the new information, or does it overreach?
4. Is a document missing from the list? Check every live engagement, not just the practice files.

Iterate until all four resolve. Never apply a partially-approved proposal.

## Step 6: Apply, in dependency order

Apply in the order the dependency graph implies, so nothing downstream reads a half-updated state.
For a factor change the order is fixed: model → source map → methodology note → report prose →
client communication. Never the reverse; a client told about a change before the model reflects it
will ask a question nobody can yet answer.

Append a decision-log entry if the change is significant enough. Update any index or summary that
lists what exists.

## Handling edge cases

- **Several updates in one release** (the common case when factors republish): process each
  through Steps 1 to 6 independently. Bundling them into one proposal makes the review unreadable
  and hides the one that mattered.
- **An update that implies a new document rather than a change to an existing one**: still write a
  short proposal before creating it.
- **An update mid-engagement, after a figure has been shared with the client but before the report
  is filed**: this is the hard case. Process it the same way, but Step 4's client communication is
  not optional and is not deferred to the next scheduled check-in.

## Related files

- `reference.md` : the proposal template and dependency-cascade ordering.
- `os/dependency-graph.json` : the document-relationship map Step 2 reads.
- `os/decision-log.md` : where significant applied changes get recorded.
- The `voice` skill: anything written in Step 6 still passes through the voice rules.

---

**Exit Gate reminder:** close through `os/session-rules.md`'s required slots once changes are
applied.
