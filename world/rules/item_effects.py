"""The declarative item-effect model and its validated rulebook loader.

Item mechanics identity lives in the immutable lore registry; every tunable
effect — what an item does, how much, and to whom — lives in
``rulebook/item_effects.yaml`` keyed by the item key and is read only through
the validated loader in this module (item-effect-model design §3). One item
profile is an ordered tuple of typed effect entries; an item with no effect
entry is simply unusable through the registry's ``use_mechanics`` flag, never
through a magic effect key.

Forward-declared seam (design D4, tasks 4.4): the full target-scope
vocabulary is defined and validated here, and every member maps to exactly
one :class:`~world.rules.targeting.TargetRequirement` plus the group
shorthand its candidates expand through (``scope_targeting_rule``,
add-item-effect-targeting). An item's reach is a property of the item: the
rulebook fixes it, and no caller input widens or narrows it. The vocabulary
itself is frozen — the targeting change adds reach behaviour, never new
scope words.

Consumers resolve an item's profile through the module-level
:data:`ITEM_EFFECT_PROFILES` map at call time (``items.py`` reads the module
attribute, never a name-imported copy), so the synthetic-data kit's scoped
``item_effect_profiles`` target and ``reload_item_effect_rules()`` reach the
settlement path through the same object.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Union

import yaml

from world.rules.targeting import TargetRequirement
from world.skills.registry import FactionConstraint, TargetSpec

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.clock import MAX_ADVANCE_SECONDS

_RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "item_effects.yaml"

#: One effect entry may move at most this many points of any gauge; the
#: loader rejects larger magnitudes so a malformed rulebook can never
#: smuggle an unbounded heal into settlement.
MAX_EFFECT_AMOUNT = 9999

#: The polarity-wide words ``world.rules.buffs.remove_by_selector``
#: understands. A status-apply entry must name one concrete definition key;
#: only a removal may name one of these words.
_REMOVE_SELECTORS = frozenset({"all", "positive", "negative"})


class ItemEffectsRulebookError(ValueError):
    """The item-effect rulebook is malformed, unknown, or out of bounds."""


class ItemStat(StrEnum):
    """The closed vocabulary of gauges an item effect may adjust."""

    HP = "hp"
    MP = "mp"
    SP = "sp"
    PLEASURE = "pleasure"


class ItemTargetScope(StrEnum):
    """The closed vocabulary of effect target scopes.

    Every member is validated by the loader and maps to exactly one
    :class:`~world.rules.targeting.TargetRequirement` plus the group
    shorthand its candidates expand through (item-effect-model design
    §4.2/§5.2). An item's reach is a property of the item: the rulebook
    fixes it, and no caller input widens or narrows it.
    """

    SELF = "self"
    SINGLE = "single"
    ALL_ALLIES = "all-allies"
    ALL_ENEMIES = "all-enemies"
    ALL = "all"


@dataclass(frozen=True)
class ScopeTargetingRule:
    """The fixed targeting rule one scope value maps to (design §4.2).

    ``requirement`` is the single :class:`TargetRequirement` the shared
    resolver consumes for the scope — the identical presence/alive/range/
    faction pipeline a skill's targets pass. ``shorthand`` names the group
    the scope reaches when it is a group scope (``None`` for the acting
    entity and the single explicit target); group candidates expand through
    the action context by that shorthand's semantics, never by a caller
    choice.
    """

    requirement: TargetRequirement
    shorthand: str | None = None


_SCOPE_TARGETING_RULES: dict[ItemTargetScope, ScopeTargetingRule] = {
    ItemTargetScope.SELF: ScopeTargetingRule(
        TargetRequirement(TargetSpec.SELF, FactionConstraint.SELF_ONLY)
    ),
    ItemTargetScope.SINGLE: ScopeTargetingRule(
        TargetRequirement(TargetSpec.SINGLE)
    ),
    ItemTargetScope.ALL_ALLIES: ScopeTargetingRule(
        TargetRequirement(TargetSpec.AREA), "all-allies"
    ),
    ItemTargetScope.ALL_ENEMIES: ScopeTargetingRule(
        TargetRequirement(TargetSpec.AREA), "all-enemies"
    ),
    ItemTargetScope.ALL: ScopeTargetingRule(
        TargetRequirement(TargetSpec.AREA), "all"
    ),
}


def scope_targeting_rule(scope: ItemTargetScope) -> ScopeTargetingRule:
    """Return the one targeting rule the rulebook fixed for ``scope``."""
    if not isinstance(scope, ItemTargetScope):
        raise ValueError(f"scope must be an ItemTargetScope member, got {scope!r}")
    return _SCOPE_TARGETING_RULES[scope]


@dataclass(frozen=True)
class GaugeAdjustEffect:
    """One bounded signed adjustment to one gauge on entries in ``scope``.

    ``amount`` is signed: positive raises the gauge, negative drains it, and
    zero is never valid (an entry that does nothing is a rulebook mistake,
    not a no-op effect).
    """

    stat: ItemStat
    amount: int
    scope: ItemTargetScope = ItemTargetScope.SELF

    def __post_init__(self) -> None:
        if not isinstance(self.stat, ItemStat):
            raise ValueError(f"stat must be an ItemStat member, got {self.stat!r}")
        if isinstance(self.amount, bool) or not isinstance(self.amount, int):
            raise ValueError(f"amount must be an integer, got {self.amount!r}")
        if self.amount == 0:
            raise ValueError("amount must not be zero")
        if not isinstance(self.scope, ItemTargetScope):
            raise ValueError(f"scope must be an ItemTargetScope member, got {self.scope!r}")


@dataclass(frozen=True)
class StatusApplyEffect:
    """Apply one concrete status definition to every entity in ``scope``."""

    status: str
    scope: ItemTargetScope = ItemTargetScope.SELF

    def __post_init__(self) -> None:
        if not isinstance(self.status, str) or not self.status:
            raise ValueError("status must be a non-empty string")
        if self.status in _REMOVE_SELECTORS:
            raise ValueError(
                f"status {self.status!r} is a removal selector, not a concrete "
                "status definition key"
            )
        if not isinstance(self.scope, ItemTargetScope):
            raise ValueError(f"scope must be an ItemTargetScope member, got {self.scope!r}")


@dataclass(frozen=True)
class StatusRemoveEffect:
    """Remove matching status instances from every entity in ``scope``.

    ``selector`` is either one concrete definition key or one of the
    polarity-wide words ``all``/``positive``/``negative``.
    """

    selector: str
    scope: ItemTargetScope = ItemTargetScope.SELF

    def __post_init__(self) -> None:
        if not isinstance(self.selector, str) or not self.selector:
            raise ValueError("selector must be a non-empty string")
        if not isinstance(self.scope, ItemTargetScope):
            raise ValueError(f"scope must be an ItemTargetScope member, got {self.scope!r}")


ItemEffect = Union[GaugeAdjustEffect, StatusApplyEffect, StatusRemoveEffect]


@dataclass(frozen=True)
class ItemEffectProfile:
    """The ordered, complete effect declaration of one usable item.

    Settlement executes the entries in order (design §5.1). An item may
    declare at most one gauge adjustment per stat — two adjustments to the
    same gauge are ambiguous, not additive (design D3).
    """

    effects: tuple[ItemEffect, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.effects, tuple) or not self.effects:
            raise ValueError("effects must be a non-empty tuple")
        for effect in self.effects:
            if not isinstance(effect, (GaugeAdjustEffect, StatusApplyEffect, StatusRemoveEffect)):
                raise ValueError(f"unknown effect entry {effect!r}")
        adjusted: list[str] = []
        for effect in self.effects:
            if isinstance(effect, GaugeAdjustEffect):
                if effect.stat in adjusted:
                    raise ValueError(
                        f"profile adjusts {effect.stat.value!r} more than once"
                    )
                adjusted.append(effect.stat)


# Per-verb field vocabularies: every entry key beyond the verb and ``scope``
# is rejected, so a malformed entry can never carry a stray amount.
_ENTRY_FIELDS: dict[str, frozenset[str]] = {
    "stat": frozenset({"stat", "amount", "scope"}),
    "apply_status": frozenset({"apply_status", "scope"}),
    "remove_status": frozenset({"remove_status", "scope"}),
}
_ENTRY_VERBS = frozenset(_ENTRY_FIELDS)


def _parse_effect_entry(entry: Any, field: str, buff_definitions: Mapping[str, Any]) -> ItemEffect:
    """Parse one effect-entry mapping into exactly one typed effect."""
    if not isinstance(entry, Mapping):
        raise ItemEffectsRulebookError(f"{field}: effect entry must be a mapping")
    verbs = _ENTRY_VERBS.intersection(entry)
    if not verbs:
        raise ItemEffectsRulebookError(
            f"{field}: effect entry must declare exactly one of "
            "stat/apply_status/remove_status"
        )
    if len(verbs) > 1:
        raise ItemEffectsRulebookError(
            f"{field}: effect entry declares more than one effect verb "
            f"{sorted(verbs)}"
        )
    verb = next(iter(verbs))
    extra = set(entry) - _ENTRY_FIELDS[verb]
    if extra:
        raise ItemEffectsRulebookError(
            f"{field}: effect entry carries unknown fields {sorted(extra)}"
        )
    scope = _parse_scope(entry.get("scope", ItemTargetScope.SELF.value), field)
    if verb == "stat":
        return GaugeAdjustEffect(
            stat=_parse_stat(entry["stat"], field),
            amount=_parse_amount(entry.get("amount"), field),
            scope=scope,
        )
    name = entry[verb]
    if not isinstance(name, str) or not name:
        raise ItemEffectsRulebookError(f"{field}: {verb} must be a non-empty string")
    if verb == "apply_status":
        if name in _REMOVE_SELECTORS:
            raise ItemEffectsRulebookError(
                f"{field}: apply_status {name!r} is a removal selector; "
                "apply needs a concrete status key"
            )
        if buff_definitions.get(name) is None:
            raise ItemEffectsRulebookError(
                f"{field}: apply_status names unknown status {name!r}"
            )
        return StatusApplyEffect(status=name, scope=scope)
    if name not in _REMOVE_SELECTORS and buff_definitions.get(name) is None:
        raise ItemEffectsRulebookError(
            f"{field}: remove_status names neither a selector nor a known "
            f"status {name!r}"
        )
    return StatusRemoveEffect(selector=name, scope=scope)


def _parse_scope(value: Any, field: str) -> ItemTargetScope:
    """Parse one scope word from the closed five-member vocabulary."""
    if not isinstance(value, str):
        raise ItemEffectsRulebookError(f"{field}: scope must be a string")
    try:
        scope = ItemTargetScope(value)
    except ValueError:
        raise ItemEffectsRulebookError(f"{field}: unknown target scope {value!r}") from None
    return scope


def _parse_stat(value: Any, field: str) -> ItemStat:
    if not isinstance(value, str):
        raise ItemEffectsRulebookError(f"{field}: stat must be a string")
    try:
        return ItemStat(value)
    except ValueError:
        raise ItemEffectsRulebookError(f"{field}: unknown stat {value!r}") from None


def _parse_amount(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ItemEffectsRulebookError(f"{field}: stat amount must be an integer")
    if value == 0:
        raise ItemEffectsRulebookError(f"{field}: stat amount must not be zero")
    if not -MAX_EFFECT_AMOUNT <= value <= MAX_EFFECT_AMOUNT:
        raise ItemEffectsRulebookError(
            f"{field}: stat amount must be between -{MAX_EFFECT_AMOUNT} "
            f"and {MAX_EFFECT_AMOUNT}"
        )
    return value


def validate_item_effect_rules(
    document: Any,
    registry: Mapping[str, Any],
    buff_definitions: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one parsed rulebook against the live item and buff catalogs.

    Returns ``{"item_use_seconds": int, "profiles": {item_key:
    ItemEffectProfile}}``. The items mapping must align bi-directionally
    with the registry's usable key set: an orphan entry names an item the
    registry does not allow to be used, and a missing entry leaves a usable
    item with no declared effect — both fail validation at startup.
    """
    if not isinstance(document, Mapping) or set(document) != {"item_use_seconds", "items"}:
        raise ItemEffectsRulebookError(
            "rulebook must declare exactly item_use_seconds and items"
        )
    seconds = document["item_use_seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise ItemEffectsRulebookError("item_use_seconds must be an integer")
    if not 1 <= seconds <= MAX_ADVANCE_SECONDS:
        raise ItemEffectsRulebookError(
            f"item_use_seconds must be between 1 and {MAX_ADVANCE_SECONDS}"
        )
    items = document["items"]
    if not isinstance(items, Mapping):
        raise ItemEffectsRulebookError("items must be a mapping")
    usable = {
        key
        for key, definition in registry.items()
        if getattr(definition, "use_mechanics", None) is not None
    }
    orphans = set(items) - usable
    if orphans:
        raise ItemEffectsRulebookError(
            f"items declare entries no usable item needs {sorted(orphans)}"
        )
    missing = usable - set(items)
    if missing:
        raise ItemEffectsRulebookError(
            f"usable items without effect profiles {sorted(missing)}"
        )
    profiles: dict[str, ItemEffectProfile] = {}
    for item_key, entry in items.items():
        field = f"items.{item_key}"
        if not isinstance(entry, Mapping) or set(entry) != {"effects"}:
            raise ItemEffectsRulebookError(f"{field} must carry exactly effects")
        effect_entries = entry["effects"]
        if not isinstance(effect_entries, list) or not effect_entries:
            raise ItemEffectsRulebookError(f"{field}.effects must be a non-empty list")
        parsed: list[ItemEffect] = []
        for position, effect_entry in enumerate(effect_entries, start=1):
            parsed.append(
                _parse_effect_entry(
                    effect_entry, f"{field}.effects[{position}]", buff_definitions
                )
            )
        try:
            profiles[item_key] = ItemEffectProfile(effects=tuple(parsed))
        except ValueError as error:
            raise ItemEffectsRulebookError(f"{field}: {error}") from None
    return {"item_use_seconds": seconds, "profiles": profiles}


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys at any nesting level.

    PyYAML's default mapping constructor silently keeps the LAST duplicate,
    so a rulebook reviewed by a human and the data actually loaded could
    disagree. Fail-loud contract (mirroring ``equipment_effects.py``):
    duplicates are malformed data.
    """

    def construct_mapping(self, node: Any, deep: bool = False) -> Any:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise ItemEffectsRulebookError(
                    "duplicate YAML mapping key "
                    f"{key!r} at line {key_node.start_mark.line + 1}"
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_item_effect_rules(
    path: Path | None = None,
    registry: Mapping[str, Any] | None = None,
    buff_definitions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load and validate the item-effect rulebook.

    Defaults to the canonical rulebook file, the live lore item registry, and
    the live buff definitions; every parameter is injectable so loader tests
    run against fabricated catalogs without touching shipped content.
    """
    document = yaml.load(
        (path or _RULEBOOK_PATH).read_text(encoding="utf-8"),
        Loader=_UniqueKeyLoader,
    )
    if registry is None:
        from world.lore.items import ITEM_REGISTRY

        registry = ITEM_REGISTRY
    if buff_definitions is None:
        buff_definitions = BUFF_DEFINITIONS
    return validate_item_effect_rules(document, registry, buff_definitions)


_loaded = load_item_effect_rules()

#: The canonical out-of-combat item-use time cost, settled through the same
#: command-source advance path as casts.
ITEM_USE_SECONDS: int = _loaded["item_use_seconds"]

#: The live item-effect profile map, keyed by item key. Settlement reads this
#: map through the module attribute at call time; ``reload_item_effect_rules``
#: refreshes it in place so existing references (including the synthetic kit's
#: scoped patches and their restore closures) stay meaningful.
ITEM_EFFECT_PROFILES: dict[str, ItemEffectProfile] = _loaded["profiles"]


def reload_item_effect_rules(
    path: Path | None = None,
    registry: Mapping[str, Any] | None = None,
    buff_definitions: Mapping[str, Any] | None = None,
) -> None:
    """Re-validate and refresh the live profile map in place (idempotent sync).

    Reload outside any open synthetic scope: it refills the live dict with
    production rows, so profiles a still-open ``items`` scope patched in are
    dropped mid-test (the scope's restore closure then reverts them).
    """
    global ITEM_USE_SECONDS
    loaded = load_item_effect_rules(path, registry, buff_definitions)
    ITEM_USE_SECONDS = loaded["item_use_seconds"]
    ITEM_EFFECT_PROFILES.clear()
    ITEM_EFFECT_PROFILES.update(loaded["profiles"])


__all__ = [
    "ItemEffect",
    "ItemEffectProfile",
    "ItemEffectsRulebookError",
    "ItemStat",
    "ItemTargetScope",
    "ITEM_EFFECT_PROFILES",
    "ITEM_USE_SECONDS",
    "MAX_EFFECT_AMOUNT",
    "GaugeAdjustEffect",
    "ScopeTargetingRule",
    "StatusApplyEffect",
    "StatusRemoveEffect",
    "load_item_effect_rules",
    "reload_item_effect_rules",
    "scope_targeting_rule",
    "validate_item_effect_rules",
]
