---
name: "session-start"
# Keep name == this skill's folder name == its registry id. A firm prefix
# (like "acme-session-start") is fine only if the folder and registry id use it too.
description: >-
  [Orient a new work session before any real work: confirm who is running it, load the
  always-loaded core, pick up where the last session stopped, and check the branch, worktree,
  and tools. Use at the start of every session. Include at least three colloquial phrasings:
  see skills/README.md's colloquial-trigger rule.]
---

# [Your Firm] Session Start

A thin trigger. The procedure is the Start Sequence in `os/session-start.md`; this skill runs it
and reports the result. It does not restate the steps, so there is one copy to keep current: if
the sequence changes, change it there.

---

**Exit Gate.** This skill opens a session rather than closing one, so it has no Exit Gate slots of
its own. Its orientation report is the first thing the session's eventual Exit Gate report can
point back to.

---

## Step 1: Run the sequence

Open `os/session-start.md` and run the Start Sequence in order. For each step, record one line:
passed, or skipped and why. Two steps stop the session rather than letting it guess:

- Profiles exist but none matches `git config user.email`, or more than one does (the template
  and inactive profiles never count). Ask who is running the session. Never pick one.
- The task names a branch or worktree and the session is not on it. Resolve which one before
  any edit.

## Step 2: Check capabilities, not tool names

For each capability the task will need, confirm something in this session provides it, using the
capability list in `os/session-start.md`. Where nothing does, say which fallback the session will
use instead. Never refer to a capability by the name of the server or connector
that provided it last time.

## Step 3: Report the orientation

Give the operator a short report before starting work:

- **Operator:** the matched profile, or "solo, no profile" if the instance has none yet.
- **Picking up from:** the newest handoff entry's title and its Next Session Prompt, in one line
  (in PR close mode, your newest open pull request's report if it is newer).
- **Where:** branch, worktree, clean or dirty, and how far behind the remote default branch.
- **Tools:** each needed capability, and its provider or fallback.
- **Few-person mode:** the files this session owns and its id block, or "solo mode".

Then wait for the operator's go-ahead if anything above stopped the sequence; otherwise begin.

## Related files

- `os/session-start.md` : the Start Sequence and the capability list, the procedure this skill
  triggers.
- `os/session-rules.md` : Tools by Capability, the rule the capability list follows.
- `os/operators/` : the operator profiles Step 1 matches against.
- `os/handoff/` : the handoff files Step 1 reads from.
- `docs/operating-with-more-than-one.md` : what changes in few-person mode.
