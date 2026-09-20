"""Place identity registry (settlement-shops design §3.2).

A place is the single authored record of one service location: its interior
room's identity and description, the exterior grid coordinate the interior
attaches to (the z coordinate derives from the settlement), the doorway
naming, its host's identity, the host's profession and that profession's
component identity kwargs, and the assortments the place sells. Nothing a
place declares is declared anywhere else.

``host_race`` / ``host_subrace`` / ``host_sex`` are creation-time authored
identity carried by the record now but not read until
``place-driven-service-sync`` moves interior and host creation onto the
registry (spec documents this seam).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.lore.sex import SEX_VALUES

from world.lore.settlements.settlements import SETTLEMENT_REGISTRY


class PlaceKind(StrEnum):
    GUILD_HALL = "guild_hall"
    GENERAL_STORE = "general_store"
    WEAPONSMITH = "weaponsmith"
    OUTFITTER = "outfitter"
    EATERY = "eatery"


@dataclass(frozen=True)
class PlaceDefinition:
    """Immutable identity of one service location."""

    key: str  # also the interior room tag
    settlement_key: str
    kind: PlaceKind
    room_name_zh: str
    room_desc_zh: str
    exterior_xy: tuple[int, int]  # z derives from the settlement
    doorway_key_zh: str
    doorway_aliases: tuple[str, ...]
    host_name: str
    host_title: str
    host_race: str  # RACE_REGISTRY key
    host_subrace: str | None  # SUBRACE_REGISTRY key under host_race
    host_sex: str  # SEX_VALUES member
    profession: str
    service_id: str
    assortment_keys: tuple[str, ...]
    # The profession blueprint's authored component identity kwargs (shop_key /
    # branch_key / dialogue_key), frozen as a mapping. Projected onto the
    # blueprint exactly as validate_service_hosts projects roster kwargs today.
    authored_kwargs: tuple[tuple[str, str], ...]
    # Per-place assortment adjustments (settlement-shops design §4). Additions
    # stock items outside the referenced assortments — each addition MUST
    # carry a complete override in the shop row (commerce.yaml) because it has
    # no assortment base rule. Removals decline items the referenced
    # assortments contain. Both are shop-only concepts: a place without a
    # shop identity may declare neither.
    extra_item_keys: tuple[str, ...] = ()
    excluded_item_keys: tuple[str, ...] = ()


def _authored_kwargs_map(place: PlaceDefinition) -> dict[str, str]:
    """Flatten the record's frozen kwargs mapping, rejecting silent collapse."""
    if not isinstance(place.authored_kwargs, tuple):
        raise ValueError(
            f"place {place.key!r} authored_kwargs must be a tuple of (key, value) pairs"
        )
    authored: dict[str, str] = {}
    for position, pair in enumerate(place.authored_kwargs):
        if (
            not isinstance(pair, tuple)
            or len(pair) != 2
            or not isinstance(pair[0], str)
            or not pair[0].strip()
            or not isinstance(pair[1], str)
            or not pair[1].strip()
        ):
            raise ValueError(
                f"place {place.key!r} authored_kwargs[{position}] must be a "
                "(non-empty string key, non-empty string value) pair"
            )
        key, value = pair
        if key in authored:
            raise ValueError(f"place {place.key!r} authors kwarg {key!r} more than once")
        authored[key] = value
    return authored


def validate_place_registry(places: Mapping[str, PlaceDefinition]) -> None:
    """Fail closed on a malformed place record, naming the place and rule.

    Record validity (design §3.2): the settlement must exist, the host race
    and sex must be registry members, a subrace must exist and belong to the
    authored race, the exterior must be an (x, y) integer pair, and a place
    declares assortments iff it authors a shop identity. Blueprint coverage
    and dead-kwarg rejection are inherited unchanged from
    ``validate_service_hosts`` at catalog load, not duplicated here.
    """
    for place_key, place in places.items():
        if place_key != place.key:
            raise ValueError(f"place {place_key!r} key mismatch (declared {place.key!r})")
        if place.settlement_key not in SETTLEMENT_REGISTRY:
            raise ValueError(
                f"place {place.key!r} names unknown settlement {place.settlement_key!r}"
            )
        if place.host_race not in RACE_REGISTRY:
            raise ValueError(
                f"place {place.key!r} names unknown host_race {place.host_race!r}"
            )
        if place.host_sex not in SEX_VALUES:
            raise ValueError(
                f"place {place.key!r} names unknown host_sex {place.host_sex!r}"
            )
        if place.host_subrace is not None:
            subrace = SUBRACE_REGISTRY.get(place.host_subrace)
            if subrace is None:
                raise ValueError(
                    f"place {place.key!r} names unknown host_subrace {place.host_subrace!r}"
                )
            if subrace.race_key != place.host_race:
                raise ValueError(
                    f"place {place.key!r} host_subrace {place.host_subrace!r} belongs to "
                    f"race {subrace.race_key!r}, not {place.host_race!r}"
                )
        if (
            not isinstance(place.exterior_xy, tuple)
            or len(place.exterior_xy) != 2
            or any(type(axis) is not int for axis in place.exterior_xy)
        ):
            raise ValueError(
                f"place {place.key!r} exterior_xy must be an (x, y) integer pair, "
                f"got {place.exterior_xy!r}"
            )
        authored = _authored_kwargs_map(place)
        has_shop_identity = "shop_key" in authored
        if bool(place.assortment_keys) != has_shop_identity:
            if place.assortment_keys:
                raise ValueError(
                    f"place {place.key!r} declares assortments without a shop identity "
                    "(shop_key)"
                )
            raise ValueError(
                f"place {place.key!r} declares a shop identity (shop_key) without assortments"
            )
        for field_name in ("extra_item_keys", "excluded_item_keys"):
            keys = getattr(place, field_name)
            if not isinstance(keys, tuple) or any(
                not isinstance(key, str) or not key.strip() for key in keys
            ):
                raise ValueError(
                    f"place {place.key!r} {field_name} must be a tuple of "
                    "non-empty item keys"
                )
            if len(set(keys)) != len(keys):
                raise ValueError(f"place {place.key!r} {field_name} has duplicate item keys")
        if (place.extra_item_keys or place.excluded_item_keys) and not has_shop_identity:
            raise ValueError(
                f"place {place.key!r} declares extra_item_keys/excluded_item_keys "
                "without a shop identity (shop_key)"
            )


# The registry is assembled from the per-settlement slices in fixed order (the
# world/lore/items assembly precedent). Slice order is load-bearing: the
# derived service-host roster and the derived SHOP_REGISTRY both iterate this
# dict, and sync_service_content processes roster rows in this order.
from world.lore.settlements.places_altoria import ROWS as ALTORIA_ROWS  # noqa: E402

PLACE_REGISTRY: dict[str, PlaceDefinition] = {
    definition.key: definition
    for definition in (*ALTORIA_ROWS,)
}

validate_place_registry(PLACE_REGISTRY)