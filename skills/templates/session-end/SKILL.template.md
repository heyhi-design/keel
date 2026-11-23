---
name: "session-end"
# Keep name == this skill's folder name == its registry id. A firm prefix
# (like "acme-session-end") is fine only if the folder and registry id use it too.
description: >-
  [Close a work session and hand it off: write the Exit Gate report somewhere tracked (the
  operator's handoff file, or the pull request body in PR mode), rotate the handoff file, and
  close the work by the instance's close mode so no branch is left stranded. Use when you are
  done for now and want the next session to pick up cleanly. Include at least three colloquial
  phrasings: see skills/README.md's colloquial-trigger rule.]
---

# [Your Firm] Session End

A thin trigger. The procedure is The Session Close Sequence in `os/session-rules.md`; this skill
runs it and reports the result. The review of the session's own output belongs to
`session-integrity`, which this skill calls for a substantial session rather than repeating.

---

**Exit Gate.** This skill is where the Exit Gate report stops being chat and becomes a record. It
does not decide what the report says (`session-integrity` and `os/session-rules.md` do); it decides
where the report and the work go.

---

## Step 1: Review, scaled to the session

For a substantial session (more than a small mechanical change), run `session-integrity` and take
its Phase 8 report as the Exit Gate report. If this session already ran `session-integrity` (it
hands its report here at its Phase 9), use that report and do not run it again. For a small one, fill the Exit Gate slots from
`os/session-rules.md` directly. Either way every required slot is present; an empty slot says why
it is empty.

## Step 2: Persist the report

Read `operating_mode.close_mode` in `os/project-state.yaml`.

- **`commit`:** add the report as the newest entry of your handoff file,
  `os/handoff/<operator-id>.md`, under a `## YYYY-MM-DD · <title>` heading with the slots as
  level-3 headings.
- **`pr`:** the report becomes the pull request body, with the slots as level-2 headings, and the
  handoff entry is a link to it. The order (commit, push, open the pull request, then the entry,
  then rotate) is in The Session Close Sequence, `pr` mode, in `os/session-rules.md`; follow it
  there rather than from this summary.

Never leave the report only in the chat.

## Step 3: Rotate the handoff file

If the file now holds more entries than `operating_mode.handoff.keep_newest`, move the oldest
entries, unchanged and in order, to the archive file the handoff names. Write the archive before
removing anything from the handoff. Never delete an entry.

## Step 4: Close by mode

Follow step 4 of The Session Close Sequence for the instance's close mode. In `pr` mode, keep any
change to a methodology-layer file (a skill, a rule, a protocol) in its own pull request for that
file's approver.

## Step 5: Confirm nothing is stranded

Name the branch's end state: pull request open (give its link), pushed as a backup branch, or
explicitly abandoned. A branch with commits that exist only on this machine is not an end state;
fix it before you stop.

## Step 6: Report the close

Tell the operator, in a few lines: where the report was written, whether rotation moved anything,
what was committed or opened, and the Next Session Prompt.

## Related files

- `os/session-rules.md` : The Exit Gate and The Session Close Sequence, the procedure this skill
  triggers.
- `os/handoff/` : the per-operator handoff files Steps 2 and 3 write.
- `os/project-state.yaml` : `operating_mode`, which sets the close mode and the rotation number.
- `skills/templates/session-integrity/` : the review Step 1 calls for a substantial session.
