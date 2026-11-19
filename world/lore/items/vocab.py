"""Vocabulary and value types for the item registry.

Holds the ``SUMMARY_MAX`` bound, the closed ``ItemKind``/``ItemIconKey``/
``ItemRarity``/``LiturgicalRole`` vocabularies, and
the frozen ``ItemUseMechanics``/``ItemPresentation``/``ItemDefinition``
dataclasses, moved verbatim from the head of the single ``world/lore/items.py``
module. ``EquipmentSlot`` stays imported here because ``ItemDefinition``
validates against it at construction.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from world.lore.registry_refs import ref
from world.skills.equipment import EquipmentSlot

# Player-facing item summaries are bounded; the bound mirrors the
# skill-registry label contract.
SUMMARY_MAX = 128


class ItemKind(StrEnum):
    """Closed item-category vocabulary owned by the lore registry."""

    FOOD = "food"
    POTION = "potion"
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    AMMUNITION = "ammunition"
    TOOL = "tool"
    MATERIAL = "material"
    MISC = "misc"
    TOY = "toy"


class ItemIconKey(StrEnum):
    """Closed local-SVG icon vocabulary.

    The Vue renderer maps each key to a self-hosted inline SVG; the registry
    never carries raw SVG, image URLs, CSS values, or emoji.
    """

    FOOD = "food"
    POTION = "potion"
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    AMMUNITION = "ammunition"
    TOOL = "tool"
    MATERIAL = "material"
    MISC = "misc"
    TOY = "toy"


class ItemRarity(StrEnum):
    """Closed rarity vocabulary used for visual treatment only.

    Rarity is a presentation classification, not a balance multiplier; it must
    not feed prices, stock, loot odds, or combat until a reviewed rules
    contract owns that behavior.
    """

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class LiturgicalRole(StrEnum):
    """Closed Church-of-Light liturgical-role vocabulary.

    A role is immutable item lore belonging to the equipment record itself,
    never to its effect entry: a rulebook edit can tune magnitudes but can
    never move an item between doctrine sub-sets or borrow another role's
    exemption (``church-of-light-equipment-obeys-its-canon-doctrine``). An
    item declaring a role must be equipment, so the role always has a worn
    identity to validate against.
    """

    VESTMENT_OR_EMBLEM = "vestment_or_emblem"
    SANCTUARY_DEVICE = "sanctuary_device"


@dataclass(frozen=True)
class ItemUseMechanics:
    """The immutable use semantics of one registered consumable or reusable.

    What a use *does* is declared in the item-effect rulebook keyed by the
    item key (``world/rules/item_effects.py``); this record only states that
    the item can be used and what a use costs structurally; effects never
    live in this registry (item-effect-model design §3.1).
    """

    consumable: bool
    combat_allowed: bool

    def __post_init__(self) -> None:
        """Enforce the boolean flags."""
        for name in ("consumable", "combat_allowed"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True)
class ItemPresentation:
    """The frozen visual identity of one registered item."""

    kind: ItemKind
    icon_key: ItemIconKey
    rarity: ItemRarity
    summary_zh: str

    def __post_init__(self) -> None:
        """Enforce the closed presentation contracts at construction time."""
        for value, vocabulary in (
            (self.kind, ItemKind),
            (self.icon_key, ItemIconKey),
            (self.rarity, ItemRarity),
        ):
            if not isinstance(value, vocabulary):
                raise ValueError(
                    f"{vocabulary.__name__} member required, got {value!r}"
                )
        if not isinstance(self.summary_zh, str) or not self.summary_zh.strip():
            raise ValueError("summary_zh must be a non-empty string")
        if sum(1 for _ in self.summary_zh) > SUMMARY_MAX:
            raise ValueError(f"summary_zh exceeds {SUMMARY_MAX} code points")
        if any(breaker in self.summary_zh for breaker in ("\r", "\n", "\u2028", "\u2029")):
            raise ValueError("summary_zh must be a single line of plain text")
        if "<" in self.summary_zh:
            raise ValueError("summary_zh must not contain markup")
        if (
            "://" in self.summary_zh
            or self.summary_zh.startswith("//")
            or " //" in self.summary_zh
        ):
            raise ValueError("summary_zh must not contain URL forms")
        if any(
            0x2600 <= ord(ch) <= 0x27BF
            or 0x1F000 <= ord(ch) <= 0x1FAFF
            or 0x1F1E6 <= ord(ch) <= 0x1F1FF
            or ch in ("\u200d", "\u20e3", "\ufe0f")
            for ch in self.summary_zh
        ):
            raise ValueError("summary_zh must not contain emoji or emoji sequence parts")


@dataclass(frozen=True)
class ItemDefinition:
    """The immutable identity of one supported inventory item.

    Exactly one of ``use_mechanics`` or ``equipment_slot`` may be present;
    an item carrying neither is inspect-only. The pair is validated at
    construction so an ambiguous definition can never be presented or used.
    A slotted item's dedicated effect mapping is authored on its own row in
    ``content/items/`` and bound by its own key; magnitudes never live here.
    """

    key: str
    display_name_zh: str
    price_table_key: str = field(metadata=ref("prices", inverse="items"))
    sellable: bool
    presentation: ItemPresentation
    use_mechanics: ItemUseMechanics | None = None
    equipment_slot: EquipmentSlot | None = None
    guild_property: bool = False
    # The Church-of-Light liturgical role this equipment plays, if any: the
    # immutable item-lore classification that owns doctrine coverage, so an
    # effect-rule edit can never reclassify a vestment into (or out of) a
    # doctrine sub-set.
    liturgical_role: LiturgicalRole | None = None

    def __post_init__(self) -> None:
        """Require the frozen presentation object and exclusive mechanics."""
        if not isinstance(self.guild_property, bool):
            raise ValueError("guild_property must be a boolean")
        if self.guild_property and self.sellable:
            raise ValueError("guild property cannot be sellable")
        if self.liturgical_role is not None:
            if not isinstance(self.liturgical_role, LiturgicalRole):
                raise ValueError(
                    f"item {self.key!r} liturgical_role must be a "
                    f"LiturgicalRole member, got {self.liturgical_role!r}"
                )
            if self.equipment_slot is None:
                raise ValueError(
                    f"item {self.key!r} declares liturgical_role "
                    f"{self.liturgical_role.value!r} without an equipment "
                    "slot; doctrine roles describe worn equipment only"
                )
        if not isinstance(self.presentation, ItemPresentation):
            raise ValueError(
                f"item {self.key!r} presentation must be an ItemPresentation"
            )
        if self.use_mechanics is not None and self.equipment_slot is not None:
            raise ValueError(
                f"item {self.key!r} declares both use mechanics and an "
                "equipment slot; the forms are mutually exclusive"
            )
        if self.use_mechanics is not None and not isinstance(
            self.use_mechanics, ItemUseMechanics
        ):
            raise ValueError(
                f"item {self.key!r} use_mechanics must be an ItemUseMechanics"
            )
        if self.equipment_slot is not None and not isinstance(
            self.equipment_slot, EquipmentSlot
        ):
            raise ValueError(
                f"item {self.key!r} equipment_slot must be an EquipmentSlot "
                f"member, got {self.equipment_slot!r}"
            )


