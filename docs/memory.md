# Memory

"Memory" here means one specific thing: giving your agent a way to recall things from past
sessions without you having to re-explain them, searchable by meaning rather than by exact file
and line. It is a separate concern from the corrections registry and decision log, which are
memory too, just not searchable-by-meaning memory.

You do not need any of this to use Keel. Read this page when you're deciding whether
you've outgrown the free tier below.

## Tier 1: File-based memory (the default, no setup required)

Your corrections registry and decision log are already durable memory: plain files, version
controlled if you keep this repository in git, readable by you and by your agent without any
database. For a solo practice, especially early on, this is enough. Don't add infrastructure you
don't need yet.

## Tier 2: A lightweight local backend for searchable recall

When you want to search past sessions rather than remember which file they're in, the recommended
lightweight backend is **SQLite**. In its shipped v1 form it uses **FTS5** (SQLite's built-in
full-text search) for keyword recall: a single local database file, no server to run, no
credentials to manage, no model to download — fully offline, and nothing to install beyond Python
itself.

Recall *by meaning* (finding a past decision by describing it, not by matching its wording) is an
**optional semantic follow-on**, off by default and installed only when you want it. You add it
with two packages — the **sqlite-vec** extension for vector similarity and an embedding model — and
inject the model at the adapter's seam. A reference embedder ships for this:
`FastEmbedEmbedder` (in [`../memory/embedders/`](../memory/embedders/)) wraps
[`fastembed`](https://github.com/qdrant/fastembed) (Apache-2.0), a small, local, torch-free
embedder defaulting to `sentence-transformers/all-MiniLM-L6-v2` (384-dim, Apache-2.0):

```python
# pip install fastembed sqlite-vec
from memory import create_adapter
from memory.embedders import FastEmbedEmbedder
mem = create_adapter(embedder=FastEmbedEmbedder())   # or: create_adapter(embedder="fastembed")
```

No model is bundled in the tree (fastembed downloads it on first use) and none is named inside the
store — the seam also accepts any callable `str -> list[float]` (or an object with `.embed` /
`.encode`), so any embedder works. When both pieces are present the adapter fuses vector recall with
the keyword leg; when either is missing it degrades cleanly back to FTS5. Keeping the model out of
the shipped tree is what keeps this backend dependency-light.

**Known limitation on macOS.** Apple's bundled `/usr/bin/python3` ships a `sqlite3` built without
`enable_load_extension`, so it cannot load `sqlite-vec` at all. On that interpreter the semantic
follow-on simply can't be turned on: the adapter falls back to the FTS5 keyword leg and logs the
degrade once, so nothing breaks, but installing the two packages won't get you vector recall. If
you want semantic recall on a Mac, run this against a Homebrew (`brew install python`) or
python.org interpreter instead — their SQLite builds allow extension loading. Everything else in
this repository, including the whole default FTS5 store, works fine on Apple's Python.

This backend sits behind the same tool contract described below, so a skill or workflow written
against the contract does not change when you move up a tier — or when you later add the semantic
follow-on: it calls the same twelve tools either way. A working reference implementation of this
shape ships in [`../memory/`](../memory/): a single-file SQLite adapter with FTS5 keyword search by
default and the optional sqlite-vec + injected-embedder vector leg, behind the twelve-call
contract. Point it at a database file and wire its methods to your runtime's tools
(`from memory import create_adapter`); see [`../memory/README.md`](../memory/README.md) for the
wiring pattern and the embedder-injection seam. It is additive and opt-in. Tier 1 (file-based)
stays the default, and you move up only when searchable recall is worth a local database.

## Tier 3: A server-backed database for scale

For a larger corrections registry, a longer operating history, or multiple people writing to the
same memory at once, **Postgres with the pgvector extension** is the scale option. This is more
setup (a running database server, credentials, a backup plan) in exchange for handling more
concurrent writers and more data than a single local file comfortably holds. Most solo practices
won't need this tier; it's here for when the practice has grown enough that they do.

## The contract that stays the same across all three

Whichever tier you choose, your agent talks to it through the same twelve-tool contract, so a
skill or a workflow written against the contract doesn't need to know or care which tier is behind
it:

| Category | Tools |
|---|---|
| Entries | `memory_write`, `memory_search`, `memory_get`, `memory_list`, `memory_update`, `memory_delete` |
| Diary | `memory_diary_write`, `memory_diary_read` |
| Relations (a small knowledge graph) | `memory_add_relation`, `memory_query_relations` |
| Other | `memory_link`, `memory_status` |

A relations tip: when you write a status-like fact through `memory_add_relation`, attach it to
the finest-grained named thing the fact is actually about (a specific project, task, or piece of
work), not to a broad, frequently reused subject like your company name, a client name, or
yourself. Any tool that groups relations by subject to detect supersession (treating a newer fact
about the same subject as replacing an older one) will otherwise lump unrelated facts together
just because they share that broad subject, and may propose discarding real information as if it
had been superseded.

This is the same discipline as Layer 1 of the three-layer model applied one level down: name no
specific backend in anything that calls memory tools, and swapping the backend later becomes a
configuration change instead of a rewrite.

## Choosing a tier

Start at Tier 1. Move to Tier 2 when you notice yourself wishing you could search past sessions by
what they were about rather than by remembering which file they're in. Move to Tier 3 only when
Tier 2's single-local-file model is genuinely the bottleneck, not before.
