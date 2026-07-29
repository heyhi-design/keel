<!--
KEEL · CONFIGURATION TEMPLATE
File: os/decision-log.template.md

What this is: the append-only record of your firm's significant decisions. It is the semantic
  memory of WHY the firm is shaped the way it is. Paired with the corrections registry, it is
  durable institutional memory that compounds without a growing headcount, and it needs no
  database: two files on disk are enough to start.
When it loads: on demand, when a session needs to know why a prior decision was made, or at
  close when a session made a decision worth recording.
How to fill it: delete the example entry below and start your own. Keep the append-only rule.
  Delete this comment block when done.
-->

# [Firm Name] Decision Log

**Append-only. The permanent record of this firm's significant decisions.**

**Start date:** [date]

---

## The rules

1. **Append-only.** Never edit an existing entry. Add new ones. The one exception is a security
   redaction (removing a leaked secret): edit in place, then record the redaction in a new
   appended entry so the edit is never silent.
2. **Newest-first.** Prepend new entries directly under the `## Entries` heading below.
3. **Read before you write.** Before appending, read the last few entries to check for overlap
   or a decision this one supersedes.
4. **Log decisions, not activity.** An entry earns its place when it changes the direction of
   the work: an architectural choice, a positioning call, a product decision, a boundary ruling.

---

## Entries

<!-- Prepend new entries directly below this line, newest first. -->

## [YYYY-MM-DD] - [scope] [Short title of the decision]

**Type:** [direction | execution | research | convergence] · **Criticality:** [low | medium |
high] · **Contributor:** [who decided / who wrote this up]

### What We Had
[The situation before this decision. What was unresolved, and why it needed a call.]

### What Changed
[What was done or investigated that produced the decision.]

### What We Decided
[The decision itself, stated plainly, with the rationale. This is the part a future reader
comes for.]

### Documents Affected
[Which files this decision creates, edits, or supersedes.]

### Open items (carry forward)
[Anything this decision leaves for a later session to resolve.]

---

*Delete the example entry above once you have written your first real one.*
