"""LIVE integration test for the semantic (vector) leg — skipped unless the whole
optional stack is present.

Unlike ``test_memory_adapter.py`` (which drives the seam with a trivial fake
embedder and a fake sqlite-vec, so it runs fully offline), this test uses the
REAL pieces end to end: the ``FastEmbedEmbedder`` (which downloads
``sentence-transformers/all-MiniLM-L6-v2`` on first construction) plus a real
``sqlite-vec`` vector table. It therefore runs only when ALL of these hold:

  * ``sqlite_vec`` is importable,
  * ``fastembed`` is importable, and
  * this Python's ``sqlite3`` build can load extensions (Apple's bundled macOS
    Python cannot — its connections have no ``enable_load_extension``).

On a machine missing any of the three (the build/CI machine here), the module is
cleanly SKIPPED at collection — the live run belongs in a venv with the optional
deps installed, and needs network for the one-time model download.

What it proves: the vector leg adds recall that keyword search alone cannot. A
semantic pair is chosen with NO shared word token — content "the feline dozed on
a warm windowsill" and query "cat napping near sunny glass" — and the test asserts
the vector adapter returns that entry for that query, while a parallel FTS5-only
adapter does NOT (and, as a control, that the FTS5-only adapter still finds the
same entry via a keyword query, so its miss is about semantics, not an empty
store).
"""

import sqlite3
import sys
from pathlib import Path

import pytest

# Gate the whole module on the optional semantic stack. importorskip handles the
# two packages; a skipif covers the sqlite3-can-load-extensions capability. All
# three are evaluated at collection, so this module is skipped as a unit.
pytest.importorskip(
    "sqlite_vec", reason="sqlite-vec not installed (optional semantic follow-on)"
)
pytest.importorskip(
    "fastembed", reason="fastembed not installed (optional semantic follow-on)"
)


def _sqlite3_can_load_extensions() -> bool:
    """True only if a fresh sqlite3 connection exposes enable_load_extension.
    Apple's bundled macOS Python ships a sqlite3 built without it, which is the
    documented reason the vector leg degrades to FTS5 there."""
    try:
        con = sqlite3.connect(":memory:")
    except Exception:
        return False
    try:
        return hasattr(con, "enable_load_extension")
    finally:
        con.close()


pytestmark = pytest.mark.skipif(
    not _sqlite3_can_load_extensions(),
    reason="this Python's sqlite3 cannot load extensions (e.g. Apple's bundled macOS Python)",
)

# The `memory` package lives at the repo root, not on sys.path under tests/.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from memory import SqliteAdapter  # noqa: E402
from memory.embedders import FastEmbedEmbedder  # noqa: E402

# The semantic target and a keyword-disjoint query. Tokenized on \w+, these share
# no word (cat/napping/near/sunny/glass vs the/feline/dozed/on/a/warm/windowsill),
# so FTS5's OR-of-tokens MATCH cannot retrieve the target for this query — only a
# meaning-aware embedding can.
TARGET = "the feline dozed on a warm windowsill"
SEMANTIC_QUERY = "cat napping near sunny glass"
KEYWORD_QUERY = "feline windowsill dozed"  # control: shares tokens with TARGET
DISTRACTORS = [
    "quarterly tax filing deadline moved to April",
    "repaint the garage door before the first frost",
    "the bicycle chain needs oiling again",
]


def _populate(adapter):
    """Write the target + distractors; return the target's id."""
    target_id = adapter.write(wing="home", room="notes", content=TARGET)["id"]
    for content in DISTRACTORS:
        adapter.write(wing="home", room="notes", content=content)
    return target_id


def test_semantic_leg_recalls_what_fts5_cannot(tmp_path):
    # --- vector adapter: real embedder + real sqlite-vec -------------------
    vec_adapter = SqliteAdapter(
        db_path=str(tmp_path / "vec.db"), embedder=FastEmbedEmbedder()
    )
    # With both pieces live, the vector leg must actually be on — if this is
    # False, sqlite-vec did not load and the rest would silently be FTS5-only.
    assert vec_adapter.vector_enabled is True

    target_id = _populate(vec_adapter)

    # k=2 out of 4 entries: the target has zero keyword overlap with the query,
    # so it can only enter the top-2 via the semantic leg out-ranking the three
    # unrelated distractors. Membership (not an exact rank) is asserted.
    vec_hits = vec_adapter.search(SEMANTIC_QUERY, k=2)
    vec_ids = [r["id"] for r in vec_hits["results"]]
    assert target_id in vec_ids, (
        "the vector leg should recall the semantically-close entry for a "
        "keyword-disjoint query; got ids=%r" % (vec_ids,)
    )

    # --- parallel FTS5-only adapter: no embedder --------------------------
    fts_adapter = SqliteAdapter(db_path=str(tmp_path / "fts.db"))
    assert fts_adapter.vector_enabled is False
    fts_target_id = _populate(fts_adapter)
    # ids are a deterministic hash of (wing, room, chunk_index, content), so the
    # same target content yields the same id in both stores.
    assert fts_target_id == target_id

    # Control: FTS5 CAN find the target by keyword, so the store is populated and
    # keyword recall works — the semantic miss below is about meaning, not setup.
    fts_control = fts_adapter.search(KEYWORD_QUERY, k=5)
    assert target_id in [r["id"] for r in fts_control["results"]]

    # The point: FTS5 alone does NOT surface the target for the keyword-disjoint
    # semantic query. This is the recall the vector leg adds.
    fts_hits = fts_adapter.search(SEMANTIC_QUERY, k=5)
    assert target_id not in [r["id"] for r in fts_hits["results"]], (
        "FTS5-only should NOT retrieve the keyword-disjoint target; if it did, "
        "the query and target share a token and the test's premise is broken"
    )


def test_fastembed_embedder_shape(tmp_path):
    # The embedder honors the seam contract directly: single-string .embed and
    # __call__ both return a flat list[float] of width .dim, and .dim is the
    # expected 384 for all-MiniLM-L6-v2.
    emb = FastEmbedEmbedder()
    assert emb.dim == 384
    v = emb.embed("a short sentence to embed")
    assert isinstance(v, list) and len(v) == emb.dim
    assert all(isinstance(x, float) for x in v)
    # callable path returns the same vector as .embed
    assert emb("a short sentence to embed") == v


def test_fastembed_alias_rejects_conflicting_embed_dim(tmp_path):
    """The create_adapter("fastembed") alias fills embed_dim from the model's
    authoritative .dim; a caller-supplied embed_dim that disagrees is rejected up
    front, rather than building a mis-sized vec0 table that crashes (and rolls
    back) the first write."""
    from memory.factory import create_adapter

    with pytest.raises(ValueError, match="conflicts with"):
        create_adapter(embedder="fastembed", embed_dim=999)
    # the correct path (omitting embed_dim) still opts into the vector leg
    ok = create_adapter(db_path=str(tmp_path / "ok.db"), embedder="fastembed")
    assert ok.vector_enabled is True


def test_wrong_embed_dim_degrades_and_keeps_entry(tmp_path):
    """Bare injection with a wrong embed_dim bypasses the alias's guard: the vec0
    table is built too wide (999) for the 384-d embedder, so the real vec insert
    fails at write time. The entry must still survive via FTS5 with the vector leg
    disabled — 'degrade, never crash' holds for the vector INSERT, not only the
    embed call."""
    adapter = SqliteAdapter(
        db_path=str(tmp_path / "bad.db"), embedder=FastEmbedEmbedder(), embed_dim=999
    )
    assert adapter.vector_enabled is True  # 999-wide table built; the embedder is 384-d
    r = adapter.write(wing="home", room="notes",
                      content="this entry must survive a vec dimension mismatch")
    assert r["success"] is True
    assert adapter.vector_enabled is False  # disabled after the failed vec insert
    assert "must survive" in adapter.get(r["id"])["content"]
    assert r["id"] in [x["id"] for x in adapter.search("survive vec dimension mismatch")["results"]]
