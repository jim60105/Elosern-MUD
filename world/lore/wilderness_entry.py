"""Wilderness entry point registry: which grid-placed anchor's gate opens onto which coordinate."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WildernessEntryPoint:
    """One anchor's wilderness gateway: the anchor's grid placement and the one
    wilderness coordinate its gate exit opens onto.

    ``anchor_key`` must exist in ``world.lore.anchor_placement.
    ANCHOR_PLACEMENT_REGISTRY``; this is asserted by a test, not enforced by
    the dataclass. Kept deliberately partial, mirroring change 12's own
    ``ANCHOR_PLACEMENT_REGISTRY`` posture: only anchors with a grid placement
    get a wilderness connection.
    """

    anchor_key: str
    wilderness_xy: tuple[int, int]


WILDERNESS_ENTRY_REGISTRY: dict[str, WildernessEntryPoint] = {
    "capital_altoria": WildernessEntryPoint("capital_altoria", (60, 100)),
}
