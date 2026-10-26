"""The authored capability declaration carriers (npc-capability-declarations).

A pure data leaf: the exact immutable shape an NPC's capability declaration
takes in JSON — ``{type, kwargs, binding}`` — plus the two binding forms. It
imports nothing from ``typeclasses`` on purpose: the place registry (which
authors these declarations in lore) imports it at load time, and lore must stay
importable without an Evennia/Django environment. The vocabulary, validation
and assembly live in :mod:`world.rules.npc_capabilities`, which re-exports
these carriers as its public surface.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

#: The closed binding vocabulary: a capability either travels with the person
#: (co-presence) or is anchored to exactly one authored place.
BINDING_KINDS = frozenset({"person", "place"})


class CapabilityValidationError(ValueError):
    """One or more authored capability declarations are unusable.

    ``issues`` holds one named message per offense (record/place/role, type and
    field). Callers translate the list into their own failure surface without
    re-deriving what was wrong.
    """

    def __init__(self, issues, *, owner: str | None = None):
        self.issues = tuple(issues)
        self.owner = owner
        prefix = f"{owner}: " if owner else ""
        super().__init__(prefix + "; ".join(self.issues))


@dataclass(frozen=True)
class Binding:
    """One authored availability binding."""

    kind: str
    #: The room tag a ``place`` binding anchors to; ``None`` for ``person``.
    anchor_room: str | None = None


def person_bound() -> Binding:
    """Return the co-presence binding a traveling capability declares."""
    return Binding("person")


def place_bound(anchor_room: str) -> Binding:
    """Return the anchored binding a fixed-location capability declares."""
    return Binding("place", anchor_room)


@dataclass(frozen=True)
class CapabilityDeclaration:
    """One authored capability: its type, authored kwargs and binding.

    Exactly the JSON entry's fields, frozen. ``kwargs`` is exposed as a
    read-only mapping, so a declaration cannot be edited after authoring and a
    plan built from it stays immutable.
    """

    type: str
    kwargs: Mapping[str, Any]
    binding: Binding | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kwargs, Mapping):
            raise CapabilityValidationError(
                [f"component {self.type!r} kwargs must be a mapping"]
            )
        object.__setattr__(self, "kwargs", MappingProxyType(dict(self.kwargs)))


def capability(
    type_key: str, *, binding: Binding | None = None, **kwargs: Any
) -> CapabilityDeclaration:
    """Author one declaration in the same shape a JSON record uses."""
    return CapabilityDeclaration(type_key, kwargs, binding)


__all__ = [
    "BINDING_KINDS",
    "Binding",
    "CapabilityDeclaration",
    "CapabilityValidationError",
    "capability",
    "person_bound",
    "place_bound",
]
