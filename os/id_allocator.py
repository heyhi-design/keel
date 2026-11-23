#!/usr/bin/env python3
# origin: keel
"""
Id allocator: the next free id for a registry, counted across every branch, not just yours.

Any record with sequential ids (corrections, decisions, plan items, ledger rows) collides
when two parallel sessions each take "the next free id" from their own branch: both see the
same highest id, both add one, and the merge carries two records with one id. The fix is to
count before the sessions start, on the default branch and on every open branch, and hand
each session its own block (`docs/operating-with-more-than-one.md`, Assign ids up front).
This script does the counting.

What it reads, for the files you name:
  - the file as committed on every local branch and every remote-tracking branch
    (`git for-each-ref refs/heads refs/remotes`);
  - the file on disk in every worktree of the repository, uncommitted edits included, since
    a parallel session usually takes its ids before it commits them (`--refs-only` skips this).

An id is the prefix, the separator, and a number: `--prefix KS` finds `KS-1`, `KS-06`,
`KS-112`. Every occurrence counts, not only `id:` lines, so an id that is only referenced
(a `supersedes:` pointer, a pre-assigned block written in a plan) is never handed out again.
A written range counts every id in it: `KS-06 to KS-11`, `KS-06..KS-11` and `KS-06 – KS-11`
all take six ids. That is also how a reservation becomes visible to the next run: write the
block you handed out into a tracked file (the plan or dispatch that assigns it) and name that
file here.

The next free id is one above the highest taken anywhere; gaps are never refilled, because a
gap is usually a record that was retired, and its id still means it in the history. New ids
keep the existing zero-padding (`KS-06` stays two digits) unless `--width` says otherwise.

It counts the refs you have: a colleague's branch you have not fetched is invisible to it, so
fetch first (`--fetch` does; it writes remote-tracking refs and git's record of the last fetch, with automatic gc
off for that call). A path that matches
no file on any branch or worktree is refused (exit 2), because a typo would otherwise hand out
ids that are already taken; `--allow-empty` accepts it for a registry that does not exist yet.

It is read-only: it prints and never writes. `--reserve N` prints a block of N ids for one
lane; repeat it for several lanes and the blocks come out consecutive and disjoint.

Usage:
    python3 os/id_allocator.py --prefix C os/corrections/corrections-registry.yaml
    python3 os/id_allocator.py --prefix D os/decision-log.md --reserve 3 --reserve 3
    python3 os/id_allocator.py --prefix KS 'plans/*.md' docs/ledger.md --json

A path may be a file, a directory ending in `/` (everything under it), or a glob (`*`, `?`).

Exit codes: 0 report printed. 2 not a git repository, a path that matches nothing, or a bad
argument.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
MAX_RANGE = 200  # a written range wider than this is read as two ids, not expanded (a typo guard)


def _env():
    """The environment for every git call, read at call time."""
    return dict(os.environ, GIT_OPTIONAL_LOCKS="0")


class AllocatorError(Exception):
    """The allocator cannot run (exit code 2)."""


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="surrogateescape", check=False, env=_env())


def id_patterns(prefix: str, sep: str) -> Tuple["re.Pattern[str]", "re.Pattern[str]"]:
    """(single id, written range). Bounded so `XKS-1` and `KS-1a` are not ids."""
    one = re.escape(prefix) + re.escape(sep) + r"(\d+)"
    left, right = r"(?<![A-Za-z0-9_])", r"(?![A-Za-z0-9_])"
    single = re.compile(left + one + right)
    span = re.compile(left + one + r"\s*(?:to|through|\.\.|\u2013|\u2014)\s*" + one + right)
    return single, span


def ids_in(text: str, single: "re.Pattern[str]", span: "re.Pattern[str]") -> Dict[int, str]:
    """{number: the digits as written} for every id and every id inside a written range."""
    found: Dict[int, str] = {}
    for match in single.finditer(text):
        found.setdefault(int(match.group(1)), match.group(1))
    for match in span.finditer(text):
        low, high = int(match.group(1)), int(match.group(2))
        if 0 <= high - low <= MAX_RANGE:
            for number in range(low, high + 1):
                found.setdefault(number, "")
    return found


def normalize(pattern: str) -> str:
    pattern = pattern.replace("\\", "/")
    while pattern.startswith("./"):
        pattern = pattern[2:]
    return pattern


def _search_roots(patterns: Iterable[str]) -> List[str]:
    """The fixed leading directory of each pattern, to narrow `git ls-tree` to what can match."""
    roots = []
    for pattern in patterns:
        fixed = re.split(r"[*?\[]", pattern, maxsplit=1)[0]
        if fixed == pattern:  # no glob: a file, or a directory ending in /
            roots.append(pattern)
        elif "/" in fixed:
            roots.append(fixed.rsplit("/", 1)[0] + "/")
        else:
            return []  # a glob at the top level can match anywhere: list everything
    return sorted(set(roots))


def matches(path: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        elif any(ch in pattern for ch in "*?["):
            if fnmatch.fnmatchcase(path, pattern):
                return True
        elif path == pattern or path.startswith(pattern + "/"):  # a file, or a directory named without its /
            return True
    return False


def branch_refs(root: Path) -> List[str]:
    out = _git(root, "for-each-ref", "--format=%(refname)%00%(symref)", "refs/heads", "refs/remotes")
    if out.returncode != 0:
        raise AllocatorError(f"not a git repository: {root}")
    refs = []
    for line in out.stdout.splitlines():
        name, _, symref = line.partition("\0")
        if name and not symref:  # skip refs/remotes/origin/HEAD and other symbolic refs
            refs.append(name)
    return refs


def _blobs_on(root: Path, ref: str, patterns: List[str]) -> List[Tuple[str, str]]:
    """[(path, blob oid)] for the matching files committed on ref."""
    roots = _search_roots(patterns)
    out = _git(root, "ls-tree", "-r", "-z", "--full-tree", ref, *(["--", *roots] if roots else []))
    if out.returncode != 0:
        return []
    blobs = []
    for record in out.stdout.split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob" and matches(path, patterns):
            blobs.append((path, parts[2]))
    return blobs


def _read_blobs(root: Path, oids: List[str]) -> Dict[str, str]:
    """Blob contents by oid, in one `git cat-file --batch` call."""
    if not oids:
        return {}
    proc = subprocess.run(
        ["git", "-C", str(root), "cat-file", "--batch"],
        input=("\n".join(oids) + "\n").encode(),
        capture_output=True,
        check=False,
        env=_env(),
    )
    data, contents, pos = proc.stdout, {}, 0
    for oid in oids:
        newline = data.find(b"\n", pos)
        if newline < 0:
            break
        header = data[pos:newline].decode(errors="replace").split()
        pos = newline + 1
        if len(header) < 3 or header[1] == "missing":
            continue
        size = int(header[2])
        contents[oid] = data[pos:pos + size].decode("utf-8", errors="replace")
        pos += size + 1  # the blob, then a newline
    return contents


def worktree_paths(root: Path) -> List[Path]:
    out = _git(root, "worktree", "list", "--porcelain")
    paths = []
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree "):])
            if path.is_dir():
                paths.append(path)
    return paths


def _files_on_disk(worktree: Path, patterns: List[str]) -> List[str]:
    """Tracked and untracked (not ignored) files in a worktree that match."""
    out = _git(worktree, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if out.returncode != 0:
        return []
    return sorted({p for p in out.stdout.split("\0") if p and matches(p, patterns)})


def count(
    root: Path,
    patterns: List[str],
    prefix: str,
    sep: str = "-",
    worktrees: bool = True,
) -> Dict[str, Any]:
    """Every taken id and where it was seen. Read-only."""
    single, span = id_patterns(prefix, sep)
    # Paths are given relative to the instance root; git lists them relative to the repository
    # root. They differ only when the instance lives in a subdirectory of a larger repository.
    inside = _git(root, "rev-parse", "--show-prefix")
    if inside.returncode != 0:
        raise AllocatorError(f"not a git repository: {root}")
    given_paths = list(patterns)
    patterns = [inside.stdout.strip() + normalize(p) for p in patterns]
    taken: Dict[int, Set[str]] = {}
    digits: Dict[int, str] = {}

    def record(found: Dict[int, str], where: str) -> None:
        for number, written in found.items():
            taken.setdefault(number, set()).add(where)
            if written and len(written) > len(digits.get(number, "")):
                digits[number] = written

    refs = branch_refs(root)
    on_ref: Dict[str, List[Tuple[str, str]]] = {ref: _blobs_on(root, ref, patterns) for ref in refs}
    unique = sorted({oid for blobs in on_ref.values() for _, oid in blobs})
    contents = _read_blobs(root, unique)
    for ref, blobs in on_ref.items():
        for _, oid in blobs:
            record(ids_in(contents.get(oid, ""), single, span), ref)

    seen_paths = {path for blobs in on_ref.values() for path, _ in blobs}
    scanned_worktrees: List[str] = []
    if worktrees:
        for tree in worktree_paths(root):
            scanned_worktrees.append(str(tree))
            on_disk = _files_on_disk(tree, patterns)
            seen_paths.update(on_disk)
            for rel in on_disk:
                try:
                    text = (tree / rel).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                record(ids_in(text, single, span), f"worktree {tree}")

    files_seen = sorted({path for blobs in on_ref.values() for path, _ in blobs})
    # A path that matches nothing anywhere is almost always a typo, and a typo here would hand
    # out ids that are already taken. Name each one so the caller can refuse.
    unmatched = [given for given, pattern in zip(given_paths, patterns) if not any(matches(p, [pattern]) for p in seen_paths)]
    return {
        "unmatched": unmatched,
        "prefix": prefix,
        "sep": sep,
        "refs": refs,
        "worktrees": scanned_worktrees,
        "files": files_seen,
        "taken": {n: sorted(w) for n, w in sorted(taken.items())},
        "digits": digits,
    }


def pad_width(digits: Dict[int, str]) -> int:
    """The zero-padding in use: the longest written number that starts with 0, else none."""
    padded = [len(d) for d in digits.values() if len(d) > 1 and d.startswith("0")]
    return max(padded) if padded else 0


def fmt(prefix: str, sep: str, number: int, width: int) -> str:
    return f"{prefix}{sep}{number:0{width}d}" if width else f"{prefix}{sep}{number}"


def allocate(counted: Dict[str, Any], reserve: List[int], width: Optional[int] = None) -> Dict[str, Any]:
    taken = counted["taken"]
    highest = max(taken) if taken else 0
    width = pad_width(counted["digits"]) if width is None else width
    prefix, sep = counted["prefix"], counted["sep"]
    nxt = highest + 1
    blocks = []
    for size in reserve:
        blocks.append({"size": size, "first": fmt(prefix, sep, nxt, width), "last": fmt(prefix, sep, nxt + size - 1, width)})
        nxt += size
    return {
        "highest": fmt(prefix, sep, highest, width) if taken else None,
        "highest_seen_in": taken.get(highest, []) if taken else [],
        "next_free": fmt(prefix, sep, highest + 1, width),
        "blocks": blocks,
        "width": width,
    }


def off_default(counted: Dict[str, Any], default_ref: Optional[str]) -> List[int]:
    """Ids taken somewhere but not on the default branch: the ones a single-branch count misses."""
    if default_ref is None:
        return []
    return [n for n, where in counted["taken"].items() if default_ref not in where]


def _default_ref(root: Path) -> Optional[str]:
    head = _git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head.returncode == 0 and head.stdout.strip():
        return head.stdout.strip()
    for ref in ("refs/remotes/origin/main", "refs/remotes/origin/master", "refs/heads/main", "refs/heads/master"):
        if _git(root, "rev-parse", "--verify", "--quiet", ref).returncode == 0:
            return ref
    return None


def _runs(numbers: List[int]) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    for n in numbers:
        if runs and n == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], n)
        else:
            runs.append((n, n))
    return runs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Count ids across every branch and worktree; print the next free block.")
    parser.add_argument("paths", nargs="+", help="files, directories (ending in /) or globs that hold the ids")
    parser.add_argument("--prefix", required=True, help="the id prefix, e.g. C for C-012")
    parser.add_argument("--sep", default="-", help="the separator between prefix and number (default: -)")
    parser.add_argument("--reserve", type=int, action="append", default=[], metavar="N",
                        help="print a block of N ids for one lane; repeat for several lanes")
    parser.add_argument("--width", type=int, default=None, help="zero-pad new ids to this many digits (default: as found)")
    parser.add_argument("--refs-only", action="store_true", help="skip uncommitted files in worktrees")
    parser.add_argument("--allow-empty", action="store_true",
                        help="accept a path that matches no file anywhere (a registry that does not exist yet)")
    parser.add_argument("--fetch", action="store_true",
                        help="run `git fetch --quiet` first, so other people's branches are counted")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="any checkout of the instance (default: this repository)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if not args.prefix.strip() or any(ch.isspace() for ch in args.prefix):
        print("id_allocator: --prefix must be a non-empty word", file=sys.stderr)
        return 2
    if any(size < 1 for size in args.reserve) or (args.width is not None and args.width < 0):
        print("id_allocator: --reserve sizes must be positive and --width zero or more", file=sys.stderr)
        return 2
    if args.fetch:
        fetched = _git(root, "-c", "gc.auto=0", "-c", "maintenance.auto=false", "fetch", "--quiet")
        if fetched.returncode != 0:
            print(f"id_allocator: fetch failed, counting the refs you have: {fetched.stderr.strip()}", file=sys.stderr)
    try:
        counted = count(root, args.paths, args.prefix, args.sep, worktrees=not args.refs_only)
    except AllocatorError as exc:
        print(f"id_allocator: {exc}", file=sys.stderr)
        return 2
    if counted["unmatched"] and not args.allow_empty:
        print(f"id_allocator: no file on any branch or worktree matches: {', '.join(counted['unmatched'])}. "
              "Check the path (and quote a glob), or pass --allow-empty for a "
              "registry that does not exist yet.", file=sys.stderr)
        return 2
    result = allocate(counted, args.reserve, args.width)
    default_ref = _default_ref(root)
    elsewhere = off_default(counted, default_ref)

    if args.json:
        payload = {k: v for k, v in counted.items() if k != "digits"}
        payload["taken"] = {str(k): v for k, v in counted["taken"].items()}
        payload.update(result, default_ref=default_ref, off_default=elsewhere)
        print(json.dumps(payload, indent=2))
        return 0

    p, s, w = args.prefix, args.sep, result["width"]
    print(f"{p}{s} ids: {len(counted['taken'])} taken, across {len(counted['refs'])} branch ref(s)"
          + (f" and {len(counted['worktrees'])} worktree(s)" if counted["worktrees"] else ""))
    if result["highest"]:
        seen = result["highest_seen_in"]
        print(f"highest: {result['highest']} (seen in {seen[0]}" + (f" and {len(seen) - 1} more" if len(seen) > 1 else "") + ")")
    if elsewhere:
        spans = ", ".join(fmt(p, s, a, w) if a == b else f"{fmt(p, s, a, w)} to {fmt(p, s, b, w)}" for a, b in _runs(elsewhere))
        print(f"taken off {default_ref}: {spans}")
    print(f"next free: {result['next_free']}")
    for block in result["blocks"]:
        print(f"reserve {block['size']}: {block['first']} to {block['last']}")
    if result["blocks"]:
        print("\nWrite each block into the tracked file that assigns it, and name that file here next time,"
              "\nso the next count sees the reservation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
