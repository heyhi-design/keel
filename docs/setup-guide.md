# Setup Guide

This is the standup sequence: how to go from a fresh copy of this repository to a working first
session. Read `docs/three-layer-model.md` first if you haven't; it explains what each step below
is actually doing.

Prefer to have your agent do this for you? `docs/bootstrap-prompt.md` is a single prompt you paste
into your agent inside your own copy of the repository; it runs every step below and proves each
one worked. This guide is the by-hand path, and the reference for what the bootstrap prompt is
doing under the hood.

## A note on filenames: the rename rule

Every file with `.template` in its name is a fill-in-place template. When you fill one in, drop
`.template` from the filename: `agent-context.template.md` becomes `agent-context.md`,
`company-profile.template.yaml` becomes `company-profile.yaml`. Files without `.template`
(`LIFECYCLE.md`, `seed-corrections.yaml`, `intake-conversation.md`) you keep as they are. The
templates already refer to one another by their final (post-rename) names, so renaming is all you
do: drop `.template` from each filename and nothing else needs repointing. (The only places a
`.template` name is written on purpose are the few lines that explain this rename itself, such as
in `os/corrections/LIFECYCLE.md`.)

## Step 0: Verify your own environment

Before filling in anything, confirm the basics work:

- Your agent tool (Claude Code, Cowork, or your chosen runtime) runs and can read and write files
  in this copy of the repository.
- **Python 3.9 or newer**, if you intend to run the registry search or the test suite. Both are
  tested through Python 3.14, and CI covers 3.9, 3.11, and 3.13. This repository is not a package
  you install, so there is no `pip install .` step and no version constraint to satisfy beyond the
  interpreter itself; the two `requirements*.txt` files cover the test suite's own dependencies.
- If you're standing this up **inside an employer's or client's environment** rather than for your
  own independent practice, stop here and read their tooling and data-handling policy first. Confirm
  which content is permitted into which tools, under which account, before you paste anything of
  theirs into an agent session. A missing written policy is a question to ask, not a green light.
  This step matters more than it looks: getting it wrong is the one mistake in this whole setup
  that isn't easily reversible.
- If you're standing this up for your own practice and nobody else's policy governs your
  environment, this step is a one-line check: confirm your tools authenticate and move on.

**You know it worked when:** you can ask your agent to open this repository's `README.md` and it
shows you the contents. If it can't reach the files, fix that before going further.

## Step 1: Fill in your profile

Open `profile/company-profile.template.yaml` and fill in every field: your identity, your voice,
your services, and your constraints. If you'd rather talk it through than fill in YAML directly,
work through `profile/intake-conversation.md` instead. It asks the same questions as a guided
self-interview, and you (or your agent) can transcribe the answers into the YAML afterward.

Don't skip fields to come back later. A half-filled profile produces a half-oriented agent, and
the gaps tend to surface as inconsistent output rather than an obvious error.

If a field leaves you wondering how specific to be, `examples/baseline-year/profile/company-profile.yaml`
is the same file filled in for a fictional practice. The whole worked instance is in
`examples/`, and the profile is the one most worth reading before you start: almost everything
downstream is parameterized by it.

**You know it worked when:** your filled `company-profile.yaml` has no remaining empty `""` or `[]`
fields you meant to fill. Ask your agent to list any that are still blank. Point it at the file by
exact path rather than by basename: `examples/` holds a second `company-profile.yaml` (along with
an `agent-context.md`, a `decision-log.md`, and a `corrections-registry.yaml`), and the paragraph
above has just sent you there to read it.

## Step 2: Fill in the configuration templates

Fill in each `os/` template's bracketed slots using your completed profile, and rename each one per
the rename rule above:

- `os/agent-context.template.md` becomes your agent's always-loaded identity file.
- `os/operating-principles.template.md` becomes your binding constraints file.
- `os/session-rules.template.md` becomes your session workflow, including the Exit Gate.
- `os/decision-log.template.md` becomes your append-only decision record, started empty.
- `os/project-state.template.yaml` and `os/dependency-graph.template.json` become your ground-truth
  anchor and structural map, also started empty.
- `os/corrections/corrections-registry.template.yaml` becomes your corrections memory. It ships
  with **zero entries** by design. `os/corrections/seed-corrections.yaml` holds five
  framework-level starter corrections; merge the ones you want into your registry and recompute its
  `meta` counts (the bootstrap prompt does this merge and recount for you).

Not all seven of these load the same way. Three form your **always-loaded core**, read at the start
of every session: `agent-context`, `operating-principles`, and the active entries of your
`corrections-registry`. The other four are **on-demand** files your context file points at, read
only when a task needs them: `session-rules` (at session close), `decision-log`, `project-state`,
and `dependency-graph`. You fill in all seven the same way; the difference is only when each gets
loaded, and Step 4 is where you wire that up.

**You know it worked when:** none of the `os/` templates you filled still hold a `[BRACKETED SLOT]`.
Ask your agent to scan the files you filled for leftover template brackets; it can tell a real slot
like `[Firm Name]` from a legitimate empty `[]` array or a Markdown link. Skip
`os/corrections/seed-corrections.yaml` and `os/dispatch/`, which keep their example brackets on
purpose until you use them. Keep the scan scoped to the files you filled: `examples/` legitimately
carries bracket-like strings and `.template` references (it explains which template each example
file was filled from) and is not part of your instance, so a wider scan reports defects that
aren't.

## Step 3: Fill in and register your skills

Fill in the five starter skills under `skills/templates/` from your profile, renaming each
`SKILL.template.md` to `SKILL.md` (and `reference.template.md` to `reference.md`) per the rename
rule. Then register them in `skills/registry/skill-registry.yaml` (rename it from
`.template.yaml`) so your agent finds the right one by search instead of loading all of them into
every session. The registry already ships an entry for each of the five starters; adjust each
entry's wording and its `location` to where you deploy the skill (Step 4). See `skills/README.md`
for the authoring standards these skills follow, and for how to add a new one later.

**You know it worked when:** `python3 skills/registry/skill-registry.py --registry
skills/registry/skill-registry.yaml --list` runs without error and lists your skills, and
`--stats` reports a token figure without a traceback.

## Step 4: Wire it into your runtime

This is the step that turns a filled-in folder into a running system. A scaffold no runtime reads
is just a folder; this is how your agent tool actually loads it. The wiring is specific to your
runtime.

### Claude Code

Claude Code reads a file named `CLAUDE.md` at your repository root at the start of every session,
and it loads skills from `.claude/skills/<name>/SKILL.md`. That is the whole wiring. Two moves:

1. **Create a `CLAUDE.md` at the repository root** that points Claude Code at your filled-in `os/`
   files. Because it loads every session, keep it short and let it reference the rest. Claude Code
   supports `@relative/path` import lines that pull a file's contents in at load time; if you'd
   rather not use imports, list the files in prose and tell the agent to read them. A worked
   example:

   ```markdown
   # [Your Firm] Operating Context

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

   ## On demand (read when the task calls for it, not every session)
   - Session close: os/session-rules.md (the Exit Gate)
   - Ground truth: os/project-state.yaml
   - Decisions, append only: os/decision-log.md
   - Structure map: os/dependency-graph.json
   ```

2. **Deploy each filled skill** to `.claude/skills/<name>/SKILL.md`. Copy
   `skills/templates/voice/SKILL.md` to `.claude/skills/voice/SKILL.md`, and the same for the
   other four starters. Keep each skill's reference material with it: a flat `reference.md`, or a
   `references/` folder for the skills that ship one.

### Cowork

Cowork reads your project's context once you connect the repository folder in the app. Connect the
folder (the `os/dispatch/README.md` ENV CHECK pattern is the same idea: confirm the folder is
connected before you rely on it) and point Cowork at your always-loaded context file. Where Cowork
loads skills from depends on your Cowork setup rather than a fixed path here, so follow Cowork's own
skills documentation for where the skill files live, then place your filled skills there. The shape
is identical to Claude Code: one always-loaded context file that points at everything else, plus
skills the agent finds by search. You verify a Cowork wiring the same way, through Steps 5 and 6
below.

### The skill-routing block

Whichever runtime you use, put this block in your always-loaded context file so the agent routes
through the registry instead of loading every skill. The Claude Code worked example above already
contains it; here it is on its own to drop into any runtime's context file. Copy it as-is:

```markdown
## Skill routing
Before loading any skill, run:
    python3 skills/registry/skill-registry.py "<the task, in a few words>" --confidence
Load only the top skill it returns (or, if it reports two close matches, ask which one).
Never load a skill you weren't routed to. This keeps each session's context small.
```

### The finished layout

Once wired, your repository looks like this (filled filenames, `.template` dropped):

```
your-firm-os/
├── CLAUDE.md                        # you create this: always-loaded, points at os/
├── .claude/
│   └── skills/
│       ├── voice/SKILL.md           # deployed from skills/templates/voice/
│       ├── proposal/SKILL.md
│       ├── session-integrity/SKILL.md
│       ├── project-scanner/SKILL.md
│       └── intelligence-processor/SKILL.md
├── os/
│   ├── agent-context.md             # filled (was agent-context.template.md)
│   ├── operating-principles.md
│   ├── session-rules.md
│   ├── decision-log.md
│   ├── project-state.yaml
│   ├── dependency-graph.json
│   └── corrections/
│       ├── corrections-registry.yaml
│       ├── seed-corrections.yaml
│       └── LIFECYCLE.md
├── profile/
│   └── company-profile.yaml         # filled
└── skills/
    ├── registry/
    │   ├── skill-registry.yaml       # filled (was skill-registry.template.yaml)
    │   └── skill-registry.py
    └── templates/                    # the source templates you filled and deployed from
```

**You know it worked when:** you start a fresh session and your agent already knows your firm's
name and voice without you pasting anything, and `python3 skills/registry/skill-registry.py "draft
a proposal"` returns your proposal skill. If the agent starts cold, the context file isn't being
loaded; recheck this step before writing any real work.

## Step 5: Run your first session

Start a session with your agent tool pointed at the wired-up repository. The real test of the
wiring (whichever runtime you set up in Step 4) is a question you never answered in this session:

**You know it worked when:** you ask *"which words do we never use?"* and your agent answers from
the Voice / Word-rules section of your filled `os/agent-context.md`, unprompted. Nothing loads your
`profile/company-profile.yaml` at session start, so the answer comes from the always-loaded context
file, which is the whole point of the wiring. If your agent starts cold and knows nothing, the
wiring in Step 4 didn't take: recheck that your context file loads and that it points at your
filled `os/` files. If the file loads but the answer is thin or missing, your `os/agent-context.md`
Voice section is underfilled: revisit Step 2.

## Step 6: Close your first session through the Exit Gate

`os/session-rules.md` defines the Exit Gate: the required close-out slots (fixes applied, a smoke
test, what's next) every session passes through before it ends. Use it from session one, even
though there's nothing to fix yet. The discipline is the point, not the content.

**You know it worked when:** your close-out names all three slots, even if two of them read
"nothing this session."

## Step 7: Start the corrections loop

The first time your agent gets something wrong in a way you had to correct, write it down in your
corrections registry rather than only correcting it in the moment. See `os/corrections/LIFECYCLE.md`
for the format and for when a correction earns promotion into a hard rule. This loop is what makes
session ten more reliable than session one.

**You know it worked when:** your corrections registry has at least one real entry and its `meta`
counts match the entries below it.

## Going further: delegate with dispatch

Once the loop above is running, `os/dispatch/README.md` describes the delegation pattern: how to
write a self-contained work order an agent can run in a fresh session with no prior context. It's
optional and worth reading once you find yourself handing the same kind of bounded task to an agent
more than once.

## When to add memory

Everything above works with no database at all: your corrections registry and decision log, both
plain files, already function as durable memory. If you later want your agent to recall past
sessions by meaning rather than by you remembering which file to open, see `docs/memory.md` for
the options and when each one is worth the setup cost.
