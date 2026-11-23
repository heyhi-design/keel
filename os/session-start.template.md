<!--
KEEL · CONFIGURATION TEMPLATE
File: os/session-start.template.md

What this is: The Session Start Sequence, the short procedure that orients every session before
  its first piece of real work, plus the list of capabilities your instance relies on. It is
  kept in its own small file, apart from os/session-rules.md, because it runs every session
  while the session rules load only at close.
When it loads: at the start of every session, triggered by the session-start skill or by your
  root instruction file (AGENTS.md).
How to fill it: fill the capability list at the bottom, keep the steps, delete the italic
  authoring notes and this comment block when done.
-->

# Session Start

Run in order, before the first piece of real work. Each step either passes or says out loud why
it was skipped.

1. **Who is running this session.** Look in `os/operators/` at every profile except the
   template itself (`*.template.md`) and any profile with `status: inactive`. If the folder
   holds no profile at all (the template aside), this is a firm of one that has not made a
   profile yet: skip this step and step 3, say so,
   and create the profile and the handoff file (`SETUP.md` Steps 2 and 3) before the session
   closes, because the Close Sequence writes to that handoff file. Otherwise match
   `git config user.email` against each profile's `git_emails`. Exactly one match: load that
   profile. Zero or two: stop and ask who is running the session. Never fall back to a default
   identity, because a default silently hands one person's preferences and approval rights to
   another. `python3 os/resolve_operator.py` runs this check and exits nonzero, by name, on zero
   or two matches.
2. **The always-loaded core.** Your root instruction file (`AGENTS.md`) names it. Read it once.
3. **Where the last session stopped.** Read the newest entry of your own handoff file,
   `os/handoff/<operator-id>.md`. In PR close mode, also look at your own newest open pull
   request: its entry only reaches the default branch when it merges, so if it is newer than
   your newest handoff entry, its body is where you stopped. Read another operator's handoff
   only when the task needs it.
4. **Where you are.** Name the branch and worktree you are on, whether the tree is clean, and
   whether it is behind the remote default branch (fetch first). If it is behind, read the files
   you are about to rely on from the remote ref, not the local copy. If the task names a branch,
   confirm you are on it; if not, stop and resolve which one you are working in.
5. **What tools you have.** For each capability the task needs (the list below), confirm
   something in this session provides it. Where nothing does, use the fallback and say so.
6. **In few-person mode only** (`operating_mode.operators: few` in `os/project-state.yaml`):
   confirm which files this session owns and which id block it may use, per
   `docs/operating-with-more-than-one.md`. A session that needs a file it does not own reports
   the edit it needs instead of making it.

*Authoring note: keep this list short. Every step here runs in every session, so a step that
earns its place in fewer than half of your sessions belongs in a skill instead.*

## Capabilities this instance relies on

Each line names a capability, never the server or connector that provides it today, and what a
step does when nothing provides it (the rule is in `os/session-rules.md`, Tools by Capability).

*Authoring note: list the capabilities your instance actually uses and delete the rest. Common
ones: issue tracker (read or write), memory store, design tool, browser, shell, version control
host.*

- **[Capability]:** [what it is used for] · fallback: [a file here, or "stop and ask"]
