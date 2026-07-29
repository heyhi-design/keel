"""SqliteAdapter — a zero-server local backend for agent memory.

A single-file ``memory.db``, no server process, no setup at all in its default
mode. This is the reference implementation of the Tier-2 shape described in
``docs/memory.md``: durable recall that does not ask you to stand up Postgres. It
implements the same ``MemoryAdapter`` contract (``base.py``) that a Postgres
backend would, so a caller cannot tell two backends apart except by
search-ranking quality — swapping is a configuration change, not a rewrite.

Default (v1): FTS5 keyword recall only. SQLite's own tokenized full-text index,
built into every modern SQLite — no extension, no model, no network, nothing to
install. This is the whole store out of the box: keyword search over everything
written, fully offline.

Optional semantic follow-on: pass your own embedder into the constructor
(``embedder=...``, ``embed_dim=...``) and, if ``sqlite-vec`` is installed and
loadable, the adapter additionally maintains a ``vec0`` virtual table (cosine
distance, brute-force KNN — fine below ~1M vectors, and a personal store is
nowhere near that scale) and fuses vector recall with the keyword leg. No
embedder is shipped in-tree: you inject an Apache-2.0 (or any-licensed) model
such as ``fastembed``. The injectable seam is a callable ``str -> list[float]``
(or an object exposing ``.embed`` / ``.encode``); see ``_coerce_embedder`` and
``memory/README.md``. ``sqlite-vec`` is PRE-v1 (0.x) and its API can break
between releases, so if you install it, pin it (see ``requirements.txt``).

Degrade, never crash: the vector leg engages only when BOTH an embedder is
injected AND ``sqlite-vec`` loads in the current Python's sqlite3 build. If no
embedder is injected (the default), or ``sqlite-vec`` is absent, or the extension
cannot load — the documented case is Apple's bundled macOS Python, which ships
with ``enable_load_extension`` unavailable entirely — the adapter runs pure FTS5
keyword search rather than raising. That degrade is logged once, not hidden.

Hybrid ranking, when both legs are available, is Reciprocal Rank Fusion
(rank-based, not raw-score blending) — sum of 1/(K+rank) per leg, summed per
candidate id. What is *stored* and *rejected* is identical whether or not the
vector leg is present; the vector leg additionally surfaces semantic near-matches
keyword search alone would not, so returned results can differ in membership and
order.

Write-time guards: ``mining_filter.classify()`` (rejects mining noise on
entries) and ``vocab.prepare_relation()`` (the closed predicate vocabulary and
128-char object cap on relations) are shared, backend-neutral modules, so any
other backend that imports them enforces the same rules by construction.

Concurrency: SQLite's own ``journal_mode=WAL`` allows multiple readers
alongside one writer; this class also serializes its own callers with a
``threading.RLock`` for defense-in-depth, which only matters if the adapter is
driven from more than one thread in-process.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from . import canon, vocab
from .base import MemoryAdapter, Result

# The mining-noise write-time guard. Shared, backend-neutral: any backend that
# imports it rejects the same entry-level noise by construction, not by parallel
# maintenance.
from . import mining_filter

logger = logging.getLogger("memory.sqlite")

# sqlite-vec is an OPTIONAL runtime dependency: the adapter module must import
# cleanly even when the package is absent (a fresh user who hasn't
# `pip install sqlite-vec`'d yet, or a system Python whose sqlite3 cannot load
# extensions — see _resolve_vector_enabled). A top-level `import sqlite_vec`
# would crash the whole module on any environment missing the package, which
# would break even the FTS5-only fallback mode — the one thing this adapter must
# never do.
try:
    import sqlite_vec

    _SQLITE_VEC_IMPORTABLE = True
except ImportError:  # pragma: no cover - exercised by the FTS5-fallback test
    sqlite_vec = None  # type: ignore[assignment]
    _SQLITE_VEC_IMPORTABLE = False

# PINNED: sqlite-vec is pre-v1 (0.x) and its author has stated the API may
# break between releases without a deprecation window. Bump this deliberately,
# re-run the adapter test suite (especially the KNN query syntax probe —
# `WHERE embedding MATCH ? AND k = ?` — and `distance_metric=cosine` table
# option support), and update this comment with the date and what changed.
SQLITE_VEC_PINNED_VERSION = "0.1.9"

DEFAULT_DB_PATH = os.environ.get(
    "MEMORY_SQLITE_PATH", os.path.expanduser("~/.keel/memory.db")
)
RRF_K = 60
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _fts5_match_expr(query: str) -> str | None:
    """Build a safe FTS5 MATCH expression: OR of individually-quoted word
    tokens. Each token is `\\w+` (no quotes, spaces, or FTS5 operator
    characters can appear inside one), so wrapping it in double quotes makes
    it a literal phrase token that cannot be misparsed as a MATCH operator —
    this is what keeps arbitrary user query text (hyphens, colons, unbalanced
    quotes, boolean-looking words) from ever raising a syntax error."""
    tokens = _TOKEN_RE.findall(query or "")
    if not tokens:
        return None
    return " OR ".join(f'"{t}"' for t in tokens)


# The injected-embedder seam. No embedder ships in this reference cut: v1 is
# FTS5 keyword recall only. The semantic follow-on is opt-in — the caller injects
# their own model (e.g. Apache-2.0 ``fastembed``) via the constructor. This keeps
# the adapter free of any bundled model and its licensing questions.
#
# An injected embedder is either a plain callable ``str -> Sequence[float]`` or an
# object exposing a ``.embed`` or ``.encode`` method of that shape.
EmbedderLike = Any


def _to_vector(out: Any) -> "list[float]":
    """Coerce an embedder's output into a flat ``list[float]``. Accepts a plain
    sequence, a numpy vector (``.tolist()``), a one-shot iterator/generator of
    vectors (fastembed's ``.embed`` — the first vector is taken), or an
    already-batched ``[[...]]`` result (the first row is taken)."""
    # A one-shot iterator/generator of vectors (e.g. fastembed) -> first vector.
    if not isinstance(out, (list, tuple, bytes, str)) and not hasattr(out, "tolist"):
        if hasattr(out, "__iter__") or hasattr(out, "__next__"):
            try:
                out = next(iter(out))
            except StopIteration as exc:
                raise ValueError("the injected embedder returned no vector") from exc
    # numpy array (or anything with .tolist()) -> nested python lists
    if hasattr(out, "tolist"):
        out = out.tolist()
    # a batched 2-D result [[...]] -> first row
    if isinstance(out, (list, tuple)) and out and isinstance(out[0], (list, tuple)):
        out = out[0]
    return [float(x) for x in out]


def _coerce_embedder(embedder: "EmbedderLike | None"):
    """Normalize an injected embedder into a uniform ``str -> list[float]``
    callable, or return ``None`` when no embedder is injected (the FTS5-only
    default). A plain callable is used directly; an object is adapted via its
    ``.embed`` or ``.encode`` method. Anything else raises ``TypeError`` at
    construction so a misconfigured seam fails loudly, not on the first write."""
    if embedder is None:
        return None
    if callable(embedder):
        raw = embedder
    elif hasattr(embedder, "embed"):
        raw = embedder.embed
    elif hasattr(embedder, "encode"):
        raw = embedder.encode
    else:
        raise TypeError(
            "embedder must be callable or expose an .embed/.encode method; "
            f"got {type(embedder).__name__}"
        )

    def _embed(text: str) -> "list[float]":
        return _to_vector(raw(text))

    return _embed


class SqliteAdapter(MemoryAdapter):
    name = "sqlite"

    def __init__(self, db_path: str = DEFAULT_DB_PATH,
                 embedder: "EmbedderLike | None" = None, embed_dim: int | None = None):
        """`embedder`: an optional, caller-supplied embedding function — a
        callable ``str -> list[float]``, or an object exposing ``.embed`` /
        ``.encode`` of that shape. Default ``None`` ⇒ FTS5 keyword search only:
        no vector table, no embedding calls, no dependency beyond the stdlib
        ``sqlite3``. Inject one to opt into the semantic follow-on; the vector
        leg then engages iff ``sqlite-vec`` also loads, and degrades to FTS5
        otherwise (logged once). No embedder ships in-tree — bring your own
        (e.g. Apache-2.0 ``fastembed``). `embed_dim`: the embedder's output
        dimension, used to size the ``vec0`` table. Optional — when omitted while
        an embedder is injected, it is inferred once from a probe embedding at
        connect time."""
        self.db_path = db_path
        self._embed_fn = _coerce_embedder(embedder)
        self._embed_dim = int(embed_dim) if embed_dim else None
        self._conn: sqlite3.Connection | None = None
        self._vector_enabled: bool | None = None  # resolved lazily on first .conn access
        self._lock = threading.RLock()

    # --- infra ---------------------------------------------------------
    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            parent = os.path.dirname(self.db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            c = sqlite3.connect(self.db_path, check_same_thread=False)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=5000")
            c.execute("PRAGMA foreign_keys=ON")
            self._vector_enabled = self._resolve_vector_enabled(c)
            self._conn = c
            self._init_schema()
        return self._conn

    @property
    def vector_enabled(self) -> bool:
        self.conn  # trigger lazy resolution if not yet connected
        return bool(self._vector_enabled)

    def _resolve_vector_enabled(self, c: sqlite3.Connection) -> bool:
        """Enabled iff an embedder was injected AND sqlite-vec loads in this
        Python. The v1 default (no embedder) is FTS5 keyword search only. Any
        failure degrades to FTS5, logged once — the adapter never raises here."""
        # No embedder injected -> FTS5-only. This is the default and the whole
        # v1 story: nothing to install, nothing to download, fully offline.
        if self._embed_fn is None:
            logger.info("sqlite adapter: no embedder injected — FTS5 keyword search only")
            return False
        # An embedder is present; the vector leg additionally needs sqlite-vec.
        if not _SQLITE_VEC_IMPORTABLE:
            logger.warning(
                "an embedder was injected but the sqlite-vec package is not "
                "installed; falling back to FTS5 keyword search"
            )
            return False
        if not hasattr(c, "enable_load_extension"):
            logger.warning(
                "an embedder was injected but this Python's sqlite3 build has no "
                "enable_load_extension (common on Apple's bundled macOS Python); "
                "falling back to FTS5 keyword search"
            )
            return False
        try:
            c.enable_load_extension(True)
            sqlite_vec.load(c)
            c.enable_load_extension(False)
        except Exception as exc:
            try:
                c.enable_load_extension(False)
            except Exception:
                pass
            logger.warning(
                "sqlite-vec extension failed to load (%s: %s); falling back to "
                "FTS5 keyword search", type(exc).__name__, exc,
            )
            return False

        # sqlite-vec is loaded and an embedder is present. Resolve the embedding
        # dimension: use the injected embed_dim if given, else infer it once from
        # a single probe embedding (the vec0 table needs a fixed width at creation
        # time). A probe failure degrades to FTS5 rather than crashing.
        if self._embed_dim is None:
            try:
                self._embed_dim = len(self._embed_fn("dimension probe"))
            except Exception as exc:
                logger.warning(
                    "the injected embedder failed to produce a probe embedding "
                    "(%s: %s); falling back to FTS5 keyword search",
                    type(exc).__name__, exc,
                )
                return False
        if not self._embed_dim or self._embed_dim <= 0:
            logger.warning(
                "could not determine a positive embedding dimension; falling back "
                "to FTS5 keyword search"
            )
            return False
        return True

    def _init_schema(self) -> None:
        c = self._conn
        assert c is not None
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory_entries (
                id          TEXT PRIMARY KEY,
                kind        TEXT NOT NULL DEFAULT 'entry',
                wing        TEXT,
                room        TEXT,
                topic       TEXT,
                agent       TEXT,
                content     TEXT NOT NULL,
                tags        TEXT,
                source_file TEXT,
                chunk_index INTEGER,
                embed_model TEXT,  -- reserved: which model embedded a row; NULL in FTS5-only v1, set by the semantic follow-on
                entry_date  TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS memory_entries_wing_room ON memory_entries(wing, room);
            CREATE INDEX IF NOT EXISTS memory_entries_diary ON memory_entries(kind, agent, created_at);

            CREATE VIRTUAL TABLE IF NOT EXISTS memory_entries_fts USING fts5(
                content, content='memory_entries', content_rowid='rowid'
            );
            CREATE TRIGGER IF NOT EXISTS memory_entries_ai AFTER INSERT ON memory_entries BEGIN
                INSERT INTO memory_entries_fts(rowid, content) VALUES (new.rowid, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS memory_entries_ad AFTER DELETE ON memory_entries BEGIN
                INSERT INTO memory_entries_fts(memory_entries_fts, rowid, content) VALUES('delete', old.rowid, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS memory_entries_au AFTER UPDATE ON memory_entries BEGIN
                INSERT INTO memory_entries_fts(memory_entries_fts, rowid, content) VALUES('delete', old.rowid, old.content);
                INSERT INTO memory_entries_fts(rowid, content) VALUES (new.rowid, new.content);
            END;

            CREATE TABLE IF NOT EXISTS memory_relations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                subject     TEXT NOT NULL,
                predicate   TEXT NOT NULL,
                object      TEXT NOT NULL,
                confidence  REAL,
                valid_from  TEXT NOT NULL,
                valid_to    TEXT,
                source      TEXT,
                created_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS memory_relations_subject_current
                ON memory_relations(subject) WHERE valid_to IS NULL;
            CREATE INDEX IF NOT EXISTS memory_relations_object_current
                ON memory_relations(object) WHERE valid_to IS NULL;

            CREATE TABLE IF NOT EXISTS memory_links (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source_wing TEXT, source_room TEXT, source_id TEXT,
                target_wing TEXT, target_room TEXT, target_id TEXT,
                label       TEXT,
                created_at  TEXT NOT NULL
            );
            """
        )
        if self._vector_enabled:
            c.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS memory_entries_vec "
                f"USING vec0(embedding float[{self._embed_dim}] distance_metric=cosine)"
            )
        c.commit()

    @contextmanager
    def _tx(self):
        with self._lock:
            cur = self.conn.cursor()
            try:
                yield cur
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
            finally:
                cur.close()

    @staticmethod
    def _mkid(*parts: Any) -> str:
        h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
        return f"d_{h[:24]}"

    @staticmethod
    def _filter_sql(wing, room, alias="") -> tuple[str, list]:
        a = f"{alias}." if alias else ""
        clauses, params = [], []
        if wing:
            clauses.append(f"{a}wing = ?")
            params.append(wing)
        if room:
            clauses.append(f"{a}room = ?")
            params.append(room)
        return (" AND " + " AND ".join(clauses) if clauses else ""), params

    def _upsert_vector(self, cur: sqlite3.Cursor, rowid: int, embedding: list[float]) -> None:
        cur.execute("DELETE FROM memory_entries_vec WHERE rowid=?", (rowid,))
        cur.execute(
            "INSERT INTO memory_entries_vec(rowid, embedding) VALUES (?, ?)",
            (rowid, sqlite_vec.serialize_float32(embedding)),
        )

    def _upsert_vector_or_degrade(self, cur: sqlite3.Cursor, rowid: int,
                                  embedding: list[float]) -> None:
        """Insert the embedding into the vec table, degrading to FTS5 rather than
        aborting the surrounding write if the insert itself fails — e.g. an
        embed_dim that does not match the vec0 table width, or a corrupt vec
        table. _embed_or_degrade guards the embedding *call*; this guards the
        vector *INSERT*. The FTS5 row is already written in this same transaction
        and must survive, so the failure is swallowed here (the entry commits) and
        the vector leg is disabled for the rest of this process, logged once."""
        try:
            self._upsert_vector(cur, rowid, embedding)
        except Exception as exc:
            if self._vector_enabled:
                logger.warning(
                    "the vector insert failed (%s: %s); disabling the vector leg "
                    "and keeping the entry via FTS5 keyword search",
                    type(exc).__name__, exc,
                )
            self._vector_enabled = False

    def _embed_or_degrade(self, text: str) -> list[float] | None:
        """Compute an embedding via the injected embedder, degrading to FTS5
        rather than crashing if it fails at call time. Defense-in-depth behind
        the connect-time resolution in _resolve_vector_enabled: if the vector leg
        resolved on but embedding still fails later, a write must still store the
        row and a search must still return keyword results. Returns the embedding,
        or None on failure (or when no embedder is injected) — in which case the
        vector leg is disabled for the rest of this process and the caller falls
        back to FTS5. The 'disabled' warning is logged once, on the transition."""
        if self._embed_fn is None:
            return None
        try:
            return self._embed_fn(text)
        except Exception as exc:
            if self._vector_enabled:
                logger.warning(
                    "the injected embedder failed at call time (%s: %s); disabling "
                    "the vector leg and continuing with FTS5 keyword search",
                    type(exc).__name__, exc,
                )
            self._vector_enabled = False
            return None

    # --- entries ---------------------------------------------------------
    def write(self, wing, room, content, id=None, topic=None, tags=None,
              source_file=None, chunk_index=None) -> Result:
        is_noise, reason = mining_filter.classify(content, source_file)
        if is_noise:
            return {"success": False, "error": (
                f"rejected: content classifies as mining noise ({reason}); "
                f"if this is a genuine fact, write it as prose with the fact "
                f"stated, not a bare fragment")}
        eid = id or self._mkid(wing, room, chunk_index, content)
        now = _now_iso()
        tags_json = json.dumps(tags) if tags is not None else None
        with self._tx() as cur:
            cur.execute(
                """
                INSERT INTO memory_entries
                    (id, kind, wing, room, topic, content, tags, source_file,
                     chunk_index, created_at, updated_at)
                VALUES (?, 'entry', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    wing = excluded.wing, room = excluded.room, topic = excluded.topic,
                    content = excluded.content, tags = excluded.tags,
                    source_file = excluded.source_file, chunk_index = excluded.chunk_index,
                    updated_at = excluded.updated_at
                """,
                (eid, wing, room, topic, content, tags_json, source_file,
                 chunk_index, now, now),
            )
            if self.vector_enabled:
                emb = self._embed_or_degrade(content)
                if emb is not None:
                    rowid = cur.execute("SELECT rowid FROM memory_entries WHERE id=?", (eid,)).fetchone()[0]
                    self._upsert_vector_or_degrade(cur, rowid, emb)
        return {"success": True, "id": eid, "backend": self.name}

    def search(self, query, wing=None, room=None, k=5, filters=None) -> Result:
        k = int(k or 5)
        over = max(k * 4, 20)
        fsql, fparams = self._filter_sql(wing, room)
        with self._tx() as cur:
            semantic_ranks: dict[str, int] = {}
            q_vec = self._embed_or_degrade(query) if self.vector_enabled else None
            if q_vec is not None:
                qemb = sqlite_vec.serialize_float32(q_vec)
                vec_rows = cur.execute(
                    "SELECT rowid, distance FROM memory_entries_vec "
                    "WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                    (qemb, over),
                ).fetchall()
                if vec_rows:
                    rowids = [r[0] for r in vec_rows]
                    placeholders = ",".join("?" * len(rowids))
                    id_rows = cur.execute(
                        f"SELECT rowid, id FROM memory_entries WHERE rowid IN ({placeholders}) {fsql}",
                        [*rowids, *fparams],
                    ).fetchall()
                    rowid_to_id = {r[0]: r[1] for r in id_rows}
                    for rank, (rid, _dist) in enumerate(vec_rows, start=1):
                        eid = rowid_to_id.get(rid)
                        if eid:
                            semantic_ranks[eid] = rank

            lexical_ranks: dict[str, int] = {}
            match_expr = _fts5_match_expr(query)
            if match_expr:
                fsql_e, fparams_e = self._filter_sql(wing, room, alias="e")
                try:
                    lex_rows = cur.execute(
                        f"SELECT e.id FROM memory_entries_fts f "
                        f"JOIN memory_entries e ON e.rowid = f.rowid "
                        f"WHERE memory_entries_fts MATCH ? {fsql_e} "
                        f"ORDER BY rank LIMIT ?",
                        [match_expr, *fparams_e, over],
                    ).fetchall()
                except sqlite3.OperationalError as exc:
                    logger.warning("FTS5 query failed (%s); returning vector-only results", exc)
                    lex_rows = []
                for rank, (eid,) in enumerate(lex_rows, start=1):
                    lexical_ranks[eid] = rank

            all_ids = set(semantic_ranks) | set(lexical_ranks)
            scored = []
            for eid in all_ids:
                score = 0.0
                if eid in semantic_ranks:
                    score += 1.0 / (RRF_K + semantic_ranks[eid])
                if eid in lexical_ranks:
                    score += 1.0 / (RRF_K + lexical_ranks[eid])
                scored.append((eid, score))
            scored.sort(key=lambda x: -x[1])
            top = scored[:k]
            if not top:
                return {"query": query, "count": 0, "results": []}
            top_ids = [eid for eid, _ in top]
            placeholders = ",".join("?" * len(top_ids))
            rows = cur.execute(
                f"SELECT id, wing, room, topic, kind, content FROM memory_entries "
                f"WHERE id IN ({placeholders})",
                top_ids,
            ).fetchall()
        by_id = {r[0]: r for r in rows}
        score_map = dict(top)
        results = []
        for eid in top_ids:
            r = by_id.get(eid)
            if not r:
                continue
            results.append({"id": r[0], "wing": r[1], "room": r[2], "topic": r[3],
                             "kind": r[4], "content": r[5], "score": score_map[eid]})
        return {"query": query, "count": len(results), "results": results}

    def get(self, id) -> Result:
        with self._tx() as cur:
            row = cur.execute(
                "SELECT id, kind, wing, room, topic, content, tags, source_file, "
                "chunk_index, created_at, updated_at FROM memory_entries WHERE id=?",
                (id,),
            ).fetchone()
        if not row:
            return {"success": False, "error": f"Entry not found: {id}"}
        tags = json.loads(row[6]) if row[6] else None
        return {"id": row[0], "kind": row[1], "wing": row[2], "room": row[3], "topic": row[4],
                "content": row[5], "tags": tags, "source_file": row[7], "chunk_index": row[8],
                "created_at": row[9], "updated_at": row[10]}

    def list(self, wing=None, room=None, limit=20, offset=0) -> Result:
        fsql, fparams = self._filter_sql(wing, room)
        with self._tx() as cur:
            rows = cur.execute(
                f"SELECT id, wing, room, topic, kind, substr(content,1,160) "
                f"FROM memory_entries WHERE kind='entry' {fsql} "
                f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [*fparams, int(limit), int(offset)],
            ).fetchall()
        return {"count": len(rows), "entries": [
            {"id": r[0], "wing": r[1], "room": r[2], "topic": r[3], "preview": r[5]} for r in rows]}

    def update(self, id, content=None, wing=None, room=None, tags=None) -> Result:
        sets, params = [], []
        new_emb: list[float] | None = None
        if content is not None:
            is_noise, reason = mining_filter.classify(content)
            if is_noise:
                return {"success": False, "error": (
                    f"rejected: content classifies as mining noise ({reason}); "
                    f"if this is a genuine fact, write it as prose with the fact "
                    f"stated, not a bare fragment")}
            sets.append("content=?")
            params.append(content)
        if wing is not None:
            sets.append("wing=?"); params.append(wing)
        if room is not None:
            sets.append("room=?"); params.append(room)
        if tags is not None:
            sets.append("tags=?"); params.append(json.dumps(tags))
        if not sets:
            return {"success": True, "id": id, "noop": True}
        sets.append("updated_at=?")
        params.append(_now_iso())
        params.append(id)
        with self._tx() as cur:
            cur.execute(f"UPDATE memory_entries SET {', '.join(sets)} WHERE id=?", params)
            n = cur.rowcount
            if n and content is not None and self.vector_enabled:
                new_emb = self._embed_or_degrade(content)
                if new_emb is not None:
                    row = cur.execute("SELECT rowid FROM memory_entries WHERE id=?", (id,)).fetchone()
                    if row:
                        self._upsert_vector_or_degrade(cur, row[0], new_emb)
        return {"success": n > 0, "id": id} if n else {"success": False, "error": f"Not found: {id}"}

    def delete(self, id) -> Result:
        with self._tx() as cur:
            row = cur.execute("SELECT rowid FROM memory_entries WHERE id=?", (id,)).fetchone()
            if not row:
                return {"success": False, "id": id, "deleted": 0}
            rowid = row[0]
            if self.vector_enabled:
                cur.execute("DELETE FROM memory_entries_vec WHERE rowid=?", (rowid,))
            cur.execute("DELETE FROM memory_entries WHERE id=?", (id,))
            n = cur.rowcount
        return {"success": n > 0, "id": id, "deleted": n}

    # --- diary -------------------------------------------------------------
    def diary_write(self, agent, topic, content, date=None, wing=None) -> Result:
        agent = vocab.canonical_agent(agent)
        wing = vocab.canonical_wing(wing) or f"wing_{agent}"
        eid = self._mkid("diary", agent, topic, content)
        now = _now_iso()
        entry_date = date or _today_iso()
        with self._tx() as cur:
            cur.execute(
                """
                INSERT INTO memory_entries
                    (id, kind, wing, room, topic, agent, content, entry_date,
                     created_at, updated_at)
                VALUES (?, 'diary', ?, 'diary', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at
                """,
                (eid, wing, topic, agent, content, entry_date, now, now),
            )
            if self.vector_enabled:
                emb = self._embed_or_degrade(content)
                if emb is not None:
                    rowid = cur.execute("SELECT rowid FROM memory_entries WHERE id=?", (eid,)).fetchone()[0]
                    self._upsert_vector_or_degrade(cur, rowid, emb)
        return {"success": True, "id": eid, "agent": agent}

    def diary_read(self, agent="default-agent", limit=10, since=None, wing=None) -> Result:
        agent = vocab.canonical_agent(agent)
        # diary_write stores the canonicalized wing (vocab.canonical_wing), so the
        # read filter must canonicalize too — otherwise diary_write(wing="My Work")
        # (stored "my_work") is unreachable via diary_read(wing="My Work").
        wing = vocab.canonical_wing(wing) if wing else None
        clauses = ["kind='diary'", "agent=?"]
        params: list[Any] = [agent]
        if since:
            clauses.append("entry_date >= ?"); params.append(since)
        if wing:
            clauses.append("wing=?"); params.append(wing)
        params.append(int(limit))
        with self._tx() as cur:
            rows = cur.execute(
                f"SELECT entry_date, topic, content, created_at FROM memory_entries "
                f"WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
        entries = [{"date": r[0], "topic": r[1], "content": r[2], "timestamp": r[3]}
                   for r in reversed(rows)]
        return {"agent": agent, "total": len(entries), "entries": entries}

    # --- knowledge graph ---------------------------------------------------
    def add_relation(self, subject, predicate, object, confidence=None,
                     valid_from=None, valid_to=None, source=None) -> Result:
        # Same normalization + validation any backend uses (vocab is
        # backend-neutral) — an off-vocabulary predicate or an over-long object
        # is rejected identically wherever this guard is imported.
        subject, predicate, object, err = vocab.prepare_relation(subject, predicate, object)
        if err:
            return {"success": False, "error": err}
        now = _now_iso()
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO memory_relations "
                "(subject, predicate, object, confidence, valid_from, valid_to, source, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (subject, predicate, object, confidence, valid_from or now, valid_to, source, now),
            )
            rid = cur.lastrowid
        return {"success": True, "id": rid}

    def query_relations(self, subject=None, predicate=None, object=None,
                        as_of=None, direction="both") -> Result:
        """Subject/object match on canon.canonical() of both sides, so an alias
        surface form finds the canonicalized row."""
        clauses, params = [], []
        if predicate:
            clauses.append("predicate=?"); params.append(predicate)
        if as_of:
            # valid_from / valid_to are stored as full microsecond timestamps
            # ("2026-07-19T14:..."), so a raw string compare against a date-only
            # as_of ("2026-07-19") drops same-day relations: the string
            # "2026-07-19T14:..." <= "2026-07-19" is False. Expand a date-only
            # as_of to end-of-day so a relation that became valid earlier that day
            # is included; a full-timestamp as_of is compared as-is. Both halves
            # use the same expanded value to stay consistent.
            as_of_cmp = as_of
            if len(as_of) == 10 and "T" not in as_of:
                as_of_cmp = as_of + "T23:59:59.999999"
            clauses.append("valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)")
            params += [as_of_cmp, as_of_cmp]
        else:
            clauses.append("valid_to IS NULL")
        where = " AND ".join(clauses) if clauses else "1=1"
        cols = "id, subject, predicate, object, confidence, valid_from, valid_to, source"
        limit = 200 if not subject and not object else 5000
        with self._tx() as cur:
            rows = cur.execute(
                f"SELECT {cols} FROM memory_relations WHERE {where} "
                f"ORDER BY valid_from DESC LIMIT ?",
                [*params, limit],
            ).fetchall()
        if subject or object:
            cs = canon.canonical(subject) if subject else None
            co = canon.canonical(object) if object else None
            rows = [r for r in rows
                    if (cs is None or canon.canonical(r[1]) == cs)
                    and (co is None or canon.canonical(r[3]) == co)][:200]
        return {"count": len(rows), "relations": [
            {"id": r[0], "subject": r[1], "predicate": r[2], "object": r[3], "confidence": r[4],
             "valid_from": r[5], "valid_to": r[6],
             "status": "current" if r[6] is None else "retired", "source": r[7]}
            for r in rows]}

    def link(self, source_wing, source_room, target_wing, target_room,
             label="", source_id=None, target_id=None) -> Result:
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO memory_links "
                "(source_wing, source_room, source_id, target_wing, target_room, target_id, label, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (source_wing, source_room, source_id, target_wing, target_room, target_id,
                 label, _now_iso()),
            )
            lid = cur.lastrowid
        return {"success": True, "id": lid}

    # --- health --------------------------------------------------------
    def status(self) -> Result:
        with self._tx() as cur:
            entries = cur.execute("SELECT count(*) FROM memory_entries WHERE kind='entry'").fetchone()[0]
            diary = cur.execute("SELECT count(*) FROM memory_entries WHERE kind='diary'").fetchone()[0]
            rels = cur.execute("SELECT count(*) FROM memory_relations").fetchone()[0]
            wing_rows = cur.execute(
                "SELECT wing, count(*) FROM memory_entries WHERE kind='entry' "
                "GROUP BY wing ORDER BY count(*) DESC"
            ).fetchall()
        wings = {w or "(none)": c for w, c in wing_rows}
        return {"backend": self.name, "db_path": self.db_path, "total_drawers": entries,
                "diary_entries": diary, "relations": rels, "wings": wings, "healthy": True,
                "vector_enabled": self.vector_enabled}
