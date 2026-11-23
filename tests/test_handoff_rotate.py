"""
Handoff rotation (os/handoff_rotate.py).

What must hold: by default it writes nothing; with --apply it keeps the newest N entries and
moves the rest, unchanged and in order, to the top of the archive, writing the archive first;
nothing is ever deleted; a misordered file is refused rather than rotated; headings inside
fences and frontmatter are not entries; line endings survive.
"""

import json
import subprocess
import sys

from conftest import REPO_ROOT, load_tool

hr = load_tool("os/handoff_rotate.py", "handoff_rotate_under_test")
SCRIPT = REPO_ROOT / "os" / "handoff_rotate.py"

FRONT = '---\noperator: "ada"\narchive: "os/handoff/archive/ada.md"\n---\n\n# Handoff · ada\n\n*Newest first.*\n\n'


def entry(date, title, body="### Fixes Applied\n\n- one\n\n### Smoke Test\n\n- ran\n\n### Next Session Prompt\n\nGo on.\n\n"):
    return f"## {date} · {title}\n\n{body}"


def handoff(tmp_path, entries, front=FRONT, keep=2):
    (tmp_path / "os" / "handoff").mkdir(parents=True, exist_ok=True)
    (tmp_path / "os" / "project-state.yaml").write_text(
        f"operating_mode:\n  operators: few\n  close_mode: commit\n  handoff:\n    keep_newest: {keep}\n", encoding="utf-8")
    path = tmp_path / "os" / "handoff" / "ada.md"
    path.write_bytes((front + "".join(entries)).encode("utf-8"))
    return path


def run(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args], capture_output=True, text=True)


def test_split_is_lossless_and_ignores_fences_and_frontmatter():
    text = FRONT + entry("2026-03-02", "b", "```\n## not an entry\n```\n\n") + entry("2026-03-01", "a")
    preface, entries = hr.split_entries(text)
    assert preface + "".join(entries) == text
    assert len(entries) == 2
    assert entries[0].startswith("## 2026-03-02")


def test_newest_entry_is_the_first():
    text = FRONT + entry("2026-03-02", "newest") + entry("2026-03-01", "older")
    assert hr.newest_entry(text).startswith("## 2026-03-02 · newest")
    assert hr.newest_entry(FRONT) is None


def test_the_default_run_writes_nothing(tmp_path):
    path = handoff(tmp_path, [entry(f"2026-03-0{d}", f"s{d}") for d in (4, 3, 2, 1)])
    before = path.read_bytes()
    out = run(tmp_path, "--operator", "ada")
    assert out.returncode == 0, out.stderr
    assert "would move" in out.stdout and "s2" in out.stdout and "s1" in out.stdout
    assert path.read_bytes() == before
    assert not (tmp_path / "os" / "handoff" / "archive").exists()


def test_apply_keeps_the_newest_and_moves_the_rest_unchanged(tmp_path):
    entries = [entry(f"2026-03-0{d}", f"s{d}") for d in (4, 3, 2, 1)]
    path = handoff(tmp_path, entries)
    out = run(tmp_path, "--operator", "ada", "--apply")
    assert out.returncode == 0, out.stderr
    _, kept = hr.split_entries(path.read_text(encoding="utf-8"))
    assert [e.splitlines()[0] for e in kept] == ["## 2026-03-04 · s4", "## 2026-03-03 · s3"]
    archive = (tmp_path / "os" / "handoff" / "archive" / "ada.md").read_text(encoding="utf-8")
    _, moved = hr.split_entries(archive)
    assert [e.rstrip("\n") for e in moved] == [e.rstrip("\n") for e in entries[2:]]


def test_a_second_rotation_puts_newer_entries_on_top_of_the_archive(tmp_path):
    path = handoff(tmp_path, [entry(f"2026-03-0{d}", f"s{d}") for d in (4, 3, 2, 1)])
    run(tmp_path, "--operator", "ada", "--apply")
    text = path.read_text(encoding="utf-8")
    preface, kept = hr.split_entries(text)
    path.write_text(preface + entry("2026-03-05", "s5") + "".join(kept), encoding="utf-8")
    assert run(tmp_path, "--operator", "ada", "--apply").returncode == 0
    _, archived = hr.split_entries((tmp_path / "os" / "handoff" / "archive" / "ada.md").read_text(encoding="utf-8"))
    assert [e.splitlines()[0] for e in archived] == ["## 2026-03-03 · s3", "## 2026-03-02 · s2", "## 2026-03-01 · s1"]


def test_nothing_is_lost_across_a_rotation(tmp_path):
    entries = [entry(f"2026-03-0{d}", f"s{d}") for d in (5, 4, 3, 2, 1)]
    path = handoff(tmp_path, entries, keep=1)
    run(tmp_path, "--operator", "ada", "--apply")
    both = path.read_text(encoding="utf-8") + (tmp_path / "os" / "handoff" / "archive" / "ada.md").read_text(encoding="utf-8")
    for e in entries:
        assert e.rstrip("\n") in both


def test_a_misordered_file_is_refused_and_left_alone(tmp_path):
    path = handoff(tmp_path, [entry("2026-03-01", "old"), entry("2026-03-04", "new"), entry("2026-02-01", "older")], keep=1)
    before = path.read_bytes()
    out = run(tmp_path, "--operator", "ada", "--apply")
    assert out.returncode == 1
    assert "not newest first" in out.stderr
    assert path.read_bytes() == before


def test_crlf_line_endings_survive(tmp_path):
    entries = [entry(f"2026-03-0{d}", f"s{d}").replace("\n", "\r\n") for d in (3, 2, 1)]
    path = handoff(tmp_path, entries, front=FRONT.replace("\n", "\r\n"), keep=1)
    run(tmp_path, "--operator", "ada", "--apply")
    kept = path.read_bytes()
    assert b"\r\n" in kept and b"\n" not in kept.replace(b"\r\n", b"")
    archive = (tmp_path / "os" / "handoff" / "archive" / "ada.md").read_bytes()
    assert entries[1].encode() in archive


def test_keep_newest_must_be_a_positive_integer(tmp_path):
    handoff(tmp_path, [entry("2026-03-01", "a")])
    for bad in ("0", "-1"):
        assert run(tmp_path, "--operator", "ada", "--keep", bad).returncode == 2
    (tmp_path / "os" / "project-state.yaml").write_text("operating_mode:\n  handoff:\n    keep_newest: true\n", encoding="utf-8")
    out = run(tmp_path, "--operator", "ada")
    assert out.returncode == 2 and "positive integer" in out.stderr


def test_an_unresolved_operator_is_an_error(tmp_path):
    handoff(tmp_path, [entry("2026-03-01", "a")])
    out = run(tmp_path)
    assert out.returncode == 2 and "pass --operator or --all" in out.stderr


def test_an_operator_id_cannot_walk_out_of_the_folder(tmp_path):
    handoff(tmp_path, [entry("2026-03-01", "a")])
    out = run(tmp_path, "--operator", "../../etc/passwd")
    assert out.returncode == 2


def test_all_reports_every_handoff_file(tmp_path):
    handoff(tmp_path, [entry(f"2026-03-0{d}", f"s{d}") for d in (3, 2, 1)])
    (tmp_path / "os" / "handoff" / "lin.md").write_text(FRONT.replace("ada", "lin") + entry("2026-03-01", "x"), encoding="utf-8")
    out = run(tmp_path, "--all", "--json")
    data = json.loads(out.stdout)
    assert {d["handoff"] for d in data} == {"os/handoff/ada.md", "os/handoff/lin.md"}


def test_the_shipped_template_parses_as_one_entry():
    text = (REPO_ROOT / "os" / "handoff.template.md").read_text(encoding="utf-8")
    preface, entries = hr.split_entries(text)
    assert len(entries) == 1 and entries[0].startswith("## [YYYY-MM-DD]")
    assert "## YYYY-MM-DD · <one-line title>" in preface  # the contract comment is not an entry


# ── an archive that is not a file of its own is refused (review finding) ─────


def test_an_archive_that_is_the_handoff_itself_is_refused_and_nothing_is_lost(tmp_path):
    for spelling in ("os/handoff/ada.md", "os/handoff/ADA.md", "os/handoff/./ada.md", "os/handoff/lin.md"):
        root = tmp_path / spelling.replace("/", "_")
        path = handoff(root, [entry(f"2026-03-0{d}", f"s{d}") for d in (3, 2, 1)],
                       front=FRONT.replace("os/handoff/archive/ada.md", spelling), keep=1)
        before = path.read_bytes()
        out = run(root, "--operator", "ada", "--apply")
        assert out.returncode == 2, (spelling, out.stdout, out.stderr)
        assert path.read_bytes() == before, spelling


def test_a_handoff_symlinked_outside_the_root_is_an_error_not_a_crash(tmp_path):
    import os
    import pytest
    root = tmp_path / "inst"
    handoff(root, [entry("2026-03-01", "a")])
    elsewhere = tmp_path / "elsewhere.md"
    elsewhere.write_text(FRONT + entry("2026-03-01", "x"), encoding="utf-8")
    link = root / "os" / "handoff" / "lin.md"
    try:
        os.symlink(str(elsewhere), str(link))
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    out = run(root, "--operator", "lin")
    assert out.returncode == 2 and "Traceback" not in out.stderr and "outside the instance root" in out.stderr


def test_a_handoff_that_is_not_utf8_is_an_error_not_a_crash(tmp_path):
    path = handoff(tmp_path, [entry("2026-03-01", "a")])
    path.write_bytes(b"# Handoff\n\n## 2026-03-01 \xb7 caf\xe9\n")
    out = run(tmp_path, "--operator", "ada")
    assert out.returncode == 2 and "Traceback" not in out.stderr and "not UTF-8" in out.stderr


# ── CV1.1 (LA2-F6, F7) ───────────────────────────────────────────────────────


def test_apply_refuses_an_undated_level_two_section_rather_than_count_it(tmp_path):
    path = handoff(tmp_path, ["## How to read this file\n\nNewest first.\n\n"]
                   + [entry(f"2026-0{m}-01", f"s{m}") for m in (4, 3, 2, 1)], keep=3)
    before = path.read_text(encoding="utf-8")
    out = run(tmp_path, "--operator", "ada", "--apply")
    assert out.returncode == 1 and "no date" in out.stderr
    assert path.read_text(encoding="utf-8") == before


def test_an_unclosed_frontmatter_is_an_error_not_an_empty_file(tmp_path):
    path = handoff(tmp_path, [entry("2026-04-01", "s")])
    path.write_text("---\noperator: ada\n" + entry("2026-04-01", "s"), encoding="utf-8")
    out = run(tmp_path, "--operator", "ada")
    assert out.returncode == 2 and "never closes" in out.stderr


def test_an_archive_path_that_is_a_directory_is_refused_cleanly(tmp_path):
    path = handoff(tmp_path, [entry(f"2026-0{m}-01", f"s{m}") for m in (3, 2, 1)], keep=1)
    (tmp_path / "os" / "handoff" / "archive" / "ada.md").mkdir(parents=True)
    before = path.read_text(encoding="utf-8")
    out = run(tmp_path, "--operator", "ada", "--apply")
    assert out.returncode == 2 and "directory" in out.stderr and "Traceback" not in out.stderr
    assert path.read_text(encoding="utf-8") == before


def test_all_skips_a_readme_in_the_handoff_folder(tmp_path):
    handoff(tmp_path, [entry("2026-04-01", "s")])
    (tmp_path / "os" / "handoff" / "README.md").write_text("# Handoffs\n\n## How these work\n\nText.\n",
                                                           encoding="utf-8")
    assert "README" not in run(tmp_path, "--all").stdout
