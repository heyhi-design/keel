"""FastEmbedEmbedder — a real, OPTIONAL embedder for the semantic follow-on.

This is the one concrete embedder the reference cut ships, and it is opt-in: the
adapter's default is FTS5 keyword recall only (``memory/sqlite_adapter.py``), and
nothing here is imported until you construct this class. It plugs straight into
the adapter's injection seam — pass an instance as ``embedder=...`` to
``SqliteAdapter`` / ``create_adapter`` and, if ``sqlite-vec`` is also installed
and loadable, the vector leg engages; otherwise the adapter cleanly stays on
FTS5.

Seam contract (see ``memory/sqlite_adapter.py`` ``_coerce_embedder`` /
``_to_vector``): this class exposes ``.embed(text) -> list[float]`` for a single
string AND is directly callable (``__call__ = embed``), so it satisfies either
accepted shape — a plain ``str -> list[float]`` callable, or an object with an
``.embed`` method. It also exposes ``.dim`` (the model's output dimension); pass it
as ``embed_dim`` — the ``create_adapter(embedder="fastembed")`` alias does this for
you — to let the adapter size its ``vec0`` table without a probe embedding. A bare
``SqliteAdapter(embedder=FastEmbedEmbedder())`` still measures one probe embedding
at connect.

Research caveats worth knowing before you rely on this:

* **The default model is named explicitly, and is NOT fastembed's own default.**
  fastembed's built-in default is ``BAAI/bge-small-en-v1.5``; this class instead
  defaults to ``sentence-transformers/all-MiniLM-L6-v2`` (384-dim, Apache-2.0) —
  a widely used, small, general-purpose sentence embedder. We name it explicitly
  rather than inheriting fastembed's default so the choice is visible and stable.
  Pass ``model_name=...`` to use any other fastembed-supported model.
* **fastembed downloads the model on first use.** Constructing this class fetches
  the model files remotely (Hugging Face, with a Google Cloud Storage fallback)
  and caches them locally; there is no model shipped in this tree. The first
  construction therefore needs network access; subsequent runs use the cache.
* **License.** fastembed itself is Apache-2.0, and the default model above is
  Apache-2.0. fastembed is an ordinary pip dependency (no vendored code), so it
  carries no NOTICE obligation here — install it yourself:
  ``pip install fastembed sqlite-vec``.

The ``fastembed`` import is deliberately deferred into ``__init__`` so this module
imports cleanly with fastembed absent (the whole point of the FTS5-only default).
Constructing the class without fastembed installed raises a clear ``ImportError``
pointing at the fix, rather than failing obscurely at module import time.
"""

from __future__ import annotations

from typing import Any

# The fastembed identifier for the all-MiniLM-L6-v2 sentence embedder. This is
# the exact string fastembed lists in TextEmbedding.list_supported_models(); it
# is 384-dimensional and Apache-2.0 licensed. Named here (not inherited from
# fastembed's own default) so the model choice is explicit and stable.
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class FastEmbedEmbedder:
    """A single-string embedder over fastembed's batch ``TextEmbedding`` API.

    ``FastEmbedEmbedder(model_name="sentence-transformers/all-MiniLM-L6-v2")``.
    Exposes ``.embed(text) -> list[float]``, is callable (``__call__``), and
    carries ``.dim``. Any extra keyword arguments are forwarded to
    ``fastembed.TextEmbedding`` (e.g. ``cache_dir=...``, ``threads=...``).
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, **kwargs: Any) -> None:
        # Deferred, guarded import: keep this module importable with fastembed
        # absent, and fail loudly (with the fix) only when someone actually asks
        # for the embedder. This is what lets the FTS5-only default ship with
        # zero dependencies.
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - exercised without fastembed
            raise ImportError(
                "pip install fastembed to use FastEmbedEmbedder"
            ) from exc

        self.model_name = model_name
        self._TextEmbedding = TextEmbedding
        # Constructing the model downloads it on first use (see module docstring).
        self._model = TextEmbedding(model_name=model_name, **kwargs)
        self.dim = self._resolve_dim()

    # --- seam methods ------------------------------------------------------
    def embed(self, text: str) -> "list[float]":
        """Embed a single string into a flat ``list[float]``.

        fastembed's ``.embed`` is a BATCH API: it takes an iterable of documents
        and returns a generator of numpy vectors. A single-string call must
        therefore pass ``[text]`` and take the first result — NOT ``embed(text)``,
        which would iterate the string character-by-character.
        """
        out = list(self._model.embed([text]))[0]
        tolist = getattr(out, "tolist", None)
        if callable(tolist):
            return tolist()
        return [float(x) for x in out]

    # Make instances directly callable so they also satisfy the seam's plain
    # ``str -> list[float]`` callable shape, not only the ``.embed`` object shape.
    __call__ = embed

    # --- internals ---------------------------------------------------------
    def _resolve_dim(self) -> int:
        """The model's output dimension.

        Read it from fastembed's static model metadata
        (``list_supported_models()``), which needs no probe embedding. If that
        lookup does not yield a dimension (an unknown model, or a metadata-shape
        change in a future fastembed), fall back to measuring one probe vector.
        """
        dim = self._lookup_dim_from_metadata()
        if dim:
            return dim
        return len(self.embed("dimension probe"))

    def _lookup_dim_from_metadata(self) -> "int | None":
        """Best-effort dimension lookup from ``list_supported_models()``.

        Tolerates both the dict metadata shape and an attribute/object shape, and
        both the ``dim`` and ``dimension`` key spellings, so a fastembed version
        bump is unlikely to break it. Returns ``None`` if nothing matches."""
        try:
            models = self._TextEmbedding.list_supported_models()
        except Exception:
            return None
        target = self.model_name.lower()
        for m in models:
            if isinstance(m, dict):
                name = m.get("model") or m.get("model_name")
                dim = m.get("dim") or m.get("dimension")
            else:
                name = getattr(m, "model", None) or getattr(m, "model_name", None)
                dim = getattr(m, "dim", None) or getattr(m, "dimension", None)
            if name and str(name).lower() == target and dim:
                try:
                    return int(dim)
                except (TypeError, ValueError):
                    return None
        return None

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        dim = getattr(self, "dim", "?")
        return f"FastEmbedEmbedder(model_name={self.model_name!r}, dim={dim})"
