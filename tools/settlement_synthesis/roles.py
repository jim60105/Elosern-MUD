"""The archetype role catalogue: which places a settlement of one class gets.

Each row is one coarse zoning choice from the location-applicability matrix in
``docs/lore/settlement-locations.md``. A row is a slot the generator may place,
not a room: the prose pass fills ``key`` and ``desc`` later. Rows are matched by
settlement class, by the budget's node count and, for the water roles, by
whether the footprint actually touches the required water.

The catalogue is deliberately data: a review can change one row without touching
the placement code. The tests pass synthetic catalogues, so nothing here is
pinned by a test.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Every placement rule the generator implements.
PLACEMENTS = (
    "near_anchor",
    "high_ground",
    "periphery",
    "ring",
    "water_edge",
    "water_downstream",
)

@dataclass(frozen=True)
class RoleEntry:
    """One catalogue row: a role slot, its classes and its placement rule."""

    slot_id: str
    key_zh: str
    classes: frozenset[str]  # subset of SETTLEMENT_CLASSES
    placement: str  # one of PLACEMENTS
    priority: int  # lower first; ties by slot_id
    min_nodes: int  # included only when budget.node_count >= min_nodes
    requires: str | None  # None | "water" | "river"


def _classes(*names: str) -> frozenset[str]:
    return frozenset(names)


DEFAULT_CATALOGUE: tuple[RoleEntry, ...] = (
    RoleEntry("quay", "碼頭", _classes("port"), "water_edge", 5, 0, "water"),
    RoleEntry(
        "market_street",
        "市場街",
        _classes("human_capital", "human_town", "port", "beast_capital", "beast_town"),
        "near_anchor",
        10,
        0,
        None,
    ),
    RoleEntry(
        "palace_forecourt",
        "王宮前庭",
        _classes("human_capital"),
        "high_ground",
        12,
        0,
        None,
    ),
    RoleEntry(
        "tribal_hall",
        "部族議事廳前",
        _classes("beast_capital", "beast_town"),
        "ring",
        12,
        0,
        None,
    ),
    RoleEntry(
        "assembly_ground",
        "集會場",
        _classes("beast_capital", "beast_town"),
        "near_anchor",
        13,
        0,
        None,
    ),
    RoleEntry(
        "training_ground",
        "校場外",
        _classes("beast_capital", "beast_town"),
        "ring",
        14,
        0,
        None,
    ),
    RoleEntry(
        "harbour_office",
        "港務總管府前",
        _classes("port"),
        "water_edge",
        15,
        0,
        "water",
    ),
    RoleEntry(
        "guild_forecourt",
        "公會前",
        _classes("human_capital", "human_town", "port", "beast_capital", "beast_town"),
        "near_anchor",
        20,
        0,
        None,
    ),
    RoleEntry(
        "river_quay",
        "河港碼頭",
        _classes("human_capital", "human_town"),
        "water_edge",
        25,
        8,
        "river",
    ),
    RoleEntry(
        "temple_forecourt",
        "神殿前",
        _classes("human_capital", "human_town", "port"),
        "high_ground",
        30,
        0,
        None,
    ),
    RoleEntry(
        "ancestral_altar",
        "祖靈祭壇",
        _classes("beast_capital", "beast_town"),
        "high_ground",
        30,
        0,
        None,
    ),
    RoleEntry(
        "noble_quarter",
        "貴族區前",
        _classes("human_capital"),
        "high_ground",
        35,
        0,
        None,
    ),
    RoleEntry(
        "inn_lane",
        "客棧巷",
        _classes("human_capital", "human_town", "port"),
        "near_anchor",
        40,
        8,
        None,
    ),
    RoleEntry(
        "tavern_lane",
        "酒館巷",
        _classes("beast_capital", "beast_town"),
        "near_anchor",
        40,
        8,
        None,
    ),
    RoleEntry(
        "riverbank",
        "河岸道",
        _classes("human_capital", "human_town", "port"),
        "water_edge",
        45,
        10,
        "river",
    ),
    RoleEntry(
        "ferry_landing",
        "渡口碼頭",
        _classes("beast_capital", "beast_town"),
        "water_edge",
        45,
        8,
        "river",
    ),
    RoleEntry(
        "exchange_forecourt",
        "商會前",
        _classes("human_capital", "port"),
        "near_anchor",
        45,
        10,
        None,
    ),
    RoleEntry(
        "exchange_forecourt",
        "商會前",
        _classes("human_town"),
        "near_anchor",
        45,
        12,
        None,
    ),
    RoleEntry(
        "craft_alley",
        "工匠巷",
        _classes("human_capital", "human_town", "port", "beast_capital", "beast_town"),
        "water_downstream",
        50,
        8,
        None,
    ),
    RoleEntry(
        "academy",
        "學院前",
        _classes("human_capital"),
        "high_ground",
        55,
        0,
        None,
    ),
    RoleEntry(
        "manor_gate",
        "領主宅邸前",
        _classes("human_town"),
        "high_ground",
        56,
        8,
        None,
    ),
    RoleEntry(
        "training_ground",
        "校場外",
        _classes("human_capital"),
        "periphery",
        60,
        0,
        None,
    ),
    RoleEntry(
        "training_ground",
        "校場外",
        _classes("human_town"),
        "periphery",
        60,
        12,
        None,
    ),
    RoleEntry(
        "bath_forecourt",
        "浴場前",
        _classes("human_capital", "port"),
        "near_anchor",
        65,
        10,
        None,
    ),
    RoleEntry(
        "bath_forecourt",
        "浴場前",
        _classes("human_town"),
        "near_anchor",
        65,
        12,
        None,
    ),
)


def _check_slot_ids(catalogue: tuple[RoleEntry, ...]) -> None:
    """Refuse two rows for one slot id whose class sets overlap."""

    for index, entry in enumerate(catalogue):
        for other in catalogue[index + 1 :]:
            if entry.slot_id == other.slot_id and entry.classes & other.classes:
                raise ValueError(
                    f"catalogue slot {entry.slot_id!r} is declared twice for the "
                    f"class(es) {sorted(entry.classes & other.classes)}"
                )


_check_slot_ids(DEFAULT_CATALOGUE)


__all__ = [
    "DEFAULT_CATALOGUE",
    "PLACEMENTS",
    "RoleEntry",
]
