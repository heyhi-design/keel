# The Skill Registry

The registry is how your agent finds the right skill for a task instead of loading every
skill it owns into every session. You describe what you need in ordinary language, the
search returns the few capabilities most likely to serve it, and only those get loaded.

This matters more the more skills you have. Five skills fit in a session's context without
anyone noticing the cost. Forty do not, and the failure is quiet: the context fills with
procedures the task will never touch, and the work gets worse without ever announcing why.

## The two files

| File | What it is |
|---|---|
| `skill-registry.template.yaml` | The index itself: one entry per capability. Ships populated with the seven starter skills, so the search works before you have written anything of your own. |
| `skill-registry.py` | The search over that index. Keyword and tag matching, a confidence gate, and a token-savings report. |

Rename the template to `skill-registry.yaml` (drop the `.template`) so the script finds it
by default, or pass `--registry skill-registry.template.yaml` explicitly.

## Running it

Install once, from the repository root (that is where `requirements.txt` lives). A virtual
environment keeps this off your system Python:

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
python3 -m pip install -r requirements.txt
```

Then, from this directory (`skills/registry/`). These run against the seven starter skills the
template ships with, so they work before you have written anything of your own:

```bash
# What should handle this task?
python3 skill-registry.py --registry skill-registry.template.yaml "draft a proposal"
#   -> Proposal  [skill]

# Same, but ask the search how sure it is before you act on the answer.
python3 skill-registry.py --registry skill-registry.template.yaml "where are we" --confidence
#   -> Confidence: confident   ->  Project Scanner  [skill]

# What is this registry costing you, and what is discovery saving?
python3 skill-registry.py --registry skill-registry.template.yaml --stats

# Everything currently registered.
python3 skill-registry.py --registry skill-registry.template.yaml --list
```

Once you rename the file to `skill-registry.yaml`, drop the `--registry` flag: the script
looks for that name by default.

One thing worth knowing about `--stats`, and it is not a bug: at the seven starter skills it
ships with, the registry already reports a positive saving. Cut it down to one or two
capabilities and the number goes **negative**, because the flat cost of the discovery step is
larger than the whole index at that size. Savings compound with the number of skills, so the
figure only climbs from here.

## The per-entry schema

Every capability in the registry carries these fields:

| Field | What it does |
|---|---|
| `id` | Unique kebab-case identifier. |
| `name` | Human-readable name. |
| `type` | `skill`, `reference`, or `tool`. |
| `description` | Natural-language description. Matched against the query, so write it the way you would actually describe the task. |
| `semantic_tags` | Keywords that widen the search surface. |
| `trigger_patterns` | Exact phrases that activate this capability at the highest weight. |
| `dependencies` | Files co-loaded with this capability. Paths that exist on disk. |
| `not_for` | Phrases that *suppress* this capability. See below. |
| `load_cost_tokens` | Estimated token cost when loaded. Roughly `character_count / 4`. |
| `location` | Path to the capability file. |

Write `trigger_patterns` as bare phrases with no leading or trailing punctuation: matching is word-boundary anchored, so a pattern like `where are we?` never fires, while the bare `where are we` still matches a query that ends in a question mark.

## `not_for` is the field that earns its keep

Two skills that sound alike will collide. An invoice *drafter* and an invoice *auditor*
share almost all their vocabulary, and a query about invoices matches both about equally
well. Positive scoring alone cannot separate them, because there is nothing to separate on.

`not_for` is how you say what a skill is *not* for, and it carries negative weight:

```yaml
not_for:
  - "Reviewing an invoice that already exists (use invoice-auditor)"
```

A query that matches a `not_for` clause is steered away from that capability and toward the
one the clause names. The trailing `(use other-skill)` hint is documentation for whoever
reads the registry later; it is stripped before matching and never affects the score.

Write a `not_for` clause the first time two skills collide, not before. It is a fix for an
observed problem, and clauses written speculatively tend to suppress the wrong things.

### A clause can read as correct and do nothing

The penalty only applies when the clause's *leading* meaningful word prefix-matches a term
in the query, and at least two query terms match the clause overall. That first condition
is a narrow gate: a clause can be grammatically fine, aimed at the right query, and still
never fire, because the word it happens to lead with never shows up the way the query is
actually phrased. Nothing in the registry tells you this happened -- an inert clause looks
identical to a working one until you measure it, and the two skills it was meant to
separate keep colliding.

Before you trust a new `not_for` clause, verify it, in this order:

1. **Run the host skill's own trigger phrases back through the search.** The skill the
   clause lives on should still win all of them. A clause that accidentally penalizes its
   own skill is the most common way this goes wrong.
2. **Run two or three realistic queries the clause is meant to redirect.** Confirm the
   *other* skill -- the one named in the `(use ...)` hint -- now wins them.
3. **Don't lead the clause with the single most common word in the skill's own domain.**
   That word is exactly the one most likely to also open the skill's own trigger phrases,
   which is what breaks step 1.

Correct-looking English is not evidence a clause fires. Verify by measurement: swap the
clause in and out, and read the actual scores, rather than re-reading the wording.

## Tuning

Every number that shapes a routing decision -- the scoring weights, the `not_for` penalty,
and the three confidence thresholds -- is a named constant in the `TUNING` block at the top
of `skill-registry.py`. There are no scoring numbers buried anywhere else in the file, and
the test suite enforces that: the docstrings cite those constants by name and are not
allowed to restate their values, because a number written into prose goes stale the first
time someone re-tunes the code and it goes stale silently.

They ship as generic starting defaults, not as calibrated values. The right numbers depend
on how many skills you have registered and how you write your triggers and tags. Once you
have a handful in the registry, tune them against a small set of known
query-to-expected-skill cases of your own. Nothing in that block is a magic constant.

## The confidence gate

`--confidence` classifies a result three ways, and the third one is the point of the whole
mechanism:

- **confident** : the top result pulls clearly ahead of the runner-up. (When it is the *only* result, there is no gap to measure, so it has to clear the score bar outright instead.) Load it and go.
- **ambiguous** : something matched, but two candidates are close enough that the search should not be the one choosing. Surface both and ask.
- **insufficient** : nothing cleared the floor. Say so, rather than loading the least-bad guess.

A registry that returns "insufficient" honestly is more useful than one that always returns
something. The wrong skill loaded confidently is worse than no skill at all, because it
looks like an answer.

## When routing starts to misfire

`--log-gaps` appends one record per search to `score-gap-log.jsonl`: the query, the top
score, and the gap to the runner-up. If the gap is narrow on more than about a quarter of
your queries, keyword matching has stopped discriminating well for the size your registry
has grown to, and it is time to consider a semantic-embedding backend. The search function
and the registry schema are the interface; a different scorer can sit behind them without
anything else changing.
