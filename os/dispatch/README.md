<!--
KEEL · CONFIGURATION TEMPLATE
File: os/dispatch/README.md
What this is: the anatomy of a dispatch prompt - a fully self-contained work order an agent can
  execute in a fresh session with no prior conversation. This is your delegation pattern: it is
  how you hand a bounded task to an unattended agent and trust the result.
When it loads: on demand, when you write or run a dispatch prompt.
How to fill it: this is a mechanism doc plus a fillable ENV CHECK. Adjust the ENV CHECK to your
  own workspace path and runtime, then delete this comment block.
-->

# Dispatch System - Reference

A dispatch prompt is a self-contained work order: everything an agent needs to complete a
defined task in a fresh session with no prior context. You write dispatch prompts; agents
execute them.

---

## What dispatch is for

Dispatch fits tasks where:

- The output is a document or a decision record, not a send, a schedule, or a live action.
- The source material already exists in your workspace (the agent can read everything it needs).
- The constraints are fully knowable from files (no mid-run judgment call from you).
- The work can run asynchronously. You do not need to be present.

Dispatch is not for: sending messages, scheduling with other people, financial inputs, or
anything requiring credentials or live machine access.

---

## ENV CHECK - required at the top of every dispatch prompt

A fresh session may not have your workspace connected. Put a short check at the very top so the
agent verifies its environment before doing any work. Fill in your own root path and identity
file:

```
─── ENV CHECK (complete before anything else) ────────────────────────────────
Read the file at: [ABSOLUTE PATH TO YOUR PROJECT ROOT]/[YOUR IDENTITY FILE]

IF it loads (you see your project's instructions): proceed to MISSION below.

IF you get any error:
  STOP. Report: "ENV ERROR: cannot read [path]. Confirm the workspace is connected/mounted,
  then run this prompt again." Do not attempt any further steps.
──────────────────────────────────────────────────────────────────────────────
```

Point it at a medium-size file that is always present at your root and whose first line is a
recognizable identity check.

---

## Prompt anatomy - all six sections required

Every dispatch prompt contains these sections, in this order.

### MISSION
One directive. What the agent must produce. Specific, not aspirational. "Append one decision
entry documenting X," not "help with the decision log."

### CONTEXT LOAD
An ordered list of files to read before writing anything. For each: the path, what to extract
from it (not just "read this"), and any constraint on how to interpret it. Order matters: source
files before derivative files, constraint files before content files.

Include this standing directive once, after the file list, so a sub-agent does not falsely
declare a path missing:

> Before declaring any cited path missing or unreadable, run a glob against the canonical path
> and report the result. The glob is the source of truth, not partial inferences from earlier
> reads.

### OUTPUT SPEC
The exact delivery: file path, format, any required frontmatter, classification mark, an honest
length range, and the section structure if prescribed. If the output edits an existing file,
say "append only" or "edit in place" and name the exact location.

### CRITICAL CONSTRAINTS
The non-negotiable rules. Include your standing voice and classification constraints, then add
the task-specific ones beneath them.

### SMOKE TESTS
Specific, verifiable checks the agent runs before marking the task done. A smoke test is binary:
it passes or it does not. "Search the output for the banned term; if it appears outside a
citation, rewrite" is a smoke test. "Make sure it sounds good" is not. Aim for at least four;
use six to eight for high-stakes output.

### QUALITY GATE
A single paragraph stating what "done" looks like, written as a checklist the agent can verify.
The task is not done until every item is met.

---

## Execution status - frontmatter convention

Every dispatch file carries a `status:` frontmatter field so a scanner can tell open work from
done work.

| Value | Meaning |
|---|---|
| `pending` | Not yet run. |
| `partial` | Some prompts in a multi-prompt file are done; others remain. |
| `done` | All prompts run. |
| `archived` | Superseded or no longer relevant. Do not run. |

Update this field when a prompt runs. An unflipped status is a stale trigger the next scan
re-fires on.

---

## Writing new dispatch prompts

Write the prompt in the same session that surfaces the work, not later. The moment the work is
understood is the lowest-cost time to specify it. Confirm it is dispatch-eligible, add a
`## DISPATCH-NN: [Short Title]` header, write the six-section block, and prepend the ENV CHECK if
it runs first.
