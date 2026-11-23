"""
The id allocator (os/id_allocator.py).

The collision it exists to prevent: two parallel sessions each take "the next free id" from
their own branch. So the tests put ids where a single-branch count cannot see them (an
unmerged branch, another worktree's uncommitted edit, a range written in a plan) and check
that each one is skipped. It must also never write.
"""

import json
import subprocess
import sys

from conftest import REPO_ROOT, load_tool

ia = load_tool("os/id_allocator.py", "id_allocator_under_test")
SCRIPT = REPO_ROOT / "os" / "id_allocator.py"
REGISTRY = "os/corrections/corrections-registry.yaml"


def registry(*ids):
    return "entries:\n" + "".join(f"  - id: {i}\n    status: active\n" for i in ids)


def run(repo, *args):
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(repo.path), *args],
                         capture_output=True, text=True, env=repo.env)
    assert out.returncode == 0, out.stderr
    return out


def allocate(repo, *args):
    return json.loads(run(repo, "--json", *args).stdout)


def test_the_next_id_is_one_above_the_highest_on_main(scratch_repo):
    scratch_repo.write(REGISTRY, registry("C-001", "C-002", "C-007"))
    scratch_repo.commit("registry")
    data = allocate(scratch_repo, "--prefix", "C", REGISTRY)
    assert data["next_free"] == "C-008"  # gaps are never refilled, and the padding is kept


def test_an_id_on_an_unmerged_branch_is_skipped(scratch_repo):
    scratch_repo.write(REGISTRY, registry("C-001", "C-002"))
    scratch_repo.commit("registry")
    scratch_repo.git("checkout", "-q", "-b", "lane-a")
    scratch_repo.write(REGISTRY, registry("C-001", "C-002", "C-003"))
    scratch_repo.commit("lane a takes C-003")
    scratch_repo.git("checkout", "-q", "main")
    data = allocate(scratch_repo, "--prefix", "C", REGISTRY)
    assert data["next_free"] == "C-004"
    assert data["off_default"] == [3]
    assert "refs/heads/lane-a" in data["taken"]["3"]
    assert "taken off refs/heads/main: C-003" in run(scratch_repo, "--prefix", "C", REGISTRY).stdout


def test_an_uncommitted_id_in_another_worktree_is_skipped(scratch_repo, tmp_path):
    scratch_repo.write(REGISTRY, registry("C-001"))
    scratch_repo.commit("registry")
    other = tmp_path / "other-session"
    scratch_repo.git("worktree", "add", "-q", "-b", "lane-b", str(other))
    (other / REGISTRY).write_text(registry("C-001", "C-002"), encoding="utf-8")
    assert allocate(scratch_repo, "--prefix", "C", REGISTRY)["next_free"] == "C-003"
    assert allocate(scratch_repo, "--prefix", "C", REGISTRY, "--refs-only")["next_free"] == "C-002"


def test_a_written_range_reserves_every_id_in_it(scratch_repo):
    scratch_repo.write(REGISTRY, registry("KS-01", "KS-05"))
    scratch_repo.write("plans/batch-plan.md", "Pre-assigned: KS-06 to KS-11 lane A, KS-12..KS-14 lane B.\n")
    scratch_repo.commit("plan")
    data = allocate(scratch_repo, "--prefix", "KS", REGISTRY, "plans/*.md")
    assert data["next_free"] == "KS-15"
    assert set(range(6, 15)) <= {int(k) for k in data["taken"]}


def test_reserve_prints_consecutive_disjoint_blocks(scratch_repo):
    scratch_repo.write(REGISTRY, registry("D-9"))
    scratch_repo.commit("registry")
    data = allocate(scratch_repo, "--prefix", "D", REGISTRY, "--reserve", "3", "--reserve", "2")
    assert [(b["first"], b["last"]) for b in data["blocks"]] == [("D-10", "D-12"), ("D-13", "D-14")]


def test_ids_inside_longer_tokens_are_not_ids(scratch_repo):
    scratch_repo.write(REGISTRY, "notes: XC-900 C-900a C_900 and C-002\n")
    scratch_repo.commit("noise")
    assert allocate(scratch_repo, "--prefix", "C", REGISTRY)["next_free"] == "C-003"


def test_it_never_writes(scratch_repo):
    scratch_repo.write(REGISTRY, registry("C-001"))
    scratch_repo.commit("registry")
    before = scratch_repo.git("status", "--porcelain", "--ignored")
    refs = scratch_repo.git("for-each-ref")
    run(scratch_repo, "--prefix", "C", REGISTRY, "--reserve", "5")
    assert scratch_repo.git("status", "--porcelain", "--ignored") == before
    assert scratch_repo.git("for-each-ref") == refs


def test_a_path_that_matches_nothing_is_refused(scratch_repo):
    """A typo would hand out id 1 again: refused unless the registry is declared not to exist yet."""
    def cli(*args):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(scratch_repo.path), "--prefix", "C", *args],
                              capture_output=True, text=True, env=scratch_repo.env)
    scratch_repo.write(REGISTRY, registry("C-001"))
    scratch_repo.commit("registry")
    for args in (["nope.yaml"], ["--json", "nope.yaml"], [REGISTRY, "plans/*.md"]):
        out = cli(*args)
        assert out.returncode == 2 and "no file on any branch or worktree matches" in out.stderr, args
    out = cli("--allow-empty", "nope.yaml")
    assert out.returncode == 0 and "next free: C-1" in out.stdout


def test_a_directory_named_without_its_slash_is_read(scratch_repo):
    scratch_repo.write(REGISTRY, registry("C-004"))
    scratch_repo.commit("registry")
    assert allocate(scratch_repo, "--prefix", "C", "os/corrections")["next_free"] == "C-005"


def test_bad_arguments_exit_two(scratch_repo):
    for args in (["--prefix", "C", "--reserve", "0", REGISTRY], ["--prefix", " ", REGISTRY]):
        out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(scratch_repo.path), *args],
                             capture_output=True, text=True, env=scratch_repo.env)
        assert out.returncode == 2


def test_padding_follows_what_is_written():
    assert ia.pad_width({1: "001", 20: "020"}) == 3
    assert ia.pad_width({1: "1", 12: "12"}) == 0
    assert ia.fmt("KS", "-", 6, 2) == "KS-06"
