---
name: "project-scanner"
description: >-
  On-demand pulse across every live client engagement and the practice's own state. Produces one
  report: what's done, what's overdue against a reporting deadline, what's blocked waiting on a
  client, what needs attention this week. Also for "where am I", "catch me up", "what's on fire",
  or "what did I forget".
---

# Baseline Year Project Scanner

> **Worked example — this firm does not exist.** "Baseline Year" and Sam Oyelaran are invented.
> This is `skills/templates/project-scanner/SKILL.template.md` filled in. Copy the template, not
> this file, and do not deploy this skill: its `name:` collides with the real one you will
> deploy. See [`examples/README.md`](../../../README.md).

A pulse across every live engagement, runnable any time. The thing this practice is actually
exposed to is a fixed external deadline it does not control, so the scan is organized around
distance to each client's reporting date rather than around task lists.

---

**Exit Gate.** This skill's report is itself the close-out artifact. It doesn't need the full
Exit Gate slots from `os/session-rules.md` unless the scan surfaces something fixed in the same
session, in which case log that fix there too.

---

## Step 1: Get your bearings

Note today's date and, for each live engagement, the weeks remaining until that client's
mandatory reporting date and until their assurance window opens. Derive both from the engagement
files every time. Never hardcode a date or a client's phase into this skill; both are wrong by
the next run.

## Step 2: Check recent activity

Check what actually landed since the last scan: commits in the OS repository, and the modified
dates on each live client's inventory model and boundary log. This anchors the scan in what
happened rather than what the notes claim happened.

## Step 3: Read the tracking files

Read in parallel and check each against the others:

- **Per engagement:** the engagement intake, the boundary log, the gap register, and the findings
  list if a review is open.
- **Practice-level:** `os/decision-log.md` for anything decided but not yet propagated, and
  `os/corrections/corrections-registry.yaml` for entries that fired recently.

Check for:

- **Unprocessed intake.** Client data received and not yet loaded. This is the most common form
  of silent slippage here, because receiving the file feels like progress.
- **Claimed vs. actual.** Is anything marked done backed by something real — a reconciled model,
  a sent draft — or is it resting on intention?
- **Waiting on the client.** Anything blocked on a client response, with how long it has been
  waiting. Past two weeks this stops being "waiting" and becomes a thing to escalate.
- **Staleness.** Any gap register describing a gap that has since been closed or widened.

## Step 4: External tracker

None. This practice tracks work in the engagement files and a calendar. Noted so a future reader
knows the absence is deliberate.

## Step 5: Verify counts

Anything stated as a count gets checked against live state: number of live engagements, open
findings per engagement, gaps closed versus opened this cycle. Counts drift the moment anyone
forgets to update one by hand, and a stale count in a client-facing progress note is a small
credibility leak.

## Step 6: Scan for completed work

Look for anything genuinely finished since the last scan and not marked as such. Finished work
that isn't recorded looks, from outside, exactly like work that never got done — including to
the client deciding whether to renew.

## Step 7: Compute your current position

For each engagement, state where it actually is against that client's reporting date, computed
from Steps 2 through 6. If the computed position and the recorded position disagree, the computed
one is right and the recorded one is a finding.

## Step 8: List blockers

What is actually stopping progress right now, as distinct from what is merely unfinished. In this
practice a blocker is almost always one of three things: data the client has not sent, a decision
the client has not made, or a factor publication not yet released.

## The report

- **Where things stand**: one paragraph.
- **Per engagement**: computed position, weeks to reporting date, weeks to assurance window.
- **Recent activity**: what actually landed.
- **Unprocessed intake**: received and not yet loaded, with age.
- **Waiting on client**: with age, flagged past two weeks.
- **Claimed-vs-actual gaps**: marked done without evidence.
- **Stale references found**.
- **Completed but unrecorded**.
- **Blockers**: what is actually stopping progress.
- **Counts, verified**.
- **What needs attention this week**: ranked, and ranked by deadline distance rather than by size.

## Optional: monitoring note

Anything worth watching across several scans rather than acting on now goes in a named note, so
the next scan picks up the thread instead of rediscovering it. Current standing item: whether
three retained clients is the ceiling for one person through a Q1 crunch, which is a question
about capacity that only answers itself across a full cycle.

## Optional: before saving

Ask before saving a dated snapshot. Not every scan is worth keeping, but the question gets asked
rather than skipped by default.

## Related files

- `reference.md` : the file map and report-section legend for this practice's tracking files.
- `os/project-state.yaml` : practice-level state this skill reads.

---

**Exit Gate reminder:** if this scan surfaces something fixed in the same session, log that fix
through `os/session-rules.md`'s Exit Gate before closing.
