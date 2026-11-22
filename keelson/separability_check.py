#!/usr/bin/env python3
"""
keelson -- separability check

The keelson convention lets a keel instance keep its base-tagged files liftable. A file that
is part of the generic, shareable base declares `origin: keel`; a file that is specific to
this instance declares `origin: instance`. This script is the lint that makes the claim
checkable: it fails if a file that calls itself `origin: keel` reaches into content you have
declared private to the instance.

Why it exists: a mechanism proven inside one instance is only safe to bind up into the
public keel base if it drags none of that instance's private content with it. Tag the
candidate `origin: keel`, run this check, and a clean pass is the mechanical proof that the
lift is clean -- the thing that lets the moat filter stay a standing membrane rather than a
one-time read someone remembers to do.

What this does NOT do: it does not decide whether a file *should* be base or instance, and
it does not read code semantically. It checks one thing -- that a file claiming keel origin
carries no reference to a path you have declared instance-private. Whether a mechanism is
genuinely generic, and worth lifting at all, stays a human judgment.

How a file is tagged:
  - Markdown: an HTML comment as the first non-empty line, `<!-- origin: keel -->`
    (invisible when the Markdown is rendered).
  - Every other text file: a header comment in the first lines, e.g. `# origin: keel`.
  A file with no tag makes no claim and is skipped. Tag the files you intend to keep liftable.

Instance-private paths default to `examples/` (keel's own instance content). Add your own
with --private (repeatable), e.g. --private clients/ --private financial/.

A "reference" is the path used *as a path*, not merely named in prose:
  - in Markdown, a link or image target that points into the path -- `](examples/...)`;
  - in every other file, the path in a quoted string, or its top segment in an
    `import` / `from` statement.
A backticked mention or plain prose ("see the examples directory") is illustrative, not a
reference, and is left alone -- otherwise a file could never *describe* the boundary it
keeps, this script and its README included.

Usage:
    python3 keelson/separability_check.py [root]              # default root: .
    python3 keelson/separability_check.py . --private clients/
    python3 keelson/separability_check.py --quiet

Exit 0 = every origin:keel file is clean; exit 1 = one or more references found; exit 2 =
the root is not a directory.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Text files worth scanning. A suffix not listed here carries no liftable source we can read
# as text (images, compiled artifacts, SVG figures), so it is skipped rather than guessed at.
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".json", ".txt", ".cfg", ".ini", ".sh"}

# Directories never worth walking into.
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "env", ".pytest_cache", "node_modules"}

# keel's own instance content lives here, and it is the one place filled content is allowed.
# An instance adds its own private trees (clients/, financial/, ...) with --private.
DEFAULT_PRIVATE = ("examples/",)

# The origin tag in a code/config file: `origin: keel` or `origin: instance`, anchored to a
# line start (optionally behind a comment marker) and required to be followed by keel|instance,
# so `origin_date:` and prose like "its origin is unclear" are never read as a tag.
_TAG_RE = re.compile(r"(?m)^[ \t]*(?:#|//|;|--)?[ \t]*origin:[ \t]*(keel|instance)\b")

# The Markdown tag: an HTML comment carrying the whole line. Restricting it to the first
# non-empty line (below) keeps a fenced example or a prose mention in the body from being
# read as the file's own tag.
_MD_TAG_RE = re.compile(r"^\s*<!--\s*origin:\s*(keel|instance)\s*-->\s*$")

# A code-file tag belongs in the header. Reading only the first lines keeps a stray body
# line that happens to say "origin: keel" (an example inside a docstring) from being read as
# the file's own tag.
TAG_SCAN_LINES = 20


def read_text(path: Path) -> str | None:
    """The file's text, or None if it is not readable UTF-8 (a binary, a broken symlink)."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def origin_tag(path: Path, text: str) -> str | None:
    """The origin this file declares ('keel' | 'instance'), or None if it is untagged.

    Markdown declares it as an HTML comment on the first non-empty line; every other file
    type declares it in a header comment. Restricting each to its proper place keeps a prose
    mention or a fenced example of the tag in a document body (this convention's own README,
    say) from being read as a declaration.
    """
    if path.suffix == ".md":
        for line in text.splitlines():
            if not line.strip():
                continue
            match = _MD_TAG_RE.match(line)  # only the first non-empty line can carry the tag
            return match.group(1) if match else None
        return None
    region = "\n".join(text.splitlines()[:TAG_SCAN_LINES])
    match = _TAG_RE.search(region)
    return match.group(1) if match else None


def references(path: Path, text: str, private_path: str) -> list[str]:
    """Reference-position occurrences of `private_path` in this file, by file type.

    Markdown: a link or image target that points into the path -- `](examples/...)`.
    Every other file: the path inside a quoted string, or its top segment named in an
    `import` / `from` statement.

    A backticked mention or bare prose is not a reference: a document has to be able to
    describe the boundary it respects without tripping the check that enforces it. The
    trade-off is that an *unquoted* path in a config value is not matched either -- quote a
    path you mean as a path, and this catches it.
    """
    if path.suffix == ".md":
        link = re.compile(r"!?\]\(\s*<?" + re.escape(private_path))
        return link.findall(text)
    segment = private_path.rstrip("/").split("/")[0]  # "examples/" -> "examples"
    quoted = re.compile(r"""["']""" + re.escape(private_path))
    imported = re.compile(r"\b(?:import|from)\s+" + re.escape(segment) + r"\b")
    return quoted.findall(text) + imported.findall(text)


def scan(root: Path, private: list[str]):
    """Walk `root` and return (violations, keel_tagged_count).

    A violation is (relative_path, private_path, sample) for each origin:keel file that
    references an instance-private path. keel_tagged_count is how many origin:keel files
    were checked -- reported so a clean run is visibly non-vacuous.
    """
    violations = []
    keel_tagged = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        text = read_text(path)
        if text is None:
            continue
        if origin_tag(path, text) != "keel":
            continue
        keel_tagged += 1
        rel = path.relative_to(root)
        for private_path in private:
            hits = references(path, text, private_path)
            if hits:
                violations.append((str(rel), private_path, hits[0]))
    return violations, keel_tagged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="keelson separability check: no origin:keel file may reference "
        "instance-private content."
    )
    parser.add_argument("root", nargs="?", default=".", help="Directory to scan (default: .).")
    parser.add_argument(
        "--private",
        action="append",
        default=[],
        metavar="PATH",
        help="An instance-private path prefix an origin:keel file may not reference. "
        "Repeatable. Adds to the default 'examples/'.",
    )
    parser.add_argument("--quiet", action="store_true", help="Print only on failure.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    private = list(DEFAULT_PRIVATE) + list(args.private)
    violations, keel_tagged = scan(root, private)

    if violations:
        print(
            f"Separability: {len(violations)} reference(s) from origin:keel files into "
            f"instance-private content:\n",
            file=sys.stderr,
        )
        for rel, private_path, sample in violations:
            print(f"  - {rel}: references instance-private '{private_path}' ({sample!r})", file=sys.stderr)
        print(
            "\nEither the file is not liftable after all (retag it origin:instance), or it "
            "should not point into instance-private content (fix the reference).",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(
            f"Separability: {keel_tagged} origin:keel file(s) checked, none reference "
            f"instance-private content ({', '.join(private)})."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
