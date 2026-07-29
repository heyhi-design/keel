---
name: "proposal"
# Keep name == this skill's folder name == its registry id. A firm prefix
# (like "acme-proposal") is fine only if the folder and registry id use it too.
description: >-
  [Draft a scoped proposal for a prospective engagement. Use when asked to write a proposal,
  scope a project, or put together an SOW for a specific prospect. Include at least three
  colloquial phrasings: see skills/README.md's colloquial-trigger rule.]
---

# [Your Firm] Proposal

Drafts a proposal scoped to a specific prospect and a specific offering from your services list,
in your voice, without ever stating a price. See `reference.md` for the document
skeleton, worked openings, and approved pricing-deferral language.

---

**Exit Gate.** This skill closes through `os/session-rules.md`'s Exit Gate: fixes applied,
a smoke test (did the pre-send check below actually run), findings integration if this proposal
surfaced a gap in your services list or profile, and what's next.

---

## Before you draft

If the session already has enough context (the prospect, what they need, which offering fits),
skip straight to drafting. Don't re-ask what's already been said. Otherwise, confirm:

**About the client:**
- Who is the prospect, and what do you already know about their situation?
- What prompted this conversation? What's the trigger?

**About the engagement:**
- Which of your offerings fits this need? (See the lookup below if it isn't obvious.)
- Is there a timeline constraint or a deadline driving this?

**About this proposal specifically:**
- Has anything been promised or implied already, in an earlier conversation, that this proposal
  needs to honor or needs to walk back carefully?

## Choosing the right offering

<!-- AUTHORING NOTE: a two-stage lookup works better than a flat list once you have more than a
     handful of offerings. Stage one: what situation is the prospect in? Stage two: which
     specific offering fits that situation? Fill in your own categories and offerings from
     profile.services. -->

**Stage 1: what situation is the prospect in?**

| Situation | Points toward |
|---|---|
| [Situation pattern 1] | [Category of offering] |
| [Situation pattern 2] | [Category of offering] |

**Stage 2: which specific offering, within that category?**

| Offering | Scope | Fits when |
|---|---|---|
| [Offering 1, from profile.services.offerings] | [scope] | [fit signal] |
| [Offering 2] | [scope] | [fit signal] |

## The document skeleton

<!-- AUTHORING NOTE: a fixed four-section shape keeps every proposal consistent and keeps you
     from forgetting a section under deadline pressure. Adjust section names to your own
     vocabulary if "situation / stakes / work / logistics" doesn't fit how you think, but keep
     the shape: where they are, why it matters, what you'll do, how it runs. -->

1. **Situation.** Where the prospect is right now, in language that shows you actually listened,
   not a template restating what a proposal always says.
2. **Stakes.** What happens if this problem stays unaddressed. Draw on `profile.core_argument` if
   your firm has a thesis that applies here. Don't manufacture urgency that isn't real.
3. **The work.** What you'll actually do, scoped specifically enough that both sides know what's
   in and what's out. Vague scope is the single most common cause of a strained engagement later.
4. **Logistics.** Timeline, what you need from them, next steps. Never a number. See the
   pricing-deferral language in `reference.md`.

## Pre-send check

Before sending any proposal:

- [ ] Zero pricing anywhere in the document. Every mention of cost uses the approved deferral
      language, not an implied number.
- [ ] Scope in section 3 is specific enough that a disagreement about "what's included" is
      unlikely six weeks from now.
- [ ] Run this proposal through your voice skill's self-audit before sending.
- [ ] The situation section actually reflects this specific prospect, not a generic opener that
      could apply to anyone.

## Saving the draft

<!-- AUTHORING NOTE: name your own convention. A consistent, predictable save path means you
     (or your agent) can find any past proposal without searching. -->

Save drafts as [your naming convention, e.g., `proposals/[client-slug]-[date].md`].

## After acceptance

<!-- AUTHORING NOTE: what happens the moment a prospect says yes? Naming this now, before it's
     needed under time pressure, avoids improvising a new process every time. -->

Once a proposal is accepted:
1. [Set up the engagement workspace, from whatever template you use for a new client.]
2. [Fill in an intake document for this specific engagement.]
3. **Gate:** don't begin billable work until [a signed contract / an NDA / whatever your own
   gating condition is] is actually in place. Flag this gate explicitly rather than assuming it's
   been handled.

## Related files

- `reference.md` : document skeleton in full, worked openings, pricing-deferral language.
- `profile/company-profile.yaml` : your services list and core argument.
- `os/session-rules.md` : the Exit Gate this skill closes through.

---

**Exit Gate reminder:** close every use of this skill with the required close-out slots from
`os/session-rules.md`.
