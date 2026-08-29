"""Deterministic per-subrace basic starting equipment kits for custom creation."""

from dataclasses import dataclass

from world.lore.items import ITEM_REGISTRY
from world.lore.races import SUBRACE_REGISTRY


@dataclass(frozen=True)
class SubraceStartingKit:
    """The basic equipment a custom-created character of one subrace wakes with."""

    subrace_key: str
    items: tuple[tuple[str, int], ...]

    def inventory_list(self) -> list[str]:
        """Return the flat repeated-key inventory the activation hands out."""
        return [
            item_key
            for item_key, quantity in self.items
            for _ in range(quantity)
        ]


def _kit(subrace_key: str, *item_keys: str) -> SubraceStartingKit:
    return SubraceStartingKit(subrace_key, tuple((key, 1) for key in item_keys))


SUBRACE_STARTING_KIT_REGISTRY: dict[str, SubraceStartingKit] = {
    kit.subrace_key: kit
    for kit in (
        _kit("human_royal", "gilded_saber", "chainmail", "silver_hairpin"),
        _kit("human_noble", "knight_blade", "leather_armor", "silver_hairpin"),
        _kit("human_wealthy", "knight_blade", "chainmail", "silver_hairpin"),
        _kit("human_commoner", "plain_sword", "leather_armor"),
        _kit("human_laborer", "wooden_club", "leather_armor"),
        _kit("fionnen", "hunters_longbow", "leather_armor"),
        _kit("ciaran", "ashen_scimitar", "leather_armor"),
        _kit("eolas", "apprentice_focus_staff", "mage_robe", "prism_charm"),
        _kit(
            "wolfkin",
            "plain_sword",
            "iron_dagger",
            "leather_armor",
            "wolf_fang_necklace",
        ),
        _kit("catkin", "steel_fang_dagger", "iron_dagger", "leather_armor"),
        _kit("bearkin", "great_axe", "chainmail"),
        _kit("rabbitkin", "hunters_longbow", "leather_armor"),
        _kit("bovinekin", "plain_sword", "iron_shield", "chainmail"),
        _kit("tigerkin", "steel_fang_dagger", "hunting_throwing_axe", "leather_armor"),
        _kit("foxkin", "apprentice_focus_staff", "mage_robe", "pilgrim_medallion"),
    )
}


def _validate_starting_kit(registry_key: str, kit: object) -> None:
    """Reject one kit an activation could never hand out.

    Mirrors the preset starting-item validator's load-time stance and adds the
    kit-specific rules: the kit must be non-empty (a subrace never wakes
    bare-handed) and equipment-only (a consumable or inspect-only item can
    never compose a kit), so an invalid kit raises at import instead of
    mid-activation. Item keys are checked as strings before the registry
    lookup so malformed hand-built entries fail with a stable ValueError.
    """
    if not isinstance(kit, SubraceStartingKit):
        raise ValueError(f"starting kit {registry_key!r} must be a SubraceStartingKit")
    if kit.subrace_key != registry_key:
        raise ValueError(
            f"starting kit {registry_key!r} declares mismatched subrace "
            f"{kit.subrace_key!r}"
        )
    if not isinstance(kit.items, tuple) or len(kit.items) == 0:
        raise ValueError(f"starting kit {registry_key!r} must be a non-empty tuple")
    seen: set[str] = set()
    for entry in kit.items:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError(
                f"starting kit {registry_key!r} declares a malformed item entry"
            )
        item_key, quantity = entry
        if not isinstance(item_key, str) or item_key not in ITEM_REGISTRY:
            raise ValueError(
                f"starting kit {registry_key!r} declares unknown item {item_key!r}"
            )
        if ITEM_REGISTRY[item_key].equipment_slot is None:
            raise ValueError(
                f"starting kit {registry_key!r} declares non-equipment item "
                f"{item_key!r}"
            )
        if item_key in seen:
            raise ValueError(
                f"starting kit {registry_key!r} declares duplicate item {item_key!r}"
            )
        seen.add(item_key)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError(
                f"starting kit {registry_key!r} declares a non-positive "
                f"quantity for {item_key!r}"
            )


def _validate_starting_kit_coverage(registry: dict[str, SubraceStartingKit]) -> None:
    """Require exactly one kit per registered subrace before any activation."""
    missing = set(SUBRACE_REGISTRY) - set(registry)
    if missing:
        raise ValueError(
            f"starting-kit registry is missing subrace(s): {sorted(missing)}"
        )
    unknown = set(registry) - set(SUBRACE_REGISTRY)
    if unknown:
        raise ValueError(
            f"starting-kit registry declares unknown subrace(s): {sorted(unknown)}"
        )
    for registry_key, kit in registry.items():
        _validate_starting_kit(registry_key, kit)


_validate_starting_kit_coverage(SUBRACE_STARTING_KIT_REGISTRY)
