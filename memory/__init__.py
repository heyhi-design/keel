"""A provider-agnostic memory adapter for the Keel scaffold.

The Tier-2 shape from ``docs/memory.md``: a single-file SQLite store behind one
stable interface. v1 ships FTS5 keyword recall only — fully offline, nothing to
install. Semantic recall (a ``sqlite-vec`` vector leg) is an optional follow-on
you opt into by injecting your own embedder; no embedder ships in-tree. See
``README.md`` in this folder for how to use it, wire the semantic follow-on, and
attach it to an MCP server.

    from memory import SqliteAdapter, create_adapter

    mem = create_adapter()            # or SqliteAdapter(db_path=...)
    mem.write(wing="work", room="decisions", content="Chose X over Y because Z.")
    mem.search("why did we choose X")
"""
from __future__ import annotations

from .base import MemoryAdapter, Result
from .factory import create_adapter
from .sqlite_adapter import SqliteAdapter

__all__ = ["MemoryAdapter", "Result", "SqliteAdapter", "create_adapter"]

__version__ = "0.1.0"
