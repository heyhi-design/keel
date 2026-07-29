"""End-to-end smoke test for the SQLite memory adapter (memory/).

Runs fully OFFLINE. The adapter's v1 default is FTS5 keyword-only recall — no
embedder is shipped and no vector extension is required — so this suite is green
with nothing installed beyond the standard library, on any machine.

Everything round-trips against a throwaway temp database:
  - entries:   write -> search -> get -> update -> delete
  - diary:     diary_write -> diary_read
  - relations: add_relation -> query_relations, plus the closed-vocabulary
               guard rejecting an off-vocabulary predicate and a >128-char object

It also covers the paths the round-trip alone skips: the embedder-injection seam
(default is FTS5-only; injecting an embedder enables the vector leg iff sqlite-vec
loads, else it cleanly stays FTS5), and the backend-neutral day-0 fixes — the
date-only `as_of` relation query, the diary wing-filter canonicalization, and the
example alias file's comment field. The seam tests use a trivial deterministic
fake embedder (and, where needed, a fake sqlite-vec) so they too run offline with
no extension and no model download.
"""

import hashlib
import sys
import types
from pathlib import Path

import pytest

# The `memory` package lives at the repository root, which is not on sys.path
# when pytest collects from tests/. Add it, mirroring how conftest.py loads the
# registry module by path.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from memory import SqliteAdapter, create_adapter  # noqa: E402
from memory import canon as canon  # noqa: E402
from memory import sqlite_adapter as sa  # noqa: E402
from memory.vocab import OBJECT_MAX  # noqa: E402


@pytest.fixture
def mem(tmp_path):
    """A fresh adapter over a throwaway db. With no embedder injected (the v1
    default), it is FTS5 keyword-only, so the test needs no vector extension and
    no embedding model."""
    adapter = SqliteAdapter(db_path=str(tmp_path / "memory.db"))
    assert adapter.vector_enabled is False  # confirms the FTS5-only default path
    return adapter


# ── entries: write -> search -> get -> update -> delete ────────────────────


def test_entry_round_trip_write_search_get(mem):
    w = mem.write(
        wing="work",
        room="decisions",
        content="The quarterly invoice reconciliation favored the vendor portal rollout.",
        topic="reconciliation",
    )
    assert w["success"] is True
    eid = w["id"]

    found = mem.search("invoice reconciliation vendor")
    assert found["count"] >= 1
    assert eid in [r["id"] for r in found["results"]]

    got = mem.get(eid)
    assert got["wing"] == "work"
    assert got["room"] == "decisions"
    assert "invoice reconciliation" in got["content"]


def test_entry_update_and_delete(mem):
    eid = mem.write(wing="work", room="notes", content="Original draft of the onboarding plan.")["id"]

    upd = mem.update(eid, content="Revised onboarding plan with a two-week ramp.")
    assert upd["success"] is True
    assert "two-week ramp" in mem.get(eid)["content"]
    # keyword search reflects the new content
    assert eid in [r["id"] for r in mem.search("revised onboarding ramp")["results"]]

    d = mem.delete(eid)
    assert d["success"] is True and d["deleted"] == 1
    assert mem.get(eid).get("success") is False  # gone


def test_search_empty_store_is_clean(mem):
    out = mem.search("nothing has been written yet")
    assert out["count"] == 0 and out["results"] == []


def test_write_rejects_obvious_noise(mem):
    # An empty entry is unambiguous mining noise; the write-time guard refuses it.
    r = mem.write(wing="work", room="notes", content="   ")
    assert r["success"] is False
    assert "noise" in r["error"].lower()


# ── diary: diary_write -> diary_read ───────────────────────────────────────


def test_diary_round_trip(mem):
    mem.diary_write(agent="test-agent", topic="build", content="Wired the adapter into the server.")
    mem.diary_write(agent="test-agent", topic="build", content="Added the offline fallback test.")

    read = mem.diary_read(agent="test-agent")
    assert read["agent"] == "test-agent"
    assert read["total"] == 2
    contents = [e["content"] for e in read["entries"]]
    assert "Wired the adapter into the server." in contents
    assert "Added the offline fallback test." in contents


def test_diary_is_per_agent(mem):
    mem.diary_write(agent="agent-a", topic="x", content="Entry for A.")
    mem.diary_write(agent="agent-b", topic="y", content="Entry for B.")
    assert mem.diary_read(agent="agent-a")["total"] == 1
    assert mem.diary_read(agent="agent-b")["total"] == 1


# ── relations: add_relation -> query_relations + closed-vocab guard ────────


def test_relation_round_trip(mem):
    r = mem.add_relation(subject="website relaunch", predicate="gated_on", object="copy review")
    assert r["success"] is True

    q = mem.query_relations(subject="website relaunch")
    assert q["count"] >= 1
    row = q["relations"][0]
    assert row["predicate"] == "gated_on"
    assert row["object"] == "copy review"
    assert row["status"] == "current"


def test_relation_guard_rejects_off_vocabulary_predicate(mem):
    r = mem.add_relation(subject="project atlas", predicate="relates to", object="project beacon")
    assert r["success"] is False
    assert "vocabulary" in r["error"].lower()
    # and nothing was written
    assert mem.query_relations(subject="project atlas")["count"] == 0


def test_relation_guard_rejects_overlong_object(mem):
    too_long = "x" * (OBJECT_MAX + 1)
    r = mem.add_relation(subject="project atlas", predicate="status", object=too_long)
    assert r["success"] is False
    assert str(OBJECT_MAX) in r["error"]
    assert mem.query_relations(subject="project atlas")["count"] == 0


def test_relation_predicate_remap_is_accepted(mem):
    # "gated_behind" is a known morphological variant of "gated_on".
    r = mem.add_relation(subject="launch", predicate="gated_behind", object="legal sign-off")
    assert r["success"] is True
    assert mem.query_relations(subject="launch")["relations"][0]["predicate"] == "gated_on"


# ── factory + status ───────────────────────────────────────────────────────


def test_factory_returns_sqlite_by_default(tmp_path):
    mem = create_adapter(db_path=str(tmp_path / "m.db"))
    assert mem.name == "sqlite"
    assert mem.vector_enabled is False  # FTS5-only by default (no embedder injected)


def test_factory_rejects_unbundled_postgres_backend():
    with pytest.raises(ValueError, match="not included"):
        create_adapter(backend="postgres")


def test_status_reports_counts(mem):
    mem.write(wing="work", room="decisions", content="A durable decision worth recalling later.")
    mem.diary_write(agent="test-agent", topic="t", content="A diary line.")
    mem.add_relation(subject="thing", predicate="status", object="done")

    s = mem.status()
    assert s["backend"] == "sqlite"
    assert s["vector_enabled"] is False
    assert s["total_drawers"] >= 1
    assert s["diary_entries"] >= 1
    assert s["relations"] >= 1
    assert s["healthy"] is True


# ── the embedder-injection seam ─────────────────────────────────────────────
#
# v1 ships NO embedder: the default adapter is FTS5 keyword-only. The seam lets a
# caller opt into semantic recall by injecting their own embedder (a callable
# str -> list[float]). The vector leg then engages iff sqlite-vec ALSO loads;
# otherwise it degrades cleanly to FTS5. This machine has no sqlite-vec, so the
# enable branch is driven deterministically with a fake connection + fake
# sqlite-vec, and the live-injection test asserts whichever branch this
# environment actually lands on.

EMBED_DIM = 8


def _fake_embedder(text: str) -> list:
    """A trivial deterministic embedder: hash the text into a fixed-dim vector.
    No model, no network — enough to exercise the seam and the vector leg."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    return [h[i % len(h)] / 255.0 for i in range(EMBED_DIM)]


class _FakeConn:
    """Stand-in for a sqlite3 connection whose build supports extension loading
    (this machine's real sqlite3 does not), so _resolve_vector_enabled can be
    driven past its platform gates deterministically."""

    def enable_load_extension(self, flag):
        return None


def _fake_sqlite_vec():
    return types.SimpleNamespace(load=lambda c: None, serialize_float32=lambda v: b"")


def test_default_adapter_is_fts5_only_and_round_trips(tmp_path):
    # No embedder injected -> FTS5-only, and a full write -> search -> get still
    # round-trips. This is the whole v1 store: no vector extension, no model.
    mem = create_adapter(db_path=str(tmp_path / "m.db"))
    assert mem.vector_enabled is False
    eid = mem.write(wing="work", room="decisions",
                    content="FTS5-only default: this keyword line must be recallable.")["id"]
    found = mem.search("keyword line recallable")
    assert eid in [r["id"] for r in found["results"]]
    assert "keyword line" in mem.get(eid)["content"]


def test_injected_embedder_enables_vector_iff_sqlite_vec_else_fts5(tmp_path):
    # Injecting an embedder opts into semantic recall. The vector leg engages only
    # if sqlite-vec is importable AND loadable in this Python; otherwise the same
    # injection cleanly stays on FTS5. Either way the round-trip must work — so
    # this passes offline (FTS5) and with sqlite-vec present (vector).
    mem = SqliteAdapter(db_path=str(tmp_path / "m.db"),
                        embedder=_fake_embedder, embed_dim=EMBED_DIM)
    assert isinstance(mem.vector_enabled, bool)
    if not sa._SQLITE_VEC_IMPORTABLE:
        assert mem.vector_enabled is False  # no sqlite-vec on this machine -> FTS5

    eid = mem.write(wing="work", room="notes",
                    content="Seam line: recallable whether we are on the vector or FTS5 leg.")["id"]
    found = mem.search("seam recallable vector fts5")
    assert eid in [r["id"] for r in found["results"]]
    assert mem.get(eid)["content"].startswith("Seam line")


def test_resolve_vector_enabled_when_embedder_injected_and_sqlite_vec_loads(tmp_path, monkeypatch):
    # Drive the enable branch deterministically offline: an injected embedder plus
    # a fake sqlite-vec that "loads" -> the vector leg resolves ON, and embed_dim
    # is inferred from a probe embedding (none was passed to the constructor).
    monkeypatch.setattr(sa, "_SQLITE_VEC_IMPORTABLE", True)
    monkeypatch.setattr(sa, "sqlite_vec", _fake_sqlite_vec())
    adapter = sa.SqliteAdapter(db_path=str(tmp_path / "m.db"), embedder=_fake_embedder)
    assert adapter._resolve_vector_enabled(_FakeConn()) is True
    assert adapter._embed_dim == EMBED_DIM  # inferred from the probe embedding


def test_resolve_stays_fts5_when_embedder_injected_but_no_sqlite_vec(tmp_path, monkeypatch):
    # An embedder is injected, but sqlite-vec is not importable -> degrade to FTS5
    # (no crash, no vector table). This is the offline default for a user who
    # wired an embedder but has not installed sqlite-vec.
    monkeypatch.setattr(sa, "_SQLITE_VEC_IMPORTABLE", False)
    adapter = sa.SqliteAdapter(db_path=str(tmp_path / "m.db"), embedder=_fake_embedder)
    assert adapter._resolve_vector_enabled(_FakeConn()) is False


def test_no_embedder_is_pure_fts5_resolve(tmp_path, monkeypatch):
    # The default: no embedder injected -> _resolve_vector_enabled is False even
    # if sqlite-vec were importable (the vector leg needs an embedder to compute a
    # vector at all).
    monkeypatch.setattr(sa, "_SQLITE_VEC_IMPORTABLE", True)
    monkeypatch.setattr(sa, "sqlite_vec", _fake_sqlite_vec())
    adapter = sa.SqliteAdapter(db_path=str(tmp_path / "m.db"))
    assert adapter._resolve_vector_enabled(_FakeConn()) is False


def test_write_degrades_to_fts_when_injected_embedder_fails_at_call_time(mem):
    """Defense-in-depth on the seam: if the vector leg is on but the injected
    embedder raises at write time, the write still succeeds via FTS5 (row stored +
    searchable) and the vector leg disables — no crash."""
    mem.conn  # connect + build schema (FTS-only: no vec table exists)
    mem._vector_enabled = True  # pretend the vector leg resolved on

    def _boom(text):
        raise RuntimeError("injected embedder blew up at call time")

    mem._embed_fn = _boom  # the injected seam, now failing at call time

    r = mem.write(
        wing="work",
        room="notes",
        content="Degrade path: store this keyword line even though the embed step fails.",
    )
    assert r["success"] is True         # no crash
    assert mem.vector_enabled is False  # vector leg disabled after the failure

    found = mem.search("degrade keyword store")
    assert r["id"] in [x["id"] for x in found["results"]]


def test_write_degrades_to_fts_when_vector_insert_fails(mem, monkeypatch):
    """The vector INSERT failing (not the embed call) — e.g. an embed_dim that does
    not match the vec0 width — must ALSO degrade: the embedding succeeds, the vec
    insert raises, and the FTS5 row must still be stored (not rolled back with the
    failed insert). This is the _upsert_vector_or_degrade guard; without it a vec
    failure inside the write transaction loses the whole entry."""
    mem.conn  # connect + build schema
    mem._vector_enabled = True       # pretend the vector leg resolved on
    mem._embed_fn = _fake_embedder   # embedding succeeds...

    def _boom(cur, rowid, embedding):
        raise RuntimeError("vec insert dimension mismatch (simulated)")

    monkeypatch.setattr(mem, "_upsert_vector", _boom)  # ...but the vec INSERT fails

    r = mem.write(
        wing="work",
        room="notes",
        content="Vec-insert degrade: store this keyword line even though the vector write fails.",
    )
    assert r["success"] is True         # no crash
    assert mem.vector_enabled is False  # vector leg disabled after the failure
    # the entry SURVIVED — the failed vec insert did not roll back the FTS5 row
    assert "keyword line" in mem.get(r["id"])["content"]
    found = mem.search("vec insert degrade keyword store")
    assert r["id"] in [x["id"] for x in found["results"]]


def test_embedder_seam_accepts_callable_encode_and_embed():
    # The documented seam: a plain callable, or an object exposing .encode
    # (sentence-transformers shape) or .embed (fastembed single-text shape). All
    # normalize to a flat list[float]; a numpy-like .tolist(), a one-shot
    # generator, and a batched [[...]] result are all coerced. No embedder (None)
    # stays the FTS5-only default; a non-embedder type fails loudly.
    class _Arr:  # numpy-like: exposes .tolist()
        def __init__(self, v):
            self._v = v

        def tolist(self):
            return self._v

    class _EncodeStyle:
        def encode(self, text):
            return _Arr([1.0, 2.0, 3.0])

    class _EmbedGenStyle:
        def embed(self, text):
            yield _Arr([4.0, 5.0])

    assert sa._coerce_embedder(lambda t: [0.1, 0.2])("x") == [0.1, 0.2]
    assert sa._coerce_embedder(_EncodeStyle())("x") == [1.0, 2.0, 3.0]
    assert sa._coerce_embedder(_EmbedGenStyle())("x") == [4.0, 5.0]
    assert sa._to_vector([[7.0, 8.0]]) == [7.0, 8.0]  # batched 2-D -> first row
    assert sa._coerce_embedder(None) is None          # FTS5-only default
    with pytest.raises(TypeError):
        sa._coerce_embedder(12345)                    # not callable / no method


# ── fix #3: query_relations(as_of=<date-only>) includes same-day relations ──


def test_query_relations_as_of_date_only_includes_same_day(mem):
    # valid_from is stored as a full microsecond timestamp; a date-only as_of used
    # to drop the row via raw string compare ("...T14:30..." <= "2026-07-19" False).
    mem.add_relation(
        subject="alpha project",
        predicate="status",
        object="in review",
        valid_from="2026-07-19T14:30:00.000000+00:00",
    )

    q = mem.query_relations(subject="alpha project", as_of="2026-07-19")
    assert q["count"] == 1
    assert q["relations"][0]["object"] == "in review"

    # a full-timestamp as_of is compared as-is (behavior unchanged)
    q2 = mem.query_relations(
        subject="alpha project", as_of="2026-07-19T23:59:00.000000+00:00"
    )
    assert q2["count"] == 1

    # and it is current with no as_of filter at all
    assert mem.query_relations(subject="alpha project")["count"] == 1


# ── fix #6: diary_read canonicalizes its wing filter, mirroring diary_write ──


def test_diary_read_canonicalizes_wing_filter(mem):
    # diary_write stores canonical_wing("My Work") == "my_work"; diary_read must
    # canonicalize its filter too, or the mixed-case wing is unreachable.
    mem.diary_write(
        agent="wtest", topic="t", content="Wing-filtered diary line.", wing="My Work"
    )
    got = mem.diary_read(agent="wtest", wing="My Work")
    assert got["total"] == 1
    assert got["entries"][0]["content"] == "Wing-filtered diary line."


# ── fix #5: the example alias file does not pollute the canon map when copied ──


def test_example_alias_file_does_not_pollute_map(monkeypatch):
    # Users are told to copy entity_aliases.example.json. Its "_comment" string
    # value must not be iterated character-by-character into junk single-char
    # surfaces (including the empty string), all mapping to "comment".
    example = Path(canon.__file__).resolve().parent / "entity_aliases.example.json"
    assert example.exists()
    monkeypatch.setenv("MEMORY_ALIAS_EXTRA", str(example))
    try:
        amap = canon.alias_map(reload=True)
        assert "" not in amap                              # no empty-string surface
        assert "comment" not in amap                       # no _comment canonical
        assert all(v != "comment" for v in amap.values())  # nothing maps to it
        # the real aliases still load — the guard did not over-reject
        assert amap.get("acme") == "acme corp"
        assert amap.get("the client") == "acme corp"
    finally:
        monkeypatch.delenv("MEMORY_ALIAS_EXTRA", raising=False)
        canon.alias_map(reload=True)  # restore the default (empty) cached map
