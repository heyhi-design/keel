---
name: "intelligence-processor"
# Keep name == this skill's folder name == its registry id. A firm prefix
# (like "acme-intelligence-processor") is fine only if the folder and registry id use it too.
description: >-
  [Take in new research, a finding, or an outside development, and figure out what it means
  for what you already have written down. Use when new information arrives that might change
  an existing document, decision, or plan. Include at least three colloquial phrasings: see
  skills/README.md's colloquial-trigger rule.]
---

# [Your Firm] Intelligence Processor

Takes something new (a piece of research, a competitor development, a finding from a client
conversation) and figures out what it implies for what you've already written down, without ever
silently rewriting anything.

See `reference.md` for the document-relationship map and the proposal template.

---

**Exit Gate.** Closes through `os/session-rules.md`'s Exit Gate: fixes applied (the
changes actually made once approved), a smoke test (did every touched document still make sense
afterward), and what's next.

---

> **Non-negotiable:** never write a change to an existing document based on new information
> without a reviewed proposal first. The one exception is adding a brand-new document that
> contradicts nothing; even then, say what you're doing before you do it.

## Step 1: Identify what kind of input this is

- **New research or a report** someone else produced.
- **A finding from your own work** (a client conversation, a session, a pattern you noticed).
- **An outside development** (a competitor move, a change in your market, a new tool).

## Step 2: Check what it touches

Load `os/dependency-graph.json` (once filled in) to see which of your documents relate to
this topic. If you haven't built that graph out yet, do a direct search across your project for
anything that touches the same subject.

## Step 3: Classify the impact, per document

For each document the new information touches, classify the relationship:

- **Contradicts**: the new information conflicts with what's written; the document needs a
  correction.
- **Extends**: the new information adds to what's written without conflicting; the document needs
  an addition.
- **Confirms**: the new information supports what's already written; no change needed, but worth
  noting where you tracked the confirming evidence, if you keep one.
- **Obsoletes**: the new information makes the document no longer relevant; it needs to be marked
  superseded, not deleted outright.

## Step 4: Write the proposal

Generate a dated Change Proposal (see the template in `reference.md`) covering every
document from Step 3, and present it for review before touching anything. Include, per document:
what would change, why, and which classification from Step 3 applies.

If nothing is actually impacted, say so explicitly ("reviewed against N documents, no changes
proposed") rather than silently doing nothing and leaving no trace that this input was processed
at all.

## Step 5: Review

Walk through four questions before approving:

1. Does every proposed change accurately reflect the new information?
2. Does anything proposed contradict a constraint in your operating principles?
3. Is the proposed change the smallest one that actually addresses the new information, or does it
   overreach?
4. Is anything missing: a document that should be on this list but isn't?

Iterate on the proposal until every question resolves cleanly. Don't apply a partially-approved
proposal.

## Step 6: Apply, in dependency order

Once approved, apply changes in the order your dependency graph implies: a document other things
depend on gets updated before the things that depend on it, so nothing downstream reads a
half-updated state partway through. Append a decision-log entry if the change is significant enough
to warrant one. Update any index or summary document that lists what exists.

## Handling edge cases

- **Multiple findings in one pass**: process each through Steps 1 to 6 independently; don't merge
  unrelated findings into one proposal.
- **A finding that implies a brand-new document, not a change to an existing one**: still write a
  short proposal (what the new document would contain, why it's needed) before creating it.

## Related files

- `reference.md` : the proposal template and the dependency-cascade ordering logic.
- `os/dependency-graph.json` : the document-relationship map Step 2 reads.
- `os/decision-log.md` : where significant applied changes get recorded.
- The `voice` skill: once a proposal is approved, anything written in Step 6 should still pass
  through your voice rules.

---

**Exit Gate reminder:** close through `os/session-rules.md`'s required slots once changes
are applied.
