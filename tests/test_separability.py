"""
Tests for the keelson separability check (keelson/separability_check.py).

Two things have to be true for the check to be worth running in CI:

  1. It passes over keel's own tree -- a green run here is a real signal, not a vacuous one,
     because at least one file really does declare `origin: keel` and really is scanned.
  2. It fails when it should -- a file that claims keel origin and then reaches into
     instance-private content is caught, and the three ways a file can look guilty but be
     innocent (an instance-tagged file, an untagged file, a prose mention) are not.

The module's filename has no hyphen, but it is not on the import path, so it is loaded from
its location the same way conftest loads the registry module.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "keelson" / "separability_check.py"


def _load_check_module():
    spec = importlib.util.spec_from_file_location("separability_check", MODULE_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - only if the file moves
        raise ImportError(f"Could not load the separability check from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sc = _load_check_module()
PRIVATE = list(sc.DEFAULT_PRIVATE)


# ── it passes over keel's own tree, non-vacuously ────────────────────────────


def test_the_check_passes_over_the_keel_tree():
    """main() exits 0 over the whole repository as shipped."""
    assert sc.main([str(REPO_ROOT), "--quiet"]) == 0


def test_at_least_one_keel_tagged_file_is_actually_scanned():
    """
    Guards against a green run that is green only because nothing was checked. keel ships at
    least the keelson README tagged `origin: keel`; if that count ever drops to zero, the
    tree-passes test above has quietly stopped meaning anything.
    """
    _violations, keel_tagged = sc.scan(REPO_ROOT, PRIVATE)
    assert keel_tagged >= 1


# ── it catches a real leak, in each reference shape ──────────────────────────


def test_a_keel_tagged_python_import_of_an_instance_path_is_flagged(tmp_path):
    (tmp_path / "bad.py").write_text("# origin: keel\nimport examples.secret\n", encoding="utf-8")
    violations, _ = sc.scan(tmp_path, PRIVATE)
    assert [v[0] for v in violations] == ["bad.py"]


def test_a_keel_tagged_quoted_instance_path_is_flagged(tmp_path):
    (tmp_path / "bad.py").write_text('# origin: keel\nSEED = "examples/private.yaml"\n', encoding="utf-8")
    violations, _ = sc.scan(tmp_path, PRIVATE)
    assert [v[0] for v in violations] == ["bad.py"]


def test_a_keel_tagged_markdown_link_into_an_instance_path_is_flagged(tmp_path):
    (tmp_path / "bad.md").write_text("<!-- origin: keel -->\n\n[x](examples/secret.md)\n", encoding="utf-8")
    violations, _ = sc.scan(tmp_path, PRIVATE)
    assert [v[0] for v in violations] == ["bad.md"]


def test_main_returns_one_when_a_leak_is_present(tmp_path):
    (tmp_path / "bad.py").write_text("# origin: keel\nimport examples.secret\n", encoding="utf-8")
    assert sc.main([str(tmp_path), "--quiet"]) == 1


# ── it does not cry wolf ─────────────────────────────────────────────────────


def test_an_instance_tagged_file_may_reference_instance_content(tmp_path):
    """The whole point of `origin: instance` is that this file is not being lifted."""
    (tmp_path / "local.py").write_text("# origin: instance\nimport examples.secret\n", encoding="utf-8")
    violations, keel_tagged = sc.scan(tmp_path, PRIVATE)
    assert violations == []
    assert keel_tagged == 0


def test_an_untagged_file_is_skipped(tmp_path):
    """No tag is no claim: an untagged file is not the check's business, references and all."""
    (tmp_path / "whatever.py").write_text("import examples.secret\n", encoding="utf-8")
    violations, keel_tagged = sc.scan(tmp_path, PRIVATE)
    assert violations == []
    assert keel_tagged == 0


def test_prose_and_backticked_mentions_are_not_references(tmp_path):
    """
    A document has to be able to name the boundary it keeps. A keel-tagged file that mentions
    the instance-private path in prose or a backticked span -- but never links or imports it
    -- is clean. This is what lets keelson/README.md carry `origin: keel` honestly.
    """
    body = "<!-- origin: keel -->\n\nDo not point into the examples directory or `examples/foo`.\n"
    (tmp_path / "doc.md").write_text(body, encoding="utf-8")
    violations, keel_tagged = sc.scan(tmp_path, PRIVATE)
    assert violations == []
    assert keel_tagged == 1


def test_a_body_line_that_looks_like_a_tag_does_not_tag_a_markdown_file(tmp_path):
    """Only the first non-empty line carries a Markdown tag; a fenced example below does not."""
    body = "# A heading, not a tag\n\n```\n<!-- origin: keel -->\n```\n[x](examples/secret.md)\n"
    (tmp_path / "doc.md").write_text(body, encoding="utf-8")
    violations, keel_tagged = sc.scan(tmp_path, PRIVATE)
    assert violations == []
    assert keel_tagged == 0


# ── the private set is configurable ──────────────────────────────────────────


def test_an_extra_private_path_is_honored(tmp_path):
    (tmp_path / "bad.py").write_text('# origin: keel\nP = "clients/acme.md"\n', encoding="utf-8")
    assert sc.scan(tmp_path, PRIVATE)[0] == []  # not private by default
    assert [v[0] for v in sc.scan(tmp_path, PRIVATE + ["clients/"])[0]] == ["bad.py"]
