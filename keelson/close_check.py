#!/usr/bin/env python3
# origin: keel
"""
keelson -- close check: was the Exit Gate report persisted, with every slot filled?

The Exit Gate (`os/session-rules.md`) asks every session to close with a report under named
headings, and to persist that report somewhere tracked rather than leave it in the chat: the
newest entry of the operator's handoff file in commit close mode, or the pull request body in
PR close mode. A report that lives only in the chat is gone when the chat is, and an empty
heading is a failure the next reader should be able to see. This lint makes both checkable.

What it checks, by the slot names the Exit Gate defines:

  Flavor A   Fixes Applied, Smoke Test, Next Session Prompt
  Flavor B   the three above, plus Findings Integration and Session Integrity. An entry that
             carries either of the two extra slots is Flavor B and must carry all five.

Each required slot must be present (matched by name, ignoring case) and must hold something:
a slot that is empty, or holds only an HTML comment, an unfilled `[bracketed placeholder]`
(even one wrapped across lines), a bare list marker, or a stand-in like TBD or TODO, fails.
It checks that something was written, not that it is any good: that read stays with a person. In a handoff file the slots are level-3 headings inside a dated level-2 entry
(`## YYYY-MM-DD · title`); in a PR body (--pr-body) they are level-2 headings.

One allowance, from the handoff contract: in PR close mode (`operating_mode.close_mode: pr` in
os/project-state.yaml) a handoff entry may instead be only the link of each pull request the
session opened, one per line, since the pull request body carries the report. In commit mode
a link-only entry fails, because nothing else holds the report.

Read-only, and a lint: it exits 1 when a report fails, so it can gate a pull request or a CI
step. It installs nothing; wiring it into your own runtime's hooks is your choice to make.

Usage:
    python3 keelson/close_check.py                          # newest entry, operator from git config
    python3 keelson/close_check.py os/handoff/ada.md        # newest entry of one file
    python3 keelson/close_check.py os/handoff/ada.md --all  # every entry in it
    python3 keelson/close_check.py --pr-body body.md        # a pull request body saved to a file

Exit 0 = the report passes; exit 1 = a slot is missing or empty, the entry is malformed, or
there is no entry; exit 2 = the file cannot be read or the operator cannot be resolved.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

KEEL_ROOT = Path(__file__).resolve().parent.parent
FLAVOR_A = ("Fixes Applied", "Smoke Test", "Next Session Prompt")
FLAVOR_B_EXTRA = ("Findings Integration", "Session Integrity")

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t#]*$")
_DATED_RE = re.compile(r"^ {0,3}##[ \t]+\d{4}-\d{2}-\d{2}\b")
_LINK_LINE_RE = re.compile(r"^\s*(?:[-*+]\s+)?<?https?://\S+>?\s*$")
# A bracketed span not followed by `(` (a link) or `:` (a reference definition): a template slot.
_BRACKET_RE = re.compile(r"\[[^\]]*\](?![(:\[])", re.S)
_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])(?:\s+\[[ xX]\])?(?=\s|$)")
_FILLERS = {"", "tbd", "todo", "tk", "xxx", "n/a", "na", "...", "placeholder", "fill this in", "to do"}
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def _load(relative: str, name: str):
    path = KEEL_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sections(text: str, level: int) -> List[Tuple[str, str]]:
    """[(heading text, body)] for every heading of exactly `level`, fences respected.

    A section's body runs to the next heading of the same or a higher level.
    """
    out: List[Tuple[str, List[str]]] = []
    fence: Optional[str] = None
    for line in text.splitlines():
        match = _FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
        heading = None if fence is not None or match else _HEADING_RE.match(line)
        if heading and len(heading.group(1)) <= level:
            if len(heading.group(1)) == level:
                out.append((heading.group(2).strip(), []))
            else:
                out.append(("", []))  # a higher heading closes the open section
            continue
        if out:
            out[-1][1].append(line)
    return [(name, "\n".join(body)) for name, body in out if name]


def has_content(body: str) -> bool:
    """True when a slot says something: not blank, not a comment, not an unfilled placeholder.

    Removed before looking: HTML comments; bracketed template slots, even ones wrapped across
    lines (`[A copy-pasteable paragraph ... resume.]`), unless they are a link's text; list
    markers with nothing after them; and the usual stand-ins (TBD, TODO, n/a, ...).
    """
    text = _COMMENT_RE.sub("", body)
    text = _BRACKET_RE.sub(" ", text)
    for line in text.splitlines():
        words = _MARKER_RE.sub("", line).strip()
        if words and words.strip(".:;,-*_ ").lower() not in _FILLERS:
            return True
    return False


def check_slots(text: str, level: int) -> List[str]:
    """The failures in one report, given the heading level its slots sit at."""
    found: Dict[str, str] = {}
    for name, body in sections(text, level):
        found.setdefault(name.lower(), body)
    flavor_b = any(slot.lower() in found for slot in FLAVOR_B_EXTRA)
    required = FLAVOR_A + (FLAVOR_B_EXTRA if flavor_b else ())
    problems = []
    for slot in required:
        body = found.get(slot.lower())
        if body is None:
            problems.append(f"missing slot: {slot}" + (" (Flavor B carries all five)" if flavor_b else ""))
        elif not has_content(body):
            problems.append(f"empty slot: {slot}")
    return problems


def _link_only(body: str) -> bool:
    lines = [ln for ln in _COMMENT_RE.sub("", body).splitlines() if ln.strip()]
    return bool(lines) and all(_LINK_LINE_RE.match(ln) for ln in lines)


def close_mode(root: Path) -> str:
    """operating_mode.close_mode, or 'commit' (the default) when it cannot be read."""
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return "commit"
    for name in ("project-state.yaml", "project-state.template.yaml"):
        path = root / "os" / name
        if path.is_file():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                mode = data["operating_mode"]["close_mode"]
            except Exception:
                return "commit"
            return mode if isinstance(mode, str) else "commit"
    return "commit"


def check_entry(entry: str, mode: str) -> List[str]:
    heading, _, body = entry.partition("\n")
    problems = []
    if not _DATED_RE.match(heading):
        problems.append("the entry heading must read `## YYYY-MM-DD · title`")
    if _link_only(body):
        if mode != "pr":
            problems.append("a link-only entry is allowed only in PR close mode (operating_mode.close_mode: pr)")
        return problems
    return problems + check_slots(body, 3)


class Unresolved(Exception):
    """No handoff file to check: the operator cannot be resolved (exit code 2)."""


def resolve_handoff(root: Path) -> Path:
    resolver = _load("os/resolve_operator.py", "keel_resolve_operator")
    try:
        result = resolver.resolve(root)
    except resolver.ProfileError as exc:
        raise Unresolved(str(exc)) from exc
    if result["status"] != "matched":
        raise Unresolved(f"operator not resolved ({result['status']}): {result['reason']}; pass the handoff file")
    return root / result["handoff"]


def _fail(code: int, message: str) -> int:
    print(f"close_check: {message}", file=sys.stderr)
    return code


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check that the Exit Gate report was persisted with every slot filled.")
    parser.add_argument("file", nargs="?", type=Path, default=None, help="a handoff file, or with --pr-body a PR body")
    parser.add_argument("--pr-body", action="store_true", help="the file is a pull request body (slots are level-2 headings)")
    parser.add_argument("--all", action="store_true", help="check every handoff entry, not only the newest")
    parser.add_argument("--root", type=Path, default=KEEL_ROOT, help="the instance root (default: this repository)")
    parser.add_argument("--quiet", action="store_true", help="print only on failure")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.file is None:
        if args.pr_body:
            return _fail(2, "--pr-body needs the file the body was saved to")
        try:
            path = resolve_handoff(root)
        except Unresolved as exc:
            return _fail(2, str(exc))
    else:
        path = args.file if args.file.is_absolute() or args.file.exists() else root / args.file
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _fail(2, f"cannot read {path}: {type(exc).__name__}")

    if args.pr_body:
        reports = [("pull request body", check_slots(text, 2))]
    else:
        entries = _load("os/handoff_rotate.py", "keel_handoff_rotate").split_entries(text)[1]
        if not entries:
            print(f"close_check: {path.name}: FAIL, no entry: the Exit Gate report was not persisted", file=sys.stderr)
            return 1
        mode = close_mode(root)
        chosen = entries if args.all else entries[:1]
        reports = [(e.splitlines()[0].strip(), check_entry(e, mode)) for e in chosen]

    failed = [(name, problems) for name, problems in reports if problems]
    if failed:
        for name, problems in failed:
            print(f"close_check: {path.name}: FAIL {name}", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
        return 1
    if not args.quiet:
        which = "the PR body" if args.pr_body else f"{len(reports)} entr{'y' if len(reports) == 1 else 'ies'}"
        print(f"close_check: {path.name}: {which} passed (every required slot present and filled)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
