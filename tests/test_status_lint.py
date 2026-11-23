"""
The status-vocabulary lint (os/status_lint.py) and the generated index (os/gen_index.py).

The lint: only the first word of `status:` is checked, against keel's four words or an
instance's own `--vocab`; a missing frontmatter or status fails; the first words in use are
counted so drift is visible. The index: built from the files, grouped so off-vocabulary
statuses stand out, deterministic so `--check` can call a hand-edited or stale index a failure.
"""

import subprocess
import sys

from conftest import REPO_ROOT, load_tool

sl = load_tool("os/status_lint.py", "status_lint_under_test")
SCRIPT = REPO_ROOT / "os" / "status_lint.py"
INDEX = REPO_ROOT / "os" / "gen_index.py"


def plans(tmp_path, files):
    folder = tmp_path / "plans"
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    return folder


def doc(status=None, title=None, created=None, body="# Heading\n"):
    lines = ["---"]
    if title:
        lines.append(f'title: "{title}"')
    if created:
        lines.append(f'created: "{created}"')
    if status is not None:
        lines.append(f"status: {status}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def lint(tmp_path, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(tmp_path), *args], capture_output=True, text=True)


def index(tmp_path, *args):
    return subprocess.run([sys.executable, str(INDEX), "plans/", "--root", str(tmp_path), *args], capture_output=True, text=True)


def test_the_first_word_is_what_counts():
    assert sl.first_word("partial  # items 3 and 4 remain") == "partial"
    assert sl.first_word('"done (2026-05-01)"') == "done"
    fields = sl.frontmatter(doc("done   # a comment"))
    assert fields["status"] == "done"


def test_vocabulary_statuses_pass(tmp_path):
    plans(tmp_path, {"a-plan.md": doc("pending"), "b-plan.md": doc("partial # half"), "c-plan.md": doc("done")})
    out = lint(tmp_path)
    assert out.returncode == 0, out.stderr
    assert "3 artifact(s) checked" in out.stdout


def test_drift_missing_status_and_missing_frontmatter_fail(tmp_path):
    plans(tmp_path, {
        "a-plan.md": doc("ready to execute"),
        "b-plan.md": doc(None),
        "c-plan.md": "# no frontmatter\n",
        "d-plan.md": doc("done"),
    })
    out = lint(tmp_path)
    assert out.returncode == 1
    assert "a-plan.md: status starts with 'ready'" in out.stderr
    assert "b-plan.md: no status: field" in out.stderr
    assert "c-plan.md: no frontmatter" in out.stderr
    assert "First words in use" in out.stderr


def test_default_targets_are_the_planning_artifacts(tmp_path):
    plans(tmp_path, {"x-plan.md": doc("done"), "notes.md": doc("whatever")})
    (tmp_path / "os" / "dispatch").mkdir(parents=True)
    (tmp_path / "os" / "dispatch" / "dispatch-prompts.md").write_text(doc("ready"), encoding="utf-8")
    (tmp_path / "os" / "dispatch" / "README.md").write_text("# readme\n", encoding="utf-8")
    (tmp_path / "os" / "x-plan.template.md").write_text("# template\n", encoding="utf-8")
    names = sorted(p.name for p in sl.default_targets(tmp_path))
    assert names == ["dispatch-prompts.md", "x-plan.md"]


def test_an_instance_vocabulary_is_honored(tmp_path):
    plans(tmp_path, {"a-plan.md": doc("blocked")})
    assert lint(tmp_path).returncode == 1
    assert lint(tmp_path, "--vocab", "pending,partial,done,archived,blocked").returncode == 0


def test_a_named_path_that_does_not_exist_exits_two(tmp_path):
    assert lint(tmp_path, "nowhere/").returncode == 2


def test_keels_own_tree_passes():
    out = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr


# ── the generated index ──────────────────────────────────────────────────────


def test_the_index_groups_and_flags_off_vocabulary(tmp_path):
    plans(tmp_path, {
        "2026-03-01-a.md": doc("pending", title="Alpha", body="# Alpha\n\n## Next Session Prompt\n\nStart with step two.\n"),
        "b.md": doc("done", title="Bravo", created="2026-02-01"),
        "c.md": doc("mostly there", title="Charlie"),
        "README.md": "# not indexed\n",
    })
    out = index(tmp_path)
    assert out.returncode == 0, out.stderr
    text = out.stdout
    assert "**Open** 1 · **Done** 1 · **Archived** 0 · **Other** 0 · **Off the vocabulary** 1" in text
    assert "| 2026-03-01 | [Alpha](2026-03-01-a.md) | `pending` |" in text
    assert "[Alpha](2026-03-01-a.md): Start with step two." in text
    assert "[Charlie](c.md)" in text.split("## Off the vocabulary")[1]
    assert "README" not in text


def test_write_then_check_round_trips_and_detects_staleness(tmp_path):
    folder = plans(tmp_path, {"a.md": doc("pending", title="Alpha")})
    assert not (folder / "INDEX.md").exists()  # the default run only prints
    assert index(tmp_path).returncode == 0 and not (folder / "INDEX.md").exists()
    assert index(tmp_path, "--check").returncode == 1  # missing counts as stale
    assert index(tmp_path, "--write").returncode == 0
    assert index(tmp_path, "--check").returncode == 0
    first = (folder / "INDEX.md").read_bytes()
    assert index(tmp_path, "--write").returncode == 0
    assert (folder / "INDEX.md").read_bytes() == first  # deterministic: no generation date
    (folder / "b.md").write_text(doc("pending", title="Bravo"), encoding="utf-8")
    assert index(tmp_path, "--check").returncode == 1


def test_links_are_relative_to_the_output_file(tmp_path):
    plans(tmp_path, {"a.md": doc("pending", title="Alpha")})
    assert index(tmp_path, "--out", "docs/plans-index.md", "--write").returncode == 0
    assert "[Alpha](../plans/a.md)" in (tmp_path / "docs" / "plans-index.md").read_text(encoding="utf-8")


def test_a_word_the_instance_adds_is_not_called_off_vocabulary(tmp_path):
    plans(tmp_path, {"a.md": doc("blocked", title="Alpha"), "b.md": doc("mostly", title="Bravo")})
    text = index(tmp_path, "--vocab", "pending,partial,done,archived,blocked").stdout
    assert "[Alpha](a.md)" in text.split("## Other")[1].split("## Off")[0]
    assert "[Bravo](b.md)" in text.split("## Off the vocabulary")[1]
