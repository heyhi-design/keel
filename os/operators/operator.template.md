---
# KEEL · CONFIGURATION TEMPLATE
# File: os/operators/operator.template.md
#
# What this is: one operator's profile. An operator is a person who runs agent sessions on
#   this instance. A session finds its operator by matching `git config user.email` against
#   the `git_emails` list below, so a second person never inherits the first person's
#   preferences or approval rights by accident.
# When it loads: at session start (os/session-start.md, step 1). Only the matching profile
#   loads; other operators' profiles stay on disk. The resolver ignores this template itself
#   (any *.template.md) and every profile with `status: inactive`.
# How to fill it: copy this file once per operator to os/operators/<operator-id>.md (the one
#   exception to the rename rule: keep this template, copy it per person). Replace every
#   [BRACKETED SLOT], then delete this comment block. A solo instance fills one copy.
#
# The shape below is a contract other tools read. Keep the key names and types:
#   operator    string. Your operator id, kebab-case. It names this file and your handoff file,
#               os/handoff/<operator-id>.md (that path is derived, so it is not a field here).
#   name        string. How sessions address you.
#   pronouns    string. Leave empty if you prefer not to state them.
#   git_emails  list of strings. Every address you commit with; compared to
#               `git config user.email` exactly, ignoring case. Exactly one profile may match a
#               session. Zero matches or two matches means stop and ask, never a default.
#   role        founding | member. Descriptive: who founded the instance. It grants nothing by
#               itself; approval comes only from `approves` and from a file's `approver:`.
#   approves    list drawn from: methodology | engagement | hybrid. The layers this operator may
#               approve a change to when a file names no `approver:` of its own. The one approval
#               rule is in docs/operating-with-more-than-one.md (Who owns what). The founding
#               operator's profile usually lists all three, because an untagged file needs an
#               approver who approves all three layers.
#   status      active | inactive. An inactive profile stays for the record and never matches.
operator: "[operator-id]"
name: "[Your name]"
pronouns: "[pronouns]"
git_emails:
  - "[you@example.com]"
role: "[founding | member]"
approves:
  - "[engagement]"
status: active
---

# [Your name] · Operator Profile

*Loaded at session start for the operator whose git email matches. Everything below is personal
to this operator. Facts the whole firm depends on belong in a shared file, not here.*

## How to work with [Your name]

*Authoring note: the highest-value slot. How a capable collaborator should behave with you
specifically: how you think and move, what "useful" means to you, what to surface without being
asked, how much to push back and from what standing.*

- [How you think and move; what "useful" means here.]
- [What to surface proactively vs. what to just do.]
- [How much to push back, and from what standing.]

## Preferences

*Authoring note: working preferences a session should honor for you and no one else. A preference
that should hold for every operator is a firm rule: put it in os/operating-principles.md instead.*

- **Review style:** [how you like changes presented: a diff, a summary first, a PR].
- [Anything else a session should do differently for you. The close mode is an instance setting
  in os/project-state.yaml, not a personal one.]

## Approval rights

*Authoring note: say in words what the `approves` list above means for you, and anything it
does not cover. The list is what tools read; this section is what a person reads.*

- [What you may approve without anyone else, e.g. "engagement files for the projects I run".]
- [What needs someone else's approval, and whose.]
