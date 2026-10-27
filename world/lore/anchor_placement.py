"""Grid placement registry for geographic anchors (map-anchor-grid).

A placement names the authored settlement node an anchor was built into. It
holds a qualified identity, never a grid coordinate: the current entrance room
address is derived from the settlement graph at the consumer boundary
(``world/maps/static_references.py``).
"""

from dataclasses import dataclass

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.references import settlement_node_ref


@dataclass(frozen=True)
class AnchorPlacement:
    """The authored node one anchor is built into.

    ``anchor_key`` must exist in ``world.lore.anchors.ANCHOR_REGISTRY``;
    this is asserted by a test, not enforced by the dataclass. ``zcoord`` is
    the map scope of the node identity, exposed so a consumer never repeats
    the reference's map id.
    """

    anchor_key: str
    node: QualifiedRef

    @property
    def zcoord(self) -> str:
        """The map coordinate space this placement lives in (from its identity)."""

        return self.node.map_id or ""


# Kept deliberately partial: only anchors built into the grid so far get an
# entry. Future changes (13/14 and later world-building passes) add more.
ANCHOR_PLACEMENT_REGISTRY: dict[str, AnchorPlacement] = {
    "capital_altoria": AnchorPlacement(
        "capital_altoria", settlement_node_ref("capital_altoria", "central_plaza")
    ),
    "village_ciaran": AnchorPlacement(
        "village_ciaran", settlement_node_ref("village_ciaran", "village_plaza")
    ),
}
