"""Synthetic permanent-interior publication for behaviour tests.

A permanent room's prose, scene facts, connections and exterior entrance belong
to its interior document, so a test that authors a synthetic room publishes a
synthetic interior world rather than inheriting a shipped room. These helpers
build those documents from explicit values and install them as a replaced
bundle, restoring the previous map world on exit.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from types import MappingProxyType

from elosern_map_core.codec import document_from_data

from world.maps import runtime
from world.maps.interiors import build_interiors


def interior_room(
    name_zh: str,
    desc_zh: str,
    *,
    scene_archetype: str | None = "tavern_interior",
    art_key: str | None = None,
) -> dict:
    """One authored room declaration for :func:`interior_document`."""

    return {
        "name_zh": name_zh,
        "desc_zh": desc_zh,
        "scene_archetype": scene_archetype,
        "art_key": art_key,
    }


def interior_exterior(
    settlement: str,
    node: str,
    room: str,
    doorway_key: str,
    doorway_aliases: tuple[str, ...] = (),
) -> dict:
    """One authored exterior entrance relationship for :func:`interior_document`."""

    return {
        "settlement": settlement,
        "node": node,
        "room": room,
        "doorway_key": doorway_key,
        "doorway_aliases": list(doorway_aliases),
    }


def interior_document(
    interior_id: str,
    rooms: dict[str, dict],
    *,
    exterior: dict | None = None,
    connections: tuple[dict, ...] = (),
    interior_links: tuple[dict, ...] = (),
):
    """One typed interior document built from explicit values."""

    data = {
        "version": 1,
        "kind": "interior",
        "id": interior_id,
        "rooms": dict(rooms),
        "connections": [dict(item) for item in connections],
        "interior_links": [dict(item) for item in interior_links],
        "exterior": exterior,
    }
    return document_from_data(f"content/maps/interiors/{interior_id}.yaml", data)


@contextmanager
def published_interiors(*documents, replace_existing: bool = False):
    """Install a map bundle whose interior world includes ``documents``.

    ``replace_existing`` swaps the whole interior world; the default overlays
    the synthetic documents on the currently published ones, so a test can add
    one room beside the shipped world.
    """

    previous = runtime.ensure_published()
    current = previous.interiors
    documents_by_id = dict(current.documents)
    if replace_existing:
        documents_by_id = {}
    for document in documents:
        documents_by_id[document.identity] = document
    snapshot = build_interiors(documents_by_id, fingerprints=current.fingerprints)
    runtime.publish(replace(previous, interiors=snapshot))
    try:
        yield snapshot
    finally:
        runtime.publish(previous)


def empty_interiors():
    """The composed (empty) interior world, for a scope with no authored rooms."""

    return build_interiors(MappingProxyType({}))


__all__ = [
    "empty_interiors",
    "interior_document",
    "interior_exterior",
    "interior_room",
    "published_interiors",
]
