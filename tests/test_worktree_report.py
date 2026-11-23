"""
The worktree report (os/worktree_report.py).

It lists and never removes. The reapable set is exactly the worktrees that are merged into
the default branch (by merge, by an equivalent patch, or by a squash) and clean; a dirty tree
or a branch with work the default branch lacks is never in it, nor is the main worktree.
"""

import json
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT, load_tool

wr = load_tool("os/worktree_report.py", "worktree_report_under_test")
SCRIPT = REPO_ROOT / "os" / "worktree_report.py"


def add_worktree(repo, tmp_path, name, change=None):
    path = tmp_path / name
    repo.git("worktree", "add", "-q", "-b", name, str(path))
    if change:
        (path / f"{name}.txt").write_text(change, encoding="utf-8")
        repo.git("add", "-A", cwd=path)
        repo.git("commit", "-q", "-m", f"{name} work", cwd=path)
    return path


def report(repo):
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(repo.path), "--base", "main", "--json"],
                         capture_output=True, text=True, env=repo.env, cwd=str(repo.path))
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _paths(listed):
    """git prints worktree paths with forward slashes on every platform; compare them resolved."""
    return {Path(p).resolve() for p in listed}


def by_branch(data):
    return {r["branch"]: r for r in data["worktrees"]}


def test_it_lists_without_removing(scratch_repo, tmp_path):
    add_worktree(scratch_repo, tmp_path, "merged-clean")
    add_worktree(scratch_repo, tmp_path, "open-work", change="unmerged\n")
    before = scratch_repo.git("worktree", "list", "--porcelain")
    data = report(scratch_repo)
    assert len(data["worktrees"]) == 3
    assert scratch_repo.git("worktree", "list", "--porcelain") == before


def test_the_reapable_set_is_merged_and_clean_only(scratch_repo, tmp_path):
    merged = add_worktree(scratch_repo, tmp_path, "merged-clean")
    add_worktree(scratch_repo, tmp_path, "open-work", change="unmerged\n")
    dirty = add_worktree(scratch_repo, tmp_path, "merged-dirty")
    (dirty / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")
    rows = by_branch(report(scratch_repo))
    assert rows["merged-clean"]["reapable"]
    assert rows["open-work"]["merged"] == "no" and not rows["open-work"]["reapable"]
    assert rows["merged-dirty"]["dirty"] and not rows["merged-dirty"]["reapable"]
    assert rows["main"]["main"] and not rows["main"]["reapable"]
    assert _paths(report(scratch_repo)["reapable"]) == {merged.resolve()}


def test_a_squash_merged_branch_is_merged(scratch_repo, tmp_path):
    path = add_worktree(scratch_repo, tmp_path, "squashed", change="one\n")
    (path / "second.txt").write_text("two\n", encoding="utf-8")
    scratch_repo.git("add", "-A", cwd=path)
    scratch_repo.git("commit", "-q", "-m", "second", cwd=path)
    scratch_repo.git("merge", "-q", "--squash", "squashed")
    scratch_repo.git("commit", "-q", "-m", "squash")
    row = by_branch(report(scratch_repo))["squashed"]
    assert row["merged"] == "content in base" and row["reapable"]


def test_a_rebased_branch_reads_patches_upstream(scratch_repo, tmp_path):
    add_worktree(scratch_repo, tmp_path, "picked", change="one\n")
    tip = scratch_repo.git("rev-parse", "picked")
    scratch_repo.write("unrelated.txt", "main moved on\n")
    scratch_repo.commit("main moves")
    scratch_repo.git("cherry-pick", tip)
    assert by_branch(report(scratch_repo))["picked"]["merged"] == "patches upstream"


def test_a_squash_edited_again_on_main_reads_not_merged(scratch_repo, tmp_path):
    path = add_worktree(scratch_repo, tmp_path, "edited", change="one\n")
    (path / "second.txt").write_text("two\n", encoding="utf-8")
    scratch_repo.git("add", "-A", cwd=path)
    scratch_repo.git("commit", "-q", "-m", "second", cwd=path)
    scratch_repo.git("merge", "-q", "--squash", "edited")
    scratch_repo.git("commit", "-q", "-m", "squash")
    scratch_repo.write("edited.txt", "one, then changed\n")
    scratch_repo.commit("edit after merge")
    # Two commits squashed into one, so no single patch matches upstream, and a file the branch
    # changed now differs from main's: the check cannot prove the work landed, so it says no.
    row = by_branch(report(scratch_repo))["edited"]
    assert row["merged"] == "no" and not row["reapable"]


def test_a_missing_directory_is_a_stale_entry_not_reapable(scratch_repo, tmp_path):
    import shutil
    path = add_worktree(scratch_repo, tmp_path, "gone")
    shutil.rmtree(path)
    data = report(scratch_repo)
    assert path.resolve() in _paths(data["stale"]) and path.resolve() not in _paths(data["reapable"])


def test_the_worktree_it_ran_from_is_never_reapable(scratch_repo, tmp_path):
    path = add_worktree(scratch_repo, tmp_path, "this-session")
    data = wr.report(scratch_repo.path, "main", here=path.resolve())
    row = by_branch(data)["this-session"]
    assert row["this"] and not row["reapable"]


def test_a_missing_base_is_an_error(scratch_repo):
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(scratch_repo.path), "--base", "nope"],
                         capture_output=True, text=True, env=scratch_repo.env)
    assert out.returncode == 2 and "does not exist" in out.stderr


def test_the_text_report_says_it_removes_nothing(scratch_repo):
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(scratch_repo.path), "--base", "main"],
                         capture_output=True, text=True, env=scratch_repo.env)
    assert out.returncode == 0 and "removes nothing" in out.stdout


def test_there_is_no_flag_that_removes_anything():
    flags = {a for action in wr.build_parser()._actions for a in action.option_strings}
    assert not any(word in flag for flag in flags for word in ("reap", "remove", "prune", "delete"))


def test_a_worktree_holding_gitignored_files_is_not_reapable(scratch_repo, tmp_path):
    """`git worktree remove` deletes ignored files without asking, so they block the reapable set."""
    scratch_repo.write(".gitignore", "private/\n")
    scratch_repo.commit("ignore private/")
    path = add_worktree(scratch_repo, tmp_path, "holds-private")
    (path / "private").mkdir()
    (path / "private" / "notes.md").write_text("never committed\n", encoding="utf-8")
    data = report(scratch_repo)
    row = by_branch(data)["holds-private"]
    assert row["dirty"] is False and row["ignored"] == ["private/"]
    assert not row["reapable"] and path.resolve() in _paths(data["look_first"])
    assert path.resolve() not in _paths(data["reapable"])


def test_the_worktree_root_names_is_protected_wherever_it_runs_from(scratch_repo, tmp_path):
    path = add_worktree(scratch_repo, tmp_path, "named-by-root")
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(path), "--base", "main", "--json"],
                         capture_output=True, text=True, env=scratch_repo.env, cwd=str(tmp_path))
    row = by_branch(json.loads(out.stdout))["named-by-root"]
    assert row["this"] and not row["reapable"]


def test_config_that_hides_untracked_files_does_not_make_a_tree_reapable(scratch_repo, tmp_path):
    # `status.showUntrackedFiles=no` hides an untracked file from a plain `git status`, and
    # `git worktree remove` would delete it without --force.
    path = add_worktree(scratch_repo, tmp_path, "hide-untracked")
    scratch_repo.git("config", "status.showUntrackedFiles", "no", cwd=path)
    (path / "precious.txt").write_text("not committed\n", encoding="utf-8")
    row = by_branch(report(scratch_repo))["hide-untracked"]
    assert row["dirty"] and not row["reapable"]


def test_a_skip_worktree_edit_is_hidden_work_and_never_reapable(scratch_repo, tmp_path):
    path = add_worktree(scratch_repo, tmp_path, "skip-wt")
    tracked = "README.md"
    scratch_repo.git("update-index", "--skip-worktree", tracked, cwd=path)
    (path / tracked).write_text("edited behind git's back\n", encoding="utf-8")
    row = by_branch(report(scratch_repo))["skip-wt"]
    assert row["hidden"] == [tracked] and not row["reapable"]


def test_a_detached_commit_no_ref_holds_is_not_reapable(scratch_repo, tmp_path):
    path = add_worktree(scratch_repo, tmp_path, "detached")
    scratch_repo.git("checkout", "-q", "--detach", cwd=path)
    scratch_repo.git("commit", "-q", "--allow-empty", "-m", "orphan-to-be", cwd=path)
    rows = [r for r in report(scratch_repo)["worktrees"] if Path(r["path"]).resolve() == path.resolve()]
    assert rows and not rows[0]["reapable"]
    assert any("detached" in why for why in rows[0]["why_not"])
