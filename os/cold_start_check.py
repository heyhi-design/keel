#!/usr/bin/env python3
# origin: keel
"""
Cold-start check: does a fresh clone of this instance get through the start sequence?

An instance that has only ever run on its founder's machine carries assumptions nobody can
see from that machine: a file that is gitignored or never committed, an absolute path, a
directory prefix that only exists in one checkout, a script that leans on git state a fresh
clone does not have. `SETUP.md` (Before you join: the cold-start test) asks whoever hands an
instance over to clone it fresh and walk the start sequence. This script runs the mechanical
half of that test.

What it does:
  1. Clones the repository into a new temporary directory (`git clone --no-local`, nothing
     else touched), from this checkout's current branch, or from `--source` and `--branch`.
     Uncommitted changes are not in the clone; that is the point. A clone of your own checkout
     still carries commits you have not pushed, so the report notes them (and a branch with no
     upstream); `--source <remote url>` tests exactly what a new person would get.
  2. Runs these checks against the clone, each reported pass, warn, fail or skip:
       runtime-file  a root instruction file (AGENTS.md or CLAUDE.md) exists
       imports       every `@path` import in it resolves inside the clone
       start-paths   every path the start files name (the root instruction file, its imports,
                     os/session-start.md) exists in the clone. A miss is classified:
                     absolute or home-directory path; only on this machine (it exists in your
                     checkout, not in the clone: gitignored or uncommitted); a prefix break (it
                     resolves only with leading directories removed); or missing. A path whose
                     filled file is absent but whose `.template` is present is a warning: the
                     file was never filled in.
       git-state     no start file and no tracked script relies on a ref a fresh clone lacks
                     (the refs a merge, rebase, fetch or stash leaves behind in one checkout;
                     FRESH_CLONE_LACKS below lists them). A line that names one on purpose can
                     carry the marker `cold-start: ignore`.
       operators     every profile reads, no git email belongs to two active profiles
       handoffs      every active operator has a handoff file (a warning when not: their first
                     session starts with nothing to pick up)
  3. Removes the temporary clone (its own directory, nothing else), unless `--keep`.

Report-first: it exits 0 whatever it finds, unless `--strict`, which exits 1 on any fail. It
never writes to your checkout.

Usage:
    python3 os/cold_start_check.py
    python3 os/cold_start_check.py --source https://example.com/your/instance.git --branch main
    python3 os/cold_start_check.py --keep --json
    python3 os/cold_start_check.py --strict

Exit codes: 0 report printed. 1 `--strict` and a check failed. 2 the clone could not be made.

Requires PyYAML (see requirements.txt).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
SESSION_START = "os/session-start.md"
PATH_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".sh", ".toml", ".txt", ".cfg", ".ini", ".js", ".ts", ".csv", ".html"}
SCRIPT_SUFFIXES = {".py", ".sh", ".bash", ".ps1"}
IGNORE_MARKER = "cold-start: ignore"
# Refs that exist only after a merge, rebase, fetch or stash in one particular checkout.
FRESH_CLONE_LACKS = ("ORIG_HEAD", "FETCH_HEAD", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "REBASE_HEAD", "AUTO_MERGE", "refs/stash", "stash@{")  # cold-start: ignore
_GIT_STATE_RE = re.compile(r"(?<![A-Za-z_])(" + "|".join(re.escape(r) for r in FRESH_CLONE_LACKS) + r")")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_CODE_RE = re.compile(r"`([^`\n]+)`")
_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?\s*\)")


def _env():
    """The environment for every git call, read at call time."""
    return dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")


class CloneError(Exception):
    """The fresh clone could not be made (exit code 2)."""


def _load_sibling(name: str):
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"keel_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8", errors="surrogateescape", check=False, env=_env())


def _ok(cwd: Path, *args: str) -> Optional[str]:
    out = _git(cwd, *args)
    return out.stdout.strip() if out.returncode == 0 else None


def _remove_tree(path: Path) -> None:
    """Remove the temporary clone. Git marks pack files read-only, which Windows refuses to delete."""
    def force(func, target, _info):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=force)
    else:
        shutil.rmtree(path, onerror=force)


def make_clone(root: Path, source: Optional[str], branch: Optional[str], into: Path) -> Dict[str, Any]:
    """Clone into `into`/clone. Returns where the instance sits inside it and what was cloned."""
    top = _ok(root, "rev-parse", "--show-toplevel")
    if top is None and source is None:
        raise CloneError(f"not a git repository: {root}")
    prefix = (_ok(root, "rev-parse", "--show-prefix") or "") if top else ""
    notes: List[str] = []
    if branch is None and source is None:
        branch = _ok(root, "symbolic-ref", "--quiet", "--short", "HEAD")
        if branch is None:
            notes.append("HEAD is detached here, so the clone checks out the commit this checkout's HEAD points at")
    if source is None:
        if _ok(root, "status", "--porcelain"):
            notes.append("this checkout has uncommitted changes; they are not in the clone")
        # A clone of this checkout still has commits nobody else can fetch. Say so, since a new
        # person clones the remote, not your disk.
        upstream = _ok(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{u}}") if branch else None
        if branch and upstream is None:
            notes.append(f"{branch} has no upstream: a new person cloning the remote would not get it; "
                         "rerun with --source <remote url> to test what they would get")
        elif upstream:
            ahead = _ok(root, "rev-list", "--count", f"{upstream}..{branch}")
            if ahead and ahead != "0":
                notes.append(f"{ahead} commit(s) here are not on {upstream}; the clone has them, a new "
                             "person's would not (push, or rerun with --source <remote url>)")
    target = into / "clone"
    # --no-local: copy objects rather than hardlink them, so nothing this check later does to
    # its clone (removing read-only pack files on Windows) can touch your repository's files.
    command = ["git", "clone", "--quiet", "--no-local"] + (["--branch", branch] if branch else []) + [source or top, str(target)]
    out = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="surrogateescape", check=False, env=_env())
    if out.returncode != 0:
        raise CloneError(f"git clone failed: {out.stderr.strip() or out.stdout.strip()}")
    return {"clone": target, "instance": target / prefix, "branch": branch, "source": source or top, "notes": notes}


def _result(name: str) -> Dict[str, Any]:
    return {"check": name, "status": "pass", "details": []}


def _set(result: Dict[str, Any], status: str, detail: str) -> None:
    order = {"pass": 0, "skip": 0, "warn": 1, "fail": 2}
    if order[status] > order[result["status"]]:
        result["status"] = status
    result["details"].append(f"{status.upper()}: {detail}")


def start_files(instance: Path) -> List[str]:
    """The root instruction file, its imports, and the start sequence, as paths that exist."""
    slc = _load_sibling("start_load_check")
    files = []
    for item in slc.runtime_chain(instance):
        rel = item if isinstance(item, str) else item["path"]
        if (instance / rel).is_file():
            files.append(rel)
    for rel in (SESSION_START, "os/session-start.template.md"):
        if (instance / rel).is_file():
            files.append(rel)
            break
    return files


def path_refs(text: str) -> List[Tuple[int, str, str]]:
    """[(line, kind, path)] for backticked paths and relative link targets that look like files."""
    found = []
    fence: Optional[str] = None
    for number, line in enumerate(text.splitlines(), 1):
        # The same fence rule as the other tools: a fence closes only on a marker of the same
        # character at least as long as the one that opened it.
        match = _FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is not None or IGNORE_MARKER in line:
            continue
        for match in _CODE_RE.finditer(line):
            found.append((number, "code", match.group(1).strip()))
        for match in _LINK_RE.finditer(line):
            found.append((number, "link", match.group(1).strip()))
    out = []
    for number, kind, token in found:
        token = token.split("#", 1)[0]
        if not token or re.search(r"[\s<>\[\]{}*?|]", token) or re.match(r"^[a-z][a-z0-9+.-]*:", token, re.I) and not re.match(r"^[A-Za-z]:[\\/]", token):
            continue  # empty, a placeholder or glob, a command, or a URL scheme (a Windows drive is kept)
        bare = token[2:] if token.startswith("./") else token
        if "/" in bare or Path(bare).suffix.lower() in PATH_SUFFIXES:
            out.append((number, kind, token))
    return out


def _is_absolute(token: str) -> bool:
    return token.startswith(("/", "~", "\\")) or bool(re.match(r"^[A-Za-z]:[\\/]", token))


def _template_of(rel: str) -> str:
    path = Path(rel)
    return path.with_name(path.stem + ".template" + path.suffix).as_posix()


def classify(token: str, kind: str, file_rel: str, instance: Path, source_root: Path) -> Tuple[str, str]:
    """(status, reason) for one referenced path."""
    if _is_absolute(token):
        return "fail", "an absolute or home-directory path: a clone on another machine cannot have it"
    here = Path(file_rel).parent
    candidates = [(here / token).as_posix()] if kind == "link" else [Path(token).as_posix(), (here / token).as_posix()]
    candidates = [os.path.normpath(c).replace("\\", "/") for c in candidates]
    for rel in candidates:
        if rel.startswith("../"):
            continue
        if (instance / rel).exists():
            return "pass", ""
    # Machine-only first: a filled file that is gitignored hides behind its committed template
    # otherwise, and reads as "not filled in yet" when it is really "only on this machine".
    for rel in candidates:
        if not rel.startswith("../") and (source_root / rel).exists():
            return "fail", "exists in your checkout but not in a fresh clone (gitignored or uncommitted)"
    for rel in candidates:
        if not rel.startswith("../") and Path(rel).suffix and (instance / _template_of(rel)).exists():
            return "warn", f"only the template ({_template_of(rel)}) exists: not filled in yet"
    parts = candidates[0].split("/")
    for cut in range(1, len(parts)):
        rest = "/".join(parts[cut:])
        if (instance / rest).exists():
            return "fail", f"a prefix break: it resolves only without the leading '{'/'.join(parts[:cut])}/'"
    if any(c.startswith("../") for c in candidates):
        return "fail", "points outside the instance"
    return "fail", "missing from a fresh clone"


def check_runtime(instance: Path) -> Dict[str, Any]:
    result = _result("runtime-file")
    present = [name for name in ("AGENTS.md", "CLAUDE.md") if (instance / name).is_file()]
    if present:
        _set(result, "pass", ", ".join(present))
    else:
        _set(result, "fail", "no AGENTS.md or CLAUDE.md at the instance root")
    return result


def check_imports(instance: Path) -> Dict[str, Any]:
    result = _result("imports")
    slc = _load_sibling("start_load_check")
    chain = slc.runtime_chain(instance)
    imported = [i for i in chain if not isinstance(i, str)]
    if not imported:
        _set(result, "skip", "the root instruction file imports nothing")
        return result
    for item in imported:
        status = item.get("status")
        if status in ("outside", "unreadable"):
            _set(result, "fail", f"{item['path']}: {item['note']}")
        elif not (instance / item["path"]).is_file():
            _set(result, "fail", f"{item['path']}: {item['note']}; missing from a fresh clone")
        else:
            _set(result, "pass", f"{item['path']} ({item['note']})")
    return result


def check_paths(instance: Path, source_root: Path, files: List[str]) -> Dict[str, Any]:
    result = _result("start-paths")
    if not files:
        _set(result, "skip", "no start files to read")
        return result
    seen = set()
    for rel in files:
        text = (instance / rel).read_text(encoding="utf-8", errors="replace")
        for number, kind, token in path_refs(text):
            key = (rel, kind, token)
            if key in seen:
                continue
            seen.add(key)
            status, reason = classify(token, kind, rel, instance, source_root)
            if status != "pass":
                _set(result, status, f"{rel}:{number}: {token}: {reason}")
    if not result["details"]:
        _set(result, "pass", f"every path named in {', '.join(files)} exists in the clone")
    return result


def check_git_state(instance: Path, files: List[str]) -> Dict[str, Any]:
    result = _result("git-state")
    listed = _git(instance, "ls-files", "-z")
    scripts = [p for p in listed.stdout.split("\0") if p and Path(p).suffix in SCRIPT_SUFFIXES]
    for rel in sorted(set(files) | set(scripts)):
        try:
            text = (instance / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if IGNORE_MARKER in line:
                continue
            for match in _GIT_STATE_RE.finditer(line):
                _set(result, "fail", f"{rel}:{number}: uses {match.group(1)}, which a fresh clone does not have")
    if not result["details"]:
        _set(result, "pass", f"no start file or tracked script ({len(scripts)} scanned) relies on {', '.join(FRESH_CLONE_LACKS[:3])} or the like")
    return result


def check_operators(instance: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    operators, handoffs = _result("operators"), _result("handoffs")
    resolver = _load_sibling("resolve_operator")
    try:
        profiles = resolver.list_profiles(instance)
    except resolver.ProfileError as exc:
        _set(operators, "fail", str(exc))
        _set(handoffs, "skip", "the profiles cannot be read")
        return operators, handoffs
    active = [p for p in profiles if p["active"]]
    if not active:
        _set(operators, "skip", "no operator profile yet (a firm of one): the start step is skipped")
        _set(handoffs, "skip", "no operators")
        return operators, handoffs
    owners: Dict[str, List[str]] = {}
    for profile in active:
        for email in profile["git_emails"]:
            owners.setdefault(email.strip().lower(), []).append(profile["path"])
        for warning in profile["warnings"]:
            _set(operators, "warn", warning)
    for email, paths in sorted(owners.items()):
        if len(paths) > 1:
            _set(operators, "fail", f"one git email is listed by {len(paths)} active profiles ({', '.join(paths)}); a session with it cannot resolve")
    if operators["status"] == "pass":
        _set(operators, "pass", f"{len(active)} active profile(s), every git email in exactly one")
    for profile in active:
        handoff = instance / profile["handoff"]
        if handoff.is_file():
            _set(handoffs, "pass", profile["handoff"])
        else:
            _set(handoffs, "warn", f"{profile['handoff']} does not exist: {profile['operator']}'s first session has nothing to pick up")
    return operators, handoffs


def run_checks(instance: Path, source_root: Path) -> List[Dict[str, Any]]:
    files = start_files(instance)
    operators, handoffs = check_operators(instance)
    checks = [
        check_runtime(instance),
        check_imports(instance),
        check_paths(instance, source_root, files),
        check_git_state(instance, files),
        operators,
        handoffs,
    ]
    for check in checks:  # a check that only skipped says so, rather than claiming a pass
        if check["status"] == "pass" and check["details"] and all(d.startswith("SKIP") for d in check["details"]):
            check["status"] = "skip"
    return checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clone this instance fresh into a temp directory and check its start sequence.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="the instance root (default: this repository)")
    parser.add_argument("--source", default=None, help="clone from this URL or path instead of this checkout")
    parser.add_argument("--branch", default=None, help="the branch to clone (default: the one checked out here)")
    parser.add_argument("--keep", action="store_true", help="keep the temporary clone and print where it is")
    parser.add_argument("--strict", action="store_true", help="exit 1 when any check fails")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    workdir = Path(tempfile.mkdtemp(prefix="keel-cold-start-"))
    try:
        try:
            cloned = make_clone(root, args.source, args.branch, workdir)
        except CloneError as exc:
            print(f"cold_start_check: {exc}", file=sys.stderr)
            return 2
        checks = run_checks(cloned["instance"], root)
        failed = any(c["status"] == "fail" for c in checks)
        code = 1 if (failed and args.strict) else 0
        if args.json:
            print(json.dumps({
                "source": cloned["source"], "branch": cloned["branch"], "notes": cloned["notes"],
                "clone": str(cloned["clone"]) if args.keep else None, "checks": checks, "exit_code": code,
            }, indent=2))
        else:
            print(f"Cold start: cloned {cloned['branch'] or 'the default branch'} of {cloned['source']}")
            for note in cloned["notes"]:
                print(f"note: {note}")
            print()
            for check in checks:
                print(f"{check['status'].upper():5} {check['check']}")
                for detail in check["details"]:
                    if not detail.startswith("PASS: ") or check["status"] == "pass":
                        print(f"      {detail}")
            print()
            print("FAILED: fix these in the shared files, commit, and run again." if failed else
                  "Passed: a fresh clone gets through the start sequence (warnings are for you to judge).")
            if args.keep:
                print(f"clone kept at: {cloned['clone']}")
        return code
    finally:
        if not args.keep:
            _remove_tree(workdir)


if __name__ == "__main__":
    sys.exit(main())
