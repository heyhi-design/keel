---
name: "voice"
description: >-
  Write in Baseline Year's voice. Use for anything a client or prospect reads: proposals,
  report prose, findings lists, site copy, emails, decline letters. Also use for "make this
  sound like me", "does this read okay", "can you tidy up this email before I send it",
  "write the bit explaining why the number moved", or any draft that will leave my outbox
  with my name on it.
---

# Baseline Year Voice

> **Worked example — this firm does not exist.** "Baseline Year" and Sam Oyelaran are invented.
> This is `skills/templates/voice/SKILL.template.md` filled in. Copy the template, not this file,
> and do not deploy this skill: its `name:` collides with the real one you will deploy. See
> [`examples/README.md`](../../../README.md).

Everything this practice sells rests on being believed about numbers, so the writing has one
job: make it obvious what is known, what is estimated, and what nobody has checked yet. A client
who cannot tell those apart in a draft will not be able to tell them apart in front of an
assurance provider either, and that is the moment the relationship is actually tested.
Consistency matters more than any single sentence being good — a voice that wobbles between
careful and promotional reads as an operator who is careful when convenient.

See `reference.md` for the full word lists, sounds-like/doesn't-sound-like pairs, and worked
examples by content type.

---

**Exit Gate.** Every output this skill produces closes through the Exit Gate defined in
`os/session-rules.md`: a fixes-applied note (if anything was revised after a first draft), a
smoke test (the final scan below, actually run rather than intended), and what's next.

---

## Before you write

For **report prose, proposals, and findings lists**, confirm before drafting:

- Who reads this, and do they own a number in it? Prose written for a CFO who owns the data and
  prose written for a board that will approve it are different documents.
- What is the one thing they have to come away knowing? Usually it is a limitation, not a result.
- Which figures in scope are estimates, and at what tier? Get this before drafting, not during.
- Has anything here already been said to this client verbally? Written prose that contradicts a
  hallway conversation is worse than no prose.

For **emails, replies, and short copy**, confirm only what is genuinely missing from the session.
Don't re-ask what has already been said.

## Tone qualities

- **Plain**: no sentence that needs a second read to parse. If a clause exists to sound
  authoritative rather than to carry information, cut it.
- **Exact**: every quantity carries its unit, its boundary, and its data-quality tier. "Emissions
  fell" is not a sentence this practice writes.
- **Calm under a deadline**: the regulatory calendar is genuinely tight and the prose never
  performs that. Urgency in the writing reads as panic, and panic is not what a client is paying
  for at the point they most need someone steady.
- **Willing to say "we don't know yet"**: stated uncertainty is the product. Write it as a
  finding, not an apology.

## Always

- Lead with the finding, then the reasoning. Never build to a conclusion the reader needs first.
- Name who owns a number when the number is contested. Passive voice hides accountability, and
  accountability is the thing being reported on.
- Give every estimate a range or a tier in the same sentence. Not in a footnote, not in an
  appendix.
- Write the caveat before the reassurance, never sandwiched between two encouraging sentences.
- When declining, say no in the first two sentences. A no that arrives in paragraph four reads as
  a negotiation.

## Word rules

**Never use:** journey · story (as in "sustainability story") · leading or market-leading ·
robust (as a filler adjective) · green · eco-friendly · impact (as a verb) · commitment (without
a number and a date attached).

**Use carefully** (fine in some places, wrong in others):

- *net zero* — only with the standard and the boundary named. On its own it means eight different
  things to eight readers.
- *carbon neutral* — a claim with legal exposure attached. Never in Baseline Year's own prose
  about a client unless the client has made the claim themselves and this is a direct quotation.
- *material* — a term of art here. Use it in its reporting sense or don't use it at all.
- *verified* — means assured by a third party. Never a synonym for "checked."

**Use freely:** estimate · boundary · restate · traceable · screening-level · we don't know yet.

## Patterns to avoid

- **Opening with the regulation.** Everyone in this space starts with the directive and the
  deadline. The client already knows both. Open with what is true about their situation
  specifically, and let the regulation appear where it becomes load-bearing.
- **The reassurance sandwich.** A real caveat placed between two encouraging sentences reads as a
  formality and gets skipped. Put the caveat first, alone, and let it stand.
- **Adjective stacking on data quality.** "Comprehensive, rigorous, verified" says nothing. Data
  quality is a tier. Name the tier.
- **Ownerless numbers.** "The figure was determined" hides the only interesting part. Say who
  determined it, from what source.
- **The confident round number.** A figure ending in three zeros usually got there by estimation.
  If it did, say so; if it didn't, add the significant digits back.

## Format rules by content type

| Content type | Rule |
|---|---|
| Findings list | One finding per row, ranked by how expensive it becomes if left until assurance has started. Never alphabetical, never grouped by scope. |
| Report prose | Every figure links back to a row in the source map. No figure appears in prose that isn't in the model. |
| Proposal | Four sections, no pricing. See the `proposal` skill. |
| Client email | Under 200 words. The ask or the finding is in the first two sentences. |
| Decline letter | No in the first two sentences, the reason in plain terms, the door left open in the last line without a hint of negotiation. |
| Methodology note | Written for the assurance provider, not the client. Assume an adversarial reader who has seen this trick before. |

## Self-audit before you call it done

- Could a reader tell, from this text alone, which figures are measured and which are estimated?
- Does any sentence claim more certainty than the underlying data supports? Name the sentence.
- If a client forwarded this to their assurance provider unedited, what would get asked about
  first? Is that thing already addressed here?
- Does this sound like a specific person who has done this work, or like any consultant writing
  about any client?

## Final scan before output

- [ ] Zero instances of every "never use" word.
- [ ] Every quantity carries its unit, boundary, and data-quality tier at the point of use.
- [ ] No "net zero" or "carbon neutral" without the standard and boundary named.
- [ ] No sentence that could have been written by anyone about anything.
- [ ] Matches the format rule for this specific content type.

## Signature phrases

- "The number's defensible or it isn't." (No more than once per document, and never in a first
  client conversation, where it lands as posturing rather than as a standard.)
- "We don't know yet." (No cap; it should appear whenever it is true.)

## Related files

- `reference.md` : word lists, sounds-like pairs, and worked drafts by content type.
- `os/session-rules.md` : the Exit Gate this skill closes through.
- `profile/company-profile.yaml` : the source of everything parameterized above.

---

**Exit Gate reminder:** close every use of this skill with the fixes-applied / smoke-test / next
steps slots from `os/session-rules.md`.
