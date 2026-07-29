"""Optional embedders for the semantic follow-on.

Nothing here is required by the adapter: its default is FTS5 keyword recall only,
and this package is imported only when you opt into semantic recall. One concrete
embedder ships — ``FastEmbedEmbedder`` (fastembed, Apache-2.0) — and it plugs into
the adapter's injection seam. Importing this package is safe with fastembed
absent; the fastembed import is deferred until you construct the embedder.

    from memory import SqliteAdapter
    from memory.embedders import FastEmbedEmbedder

    mem = SqliteAdapter(embedder=FastEmbedEmbedder())   # or create_adapter(embedder="fastembed")
"""

from __future__ import annotations

from .fastembed_embedder import DEFAULT_MODEL, FastEmbedEmbedder

__all__ = ["FastEmbedEmbedder", "DEFAULT_MODEL"]
