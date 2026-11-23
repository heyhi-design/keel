#!/usr/bin/env python3
# origin: keel
"""
Worktree report: every worktree, its branch, whether it is merged and clean, and how old it is.

Parallel sessions each get their own worktree (`docs/operating-with-more-than-one.md`,
Parallel sessions and worktrees), and worktrees are not self-cleaning: merged ones pile up
beside the few that still hold work. This report lists them all and names the reapable set,
the worktrees that are safe to remove: merged into the default branch and clean.

It removes nothing, ever. There is no flag that makes it remove anything; removing a
worktree stays a decision you make and a command you type.

How each column is decided:

  merged   the worktree's commit is already in the default branch, by one of three checks
           in order: it is an ancestor (a normal merge); every commit it adds has an
           equivalent patch upstream (`git cherry`: a rebase or a one-commit squash); or
           every file it changed reads the same in the default branch as at its tip (a
           many-commit squash). Anything else is "no". A branch whose work was merged and
           then edited again on the default branch reads "no", which is the safe direction.
  dirty    `git status --porcelain` in that worktree prints anything, untracked files included,
           whatever the user's own config hides (untracked files, submodule changes).
  hidden   files git status cannot show you: marked skip-worktree or assume-unchanged
           (`git ls-files -v`). A worktree holding any is never reapable.
  ignored  how many gitignored paths it holds (`git status --porcelain --ignored`).
  age      days since the worktree's last commit, and minutes since its index last changed (a
           rough sign of a live session).
  in use   an `index.lock` is present: a git command is running there right now.

Reapable = merged, clean, holding no gitignored files and no hidden files, not the main
worktree, not locked, not in use, its directory exists, not a detached commit that no branch,
remote branch or tag holds, and not a worktree a live session may be in (the one you ran
this from, the one `--root` names, and the one this script sits in). A merged, clean worktree
that holds gitignored files is listed separately: `git worktree remove` deletes those files
without asking, so look at them first. Missing directories are listed separately as
stale entries (`git worktree prune` clears them; this report does not).

The default branch is `origin/HEAD` if the remote has one, else `origin/main`, else
`origin/master`, else the local `main` or `master`; `--base REF` overrides. The answer is only
as current as your last fetch: run with `--fetch` or fetch yourself. `--fetch` runs
`git fetch --quiet` first, with automatic gc turned off for that call; it writes remote-tracking
refs and git's record of the last fetch, the only writes this script ever causes.

Usage:
    python3 os/worktree_report.py
    python3 os/worktree_report.py --fetch
    python3 os/worktree_report.py --base origin/main --json

Exit codes: 0 report printed. 2 not a git repository, or the base ref does not exist.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


class ReportError(Exception):
    """The report cannot run (exit code 2)."""


def _env():
    """The environment for every git call, read at call time.

    GIT_OPTIONAL_LOCKS=0 stops `git status` from refreshing the index, which is a write and
    would take the lock a live session in that worktree may need.
    """
    return dict(os.environ, GIT_OPTIONAL_LOCKS="0")


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8", errors="surrogateescape", check=False, env=_env())


def _ok(cwd: Path, *args: str) -> Optional[str]:
    out = _git(cwd, *args)
    return out.stdout.strip() if out.returncode == 0 else None


def default_branch(root: Path) -> Optional[str]:
    """The ref this instance merges into, preferring the remote's view over the local copy."""
    head = _ok(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head:
        return head
    for ref in ("refs/remotes/origin/main", "refs/remotes/origin/master", "refs/heads/main", "refs/heads/master"):
        if _ok(root, "rev-parse", "--verify", "--quiet", ref + "^{commit}"):
            return ref
    return None


def list_worktrees(root: Path) -> List[Dict[str, Any]]:
    """`git worktree list --porcelain`, parsed. The first entry is the main worktree."""
    out = _git(root, "worktree", "list", "--porcelain")
    if out.returncode != 0:
        raise ReportError(f"not a git repository: {root}")
    worktrees: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in out.stdout.splitlines() + [""]:
        if not line:
            if current:
                worktrees.append(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {"path": value, "head": None, "branch": None, "bare": False,
                       "detached": False, "locked": False, "prunable": False}
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = value
        elif key in ("bare", "detached", "locked", "prunable"):
            current[key] = True
    for index, wt in enumerate(worktrees):
        wt["main"] = index == 0
    return worktrees


def merged_state(root: Path, commit: str, base: str) -> str:
    """'ancestor' | 'patches upstream' | 'content in base' | 'no'."""
    if _git(root, "merge-base", "--is-ancestor", commit, base).returncode == 0:
        return "ancestor"
    cherry = _git(root, "cherry", base, commit)
    lines = [ln for ln in cherry.stdout.splitlines() if ln.strip()]
    if cherry.returncode == 0 and lines and all(ln.startswith("-") for ln in lines):
        return "patches upstream"
    # A many-commit branch squashed into one commit: every file the branch changed already
    # reads, in the base, exactly as it does at the branch tip. Read-only (two diffs).
    fork = _ok(root, "merge-base", base, commit)
    if not fork:
        return "no"
    changed = _git(root, "diff", "--name-only", "--no-renames", "-z", fork, commit)
    if changed.returncode != 0:
        return "no"
    files = [f for f in changed.stdout.split("\0") if f]
    for start in range(0, len(files), 200):  # chunked, to stay under command-line limits
        same = _git(root, "diff", "--quiet", "--no-renames", base, commit, "--", *files[start:start + 200])
        if same.returncode != 0:
            return "no"
    return "content in base"


def _git_dir(path: Path) -> Optional[Path]:
    value = _ok(path, "rev-parse", "--absolute-git-dir")
    return Path(value) if value else None


def inspect_worktree(root: Path, wt: Dict[str, Any], base: str, protected: Set[Path], now: float) -> Dict[str, Any]:
    path = Path(wt["path"])
    row: Dict[str, Any] = {
        "path": wt["path"],
        "branch": wt["branch"][len("refs/heads/"):] if wt["branch"] else None,
        "head": wt["head"],
        "main": wt["main"],
        "this": path.resolve() in protected,
        "locked": wt["locked"],
        "missing": wt["prunable"] or not path.is_dir(),
        "merged": None,
        "dirty": None,
        "ignored": None,
        "hidden": None,
        "in_use": False,
        "commit_age_days": None,
        "index_age_minutes": None,
        "reapable": False,
        "why_not": [],
    }
    if row["missing"]:
        row["why_not"].append("directory missing (stale entry)")
        return row
    if wt["bare"] or not wt["head"]:
        row["why_not"].append("bare or no commit")
        return row
    row["merged"] = merged_state(root, wt["head"], base)
    # --ignored as well: `git worktree remove` deletes gitignored files without asking, and a
    # gitignored folder is exactly where content that must not be committed tends to live.
    # The flags override the user's own config: `status.showUntrackedFiles=no` or a
    # `submodule.*.ignore` setting would otherwise hide work `git worktree remove` deletes.
    status = _git(path, "status", "--porcelain", "--ignored", "--untracked-files=normal",
                  "--ignore-submodules=none")
    lines = [ln for ln in status.stdout.splitlines() if ln.strip()]
    row["dirty"] = status.returncode != 0 or any(not ln.startswith("!! ") for ln in lines)
    row["ignored"] = sorted(ln[3:] for ln in lines if ln.startswith("!! "))
    # skip-worktree (S) and assume-unchanged (a lowercase tag) hide local edits from status.
    tags = _git(path, "ls-files", "-v")
    row["hidden"] = sorted(
        ln[2:] for ln in tags.stdout.splitlines()
        if len(ln) > 2 and (ln[0] == "S" or ln[0].islower())
    ) if tags.returncode == 0 else None
    stamp = _ok(root, "log", "-1", "--format=%ct", wt["head"])
    if stamp and stamp.isdigit():
        row["commit_age_days"] = round((now - int(stamp)) / 86400, 1)
    git_dir = _git_dir(path)
    if git_dir is not None:
        row["in_use"] = (git_dir / "index.lock").exists()
        index = git_dir / "index"
        if index.exists():
            row["index_age_minutes"] = round((now - index.stat().st_mtime) / 60)

    if row["main"]:
        row["why_not"].append("the main worktree")
    if row["this"]:
        row["why_not"].append("the worktree this report runs from or reports on")
    if row["locked"]:
        row["why_not"].append("locked")
    if row["in_use"]:
        row["why_not"].append("in use (index.lock)")
    if row["merged"] == "no":
        row["why_not"].append("not merged")
    if row["dirty"]:
        row["why_not"].append("uncommitted changes")
    if row["hidden"] is None:
        row["why_not"].append("could not list skip-worktree or assume-unchanged files")
    elif row["hidden"]:
        row["why_not"].append(f"{len(row['hidden'])} file(s) marked skip-worktree or assume-unchanged")
    if not wt["branch"] and row["merged"] != "ancestor":
        holders = _ok(root, "for-each-ref", "--contains", wt["head"], "--format=%(refname)",
                      "refs/heads", "refs/remotes", "refs/tags")
        if not holders:
            row["why_not"].append("a detached commit no branch or tag holds")
    row["reapable"] = not row["why_not"] and not row["ignored"]
    if not row["why_not"] and row["ignored"]:
        row["why_not"].append(f"holds {len(row['ignored'])} gitignored path(s); look before removing")
    return row


def _toplevel(path: Path) -> Optional[Path]:
    top = _ok(path if path.is_dir() else path.parent, "rev-parse", "--show-toplevel")
    return Path(top).resolve() if top else None


def protected_worktrees(root: Path) -> Set[Path]:
    """The worktrees a live session may be in: where you ran this, the one --root names, and the
    one this script sits in. Guarding only the current directory is a known trap."""
    found = {_toplevel(Path.cwd()), _toplevel(root), _toplevel(Path(__file__).resolve())}
    return {p for p in found if p is not None}


def report(root: Path, base: Optional[str] = None, here: Optional[Path] = None) -> Dict[str, Any]:
    root = root.resolve()
    if _ok(root, "rev-parse", "--git-dir") is None:
        raise ReportError(f"not a git repository: {root}")
    base = base or default_branch(root)
    if base is None:
        raise ReportError("no default branch found (no origin/HEAD, origin/main, main or master); pass --base REF")
    if _ok(root, "rev-parse", "--verify", "--quiet", base + "^{commit}") is None:
        raise ReportError(f"base ref {base!r} does not exist")
    protected = protected_worktrees(root)
    if here is not None:
        protected.add(here.resolve())
    now = time.time()
    worktrees = list_worktrees(root)
    # Each probe is a few git subprocesses, so they run side by side; map() keeps the order.
    with ThreadPoolExecutor(max_workers=max(1, min(8, len(worktrees)))) as pool:
        rows = list(pool.map(lambda wt: inspect_worktree(root, wt, base, protected, now), worktrees))
    return {
        "base": base,
        "worktrees": rows,
        "reapable": [r["path"] for r in rows if r["reapable"]],
        "look_first": [r["path"] for r in rows if not r["reapable"] and r["ignored"] and len(r["why_not"]) == 1],
        "stale": [r["path"] for r in rows if r["missing"]],
    }


def format_report(data: Dict[str, Any]) -> str:
    rows = data["worktrees"]
    lines = [f"Worktrees against {data['base']} ({len(rows)} total)", ""]
    header = ("Branch", "Merged", "Dirty", "Ignored", "Commit age", "Index age", "Path")
    table = [header]
    for r in rows:
        branch = r["branch"] or ("(detached)" if r["head"] else "-")
        if r["main"]:
            branch += " [main]"
        if r["this"]:
            branch += " [this]"
        table.append((
            branch,
            "-" if r["merged"] is None else r["merged"],
            "-" if r["dirty"] is None else ("yes" if r["dirty"] else "no"),
            "-" if r["ignored"] is None else str(len(r["ignored"])),
            "-" if r["commit_age_days"] is None else f"{r['commit_age_days']}d",
            "-" if r["index_age_minutes"] is None else f"{r['index_age_minutes']}m",
            r["path"],
        ))
    widths = [max(len(str(row[i])) for row in table) for i in range(len(header) - 1)]
    for row in table:
        cells = [str(row[i]).ljust(widths[i]) for i in range(len(widths))] + [str(row[-1])]
        lines.append("  ".join(cells))
    lines.append("")
    if data["reapable"]:
        lines.append(f"Reapable (merged and clean): {len(data['reapable'])}")
        lines.extend(f"  {path}" for path in data["reapable"])
    else:
        lines.append("Reapable (merged and clean): none")
    if data["look_first"]:
        lines.append(f"Merged and clean, but holding gitignored files (look first): {len(data['look_first'])}")
        for row in rows:
            if row["path"] in data["look_first"]:
                sample = ", ".join(row["ignored"][:3]) + (", ..." if len(row["ignored"]) > 3 else "")
                lines.append(f"  {row['path']}  ({sample})")
    if data["stale"]:
        lines.append(f"Stale entries (directory missing): {len(data['stale'])}")
        lines.extend(f"  {path}" for path in data["stale"])
    lines.append("")
    lines.append("This report removes nothing. Check a worktree yourself before you remove it.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report worktrees and the reapable set. Removes nothing.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="any checkout of the instance (default: this repository)")
    parser.add_argument("--base", default=None, help="the default branch to compare against (default: origin/HEAD, then origin/main, ...)")
    parser.add_argument("--fetch", action="store_true", help="run `git fetch --quiet` first, so merged state is current")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if args.fetch:
        fetched = _git(root, "-c", "gc.auto=0", "-c", "maintenance.auto=false", "fetch", "--quiet")
        if fetched.returncode != 0:
            print(f"worktree_report: fetch failed, reporting against the refs you have: {fetched.stderr.strip()}", file=sys.stderr)
    try:
        data = report(root, args.base)
    except ReportError as exc:
        print(f"worktree_report: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(format_report(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
