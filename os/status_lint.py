#!/usr/bin/env python3
# origin: keel
"""
Status-vocabulary lint: every planning artifact says where it stands, in the shared words.

The Planning Artifact Convention (`os/session-rules.md`) gives every plan, spec, brief,
next-session prompt and dispatch file a `status:` frontmatter field, and a small vocabulary
for it: `pending` (not started), `partial` (some items done), `done`, `archived`
(superseded). A scanner can tell open work from done work only while the field is present
and uses those words. Left alone, status lines drift into free prose ("ready to execute",
"mostly there", twenty different first words), and the index that reads them rots with them.

This lint reads the first word of each artifact's `status:` and reports:
  - an artifact with no frontmatter, or no `status:` in it;
  - a first word outside the vocabulary;
  - a count of every first word in use, so drift is visible before it is everywhere.

Only the first word is checked: `status: partial  # items 3 and 4 remain` is fine, and so is
`status: done (2026-05-01)`. The vocabulary is keel's four words unless you pass your own with
`--vocab`; an instance that wants another word should add it there on purpose, once, rather
than let it appear by accident.

Which files, by default (under the root, skipping templates and the usual tool directories):
`*-plan.md`, `*-spec.md`, `*-brief.md`, `*next-session*.md`, and every `.md` in `os/dispatch/`
except its README. Name files or directories to check those instead.

Read-only. Exit 0 = every artifact passes; exit 1 = one or more fail; exit 2 = a bad
argument or a named path that does not exist.

Usage:
    python3 os/status_lint.py
    python3 os/status_lint.py plans/ os/dispatch/
    python3 os/status_lint.py --vocab pending,partial,done,archived,blocked
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
VOCABULARY = ("pending", "partial", "done", "archived")
DEFAULT_GLOBS = ("*-plan.md", "*-spec.md", "*-brief.md", "*next-session*.md")
DISPATCH_DIR = Path("os") / "dispatch"
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "env", ".pytest_cache", "node_modules"}

_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:[ \t]*(.*?)[ \t]*$")
_FIRST_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def frontmatter(text: str) -> Optional[Dict[str, str]]:
    """Top-level `key: value` scalars of a leading YAML block, or None if there is no block.

    Deliberately small: it reads one line per key, drops a trailing ` # comment` and
    surrounding quotes, and leaves nested or multi-line values as their first line. That is
    all a status, title or date needs, and it keeps this lint free of dependencies.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() in ("---", "..."):
            return fields
        if line[:1].isspace() or line.lstrip().startswith("#"):
            continue
        match = _KEY_RE.match(line)
        if not match:
            continue
        value = re.split(r"[ \t]+#", match.group(2), maxsplit=1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields.setdefault(match.group(1), value)
    return None  # never closed: not frontmatter


def first_word(status: str) -> str:
    match = _FIRST_WORD_RE.search(status)
    return match.group(0).lower() if match else ""


def default_targets(root: Path) -> List[Path]:
    found = set()
    for path in root.rglob("*.md"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or path.name.endswith(".template.md"):
            continue
        if any(fnmatch.fnmatch(path.name, g) for g in DEFAULT_GLOBS):
            found.add(path)
        elif rel.parent == DISPATCH_DIR and path.name.lower() != "readme.md":
            found.add(path)
    return sorted(found)


def named_targets(root: Path, names: List[str]) -> List[Path]:
    found = set()
    for name in names:
        path = Path(name) if Path(name).is_absolute() else root / name
        if path.is_dir():
            found.update(p for p in path.rglob("*.md") if not p.name.endswith(".template.md"))
        elif path.is_file():
            found.add(path)
        else:
            raise FileNotFoundError(name)
    return sorted(found)


def lint_file(path: Path, vocab: Tuple[str, ...]) -> Tuple[str, Optional[str]]:
    """(first word, problem or None)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return "", f"cannot read ({type(exc).__name__})"
    fields = frontmatter(text)
    if fields is None:
        return "", "no frontmatter, so no status"
    if "status" not in fields or not fields["status"]:
        return "", "no status: field"
    word = first_word(fields["status"])
    if word not in vocab:
        return word, f"status starts with {word or fields['status']!r}, not one of {', '.join(vocab)}"
    return word, None


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check planning artifacts' status: fields against the vocabulary.")
    parser.add_argument("paths", nargs="*", help="files or directories to check (default: the planning-artifact globs)")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="the instance root (default: this repository)")
    parser.add_argument("--vocab", default=",".join(VOCABULARY), help="comma-separated allowed first words")
    parser.add_argument("--quiet", action="store_true", help="print only on failure")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    vocab = tuple(w.strip().lower() for w in args.vocab.split(",") if w.strip())
    if not vocab:
        print("status_lint: --vocab is empty", file=sys.stderr)
        return 2
    try:
        files = named_targets(root, args.paths) if args.paths else default_targets(root)
    except FileNotFoundError as exc:
        print(f"status_lint: no such file or directory: {exc}", file=sys.stderr)
        return 2

    words: Counter = Counter()
    problems = []
    for path in files:
        word, problem = lint_file(path, vocab)
        words[word or "(none)"] += 1
        if problem:
            problems.append((_rel(path, root), problem))

    if problems:
        print(f"Status lint: {len(problems)} of {len(files)} artifact(s) fail:\n", file=sys.stderr)
        for rel, problem in problems:
            print(f"  - {rel}: {problem}", file=sys.stderr)
    if problems or not args.quiet:
        stream = sys.stderr if problems else sys.stdout
        if files:
            used = ", ".join(f"{w} {n}" for w, n in sorted(words.items(), key=lambda kv: (-kv[1], kv[0])))
            print(f"\nFirst words in use ({len(words)}): {used}", file=stream)
        if not files:
            print("Status lint: no planning artifacts found, so nothing to check.", file=stream)
        elif not problems:
            print(f"Status lint: {len(files)} artifact(s) checked, every status in: {', '.join(vocab)}.", file=stream)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
