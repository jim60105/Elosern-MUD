"""Grid placement registry for geographic anchors (map-anchor-grid).

A placement names the authored settlement node an anchor was built into. It
holds a qualified identity, never a grid coordinate: the current entrance room
address is derived from the settlement graph at the consumer boundary
(``world/maps/static_references.py``).

The authored declaration lives in the settlement document: its ``location_ref``
names the anchor and its ``anchor_room`` node is the placement. This module
exposes the composed view of the published settlement world, keyed by that
location identity, so a location with no local map simply has no placement.
"""

from dataclasses import dataclass
from typing import Mapping

from elosern_map_core.documents import QualifiedRef

from world.maps.published import PublishedView


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


# Kept deliberately partial: only anchors with a discovered settlement document
# get a placement. A location with no local map needs no placeholder row.
ANCHOR_PLACEMENT_REGISTRY: Mapping[str, AnchorPlacement] = PublishedView(
    "anchor_placements"
)


__all__ = ["ANCHOR_PLACEMENT_REGISTRY", "AnchorPlacement"]
