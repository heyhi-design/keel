---
name: "proposal"
description: >-
  Draft a scoped proposal for a prospective reporting engagement. Use when asked to write a
  proposal, scope an inventory or a review, or put together an SOW. Also for "write up what
  we discussed for the manufacturing prospect", "turn Tuesday's call into a proposal", "they
  want something in writing by Friday", or any request to put a scope on paper.
---

# Baseline Year Proposal

> **Worked example — this firm does not exist.** "Baseline Year" and Sam Oyelaran are invented.
> This is `skills/templates/proposal/SKILL.template.md` filled in. Copy the template, not this
> file, and do not deploy this skill: its `name:` collides with the real one you will deploy. See
> [`examples/README.md`](../../../README.md).

Drafts a proposal scoped to a specific prospect and a specific offering, in Baseline Year's
voice, without stating a fee. See `reference.md` for the document skeleton in full, worked
openings, and the fee-deferral language.

---

**Exit Gate.** This skill closes through `os/session-rules.md`'s Exit Gate: fixes applied, a
smoke test (the pre-send check below, actually run), findings integration if this proposal
surfaced a gap in the services list or profile, and what's next.

---

## Before you draft

If the session already has the prospect, their situation, and which offering fits, go straight
to drafting. Otherwise, confirm:

**About the client:**
- Who are they, what do they make or do, and how many sites?
- Which regime pulls them in, and what is their first mandatory reporting date?
- Has anyone built them an inventory before? Who, and is it still maintained?

**About the engagement:**
- What triggered the conversation: the deadline, a board question, a customer questionnaire, or
  an assurance provider who has already asked something uncomfortable?
- Who inside the company owns the data today? If the answer is "nobody" or "the person who left",
  that changes the scope more than anything else on this list.

**About this proposal specifically:**
- Was anything promised or implied on the call — a date, an inclusion, a rough shape of fee —
  that this proposal has to honor or carefully walk back?

## Choosing the right offering

**Stage 1: what situation is the prospect in?**

| Situation | Points toward |
|---|---|
| First reporting cycle, nothing built yet | Measure |
| Inventory exists, built by someone else, nobody can explain it | Measure (Repair, not Build) |
| Inventory is sound, the report is the gap | Disclose |
| Assurance provider is booked and they are nervous | Hold (Readiness Review) |
| Wants a second opinion, not a relationship | Hold (Readiness Review, standalone — see the decision log, 2026-06-30) |
| Reported once, now facing every year of it | Hold (Retainer) |
| "Just write the report over our numbers" | Measure first, always. See the hard rule below. |

**Stage 2: which specific offering?**

| Offering | Scope | Fits when |
|---|---|---|
| Inventory Build | Scope 1 and 2 from source, screening Scope 3, plus the model they rerun next year | Nothing exists, or what exists is not worth repairing |
| Inventory Repair | Trace to source, decide what recalculates versus what discloses with a limitation | Something exists and roughly half of it survives contact |
| Double Materiality Assessment | Impact and financial materiality with the engagement it has to evidence | The topic list is the gate, usually because the regime demands it |
| First Report | The disclosure itself, over an inventory this practice has traced | Never on its own. Always downstream of Build or Repair. |
| Assurance Readiness Review | Walk it as the assurance provider would; ranked findings list | Assurance is booked, or they want to know what they'd fail on |
| Reporting Year Retainer | Quarterly checks, boundary monitoring, regulation changes, next report | The first cycle is done and the second is the real problem |

**The hard rule.** A request to write a report over an inventory this practice has not traced is
declined as scoped, every time. Route it to Inventory Repair, priced with the trace included, or
decline. This is not a preference and it is not negotiable under deadline pressure — the reason
is in the decision log, entry of 2026-03-02, and the cost of the one time it nearly happened is
the whole reason the rule exists.

## The document skeleton

1. **Situation.** Where the prospect actually is, specific enough that they recognize themselves:
   their sites, their data owners, their first mandatory date, what somebody already told them
   that is not quite right. If this section could be sent to a different prospect, it is not done.
2. **Stakes.** What a restated baseline costs them, in their own terms. Draw on the argument in
   `profile/company-profile.yaml`. Do not manufacture urgency; the regulatory calendar supplies
   plenty and inventing more reads as sales.
3. **The work.** What gets done, in stages, with what they get at the end of each. Name what is
   out of scope explicitly — Scope 3 categories not covered, sites excluded, assurance itself.
   Vague scope is the single most common cause of a strained engagement later, and in this domain
   it usually shows up as an argument about which Scope 3 categories were "obviously" included.
4. **Logistics.** Timeline against their reporting date, what is needed from them and by when,
   who from their side has to be available, next steps. Never a number.

## Why there is no number in the proposal

The fee shape goes in the document; the figure goes in the conversation. This is not coyness — in
this practice the number genuinely moves with the facility count and the state of the data, and
neither is known until the walk-through is done. A figure quoted before then is either padded
against the worst case or about to be revised upward, and both damage the thing being sold.

Say what the shape is (fixed for a Build, staged for a Repair, retained for a cycle) and that the
figure follows the walk-through. Approved wording is in `reference.md`.

## Pre-send check

- [ ] No fee anywhere in the document. Every mention of cost uses the approved deferral language,
      not an implied number or a range.
- [ ] The situation section names things specific to this prospect that a generic opener could
      not contain.
- [ ] Out-of-scope is explicit, and names Scope 3 categories and excluded sites by name.
- [ ] Nothing in the scope requires writing over data this practice has not traced.
- [ ] Timeline is stated against their mandatory reporting date, not in abstract weeks.
- [ ] Run through the `voice` skill's self-audit before sending.

## Saving the draft

`proposals/[prospect-slug]-[YYYY-MM-DD].md`. One file per version; never overwrite a sent
proposal, because which version they actually received matters later.

## After acceptance

1. Create the engagement folder from the standard shape, outside version control.
2. Fill the engagement intake: sites, data owners, systems of record, reporting date, and the
   boundary as understood on day one. The boundary log starts here and runs for the life of the
   relationship.
3. **Gate:** no billable work, and no data access requested, before the signed engagement letter
   is in place. Flag this explicitly rather than assuming it has been handled — data access in
   particular tends to get offered enthusiastically before anything is signed.

## Related files

- `reference.md` : document skeleton in full, worked openings, fee-deferral language.
- `profile/company-profile.yaml` : the services list and the core argument.
- `os/decision-log.md` : the 2026-03-02 entry behind the hard rule above.
- `os/session-rules.md` : the Exit Gate this skill closes through.

---

**Exit Gate reminder:** close every use of this skill with the required close-out slots from
`os/session-rules.md`.
