"""
Regression guards for `examples/` -- the worked instance, which until now had none.

The rest of the suite tests the scaffold's *code*. This file tests the one directory that
is pure content, and content is where the defects actually were: an adversarial review of
`examples/baseline-year/` found eighteen, every one of them re-findable today only by
running another adversarial review. Roughly ten ad-hoc verification scripts were written
during that review and none survived it. These four checks are the load-bearing subset,
made permanent.

Each check below is parameterized over a glob rather than a file list. Each glob asserts a
non-zero match count, because a parametrize over an empty list passes every assertion it
contains without running one.

What that does and does not buy a *second* worked example, stated precisely because the
first draft of this docstring overclaimed it: the per-file checks (disclaimers, references,
backlinks) cover a new example the day it lands. The registry checks cover it only if it
ships its own `corrections-registry.yaml` and `skill-registry.yaml` -- the globs find those
anywhere under `examples/`, but a second example that omits them is silently unexamined
rather than red. Closing that would mean asserting what a worked example must contain,
which is a call for whoever writes the second one.

**This file is one half of a two-layer gate, and the halves are complementary.** Deleting
an example file outright is caught by CI's `markdown-links` job for the five files
`examples/README.md` links to, and by the registry checks here for the six skill files and
the registry it does not link. Measured across all twelve files, every deletion reds at
least one layer and neither layer covers all twelve alone. If that CI job is ever narrowed,
re-check this file's coverage before assuming it compensates.

What is deliberately NOT here: an em-dash density lint, a machine-writing-tell lint, and a
publisher-voice-leak diff. All three were measured and rejected -- see
`plans/plan-keel-example-hardening-2026-07-19.md` section 5 for the numbers. They
would redden the scaffold before they reddened the example.
"""

import re
from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT, sr

EXAMPLES = REPO_ROOT / "examples"

# Every worked example is a directory under `examples/`. `examples/README.md` is the
# disclosure document that describes them and is not itself one.
EXAMPLE_SLUGS = sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir())

# Content files a reader can open, and whose format has somewhere to put a visible
# disclaimer: markdown gets a blockquote, YAML gets a `#` header.
CHECKED_SUFFIXES = {".md", ".yaml", ".yml"}

EXAMPLE_FILES = sorted(
    (p for p in EXAMPLES.rglob("*") if p.is_file() and p.suffix in CHECKED_SUFFIXES),
    key=lambda p: p.as_posix(),
)


def _rel(path):
    """Repo-relative POSIX string, so failure messages read the same on Windows."""
    return path.relative_to(REPO_ROOT).as_posix()


def _params(paths):
    return [pytest.param(p, id=_rel(p)) for p in paths]


def test_the_globs_matched_something():
    """
    The guard on every other test in this file. A parametrize over an empty list is a
    green test that ran nothing, which is exactly the failure mode this file exists to
    prevent elsewhere -- so it gets its own assertion rather than a comment.
    """
    assert EXAMPLE_SLUGS, f"no example directories found under {_rel(EXAMPLES)}"
    assert EXAMPLE_FILES, f"no .md/.yaml files found under {_rel(EXAMPLES)}"


def test_no_example_file_has_an_unchecked_format():
    """
    Every check in this file collects on CHECKED_SUFFIXES, so a file in any other format
    is silently exempt from all of them -- no disclaimer check, no reference check.

    `os/dependency-graph.template.json` is the obvious next one: `examples/README.md`
    already lists it as a deliberate omission, so a filled instance is a plausible
    addition, and JSON has no comment syntax to put a disclaimer in. That is a real
    decision for whoever adds it, so this fails loudly and asks for one rather than
    quietly waving the file through.
    """
    unchecked = sorted(
        _rel(p) for p in EXAMPLES.rglob("*") if p.is_file() and p.suffix not in CHECKED_SUFFIXES
    )
    assert not unchecked, (
        f"example files in a format no check in this file examines: {unchecked}.\n"
        f"Currently checked: {sorted(CHECKED_SUFFIXES)}. Either add the suffix here and "
        "work out where a visible disclaimer goes in that format, or keep the file out of "
        "examples/."
    )


# ── A1.a: disclaimer visibility ──────────────────────────────────────────────
#
# The blocker the first pass shipped: disclaimers written as HTML comments, which are
# invisible in every rendered view of the file -- GitHub, an editor preview, a docs site.
# A reader sees a filled, confident-looking profile for a firm that does not exist and no
# indication anywhere that it is fiction.

DISCLAIMER = re.compile(r"does not exist|fictional|invented", re.IGNORECASE)

# Unterminated comments matter. Slicing to a line budget can cut a comment in half, and a
# pattern requiring the closing `-->` would leave the orphaned opener's text in the
# haystack -- re-admitting exactly the content this strip exists to remove. `(?:-->|\Z)`
# closes at the end of the string when no terminator survived the slice.
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)

# The window a reader actually sees before deciding whether to trust the file. Fifteen
# lines clears the deepest current disclaimer (`skills/voice/SKILL.md`, line 13, sitting
# below a nine-line YAML frontmatter block) with two lines of margin. If a new file needs
# more room than this, the disclaimer has moved below the fold and the fix is to raise the
# disclaimer, not this number.
HEADER_LINES = 15


# The disclaimer has to be *marked up as* a disclaimer, not merely contain the words. The
# repo's own constraint is "a rendered blockquote for markdown, a `#` header for YAML", and
# `examples/README.md` uses a bold lead paragraph. Requiring one of those three markers
# stops an ordinary sentence that happens to use the word "invented" -- "Sam invented a new
# intake process in March" -- from satisfying the check while asserting the file is real.
DISCLAIMER_MARKUP = ("> ", ">", "#", "**")


def _header_without_comments(text):
    """The first HEADER_LINES lines with HTML comments stripped. The strip is the point."""
    header = "\n".join(text.splitlines()[:HEADER_LINES])
    return HTML_COMMENT.sub("", header)


def _declares_fiction(text):
    for line in _header_without_comments(text).splitlines():
        stripped = line.strip()
        if stripped.startswith(DISCLAIMER_MARKUP) and DISCLAIMER.search(stripped):
            return True
    return False


@pytest.mark.parametrize("path", _params(EXAMPLE_FILES))
def test_every_example_file_declares_itself_fiction_visibly(path):
    text = path.read_text(encoding="utf-8")
    assert _declares_fiction(text), (
        f"{_rel(path)} has no visible fiction disclaimer in its first {HEADER_LINES} lines.\n"
        f"It must match {DISCLAIMER.pattern!r} in content a reader can actually see: a "
        f"blockquote for markdown, a `#` comment header for YAML.\n"
        f"An HTML comment does NOT count -- it is stripped before this check runs, because "
        f"it renders as nothing on GitHub and in every preview."
    )


def test_the_disclaimer_check_rejects_an_html_comment_disclaimer():
    """
    The negative control, and the reason the test above is worth anything.

    Without this, the comment-stripping could silently stop working -- a broken regex, an
    edit that drops the `.sub()` call -- and every file would keep passing, for the wrong
    reason, while the original blocker sat right back in the tree undetected. A check that
    returns the same verdict for every input it is given has stopped being a check.
    """
    visible = "# Example Firm\n\n> This firm does not exist.\n"

    # The commented-out form has to carry the SAME markup the visible one does -- a
    # blockquote line inside the comment. A comment whose text has no `>`/`#`/`**` prefix
    # is rejected by the markup rule alone, so using one here would let the comment
    # stripping break with this control still green: the exact vacuous pass it exists to
    # prevent. Commenting out a block you previously wrote as a blockquote is also the
    # realistic way this defect actually arrives.
    hidden = "# Example Firm\n\n<!--\n> This firm does not exist.\n-->\n"

    assert _declares_fiction(visible), "the helper rejected a plainly visible disclaimer"
    assert not _declares_fiction(hidden), (
        "the helper ACCEPTED a disclaimer that exists only inside an HTML comment. "
        "Comment stripping is broken, and every file in the suite above is now passing "
        "vacuously -- including any that reintroduced the original blocker."
    )


def test_the_disclaimer_check_survives_an_unterminated_comment():
    """
    A comment opening inside the header window and closing past it must not smuggle its
    text through. Slicing first and stripping second is what makes this a live edge, not a
    hypothetical: it happens to any file whose teaching note sits near the line budget.
    """
    body = "\n".join(
        ["# Example Firm", "", "<!--", "> this firm does not exist"] + ["filler"] * 40
    )
    assert not _declares_fiction(body), (
        "text inside an unterminated HTML comment counted as a visible disclaimer"
    )


# ── A1.b: metadata coherence ─────────────────────────────────────────────────
#
# Hand-maintained counts in a `meta:` block drift the moment anyone edits the entries
# below them. Nothing else in this repo reads these fields: YAML parsing proves they are
# well-formed, and `skill-registry.py` never looks at `meta:` at all. Derive every number
# here from the entries -- a test asserting a literal 4/3/1/0 reproduces the
# hand-maintained-number problem it exists to remove.

# `os/corrections/LIFECYCLE.md` line 47: "5 or more total fires, OR the same pattern across
# 3 or more separate sessions." An entry at or above this is due for promotion to a hard
# rule, so it should not still be sitting `active`. Kept as a named constant so that
# editing the threshold in LIFECYCLE.md produces a legible red here rather than a puzzle.
LIFECYCLE_PROMOTION_FIRES = 5

CORRECTIONS_REGISTRIES = sorted(EXAMPLES.rglob("corrections-registry.yaml"))
SKILL_REGISTRIES = sorted(EXAMPLES.rglob("skill-registry.yaml"))


def test_the_metadata_globs_matched_something():
    assert CORRECTIONS_REGISTRIES, "no corrections registry found under examples/"
    assert SKILL_REGISTRIES, "no skill registry found under examples/"


@pytest.mark.parametrize("path", _params(CORRECTIONS_REGISTRIES))
def test_corrections_registry_meta_matches_its_own_entries(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    meta, entries = data["meta"], data["entries"]

    statuses = [e.get("status") for e in entries]
    expected = {
        "total_corrections": len(entries),
        "active": statuses.count("active"),
        "superseded": statuses.count("superseded"),
        "retired": statuses.count("retired"),
    }
    actual = {key: meta.get(key) for key in expected}
    assert actual == expected, (
        f"{_rel(path)} meta block disagrees with its entries.\n"
        f"  declared: {actual}\n"
        f"  actual:   {expected}"
    )


@pytest.mark.parametrize("path", _params(CORRECTIONS_REGISTRIES))
def test_every_superseded_correction_says_what_superseded_it(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    orphans = [
        e.get("id")
        for e in data["entries"]
        if e.get("status") == "superseded" and not (e.get("superseded_by") or "").strip()
    ]
    assert not orphans, (
        f"{_rel(path)}: superseded entries with no `superseded_by`: {orphans}.\n"
        "A superseded entry without a forwarding address is a dead end -- the reader "
        "cannot find the rule that replaced it."
    )


@pytest.mark.parametrize("path", _params(CORRECTIONS_REGISTRIES))
def test_no_active_correction_is_overdue_for_promotion(path):
    """
    The example's whole claim is that it models the lifecycle correctly. An `active` entry
    at or past the promotion trigger is the artifact contradicting the process it teaches
    -- and it recurs on any edit that bumps a `times_fired`.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    overdue = [
        (e.get("id"), e.get("times_fired"))
        for e in data["entries"]
        if e.get("status") == "active" and (e.get("times_fired") or 0) >= LIFECYCLE_PROMOTION_FIRES
    ]
    assert not overdue, (
        f"{_rel(path)}: still `active` at or past LIFECYCLE.md's {LIFECYCLE_PROMOTION_FIRES}-fire "
        f"promotion trigger: {overdue}.\n"
        "Promote it to a hard rule and mark the entry superseded, or the example models "
        "the failure it documents."
    )


@pytest.mark.parametrize("path", _params(SKILL_REGISTRIES))
def test_skill_registry_meta_matches_its_own_capabilities(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    meta, caps = data["meta"], data["capabilities"]

    types = [c.get("type") for c in caps]
    expected = {
        "total_capabilities": len(caps),
        "skills": types.count("skill"),
        "references": types.count("reference"),
        "tools": types.count("tool"),
    }
    actual = {key: meta.get(key) for key in expected}
    assert actual == expected, (
        f"{_rel(path)} meta block disagrees with its capabilities.\n"
        f"  declared: {actual}\n"
        f"  actual:   {expected}"
    )


# ── A1.c: references that resolve ────────────────────────────────────────────
#
# 86 backticked path references live under `examples/` and CI sees none of them: the
# markdown-link job's regex requires `[text](path)` form. A backticked path that points
# nowhere is the same broken promise with no checker behind it.

# Filename *conventions* and globs are not references. `proposals/[prospect-slug]-[YYYY-MM-DD].md`
# describes what to name an output file; `skills/evals/*/cases.yaml` is a glob. Neither can
# be made to resolve, and neither can be added to the disclosure list without making the
# disclosure false. On today's tree they are roughly 60% of the apparent failures.
CONVENTION_CHARS = set("[]*")

# The extension must START with a letter. Without that, any backticked dotted token reads
# as a path: a version string (`3.11`), a temperature target (`1.5`), a rate. Those are
# ordinary content in a filled example -- this one is a sustainability-reporting practice --
# and treating them as broken references reddens the suite over nothing.
BACKTICKED_PATH = re.compile(r"`([^`\s]+\.[A-Za-z][A-Za-z0-9]*)`")

# References that legitimately resolve nowhere. Every entry must also be named in
# `examples/README.md`, which is asserted below -- an undisclosed exemption is just a
# broken link with a note attached.
#
# `reference.md` and `references/review-checklist.md` are disclosed omissions: files the
# example deliberately does not ship (README's "what's deliberately missing" list).
#
# This set held a third entry, `agent-context.md`, for exactly one commit. That reference
# named a file which DOES exist, at `examples/baseline-year/os/agent-context.md`, but
# `examples/README.md` wrote it by bare basename. No resolution rule fixes that without
# also rescuing `reference.md` via the unrelated `skills/voice/reference.md`, which would
# have hidden the then-missing `proposal/reference.md`. It was exempted here, flagged, and
# fixed at source in the following lane -- at which point this check failed on the stale
# entry and required its removal. That is the intended behaviour: an allowlist entry whose
# underlying reference gets fixed does not get to linger.
#
# `CLAUDE.md` is a different category again: not a file this repository declines to ship, but
# one the READER creates at their own repository root. A template repo shipping a real
# `CLAUDE.md` would have its own instructions loaded by every agent that opened it, so its
# absence here is the design. `examples/README.md` explains this at length under "The one
# file with no template".
ALLOWED_UNRESOLVED = {
    "reference.md",
    "references/review-checklist.md",
    "CLAUDE.md",
}


def _resolves(ref, source):
    """
    A reference resolves if it points at a real file from any of three vantage points:
    relative to its own file, from the example's own root, or from the scaffold root as
    itself or as its `.template.` sibling.

    The `.template.` sibling rule is what makes the example's own prose honest: it names
    `os/agent-context.md` when the scaffold ships `os/agent-context.template.md`, which is
    the file the reader is being pointed at.
    """
    ref_path = Path(ref)
    sibling = ref_path.parent / (ref_path.stem + ".template" + ref_path.suffix)
    example_root = EXAMPLES / source.relative_to(EXAMPLES).parts[0]

    for base in (source.parent, example_root, REPO_ROOT):
        if (base / ref_path).exists() or (base / sibling).exists():
            return True
    return False


@pytest.mark.parametrize("path", _params(EXAMPLE_FILES))
def test_every_backticked_path_reference_resolves(path):
    text = path.read_text(encoding="utf-8")
    refs = {r for r in BACKTICKED_PATH.findall(text) if not (CONVENTION_CHARS & set(r))}

    dangling = sorted(r for r in refs if r not in ALLOWED_UNRESOLVED and not _resolves(r, path))
    assert not dangling, (
        f"{_rel(path)} references paths that resolve nowhere: {dangling}.\n"
        "Either fix the path, or -- if the file is deliberately not shipped -- add it to "
        "ALLOWED_UNRESOLVED here AND name it in examples/README.md's omissions list."
    )


def test_the_reference_check_examined_a_meaningful_number_of_refs():
    """
    The exclusion rule above is subtractive, so a regex that quietly stops matching would
    leave every file with an empty `refs` set and a green suite. Pin a floor.
    """
    found = set()
    for path in EXAMPLE_FILES:
        text = path.read_text(encoding="utf-8")
        found |= {r for r in BACKTICKED_PATH.findall(text) if not (CONVENTION_CHARS & set(r))}
    assert len(found) >= 20, (
        f"only {len(found)} backticked path references extracted from examples/ -- the "
        "extraction regex has probably stopped matching, which would make the dangling-"
        "reference test above pass on an unexamined tree."
    )


def test_every_allowlisted_reference_is_disclosed_in_the_examples_readme():
    """
    The allowlist is a promise that a missing file is missing *on purpose*. That promise is
    only kept if a reader can find it stated somewhere they will actually look.
    """
    readme = (EXAMPLES / "README.md").read_text(encoding="utf-8")

    # Match the BACKTICKED form, not a bare substring. `reference.md` occurs inside the
    # link target `baseline-year/skills/voice/reference.md` on the line that says the voice
    # reference DOES ship -- the opposite of an omission. A substring test reads that as
    # disclosure and can never fail for this entry.
    disclosed = set(BACKTICKED_PATH.findall(readme))
    undisclosed = sorted(r for r in ALLOWED_UNRESOLVED if r not in disclosed)
    assert not undisclosed, (
        f"ALLOWED_UNRESOLVED exempts references that examples/README.md never names in "
        f"backticks: {undisclosed}.\nAn exemption the disclosure document does not state is "
        "a broken link the test suite agreed to ignore."
    )


# A wrong relative depth still resolves -- from `examples/baseline-year/os/`, a stray
# `../../../README.md` lands on the repo-root README, which exists. The existing
# markdown-link checker follows it and passes green on the wrong target. Only the link
# TEXT reveals the intent, so that is what this pairs against the resolved path.
README_BACKLINK = re.compile(r"\[`?examples/README\.md`?\]\(([^)]+)\)")


@pytest.mark.parametrize("path", _params([p for p in EXAMPLE_FILES if p.suffix == ".md"]))
def test_links_that_say_examples_readme_actually_point_at_it(path):
    text = path.read_text(encoding="utf-8")
    wrong = []
    for target in README_BACKLINK.findall(text):
        # Strip the fragment before resolving, matching what CI's own markdown-links job
        # does. Without this, a correct link that deep-links a section
        # (`../../README.md#whats-here`) fails as a false alarm.
        bare = target.split("#")[0].strip()
        if not bare:
            continue
        resolved = (path.parent / bare).resolve()
        if resolved != (EXAMPLES / "README.md").resolve():
            wrong.append((target, resolved.as_posix()))
    assert not wrong, (
        f"{_rel(path)} has links labelled `examples/README.md` that resolve elsewhere: "
        f"{wrong}.\nThese pass the repo's markdown-link checker because the wrong depth "
        "still lands on a file that exists (usually the repo-root README)."
    )


def test_the_readme_backlink_check_found_backlinks():
    total = sum(
        len(README_BACKLINK.findall(p.read_text(encoding="utf-8")))
        for p in EXAMPLE_FILES
        if p.suffix == ".md"
    )
    assert total >= 5, (
        f"only {total} `examples/README.md` backlinks found -- every disclaimer header "
        "carries one, so a number this low means the pattern has stopped matching and the "
        "test above is checking nothing."
    )


# ── A1.d: the example registry loads, self-routes, and agrees with itself ────
#
# `test_bullseye.py` falls back to the *template* registry, because no live
# `skills/registry/skill-registry.yaml` ships at the scaffold root. Nothing in the suite
# reaches the example's registry -- which is how it shipped with a real trigger collision
# in the artifact whose stated job is showcasing collision handling.

EXAMPLE_REGISTRY_PATHS = _params(SKILL_REGISTRIES)


@pytest.mark.parametrize("path", EXAMPLE_REGISTRY_PATHS)
def test_the_example_registry_loads_through_the_real_loader(path):
    caps = sr.load_registry(path)
    assert caps, f"{_rel(path)} loaded no capabilities"

    declared = yaml.safe_load(path.read_text(encoding="utf-8"))["capabilities"]
    assert len(caps) == len(declared), (
        f"{_rel(path)}: the loader returned {len(caps)} capabilities but the file declares "
        f"{len(declared)}."
    )


@pytest.mark.parametrize("path", EXAMPLE_REGISTRY_PATHS)
def test_registry_id_folder_name_and_skill_frontmatter_all_agree(path):
    """
    Three names for one skill, maintained in three places. The registry entry's id, the
    directory it lives in, and the `name:` in its own frontmatter. An agent routes on the
    first and loads by the second; a mismatch routes to a skill that cannot be found.
    """
    skills_root = path.parent.parent
    mismatches = []

    for cap in (c for c in sr.load_registry(path) if c.type == "skill"):
        skill_md = skills_root / cap.id / "SKILL.md"
        if not skill_md.exists():
            mismatches.append(f"{cap.id}: no SKILL.md at {_rel(skill_md)}")
            continue
        declared = re.search(
            r'^name:\s*"?([^"\n]+?)"?\s*$', skill_md.read_text(encoding="utf-8"), re.MULTILINE
        )
        if declared is None:
            mismatches.append(f"{cap.id}: {_rel(skill_md)} declares no `name:` in frontmatter")
        elif declared.group(1) != cap.id:
            mismatches.append(
                f"{cap.id}: {_rel(skill_md)} frontmatter says name: {declared.group(1)!r}"
            )

    assert not mismatches, f"{_rel(path)} id/folder/frontmatter mismatches:\n  " + "\n  ".join(
        mismatches
    )


def _self_routing_params():
    """One case per (registry, skill, trigger phrase) -- all of them, not just the first.

    Testing only first-triggers is green on a tree with a real collision: the shipped
    collision was on the `voice` skill's FOURTH trigger, and all five first-triggers routed
    confidently. That near-miss is the entire reason this parametrize walks every phrase.
    """
    params = []
    for path in SKILL_REGISTRIES:
        registry = sr.load_registry(path)
        for cap in (c for c in registry if c.type == "skill"):
            for index, phrase in enumerate(cap.trigger_patterns):
                params.append(
                    pytest.param(
                        path, registry, cap, phrase, id=f"{_rel(path)}::{cap.id}::{index}"
                    )
                )
    return params


SELF_ROUTING_PARAMS = _self_routing_params()


def test_the_self_routing_harness_covers_every_trigger_phrase():
    declared = sum(
        len(c.trigger_patterns)
        for path in SKILL_REGISTRIES
        for c in sr.load_registry(path)
        if c.type == "skill"
    )
    assert declared > 0, "no trigger phrases found in any example registry"
    assert len(SELF_ROUTING_PARAMS) == declared, (
        f"the harness generated {len(SELF_ROUTING_PARAMS)} cases for {declared} declared "
        "trigger phrases -- coverage has been dropped somewhere."
    )


@pytest.mark.parametrize("path,registry,cap,phrase", SELF_ROUTING_PARAMS)
def test_every_trigger_phrase_routes_to_the_skill_that_claims_it(path, registry, cap, phrase):
    results = sr.search(phrase, registry, top_k=3)
    assert results, f"{phrase!r} matched nothing in {_rel(path)}"

    ranked = ", ".join(f"{m.id} ({m.relevance_score})" for m in results)
    assert results[0].id == cap.id, (
        f"{_rel(path)}: {cap.id} claims {phrase!r} as a trigger, but that query ranks "
        f"{results[0].id} first.\n  top 3: {ranked}"
    )


@pytest.mark.parametrize("path,registry,cap,phrase", SELF_ROUTING_PARAMS)
def test_every_trigger_phrase_routes_confidently(path, registry, cap, phrase):
    """
    Winning is not enough -- the win has to be decisive.

    The collision this example actually shipped with had the RIGHT winner: `voice` ranked
    first on its own fourth trigger, but led `session-integrity` by 0.340 against a 0.4 gap
    threshold. `assess_confidence` calls that "ambiguous", and a routing layer following
    this scaffold's own rule stops and asks the operator instead of loading. A
    winner-by-name assertion is green on that tree, which is why this is a separate check
    rather than an extra clause on the one above.

    This is the standing bar the batch plan sets for any future registry edit.
    """
    results = sr.search(phrase, registry, top_k=3)
    verdict = sr.assess_confidence(results)
    ranked = ", ".join(f"{m.id} ({m.relevance_score})" for m in results)
    assert verdict == "confident", (
        f"{_rel(path)}: {cap.id}'s trigger {phrase!r} routes {verdict!r}, not 'confident'.\n"
        f"  top 3: {ranked}\n"
        "An ambiguous trigger stalls routing even when it ranks first. Tighten a `not_for` "
        "clause on the runner-up, or reword whichever trigger is doing double duty."
    )
