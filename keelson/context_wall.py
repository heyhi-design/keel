#!/usr/bin/env python3
# origin: keel
"""
keelson -- context-wall lint

The separability check (separability_check.py) proves that a file claiming `origin: keel`
does not point into instance-private *paths*. That catches a link; it cannot catch a name. A
base file can be free of private paths and still carry the instance's client name, a
colleague's first name, an internal ticket key, or a product codename in its prose. The
context wall is the second half of the membrane: it checks the same files for *phrases*.

The phrases come from a map the instance writes and keeps. The map is instance content (it is
a list of exactly the things that must not travel), so keel ships none and never will: you
pass yours with --map, and the lint refuses to run without one rather than pass vacuously.

The map is plain text, one entry per line:

    # a comment
    Example Client Co -> a client
    examplecodename
    re:\\bEXC-\\d+\\b -> a ticket id

  - A plain entry is a phrase, matched case-insensitively and only as a whole word or words
    (so a short name does not fire inside a longer word).
  - An entry starting `re:` is a regular expression, matched case-insensitively.
  - ` -> replacement` is optional: the neutral wording to use instead, printed with each hit.

What gets checked:
  - by default, every file under the root that declares `origin: keel` (the files you mean to
    lift), the same set the separability check reads;
  - with --all, every file under the root (only `.git/` is skipped), tagged or not, whatever
    its name or suffix, except binaries (a NUL byte in the first 8 KB), which are listed as
    not checked. Use this on an
    export directory, the tree that is about to leave the instance. A file that is not UTF-8
    is still read, its undecodable bytes standing in as replacement characters.

Each file is matched as a whole, so a phrase that a hard-wrapped paragraph splits across two
lines is still caught. What it cannot see: a phrase inside an image, a PDF, or any other
binary; a phrase split by markup (`Example <b>Client</b> Co`); a spelling the map does not
list. The map is the instance's to keep complete.

Hits are printed by file, line, and map line number. The phrase itself is not printed unless
you pass --show-phrases, because the output of a lint often lands in a CI log, and a log is
one more place the phrase would travel. The file and line are enough to find it.

Report-only: it never edits a file. Neutralizing a hit is a human edit, because the right
replacement depends on what the sentence is saying.

Usage:
    python3 keelson/context_wall.py --map ../private/context-wall.map          # origin:keel files under .
    python3 keelson/context_wall.py path/to/export --all --map ../private/context-wall.map
    python3 keelson/context_wall.py --map context-wall.map --show-phrases

Exit 0 = no hits; exit 1 = one or more hits; exit 2 = no usable map (absent, empty, a bad
expression, tagged origin:keel, or inside the --all tree it would ship with) or the root is
not a directory.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def _load_separability():
    path = Path(__file__).resolve().parent / "separability_check.py"
    spec = importlib.util.spec_from_file_location("keelson_separability_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sep = _load_separability()


class MapError(Exception):
    """The phrase map is unusable (exit code 2)."""


Entry = Tuple[int, "re.Pattern[str]", str, str]  # (map line, pattern, phrase as written, replacement)


def read_map(path: Path) -> List[Entry]:
    """Parse the phrase map. Raises MapError on anything that would make the lint vacuous."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise MapError(f"cannot read the phrase map {path}: {type(exc).__name__}") from exc
    entries: List[Entry] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        phrase, _, replacement = line.partition(" -> ")
        phrase, replacement = phrase.strip(), replacement.strip()
        if phrase.startswith("re:"):
            source = phrase[3:].strip()
            if not source:
                raise MapError(f"map line {number}: an empty expression")
            try:
                pattern = re.compile(source, re.IGNORECASE)
            except re.error as exc:
                raise MapError(f"map line {number}: not a valid expression ({exc})") from exc
            if pattern.search(""):
                raise MapError(f"map line {number}: the expression matches empty text, so it would match everywhere")
        else:
            if not phrase:
                raise MapError(f"map line {number}: an empty phrase")
            words = r"\s+".join(re.escape(w) for w in phrase.split())
            pattern = re.compile(r"(?<![A-Za-z0-9])" + words + r"(?![A-Za-z0-9])", re.IGNORECASE)
        entries.append((number, pattern, phrase, replacement))
    if not entries:
        raise MapError(f"the phrase map {path} has no entries, so the check would pass vacuously")
    return entries


def _read_any(path: Path) -> Optional[str]:
    """A file's text for phrase matching, or None for a binary (a NUL byte in its first 8 KB).

    Not UTF-8 is not a reason to skip: undecodable bytes become U+FFFD and every phrase that
    does not cross one still matches, so a Latin-1 file is checked rather than waved through.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def candidate_files(root: Path, every: bool, skip: Optional[Path]) -> Tuple[List[Path], List[str]]:
    """(files to check, files skipped as binary or unreadable, by relative path)."""
    files, skipped = [], []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        # In --all mode only git's own folder is skipped; a folder named `env` or `venv` can
        # hold real docs, and a silent skip would read as clean.
        if (every and ".git" in rel.parts) or (not every and any(part in sep.SKIP_DIRS for part in rel.parts)):
            continue
        if skip is not None and path.resolve() == skip:
            continue
        if every:
            if _read_any(path) is None:
                skipped.append(rel.as_posix())
            else:
                files.append(path)
            continue
        if path.suffix not in sep.TEXT_SUFFIXES:
            continue
        text = sep.read_text(path)
        if text is not None and sep.origin_tag(path, text) == "keel":
            files.append(path)
    return files, skipped


def scan(root: Path, entries: List[Entry], every: bool = False, skip: Optional[Path] = None):
    """Return (hits, files_checked, skipped). A hit is (relative path, line, map line, phrase, replacement).

    Each file is matched whole, so a phrase hard-wrapped across two lines is still caught; the
    line reported is where the match starts.
    """
    hits = []
    checked = 0
    files, skipped = candidate_files(root, every, skip)
    for path in files:
        text = _read_any(path)
        if text is None:
            skipped.append(path.relative_to(root).as_posix())
            continue
        checked += 1
        rel = path.relative_to(root).as_posix()
        for map_line, pattern, phrase, replacement in entries:
            for match in pattern.finditer(text):
                number = text.count("\n", 0, match.start()) + 1
                hits.append((rel, number, map_line, phrase, replacement))
    hits.sort(key=lambda h: (h[0], h[1], h[2]))
    return hits, checked, skipped


def check_map_placement(map_path: Path, root: Path, every: bool) -> None:
    """The map must never travel with what it guards."""
    text = sep.read_text(map_path) or ""
    tagged_keel = sep.origin_tag(map_path, text) == "keel" if map_path.suffix in sep.TEXT_SUFFIXES else bool(
        re.search(r"(?m)^\s*(?:#|//|<!--)?\s*origin:\s*keel\b", text))
    if tagged_keel:
        raise MapError("the phrase map is tagged origin: keel; it is instance content and must never be lifted")
    if every:
        try:
            map_path.relative_to(root)
        except ValueError:
            return
        raise MapError("the phrase map is inside the tree being checked with --all, so it would ship with it; keep it outside")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="keelson context wall: no checked file may carry an instance phrase.")
    parser.add_argument("root", nargs="?", default=".", help="Directory to scan (default: .).")
    parser.add_argument("--map", type=Path, default=None, help="The instance's phrase map (required; keel ships none).")
    parser.add_argument("--all", action="store_true", help="Check every text file under the root, not only origin:keel files.")
    parser.add_argument("--show-phrases", action="store_true", help="Print the matched phrase with each hit (keep out of shared logs).")
    parser.add_argument("--quiet", action="store_true", help="Print only on failure.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    if args.map is None:
        print("error: no phrase map. Pass --map PATH: the map is your instance's own content, and keel ships none.", file=sys.stderr)
        return 2
    map_path = args.map.resolve()
    try:
        entries = read_map(map_path)
        check_map_placement(map_path, root, args.all)
    except MapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    hits, checked, skipped = scan(root, entries, args.all, map_path)
    scope = "file(s)" if args.all else "origin:keel file(s)"
    if skipped:
        print(f"Context wall: {len(skipped)} binary or unreadable file(s) not checked: "
              + ", ".join(skipped[:5]) + (", ..." if len(skipped) > 5 else ""), file=sys.stderr)
    if hits:
        print(f"Context wall: {len(hits)} hit(s) in {checked} {scope}, against {len(entries)} map entries:\n", file=sys.stderr)
        for rel, number, map_line, phrase, replacement in hits:
            shown = f' "{phrase}"' if args.show_phrases else ""
            instead = f" -> {replacement}" if replacement else ""
            print(f"  - {rel}:{number}: map line {map_line}{shown}{instead}", file=sys.stderr)
        print("\nNeutralize each line by hand (or retag the file origin: instance if it should not travel).", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"Context wall: {checked} {scope} checked against {len(entries)} map entries, no hits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
