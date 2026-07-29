#!/usr/bin/env python3
"""
Structural linter for eval cases.

Checks that every case in every skills/evals/<skill>/cases.yaml carries the fields a case
needs to be runnable by a person who did not write it: an id to refer to it by, a
description of what it is probing, an input to run, the findings you expect back, and the
criteria that decide pass from fail. Case ids must be unique across the whole eval corpus,
so that a failing case can be named without also naming its file.

What this does NOT check is whether a case is any *good* -- whether the input is realistic,
whether the expected findings are the right ones, whether the pass criteria are strict
enough to catch a skill that fakes it. That judgment is yours, and no linter substitutes
for it. This only guarantees that a case is shaped like a case, which is the part a machine
can be trusted with.

Usage:
    python3 skills/evals/lint_cases.py           # lint every skill's cases
    python3 skills/evals/lint_cases.py --quiet   # print only failures

Exits 0 when every case is well-formed, 1 otherwise.

Requires PyYAML (see requirements.txt).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only when PyYAML is absent
    print("error: PyYAML is required. Install it with: python3 -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


EVALS_DIR = Path(__file__).resolve().parent

# A case must carry all five. `fixture` is deliberately not required: a case whose input
# is self-contained (a proposal brief, say) has nothing to set up, and forcing an empty
# fixture onto it would be ceremony rather than structure.
REQUIRED_STRING_FIELDS = ("id", "description", "input", "pass_criteria")
REQUIRED_LIST_FIELDS = ("expected_findings",)


class LintError(Exception):
    """A cases file that could not be read or parsed at all, as opposed to one with bad cases."""


def lint_case(case: object, where: str) -> list[str]:
    """Return a list of problems with one case. An empty list means it is well-formed."""
    if not isinstance(case, dict):
        return [f"{where}: case is not a mapping (got {type(case).__name__})"]

    problems: list[str] = []
    case_id = case.get("id") if isinstance(case.get("id"), str) else None
    label = f"{where} [{case_id}]" if case_id else where

    for field in REQUIRED_STRING_FIELDS:
        value = case.get(field)
        if value is None:
            problems.append(f"{label}: missing required field: {field}")
        elif not isinstance(value, str):
            problems.append(f"{label}: {field} must be a string, got {type(value).__name__}")
        elif not value.strip():
            problems.append(f"{label}: {field} is empty")

    for field in REQUIRED_LIST_FIELDS:
        value = case.get(field)
        if value is None:
            problems.append(f"{label}: missing required field: {field}")
        elif not isinstance(value, list):
            # An empty list is legitimate and load-bearing: a case that expects zero
            # findings is how you catch a skill that manufactures a finding for every
            # input it is handed. Absence is the error; emptiness is a real expectation.
            problems.append(f"{label}: {field} must be a list, got {type(value).__name__}")
        elif not all(isinstance(item, str) for item in value):
            problems.append(f"{label}: every entry in {field} must be a string")

    return problems


def _load(path: Path):
    """Read and parse one cases.yaml. Raises LintError with a readable message on any failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        # A cases file is prose. If it does not decode as UTF-8 it is not a cases file,
        # and saying so is more use than a decoder traceback.
        raise LintError(f"is not valid UTF-8 text: {exc}") from exc
    except OSError as exc:
        # Covers a directory named cases.yaml, a broken or looping symlink, and a
        # permissions problem. Each has to be reported: a file the linter cannot read is
        # a file it cannot vouch for, and silently skipping it would turn an unreadable
        # eval corpus into a green check.
        raise LintError(f"cannot be read: {exc.strerror or exc}") from exc

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise LintError(f"does not parse as YAML: {exc}") from exc


def lint_file(path: Path) -> list[str]:
    """Return a list of problems with one cases.yaml."""
    rel = path.relative_to(EVALS_DIR.parent.parent)

    try:
        data = _load(path)
    except LintError as exc:
        return [f"{rel}: {exc}"]

    if not isinstance(data, dict) or "cases" not in data:
        return [f"{rel}: no top-level 'cases:' key"]

    cases = data["cases"]
    if not isinstance(cases, list) or not cases:
        return [f"{rel}: 'cases:' must be a non-empty list"]

    problems: list[str] = []
    for i, case in enumerate(cases):
        problems.extend(lint_case(case, f"{rel}: case #{i + 1}"))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint the structure of every eval case.")
    parser.add_argument("--quiet", action="store_true", help="Print only failures.")
    args = parser.parse_args(argv)

    case_files = sorted(EVALS_DIR.glob("*/cases.yaml"))
    if not case_files:
        print(f"error: no eval cases found under {EVALS_DIR}", file=sys.stderr)
        return 1

    problems: list[str] = []
    seen_ids: dict[str, str] = {}
    case_count = 0

    for path in case_files:
        file_problems = lint_file(path)
        problems.extend(file_problems)
        if file_problems:
            continue

        rel = path.relative_to(EVALS_DIR.parent.parent)
        for case in _load(path)["cases"]:
            case_count += 1
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                continue  # already reported by lint_case
            if case_id in seen_ids:
                problems.append(
                    f"{rel}: duplicate case id '{case_id}' (already used in {seen_ids[case_id]})"
                )
            else:
                seen_ids[case_id] = str(rel)

    if problems:
        print(f"Eval cases: {len(problems)} problem(s) found.\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Eval cases: {case_count} case(s) across {len(case_files)} skill(s), all well-formed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
