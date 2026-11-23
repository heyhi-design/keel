"""
The cold-start check (os/cold_start_check.py).

It clones the instance fresh and finds what only works on the founder's machine: a path that
exists only in the checkout (gitignored or uncommitted), an absolute path, a prefix break, a
script leaning on a ref a fresh clone lacks, an import that leaves the root, two profiles
claiming one email. It is report-first (exit 0 unless --strict), it never writes to the
checkout, and it removes only its own temporary clone.
"""

import json
import subprocess
import sys
import tempfile

from conftest import REPO_ROOT, load_tool

csc = load_tool("os/cold_start_check.py", "cold_start_check_under_test")
SCRIPT = REPO_ROOT / "os" / "cold_start_check.py"

CLEAN_AGENTS = """# Agent Instructions

Run the start sequence in `os/session-start.md`. Read `os/agent-context.md` and
[the guide](docs/guide.md). Your handoff is `os/handoff/<operator-id>.md`.
"""


def instance(repo, agents=CLEAN_AGENTS):
    repo.write("CLAUDE.md", "@AGENTS.md\n")
    repo.write("AGENTS.md", agents)
    repo.write("os/session-start.md", "1. Read `os/agent-context.md`.\n")
    repo.write("os/agent-context.md", "# Context\n")
    repo.write("docs/guide.md", "# Guide\n")
    repo.commit("instance")
    return repo


def run(repo, *args):
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(repo.path), "--json", *args],
                         capture_output=True, text=True, env=repo.env)
    assert out.returncode in (0, 1), out.stderr
    data = json.loads(out.stdout)
    return out.returncode, {c["check"]: c for c in data["checks"]}, data


def test_a_clean_instance_passes(scratch_repo):
    code, checks, _ = run(instance(scratch_repo), "--strict")
    assert code == 0, checks
    assert all(c["status"] in ("pass", "skip") for c in checks.values()), checks
    assert checks["imports"]["status"] == "pass"


def test_a_gitignored_file_the_start_files_name_fails(scratch_repo):
    repo = instance(scratch_repo, CLEAN_AGENTS + "\nAlso read `private/notes.md`.\n")
    repo.write(".gitignore", "private/\n")
    repo.write("private/notes.md", "only on this machine\n")
    repo.commit("ignore")
    code, checks, _ = run(repo)
    assert code == 0  # report-first
    assert checks["start-paths"]["status"] == "fail"
    assert any("not in a fresh clone" in d for d in checks["start-paths"]["details"])
    assert run(repo, "--strict")[0] == 1


def test_an_absolute_path_and_a_prefix_break_fail(scratch_repo):
    repo = instance(scratch_repo, CLEAN_AGENTS + "\nSee `/Users/someone/notes.md` and `my-checkout/docs/guide.md`.\n")
    _, checks, _ = run(repo)
    details = " ".join(checks["start-paths"]["details"])
    assert "absolute or home-directory path" in details
    assert "prefix break" in details and "my-checkout/" in details


def test_an_unfilled_file_is_a_warning_not_a_failure(scratch_repo):
    repo = instance(scratch_repo, CLEAN_AGENTS + "\nRules: `os/session-rules.md`.\n")
    repo.write("os/session-rules.template.md", "# template\n")
    repo.commit("template only")
    code, checks, _ = run(repo, "--strict")
    assert code == 0
    assert checks["start-paths"]["status"] == "warn"


def test_a_script_relying_on_a_ref_a_fresh_clone_lacks_fails(scratch_repo):
    repo = instance(scratch_repo)
    repo.write("scripts/undo.sh", "git diff ORIG_HEAD..HEAD\n")  # cold-start: ignore (a fixture, not a use)
    repo.write("scripts/ok.sh", "echo ORIG_HEAD is mentioned on purpose  # cold-start: ignore\n")
    repo.commit("scripts")
    _, checks, _ = run(repo)
    fails = [d for d in checks["git-state"]["details"] if d.startswith("FAIL")]
    assert len(fails) == 1 and "scripts/undo.sh:1" in fails[0]


def test_an_import_outside_the_root_fails(scratch_repo):
    repo = instance(scratch_repo)
    repo.write("CLAUDE.md", "@AGENTS.md\n@~/.config/personal.md\n")
    repo.commit("personal import")
    _, checks, _ = run(repo)
    assert checks["imports"]["status"] == "fail"


def test_one_email_in_two_profiles_fails(scratch_repo):
    repo = instance(scratch_repo)
    for op in ("ada", "lin"):
        repo.write(f"os/operators/{op}.md", f'---\noperator: "{op}"\ngit_emails:\n  - "shared@example.com"\nstatus: active\n---\n')
    repo.write("os/handoff/ada.md", "# Handoff · ada\n")
    repo.commit("profiles")
    _, checks, _ = run(repo)
    assert checks["operators"]["status"] == "fail"
    assert checks["handoffs"]["status"] == "warn"  # lin has no handoff file yet


def test_uncommitted_changes_are_noted_and_left_alone(scratch_repo):
    repo = instance(scratch_repo)
    repo.write("AGENTS.md", CLEAN_AGENTS + "\nAn uncommitted line.\n")
    before = repo.git("status", "--porcelain")
    _, _, data = run(repo)
    assert any("uncommitted changes" in n for n in data["notes"])
    assert repo.git("status", "--porcelain") == before


def test_it_removes_only_its_own_clone(scratch_repo, tmp_path, monkeypatch):
    repo = instance(scratch_repo)
    holder = tmp_path / "tmp-holder"
    holder.mkdir()
    (holder / "someone-elses-file").write_text("keep me\n", encoding="utf-8")
    monkeypatch.setattr(tempfile, "tempdir", str(holder))
    assert csc.main(["--root", str(repo.path), "--json"]) == 0
    assert [p.name for p in holder.iterdir()] == ["someone-elses-file"]


def test_a_root_that_is_not_a_repository_exits_two(tmp_path):
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(tmp_path)], capture_output=True, text=True)
    assert out.returncode == 2


def test_path_references_skip_placeholders_globs_and_commands():
    refs = [t for _, _, t in csc.path_refs(
        "`os/handoff/<operator-id>.md` `*.template.md` `git config user.email` `AGENTS.md` "
        "[x](https://example.com) [y](docs/a.md#part) `operating_mode.handoff.keep_newest`\n"
        "```\n`inside/a/fence.md`\n```\n")]
    assert refs == ["AGENTS.md", "docs/a.md"]


def test_keels_own_tree_passes_strict(scratch_repo, tmp_path):
    """A fresh copy of keel itself: warnings for the unfilled templates, and no failures."""
    import shutil
    copy = tmp_path / "keel-copy"
    shutil.copytree(REPO_ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"))
    repo = type(scratch_repo)(copy, scratch_repo.env)
    repo.git("init", "-q", "-b", "main")
    repo.commit("keel")
    code, checks, _ = run(repo, "--strict")
    assert code == 0, {k: v["details"] for k, v in checks.items() if v["status"] == "fail"}
    assert checks["start-paths"]["status"] == "warn"  # the templates are not filled in yet


def test_a_gitignored_filled_file_is_not_hidden_by_its_template(scratch_repo):
    repo = instance(scratch_repo)
    repo.write("os/agent-context.template.md", "# template\n")
    repo.git("rm", "-q", "--cached", "os/agent-context.md")
    repo.write(".gitignore", "os/agent-context.md\n")
    repo.commit("ignore the filled file, keep the template")
    assert (repo.path / "os" / "agent-context.md").is_file()
    code, checks, _ = run(repo, "--strict")
    assert code == 1 and checks["start-paths"]["status"] == "fail"
    assert any("os/agent-context.md" in d and "not in a fresh clone" in d for d in checks["start-paths"]["details"])


def test_a_branch_with_no_upstream_is_noted(scratch_repo):
    _, _, data = run(instance(scratch_repo))
    assert any("has no upstream" in n for n in data["notes"])
