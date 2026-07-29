# Contributing to Keel

Thanks for considering a contribution. This project is a template and documentation set, not a
running service, so most contributions are edits to templates, docs, the starter skills, or the
evaluation cases.

## Before you open a pull request

For anything beyond a typo or a broken link, open an issue first and describe what you want to
change and why. This project favors discussion before changes to shared templates, since a change
that helps one operator's practice can quietly break the assumptions another operator built on top
of.

If your change touches code (`skills/registry/skill-registry.py` or `skills/evals/lint_cases.py`),
run the tests:

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional, keeps this off your system Python
python3 -m pip install -r requirements.txt -r requirements-dev.txt
pytest
```

If it touches the eval cases, run the linter too (CI runs both, so you may as well see the result
first):

```bash
python3 skills/evals/lint_cases.py
```

A change to the registry's scoring belongs in the `TUNING` block at the top of
`skill-registry.py`, not scattered through the function bodies, and its docstrings name those
constants rather than restating their values. The test suite enforces both. That is deliberate: a
number written into prose survives a re-tuning pass that only edits the code, and then it is
quietly describing a scale the code no longer uses.

## Developer Certificate of Origin (DCO)

This project uses the [Developer Certificate of Origin](https://developercertificate.org/) instead
of a Contributor License Agreement. Every commit must be signed off, certifying that you wrote the
change (or otherwise have the right to submit it) under the project's license.

Add a sign-off line to every commit:

```bash
git commit -s -m "Your commit message"
```

This appends a line to your commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

Use your real name and a real, reachable email address. Pull requests with unsigned commits will
be asked to add sign-off before merge.

## Schema changes

The templates in `os/` and `profile/` define shapes that other people's filled-in instances depend
on. They stay templates: filled-in content belongs only under `examples/`, where it must describe a
clearly invented firm and say so visibly at the top of every file (see `examples/README.md`).

Treat schema changes conservatively:

1. Open an issue describing the change and the problem it solves before writing the patch.
2. Prefer additive changes (new optional fields) over changes that alter or remove existing fields.
3. If a field must change shape, note the migration path for anyone with an already-filled-in copy.
4. Get at least one maintainer review before merging any schema change, even a small one.

## What to contribute

- Fixes to broken links, typos, or unclear instructions in the docs.
- New eval cases for the starter skills, or better ones than what's here.
- Structural improvements to a template that make it easier to fill in without changing its shape.
- Reports of anything that reads as company-specific and shouldn't be (see `SECURITY.md` for
  anything sensitive).

## What belongs elsewhere

This repository is the free, open-source scaffold. Requests for HeyHi to configure or calibrate
this scaffold for your specific practice are a separate conversation. See the README's
"Working with HeyHi" section.

## Code of conduct

Participation in this project is governed by `CODE_OF_CONDUCT.md`.
