"""Synthetic permanent-interior catalog for the test-data kit.

A permanent room's prose, scene facts and exterior entrance belong to its
interior document, so the kit authors its stand-in rooms here and its place
rows only join them. Nothing in this module names shipped content.
"""

from __future__ import annotations

from elosern_map_core.codec import document_from_data

#: One authored interior document per stand-in room: the room declaration and
#: the single exterior entrance it owns. ``t_mossgate`` is validation-only
#: space with no grid map, so a database-backed probe that needs a materialized
#: street clones a live resolvable row instead (see ``data_world``).
SYNTH_INTERIORS: dict[str, dict] = {
    "t_mossgate_guild_hall": {
        "room": {
            "name_zh": "合成苔徑公會廳",
            "desc_zh": "A synthetic guild hall for the mossgate stand-in world.",
            "scene_archetype": None,
            "art_key": "t_mossgate_guild_hall",
        },
        "exterior": {
            "settlement": "t_mossgate",
            "node": "t_guild_hall",
            "room": "t_mossgate_guild_hall",
            "doorway_key": "合成公會廳入口",
            "doorway_aliases": ["synthetic hall"],
        },
    },
    "t_mossgate_store": {
        "room": {
            "name_zh": "合成苔徑雜貨店",
            "desc_zh": "A synthetic general store for the mossgate stand-in world.",
            "scene_archetype": None,
            "art_key": "t_mossgate_store",
        },
        "exterior": {
            "settlement": "t_mossgate",
            "node": "t_store",
            "room": "t_mossgate_store",
            "doorway_key": "合成雜貨店入口",
            "doorway_aliases": ["synthetic store"],
        },
    },
    "t_mossgate_plaza": {
        "room": {
            "name_zh": "合成苔徑村中廣場",
            "desc_zh": (
                "A synthetic gathering clearing: a place that exists with no host."
            ),
            "scene_archetype": None,
            "art_key": "t_mossgate_plaza",
        },
        "exterior": {
            "settlement": "t_mossgate",
            "node": "t_plaza",
            "room": "t_mossgate_plaza",
            "doorway_key": "合成廣場入口",
            "doorway_aliases": ["synthetic plaza"],
        },
    },
}


def interior_documents() -> tuple:
    """The kit's authored interior documents, one per stand-in room."""

    documents = []
    for interior_id, declaration in SYNTH_INTERIORS.items():
        data = {
            "version": 1,
            "kind": "interior",
            "id": interior_id,
            "rooms": {interior_id: dict(declaration["room"])},
            "connections": [],
            "interior_links": [],
            "exterior": dict(declaration["exterior"]),
        }
        documents.append(
            document_from_data(f"content/maps/interiors/{interior_id}.yaml", data)
        )
    return tuple(documents)


__all__ = ["SYNTH_INTERIORS", "interior_documents"]
