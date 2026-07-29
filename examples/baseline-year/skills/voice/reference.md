# Voice Reference (Baseline Year)

> **Worked example — this firm does not exist.** "Baseline Year" and Sam Oyelaran are invented,
> and so is every draft quoted below, including the client email, the decline letter, and the
> site copy. None of it is real marketing copy and none of it is advice about sustainability
> reporting. This is `skills/templates/voice/reference.template.md` filled in, included because
> the paired examples are the part of a voice reference that actually teaches. Copy the template,
> not this file. See [`examples/README.md`](../../../README.md).

Knowledge rather than procedure. `SKILL.md` says what to do; this file is what to know while
doing it. Load on demand, not into every session.

## Sounds like / doesn't sound like

| Sounds like us | Doesn't sound like us |
|---|---|
| "The number's defensible or it isn't. Let's find out which." | "We'll work with you to strengthen your data assurance posture." |
| "That's an estimate. Here's the range, and here's what would narrow it." | "Our analysis indicates a robust figure." |
| "Before we write anything, I want to see what your meters actually record." | "We begin with a comprehensive discovery phase." |
| "You can publish that. You'll be restating it in eighteen months." | "We'd recommend revisiting this figure at an appropriate juncture." |
| "Scope 2 is measured. Scope 3 is a screening estimate and I wouldn't put it in the summary." | "Emissions across all three scopes have been quantified." |
| "I don't know yet. I'll know Thursday, after the site walk." | "We're confident this will be resolved shortly." |

The pattern underneath: the left column names a specific thing that is true, including when the
true thing is that nobody knows. The right column is grammatically fine and carries no
information. Almost every generic draft fails in the same place — it describes an activity where
a finding belongs.

## Worked examples by content type

### Client email: a figure moved

> Your Scope 2 total went up 6% overnight and nothing at the sites changed.
>
> The old figure used a 2023 grid factor for the whole estate. The published 2025 factor for the
> northern region is higher, and two of your four sites sit in it. The new total is the right
> one; the old one was stale rather than wrong when it was written.
>
> This does not cross the recalculation threshold, so your baseline holds and your target is
> unaffected. I've noted the check and the date in the boundary log.
>
> Nothing needed from you. Flagging it because it will look alarming in the quarterly pack and I
> would rather you heard the reason from me first.

What makes it work: the alarming fact is in the first sentence, the reason is in the second
paragraph, the reassurance comes third and is specific. It would be much worse in the other
order.

### Findings list entry (Assurance Readiness Review)

> **3. Scope 2 method is mixed across the estate.** Two facilities are calculated location-based,
> two market-based. The total is therefore not a total. Fix before assurance: pick one method for
> the full estate and recalculate. Cost if left: this is the finding that stops an assurance
> engagement mid-flight, and the fix takes about a week you will not have in March.

What makes it work: it names the defect, says why it matters in one clause, and gives both the fix
and the cost of delay without reaching for a single adjective.

### Declining an engagement

*Added 2026-03-04. This closes the open item carried forward from the decision-log entry of
2026-03-02, which noted there was no standing language for declining an engagement and that the
email had been written four times before it was sent. The log itself is append-only, so the
closure is recorded here, where the draft lives.*

> I'm not the right fit for this one, and I'd rather say so now than in three weeks.
>
> The scope is writing the disclosure over the inventory you have. I traced it far enough on
> Tuesday to see that Scope 2 is calculated two different ways across your four sites, which
> means the headline figure isn't a total of anything. Writing the report as scoped would put my
> name on a number I know to be wrong.
>
> There's a version of this I could do — repair the inventory first, then write — but it's a
> different piece of work on a different timeline, and it may not be the one you want given the
> deadline.
>
> Happy to talk it through if useful, and happy to point you at two people who take report-only
> work if that's the direction you go.

What makes it work: no in the first sentence, the reason stated without hedging, an alternative
offered without pressure, and a genuinely useful referral rather than a closing pleasantry.

### Site copy

> Your first mandatory disclosure has a fixed date on it, and the part that goes wrong is almost
> never the writing. It's the week in February when someone asks where a number came from and the
> honest answer is that four people each did a reasonable thing and nobody owns the join.
>
> I build the inventory before anyone drafts a sentence. Every figure traces to something an
> assurance provider can inspect, every estimate carries the tier it was produced at, and you get
> a model your own team can rerun next year without me in the room. Some of what comes back will
> be uncomfortable, and hearing it in October costs a great deal less than hearing it in March.

What makes it work: it opens on the reader's specific week rather than on the regulation, and the
offer is stated as what happens rather than as a set of qualities. Note that it does **not** reuse
the `core_argument` wording from `profile/company-profile.yaml` verbatim — that field is the
internal statement of the argument, and copy that merely re-types it teaches nothing about how the
argument survives translation into a voice.

## Phrasing guide

- **Refer to the practice in the first person.** "I build the inventory," not "Baseline Year
  builds." One person doing the work is the offer; the corporate third person hides it.
- **Say "estimate," never "approximation" or "indicative figure."** The plain word is the honest
  one, and the alternatives exist to soften it.
- **Say "restate," not "adjust" or "update," when a published figure changes.** Restatement is
  the term of art and carries the right weight.
- **Never write "as you know."** Either they know, and the clause is filler, or they don't, and
  it is a small insult.
- **Dates, not adverbs.** "Thursday" rather than "shortly." "Before 14 March" rather than "in
  good time."
- **When quoting a range, put the wider bound first.** "Somewhere between 400 and 900 tCO2e"
  reads as an honest range; "around 400 to 900" reads as an attempt to anchor low.

## Mission and values, in full

The report is downstream of the data. That is the whole argument, and everything else follows.

Mandatory disclosure arrived for a lot of mid-market companies at once, and the market that grew
to serve them is structurally optimistic. Nearly every provider in it makes more money if the
client believes their data is in better shape than it is: the strategy consultancy that skips to
the narrative, the software vendor selling a container for numbers nobody has produced, the
practice that will happily write a report over whatever the previous consultant left behind.
Nobody is paid to say "this isn't ready."

So that is the position. Build the inventory to survive an auditor's questions before writing a
sentence of the report. Trace every figure to a source a third party can inspect. Tier the data
quality honestly, including the parts that are embarrassing. Let the report describe what the
company actually has, not what it wishes it had measured.

`profile/company-profile.yaml` states the cost in one line: a restated baseline year. What that
line compresses, and what writing sometimes needs unpacked, is the shape of the damage. A
restatement is not a correction the market forgets. It arrives as a footnote, it gets picked up by
whoever is scoring the disclosure, and it re-reads every prior claim as provisional — including
the ones that were fine. The second-order cost is worse than the first: a finance team that has
been through one restatement starts hedging every future figure, which is how a reporting function
turns slow and defensive. Almost all of it is avoidable in the first cycle by one uncomfortable
conversation held early enough to act on.

Four values, in the order they get tested:

1. **Say the uncertainty out loud.** A figure with a stated confidence range is more useful than
   a confident figure, and far more defensible.
2. **The client owns the model.** If the inventory stops being maintainable the moment I leave, I
   built the wrong thing.
3. **Decline work I can't stand behind.** A disclosure ghostwritten over unchecked numbers is a
   liability with my fingerprints on it.
4. **Boring beats clever.** Reporting rewards the method a new hire can rerun next year.
