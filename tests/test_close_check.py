"""
The keelson close check (keelson/close_check.py).

It reads the persisted Exit Gate report by slot name. What has to hold: Flavor A needs its
three slots, Flavor B (either extra slot present) all five; an empty slot, or one holding only
a comment or an unfilled placeholder, fails; a link-only entry passes in PR close mode and
fails in commit mode; no entry at all fails; a PR body is read at level 2.
"""

import subprocess
import sys

from conftest import REPO_ROOT, load_tool

cc = load_tool("keelson/close_check.py", "close_check_under_test")
SCRIPT = REPO_ROOT / "keelson" / "close_check.py"

GOOD = "### Fixes Applied\n\n- fixed a link\n\n### Smoke Test\n\n- pytest: 12 passed\n\n### Next Session Prompt\n\nStart at the index.\n"


def instance(tmp_path, entries, close_mode="commit"):
    (tmp_path / "os" / "handoff").mkdir(parents=True)
    (tmp_path / "os" / "project-state.yaml").write_text(f"operating_mode:\n  close_mode: {close_mode}\n", encoding="utf-8")
    path = tmp_path / "os" / "handoff" / "ada.md"
    path.write_text('---\noperator: "ada"\n---\n\n# Handoff · ada\n\n' + "".join(entries), encoding="utf-8")
    return path


def run(tmp_path, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(tmp_path), *map(str, args)], capture_output=True, text=True)


def test_a_full_flavor_a_entry_passes(tmp_path):
    path = instance(tmp_path, ["## 2026-03-02 · work\n\n" + GOOD])
    out = run(tmp_path, path)
    assert out.returncode == 0, out.stderr


def test_a_missing_slot_fails(tmp_path):
    path = instance(tmp_path, ["## 2026-03-02 · work\n\n" + GOOD.replace("### Smoke Test\n\n- pytest: 12 passed\n\n", "")])
    out = run(tmp_path, path)
    assert out.returncode == 1 and "missing slot: Smoke Test" in out.stderr


def test_an_empty_comment_only_or_placeholder_slot_fails(tmp_path):
    for filler in ("", "<!-- fill this in -->\n", "- [One line per fix, or \"none\".]\n"):
        body = GOOD.replace("- fixed a link\n", filler)
        path = instance(tmp_path / f"case{len(filler)}", ["## 2026-03-02 · work\n\n" + body])
        out = run(tmp_path / f"case{len(filler)}", path)
        assert out.returncode == 1 and "empty slot: Fixes Applied" in out.stderr, filler


def test_flavor_b_needs_all_five(tmp_path):
    path = instance(tmp_path, ["## 2026-03-02 · plan work\n\n" + GOOD + "\n### Findings Integration\n\n- folded into the plan\n"])
    out = run(tmp_path, path)
    assert out.returncode == 1 and "missing slot: Session Integrity" in out.stderr


def test_only_the_newest_entry_is_checked_unless_all(tmp_path):
    path = instance(tmp_path, ["## 2026-03-02 · new\n\n" + GOOD, "## 2026-03-01 · old\n\n### Fixes Applied\n\n"])
    assert run(tmp_path, path).returncode == 0
    assert run(tmp_path, path, "--all").returncode == 1


def test_an_undated_heading_fails(tmp_path):
    path = instance(tmp_path, ["## work without a date\n\n" + GOOD])
    out = run(tmp_path, path)
    assert out.returncode == 1 and "YYYY-MM-DD" in out.stderr


def test_a_link_only_entry_passes_only_in_pr_mode(tmp_path):
    link = "## 2026-03-02 · pr session\n\nhttps://example.com/org/repo/pull/7\n"
    assert run(tmp_path / "pr", instance(tmp_path / "pr", [link], close_mode="pr")).returncode == 0
    out = run(tmp_path / "commit", instance(tmp_path / "commit", [link], close_mode="commit"))
    assert out.returncode == 1 and "only in PR close mode" in out.stderr


def test_no_entry_means_the_report_was_not_persisted(tmp_path):
    path = instance(tmp_path, [])
    out = run(tmp_path, path)
    assert out.returncode == 1 and "not persisted" in out.stderr


def test_a_pr_body_is_read_at_level_two(tmp_path):
    body = tmp_path / "body.md"
    body.write_text(GOOD.replace("### ", "## "), encoding="utf-8")
    assert run(tmp_path, "--pr-body", body).returncode == 0
    body.write_text(GOOD, encoding="utf-8")  # level-3 slots in a PR body do not count
    assert run(tmp_path, "--pr-body", body).returncode == 1


def test_a_slot_heading_inside_a_fence_does_not_count(tmp_path):
    fenced = "## 2026-03-02 · work\n\n```\n### Fixes Applied\nnot real\n```\n\n" + GOOD.split("### Smoke Test")[0].replace("### Fixes Applied\n\n- fixed a link\n\n", "") + "### Smoke Test\n\n- ran\n\n### Next Session Prompt\n\nGo.\n"
    out = run(tmp_path, instance(tmp_path, [fenced]))
    assert out.returncode == 1 and "missing slot: Fixes Applied" in out.stderr


def test_with_no_file_an_unresolved_operator_exits_two(tmp_path):
    instance(tmp_path, ["## 2026-03-02 · work\n\n" + GOOD])
    assert run(tmp_path).returncode == 2


def test_the_shipped_template_example_entry_is_caught_as_unfilled():
    out = subprocess.run([sys.executable, str(SCRIPT), str(REPO_ROOT / "os" / "handoff.template.md")],
                         capture_output=True, text=True)
    assert out.returncode == 1
    assert "YYYY-MM-DD" in out.stderr and "empty slot" in out.stderr


def test_bare_markers_and_stand_ins_are_empty(tmp_path):
    body = "### Fixes Applied\n\n- \n\n### Smoke Test\n\n*\n\n### Next Session Prompt\n\nTBD\n"
    out = run(tmp_path, instance(tmp_path, ["## 2026-03-02 · work\n\n" + body]))
    assert out.returncode == 1
    for slot in ("Fixes Applied", "Smoke Test", "Next Session Prompt"):
        assert f"empty slot: {slot}" in out.stderr


def test_a_placeholder_wrapped_across_lines_is_empty_but_links_and_checkboxes_are_content():
    assert not cc.has_content("[A copy-pasteable paragraph: what to load,\nwhere to start.]\n")
    assert cc.has_content("- [x] ran the suite\n")
    assert cc.has_content("Start from [the plan](plans/a.md).\n")


def test_the_template_next_session_prompt_is_caught_too():
    out = subprocess.run([sys.executable, str(SCRIPT), str(REPO_ROOT / "os" / "handoff.template.md")],
                         capture_output=True, text=True)
    assert "empty slot: Next Session Prompt" in out.stderr
