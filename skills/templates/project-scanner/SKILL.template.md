---
name: "project-scanner"
# Keep name == this skill's folder name == its registry id. A firm prefix
# (like "acme-project-scanner") is fine only if the folder and registry id use it too.
description: >-
  [On-demand project pulse. Reads your tracking files and produces a status report: what's
  done, what's overdue, what's blocking, what needs attention. Use for a quick "where are we"
  check. Include at least three colloquial phrasings: see skills/README.md's
  colloquial-trigger rule.]
---

# [Your Firm] Project Scanner

A status pulse you can run any time without waiting for a scheduled review. Reads whatever files
you use to track work and produces one structured report: what's done, what's stale, what's
blocking, and where you actually are against your own timeline.

---

**Exit Gate.** This skill's report is itself the close-out artifact; it doesn't need the full Exit
Gate slots from `os/session-rules.md` unless the scan surfaces something that gets fixed
in the same session, in which case log the fix there too.

---

## Step 1: Get your bearings

Note the current date and, if useful, where that falls against your own timeline (a week number, a
phase, a launch countdown, whatever unit your `profile.timeline` uses). Derive this from your live
tracking files every time; never hardcode a date or a phase number into this skill itself; both
will be wrong the next time you run it.

## Step 2: Check recent activity

If you track work in version control, check what's actually landed recently (commits, merged
changes) as a baseline fact before reading anything else. This anchors the rest of the scan in
what actually happened, not just what tracking files claim happened.

## Step 3: Read your tracking files

Read whatever files you use to track state (a roadmap, a health tracker, a decision log, a
project-state file) in parallel, and check each against the others as you go:

- **Unprocessed intake.** Is there anything waiting to be read, decided on, or acted on that
  hasn't been touched yet?
- **Claimed vs. actual.** Does anything marked "done" have real evidence behind it (a merged
  change, a sent deliverable), or is the mark resting on intention?
- **Dashboard vs. detail.** If you keep both a summary view and a detailed one, do they agree?
  A stale summary is worse than no summary, because it reads as current.
- **Staleness.** Does any tracking file describe a state that's since changed elsewhere without
  being updated here?

## Step 4: External tracker (if you use one)

If you track work in a separate tool (an issue tracker, a project board) outside this repository,
reconcile against it here. Note any drift rather than assuming the two are in sync.

## Step 5: Verify counts

If any tracking file states a count (skills built, clients served, whatever your practice counts),
verify it against the actual live state rather than trusting a previously written number. Counts
drift the moment anyone forgets to update them by hand.

## Step 6: Scan for completed work

Look for anything genuinely finished since the last scan that hasn't been marked as such anywhere.
Completed work that isn't recorded as complete looks, from the outside, exactly like work that
never got done.

## Step 7: Compute your current position

State where you actually are against your own timeline, computed from what Steps 2 through 6 just
found, not from a previously recorded position. If your recorded position and your computed
position disagree, the computed one is the one to trust and the recorded one is a finding.

## Step 8: List blockers

What's actually stopping forward progress right now, distinct from what's merely unfinished?

## The report

Produce one structured report with named sections. Adjust this list to your own practice, but keep
it a fixed, scannable shape rather than free-form prose:

- **Where things stand**: the one-paragraph summary.
- **Current position**: computed, not recorded (Step 7).
- **Recent activity**: what actually landed (Step 2).
- **Unprocessed intake**: waiting for a decision or action (Step 3).
- **Claimed-vs-actual gaps**: anything marked done without evidence (Step 3).
- **Stale references found**: anything out of date (Step 3).
- **Completed but unrecorded**: anything finished but not marked as such (Step 6).
- **Blockers**: what's actually stopping progress (Step 8).
- **Counts, verified**: any count claims, checked against live state (Step 5).
- **What needs attention this week**: your own synthesis of the above, ranked.

## Optional: monitoring note

If something in this scan is worth watching over the next several scans rather than acting on
immediately, note it explicitly so future scans pick up the thread instead of rediscovering it
from scratch.

## Optional: before saving

If you keep dated snapshots of past scans, ask before saving one; not every scan is worth
permanently recording; but don't skip the question by default.

## Related files

- `reference.md` : the file map and report-section legend for your specific tracking files.
- `os/project-state.yaml` : one of the tracking files this skill reads.

---

**Exit Gate reminder:** if this scan surfaces something you fix in the same session, log that fix
through `os/session-rules.md`'s Exit Gate before closing.
