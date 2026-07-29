# Eval Cases

Each starter skill ships with a small set of eval cases, one `cases.yaml` per skill. A case is a
known input paired with the result you expect a working skill to produce. They are how you tell a
skill that works from one that only looks like it does, and how you catch a regression when you
edit a skill later.

## What a case is

Every case carries five fields (see `proposal/cases.yaml` for worked examples):

| Field | What it is |
|---|---|
| `id` | A unique name for the case, so a failure can be referred to without naming its file. Ids must be unique across every skill's cases. |
| `description` | What this case is probing: the specific behavior it is meant to catch. |
| `input` | The material you hand the skill: a draft, a log, a snippet. |
| `expected_findings` | What a working skill should report back. An empty list is a real expectation: it says "a correct skill finds nothing wrong here," which is how you catch a skill that manufactures a problem for every input. |
| `pass_criteria` | What decides pass from fail: the bar the result has to clear, stated specifically enough that you are not re-litigating it every run. |

A sixth field, `fixture`, is optional, for a case whose input needs something set up first. A case
whose input is self-contained does not need one.

## How to run a case

These cases are run by hand, or by your agent, not by an automated harness. There is no runner that
executes a skill and asserts on its output, because a skill's output is prose to be judged, not a
value to be compared byte for byte. To run one:

1. Read the case's `input` (and set up its `fixture`, if it has one).
2. Apply the skill's own procedure to that input, the same way you would in real work.
3. Compare what you got back against `expected_findings`, and decide pass or fail by
   `pass_criteria`.

Run a skill's cases when you first fill it in, and again whenever you change it. A skill you have
not run against its cases is a draft, not a deployed skill.

## Linting the cases

`lint_cases.py` checks that every case is *shaped* like a case: that it has all the required fields,
that they are the right types, and that no two cases share an id. It does not check whether a case
is any good; that judgment is yours. Run it after you write or edit any case:

```bash
python3 skills/evals/lint_cases.py           # lint every skill's cases
python3 skills/evals/lint_cases.py --quiet   # print only failures
```

It exits 0 when every case is well-formed, 1 otherwise, so you can wire it into CI if you want a
guard against a malformed case slipping in.
