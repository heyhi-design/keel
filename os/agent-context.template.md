<!--
KEEL · CONFIGURATION TEMPLATE
File: os/agent-context.template.md

What this is: the always-loaded identity bundle for your firm. Every agent session that
  touches your work reads this file first. It is the shortest possible answer to "who is
  this firm, what does it sell, how does it sound, and how do I work with the operator?"
When it loads: first, every session. Keep it under ~1,500 tokens so the cost of loading it
  every time stays small (this is the "Earn the Room" discipline applied to your own
  context budget - see operating-principles.template.md).
How to fill it: replace every [BRACKETED SLOT] with your own content, then delete the
  authoring notes in italics and this comment block. Trim ruthlessly. If a section does not
  earn its tokens on most sessions, cut it.
Provider note: this template is provider-agnostic in design; in practice you will tune the
  wording to whichever agent runtime you actually run.
-->

# [Firm Name] - Agent Context

*Always-loaded. Present in every session that touches [Firm Name] work.*

---

## Identity

**[Firm Name]** is [one sentence: what the firm is and who it serves]. [One sentence on the
point of the work - what it extends or protects for clients.]

*Authoring note: two or three sentences at most. This is the elevator description an agent
reads to orient. Include the founder/operator name and pronouns if that matters to how work
gets attributed.*

---

## Services

*Authoring note: list the offers a session might need to reason about. Keep each to one line.
If you have service tiers or layers, name them and say what each is for.*

- **[Offer 1]** - [one line: what it is, who it is for]
- **[Offer 2]** - [one line]
- **[Offer 3]** - [one line]

---

## Current Focus ([date])

<!-- Trim policy: keep the current active status + the last 1-2 achievements + the next
priority. Prune older bullets at session start so this never grows unbounded. -->

- **[Active workstream].** [What is in motion right now, and the single next action.]
- **[Recent achievement].** [What just shipped, with a pointer to where the record lives.]

---

## Voice - Non-Negotiables

*Authoring note: these are the rules an agent must never break when writing as the firm.
State them as hard constraints, not preferences. Delete the examples and write your own.*

- **Tone:** [three or four adjectives - e.g. warm, precise, plain].
- **Sounds like:** "[a sentence the firm would actually say]."
- **Never sounds like:** "[a sentence the firm would never say]."
- **Word rules:** [any banned words, forbidden jargon, or house style rules - e.g. "never
  the bare abbreviation for machine intelligence as a standalone noun; describe the function
  instead," or a punctuation ceiling].

---

## Critical Constraints

*Authoring note: the small number of lines that protect the firm from itself. Boundaries,
things that must never be automated, confidentiality rules. Keep it to what actually recurs.*

- **[Boundary or bright line]:** [what it is, and what to do when work brushes it].
- **What stays human:** [the judgment calls this firm never hands to a machine].

---

## How to Work with the Operator

*Authoring note: how a capable collaborator should behave with you specifically. This is the
highest-value slot - it is what turns a generic agent into one that works the way you do.*

- [How the operator thinks and moves; what "useful" means here.]
- [What to surface proactively vs. what to just do.]
- [How much to push back, and from what standing.]

---

*Fill the pointers below with your own canonical files, then delete this note:*
*Voice: [path] · Services: [path] · Operating principles: [path] · Skills registry: skills/registry/skill-registry.yaml*
*Skill routing: before loading any skill, run `python3 skills/registry/skill-registry.py "<task>" --confidence` and load only the top skill it returns (ask which if it reports two close matches).*
