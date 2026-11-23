# Examples

**Everything in this directory describes a firm that does not exist.**

The rest of this repository is templates, which means the rest of this repository is
`[BRACKETED SLOTS]`. Templates tell you what a field is called. They do not tell you how much
specificity a field wants, how long a filled section should run, or what a correction looks like
once it comes from something that actually went wrong twice. That is what this directory is for:
one worked instance, filled end to end, so you can see the shape of "done" before committing a
weekend to reaching it.

## What's here

[`baseline-year/`](baseline-year) — a one-person sustainability-reporting practice, invented for
this purpose. The founder, the firm, the clients, the decisions, and every mistake in the
corrections registry are made up. It is not a real practice, it is not anyone's actual voice or
services, and nothing in it is advice about sustainability reporting.

| File | Filled from | Worth looking at for |
|---|---|---|
| [`profile/company-profile.yaml`](baseline-year/profile/company-profile.yaml) | [`profile/company-profile.template.yaml`](../profile/company-profile.template.yaml) | How specific the voice and services fields want to be. Vague answers here are what produce generic agent output later. |
| [`os/agent-context.md`](baseline-year/os/agent-context.md) | [`os/agent-context.template.md`](../os/agent-context.template.md) | How short this file stays. It loads every session, so cutting matters more than covering. |
| [`os/decision-log.md`](baseline-year/os/decision-log.md) | [`os/decision-log.template.md`](../os/decision-log.template.md) | Two entries in ten months. A log that fills up fast is recording activity, not decisions. |
| [`os/corrections/corrections-registry.yaml`](baseline-year/os/corrections/corrections-registry.yaml) | [`os/corrections/corrections-registry.template.yaml`](../os/corrections/corrections-registry.template.yaml) | Four entries, one superseded. Trace that one against the decision-log entry of 2026-03-02 and the constraint in `os/agent-context.md`: promotion touches three files in one pass, and this is what it looks like when it was done properly. |
| [`skills/`](baseline-year/skills) | [`skills/templates/`](../skills/templates) | The five original starter skills, filled, plus a registry adjusted to describe them (the example predates `session-start` and `session-end`, added in 0.3.0). Notice how much of each one is firm-specific: the templates supply the shape and almost none of the content. |

Two skills also ship their filled `reference.md`. The
[`voice`](baseline-year/skills/voice/reference.md) one, because the sounds-like/doesn't-sound-like
pairs are the part of a voice reference that actually teaches. The
[`proposal`](baseline-year/skills/proposal/reference.md) one, because its approved
pricing-deferral language is a pre-send checklist item in that skill, and a rule you are told to
apply verbatim is not much use as an empty slot.

## What this example deliberately leaves out

It is a worked example, not a second copy of the scaffold. These files are referenced from inside
`baseline-year/` but not shipped with it, mostly because seeing them filled adds little you can't
get from the template. The `proposal` reference above is the exception that proves where the line
is: it ships precisely because its content is not derivable from an empty slot.

- `os/session-rules.md` — referenced by all five skills as the Exit Gate they close through. The
  Exit Gate *section* is the same for everyone; the file around it is not. Baseline Year runs a
  three-slot core: fixes applied, smoke test, what's next. `voice` and `intelligence-processor`
  close on exactly that. `proposal` adds findings integration, because a proposal is the thing
  most likely to expose a gap in the services list it was scoped from. `session-integrity` is the
  gate's reference implementation and closes on all of its slots. `project-scanner` claims a
  documented exemption, its report being the close-out artifact already. Four distinct positions
  across five skills, which is what a real one looks like.
- `os/operating-principles.md`, `os/project-state.yaml`, `os/dependency-graph.json`,
  `os/corrections/LIFECYCLE.md`.
- `references/review-checklist.md` (the reference material `session-integrity` carries), and the
  `reference.md` for the two skills other than `voice` and `proposal`.
- `skills/evals/*/cases.yaml`. The scaffold's own twenty cases are already concrete, and by its
  rules an unregistered, untested skill is a draft, so treat this example as showing what a
  filled skill *says*, not as a model of a fully shipped one.

So a pointer inside `baseline-year/` that resolves to nothing is expected, not a broken link. Every
one of them points at a real file in the scaffold above.

## Copy the templates, not these files

To set up your own instance, work from the template files in [`profile/`](../profile),
[`os/`](../os), and [`skills/templates/`](../skills/templates), or run the
[bootstrap prompt](../docs/bootstrap-prompt.md) and let your agent do it. Starting from
`baseline-year/` and editing over it means inheriting somebody else's decisions in the places you
forget to look, which is worse than starting from a blank slot, because a filled slot does not
look like a question.

**Do not deploy the example skills.** The five files under `baseline-year/skills/*/SKILL.md` carry
live frontmatter whose `name:` values (`voice`, `proposal`, `session-integrity`,
`project-scanner`, `intelligence-processor`) are exactly the ones you will deploy from
`skills/templates/`. Any runtime that discovers skills by walking the tree rather than by reading
a configured directory will find two skills claiming the same name, one of them belonging to a
sustainability consultancy that does not exist. Deploy from the templates and leave this directory
where it is.

## The file with no template: `CLAUDE.md` (Claude Code)

`docs/setup-guide.md` Step 4 has you write a `CLAUDE.md` at your **repository root**, and both
onboarding docs tell you to recheck it first when your agent starts a session cold. It has no
template anywhere, because its content depends on which runtime you are wiring into: a Cowork
setup has an always-loaded context file too, but not this file and not at this path.

It ships here as a snippet rather than as a file inside `baseline-year/`, deliberately. Claude Code
discovers `CLAUDE.md` by path, so a file sitting in a subdirectory would be loaded by any agent
working in that subtree, and no disclaimer can stop that, because the file is read before anyone
reads the disclaimer. A copy in the wrong place would also teach the wrong placement.

Here is what Baseline Year's looks like, filled from the same profile as everything else above:

```markdown
# Baseline Year Operating Context

@os/agent-context.md

## Binding constraints
@os/operating-principles.md

## Active corrections (load at session start)
At the start of every session, read the active entries of
os/corrections/corrections-registry.yaml and honor them. (Don't @import the whole file: that
pulls in superseded and retired entries too, and only the active ones should load.)

## Skill routing
Before loading any skill, run:
    python3 skills/registry/skill-registry.py "<the task, in a few words>" --confidence
Load only the top skill it returns (or, if it reports two close matches, ask which one).
Never load a skill you weren't routed to. This keeps each session's context small.

## The one rule that overrides everything
No disclosure gets written over an inventory this practice has not traced to source. Not for a
deadline, not for a good client, not as a favor. If a session drifts toward it, say so and stop.

## On demand (read when the task calls for it, not every session)
- Session close: os/session-rules.md (the Exit Gate)
- Ground truth: os/project-state.yaml
- Decisions, append only: os/decision-log.md
- Structure map: os/dependency-graph.json
```

The only firm-specific addition to the setup guide's skeleton is that one overriding rule, lifted
from the constraint the 2026-03-02 decision promoted into `os/agent-context.md`. That is the
calibration worth taking: a root context file earns its length by naming the thing you cannot
afford to have an agent forget, and almost nothing else.

## Why the fiction is deliberate

Filled content in a template repository is a hazard: someone finds it out of context, assumes it
is the real thing, and ships a stranger's positioning under their own name. So the example firm is
invented, every file in it opens with a visible note saying so (a rendered line, not an HTML
comment a markdown viewer would strip), and the pull request template treats filled content as
allowed **only** under `examples/`. Everything outside this directory stays a template.

If you contribute an example, hold the same line: invent the firm, say so visibly at the top of
every file, and keep it out of the template paths.

## Read next

- [`../README.md`](../README.md): what this repository is.
- [`../docs/three-layer-model.md`](../docs/three-layer-model.md): what it owns versus what your
  agent runtime provides. Worth reading before the setup guide.
- [`../docs/setup-guide.md`](../docs/setup-guide.md): placing and wiring the templates by hand.
