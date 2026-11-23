#!/usr/bin/env python3
# origin: keel
"""
Handoff rotation: keep each operator's handoff file short enough to read at session start.

Each operator has a handoff file, `os/handoff/<operator-id>.md` (copied from
`os/handoff.template.md`), with one entry per closed session, newest first. The rotation rule
(`os/session-rules.md`, The Session Close Sequence, step 3): keep the newest
`operating_mode.handoff.keep_newest` entries (from `os/project-state.yaml`) and move every
older entry, unchanged and in order, to the top of the archive file the handoff names in its
`archive:` field. Move, never delete.

Report-first. By default this prints what a rotation would move and writes nothing. With
`--apply` it writes, and in the only safe order: the archive first, then a re-read of the
archive to confirm every moved entry landed in it verbatim, and only then the shortened
handoff file. If any step fails, the handoff file is left as it was. It also refuses to
rotate a file whose dated entries are out of order, because the rule keeps "the newest" by
position and a misordered file would archive the wrong ones.

An entry is a level-2 heading (`## YYYY-MM-DD · title`) and everything up to the next
level-2 heading. Headings inside fenced code blocks and inside the YAML frontmatter do not
count. Line endings are preserved as the file has them. `--apply` refuses a file holding an
undated level-2 heading (a preface section such as "How to read this file", or a sub-section
written at level 2), because counting it as an entry would break the keep-newest rule: make it
level 3, or move it into the frontmatter or the title block. A file whose frontmatter never
closes is refused, not read as empty.

Usage:
    python3 os/handoff_rotate.py                    # report for the operator git config resolves
    python3 os/handoff_rotate.py --operator ada     # report for one operator
    python3 os/handoff_rotate.py --all              # report for every handoff file
    python3 os/handoff_rotate.py --keep 3           # override keep_newest
    python3 os/handoff_rotate.py --all --apply      # rotate: archive first, then the handoff

Exit codes: 0 report printed (or rotation applied). 1 a rotation was refused or failed its
check. 2 nothing to rotate could be read: no handoff file, no keep_newest, an unresolved
operator, or a bad argument.

Requires PyYAML (see requirements.txt) to read os/project-state.yaml.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only when PyYAML is absent
    print("error: PyYAML is required. Install it with: python3 -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
HANDOFF_DIR = Path("os") / "handoff"
PROJECT_STATE = Path("os") / "project-state.yaml"

_HEADING_RE = re.compile(r"^ {0,3}##(?:[ \t]|$)")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_OPERATOR_ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")
_DATE_RE = re.compile(r"^ {0,3}##[ \t]+\[?(\d{4}-\d{2}-\d{2})\b")


class RotationError(Exception):
    """A rotation cannot run (exit code 2) or was refused (raised with refused=True, exit 1)."""

    def __init__(self, message: str, refused: bool = False):
        super().__init__(message)
        self.refused = refused


def _load_sibling(name: str):
    """Load another os/ tool by path, so this works however the script is started."""
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"keel_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _lines(text: str) -> List[str]:
    """Lines with their endings kept. Splits on \\n only, so \\r\\n and odd separators survive."""
    return re.findall(r"[^\n]*\n|[^\n]+$", text)


def split_entries(text: str) -> Tuple[str, List[str]]:
    """(preface, entries). preface + "".join(entries) == text, exactly.

    The preface is the frontmatter, the title, and anything before the first level-2
    heading. Each entry runs from its level-2 heading to the line before the next one.
    """
    lines = _lines(text)
    start = 0
    if lines and lines[0].rstrip("\r\n").strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].rstrip("\r\n").strip() == "---":
                start = i + 1
                break
        else:
            start = len(lines)  # an unclosed frontmatter: no entries can be trusted
    preface: List[str] = lines[:start]
    entries: List[List[str]] = []
    fence: Optional[str] = None
    for line in lines[start:]:
        bare = line.rstrip("\r\n")
        fence_match = _FENCE_RE.match(bare)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
        elif fence is None and _HEADING_RE.match(bare):
            entries.append([line])
            continue
        if entries:
            entries[-1].append(line)
        else:
            preface.append(line)
    return "".join(preface), ["".join(e) for e in entries]


def _unclosed_frontmatter(text: str) -> bool:
    lines = _lines(text)
    if not lines or lines[0].rstrip("\r\n").strip() != "---":
        return False
    return not any(line.rstrip("\r\n").strip() == "---" for line in lines[1:])


def newest_entry(text: str) -> Optional[str]:
    """The first (newest) entry of a handoff file, or None if it has none."""
    _, entries = split_entries(text)
    return entries[0] if entries else None


def entry_date(entry: str) -> Optional[str]:
    match = _DATE_RE.match(entry)
    return match.group(1) if match else None


def entry_title(entry: str) -> str:
    return entry.splitlines()[0].strip() if entry else ""


def order_problems(entries: List[str]) -> List[str]:
    """Places where a dated entry is newer than the one above it (the file must be newest first)."""
    problems = []
    last: Optional[str] = None
    for index, entry in enumerate(entries):
        date = entry_date(entry)
        if date is None:
            continue
        if last is not None and date > last:
            problems.append(f"entry {index + 1} ({date}) is newer than an entry above it ({last})")
        last = date if last is None or date < last else last
    return problems


def _validate_keep(value: object, source: str) -> int:
    # bool is an int subclass and NaN beats every comparison, so type and range come first.
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RotationError(f"{source} must be a positive integer, got {value!r}")
    return value


def read_keep_newest(root: Path) -> int:
    """operating_mode.handoff.keep_newest from os/project-state.yaml (or its template)."""
    path = root / PROJECT_STATE
    if not path.is_file():
        template = path.with_name("project-state.template.yaml")
        if not template.is_file():
            raise RotationError("no os/project-state.yaml to read keep_newest from; pass --keep N")
        path = template
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RotationError(f"{path.relative_to(root).as_posix()} cannot be read: {exc}") from exc
    try:
        value = data["operating_mode"]["handoff"]["keep_newest"]
    except (KeyError, TypeError):
        raise RotationError(
            f"{path.relative_to(root).as_posix()} has no operating_mode.handoff.keep_newest; pass --keep N"
        ) from None
    return _validate_keep(value, "operating_mode.handoff.keep_newest")


def _read(path: Path) -> str:
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()
    except UnicodeDecodeError:
        raise RotationError(f"{path.name} is not UTF-8 text; rotate it by hand or convert it first") from None
    except OSError as exc:
        raise RotationError(f"{path.name} cannot be read: {exc}") from None


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _newline_of(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _archive_path(root: Path, handoff: Path, preface: str) -> Path:
    """The `archive:` field of the handoff's frontmatter, else os/handoff/archive/<name>."""
    match = re.search(r"(?m)^archive:[ \t]*[\"']?([^\"'\r\n#]+?)[\"']?[ \t]*(?:#.*)?\r?$", preface)
    if match and "[" not in match.group(1):
        candidate = (root / match.group(1).strip()).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            raise RotationError(f"{handoff.name}: archive path points outside the instance root") from None
    else:
        candidate = root / HANDOFF_DIR / "archive" / handoff.name
    # The archive must be a file of its own. Pointing it at this handoff (by any spelling: a
    # case variant, a symlink) would write the moved entries and then overwrite them; pointing
    # it beside the handoff files would make it read as some operator's handoff.
    same = candidate.exists() and os.path.samefile(candidate, handoff)
    if same or os.path.normcase(str(candidate)) == os.path.normcase(str(handoff)):
        raise RotationError(f"{handoff.name}: the archive path is the handoff file itself")
    if os.path.normcase(str(candidate.parent.resolve())) == os.path.normcase(str(handoff.parent.resolve())):
        raise RotationError(
            f"{handoff.name}: the archive sits beside the handoff files, where it would read as an "
            f"operator's handoff; use os/handoff/archive/"
        )
    return candidate


def _separated(chunk: str, nl: str) -> str:
    """The chunk ending in one blank line, so the next heading never runs into it."""
    if chunk.endswith(nl + nl):
        return chunk
    if chunk.endswith(nl):
        return chunk + nl
    return chunk + nl + nl


def plan(root: Path, handoff: Path, keep: int) -> Dict[str, Any]:
    """What a rotation of one handoff file would do. Writes nothing."""
    root = root.resolve()
    shown = handoff.name
    handoff = handoff.resolve()
    try:
        handoff.relative_to(root)
    except ValueError:
        raise RotationError(f"{shown} resolves outside the instance root (a symlink?); rotate it where it lives") from None
    if not handoff.is_file():
        raise RotationError(f"{handoff.relative_to(root).as_posix()} does not exist")
    text = _read(handoff)
    if _unclosed_frontmatter(text):
        raise RotationError(f"{handoff.relative_to(root).as_posix()}: the frontmatter never closes, so no entry can be trusted")
    preface, entries = split_entries(text)
    archive = _archive_path(root, handoff, preface)
    if archive.is_dir():
        raise RotationError(f"{archive.relative_to(root).as_posix()} is a directory, not an archive file")
    return {
        "handoff": handoff.relative_to(root).as_posix(),
        "archive": archive.relative_to(root).as_posix(),
        "keep_newest": keep,
        "entries": len(entries),
        "move": [entry_title(e) for e in entries[keep:]],
        "order_problems": order_problems(entries),
        "_text": text,
        "_preface": preface,
        "_entries": entries,
        "_archive_path": archive,
    }


def apply(root: Path, planned: Dict[str, Any]) -> None:
    """Archive first, confirm, then shorten the handoff. Raises RotationError(refused=True) on any doubt."""
    if planned["order_problems"]:
        raise RotationError(
            f"{planned['handoff']}: refusing to rotate, entries are not newest first: "
            + "; ".join(planned["order_problems"]),
            refused=True,
        )
    entries: List[str] = planned["_entries"]
    keep = planned["keep_newest"]
    moved, kept = entries[keep:], entries[:keep]
    if not moved:
        return
    undated = [entry_title(e) for e in entries if entry_date(e) is None]
    if undated:
        raise RotationError(
            f"{planned['handoff']}: refusing to rotate, level-2 heading(s) with no date would count as "
            f"entries: {'; '.join(undated)} (make them level 3, or fold them into the frontmatter or title block)",
            refused=True,
        )
    root = root.resolve()
    handoff = root / planned["handoff"]
    archive: Path = planned["_archive_path"]
    existed = archive.is_file()
    nl = _newline_of(planned["_text"])

    old = ""
    if existed:
        old = _read(archive)
        archive_preface, archive_entries = split_entries(old)
    else:
        operator = handoff.stem
        archive_preface = (
            f"# Handoff archive · {operator}{nl}{nl}"
            f"*Entries rotated out of {planned['handoff']}, newest first. Moved here unchanged; "
            f"never deleted.*{nl}{nl}"
        )
        archive_entries = []
    if archive_preface and not archive_preface.endswith(nl + nl):
        archive_preface = _separated(archive_preface, nl)
    new_archive = archive_preface + "".join(_separated(e, nl) for e in moved) + "".join(archive_entries)
    try:
        _write(archive, new_archive)
    except OSError as exc:
        raise RotationError(f"{planned['archive']} cannot be written ({exc}); {planned['handoff']} was left unchanged",
                            refused=True) from None

    # Confirm before removing anything: every moved entry, verbatim and in order, at the top.
    _, landed = split_entries(_read(archive))
    head = [e.rstrip("\r\n") for e in landed[: len(moved)]]
    if head != [e.rstrip("\r\n") for e in moved]:
        # Put the archive back as it was; the handoff has not been touched yet.
        if existed:
            _write(archive, old)
        else:
            archive.unlink()
        raise RotationError(
            f"{planned['archive']}: the moved entries did not read back verbatim; "
            f"{planned['handoff']} was left unchanged",
            refused=True,
        )

    new_handoff = planned["_preface"] + "".join(kept)
    _write(handoff, new_handoff)
    _, remaining = split_entries(_read(handoff))
    if [e.rstrip("\r\n") for e in remaining] != [e.rstrip("\r\n") for e in kept]:
        raise RotationError(f"{planned['handoff']}: the shortened file did not read back as written", refused=True)


def targets(root: Path, operator: Optional[str], every: bool) -> List[Path]:
    folder = root / HANDOFF_DIR
    if every:
        return sorted(p for p in folder.glob("*.md")
                      if p.is_file() and not p.name.endswith(".template.md") and p.name.lower() != "readme.md")
    if operator is None:
        resolver = _load_sibling("resolve_operator")
        try:
            result = resolver.resolve(root)
        except resolver.ProfileError as exc:
            raise RotationError(str(exc)) from exc
        if result["status"] != "matched":
            raise RotationError(f"operator not resolved ({result['status']}): {result['reason']}; pass --operator or --all")
        operator = result["operator"]
    if not _OPERATOR_ID_RE.match(operator):
        raise RotationError(f"{operator!r} is not an operator id (letters, digits, '.', '_', '-')")
    return [folder / f"{operator}.md"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rotate handoff files: keep the newest N entries, archive the rest.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="the instance root (default: this repository)")
    who = parser.add_mutually_exclusive_group()
    who.add_argument("--operator", default=None, help="the operator id whose handoff to rotate")
    who.add_argument("--all", action="store_true", help="every handoff file in os/handoff/")
    parser.add_argument("--keep", type=int, default=None, help="entries to keep (default: operating_mode.handoff.keep_newest)")
    parser.add_argument("--apply", action="store_true", help="write the rotation (default: report only)")
    parser.add_argument("--json", action="store_true", help="print the plan as JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if not root.is_dir():
            raise RotationError(f"{root} is not a directory")
        keep = _validate_keep(args.keep, "--keep") if args.keep is not None else read_keep_newest(root)
        files = targets(root, args.operator, args.all)
        if not files:
            raise RotationError("no handoff files in os/handoff/")
        plans = [plan(root, f, keep) for f in files]
    except RotationError as exc:
        print(f"handoff_rotate: {exc}", file=sys.stderr)
        return 2

    code = 0
    report = []
    for planned in plans:
        status = "nothing to move"
        if planned["move"]:
            status = "would move" if not args.apply else "moved"
            if args.apply:
                try:
                    apply(root, planned)
                except RotationError as exc:
                    print(f"handoff_rotate: {exc}", file=sys.stderr)
                    status = "refused"
                    code = 1
        public = {k: v for k, v in planned.items() if not k.startswith("_")}
        public["status"] = status
        report.append(public)

    if args.json:
        print(json.dumps(report, indent=2))
        return code
    for item in report:
        print(f"{item['handoff']}: {item['entries']} entries, keep {item['keep_newest']}: {item['status']}")
        for title in item["move"]:
            print(f"  -> {item['archive']}: {title}")
        for problem in item["order_problems"]:
            print(f"  WARNING: {problem}")
    if not args.apply and any(item["move"] for item in report):
        print("\nReport only. Run again with --apply to move these entries (archive first, then the handoff).")
    return code


if __name__ == "__main__":
    sys.exit(main())
