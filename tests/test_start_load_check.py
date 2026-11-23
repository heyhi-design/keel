"""
The start-load check (os/start_load_check.py).

It is report-first, so the two promises that matter are the quiet ones: by default it never
fails a run (a measurement is not a verdict), and it never reads a missing or malformed thing
as "fine" when it could be a gate. Concretely:

  - the table covers every file in the start set, the active entries of a corrections
    registry only, and a template stands in (and says so) for a file not filled in yet;
  - a missing file is listed, never skipped;
  - no budget means a notice and exit 0, over budget warns and exits 0, and only --strict
    turns a warning into exit 1;
  - a budget that is not a positive integer is an error in both modes (bool, zero, negative,
    text, float, NaN), because a limit read as "no limit" fails open;
  - a declaration cannot reach outside the instance root.

Every fixture lives in tmp_path. Nothing here depends on the contents of the shipped
templates beyond "they exist and measure".
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT

MODULE_PATH = REPO_ROOT / "os" / "start_load_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("start_load_check", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["start_load_check"] = module
    spec.loader.exec_module(module)
    return module


slc = _load()

REGISTRY = """\
meta:
  total_corrections: 3
entries:
  - id: first-active
    status: active
    trigger_context: "when a session starts"
    correction: "read the file first"
  - id: retired-one
    status: retired
    trigger_context: "an old situation that no longer applies, described at length so it is large"
    correction: "a long retired correction that must not count toward the start load at all"
  - id: second-active
    status: active
    trigger_context: "when a session ends"
    correction: "close through the gate"
"""


def _instance(tmp_path, runtime="CLAUDE.md"):
    """A filled-in instance: a runtime file, the start sequence, the core, and a registry with
    one retired entry. No operator profiles and no templates, so those two rows are skipped."""
    (tmp_path / "os" / "corrections").mkdir(parents=True)
    if runtime:
        (tmp_path / runtime).write_text("r" * 400, encoding="utf-8")
    (tmp_path / "os" / "session-start.md").write_text("s" * 160, encoding="utf-8")
    (tmp_path / "os" / "agent-context.md").write_text("a" * 800, encoding="utf-8")
    (tmp_path / "os" / "operating-principles.md").write_text("p" * 1200, encoding="utf-8")
    (tmp_path / "os" / "corrections" / "corrections-registry.yaml").write_text(REGISTRY, encoding="utf-8")
    return tmp_path


def _rows(measurement):
    return {r["path"]: r for r in measurement["rows"]}


# ── the estimator and the default start set ──────────────────────────────────


def test_the_estimator_is_characters_over_four_rounded_down():
    assert slc.estimate_tokens("") == 0
    assert slc.estimate_tokens("abc") == 0
    assert slc.estimate_tokens("abcd") == 1
    assert slc.estimate_tokens("x" * 4001) == 1000


def test_default_start_set_is_the_documented_core(tmp_path):
    root = _instance(tmp_path)
    m = slc.measure(root, slc.default_start_set(root))
    rows = _rows(m)
    assert list(rows) == [
        "CLAUDE.md",
        "os/session-start.md",
        "os/agent-context.md",
        "os/operating-principles.md",
        "os/corrections/corrections-registry.yaml",
        "os/operators/",
        "os/handoff/",
    ]
    assert rows["os/operators/"]["status"] == rows["os/handoff/"]["status"] == "skipped"
    assert rows["CLAUDE.md"]["tokens"] == 100
    assert rows["os/session-start.md"]["tokens"] == 40
    assert rows["os/agent-context.md"]["tokens"] == 200
    assert rows["os/operating-principles.md"]["tokens"] == 300
    assert m["total_tokens"] == sum(r["tokens"] for r in m["rows"])
    assert m["problems"] == []


def test_agents_md_stands_in_for_a_missing_claude_md(tmp_path):
    root = _instance(tmp_path, runtime="AGENTS.md")
    assert slc.default_start_set(root)[0] == "AGENTS.md"


def test_no_runtime_file_is_not_an_error(tmp_path):
    root = _instance(tmp_path, runtime=None)
    assert slc.default_start_set(root)[0] == "os/session-start.md"


# ── the corrections registry counts active entries only ──────────────────────


def test_a_registry_is_measured_over_its_active_entries(tmp_path):
    root = _instance(tmp_path)
    row = _rows(slc.measure(root, ["os/corrections/corrections-registry.yaml"]))[
        "os/corrections/corrections-registry.yaml"
    ]
    whole = slc.estimate_tokens(REGISTRY)
    assert 0 < row["tokens"] < whole
    assert row["note"] == "2 active of 3 entries"


def test_a_retired_entry_costs_nothing(tmp_path):
    root = _instance(tmp_path)
    registry = root / "os" / "corrections" / "corrections-registry.yaml"
    before = _rows(slc.measure(root, ["os/corrections/corrections-registry.yaml"]))[
        "os/corrections/corrections-registry.yaml"
    ]["tokens"]
    registry.write_text(
        REGISTRY + '  - id: another-retired\n    status: retired\n    correction: "' + "z" * 2000 + '"\n',
        encoding="utf-8",
    )
    after = _rows(slc.measure(root, ["os/corrections/corrections-registry.yaml"]))[
        "os/corrections/corrections-registry.yaml"
    ]["tokens"]
    assert after == before


def test_a_yaml_without_an_entries_list_is_measured_whole_and_says_so(tmp_path):
    (tmp_path / "other.yaml").write_text("corrections:\n  - id: x\n    status: active\n", encoding="utf-8")
    row = _rows(slc.measure(tmp_path, ["other.yaml"]))["other.yaml"]
    assert row["tokens"] == slc.estimate_tokens("corrections:\n  - id: x\n    status: active\n")
    assert "measured whole" in row["note"]


def test_only_an_explicit_retired_or_superseded_status_takes_an_entry_out(tmp_path):
    body = (
        "entries:\n"
        "  - {id: a, status: Active, correction: one}\n"       # capitalised
        "  - {id: b, status: null, correction: two}\n"           # empty status
        "  - {id: c, correction: three}\n"                       # no status at all
        "  - not-a-mapping\n"                                    # not even an entry
        "  - {id: d, status: Retired, correction: four}\n"       # retired, any case
        "  - {id: e, status: superseded, correction: five}\n"
    )
    (tmp_path / "reg.yaml").write_text(body, encoding="utf-8")
    row = slc.measure(tmp_path, ["reg.yaml"])["rows"][0]
    assert row["note"] == "4 active of 6 entries"


def test_an_unparseable_registry_is_measured_whole_with_the_right_reason(tmp_path):
    (tmp_path / "reg.yaml").write_text("entries: [unclosed\n", encoding="utf-8")
    row = slc.measure(tmp_path, ["reg.yaml"])["rows"][0]
    assert row["tokens"] > 0
    assert "does not parse as YAML" in row["note"]


# ── templates stand in for unfilled files, missing files are listed ──────────


def test_a_template_stands_in_for_an_unfilled_file_and_is_labelled(tmp_path):
    (tmp_path / "os").mkdir()
    (tmp_path / "os" / "agent-context.template.md").write_text("t" * 400, encoding="utf-8")
    row = slc.measure(tmp_path, ["os/agent-context.md"])["rows"][0]
    assert row["path"] == "os/agent-context.template.md"
    assert row["status"] == "template"
    assert row["tokens"] == 100


def test_a_filled_file_wins_over_its_template(tmp_path):
    (tmp_path / "os").mkdir()
    (tmp_path / "os" / "agent-context.md").write_text("f" * 40, encoding="utf-8")
    (tmp_path / "os" / "agent-context.template.md").write_text("t" * 4000, encoding="utf-8")
    row = slc.measure(tmp_path, ["os/agent-context.md"])["rows"][0]
    assert row["path"] == "os/agent-context.md" and row["tokens"] == 10


def test_a_missing_file_is_listed_not_skipped(tmp_path, capsys):
    m = slc.measure(tmp_path, ["nowhere.md"])
    assert m["rows"][0]["status"] == "missing" and m["rows"][0]["tokens"] == 0
    assert len(m["problems"]) == 1
    assert "MISSING" in slc.format_report(m)


def test_an_unreadable_file_is_listed_not_fatal(tmp_path):
    (tmp_path / "bad.md").write_bytes(b"\xff\xfe\x00 not utf-8 \xc3\x28")
    row = slc.measure(tmp_path, ["bad.md"])["rows"][0]
    assert row["status"] == "unreadable"


def test_a_path_the_os_rejects_is_listed_not_a_crash(tmp_path):
    # A name over the 255-character component limit makes Path.is_file() raise on some
    # Python versions; the check is report-first, so it must list the row and carry on.
    _declare(tmp_path, "start_set:\n  - " + "a" * 300 + ".md\n")
    out = _run("--root", str(tmp_path))
    assert out.returncode == 0, out.stderr
    assert "Traceback" not in out.stderr
    row = json.loads(_run("--root", str(tmp_path), "--json").stdout)["rows"][0]
    assert row["status"] in ("missing", "unreadable")
    assert _run("--root", str(tmp_path), "--strict").returncode == 1


def test_a_symlink_loop_is_listed_not_a_crash(tmp_path):
    try:
        (tmp_path / "loop-a.md").symlink_to(tmp_path / "loop-b.md")
        (tmp_path / "loop-b.md").symlink_to(tmp_path / "loop-a.md")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    _declare(tmp_path, "start_set:\n  - loop-a.md\n")
    out = _run("--root", str(tmp_path))
    assert out.returncode == 0 and "Traceback" not in out.stderr
    assert json.loads(_run("--root", str(tmp_path), "--json").stdout)["rows"][0]["status"] in (
        "missing", "unreadable")


def test_a_default_start_set_without_a_runtime_file_says_so(tmp_path):
    root = _instance(tmp_path / "bare", runtime=None)
    assert "no CLAUDE.md or AGENTS.md at the root" in _run("--root", str(root)).stdout
    full = _instance(tmp_path / "full")
    assert "no CLAUDE.md or AGENTS.md" not in _run("--root", str(full)).stdout


# ── a declared start set ─────────────────────────────────────────────────────


def _declare(tmp_path, body, name="os/start-set.yaml"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_a_declaration_replaces_the_default_and_carries_a_budget(tmp_path):
    root = _instance(tmp_path)
    _declare(root, "start_set:\n  - os/agent-context.md\nbudget_tokens: 150\n")
    out = _run("--root", str(root), "--json")
    data = json.loads(out.stdout)
    assert [r["path"] for r in data["rows"]] == ["os/agent-context.md"]
    assert data["budget_tokens"] == 150
    assert data["total_tokens"] == 200 and out.returncode == 0  # over budget, but report-first


def test_the_cli_budget_overrides_the_declared_one(tmp_path):
    root = _instance(tmp_path)
    _declare(root, "start_set:\n  - os/agent-context.md\nbudget_tokens: 150\n")
    out = _run("--root", str(root), "--budget", "1000", "--strict")
    assert out.returncode == 0 and "within budget" in out.stdout


@pytest.mark.parametrize("body", [
    "start_set: []\n",
    "start_set: not-a-list\n",
    "start_set:\n  - 5\n",
    "- just\n- a list\n",
    "start_set: [unclosed\n",
])
def test_a_malformed_declaration_is_an_error(tmp_path, body):
    root = _instance(tmp_path)
    _declare(root, body)
    out = _run("--root", str(root))
    assert out.returncode == 2 and "start_load_check:" in out.stderr


def test_a_declared_path_cannot_leave_the_instance_root(tmp_path):
    root = _instance(tmp_path)
    outside = tmp_path.parent / "outside-the-root.md"
    outside.write_text("secret", encoding="utf-8")
    _declare(root, "start_set:\n  - ../outside-the-root.md\n")
    out = _run("--root", str(root))
    assert out.returncode == 2 and "outside the instance root" in out.stderr


def test_an_explicit_start_set_file_is_read(tmp_path):
    root = _instance(tmp_path)
    decl = _declare(root, "start_set:\n  - os/operating-principles.md\n", name="elsewhere/set.yaml")
    out = _run("--root", str(root), "--start-set", str(decl), "--json")
    assert [r["path"] for r in json.loads(out.stdout)["rows"]] == ["os/operating-principles.md"]


# ── the budget: none, under, over, strict, malformed ─────────────────────────


def test_no_budget_prints_the_notice_and_exits_zero(tmp_path):
    root = _instance(tmp_path)
    out = _run("--root", str(root), "--strict")
    assert out.returncode == 0
    assert "no budget declared" in out.stdout


def test_under_budget_exits_zero_even_when_strict(tmp_path):
    root = _instance(tmp_path)
    out = _run("--root", str(root), "--budget", "100000", "--strict")
    assert out.returncode == 0 and "within budget" in out.stdout


def test_over_budget_warns_and_exits_zero_by_default(tmp_path):
    root = _instance(tmp_path)
    out = _run("--root", str(root), "--budget", "10")
    assert out.returncode == 0
    assert "WARNING" in out.stdout and "over the budget" in out.stdout


def test_over_budget_exits_one_under_strict(tmp_path):
    root = _instance(tmp_path)
    assert _run("--root", str(root), "--budget", "10", "--strict").returncode == 1


def test_exactly_at_budget_is_within(tmp_path):
    root = _instance(tmp_path)
    total = slc.measure(root, slc.default_start_set(root))["total_tokens"]
    assert _run("--root", str(root), "--budget", str(total), "--strict").returncode == 0
    assert _run("--root", str(root), "--budget", str(total - 1), "--strict").returncode == 1


def test_a_missing_file_fails_only_under_strict(tmp_path):
    _declare(tmp_path, "start_set:\n  - nowhere.md\n")
    assert _run("--root", str(tmp_path)).returncode == 0
    strict = _run("--root", str(tmp_path), "--strict")
    assert strict.returncode == 1 and "WARNING: nowhere.md is missing" in strict.stdout


@pytest.mark.parametrize("value", ["true", "0", "-5", "lots", "1.5", ".nan", "null"])
def test_a_malformed_declared_budget_is_an_error_in_both_modes(tmp_path, value):
    root = _instance(tmp_path)
    _declare(root, "start_set:\n  - os/agent-context.md\nbudget_tokens: " + value + "\n")
    for flags in ([], ["--strict"]):
        out = _run("--root", str(root), *flags)
        assert out.returncode == 2, (value, flags, out.stdout)
        assert "positive integer" in out.stderr


@pytest.mark.parametrize("value", ["0", "-3"])
def test_a_malformed_cli_budget_is_an_error(tmp_path, value):
    root = _instance(tmp_path)
    assert _run("--root", str(root), "--budget", value).returncode == 2


def test_the_root_must_be_a_directory(tmp_path):
    assert _run("--root", str(tmp_path / "absent")).returncode == 2


# ── over keel's own tree ─────────────────────────────────────────────────────


def test_it_runs_over_keels_own_templates():
    """A fresh copy of the repository measures: templates stand in, nothing crashes."""
    out = _run()
    assert out.returncode == 0, out.stderr
    data = json.loads(_run("--json").stdout)
    assert data["total_tokens"] > 0
    assert any(r["status"] == "template" for r in data["rows"])


def _run(*args):
    return subprocess.run(
        [sys.executable, str(MODULE_PATH), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


# ── the documented start sequence: imports, the start file, the operator rows ──
#
# The default start set follows the runtime file's `@path` imports (a thin CLAUDE.md that
# imports AGENTS.md counts both), adds os/session-start.md, and adds the operator's profile and
# the newest entry of their handoff, resolved by os/resolve_operator.py. Git's global config is
# pointed at a file each test controls, so the developer's own email never decides a result.


@pytest.fixture
def git_email(tmp_path, monkeypatch):
    def set_email(email):
        config = tmp_path / ".gitconfig-test"
        config.write_text(f"[user]\n\temail = {email}\n" if email else "", encoding="utf-8")
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
        monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    set_email(None)
    return set_email


def _profile(root, operator, email, body="x" * 400):
    path = root / "os" / "operators" / f"{operator}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'---\noperator: "{operator}"\ngit_emails:\n  - "{email}"\nstatus: active\n---\n{body}\n', encoding="utf-8")


def _handoff(root, operator, newest_body, older_body):
    path = root / "os" / "handoff" / f"{operator}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Handoff\n\n## 2026-03-02 · newest\n\n{newest_body}\n\n## 2026-03-01 · older\n\n{older_body}\n", encoding="utf-8")


def test_a_thin_claude_md_counts_the_agents_md_it_imports(tmp_path, git_email):
    root = _instance(tmp_path)
    (root / "CLAUDE.md").write_text("<!-- thin -->\n\n@AGENTS.md\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("g" * 2000, encoding="utf-8")
    rows = _rows(slc.measure(root, slc.default_start_set(root)))
    assert list(rows)[:2] == ["CLAUDE.md", "AGENTS.md"]
    assert rows["AGENTS.md"]["tokens"] == 500 and "imported by CLAUDE.md" in rows["AGENTS.md"]["note"]


def test_imports_are_followed_recursively_and_each_file_counts_once(tmp_path, git_email):
    root = _instance(tmp_path)
    (root / "CLAUDE.md").write_text("@AGENTS.md\n@os/agent-context.md\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("@docs/more.md\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "more.md").write_text("@../AGENTS.md\n@../CLAUDE.md\n", encoding="utf-8")
    paths = [r["path"] for r in slc.measure(root, slc.default_start_set(root))["rows"]]
    assert paths[:4] == ["CLAUDE.md", "AGENTS.md", "docs/more.md", "os/agent-context.md"]
    assert len(paths) == len(set(paths))  # os/agent-context.md is not counted again as core


def test_only_real_imports_are_followed():
    text = "see `@in-code.md`\n```\n@fenced.md\n```\nmail a@b.md or @mention, then\n@real.md and @dir/also.md.\n"
    assert slc.imports_in(text) == ["real.md", "dir/also.md"]


def test_an_import_outside_the_root_is_listed_and_fails_strict(tmp_path, git_email):
    root = _instance(tmp_path / "inst")
    (tmp_path / "outside.md").write_text("o" * 400, encoding="utf-8")
    (root / "CLAUDE.md").write_text("@../outside.md\n@~/.personal/notes.md\n@missing.md\n", encoding="utf-8")
    m = slc.measure(root, slc.default_start_set(root))
    statuses = {r["path"]: r["status"] for r in m["rows"]}
    assert statuses["../outside.md"] == "outside" and statuses["~/.personal/notes.md"] == "outside"
    assert statuses["missing.md"] == "missing"
    assert all(r["tokens"] == 0 for r in m["rows"] if r["status"] == "outside")
    assert _run("--root", str(root)).returncode == 0
    assert _run("--root", str(root), "--strict").returncode == 1


def test_a_matched_operator_counts_their_profile_and_only_the_newest_handoff_entry(tmp_path, git_email):
    root = _instance(tmp_path)
    _profile(root, "ada", "ada@example.com")
    _profile(root, "lin", "lin@example.com")
    _handoff(root, "ada", "n" * 200, "o" * 4000)
    git_email("ada@example.com")
    rows = _rows(slc.measure(root, slc.default_start_set(root)))
    assert rows["os/operators/ada.md"]["status"] == "ok"
    entry = rows["os/handoff/ada.md"]
    assert entry["status"] == "ok" and "newest entry only, 1 of 2" in entry["note"]
    assert 50 <= entry["tokens"] < 100  # the 4,000-character older entry is not in it
    assert "os/operators/lin.md" not in rows


def test_operator_flag_picks_the_profile(tmp_path, git_email):
    root = _instance(tmp_path)
    _profile(root, "ada", "ada@example.com")
    _profile(root, "lin", "lin@example.com")
    data = json.loads(_run("--root", str(root), "--operator", "lin", "--json").stdout)
    assert "os/operators/lin.md" in [r["path"] for r in data["rows"]]


def test_an_unresolved_operator_counts_the_largest_profile_as_an_estimate(tmp_path, git_email):
    root = _instance(tmp_path)
    _profile(root, "ada", "ada@example.com", body="a" * 400)
    _profile(root, "lin", "lin@example.com", body="l" * 4000)
    git_email("nobody@example.com")
    m = slc.measure(root, slc.default_start_set(root))
    rows = _rows(m)
    assert rows["os/operators/lin.md"]["status"] == "estimate"
    assert "no-match" in rows["os/operators/lin.md"]["note"]
    assert m["problems"] == []  # an estimate is a number, not a failure


def test_no_profile_yet_measures_the_templates(tmp_path, git_email):
    root = _instance(tmp_path)
    (root / "os" / "operators").mkdir()
    (root / "os" / "operators" / "operator.template.md").write_text("t" * 800, encoding="utf-8")
    (root / "os" / "handoff.template.md").write_text("# H\n\n## [date] · example\n\n" + "e" * 120 + "\n", encoding="utf-8")
    rows = _rows(slc.measure(root, slc.default_start_set(root)))
    assert rows["os/operators/operator.template.md"]["status"] == "template"
    assert rows["os/operators/operator.template.md"]["tokens"] == 200
    assert rows["os/handoff.template.md"]["status"] == "template"


def test_a_matched_operator_without_a_handoff_file_measures_the_template_entry(tmp_path, git_email):
    root = _instance(tmp_path)
    _profile(root, "ada", "ada@example.com")
    (root / "os" / "handoff.template.md").write_text("# H\n\n## [date] · example\n\nbody\n", encoding="utf-8")
    git_email("ada@example.com")
    rows = _rows(slc.measure(root, slc.default_start_set(root)))
    assert rows["os/handoff.template.md"]["status"] == "template"
    assert "no handoff file yet" in rows["os/handoff.template.md"]["note"]


def test_an_unreadable_profile_is_listed_not_a_crash(tmp_path, git_email):
    root = _instance(tmp_path)
    (root / "os" / "operators").mkdir()
    (root / "os" / "operators" / "ada.md").write_text("no frontmatter\n", encoding="utf-8")
    out = _run("--root", str(root))
    assert out.returncode == 0 and "Traceback" not in out.stderr
    assert "UNREADABLE" in out.stdout


def test_keels_own_tree_counts_the_whole_start_sequence():
    """A fresh copy: the thin CLAUDE.md, AGENTS.md through its import, the start file, the
    core, the operator template and the handoff template's example entry."""
    data = json.loads(_run("--json").stdout)
    paths = [r["path"] for r in data["rows"]]
    for expected in ("CLAUDE.md", "AGENTS.md", "os/session-start.template.md",
                     "os/operators/operator.template.md", "os/handoff.template.md"):
        assert expected in paths, paths
    agents = next(r for r in data["rows"] if r["path"] == "AGENTS.md")
    assert agents["tokens"] > next(r for r in data["rows"] if r["path"] == "CLAUDE.md")["tokens"]
