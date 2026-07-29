"""Entity canonicalization for the memory knowledge graph — deterministic, no model call.

The graph is only useful if the different ways you name one thing resolve to a
single node. If your practice sometimes writes "Acme", sometimes "Acme Corp",
and sometimes "the client", those should be one entity, not three. Two layers,
both cheap and auditable:

  1. normalize()  — mechanical: lowercase, underscores/whitespace collapsed,
     edge punctuation stripped. Makes "Acme_billing" == "acme billing".
  2. canonical()  — a curated alias map on top of normalize().

The alias map is OPTIONAL and EMPTY by default. To use it, drop an
``entity_aliases.json`` next to this module (see ``entity_aliases.example.json``
for the shape), and/or point the ``MEMORY_ALIAS_EXTRA`` environment variable at
a second JSON file. The env-var file is the right home for names you do not want
committed to a shared repository (a private client roster, say) — it merges on
top of the tracked map without ever entering it.

Alias file format: {"canonical name": ["alias", ...], ...}. Lookups are
normalized on both sides. find_entities() is the shared query/extractor
helper: which known entities does a text mention (whole-word match)?
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

# Optional, empty by default. Ship your own next to this module if you want an
# alias map; otherwise canonicalization is pure mechanical normalization.
_ALIAS_FILE = Path(__file__).resolve().parent / "entity_aliases.json"
# Parens are NOT edge-stripped: entities like "task #267 (pilot plan)" would
# lose only the trailing paren and end up unbalanced. Both sides of every
# comparison run through normalize(), so keeping parens is symmetric.
_EDGE_PUNCT = " \t\n\"'`.,;:!?[]{}<>"


def normalize(text: str) -> str:
    """Mechanical normalization: case, underscores, whitespace, edge punctuation."""
    t = re.sub(r"[_\s]+", " ", (text or "").lower()).strip(_EDGE_PUNCT)
    return re.sub(r"\s+", " ", t)


def _load_alias_map() -> dict[str, str]:
    """normalized surface -> canonical. Tracked map first, MEMORY_ALIAS_EXTRA on top."""
    merged: dict[str, str] = {}
    paths = [_ALIAS_FILE]
    extra = os.environ.get("MEMORY_ALIAS_EXTRA")
    if extra:
        paths.append(Path(extra))
    for p in paths:
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        for canon_name, surfaces in data.items():
            # Skip comment/metadata keys (leading-underscore convention) and any
            # value that is not a list of surface strings. Without this guard, the
            # "_comment" field in entity_aliases.example.json — which users are
            # told to copy to entity_aliases.json — has its string value iterated
            # character by character, seeding ~28 junk single-character surfaces
            # (including the empty string), all mapping to "comment".
            if canon_name.startswith("_") or not isinstance(surfaces, list):
                continue
            cn = normalize(canon_name)
            merged[cn] = cn  # a canonical name is its own surface
            for s in surfaces:
                merged[normalize(s)] = cn
    return merged


_cached: dict[str, str] | None = None


def alias_map(reload: bool = False) -> dict[str, str]:
    global _cached
    if _cached is None or reload:
        _cached = _load_alias_map()
    return _cached


def canonical(entity: str) -> str:
    """Canonical form of an entity: normalize, then alias-map lookup."""
    n = normalize(entity)
    return alias_map().get(n, n)


def surface_map(extra_entities=()) -> dict[str, str]:
    """All known surfaces -> canonical, extended with caller-known entities
    (e.g. the distinct subjects/objects already in memory_relations)."""
    smap = dict(alias_map())
    for e in extra_entities:
        n = normalize(e)
        smap.setdefault(n, canonical(e))
    return smap


def find_entities(text: str, smap: dict[str, str] | None = None) -> set[str]:
    """Canonical entities mentioned in `text` (whole-word surface match).
    Surfaces shorter than 3 chars are ignored — too collision-prone."""
    smap = smap if smap is not None else surface_map()
    hay = f" {normalize(text)} "
    found = set()
    for surface, canon_name in smap.items():
        if len(surface) < 3:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(surface)}(?![a-z0-9])", hay):
            found.add(canon_name)
    return found
