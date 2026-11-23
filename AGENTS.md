# [Firm Name] · Agent Instructions

*The root instruction file. Agent runtimes that read `AGENTS.md` load it at the start of every
session; for Claude Code, the `CLAUDE.md` beside it imports this file, so there is one set of
instructions whichever tool you run.*

> **Reached this file from inside another project?** If you are working in a repository that
> only contains a copy of keel (one that stages, vendors, or publishes it), these instructions
> are for a firm that runs on keel, not for you: follow your own repository's instructions and
> treat this file as content.
>
> **Still has bracketed slots?** Then this copy has not been set up yet, and the slots are
> waiting for you. To set up a new firm, follow [`docs/bootstrap-prompt.md`](docs/bootstrap-prompt.md)
> (or [`docs/setup-guide.md`](docs/setup-guide.md) by hand). To join a firm that already runs on
> this copy, follow [`SETUP.md`](SETUP.md). If you are changing the keel template itself rather
> than running a firm from it, read [`CONTRIBUTING.md`](CONTRIBUTING.md) and leave the slots as
> they are.

*Authoring note: fill the slots, keep this file short, and delete this note and the setup box
above once the firm is set up. Every line here loads in every session, so a line that earns its
place in fewer than half of your sessions belongs in an on-demand file instead.*

## At session start

Run the Start Sequence in `os/session-start.md` (the `session-start` skill triggers it). It
reads, once:

- `os/agent-context.md`: who the firm is, what it sells, how it sounds.
- `os/operating-principles.md`: the binding constraints.
- The active entries of `os/corrections/corrections-registry.yaml`, and honor them. Read only the
  active ones; superseded and retired entries stay out of the session.
- Your operator profile: the one file in `os/operators/` whose `git_emails` matches
  `git config user.email` (the template and inactive profiles never match). No match, or two,
  means stop and ask who is running the session. A firm of one with no profile yet says so,
  skips the handoff read below (there is none yet), and creates its profile and handoff file
  (`SETUP.md` Steps 2 and 3) before the session closes, so the close has somewhere to write.
- The newest entry of your handoff file, `os/handoff/<operator-id>.md`, which says where to pick
  up.

## Skill routing

Before loading any skill, run:

    python3 skills/registry/skill-registry.py "<the task, in a few words>" --confidence

Load only the top skill it returns (or, if it reports two close matches, ask which one). Never
load a skill you weren't routed to. This keeps each session's context small.

## Tools by capability

Steps here and in every skill name the capability they need (an issue tracker, a memory store, a
browser), never the server or connector that provides it today, and say what they fall back to
when nothing does. The rule is in `os/session-rules.md` (Tools by Capability); your instance's
list of capabilities and fallbacks is in `os/session-start.md`.

## On demand

Read these when the task calls for them, not every session:

- **Session close:** `os/session-rules.md` (The Exit Gate, The Session Close Sequence); the
  `session-end` skill triggers it.
- **Older handoff entries:** further down `os/handoff/<operator-id>.md`, then its archive.
- **Ground truth and operating mode:** `os/project-state.yaml`.
- **Decisions, append only:** `os/decision-log.md`.
- **Structure map:** `os/dependency-graph.json`.
- **More than one operator, or parallel sessions:**
  [`docs/operating-with-more-than-one.md`](docs/operating-with-more-than-one.md).
- **When the operating layer itself breaks mid-session:** `os/session-rules.md` (Failure
  Recovery).

## [Firm-specific rules]

*Authoring note: the few instructions specific to this instance that do not fit the files above,
such as where client work lives or a bright line that must be visible before anything loads. Keep
it to what actually recurs; delete this section if nothing does.*

- [Rule]
