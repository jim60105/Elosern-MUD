"""Read-only registry views over one explicitly published map snapshot.

The settlement domain used to be Python module data, so every consumer imported
a module-level registry object once. The authored source is now discovered YAML
and the composed views are values of an immutable snapshot that a composition
root publishes explicitly (see ``world.maps.map_data``). These two facades keep
that consumer shape -- ``REGISTRY[key]``, ``.get``, ``.items()``, ``in``, ``len``
-- while reading the *currently published* snapshot on every access, so a
replacement is immediately visible to every consumer that holds the view.

They are read views, never a second authority and never a fallback to another
format: the mapping they expose is the composed value of the one published
snapshot, and reading with nothing published raises ``SettlementNotLoaded``
exactly like ``world.maps.geography.current()``.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Set
from typing import Any

__all__ = ["PublishedKeySet", "PublishedView"]


def _snapshot() -> Any:
    """The published settlement snapshot (imported lazily: no import cycle)."""

    from world.maps.map_data import current

    return current()


class PublishedView(Mapping):
    """One composed registry view of the published settlement snapshot."""

    __slots__ = ("_attribute",)

    def __init__(self, attribute: str) -> None:
        self._attribute = attribute

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"PublishedView({self._attribute!r})"

    def _value(self) -> Mapping:
        return getattr(_snapshot(), self._attribute)

    def __getitem__(self, key: Any) -> Any:
        return self._value()[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._value())

    def __len__(self) -> int:
        return len(self._value())


class PublishedKeySet(Set):
    """The published map identities, as a read-only key set."""

    __slots__ = ("_attribute",)

    def __init__(self, attribute: str) -> None:
        self._attribute = attribute

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"PublishedKeySet({self._attribute!r})"

    def _value(self) -> Mapping:
        return getattr(_snapshot(), self._attribute)

    def __contains__(self, key: object) -> bool:
        return key in self._value()

    def __iter__(self) -> Iterator[Any]:
        return iter(self._value())

    def __len__(self) -> int:
        return len(self._value())
