---
name: "voice"
# Keep name == this skill's folder name == its registry id. A firm prefix
# (like "acme-voice") is fine only if the folder and registry id use it too.
description: >-
  [Write in your firm's voice. Use for any external-facing content: proposals, site copy,
  emails, social posts, decks. Also use whenever you're asked to write something and the
  output should sound like you. Include at least three colloquial phrasings a tired version
  of you would actually type: see skills/README.md's colloquial-trigger rule before
  finalizing this description.]
---

# [Your Firm] Voice

<!-- AUTHORING NOTE: state the standard in one paragraph. What does "sounds like us" actually
     mean here, and what's the cost of getting it wrong (an inconsistent voice reads as an
     inconsistent operator)? Point to reference.md for the word lists and examples
     this file doesn't repeat inline. -->

[One paragraph: the quality bar for anything written in your voice, and why consistency across
every piece of writing matters more than any single piece being clever.]

See `reference.md` for the full word lists, sounds-like/doesn't-sound-like examples, and
worked examples by content type.

---

**Exit Gate.** Every output this skill produces closes through the Exit Gate defined in
`os/session-rules.md`: a fixes-applied note (if you revised anything after a first
draft), a smoke test (did you actually run the checks below, not just intend to), and what's next.
See that file for the full spec.

---

## Before you write

<!-- AUTHORING NOTE: branch intake depth by content type. A one-line Slack reply doesn't need
     the same up-front questions as a 900-word essay. Name your own content-type tiers and what
     each one needs to know before drafting starts. -->

For [long-form content: essays, case studies, decks]: confirm before drafting:
- [Who is this for, specifically?]
- [What's the one thing they should take away?]
- [What's already been said elsewhere that this shouldn't repeat?]

For [everything else: replies, short copy, social posts]: confirm only what's missing from
context already in the session. Don't re-ask what you already know.

## Tone qualities

<!-- AUTHORING NOTE: list the 3-5 tone qualities from your profile's voice.tone_qualities field.
     For each, define what it means in practice, not just the word. "Warm" means nothing on its
     own; "warm: acknowledges the reader's actual situation before making a point" is usable. -->

- **[Quality 1]**: [what it means in practice, one sentence]
- **[Quality 2]**: [what it means in practice, one sentence]
- **[Quality 3]**: [what it means in practice, one sentence]

## Always

<!-- AUTHORING NOTE: a short list of non-negotiable habits, stated as instructions, not
     aspirations. "Use short sentences" is aspirational. "No sentence over 30 words without a
     reason" is enforceable. -->

- [Enforceable habit 1]
- [Enforceable habit 2]
- [Enforceable habit 3]

## Word rules

<!-- AUTHORING NOTE: three tiers, pulled directly from your profile's voice.word_rules. Keep
     this list living: update it the moment you notice a new word that should be banned or
     freed. -->

**Never use:** [list from profile.voice.word_rules.never_use]

**Use carefully** (context-dependent; fine in some places, wrong in others): [list from
profile.voice.word_rules.use_carefully]

**Use freely:** [list from profile.voice.word_rules.use_freely]

## Patterns to avoid

<!-- AUTHORING NOTE: structural habits, not word-level ones. A cliché sentence shape, a
     rhetorical move that reads as generic, a construction you're tired of seeing. Pull from
     profile.voice.writing_anti_patterns and add to this list as you catch new ones. -->

- [Anti-pattern 1, described structurally, not just named]
- [Anti-pattern 2]
- [Anti-pattern 3]

## Format rules by content type

<!-- AUTHORING NOTE: not every content type follows the same rules. A cold email and a case
     study have different length, structure, and formatting conventions. List your content
     types and the specific rule for each. -->

| Content type | Rule |
|---|---|
| [Content type 1] | [length, structure, or formatting rule specific to this type] |
| [Content type 2] | [rule] |
| [Content type 3] | [rule] |

## Self-audit before you call it done

<!-- AUTHORING NOTE: a short list of questions to ask about the draft itself, not a repeat of
     the rules above. These should catch things a rule list can't: does this sound like a
     specific person, or like anyone? -->

- [Self-audit question 1]
- [Self-audit question 2]
- [Self-audit question 3]

## Final scan before output

<!-- AUTHORING NOTE: a mechanical, almost boring checklist run right before you finalize any
     piece of writing. This catches errors a "does this sound right" read misses because it's
     reading for feel, not counting occurrences. -->

Before finalizing, check:
- [ ] Zero instances of every "never use" word.
- [ ] [Your firm's specific mechanical rule, e.g., a punctuation-frequency cap, if you have one]
- [ ] No sentence that could have been written by anyone about anything (the genericness test).
- [ ] Matches the format rule for this specific content type.

## Signature phrases

<!-- AUTHORING NOTE: optional. If your firm has a small number of phrases that are genuinely
     yours (a tagline, a recurring turn of phrase), list them here with a reuse cap so they
     stay distinctive instead of becoming a tic. -->

[Phrase 1] (use no more than [N] times per [unit, e.g., "essay" or "month"])

## Related files

- `reference.md` : word lists, examples, and worked drafts by content type.
- `os/session-rules.md` : the Exit Gate this skill closes through.
- `profile/company-profile.yaml` : the source of everything parameterized above.

---

**Exit Gate reminder:** close every use of this skill with the fixes-applied / smoke-test / next
steps slots from `os/session-rules.md`.
