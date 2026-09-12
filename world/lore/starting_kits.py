"""Deterministic per-subrace basic starting equipment kits for custom creation."""

from dataclasses import dataclass
from collections.abc import Sequence

from world.lore.items import ITEM_REGISTRY
from world.lore.races import SUBRACE_REGISTRY
from world.skills.equipment import ACCESSORY_MAX_SLOTS, EquipmentSlot


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


def validate_wearable_loadout(
    item_keys: Sequence[str], *, owner: str, declaration: str
) -> None:
    """Reject a declared wearable set the equipment writer could never fully wear.

    The shared arithmetic behind both lore validators (custom-kit-worn-at-
    activation D3): duplicate keys, a key whose ``ItemDefinition.equipment_slot``
    is ``None``, two keys claiming one singleton slot, and more accessories than
    ``ACCESSORY_MAX_SLOTS``. Every rule is an authoring mistake with no useful
    runtime meaning, because ``world/rules/equipment.py::toggle_equipment``
    TOGGLES rather than equips, silently replaces a singleton occupant, and
    rejects a sixth accessory at runtime — so each raises at registry load
    instead of mid-activation. ``owner`` (e.g. ``"starting kit 'human_plains'"``)
    and ``declaration`` (the noun each validator names the entry by: ``"item"``
    for kits, ``"starting equipment"`` for presets) parameterize only the stable
    message shapes; the rules themselves are shared so the cap and singleton
    semantics can never drift between the two callers. The singleton/accessory
    arithmetic reads ``world/skills/equipment.py`` (lore already depends on
    ``world/skills/``), never ``world.rules``.
    """
    seen: set[str] = set()
    singleton_owner: dict[EquipmentSlot, str] = {}
    accessory_count = 0
    for item_key in item_keys:
        if item_key in seen:
            raise ValueError(
                f"{owner} declares duplicate {declaration} {item_key!r}"
            )
        seen.add(item_key)
        definition = ITEM_REGISTRY.get(item_key)
        if definition is None or definition.equipment_slot is None:
            raise ValueError(
                f"{owner} declares {declaration} {item_key!r} that is not equipment"
            )
        slot = definition.equipment_slot
        if slot is EquipmentSlot.ACCESSORY:
            accessory_count += 1
            if accessory_count > ACCESSORY_MAX_SLOTS:
                raise ValueError(
                    f"{owner} declares more than {ACCESSORY_MAX_SLOTS} "
                    f"starting accessories"
                )
        else:
            prior = singleton_owner.get(slot)
            if prior is not None:
                raise ValueError(
                    f"{owner} declares {declaration} {item_key!r} and "
                    f"{prior!r} claiming the same {slot.value} slot"
                )
            singleton_owner[slot] = item_key


SUBRACE_STARTING_KIT_REGISTRY: dict[str, SubraceStartingKit] = {
    kit.subrace_key: kit
    for kit in (
        _kit("human_royal", "gilded_saber", "chainmail", "silver_hairpin"),
        _kit("human_noble", "knight_blade", "leather_armor", "silver_hairpin"),
        _kit("human_coastal", "plain_sword", "leather_armor", "iron_dagger"),
        _kit("human_plains", "plain_sword", "leather_armor", "silver_hairpin"),
        _kit("human_highland", "plain_sword", "leather_armor", "hunting_throwing_axe"),
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
    lookup so malformed hand-built entries fail with a stable ValueError. The
    wearable-set arithmetic (duplicates, singleton-slot collisions, accessory
    cap) runs through the shared helper once activation wears every kit item
    (custom-kit-worn-at-activation D3): a kit that cannot be fully worn is an
    authoring typo, and worn it would turn into a failed player activation.
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
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError(
                f"starting kit {registry_key!r} declares a non-positive "
                f"quantity for {item_key!r}"
            )
    validate_wearable_loadout(
        tuple(item_key for item_key, _ in kit.items),
        owner=f"starting kit {registry_key!r}",
        declaration="item",
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
