"""MemoryAdapter — the interface every backend implements.

One adapter per backend. Methods take the contract arg names (clean,
function-named) and return a JSON-serializable dict. Swapping backends =
writing one new adapter and pointing MEMORY_BACKEND at it. The skills and
workflows that call the memory tools never change — that is the whole point of
putting the backend behind an interface.

This is Layer 1 of the three-layer model applied to memory: name no specific
backend in anything that calls these methods, and moving from SQLite to
Postgres later becomes a configuration change instead of a rewrite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

Result = dict[str, Any]


class MemoryAdapter(ABC):
    #: short backend label, surfaced in status()
    name: str = "base"

    # --- entries (drawers) -------------------------------------------------
    @abstractmethod
    def write(
        self,
        wing: str,
        room: str,
        content: str,
        id: str | None = None,
        topic: str | None = None,
        tags: list[str] | None = None,
        source_file: str | None = None,
        chunk_index: int | None = None,
    ) -> Result: ...

    @abstractmethod
    def search(
        self,
        query: str,
        wing: str | None = None,
        room: str | None = None,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> Result: ...

    @abstractmethod
    def get(self, id: str) -> Result: ...

    @abstractmethod
    def list(
        self,
        wing: str | None = None,
        room: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Result: ...

    @abstractmethod
    def update(
        self,
        id: str,
        content: str | None = None,
        wing: str | None = None,
        room: str | None = None,
        tags: list[str] | None = None,
    ) -> Result: ...

    @abstractmethod
    def delete(self, id: str) -> Result: ...

    # --- diary -------------------------------------------------------------
    @abstractmethod
    def diary_write(
        self,
        agent: str,
        topic: str,
        content: str,
        date: str | None = None,
        wing: str | None = None,
    ) -> Result: ...

    @abstractmethod
    def diary_read(
        self,
        agent: str = "default-agent",
        limit: int = 10,
        since: str | None = None,
        wing: str | None = None,
    ) -> Result: ...

    # --- knowledge graph ---------------------------------------------------
    @abstractmethod
    def add_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        confidence: float | None = None,
        valid_from: str | None = None,
        valid_to: str | None = None,
        source: str | None = None,
    ) -> Result: ...

    @abstractmethod
    def query_relations(
        self,
        subject: str | None = None,
        predicate: str | None = None,
        object: str | None = None,
        as_of: str | None = None,
        direction: str = "both",
    ) -> Result: ...

    @abstractmethod
    def link(
        self,
        source_wing: str,
        source_room: str,
        target_wing: str,
        target_room: str,
        label: str = "",
        source_id: str | None = None,
        target_id: str | None = None,
    ) -> Result: ...

    # --- health ------------------------------------------------------------
    @abstractmethod
    def status(self) -> Result: ...
