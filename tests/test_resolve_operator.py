"""
The operator resolver (os/resolve_operator.py).

The promise that matters is that it never guesses: exactly one matching profile is the only
outcome that yields an identity. Zero matches, two matches, and no git email each fail loud,
with a named reason and a nonzero exit; no profiles at all is a stated skip (also nonzero, so
no caller mistakes it for a match). Templates and inactive profiles never count.
"""

import json
import subprocess
import sys

import pytest

from conftest import REPO_ROOT, load_tool

ro = load_tool("os/resolve_operator.py", "resolve_operator_under_test")
SCRIPT = REPO_ROOT / "os" / "resolve_operator.py"


def profile(repo, operator, emails, status="active", name=None):
    lines = "\n".join(f'  - "{e}"' for e in emails)
    repo.write(
        f"os/operators/{name or operator}.md",
        f'---\noperator: "{operator}"\nname: "{operator}"\ngit_emails:\n{lines}\nrole: member\n'
        f"approves:\n  - engagement\nstatus: {status}\n---\n\n# {operator}\n",
    )


def run(repo, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(repo.path), *args],
        capture_output=True, text=True, env=repo.env,
    )


def test_exactly_one_match_is_the_only_identity(scratch_repo):
    profile(scratch_repo, "ada", ["ada@example.com"])
    profile(scratch_repo, "lin", ["lin@example.com", "lin.alt@example.com"])
    result = ro.resolve(scratch_repo.path, "LIN.ALT@example.com ")
    assert result["status"] == "matched"
    assert result["operator"] == "lin"
    assert result["path"] == "os/operators/lin.md"
    assert result["handoff"] == "os/handoff/lin.md"


def test_the_cli_reads_git_config_user_email(scratch_repo):
    profile(scratch_repo, "ada", ["ada@example.com"])
    scratch_repo.git("config", "user.email", "ada@example.com")
    out = run(scratch_repo)
    assert out.returncode == 0, out.stderr
    assert "operator: ada" in out.stdout


def test_no_matching_profile_fails_loud(scratch_repo):
    profile(scratch_repo, "ada", ["ada@example.com"])
    scratch_repo.git("config", "user.email", "someone-else@example.com")
    out = run(scratch_repo)
    assert out.returncode == 1
    assert "no-match" in out.stderr and "stop and ask" in out.stderr
    assert "operator: ada" not in out.stdout + out.stderr


def test_two_matching_profiles_fail_loud(scratch_repo):
    profile(scratch_repo, "ada", ["shared@example.com"])
    profile(scratch_repo, "lin", ["shared@example.com"])
    out = run(scratch_repo, "--email", "shared@example.com", "--json")
    assert out.returncode == 1
    data = json.loads(out.stdout)
    assert data["status"] == "ambiguous" and data["operator"] is None
    assert sorted(data["candidates"]) == ["os/operators/ada.md", "os/operators/lin.md"]


def test_no_git_email_fails_loud(scratch_repo):
    profile(scratch_repo, "ada", ["ada@example.com"])
    out = run(scratch_repo)
    assert out.returncode == 1
    assert "no-email" in out.stderr


def test_no_profiles_is_a_stated_skip_never_an_identity(scratch_repo):
    scratch_repo.write("os/operators/operator.template.md", "---\noperator: \"[operator-id]\"\ngit_emails:\n  - \"[you@example.com]\"\n---\n")
    out = run(scratch_repo, "--email", "anyone@example.com", "--json")
    assert out.returncode == 3
    data = json.loads(out.stdout)
    assert data["status"] == "no-profiles" and data["operator"] is None


def test_templates_and_inactive_profiles_never_match(scratch_repo):
    profile(scratch_repo, "gone", ["ada@example.com"], status="inactive")
    profile(scratch_repo, "operator.template", ["ada@example.com"], name="operator.template")
    profile(scratch_repo, "ada", ["ada@example.com"])
    result = ro.resolve(scratch_repo.path, "ada@example.com")
    assert result["status"] == "matched" and result["operator"] == "ada"


def test_only_an_explicit_inactive_status_takes_a_profile_out(scratch_repo):
    profile(scratch_repo, "ada", ["ada@example.com"], status="Inactive")
    profile(scratch_repo, "lin", ["ada@example.com"], status="archived")
    result = ro.resolve(scratch_repo.path, "ada@example.com")
    assert result["status"] == "matched" and result["operator"] == "lin"


@pytest.mark.parametrize("body, reason", [
    ("# no frontmatter\n", "no frontmatter"),
    ("---\noperator: ada\ngit_emails: [\n---\n", "does not parse"),
    ("---\noperator: ada\ngit_emails: ada@example.com\n---\n", "must be a list"),
    ("---\ngit_emails:\n  - ada@example.com\n---\n", "`operator`"),
    ("---\noperator: ada\ngit_emails:\n  - ada@example.com\n", "never closes"),
])
def test_an_unreadable_profile_is_an_error_not_a_skip(scratch_repo, body, reason):
    scratch_repo.write("os/operators/ada.md", body)
    out = run(scratch_repo, "--email", "ada@example.com")
    assert out.returncode == 2
    assert reason in out.stderr


def test_a_mismatched_file_name_and_placeholders_are_warned(scratch_repo):
    profile(scratch_repo, "ada", ["[you@example.com]"], name="ada-lovelace")
    result = ro.resolve(scratch_repo.path, "x@example.com")
    assert any("does not match the file name" in w for w in result["warnings"])
    assert any("bracketed template slots" in w for w in result["warnings"])


def test_list_shows_every_profile(scratch_repo):
    profile(scratch_repo, "ada", ["ada@example.com"])
    profile(scratch_repo, "gone", ["gone@example.com"], status="inactive")
    out = run(scratch_repo, "--list")
    assert out.returncode == 0
    assert "ada" in out.stdout and "inactive" in out.stdout


def test_keels_own_tree_has_no_profiles_only_the_template():
    out = subprocess.run([sys.executable, str(SCRIPT), "--email", "x@example.com", "--json"], capture_output=True, text=True)
    assert out.returncode == 3, out.stderr
    assert json.loads(out.stdout)["status"] == "no-profiles"


def test_a_byte_order_mark_and_a_readme_do_not_break_resolution(scratch_repo):
    profile(scratch_repo, "ada", ["ada@example.com"])
    path = scratch_repo.path / "os" / "operators" / "ada.md"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    scratch_repo.write("os/operators/README.md", "# Operators\n\nOne profile per person.\n")
    result = ro.resolve(scratch_repo.path, "ada@example.com")
    assert result["status"] == "matched" and result["operator"] == "ada"


def test_a_deactivated_operator_is_told_to_stop_and_ask_not_skipped(scratch_repo):
    # Profiles exist but none is active: this is not a firm of one without a profile, so
    # the deactivated person's own email must not read as a stated skip (exit 3).
    profile(scratch_repo, "gone", ["gone@example.com"], status="inactive")
    result = ro.resolve(scratch_repo.path, "gone@example.com")
    assert result["status"] == "no-match"
