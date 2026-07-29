"""
The eval-case linter.

It is the gate on the eval corpus, and CI fails on it, so it needs to be right about both
answers: it must reject a malformed case, and it must not reject a well-formed one. The
second half matters more than it looks. A linter that is wrong in the strict direction
teaches people to delete the case rather than fix the linter, and the case it will teach
them to delete is the awkward one that was catching something.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT

LINTER = REPO_ROOT / "skills" / "evals" / "lint_cases.py"


def _load_linter():
    spec = importlib.util.spec_from_file_location("lint_cases", LINTER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["lint_cases"] = module
    spec.loader.exec_module(module)
    return module


lint = _load_linter()


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(LINTER), *args],
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
        timeout=30,
    )


def _case(**overrides):
    case = {
        "id": "sample-01-does-a-thing",
        "description": "A well-formed case.",
        "input": "Some input to run the skill against.",
        "expected_findings": ["It finds the thing."],
        "pass_criteria": "The thing is found and named.",
    }
    case.update(overrides)
    return case


# ── the real corpus passes ───────────────────────────────────────────────────


def test_the_shipped_eval_cases_are_all_well_formed():
    result = _run()
    assert result.returncode == 0, result.stderr
    assert "well-formed" in result.stdout


def test_it_runs_from_any_working_directory(tmp_path):
    """CI invokes it from the repo root; a person invokes it from wherever they are."""
    for cwd in (REPO_ROOT, REPO_ROOT / "skills" / "evals", tmp_path):
        assert _run(cwd=cwd).returncode == 0, f"failed when run from {cwd}"


def test_quiet_suppresses_the_success_line_only():
    assert _run("--quiet").returncode == 0
    assert _run("--quiet").stdout == ""


# ── it rejects what it promises to reject ────────────────────────────────────


@pytest.mark.parametrize("missing", ["id", "description", "input", "pass_criteria"])
def test_a_case_missing_any_required_string_field_is_rejected(missing):
    case = _case()
    del case[missing]
    problems = lint.lint_case(case, "where")
    assert any(f"missing required field: {missing}" in p for p in problems)


def test_a_case_missing_expected_findings_is_rejected():
    case = _case()
    del case["expected_findings"]
    assert any("missing required field: expected_findings" in p for p in lint.lint_case(case, "w"))


def test_a_field_of_the_wrong_type_is_rejected():
    assert lint.lint_case(_case(id=42), "w")
    assert lint.lint_case(_case(expected_findings="not a list"), "w")
    assert lint.lint_case(_case(expected_findings=[1, 2]), "w")
    assert lint.lint_case(_case(pass_criteria="   "), "w")
    assert lint.lint_case("not even a mapping", "w")


def test_duplicate_case_ids_across_files_are_rejected(tmp_path, monkeypatch):
    """Ids have to be unique corpus-wide, so a failing case can be named without its file."""
    evals = tmp_path / "skills" / "evals"
    for skill in ("alpha", "beta"):
        (evals / skill).mkdir(parents=True)
        (evals / skill / "cases.yaml").write_text(
            yaml.safe_dump({"cases": [_case(id="collides-01")]}), encoding="utf-8"
        )

    monkeypatch.setattr(lint, "EVALS_DIR", evals)
    assert lint.main([]) == 1


# ── it does NOT reject what it must not reject ───────────────────────────────


def test_an_empty_expected_findings_list_is_accepted():
    """
    The case that guards this whole linter against being too strict.

    A case expecting ZERO findings is how you catch a skill that manufactures a finding
    for every input it is handed -- it is the most valuable case in a suite, and the
    corpus ships one (voice-04-clean-pass). A truthiness check instead of a type check
    would fail it, and the path of least resistance would be to delete it.
    """
    assert lint.lint_case(_case(expected_findings=[]), "where") == []


def test_the_real_zero_findings_case_still_passes():
    """The same guarantee, against the actual shipped case rather than a stand-in."""
    cases = yaml.safe_load((REPO_ROOT / "skills/evals/voice/cases.yaml").read_text())["cases"]
    clean_pass = next(c for c in cases if c["expected_findings"] == [])
    assert lint.lint_case(clean_pass, "voice/cases.yaml") == []


def test_an_absent_fixture_is_accepted():
    """`fixture` is optional: a case whose input is self-contained has nothing to set up."""
    assert "fixture" not in _case()
    assert lint.lint_case(_case(), "where") == []


# ── a file it cannot read is a failure, never a silent skip ──────────────────


def test_an_unparseable_file_is_reported_not_skipped(tmp_path, monkeypatch):
    evals = tmp_path / "evals"
    (evals / "broken").mkdir(parents=True)
    (evals / "broken" / "cases.yaml").write_text("cases:\n  - id: [unclosed\n", encoding="utf-8")

    monkeypatch.setattr(lint, "EVALS_DIR", evals)
    assert lint.main([]) == 1


def test_a_file_that_is_not_utf8_is_reported_not_crashed(tmp_path, monkeypatch):
    evals = tmp_path / "evals"
    (evals / "binary").mkdir(parents=True)
    (evals / "binary" / "cases.yaml").write_bytes(b"\xff\xfe\x00garbage")

    monkeypatch.setattr(lint, "EVALS_DIR", evals)
    assert lint.main([]) == 1  # a UnicodeDecodeError traceback would not be a 1


def test_a_directory_where_a_cases_file_belongs_is_reported(tmp_path, monkeypatch):
    evals = tmp_path / "evals"
    (evals / "odd" / "cases.yaml").mkdir(parents=True)  # a directory by that name

    monkeypatch.setattr(lint, "EVALS_DIR", evals)
    assert lint.main([]) == 1


def test_an_eval_tree_with_no_cases_at_all_is_an_error(tmp_path, monkeypatch):
    """Finding nothing to check is not the same as everything checking out."""
    empty = tmp_path / "evals"
    empty.mkdir()

    monkeypatch.setattr(lint, "EVALS_DIR", empty)
    assert lint.main([]) == 1
