"""Grid placement registry for geographic anchors (map-anchor-grid)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnchorPlacement:
    """Grid coordinates for one anchor built into the xyzgrid layer.

    ``anchor_key`` must exist in ``world.lore.anchors.ANCHOR_REGISTRY``;
    this is asserted by a test, not enforced by the dataclass.
    """

    anchor_key: str
    zcoord: str
    entrance_xy: tuple[int, int]


# Kept deliberately partial: only anchors built into the grid so far get an
# entry. Future changes (13/14 and later world-building passes) add more.
ANCHOR_PLACEMENT_REGISTRY: dict[str, AnchorPlacement] = {
    "capital_altoria": AnchorPlacement("capital_altoria", "capital_altoria", (2, 2)),
}