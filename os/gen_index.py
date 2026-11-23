#!/usr/bin/env python3
# origin: keel
"""
Generated index: a plan or research folder's index, rebuilt from the files, never by hand.

A hand-maintained index (a README table of every plan, a triage list of every research
note) is right on the day it is written and wrong a few weeks later: new files are missing,
finished work still reads open. This script reads a folder's Markdown files and writes the
index from what they say about themselves, so the index is only ever as stale as your last
run, and `--check` makes "stale" a CI failure instead of a surprise.

What each row comes from (the file's frontmatter, falling back to the file itself):
  title    `title:`, else the first `# ` heading, else the file name
  status   the first word of `status:` (the vocabulary os/status_lint.py checks), and the
           value as written, less any trailing `# comment`
  date     `created:`, else a YYYY-MM-DD in the file name
  next     for open work, the first line under a "Next Session Prompt", "Next action" or
           "Next step" heading

Rows are grouped Open (pending, partial), Done, Archived, Other (a word your `--vocab` adds,
the same list os/status_lint.py accepts), and Off the vocabulary (a status outside it, or
none), newest first within a group. The last group is the point: it is where
rot shows up. The output carries no generation date, so regenerating an unchanged folder
gives a byte-identical file and `--check` can compare.

Report-first: it prints the index to stdout. `--write` writes it to the output file;
`--check` compares the output file with a fresh build and exits 1 if they differ.

Usage:
    python3 os/gen_index.py plans/                      # print the index
    python3 os/gen_index.py plans/ --write              # write plans/INDEX.md
    python3 os/gen_index.py research/ --out research/README.md --title "Research" --write
    python3 os/gen_index.py plans/ --check              # exit 1 if plans/INDEX.md is stale

Exit codes: 0 printed, written, or up to date. 1 `--check` and the index is stale or missing.
2 the folder does not exist, or a bad argument.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = "INDEX.md"
GROUPS = (
    ("Open", ("pending", "partial")),
    ("Done", ("done",)),
    ("Archived", ("archived",)),
)
OTHER = "Other"
OFF_VOCABULARY = "Off the vocabulary"
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_NEXT_RE = re.compile(r"^#{1,6}\s*(?:Next Session Prompt|Next action|Next step)\b", re.I)


def _load_sibling(name: str):
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"keel_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lint = _load_sibling("status_lint")


def _one_line(text: str, limit: int) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def describe(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    fields = lint.frontmatter(text) or {}
    body = text
    if fields:
        closing = [i for i, ln in enumerate(text.splitlines()) if ln.strip() in ("---", "...")][1:2]
        body = "\n".join(text.splitlines()[closing[0] + 1:]) if closing else text
    title = fields.get("title", "")
    if not title:
        heading = re.search(r"(?m)^#[ \t]+(.+?)[ \t#]*$", body)
        title = heading.group(1) if heading else path.stem
    status = fields.get("status", "")
    date = fields.get("created", "")
    if not _DATE_RE.fullmatch(date or ""):
        found = _DATE_RE.search(path.name) or _DATE_RE.search(date or "")
        date = found.group(1) if found else ""
    nxt = ""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if _NEXT_RE.match(line):
            for after in lines[i + 1:]:
                after = after.strip().lstrip("*->").strip()
                if after.startswith("#"):
                    break
                if after and not after.startswith(("|", "```", "<!--")):
                    nxt = after
                    break
            break
    return {
        "name": path.name,
        "title": _one_line(title, 90),
        "word": lint.first_word(status),
        "status": _one_line(status, 120),
        "date": date,
        "next": _one_line(nxt, 140),
    }


def build(folder: Path, out: Path, title: str, vocab: tuple) -> str:
    files = sorted(
        p for p in folder.glob("*.md")
        if p.is_file() and p.resolve() != out.resolve() and p.name.lower() != "readme.md"
        and not p.name.endswith(".template.md")
    )
    rows = [describe(p) for p in files]
    link_base = os.path.relpath(folder.resolve(), out.resolve().parent).replace("\\", "/")
    link_base = "" if link_base == "." else link_base + "/"
    grouped: Dict[str, List[Dict[str, Any]]] = {name: [] for name, _ in GROUPS}
    grouped[OTHER] = []
    grouped[OFF_VOCABULARY] = []
    for row in rows:
        if row["word"] not in vocab:
            grouped[OFF_VOCABULARY].append(row)
            continue
        for name, words in GROUPS:
            if row["word"] in words:
                grouped[name].append(row)
                break
        else:
            grouped[OTHER].append(row)

    out_lines = [
        f"# {title}",
        "",
        f"*Generated by `os/gen_index.py` from the {len(rows)} file(s) in this folder. Do not edit it by hand:",
        "change the files, then regenerate.*",
        "",
        " · ".join(f"**{name}** {len(grouped[name])}" for name in list(grouped)),
    ]
    for name in grouped:
        group = sorted(grouped[name], key=lambda r: (r["date"], r["name"]), reverse=True)
        if not group:
            continue
        out_lines += ["", f"## {name} ({len(group)})", "", "| Date | File | Status |", "|---|---|---|"]
        for row in group:
            status = f"`{row['status']}`" if row["status"] else "no status"
            out_lines.append(f"| {row['date'] or '-'} | [{row['title']}]({link_base}{row['name']}) | {status} |")
        if name == "Open":
            notes = [r for r in group if r["next"]]
            if notes:
                out_lines += ["", "**Next steps, as each file states them:**", ""]
                out_lines += [f"- [{r['title']}]({link_base}{r['name']}): {r['next']}" for r in notes]
    return "\n".join(out_lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a folder's index from its files' frontmatter.")
    parser.add_argument("folder", help="the folder of Markdown files to index (relative to --root)")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="the instance root (default: this repository)")
    parser.add_argument("--out", default=None, help=f"the index file (default: <folder>/{DEFAULT_OUT})")
    parser.add_argument("--title", default=None, help="the index heading (default: the folder name)")
    parser.add_argument("--vocab", default=",".join(lint.VOCABULARY), help="comma-separated status vocabulary")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write the index to --out")
    mode.add_argument("--check", action="store_true", help="exit 1 if --out differs from a fresh build")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    folder = Path(args.folder) if Path(args.folder).is_absolute() else root / args.folder
    if not folder.is_dir():
        print(f"gen_index: not a directory: {args.folder}", file=sys.stderr)
        return 2
    if args.out is None:
        out = folder / DEFAULT_OUT
    else:
        out = Path(args.out) if Path(args.out).is_absolute() else root / args.out
    vocab = tuple(w.strip().lower() for w in args.vocab.split(",") if w.strip())
    title = args.title or folder.resolve().name.replace("-", " ").replace("_", " ").title()
    text = build(folder, out, title, vocab)

    if args.check:
        try:
            current = out.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            print(f"gen_index: {out.name} does not exist yet; run with --write", file=sys.stderr)
            return 1
        if current.replace("\r\n", "\n") != text:
            print(f"gen_index: {out.name} is stale; regenerate with --write", file=sys.stderr)
            return 1
        print(f"gen_index: {out.name} is up to date")
        return 0
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print(f"gen_index: wrote {out.name} ({text.count(chr(10))} lines)")
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
