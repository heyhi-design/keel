"""
Regression test for the corrections registry's key contract.

keel ships the corrections *schema and seeds* (os/corrections/); the tool that reads them at a
session boundary -- `corrections_cli.py`'s search / audit / inject -- ships separately, in the
agent-corrections repository. That CLI requires the registry's top level to be a mapping with an
`entries:` key (corrections_cli.py, verified at authoring: "the top level of a registry must be
a mapping with an `entries:` key"). If keel's files ever drifted to a different key -- a
`corrections:` list, say -- the two would silently stop fitting together and `inject` would read
an empty registry.

This test guards keel's side of that contract. It does not import agent-corrections (that would
couple keel's suite to a second repo, and break when keel is exported on its own); it asserts the
one property keel is responsible for -- that its template and seed set are keyed on `entries:`,
shaped as the CLI expects. The behavioral other half (running `inject` against these files and
watching the active seeds come out) is verified by hand at release time, since `inject` lives in
the other repo and emits active-status entries by default.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CORRECTIONS_DIR = REPO_ROOT / "os" / "corrections"
TEMPLATE = CORRECTIONS_DIR / "corrections-registry.template.yaml"
SEEDS = CORRECTIONS_DIR / "seed-corrections.yaml"

# The statuses agent-corrections recognizes (corrections_cli.py: VALID_STATUSES).
VALID_STATUSES = {"active", "retired", "superseded"}


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ── the template ─────────────────────────────────────────────────────────────


def test_the_template_is_a_mapping_keyed_on_entries():
    """The exact shape corrections_cli.py requires: a mapping with an `entries:` list."""
    data = _load(TEMPLATE)
    assert isinstance(data, dict), "the registry top level must be a mapping"
    assert "entries" in data, "the registry must use the `entries:` key (not `corrections:`)"
    assert isinstance(data["entries"], list), "`entries:` must be a list"


def test_the_template_ships_empty():
    """The template is a scaffold, not a starter corpus: `entries: []`, filled by the operator."""
    assert _load(TEMPLATE)["entries"] == []


# ── the seed set ─────────────────────────────────────────────────────────────


def test_the_seed_set_is_keyed_on_entries_with_five_entries():
    data = _load(SEEDS)
    assert isinstance(data, dict) and isinstance(data.get("entries"), list)
    assert len(data["entries"]) == 5


def test_every_seed_entry_has_an_id_and_a_valid_status():
    for entry in _load(SEEDS)["entries"]:
        assert isinstance(entry, dict), "each entry must be a mapping"
        assert entry.get("id"), "each entry needs a non-empty id"
        assert entry.get("status") in VALID_STATUSES, f"{entry.get('id')}: bad status {entry.get('status')!r}"


def test_the_seed_meta_counts_match_the_actual_entries():
    """
    The meta block is the count the file claims; the entries are the count it has. A registry
    whose header disagrees with its body is exactly the drift the corrections audit exists to
    catch, so the seed set must not ship in that state.
    """
    data = _load(SEEDS)
    entries = data["entries"]
    meta = data["meta"]
    statuses = [e["status"] for e in entries]

    assert meta["entry_count"] == len(entries)
    assert meta["active"] == statuses.count("active")
    assert meta["superseded"] == statuses.count("superseded")


def test_the_seed_set_carries_exactly_three_injectable_active_entries():
    """
    `inject` emits active-status entries by default, so the three active seeds are what a fresh
    instance sees at session start. This is keel's side of "inject surfaces the seeds": the
    file presents three active entries, keyed where the CLI looks for them.
    """
    active = [e["id"] for e in _load(SEEDS)["entries"] if e.get("status") == "active"]
    assert len(active) == 3
