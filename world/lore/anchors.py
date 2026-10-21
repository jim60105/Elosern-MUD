"""Geographic anchor registry from design section 5.1 and lore-world-data.

``ANCHOR_REGISTRY`` is lore identity. ``ANCHOR_GEOGRAPHY_REGISTRY`` declares
the canonical wilderness cell of every anchor and ``LOCAL_FRAME_ANCHOR_REGISTRY``
binds the authored settlement frames; neither is the grid-placement registry
and neither spawns rooms.
"""

from dataclasses import dataclass
from enum import StrEnum

from .wilderness_regions import cell_center_m


class AnchorKind(StrEnum):
    CAPITAL = "capital"
    ELVEN_VILLAGE = "elven_village"
    DUNGEON = "dungeon"


@dataclass(frozen=True)
class Anchor:
    key: str
    kind: AnchorKind
    display_name_zh: str
    nation_key: str | None
    population: int | None
    floors: int | None
    description: str


ANCHOR_REGISTRY: dict[str, Anchor] = {
    "capital_grandia": Anchor(
        "capital_grandia", AnchorKind.CAPITAL, "輝煌帝都", "grandia", 800_000, None,
        "Capital of the Grandia Empire.",
    ),
    "capital_altoria": Anchor(
        "capital_altoria", AnchorKind.CAPITAL, "聖潔王都", "altoria", 600_000, None,
        "Capital of the Altoria Kingdom.",
    ),
    "capital_valhalla": Anchor(
        "capital_valhalla", AnchorKind.CAPITAL, "咆哮王城", "valhalla", 400_000, None,
        "Capital of the Valhalla Beast Kingdom.",
    ),
    "village_fionnen": Anchor(
        "village_fionnen", AnchorKind.ELVEN_VILLAGE, "翠綠森林村", None, 120, None,
        "Fionnen village on the eastern side of the neutral central range.",
    ),
    "village_ciaran": Anchor(
        "village_ciaran", AnchorKind.ELVEN_VILLAGE, "暗影谷村", None, 100, None,
        "Ciaran village underground on the western side of the neutral central range.",
    ),
    "village_eolas": Anchor(
        "village_eolas", AnchorKind.ELVEN_VILLAGE, "幽月谷村", None, 80, None,
        "Hidden Eolas village in a northern valley of the neutral central range.",
    ),
    "dungeon_eternal_night": Anchor(
        "dungeon_eternal_night", AnchorKind.DUNGEON, "永夜迷宮", "valhalla", None, 80,
        "A northern deep-forest dungeon under Valhalla's nominal but unenforced claim.",
    ),
    "dungeon_dragon_nest": Anchor(
        "dungeon_dragon_nest", AnchorKind.DUNGEON, "龍之巢穴", "grandia", None, 50,
        "A known dungeon in the eastern Grandia Empire.",
    ),
    "dungeon_arcane_ruins": Anchor(
        "dungeon_arcane_ruins", AnchorKind.DUNGEON, "魔導遺跡", "altoria", None, 60,
        "A known dungeon in the western Altoria Kingdom.",
    ),
}


@dataclass(frozen=True)
class GeographicAnchor:
    """The canonical wilderness cell of one lore anchor.

    Declaring a cell creates no room and reveals nothing to players; map
    knowledge and visibility rules remain authoritative.
    """

    anchor_key: str
    cell: tuple[int, int]
    geographic_constraint: str


ANCHOR_GEOGRAPHY_REGISTRY: dict[str, GeographicAnchor] = {
    "capital_altoria": GeographicAnchor(
        "capital_altoria", (860, 1080),
        "Western river valley and hills; riverfront below northern terraces",
    ),
    "capital_grandia": GeographicAnchor(
        "capital_grandia", (1970, 1280),
        "Eastern agricultural plain and major river supply",
    ),
    "capital_valhalla": GeographicAnchor(
        "capital_valhalla", (780, 1910),
        "Northwestern highland forest and tribal routes",
    ),
    "village_ciaran": GeographicAnchor(
        "village_ciaran", (1340, 1220),
        "Underground settlement on the western flank of the central mountains",
    ),
    "village_fionnen": GeographicAnchor(
        "village_fionnen", (1490, 1510),
        "Forest on the eastern mountain flank",
    ),
    "village_eolas": GeographicAnchor(
        "village_eolas", (1410, 2150),
        "Hidden northern mountain valley near deep forest",
    ),
    "dungeon_eternal_night": GeographicAnchor(
        "dungeon_eternal_night", (900, 2350),
        "Northern deep forest under nominal Valhalla jurisdiction",
    ),
    "dungeon_dragon_nest": GeographicAnchor(
        "dungeon_dragon_nest", (2340, 1220),
        "Remote eastern Grandia",
    ),
    "dungeon_arcane_ruins": GeographicAnchor(
        "dungeon_arcane_ruins", (480, 1160),
        "Western Altoria hills and ancient/mineral sites",
    ),
}


@dataclass(frozen=True)
class LocalFrameAnchor:
    """The authored integer-metre point that binds a settlement frame.

    ``local_anchor_m`` is the ``(east, north)`` metre position inside the
    settlement that sits at the center of its wilderness anchor cell.
    """

    anchor_key: str
    local_anchor_m: tuple[int, int]


LOCAL_FRAME_ANCHOR_REGISTRY: dict[str, LocalFrameAnchor] = {
    "capital_altoria": LocalFrameAnchor("capital_altoria", (3500, 2850)),
    "village_ciaran": LocalFrameAnchor("village_ciaran", (220, 305)),
}


def world_position_m(
    anchor_key: str, local_position_m: tuple[int, int]
) -> tuple[int, int]:
    """Absolute ``(east, north)`` metres of a settlement-local metre position.

    ``world = wilderness_anchor_cell_center + local - local_anchor``. The
    settlement's ``z`` remains a logical layer and is never elevation; this
    transform returns horizontal metres only.
    """
    geography = ANCHOR_GEOGRAPHY_REGISTRY[anchor_key]
    frame = LOCAL_FRAME_ANCHOR_REGISTRY[anchor_key]
    center_east, center_north = cell_center_m(geography.cell)
    return (
        center_east + local_position_m[0] - frame.local_anchor_m[0],
        center_north + local_position_m[1] - frame.local_anchor_m[1],
    )
