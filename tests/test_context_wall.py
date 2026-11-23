"""
The keelson context-wall lint (keelson/context_wall.py).

It is the separability check's second half: phrases, not paths. What has to hold:
  - it refuses to run without a map, or with an empty or vacuous one (a gate with nothing to
    check must not pass);
  - by default it reads only origin:keel files, with --all every text file;
  - a plain phrase matches whole words, case-insensitively; `re:` entries are expressions;
  - hits name the map line, and the phrase only on request;
  - the map itself never travels: tagged origin:keel, or inside an --all tree, is refused;
  - keel ships no map.
"""

import subprocess
import sys

from conftest import REPO_ROOT, load_tool

cw = load_tool("keelson/context_wall.py", "context_wall_under_test")
SCRIPT = REPO_ROOT / "keelson" / "context_wall.py"

MAP = "# instance phrases\nExample Client Co -> a client\nzorbit\nre:\\bEXC-\\d+\\b -> a ticket id\n"


def tree(tmp_path, files):
    root = tmp_path / "tree"
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def phrase_map(tmp_path, text=MAP):
    path = tmp_path / "private" / "context-wall.map"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def test_a_keel_file_carrying_a_phrase_fails_and_names_the_map_line(tmp_path):
    root = tree(tmp_path, {"skill.md": "<!-- origin: keel -->\n# Skill\nWritten for example client co last spring.\n"})
    out = run(root, "--map", phrase_map(tmp_path))
    assert out.returncode == 1
    assert "skill.md:3: map line 2 -> a client" in out.stderr
    assert "example client co" not in out.stderr.lower()  # the phrase stays out of the log


def test_show_phrases_prints_the_phrase(tmp_path):
    root = tree(tmp_path, {"a.py": "# origin: keel\nNAME = 'zorbit'\n"})
    out = run(root, "--map", phrase_map(tmp_path), "--show-phrases")
    assert out.returncode == 1 and '"zorbit"' in out.stderr


def test_expressions_and_whole_words(tmp_path):
    root = tree(tmp_path, {
        "hit.md": "<!-- origin: keel -->\nSee EXC-42 for the history.\n",
        "miss.md": "<!-- origin: keel -->\nzorbitals and EXC-x are not hits.\n",
    })
    hits, checked, skipped = cw.scan(root, cw.read_map(phrase_map(tmp_path)))
    assert skipped == []
    assert checked == 2
    assert [(h[0], h[2]) for h in hits] == [("hit.md", 4)]


def test_untagged_and_instance_files_are_skipped_unless_all(tmp_path):
    root = tree(tmp_path, {
        "instance.md": "<!-- origin: instance -->\nzorbit\n",
        "untagged.md": "zorbit\n",
        "clean.md": "<!-- origin: keel -->\nnothing here\n",
    })
    the_map = phrase_map(tmp_path)
    assert run(root, "--map", the_map).returncode == 0
    out = run(root, "--map", the_map, "--all")
    assert out.returncode == 1 and "instance.md" in out.stderr and "untagged.md" in out.stderr


def test_no_map_empty_map_or_vacuous_expression_exits_two(tmp_path):
    root = tree(tmp_path, {"a.md": "<!-- origin: keel -->\n"})
    assert run(root).returncode == 2
    assert run(root, "--map", phrase_map(tmp_path, "# only comments\n\n")).returncode == 2
    assert run(root, "--map", phrase_map(tmp_path, "re:.*\n")).returncode == 2
    assert run(root, "--map", phrase_map(tmp_path, "re:(\n")).returncode == 2
    assert run(root, "--map", tmp_path / "does-not-exist.map").returncode == 2


def test_the_map_never_travels(tmp_path):
    root = tree(tmp_path, {"a.md": "<!-- origin: keel -->\nclean\n"})
    tagged = phrase_map(tmp_path, "# origin: keel\nzorbit\n")
    tagged = tagged.rename(tagged.with_suffix(".txt"))
    out = run(root, "--map", tagged)
    assert out.returncode == 2 and "origin: keel" in out.stderr
    inside = root / "context-wall.map"
    inside.write_text(MAP, encoding="utf-8")
    out = run(root, "--all", "--map", inside)
    assert out.returncode == 2 and "would ship" in out.stderr


def test_keel_ships_no_phrase_map():
    names = [p for p in REPO_ROOT.rglob("*") if p.is_file() and "context-wall" in p.name and p.suffix != ".py"]
    assert names == []


def test_keels_own_keel_files_pass_a_neutral_map(tmp_path):
    out = run(REPO_ROOT, "--map", phrase_map(tmp_path, "zorbit-nonexistent-phrase\n"))
    assert out.returncode == 0, out.stderr
    assert "origin:keel file(s) checked" in out.stdout


def test_a_phrase_wrapped_across_lines_is_caught(tmp_path):
    root = tree(tmp_path, {"doc.md": "<!-- origin: keel -->\nWe wrote this for Example\nClient Co in the spring.\n"})
    hits, _, _ = cw.scan(root, cw.read_map(phrase_map(tmp_path)))
    assert [(h[0], h[1], h[2]) for h in hits] == [("doc.md", 2, 2)]


def test_all_reads_every_non_binary_file_whatever_its_suffix(tmp_path):
    root = tree(tmp_path, {"page.html": "<p>zorbit</p>\n", "data.csv": "a,zorbit\n", "NOTES.MD": "zorbit\n", "Makefile": "zorbit:\n"})
    (root / "latin1.txt").write_bytes("caf\xe9 zorbit\n".encode("latin-1"))
    (root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\0\0zorbit")
    out = run(root, "--all", "--map", phrase_map(tmp_path))
    assert out.returncode == 1
    for name in ("page.html", "data.csv", "NOTES.MD", "Makefile", "latin1.txt"):
        assert name in out.stderr, name
    assert "1 binary or unreadable file(s) not checked: image.png" in out.stderr


def test_all_mode_reads_folders_named_like_environments(tmp_path):
    # A docs/env/ folder is real content in an export; --all must not skip it silently.
    root = tree(tmp_path, {"docs/env/setup.md": "set up zorbit here\n"})
    out = run(root, "--all", "--map", phrase_map(tmp_path))
    assert out.returncode == 1 and "docs/env/setup.md" in out.stdout + out.stderr


def test_a_map_tagged_origin_keel_is_refused_whatever_its_suffix(tmp_path):
    root = tree(tmp_path, {"a.md": "<!-- origin: keel -->\nclean\n"})
    out = run(root, "--map", phrase_map(tmp_path, "# origin: keel\nzorbit\n"))
    assert out.returncode == 2 and "origin: keel" in out.stderr
