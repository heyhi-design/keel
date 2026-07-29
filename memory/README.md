# memory: a reference adapter for semantic recall

This folder is the **Tier 2** backend described in [`../docs/memory.md`](../docs/memory.md):
a single-file [SQLite](https://sqlite.org) store that gives your agent recall by
meaning, behind one stable interface. It is optional. The scaffold's file-based
Tier 1 (your corrections registry and decision log) needs none of this; reach
for the adapter when you find yourself wishing you could search past sessions by
what they were about rather than by which file they live in.

It is a **reference implementation**, not a service. You bring the runtime (an
MCP server, or any process that imports Python) and own the configuration; this
adapter is the bridge between them. That is Layer 1 of the three-layer model
applied one level down: nothing that calls the memory tools names a backend, so
moving from SQLite to Postgres later is a configuration change, not a rewrite.

## What is in here

| File | Role |
|---|---|
| `base.py` | `MemoryAdapter`: the interface every backend implements. |
| `sqlite_adapter.py` | `SqliteAdapter`: the SQLite backend — FTS5 keyword recall by default, optional sqlite-vec vector leg via an injected embedder. |
| `embedders/fastembed_embedder.py` | `FastEmbedEmbedder`: the reference embedder for the optional semantic follow-on (fastembed, Apache-2.0). Not imported unless you use it. |
| `factory.py` | `create_adapter()`: pick a backend by name in one place. |
| `vocab.py` | The closed knowledge-graph predicate vocabulary and diary canonicalization. |
| `canon.py` | Entity canonicalization (optional alias map). |
| `mining_filter.py` | A high-precision write-time noise guard. |
| `entity_aliases.example.json` | Shape example for the optional alias map. |
| `requirements.txt` | Optional dependencies for the semantic follow-on. |

## Install

The adapter is opt-in, and its **v1 default needs nothing installed**: it runs on
Python's built-in `sqlite3` and FTS5 keyword search, fully offline. That is the
whole store out of the box — enough to use it for real.

**Semantic recall is an optional follow-on, and it is not shipped in-tree.** To
add it you supply two pieces yourself (see [`requirements.txt`](requirements.txt)):

- **A vector index.** `pip install sqlite-vec` (pin it — it is pre-v1 and its API
  can break between releases).
- **An embedding model.** No model is bundled. The reference choice is
  `pip install fastembed` ([Apache-2.0](https://github.com/qdrant/fastembed)), a
  small, local, torch-free embedder, wrapped for you by the shipped
  `FastEmbedEmbedder` ([`embedders/fastembed_embedder.py`](embedders/fastembed_embedder.py)) —
  or wire any embedder into the injection seam yourself (below).

If no embedder is injected (the default), or `sqlite-vec` is absent, or the
current Python's `sqlite3` cannot load extensions (Apple's bundled macOS Python
is the documented case), the adapter runs **FTS5 keyword search** rather than
failing. Any degrade is logged once. What is *stored* and *rejected* is identical
either way; the vector leg additionally surfaces semantic near-matches keyword
search alone would not, so returned results can differ in membership and order.
One FTS5 nuance: the keyword leg ORs the query's tokens with no stop-word list, so
a match can rest on a common word alone. Results do carry scores, and they order
results sensibly within a single query, but they are not calibrated across queries
and in practice land in a narrow band — so a fixed numeric cutoff is not a reliable
filter. For tighter precision, take the top N or make the query more specific.

## The embedder-injection seam (optional semantic recall)

Semantic recall is opt-in. No model is bundled and none is downloaded until you
ask for one — keeping the reference cut dependency-light and free of any model's
weight. Turn it on by injecting an embedder at the constructor. Two ways:

**1. Use the shipped reference embedder.** `FastEmbedEmbedder`
([`embedders/fastembed_embedder.py`](embedders/fastembed_embedder.py)) wraps
[`fastembed`](https://github.com/qdrant/fastembed) (Apache-2.0). Install the two
optional packages, then pass an instance (or the `"fastembed"` alias):

```python
from memory import create_adapter                 # pip install fastembed sqlite-vec
from memory.embedders import FastEmbedEmbedder

mem = create_adapter(embedder=FastEmbedEmbedder())    # or: embedder="fastembed"
# or: SqliteAdapter(db_path="/path/to/memory.db", embedder=FastEmbedEmbedder())
```

`FastEmbedEmbedder` defaults to `sentence-transformers/all-MiniLM-L6-v2` (384-dim,
Apache-2.0) — named explicitly rather than inheriting fastembed's own default
(`BAAI/bge-small-en-v1.5`). It exposes `.embed(text) -> list[float]`, is directly
callable, and carries `.dim`, so `create_adapter(embedder="fastembed")` fills
`embed_dim` for you. The model downloads on first construction (Hugging Face, with
a Google Cloud Storage fallback) and is cached after; pass `model_name=...` to use
any other fastembed-supported model.

**2. Bring your own.** The seam is a plain callable `str -> list[float]` (or an
object exposing `.embed` / `.encode`), plus its output dimension:

```python
from memory import create_adapter

def embed(text: str) -> list[float]:
    ...                                             # your model here
mem = create_adapter(embedder=embed, embed_dim=768)
```

`embed_dim` is optional — omit it and the adapter infers the dimension once from a
probe embedding at connect time. Either way, the vector leg engages only when an
embedder is injected **and** `sqlite-vec` loads; otherwise the same call cleanly
stays on FTS5. The adapter names no model and ships none in-tree.

## Quickstart

```python
from memory import create_adapter

mem = create_adapter()                       # SQLite at ~/.keel/memory.db (FTS5 keyword recall)
# or: SqliteAdapter(db_path="/path/to/memory.db")
# add semantic recall with embedder=... / embed_dim=... — see the injection seam above

# Entries
mem.write(wing="work", room="decisions",
          content="Chose SQLite over Postgres for the solo tier: no server to run.")
mem.search("why sqlite instead of postgres")   # -> ranked results
mem.list(wing="work")

# Diary (per-agent session log)
mem.diary_write(agent="my-agent", topic="build", content="Wired up the adapter.")
mem.diary_read(agent="my-agent")

# Relations (a small, queryable knowledge graph)
mem.add_relation(subject="website relaunch", predicate="gated_on",
                 object="copy review")
mem.query_relations(subject="website relaunch")

mem.status()
```

Configuration is by environment variable: `MEMORY_SQLITE_PATH` (database file),
`MEMORY_BACKEND` (`sqlite`), `MEMORY_ALIAS_EXTRA` (a second, private alias file).
The embedder for semantic recall is injected in code (see the seam above), not
selected by env var.

## The contract

Every method maps to one of the twelve memory tools documented in
[`../docs/memory.md`](../docs/memory.md). A skill or workflow written against the
contract does not change when you move tiers:

| Category | Methods |
|---|---|
| Entries | `write`, `search`, `get`, `list`, `update`, `delete` |
| Diary | `diary_write`, `diary_read` |
| Relations | `add_relation`, `query_relations` |
| Other | `link`, `status` |

Each returns a plain JSON-serializable `dict`, so wrapping it in a tool layer is
a thin translation with no serialization work.

## Wiring it to an MCP server

You bring the runtime. The pattern, whatever MCP framework you use, is one thin
tool per method that forwards arguments and returns the dict. Sketch:

```python
from memory import create_adapter

mem = create_adapter()

# Register twelve tools named memory_write, memory_search, ... each of which
# calls the matching adapter method and returns its dict. For example:

def memory_write(wing, room, content, id=None, topic=None, tags=None,
                 source_file=None, chunk_index=None):
    return mem.write(wing, room, content, id=id, topic=topic, tags=tags,
                     source_file=source_file, chunk_index=chunk_index)

def memory_search(query, wing=None, room=None, k=5):
    return mem.search(query, wing=wing, room=room, k=k)

# ...and so on for the remaining ten. The tool names are the contract; the
# adapter behind them is swappable.
```

Keep the tool names stable and backend-free (`memory_write`, not
`memory_write_sqlite`). That is what lets you change the adapter later without
touching a single skill.

## Two write-time guards worth understanding

Both run before anything is stored, and both are shared, backend-neutral modules
so any future backend enforces them by construction:

1. **Noise rejection** (`mining_filter.classify`). A semantic store's biggest
   quality lever is corpus quality, so obvious junk (scraped pages, boilerplate,
   orphaned headings) is refused at write time. It is high-precision by design
   (it errs toward keeping), and the literal signatures in `mining_filter.py`
   are **examples to replace with the boilerplate your own runtime emits**.

2. **A closed relation vocabulary** (`vocab.prepare_relation`). Knowledge-graph
   edges are constrained to a small, fixed set of predicates and a 128-character
   object cap, so the graph stays queryable instead of filling with one-off
   free-form predicates. An off-vocabulary predicate or an over-long object is
   **rejected, not silently folded**, so the caller fixes it. Tune the predicate
   set in `vocab.py` to how you actually reason about your own work, and keep it
   small.

A relations tip carried over from the tier docs: attach a status-like fact to
the finest-grained named thing it is about (a specific project or task), not to
a broad, frequently-reused subject like your company name or yourself. Tools
that group relations by subject to detect supersession will otherwise lump
unrelated facts together.

## Customizing

- **Entity aliases** (`canon.py`): empty by default. Drop an
  `entity_aliases.json` next to the module, or point `MEMORY_ALIAS_EXTRA` at a
  private one, to make different spellings of a thing resolve to one node. See
  `entity_aliases.example.json`.
- **Default agent** (`vocab.py`): set `DEFAULT_AGENT` to whatever you call your
  agent, and add spelling folds to `AGENT_ALIASES`.
- **Noise signatures** (`mining_filter.py`): replace the example literal
  signatures with your runtime's actual boilerplate.

## Moving to Postgres later (Tier 3)

The Postgres/pgvector backend is the same `MemoryAdapter` interface with a
server-backed store behind it: a second adapter class and a new `MEMORY_BACKEND`
value, not a change to any caller. It is **not included in this reference cut**.
`create_adapter("postgres")` raises with a pointer rather than pretending to
have it. Most solo practices never need this tier; see
[`../docs/memory.md`](../docs/memory.md) for when they do.
