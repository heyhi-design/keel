"""create_adapter() — pick a backend by name, so the choice lives in one place.

The point of the adapter interface is that the rest of your system names no
backend. This factory is where the single naming happens: read ``MEMORY_BACKEND``
(default ``"sqlite"``) and hand back an adapter. Everything downstream holds a
``MemoryAdapter`` and cannot tell which backend it got.

Only the SQLite backend ships in this reference cut. A Postgres backend would
implement the exact same ``MemoryAdapter`` interface (``base.py``) — it is a
second adapter class and a new ``MEMORY_BACKEND`` value, not a change to any
caller. It is not included here (see ``README.md`` and ``docs/memory.md`` Tier 3).
"""
from __future__ import annotations

import os

from .base import MemoryAdapter
from .sqlite_adapter import SqliteAdapter

_KNOWN = ("sqlite",)
_KNOWN_EMBEDDERS = ("fastembed",)


def _resolve_embedder_kwarg(kwargs: dict) -> dict:
    """Turn an ``embedder="fastembed"`` string alias into a live
    ``FastEmbedEmbedder`` instance, importing it lazily so the factory stays
    importable without fastembed. Anything else (an instance, a callable, or
    absent/``None``) is left untouched. When the alias is used and the caller did
    not pass ``embed_dim``, fill it from the embedder's ``.dim`` so the adapter
    skips its probe embedding."""
    embedder = kwargs.get("embedder")
    if not isinstance(embedder, str):
        return kwargs
    key = embedder.strip().lower()
    if key != "fastembed":
        raise ValueError(
            f"unknown embedder alias {embedder!r}; known aliases: "
            f"{', '.join(_KNOWN_EMBEDDERS)}. Pass an object with .embed/.encode "
            f"or a str -> list[float] callable to inject your own."
        )
    from .embedders import FastEmbedEmbedder

    inst = FastEmbedEmbedder()
    kwargs["embedder"] = inst
    # The wrapper's .dim is authoritative for this model — it sizes the vec0
    # table. A caller-supplied embed_dim that disagrees would build the table at
    # the wrong width and crash (and roll back) the first write, so reject it up
    # front with a clear message rather than defer to an opaque failure later.
    inst_dim = getattr(inst, "dim", None)
    passed_dim = kwargs.get("embed_dim")
    if passed_dim is not None and inst_dim is not None and passed_dim != inst_dim:
        raise ValueError(
            f"embed_dim={passed_dim} conflicts with the {embedder!r} model's "
            f"dimension ({inst_dim}); omit embed_dim for the {embedder!r} alias "
            f"(it is filled from the embedder), or inject your own embedder + dim."
        )
    if passed_dim is None and inst_dim:
        kwargs["embed_dim"] = inst_dim
    return kwargs


def create_adapter(backend: str | None = None, **kwargs) -> MemoryAdapter:
    """Return a memory adapter for ``backend`` (default: env ``MEMORY_BACKEND``
    or ``"sqlite"``). With no extra arguments the SQLite backend runs in its v1
    default mode: FTS5 keyword recall only, fully offline, nothing to install.
    Extra keyword args pass through to the adapter constructor — ``db_path=...``,
    and ``embedder=...`` / ``embed_dim=...`` to opt into the semantic follow-on
    with a caller-supplied embedder (see ``memory/README.md``).

    ``embedder`` convenience: pass the string ``"fastembed"`` to construct the
    reference ``FastEmbedEmbedder`` (Apache-2.0; ``pip install fastembed
    sqlite-vec``) lazily — the import happens only on this branch, so the factory
    stays importable without fastembed. An already-constructed embedder instance
    (or a plain ``str -> list[float]`` callable) passes straight through; omitting
    ``embedder`` (or ``None``) keeps the FTS5-only default."""
    backend = (backend or os.environ.get("MEMORY_BACKEND", "sqlite")).strip().lower()
    if backend == "sqlite":
        return SqliteAdapter(**_resolve_embedder_kwarg(kwargs))
    if backend in ("postgres", "postgresql", "pg", "pgvector"):
        raise ValueError(
            "the Postgres backend is not included in this reference cut; it is "
            "the same MemoryAdapter interface with a Postgres/pgvector store "
            "behind it (see docs/memory.md, Tier 3). Use backend='sqlite'."
        )
    raise ValueError(
        f"unknown memory backend {backend!r}; known backends: {', '.join(_KNOWN)}"
    )
