# Baseline Year Decision Log

> **This is a worked example for a firm that does not exist.** "Baseline Year", Sam Oyelaran, and
> every decision below are invented. This file is `os/decision-log.template.md` filled in. Copy
> the template, not this file. See [`examples/README.md`](../../README.md).

**Append-only. The permanent record of this firm's significant decisions.**

**Start date:** 2025-09-01

---

## The rules

1. **Append-only.** Never edit an existing entry. Add new ones. The one exception is a security
   redaction (removing a leaked secret): edit in place, then record the redaction in a new
   appended entry so the edit is never silent.
2. **Newest-first.** Prepend new entries directly under the `## Entries` heading below.
3. **Read before you write.** Before appending, read the last few entries to check for overlap
   or a decision this one supersedes.
4. **Log decisions, not activity.** An entry earns its place when it changes the direction of
   the work: an architectural choice, a positioning call, a product decision, a boundary ruling.

---

## Entries

<!-- Prepend new entries directly below this line, newest first. -->

## [2026-06-30] - [services] Assurance Readiness Review sells standalone

**Type:** direction · **Criticality:** medium · **Contributor:** Sam

### What We Had
Assurance Readiness Review existed as a stage inside the Reporting Year Retainer, not as
something anyone could buy on its own. Two prospects this spring wanted exactly that and nothing
else: a second opinion before their assurance provider arrived, with no interest in moving their
whole reporting relationship. Both were told no, on the reasoning that a review without an
ongoing relationship would surface problems I would not be there to fix.

### What Changed
Ran it once anyway, in June, for a prospect who pushed. The finding list came back long, the
client fixed about half of it themselves before assurance, and the half they did not fix became
a scoped Inventory Repair in July. The worry that a review would end in a shrug turned out to be
backwards: the review is what makes the repair legible enough to buy.

### What We Decided
Sell Assurance Readiness Review standalone. It is the cheapest honest entry point into a client
who is not ready to change their whole setup, and the finding list does the qualifying work that
a discovery call does badly. Keep one condition: the review names what it could not verify, in
writing, so a client who fixes nothing cannot later cite the review as a clean bill of health.

### Documents Affected
- `profile/company-profile.yaml` — offering moved out of the retainer's scope description into
  its own entry under Hold.
- `os/agent-context.md` — services list updated; Current Focus notes the first standalone sale.
- The `proposal` skill — Stage 1 lookup gains the "wants a second opinion, not a relationship"
  row.

### Open items (carry forward)
The written "could not verify" section has no template yet. Next review engagement should produce
one rather than improvising it again.

---

## [2026-03-02] - [services] First Report is never sold on its own

**Type:** direction · **Criticality:** high · **Contributor:** Sam

### What We Had
First Report was listed as a standalone offering. A prospect in February wanted exactly that:
they had an inventory built by a previous consultant, they had a deadline, and they wanted
someone to write the disclosure over the numbers they already had. Good client, real budget,
work I am obviously able to do.

### What Changed
Spent two days tracing their inventory before drafting anything, on the assumption that this was
a formality. It was not. Scope 2 had been calculated location-based in one facility and
market-based in another, which meant the total was not a total of anything. Fixing it would have
moved their published baseline. Writing the report as scoped would have meant putting my name on
a document whose central figure I knew to be wrong.

Declined the engagement. They went elsewhere, published, and restated ten months later.

### What We Decided
First Report is no longer sold as a standalone offering. It is available only over an inventory
this practice has traced to source, whether that is one we built or one we repaired first. The
tracing is not a formality and is not free: it is priced into every path that ends in a report.

The general form of the rule, which matters more than this one offering: do not sell the writing
layer over data somebody else vouched for. Ghostwriting a disclosure is a liability with my
fingerprints on it and the client's name on the cover.

### Documents Affected
- `profile/company-profile.yaml` — First Report scope now states the dependency explicitly.
- `os/agent-context.md` — Critical Constraints gained "no disclosure over an untraced inventory."
- The `proposal` skill — Stage 1 lookup routes a report-only request to Measure first.
- `os/corrections/corrections-registry.yaml` — this is the promotion event for
  `report-drafted-over-untraced-inventory`. That entry (open since 2025-11-30) had fired three
  times; the rule it was carrying moved into the always-loaded constraints above, so the entry
  itself is now marked `superseded`, pointing at its new home. Registry `meta` recounted in the
  same pass, per `os/corrections/LIFECYCLE.md`.

### Open items (carry forward)
No standing language yet for declining an engagement in a way that leaves the door open. Wrote
that email four times before sending it. Worth a reusable draft in the `voice` skill's reference.
