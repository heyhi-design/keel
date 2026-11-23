#!/usr/bin/env python3
# origin: keel
"""
Operator resolver: which operator profile is running this session.

Few-person mode gives each person who runs sessions a profile in `os/operators/` (copied from
`os/operators/operator.template.md`). A session finds its operator by matching
`git config user.email` against each profile's `git_emails`. This script does that match and
refuses to guess: a session that cannot tell who is running it stops and asks, because a
default identity silently hands one person's preferences and approval rights to another
(`docs/operating-with-more-than-one.md`, Operators and handoffs).

Which files count as profiles: every `os/operators/*.md` except the template itself (any
`*.template.md`), a `README.md`, and any profile whose frontmatter says `status: inactive`. Only an explicit
`inactive` takes a profile out; an absent or unusual status still counts, so a typo can only
make the result louder, never quieter. Emails compare exactly, ignoring case and surrounding
whitespace.

The outcomes, each named, each with its own exit code:

  matched      exactly one profile lists the email                          exit 0
  no-profiles  no profile exists yet: a firm of one, the start step skips   exit 3
  no-email     profiles exist but `git config user.email` is not set        exit 1
  no-match     profiles exist and none lists the email                      exit 1
  ambiguous    two or more profiles list the email                          exit 1
  (error)      a profile cannot be read, or the arguments are wrong         exit 2

`no-profiles` exits nonzero on purpose: it is a stated skip, never an identity, so no script
can mistake it for a match. It is read-only: it never writes, and it never picks for you.

Usage:
    python3 os/resolve_operator.py                    # resolve for this repository's git email
    python3 os/resolve_operator.py --email you@example.com
    python3 os/resolve_operator.py --root path/to/instance --json
    python3 os/resolve_operator.py --list             # every profile and its emails

Requires PyYAML (see requirements.txt).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only when PyYAML is absent
    print("error: PyYAML is required. Install it with: python3 -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
OPERATORS_DIR = Path("os") / "operators"
HANDOFF_DIR = Path("os") / "handoff"

EXIT = {"matched": 0, "no-email": 1, "no-match": 1, "ambiguous": 1, "no-profiles": 3}


class ProfileError(Exception):
    """A profile exists but cannot be read as the contract says (exit code 2)."""


def read_frontmatter(path: Path) -> Dict[str, Any]:
    """The YAML frontmatter of a Markdown file as a mapping. Raises ProfileError if absent or bad."""
    try:
        text = path.read_text(encoding="utf-8-sig")  # an editor's byte-order mark is not content
    except (OSError, UnicodeDecodeError) as exc:
        raise ProfileError(f"{path.name}: cannot read ({type(exc).__name__})") from exc
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ProfileError(f"{path.name}: no frontmatter (the first line must be ---)")
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            break
    else:
        raise ProfileError(f"{path.name}: the frontmatter never closes (no second ---)")
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise ProfileError(f"{path.name}: the frontmatter does not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"{path.name}: the frontmatter is not a mapping")
    return data


def _normalize(email: object) -> str:
    return str(email).strip().lower()


def read_profile(path: Path, root: Path) -> Dict[str, Any]:
    """One profile, checked against the contract in operator.template.md."""
    data = read_frontmatter(path)
    operator = data.get("operator")
    if not isinstance(operator, str) or not operator.strip():
        raise ProfileError(f"{path.name}: `operator` must be a non-empty string")
    emails = data.get("git_emails")
    if not isinstance(emails, list) or not all(isinstance(e, str) and e.strip() for e in emails):
        raise ProfileError(f"{path.name}: `git_emails` must be a list of email strings")
    status = data.get("status")
    inactive = isinstance(status, str) and status.strip().lower() == "inactive"
    warnings: List[str] = []
    operator = operator.strip()
    if operator != path.stem:
        warnings.append(
            f"{path.name}: operator `{operator}` does not match the file name; the handoff path "
            f"is derived from the operator id, so rename one of them"
        )
    if "[" in operator or any("[" in e for e in emails):
        warnings.append(f"{path.name}: still has bracketed template slots")
    return {
        "operator": operator,
        "path": path.relative_to(root).as_posix(),
        "git_emails": [e.strip() for e in emails],
        "active": not inactive,
        "handoff": (HANDOFF_DIR / f"{operator}.md").as_posix(),
        "warnings": warnings,
    }


def list_profiles(root: Path) -> List[Dict[str, Any]]:
    """Every profile file under os/operators/, active or not, templates excluded. Sorted by path."""
    folder = root / OPERATORS_DIR
    if not folder.is_dir():
        return []
    files = sorted(
        p for p in folder.glob("*.md")
        if p.is_file() and not p.name.endswith(".template.md") and p.name.lower() != "readme.md"
    )
    return [read_profile(p, root) for p in files]


def git_email(root: Path) -> Optional[str]:
    """`git config user.email` as seen from root, or None when unset or git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "user.email"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def resolve(root: Path, email: Optional[str] = None, profiles: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Resolve the operator. Never raises for an outcome; raises ProfileError for a bad profile.

    Returns a mapping with `status` (one of the names in EXIT), `operator` and `path` when
    matched, the `email` compared, the matching `candidates`, a human `reason`, and any
    `warnings` the profiles carry.
    """
    if profiles is None:
        profiles = list_profiles(root)
    active = [p for p in profiles if p["active"]]
    warnings = [w for p in profiles for w in p["warnings"]]
    result: Dict[str, Any] = {
        "status": "",
        "operator": None,
        "path": None,
        "handoff": None,
        "email": None,
        "candidates": [],
        "reason": "",
        "warnings": warnings,
    }
    if not profiles:
        result["status"] = "no-profiles"
        result["reason"] = (
            "no operator profile in os/operators/: a firm of one that has not made a "
            "profile yet, so the operator step is skipped"
        )
        return result
    # Profiles exist but none is active: whoever is running the session (a deactivated
    # operator included) is not a firm of one without a profile. Fall through, so the email
    # matches nothing active and the answer is "stop and ask", never a stated skip.
    if email is None:
        email = git_email(root)
    result["email"] = email
    if not email:
        result["status"] = "no-email"
        result["reason"] = "git config user.email is not set, so no profile can be matched; stop and ask who is running the session"
        return result
    wanted = _normalize(email)
    matches = [p for p in active if wanted in (_normalize(e) for e in p["git_emails"])]
    result["candidates"] = [p["path"] for p in matches]
    if len(matches) == 1:
        match = matches[0]
        result.update(status="matched", operator=match["operator"], path=match["path"], handoff=match["handoff"])
        result["reason"] = f"{email} matches exactly one profile"
    elif not matches:
        result["status"] = "no-match"
        result["reason"] = f"{email} is in no active profile's git_emails; stop and ask who is running the session"
    else:
        result["status"] = "ambiguous"
        result["reason"] = (
            f"{email} is in {len(matches)} active profiles ({', '.join(result['candidates'])}); "
            f"an email may belong to one profile only, so stop and ask"
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve which operator profile is running this session.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="the instance root (default: this repository)")
    parser.add_argument("--email", default=None, help="compare this email instead of git config user.email")
    parser.add_argument("--list", action="store_true", help="list every profile, its emails and status, and exit 0")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f"resolve_operator: {root} is not a directory", file=sys.stderr)
        return 2
    try:
        profiles = list_profiles(root)
    except ProfileError as exc:
        print(f"resolve_operator: {exc}", file=sys.stderr)
        return 2

    if args.list:
        if args.json:
            print(json.dumps(profiles, indent=2))
        elif not profiles:
            print("no operator profiles in os/operators/")
        else:
            for p in profiles:
                state = "active" if p["active"] else "inactive"
                print(f"{p['operator']}  ({p['path']}, {state})  {', '.join(p['git_emails'])}")
        return 0

    result = resolve(root, args.email, profiles)
    code = EXIT[result["status"]]
    if args.json:
        print(json.dumps(dict(result, exit_code=code), indent=2))
    else:
        stream = sys.stdout if code == 0 else sys.stderr
        if result["status"] == "matched":
            print(f"operator: {result['operator']} ({result['path']})", file=stream)
            print(f"handoff:  {result['handoff']}", file=stream)
        else:
            print(f"operator: not resolved ({result['status']})", file=stream)
        print(f"reason:   {result['reason']}", file=stream)
        for warning in result["warnings"]:
            print(f"warning:  {warning}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
