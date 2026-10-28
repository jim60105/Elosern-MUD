"""Explicitly loaded permanent interiors and their immutable game views.

The authored source is ``content/maps/interiors/<interior_id>.yaml``;
``elosern_map_core`` parses and validates each document as a coordinate-free
interior room graph (rooms, internal connections, one-owned interior links and
one exterior entrance relationship). This module is the one game-side adapter
that

* composes the game-facing views a persistent synchronizer needs — the room
  prose and scene/art facts, the directed internal connections, the paired
  interior links and the exterior doorway declarations,
* validates the cross-document rules the game relies on: a room identity is
  globally unique (a persistent room is tagged by it), an exterior opens into
  a room of its own document, two interiors sharing one exterior name their
  doorways differently, and every interior link names an authored room, and
* exposes the currently published interior world.

A permanent interior needs no service record: only a service place *joins* a
room, so a standalone document synchronizes its room, connections and
doorways exactly like a shop's room does. Nothing here reads
``PLACE_REGISTRY`` and nothing here writes game state — ``world.maps.bootstrap``
performs the persistent convergence and ``world.maps.runtime`` publishes the
snapshot.

Nothing here loads or validates at import time: the game composition root (and
tests) publish an adopted bundle, and every read-only consumer goes through
:func:`current`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from elosern_map_core.documents import (
    ConnectionDeclaration,
    ExteriorDeclaration,
    InteriorDocument,
    InteriorLinkDeclaration,
    QualifiedRef,
)
from elosern_map_core.references import interior_room_ref

__all__ = [
    "InteriorError",
    "InteriorNotLoaded",
    "InteriorRoom",
    "InteriorSnapshot",
    "build_interiors",
    "current",
    "exterior_for",
    "is_published",
    "room",
    "room_name_zh",
]


class InteriorError(ValueError):
    """An interior candidate cannot be published.

    ``problems`` names every defect of the rejected candidate, so one edit that
    breaks several documents is reported in full rather than one at a time.
    """

    def __init__(self, problems) -> None:
        self.problems = tuple(problems)
        super().__init__("; ".join(self.problems))


class InteriorNotLoaded(RuntimeError):
    """A consumer read the interior domain before any candidate was published."""


@dataclass(frozen=True, slots=True)
class InteriorRoom:
    """One permanent room as the game reads it.

    ``interior_id`` scopes the authored document, ``room_id`` is the room's
    stable identity (a place key for a service room and the persistent room's
    tag either way), and ``art_key`` is the authored artwork key the room
    addresses or ``None`` when it declares no room artwork of its own.
    """

    interior_id: str
    room_id: str
    name_zh: str
    desc_zh: str
    scene_archetype: str | None
    art_key: str | None

    @property
    def ref(self) -> QualifiedRef:
        """The qualified identity of this room."""

        return interior_room_ref(self.interior_id, self.room_id)


@dataclass(frozen=True, slots=True)
class InteriorSnapshot:
    """One immutable, validated interior world."""

    documents: Mapping[str, InteriorDocument]
    rooms: Mapping[str, InteriorRoom]
    exteriors: Mapping[str, ExteriorDeclaration]
    connections: Mapping[str, tuple[ConnectionDeclaration, ...]]
    interior_links: tuple[InteriorLinkDeclaration, ...]
    room_art_keys: Mapping[str, str]
    fingerprints: Mapping[str, str] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        """A stable digest of the authored source set this snapshot came from."""

        digest = hashlib.sha256()
        for path in sorted(self.fingerprints):
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(self.fingerprints[path].encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    def room(self, room_id: str) -> InteriorRoom:
        """One authored room by its stable identity, or a named rejection."""

        found = self.rooms.get(room_id)
        if found is None:
            raise InteriorError([f"interior room {room_id!r} is not authored"])
        return found

    def rooms_of(self, interior_id: str) -> tuple[InteriorRoom, ...]:
        """Every authored room of one interior document, in authored order."""

        document = self.documents.get(interior_id)
        if document is None:
            return ()
        return tuple(self.rooms[room_id] for room_id in document.rooms)


def _validate(
    documents: Mapping[str, InteriorDocument],
) -> list[str]:
    """Every cross-document rule a published interior world must satisfy."""

    problems: list[str] = []
    seen_rooms: dict[str, str] = {}
    doorway_owners: dict[tuple[str, str, str], str] = {}

    for interior_id in sorted(documents):
        document = documents[interior_id]
        for room_id in document.rooms:
            previous = seen_rooms.get(room_id)
            if previous is not None:
                problems.append(
                    f"room {room_id!r} is declared by interior {previous!r} and "
                    f"interior {interior_id!r}; a persistent room has one identity"
                )
                continue
            seen_rooms[room_id] = interior_id
        exterior = document.exterior
        if exterior is None:
            continue
        if exterior.room not in document.rooms:
            problems.append(
                f"interior {interior_id!r} opens onto room {exterior.room!r}, "
                "which it does not author"
            )
            continue
        doorway = (exterior.settlement, exterior.node, exterior.doorway_key)
        previous = doorway_owners.get(doorway)
        if previous is not None:
            problems.append(
                f"interiors {previous!r} and {interior_id!r} both declare doorway "
                f"{exterior.doorway_key!r} on the exterior "
                f"{exterior.node!r} of {exterior.settlement!r}; two interiors on "
                "one exterior must name their doorways differently"
            )
            continue
        doorway_owners[doorway] = interior_id

    for interior_id in sorted(documents):
        for link in documents[interior_id].interior_links:
            target = documents.get(link.target_interior)
            if target is None:
                problems.append(
                    f"interior {interior_id!r} links to interior "
                    f"{link.target_interior!r}, which is not authored"
                )
            elif link.target_room not in target.rooms:
                problems.append(
                    f"interior {interior_id!r} links to room {link.target_room!r} "
                    f"of interior {link.target_interior!r}, which does not author it"
                )
    return problems


def build_interiors(
    documents: Mapping[str, InteriorDocument],
    *,
    fingerprints: Mapping[str, str] | None = None,
) -> InteriorSnapshot:
    """Validate one candidate source set and compose its immutable views."""

    problems = _validate(documents)
    if problems:
        raise InteriorError(problems)

    rooms: dict[str, InteriorRoom] = {}
    exteriors: dict[str, ExteriorDeclaration] = {}
    connections: dict[str, tuple[ConnectionDeclaration, ...]] = {}
    room_art_keys: dict[str, str] = {}
    links: list[InteriorLinkDeclaration] = []
    for interior_id, document in documents.items():
        for room_id, declaration in document.rooms.items():
            rooms[room_id] = InteriorRoom(
                interior_id=interior_id,
                room_id=room_id,
                name_zh=declaration.name_zh,
                desc_zh=declaration.desc_zh,
                scene_archetype=declaration.scene_archetype,
                art_key=declaration.art_key,
            )
            if declaration.art_key is not None:
                room_art_keys[room_id] = declaration.art_key
        if document.exterior is not None:
            exteriors[document.exterior.room] = document.exterior
        connections[interior_id] = document.connections
        links.extend(document.interior_links)

    return InteriorSnapshot(
        documents=MappingProxyType(dict(documents)),
        rooms=MappingProxyType(rooms),
        exteriors=MappingProxyType(exteriors),
        connections=MappingProxyType(connections),
        interior_links=tuple(links),
        room_art_keys=MappingProxyType(room_art_keys),
        fingerprints=MappingProxyType(dict(fingerprints or {})),
    )


_PUBLISHED: InteriorSnapshot | None = None


def _install(snapshot: InteriorSnapshot) -> InteriorSnapshot:
    """Bind one validated snapshot as this process's interior world.

    The map composition root (``world.maps.runtime``) owns publication: it
    installs the four domain views of one bundle together, so no domain can be
    replaced on its own and no partial world can be observed.
    """

    if not isinstance(snapshot, InteriorSnapshot):
        raise TypeError("_install() requires an InteriorSnapshot")
    global _PUBLISHED
    _PUBLISHED = snapshot
    return snapshot


def current() -> InteriorSnapshot:
    """The published interior world.

    Raises :class:`InteriorNotLoaded` instead of loading implicitly: the map
    composition root publishes a complete adopted bundle before any consumer
    reads it.
    """

    snapshot = _PUBLISHED
    if snapshot is None:
        raise InteriorNotLoaded(
            "permanent interiors are not loaded; publish the adopted map world "
            "before using map consumers"
        )
    return snapshot


def is_published() -> bool:
    """Whether an interior snapshot has been published in this process."""

    return _PUBLISHED is not None


def room(room_id: str) -> InteriorRoom:
    """One published room by its stable identity."""

    return current().room(room_id)


def room_name_zh(reference: QualifiedRef) -> str:
    """The authored display name of one qualified interior room.

    This is the map-facing label resolver a service record uses instead of
    copying the room's name: the name belongs to the interior document alone.
    """

    published = current()
    if reference.domain != "interior_room" or reference.object_id is None:
        raise InteriorError(
            [f"{reference!r} is not a qualified interior_room reference"]
        )
    interior_id = reference.map_id
    found = published.rooms.get(reference.object_id)
    if found is None:
        raise InteriorError(
            [f"interior room {reference.object_id!r} is not authored"]
        )
    if interior_id is not None and found.interior_id != interior_id:
        raise InteriorError(
            [
                f"interior room {reference.object_id!r} belongs to interior "
                f"{found.interior_id!r}, not {interior_id!r}"
            ]
        )
    return found.name_zh


def exterior_for(room_id: str) -> ExteriorDeclaration | None:
    """The authored exterior entrance of one published room's interior.

    The entrance relationship belongs to the interior document, so every room
    of that document — an inner room reached through its own connections
    included — resolves the same entrance. A document that declares none has no
    exterior at all.
    """

    published = current()
    found = published.rooms.get(room_id)
    if found is None:
        return None
    return published.documents[found.interior_id].exterior
