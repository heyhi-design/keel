#!/usr/bin/env python3
# origin: keel
"""
Start-load check: how many tokens your agent reads before the first useful action.

The scaffold keeps a short list of files that load at the start of every session (the
always-loaded core named in docs/setup-guide.md, Step 2). Each one costs tokens in every
session whether or not the task needs it, so the list is worth measuring. This script reads
an instance's declared start set, estimates each file in tokens, and prints a table. It is
report-first: by default it measures and prints and exits 0, and it only fails the run when
you ask it to (`--strict`).

What counts as the start set, in order of precedence:

  1. `--start-set FILE`, a YAML file you point at.
  2. `os/start-set.yaml` in the instance root, if you have written one.
  3. The documented start sequence (`AGENTS.md`, At session start), by filled name:
       - your runtime context file (`CLAUDE.md`, else `AGENTS.md`) and every file it pulls in
         with an `@path` import, followed the way the runtime follows them (relative to the
         importing file, recursively, each file once). A thin `CLAUDE.md` that imports
         `AGENTS.md` therefore counts both;
       - `os/session-start.md`, the start sequence itself;
       - `os/agent-context.md`, `os/operating-principles.md`, and
         `os/corrections/corrections-registry.yaml`;
       - your operator profile, the one `os/operators/<id>.md` whose `git_emails` matches
         `git config user.email` (os/resolve_operator.py decides, or `--operator ID`);
       - the newest entry of that operator's handoff file, `os/handoff/<id>.md`, and only
         that entry, since a session reads no further (os/handoff_rotate.py parses it).
     A file that has not been filled in yet falls back to its `.template` counterpart and is
     labelled so, so the check also runs on a fresh copy of this repository: with no operator
     profile yet the profile template stands in, and with no handoff file yet the handoff
     template's example entry does. When profiles exist but none (or more than one) matches,
     the largest active profile and its handoff stand in, labelled ESTIMATE, so the number is
     never understated by a missing identity. An import that points outside the instance
     root (a personal file in your home directory, say) is listed as OUTSIDE and not read:
     the check cannot see that part of the load, so `--strict` treats it like a missing file.
     A row the start sequence itself skips (no profile and no template; no handoff yet) is
     listed as SKIPPED at zero tokens.

A declaration replaces the whole default, imports and operator rows included: it lists exact
files, and each is measured whole. A declaration file looks like this (paths are relative to
the instance root):

    start_set:
      - CLAUDE.md
      - os/agent-context.md
      - os/operating-principles.md
      - os/corrections/corrections-registry.yaml
    budget_tokens: <N>          # optional; a number you choose, never a shipped default

A corrections registry in the start set (a YAML mapping with an `entries` list) is measured
over everything except its retired and superseded entries (its meta block and other keys
included), because that is what a session loads. It is measured as re-serialized YAML, so
comments are not counted. An entry with an odd status (capitalised, empty, absent) still counts: the check would
rather overstate the load than hide a cost. A registry without an entries list is measured
whole and the table says so. Nothing is ever skipped silently: a declared file that does not
exist is listed as MISSING, and a default start set with no runtime context file says so.

The budget. `--budget N` wins over `budget_tokens` in the declaration. With neither, the
check reports the table and prints "no budget declared"; it never invents a limit, because a
shipped number would be someone else's calibration. Over a budget, the default run prints a
WARNING and exits 0, and `--strict` exits 1. A budget that is present but is not a positive
integer is an error (exit 2) in either mode: a gate that reads a malformed limit as "no limit"
fails open.

The estimate. Tokens are characters divided by four, rounded down. It is a planning figure
for comparing one version of your start set against another, not a billing figure, and the
same estimator measures every file so the comparison holds.

Usage:
    python3 os/start_load_check.py                     # report on the repository root
    python3 os/start_load_check.py --root path/to/instance
    python3 os/start_load_check.py --start-set os/start-set.yaml --budget N
    python3 os/start_load_check.py --operator ada      # measure for one operator's profile and handoff
    python3 os/start_load_check.py --strict            # exit 1 over budget or on a missing file
    python3 os/start_load_check.py --json              # the same measurement, machine-readable

Exit codes: 0 report printed. 1 `--strict` and the start set is over budget or has a missing,
unreadable or outside file. 2 the declaration or the budget could not be read.

Requires PyYAML (see requirements.txt).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only when PyYAML is absent
    print("error: PyYAML is required. Install it with: python3 -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DECLARATION = Path("os") / "start-set.yaml"
CHARS_PER_TOKEN = 4
NO_BUDGET_NOTICE = "no budget declared"

# The documented always-loaded core, by filled name. The runtime context file is resolved
# separately (CLAUDE.md, else AGENTS.md, plus its imports), and the operator profile and the
# handoff entry depend on who is running the session, so none of those is listed here.
SESSION_START = "os/session-start.md"
CORE = (
    "os/agent-context.md",
    "os/operating-principles.md",
    "os/corrections/corrections-registry.yaml",
)
RUNTIME_CONTEXT_FILES = ("CLAUDE.md", "AGENTS.md")
OPERATOR_TEMPLATE = "os/operators/operator.template.md"
HANDOFF_TEMPLATE = "os/handoff.template.md"
PROBLEM_STATUSES = ("missing", "unreadable", "outside")

# An `@path` import: `@` at the start of a line or after whitespace (so an email address is
# never one), followed by a path. A token counts only if it looks like a file (it has a `.` or
# a `/`), so a prose `@mention` is left alone. Code spans and fenced blocks are skipped, as the
# runtime skips them.
_IMPORT_RE = re.compile(r"(?:^|(?<=\s))@([^\s`]+)")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_CODE_SPAN_RE = re.compile(r"`+[^`]*`+")

Item = Union[str, Dict[str, Any]]


class DeclarationError(Exception):
    """The start-set declaration or the budget is unusable (exit code 2)."""


def estimate_tokens(text: str) -> int:
    """The one estimator every row uses: characters / 4, rounded down."""
    return len(text) // CHARS_PER_TOKEN


def _template_path(path: Path) -> Path:
    """`os/agent-context.md` -> `os/agent-context.template.md` (the rename rule, reversed)."""
    return path.with_name(path.stem + ".template" + path.suffix)


def _validate_budget(value: object, source: str) -> int:
    # bool is an int subclass in Python, and NaN beats both comparisons, so type and range
    # are checked before the value is ever compared with a token count.
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DeclarationError(f"{source} must be a positive integer, got {value!r}")
    return value


def read_declaration(path: Path) -> Dict[str, Any]:
    """Read a declaration file into {'start_set': [...], 'budget_tokens': int | None}."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DeclarationError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise DeclarationError(f"{path} does not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise DeclarationError(f"{path} must be a mapping with a start_set list")
    entries = data.get("start_set")
    if not isinstance(entries, list) or not entries or not all(isinstance(e, str) and e.strip() for e in entries):
        raise DeclarationError(f"{path}: start_set must be a non-empty list of file paths")
    budget = None
    if "budget_tokens" in data:
        budget = _validate_budget(data["budget_tokens"], f"{path.name} budget_tokens")
    return {"start_set": [e.strip() for e in entries], "budget_tokens": budget}


def _load_sibling(name: str):
    """Load another os/ tool by path, so this works however the script is started."""
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"keel_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def imports_in(text: str) -> List[str]:
    """The `@path` import targets in a Markdown file, in order of appearance."""
    found: List[str] = []
    fence: Optional[str] = None
    for line in text.splitlines():
        match = _FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        for hit in _IMPORT_RE.finditer(_CODE_SPAN_RE.sub("", line)):
            token = hit.group(1).rstrip(".,;:!?)]}'\"")
            if token and ("/" in token or "." in token):
                found.append(token)
    return found


def runtime_chain(root: Path) -> List[Item]:
    """The runtime context file (CLAUDE.md, else AGENTS.md) and its imports, depth first, each once."""
    entry = next((name for name in RUNTIME_CONTEXT_FILES if _is_file(root / name)), None)
    if entry is None:
        return []
    real_root = root.resolve()
    items: List[Item] = []
    seen = set()

    def visit(path: Path, rel: str, via: Optional[str]) -> None:
        key = path.resolve()
        if key in seen:
            return
        seen.add(key)
        if via is None:
            items.append(rel)
        else:
            items.append({"path": rel, "note": f"imported by {via}"})
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return  # measure_file reports it
        for target in imports_in(text):
            if target.startswith("~"):
                items.append({"path": target, "status": "outside", "note": f"imported by {rel}; a home-directory file, not read"})
                continue
            candidate = Path(target) if Path(target).is_absolute() else path.parent / target
            try:
                inner = candidate.resolve().relative_to(real_root).as_posix()
            except ValueError:
                items.append({"path": target, "status": "outside", "note": f"imported by {rel}; outside the instance root, not read"})
                continue
            except (OSError, RuntimeError):
                items.append({"path": target, "status": "unreadable", "note": f"imported by {rel}; cannot be resolved"})
                continue
            visit(root / inner, inner, rel)

    visit(root / entry, entry, None)
    return items


def _largest(root: Path, profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    def size(profile: Dict[str, Any]) -> int:
        try:
            return len((root / profile["path"]).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            return 0
    return max(profiles, key=lambda p: (size(p), p["path"]))


def operator_rows(root: Path, operator: Optional[str] = None) -> List[Item]:
    """The operator profile row and the handoff-entry row, per the resolver's outcome."""
    resolver = _load_sibling("resolve_operator")
    handoff_row: Dict[str, Any]
    if operator is not None:
        profile = f"os/operators/{operator}.md"
        return [
            {"path": profile, "note": f"operator {operator} (from --operator)"},
            {"path": f"os/handoff/{operator}.md", "section": "newest-entry"},
        ]
    try:
        profiles = resolver.list_profiles(root)
        result = resolver.resolve(root, profiles=profiles)
    except resolver.ProfileError as exc:
        return [{"path": "os/operators/", "status": "unreadable", "note": str(exc)}]
    status = result["status"]
    if status == "matched":
        return [
            {"path": result["path"], "note": f"operator {result['operator']} (matched by git email)"},
            {"path": result["handoff"], "section": "newest-entry"},
        ]
    if status == "no-profiles":
        if _is_file(root / OPERATOR_TEMPLATE):
            profile_row = {"path": OPERATOR_TEMPLATE, "status": "template", "note": "no operator profile yet; measuring the template"}
        else:
            profile_row = {"path": "os/operators/", "status": "skipped", "note": "no operator profile: a firm of one, so the step is skipped"}
        handoff_row = {"path": HANDOFF_TEMPLATE, "section": "newest-entry", "status": "template",
                       "note": "no handoff file yet; measuring the template's example entry"}
        if not _is_file(root / HANDOFF_TEMPLATE):
            handoff_row = {"path": "os/handoff/", "status": "skipped", "note": "no operator, so no handoff entry"}
        return [profile_row, handoff_row]
    stand_in = _largest(root, [p for p in profiles if p["active"]])
    why = f"operator not resolved ({status}); the largest active profile stands in"
    return [
        {"path": stand_in["path"], "status": "estimate", "note": why},
        {"path": stand_in["handoff"], "section": "newest-entry", "status": "estimate", "note": why},
    ]


def _path_of(item: Item) -> str:
    return item if isinstance(item, str) else item["path"]


def default_start_set(root: Path, operator: Optional[str] = None) -> List[Item]:
    """The documented start sequence, in the order AGENTS.md lists it, each file once.

    A file the runtime file already imports (say `os/session-start.md`) is in context from
    then on, so its later place in the sequence does not count it a second time.
    """
    items = runtime_chain(root) + [SESSION_START] + list(CORE) + operator_rows(root, operator)
    seen = set()
    unique: List[Item] = []
    for item in items:
        key = _path_of(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _is_file(path: Path) -> bool:
    """Path.is_file(), except that an OS error (a name too long, a loop) reads as "no"."""
    try:
        return path.is_file()
    except (OSError, ValueError):
        return False


def _inside(root: Path, candidate: Path) -> bool:
    """True when candidate resolves to somewhere under root. Raises OSError/RuntimeError if it cannot resolve."""
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _is_inactive(entry: object) -> bool:
    """Only an explicit retired or superseded status takes an entry out of the load."""
    if not isinstance(entry, dict):
        return False
    status = entry.get("status")
    return isinstance(status, str) and status.strip().lower() in ("retired", "superseded")


def _measure_registry(text: str) -> Tuple[Optional[str], str]:
    """For a corrections registry, return (text a session loads, note). None if not a registry."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None, "does not parse as YAML"
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return None, ""
    loaded = [e for e in data["entries"] if not _is_inactive(e)]
    # Everything but the inactive entries: the meta block and any other keys load too.
    shown = yaml.safe_dump({**data, "entries": loaded}, sort_keys=False, allow_unicode=True)
    return shown, f"{len(loaded)} active of {len(data['entries'])} entries"


def measure_file(root: Path, item: Item) -> Dict[str, Any]:
    """One row of the table. Never raises on a bad file: the check is report-first.

    An item is a path (measured whole) or a mapping with a `path` and, optionally, a preset
    `status` and `note`, and `section: newest-entry` to measure only a handoff file's newest
    entry. A preset status of outside, skipped or unreadable is reported as is, unread.
    """
    spec: Dict[str, Any] = {"path": item} if isinstance(item, str) else dict(item)
    rel = spec["path"]
    row: Dict[str, Any] = {"path": rel, "tokens": 0, "status": spec.get("status", "ok"), "note": spec.get("note", "")}
    if row["status"] in ("outside", "skipped", "unreadable"):
        return row
    target = root / rel
    try:
        inside = _inside(root, target)
    except (OSError, RuntimeError, ValueError):
        row["status"] = "unreadable"
        row["note"] = "the path cannot be resolved"
        return row
    if not inside:
        raise DeclarationError(f"{rel} points outside the instance root")
    entry_only = spec.get("section") == "newest-entry"
    if not _is_file(target):
        template = Path(HANDOFF_TEMPLATE) if entry_only else _template_path(Path(rel))
        if not rel.endswith(".template" + Path(rel).suffix) and _is_file(root / template):
            target = root / template
            row["path"] = template.as_posix()
            if row["status"] != "estimate":
                row["status"] = "template"
            row["note"] = "; ".join(p for p in (row["note"], (
                "no handoff file yet; measuring the template's example entry" if entry_only
                else "not filled in yet; measuring the template")) if p)
        elif entry_only:
            # A first session has no handoff yet: nothing to read is a zero, not a failure.
            row["status"] = "skipped"
            row["note"] = "; ".join(p for p in (row["note"], "no handoff file yet, so nothing to read") if p)
            return row
        else:
            row["status"] = "missing"
            row["note"] = "; ".join(p for p in (row["note"], "declared but not found") if p)
            return row
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        row["status"] = "unreadable"
        row["note"] = f"{type(exc).__name__}"
        return row
    if entry_only:
        entries = _load_sibling("handoff_rotate").split_entries(text)[1]
        text = entries[0] if entries else ""
        count = f"newest entry only, 1 of {len(entries)}" if entries else "no entries yet"
        row["note"] = "; ".join(p for p in (row["note"], count) if p)
    elif target.suffix in (".yaml", ".yml"):
        shown, note = _measure_registry(text)
        if shown is not None:
            text = shown
            row["note"] = note
            row["status"] = "template" if row["status"] == "template" else "registry"
        else:
            why = note or "no entries list"
            row["note"] = "; ".join(p for p in (row["note"], f"measured whole ({why})") if p)
    row["tokens"] = estimate_tokens(text)
    return row


def measure(root: Path, start_set: List[Item]) -> Dict[str, Any]:
    rows = [measure_file(root, item) for item in start_set]
    return {
        "root": str(root),
        "rows": rows,
        "total_tokens": sum(r["tokens"] for r in rows),
        "problems": [r for r in rows if r["status"] in PROBLEM_STATUSES],
    }


def format_report(measurement: Dict[str, Any]) -> str:
    rows = measurement["rows"]
    total = measurement["total_tokens"] or 1
    width = max([len("File")] + [len(r["path"]) for r in rows])
    lines = [
        f"Start load (tokens, {CHARS_PER_TOKEN} characters each)",
        "",
        f"{'File'.ljust(width)}  {'~Tokens':>8}  {'Share':>6}  Note",
        f"{'-' * width}  {'-' * 8}  {'-' * 6}  {'-' * 4}",
    ]
    for r in rows:
        label = r["status"].upper() if r["status"] in PROBLEM_STATUSES + ("estimate", "skipped") else ""
        note = "; ".join(part for part in (label, r["note"]) if part)
        share = f"{100 * r['tokens'] / total:5.1f}%"
        lines.append(f"{r['path'].ljust(width)}  {r['tokens']:>8,}  {share:>6}  {note}".rstrip())
    lines.append(f"{'-' * width}  {'-' * 8}  {'-' * 6}")
    lines.append(f"{'Start load'.ljust(width)}  {measurement['total_tokens']:>8,}")
    return "\n".join(lines)


def verdict(measurement: Dict[str, Any], budget: Optional[int], strict: bool) -> Tuple[int, List[str]]:
    """The exit code and the lines that explain it. Report-first: only --strict can fail."""
    messages: List[str] = []
    failed = False
    for row in measurement["problems"]:
        messages.append(f"WARNING: {row['path']} is {row['status']}")
        failed = True
    if budget is None:
        messages.append(NO_BUDGET_NOTICE)
    elif measurement["total_tokens"] > budget:
        messages.append(
            f"WARNING: start load {measurement['total_tokens']:,} tokens is over the budget of {budget:,}"
        )
        failed = True
    else:
        messages.append(f"within budget: {measurement['total_tokens']:,} <= {budget:,}")
    return (1 if (failed and strict) else 0), messages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report the tokens your agent loads at session start.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="the instance root (default: this repository)")
    parser.add_argument("--start-set", type=Path, default=None, help="a declaration file (default: os/start-set.yaml, else the documented core)")
    parser.add_argument("--budget", type=int, default=None, help="token budget; overrides budget_tokens in the declaration")
    parser.add_argument("--operator", default=None, help="measure this operator's profile and handoff instead of resolving git config user.email")
    parser.add_argument("--strict", action="store_true", help="exit 1 when over budget or a declared file is missing")
    parser.add_argument("--json", action="store_true", help="print the measurement as JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    notes: List[str] = []
    try:
        if not root.is_dir():
            raise DeclarationError(f"{root} is not a directory")
        declaration = args.start_set
        if declaration is None and _is_file(root / DECLARATION):
            declaration = root / DECLARATION
        budget = None
        if declaration is not None:
            decl_path = declaration if declaration.is_absolute() else (Path.cwd() / declaration)
            if not _is_file(decl_path) and _is_file(root / declaration):
                decl_path = root / declaration
            parsed = read_declaration(decl_path)
            start_set, budget = parsed["start_set"], parsed["budget_tokens"]
        else:
            start_set = default_start_set(root, args.operator)
            if not any(name in start_set for name in RUNTIME_CONTEXT_FILES):
                notes.append("note: no CLAUDE.md or AGENTS.md at the root, so no runtime context file is counted")
        if args.budget is not None:
            budget = _validate_budget(args.budget, "--budget")
        measurement = measure(root, start_set)
    except DeclarationError as exc:
        print(f"start_load_check: {exc}", file=sys.stderr)
        return 2

    code, messages = verdict(measurement, budget, args.strict)
    messages = notes + messages
    if args.json:
        print(json.dumps(dict(measurement, budget_tokens=budget, messages=messages, exit_code=code), indent=2))
    else:
        print(format_report(measurement))
        print()
        for message in messages:
            print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
