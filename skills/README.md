# Authoring Skills

A skill is a procedure your agent can find and run: how to write in your voice, how to draft a
proposal, how to check a session's own work. This repository ships seven starter skills as
templates. This page is how to fill those in, and how to write your own once you need one these
don't cover.

## The SKILL.md / reference file split

Every skill separates procedure from knowledge:

- **`SKILL.md`** is the procedure: the steps to run, in order, with the decisions and branches
  spelled out. This is what your agent follows.
- **`reference.md`** (or a `references/` folder, once a skill's reference material is organized
  enough to want named subtopics rather than one flat file) is knowledge: word lists, templates,
  examples, lookup tables. This loads only when the skill needs it, not by default.

This split matters for the same reason the three-layer model does: procedure changes rarely,
knowledge changes often (a new word rule, a new example, a new service offering), and keeping them
in separate files means updating your knowledge doesn't mean re-reading or re-verifying your
procedure.

## The colloquial-trigger rule

A skill's frontmatter `description` is what your agent matches against a request to decide whether
this skill applies. Write it to cover two registers, not one:

- The formal ask: how you'd describe the task in a planning document.
- The colloquial ask: how you'd actually type it at the end of a long day, tired, in a hurry. At
  least three phrasings in this register.

If a skill only matches its own formal name, it won't fire when you actually need it, because
nobody asks for help the way a spec describes the task.

## When a skill earns existence

Not every repeatable task needs a skill. The test: has this specific kind of task come up two or
three times already, in a way where a written procedure would have made the second or third time
faster or more consistent than the first? If yes, it earns a skill. If it's a one-off, write the
procedure inline in the moment and move on. A skill folder for a task you'll do once is overhead
with no return.

## Registering a skill

A skill isn't done until it's registered where your agent can find it by search. This repository's
schema and search script live in `skills/registry/`; see [that folder's own
README](registry/README.md) for the registry format, the `not_for` field that keeps two similar
skills from colliding, and how to tune the scoring. Register every skill you deploy, including the
seven starter templates once you've filled them in, so your agent finds the right one by describing
the task rather than needing every skill loaded by default.

## Before you ship a skill

1. Validate: read through the procedure once as if you were an agent seeing it cold. Does every
   step make sense without you filling in a gap from memory?
2. Register: add it to the registry before you consider it done, not after.
3. Test: write at least a few eval cases (see `skills/evals/`) before trusting the skill on real
   work. An untested skill is a draft, not a deployed skill.

## Thin triggers over protocols

When a skill's job is to run a procedure that already lives in one of your `os/` files (a start
sequence, a close sequence), keep the skill thin: name the procedure, run it, report the result,
and never restate its steps. `session-start` (over `os/session-start.md`) and `session-end` (over
`os/session-rules.md`) are built this way. Two copies of one procedure drift apart; with one copy
and a pointer, the only thing left to keep current is the pointer itself.

## Name capabilities, not servers

Write a skill's steps against the capability they need ("read the open items from your issue
tracker"), never against the name of the server or connector that provides it today. Say what the
step falls back to when nothing provides it. `os/session-rules.md` (Tools by Capability) has the
rule; your instance's list of capabilities lives in `os/session-start.md`.

## The seven starter skills

| Skill | What it's for |
|---|---|
| `voice` | Writing in your firm's voice, consistently, across every piece of content. |
| `proposal` | Drafting a scoped proposal for a prospective engagement. |
| `session-integrity` | Checking a work session's own output for consistency and follow-through before calling it done. |
| `project-scanner` | Producing an on-demand status pulse: what's done, what's overdue, what needs attention. |
| `intelligence-processor` | Taking in new research or findings and proposing (never silently making) the changes they imply. |
| `session-start` | Orienting a session before real work: who is running it, where the last session stopped, which branch and tools it has. |
| `session-end` | Closing a session: persisting the Exit Gate report, rotating the handoff file, and closing by the instance's close mode. |

Each ships as a template under `skills/templates/<name>/`, with eval cases under
`skills/evals/<name>/cases.yaml`. Fill in the bracketed slots from your completed
`profile/company-profile.template.yaml` before registering any of them.

## A note on where deployed skills live

Each `SKILL.md` points at other files by path: its own `reference.md`, and shared files like
`os/session-rules.md` and `profile/company-profile.yaml`. Those paths resolve from your project
root, so the skills assume they run inside your project, where `os/` and `profile/` exist. For
Claude Code, deploying to `.claude/skills/<name>/SKILL.md` inside your project keeps them
reachable; keep each skill's reference material with it (a flat `reference.md`, or a `references/`
folder for the skills that ship one). If your runtime loads skills
from somewhere that can't see your project tree, update the `os/` and `profile/` pointers in each
skill to wherever those files actually live for you.
