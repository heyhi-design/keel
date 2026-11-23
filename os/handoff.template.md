---
# KEEL · CONFIGURATION TEMPLATE
# File: os/handoff.template.md
#
# What this is: one operator's handoff file. Each session that operator closes adds one entry
#   here: the persisted Exit Gate report, ending in the Next Session Prompt the next session
#   starts from. One file per operator, so two people (or one person's parallel sessions)
#   never stack their notes into a single growing log.
# When it loads: at session start, the newest entry only, for the operator running the session
#   (os/session-start.md, step 3). Older entries are read on demand.
# How to fill it: copy this file once per operator to os/handoff/<operator-id>.md (keep the
#   template; this is a per-person copy, like os/operators/). Set `operator`, delete this comment
#   block and the example entry, and let session close write the rest.
#
# The shape below is a contract other tools read. Keep it:
#   operator  string. The operator id from os/operators/<operator-id>.md.
#   archive   path. Where rotated entries go. Never deleted, only moved.
#   Entries   one level-2 heading per session, newest first:
#               ## YYYY-MM-DD · <one-line title>
#             with the Exit Gate slots as level-3 headings inside it, matched by name:
#               ### Fixes Applied / ### Smoke Test / ### Next Session Prompt
#               (plus ### Findings Integration and ### Session Integrity for Flavor B)
#             An entry carrying Findings Integration or Session Integrity is Flavor B and
#             carries all five slots; any other entry carries the three above.
#             In PR close mode an entry's body may instead be the full link of each pull request
#             the session opened, one per line; the pull request body carries the report.
#
# Rotation rule: keep the newest N entries in this file and move every older entry, unchanged
#   and in order, to the top of the archive file. N is `operating_mode.handoff.keep_newest` in
#   os/project-state.yaml (one setting for the instance, not one per file). Rotate at session
#   close, after writing the new entry. A rotation that would remove an entry without writing it
#   to the archive first is a defect: stop.
operator: "[operator-id]"
archive: "os/handoff/archive/[operator-id].md"
---

# Handoff · [operator-id]

*Newest first. One entry per closed session. The newest entry's Next Session Prompt is where the
next session starts.*

## [YYYY-MM-DD] · [one-line title of the session]

*Example entry: delete it once session close writes your first real one.*

### Fixes Applied

- [One line per fix, or "none this session, verified by <check>".]

### Smoke Test

- [What was run, and the result.]

### Next Session Prompt

[A copy-pasteable paragraph: what to load, where to start, the first concrete action. Written so
a fresh session with no memory of this one can resume.]
