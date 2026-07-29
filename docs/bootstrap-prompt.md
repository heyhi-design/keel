# Bootstrap Prompt

This is the fast path. The scaffold's whole premise is that you already own a capable agent, so the
quickest way to stand it up is to hand that agent the job. Paste the prompt below into your agent
**inside your own copy of this repository** (see the README's Quickstart for how to get one). Your
agent interviews you, fills in every template, merges the starter corrections, registers the
starter skills, wires the whole thing into your runtime, and proves each step worked before it
stops. You answer questions; it does the setup.

`docs/setup-guide.md` is the same sequence by hand, and the reference for what each phase below is
doing. If you would rather place each piece yourself, use that instead.

A caveat worth keeping: your agent is a fast pair of hands, not a substitute for your judgment. It
should never invent your voice, your values, or your services. When the prompt says "interview,"
it means the agent asks and you answer. Anything it can't get from you, it flags rather than
fabricates.

---

**Copy everything below this line into your agent.**

---

You are helping me stand up my Keel in this repository. Work through the phases below in
order. Do not skip ahead, and do not invent answers to anything that is mine to decide: my
identity, my voice, my values, my services, my constraints. Where you need one of those, ask me and
wait. Where a file gives you an instruction that conflicts with something I've told you, follow me
and flag the conflict.

Before you start, confirm you can read `README.md`, `docs/setup-guide.md`, `docs/three-layer-model.md`,
and `profile/intake-conversation.md` in this repository. If any of them is missing, stop and tell me
which one, rather than guessing at its contents.

**Phase 1: Interview me.** Work through `profile/intake-conversation.md` one question at a time. Ask
me each question, wait for my answer, and move on only when I've answered. Help me think where I'm
stuck, but never write an answer I didn't give. If I say a question doesn't apply to my practice,
record that it was skipped on purpose.

**Phase 2: Fill in my profile.** Transcribe my answers into `profile/company-profile.template.yaml`,
then rename it to `profile/company-profile.yaml` (drop `.template`). Fill every field I answered.
For any I deliberately skipped, leave the field empty and add a one-line comment saying I skipped it
on purpose. If I want to see how much specificity a field is asking for before answering, show me
the same field in `examples/baseline-year/profile/company-profile.yaml` — a worked instance for an
invented firm. Show me the filled file and let me correct it before you go on.

**Phase 3: Fill in the configuration templates.** For each of the seven `os/` templates
(`agent-context`, `operating-principles`, `session-rules`, `decision-log`, `project-state`,
`dependency-graph`, and `corrections/corrections-registry`), fill every `[BRACKETED SLOT]` from my
profile, remove the authoring guidance (the italic notes and the leading comment block in the
Markdown and YAML files; the underscore-prefixed `_` keys in `dependency-graph.template.json`,
which has no comment syntax), and rename the file to drop `.template`. Don't rename
`os/corrections/LIFECYCLE.md` or `os/corrections/seed-corrections.yaml`; they aren't fill-in
templates. LIFECYCLE.md is reference; `seed-corrections.yaml` you act on in Phase 4, keeping the
starter entries I want and dropping the rest, without renaming it. The decision log, project state,
and dependency graph start essentially empty, which is correct for a new practice.

**Phase 4: Merge the starter corrections.** `os/corrections/seed-corrections.yaml` holds five
framework-level starter corrections. Show me the five, and merge the ones I want into
`os/corrections/corrections-registry.yaml`. Then recompute that registry's `meta` block from the
actual entries: `total_corrections`, `active`, `superseded`, and `retired`. Do not carry the seed
file's counts over blindly; count what you actually merged. Keep every severity to `behavioral` or
`factual` (those are the only two the schema allows).

**Phase 5: Fill in and deploy the skills.** For each of the five starter skills under
`skills/templates/` (`voice`, `proposal`, `session-integrity`, `project-scanner`,
`intelligence-processor`), fill the bracketed slots in `SKILL.template.md` and any
`reference.template.md` from my profile, and rename them to drop `.template`. Then deploy each skill
to where my runtime loads skills from. For Claude Code that is `.claude/skills/<name>/SKILL.md`; if
you don't know my runtime, ask me before you deploy. Keep each skill's reference material with it: a
flat `reference.md`, or a `references/` folder for the skills that ship one.

**Phase 6: Register the skills.** Rename `skills/registry/skill-registry.template.yaml` to
`skills/registry/skill-registry.yaml`. It already ships one entry per starter skill; for each, set
`location` to where you actually deployed the skill in Phase 5, and adjust the description, tags,
and triggers to match my filled-in skill. Recompute the registry's `meta` counts. Then run
`python3 skills/registry/skill-registry.py --list` and show me the result.

**Phase 7: Wire it into my runtime.** Follow `docs/setup-guide.md` Step 4 for my runtime. For Claude
Code, create a `CLAUDE.md` at the repository root that loads my `os/agent-context.md` and
`os/operating-principles.md`, tells the agent to read the active entries of my
`os/corrections/corrections-registry.yaml` at the start of every session, points at my on-demand
`os/` files (`session-rules`, `project-state`, `decision-log`, `dependency-graph`), and includes
the skill-routing block (before loading any skill, run `skills/registry/skill-registry.py` and load
only what it returns). For Cowork, set up the folder-connected equivalent. Show me the `CLAUDE.md`
you wrote.

**Phase 8: Prove it worked.** Run each of these checks and report which passed and which need my
attention. Do not report success on one you didn't actually run.

1. Scan the `os/` templates I filled and my deployed skills for leftover template brackets like
   `[Firm Name]` (there should be none). Skip `os/corrections/seed-corrections.yaml` and
   `os/dispatch/` (they keep example brackets on purpose), and ignore legitimate empty `[]` arrays
   and Markdown links. Then run `grep -rn '\.template' os/ .claude/skills/` to catch leftover
   `.template` pointers: the only expected hit is the rename gloss in `os/corrections/LIFECYCLE.md`.
   A correctly filled system keeps no `.template` files or cross-references in the paths above, so
   any other hit there means a rename or a repoint was missed. Keep the grep scoped as written:
   `examples/` legitimately carries `.template` references (it explains which template each example
   file was filled from) and is not part of your instance, so a wider grep reports defects that
   aren't. For the same reason, resolve files by exact path rather than basename during setup —
   `examples/` contains a second `company-profile.yaml`, `agent-context.md`, `decision-log.md`, and
   `corrections-registry.yaml`, all belonging to a fictional firm.
2. `python3 skills/registry/skill-registry.py --registry skills/registry/skill-registry.yaml --list`
   runs without a traceback and lists my five skills.
3. `python3 skills/registry/skill-registry.py --registry skills/registry/skill-registry.yaml "draft
   a proposal"` returns my proposal skill.
4. If I also use the `agent-corrections` tool, its `audit` validates my
   `os/corrections/corrections-registry.yaml` with every entry valid.
5. The real test: in a fresh session with my wiring loaded, ask "which words do we never use?" and
   confirm the answer comes from my profile, not from you guessing. If it can't, my context file
   isn't loading; recheck Phase 7.

When you're done, give me a short summary: what you filled in, what I still need to decide, and any
check in Phase 8 that didn't pass.
