"""Frozen no-create status read model for the WebClient status presenter.

Presentation must never materialize lazy handlers or default state. This module
reads only the persistent trait attribute, optional buff cache, sexual baseline
or materialized traits, creation flag, disguise record, and combat-session
record, and interprets them in memory. It never constructs ``entity.traits``,
``entity.buffs``, or ``entity.sexual`` and never writes to storage.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat_modifiers import matched_combat_modifiers
from world.rules.equipment_effects import effective_exposure
from world.rules.sexual_state import PLEASURE_CONFIG, _LIFETIME_COUNTER_KEYS
from world.rules.status_display import display_for
from world.rules.stored_sexual_reads import StoredLevel
from world.skills.equipment import dual_wielding_from_storage
from world.skills.handler import INNATE_SKILL_KEYS, INNATE_SKILL_ORDER
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillDef, SkillKind
from world.skills.sexual_acts import unlocked_act_keys_for

# Stable Traditional Chinese labels for the canonical trait keys, shared by
# every presentation surface: the WebClient character panel and the
# displayed-stats block appended on ``look <target>`` (displayed-stats-view
# A2). Consumers must read this map instead of duplicating the labels.
TRAIT_LABELS = {
    "hp": "生命",
    "mp": "魔力",
    "sp": "耐力",
    "atk_phys": "攻擊",
    "agility": "敏捷",
    "defense": "防禦",
    "magic_level": "魔法階級",
    "guild_merit": "功績",
}

_GAUGE_KEYS = ("hp", "mp", "sp")
_STATIC_KEYS = ("atk_phys", "agility", "defense")
_COUNTER_KEYS = ("magic_level", "guild_merit")
_EQUIPMENT_SLOTS = ("weapon_main", "weapon_off", "armor")
_BUFF_CACHE_KEY = "buffs"
_SEXUAL_TRAITS_KEY = "sexual_traits"
_SEXUAL_TRAITS_CATEGORY = "traits"

# Stable Traditional Chinese labels for the skill-category taxonomy, shared by
# the out-of-combat character listing. The combat panel's equivalent mapping
# lives in combat_view.py; both iterate ``SkillCategory``'s declaration order,
# so the label text is the only deliberately duplicated part (see the
# skill-category-status-listing design D-2).
_CATEGORY_LABELS = {
    SkillCategory.ELEMENTAL_MAGIC: "元素魔法",
    SkillCategory.MARTIAL_ARTS: "武技",
    SkillCategory.ENHANCEMENT: "強化",
    SkillCategory.INNATE_GIFT: "天賦",
    SkillCategory.MOVEMENT: "移動",
    SkillCategory.DIVINE_MYSTERY: "神之秘法",
    SkillCategory.UTILITY: "特殊",
    SkillCategory.SEXUAL_ACT: "性愛行為",
}
# Presentation-only fallback bucket for keys absent from ``SKILL_REGISTRY``.
# ``"unknown"`` is a plain string sentinel, never a ``SkillCategory`` member:
# it has no position in that enum's declaration order and is appended after
# every real category.
_UNKNOWN_CATEGORY = "unknown"
_UNKNOWN_CATEGORY_LABEL = "未知技能"


class StatusQueryError(ValueError):
    """Required canonical state is missing, malformed, or could not be read."""


@dataclass(frozen=True)
class GaugeValue:
    current: int
    maximum: int


@dataclass(frozen=True)
class _LevelRef:
    """Read-only ordinal comparison mirror for an ordered level trait."""

    value: int
    levels: tuple[str, ...]

    def _ordinal_of(self, other: Any) -> int:
        if isinstance(other, _LevelRef):
            return other.value
        if isinstance(other, str):
            return self.levels.index(other)
        return int(other)

    def __eq__(self, other: object) -> bool:
        return self.value == self._ordinal_of(other)

    def __ge__(self, other: object) -> bool:
        return self.value >= self._ordinal_of(other)

    def __gt__(self, other: object) -> bool:
        return self.value > self._ordinal_of(other)

    def __le__(self, other: object) -> bool:
        return self.value <= self._ordinal_of(other)

    def __lt__(self, other: object) -> bool:
        return self.value < self._ordinal_of(other)


@dataclass(frozen=True)
class ConditionValue:
    code: str
    label: str
    severity: str
    remaining_seconds: int | None
    modifiers: dict[str, Any]


@dataclass(frozen=True)
class StatusReadModel:
    """The complete read-only inputs a presenter may serialize."""

    actor_name: str
    actor_identity: str
    location_label: str | None
    location_identity: str | None
    resources: dict[str, GaugeValue]
    conditions: tuple[ConditionValue, ...]
    disguise_active: bool
    combat_mode: str | None
    combat_round: int | None
    creation_pending: bool


@dataclass(frozen=True)
class CharacterTraitView:
    """One read-only character trait row: gauges report current/maximum."""

    key: str
    current: int
    maximum: int | None


@dataclass(frozen=True)
class CharacterEquipmentView:
    """One read-only equipped item row (slot plus canonical item key)."""

    slot: str
    item_key: str


@dataclass(frozen=True)
class CharacterSkillRow:
    """One read-only skill row: registry key plus display label."""

    key: str
    label: str


@dataclass(frozen=True)
class CharacterSkillGroupView:
    """One read-only sub-group of skill rows inside a character-panel category.

    ``group``/``label`` are both ``None`` for the single ungrouped sub-group a
    category with no second level emits; otherwise the pair carries the group
    key and its display label.
    """

    group: str | None
    label: str | None
    skills: tuple[CharacterSkillRow, ...]


@dataclass(frozen=True)
class CharacterCategoryGroupView:
    """One read-only category group of owned skill rows."""

    category: str
    label: str
    groups: tuple[CharacterSkillGroupView, ...]


@dataclass(frozen=True)
class IntimateView:
    """Read-only intimate-status values: level words plus the daily climax count."""

    arousal: str
    wetness: str
    shame: str
    exposure: str
    climax_phase: str
    climax_today: int


@dataclass(frozen=True)
class CharacterReadModel:
    """The complete read-only inputs of the version-4 ``character`` panel.

    Shares the same canonical trait storage the compact ``status`` panel reads,
    so the two panels cannot drift apart: gauges go through the same strict
    ``_require_gauge`` parser and statics/counters through the same trait dict.
    Every value is true state; ``disguise_displayed`` is reported separately
    and is never substituted for a true trait.
    """

    traits: tuple[CharacterTraitView, ...]
    active_keys: tuple[str, ...]
    passive_keys: tuple[str, ...]
    equipment: tuple[CharacterEquipmentView, ...]
    disguise_active: bool
    disguise_displayed: tuple[tuple[str, int], ...]
    guild_rank: str | None
    guild_merit: int
    wallet: int
    intimate: IntimateView | None


def _read_attribute(entity: Any, key: str, default=None, category: str | None = None) -> Any:
    return entity.attributes.get(key, default=default, category=category)


def _require_gauge(data: dict[str, Any], key: str) -> GaugeValue:
    """Read one gauge trait dict strictly without constructing a handler."""
    raw = data.get(key)
    if not isinstance(raw, Mapping):
        raise StatusQueryError(f"missing gauge trait {key!r}")
    base = raw.get("base")
    mod = raw.get("mod", 0)
    mult = raw.get("mult", 1)
    if isinstance(base, bool) or not isinstance(base, int):
        raise StatusQueryError(f"gauge {key!r} base is not an integer")
    if isinstance(mod, bool) or not isinstance(mod, (int, float)):
        raise StatusQueryError(f"gauge {key!r} mod is not numeric")
    if isinstance(mult, bool) or not isinstance(mult, (int, float)):
        raise StatusQueryError(f"gauge {key!r} mult is not numeric")
    maximum = int(round((base + mod) * mult))
    if maximum <= 0:
        raise StatusQueryError(f"gauge {key!r} has a non-positive maximum")
    current = raw.get("current")
    if current is None:
        # GaugeTrait defaults an unset current to full.
        current = maximum
    if isinstance(current, bool) or not isinstance(current, int):
        raise StatusQueryError(f"gauge {key!r} current is not an integer")
    if current < 0:
        raise StatusQueryError(f"gauge {key!r} current is negative")
    if current > maximum:
        raise StatusQueryError(f"gauge {key!r} current exceeds maximum")
    return GaugeValue(current=current, maximum=maximum)


def _read_buff_cache(entity: Any) -> dict[str, Any]:
    """Return the persisted buff cache dict without creating a handler."""
    cache = _read_attribute(entity, _BUFF_CACHE_KEY, default={})
    if cache is None:
        return {}
    if not isinstance(cache, Mapping):
        raise StatusQueryError("buff cache is malformed")
    return dict(cache)


def _active_buff_entries(entity: Any) -> list[tuple[str, dict[str, Any]]]:
    """Return unpaused, positive-stack, unexpired buff cache entries."""
    entries: list[tuple[str, dict[str, Any]]] = []
    for buff_key, cache in _read_buff_cache(entity).items():
        if not isinstance(cache, Mapping):
            raise StatusQueryError(f"buff {buff_key!r} cache is malformed")
        cache = dict(cache)
        if cache.get("paused"):
            continue
        stacks = cache.get("stacks")
        if not isinstance(stacks, int) or stacks <= 0:
            continue
        remaining = cache.get("remaining_seconds")
        if isinstance(remaining, int) and remaining <= 0:
            continue
        entries.append((buff_key, cache))
    return entries


def _sexual_level(entity: Any, field: str) -> Any:
    """Read one ordered-level or counter trait in memory without a handler.

    Returns a read-only :class:`_LevelRef` for ordinal comparison, the stored
    level string when only a baseline is available, or ``None`` when the
    record is entirely absent. A present-but-malformed record fails closed.
    Never creates ``entity.sexual``.
    """
    traits = _read_attribute(
        entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    if field == "arousal":
        if isinstance(traits, Mapping) and "pleasure" in traits:
            raw = traits["pleasure"]
            base = raw.get("base") if isinstance(raw, Mapping) else None
            if isinstance(base, int) and not isinstance(base, bool):
                # Defensive: CounterTrait.base's own setter clamps writes into
                # [0, 100], so an out-of-range stored value implies corrupted
                # storage; clamp it so the ordinal lookup still resolves.
                base = min(100, max(0, base))
                return _LevelRef(
                    PLEASURE_CONFIG.ordinal_for(base), AROUSAL_LEVELS
                )
            return None
    elif isinstance(traits, Mapping) and field in traits:
        raw = traits[field]
        if isinstance(raw, Mapping):
            value = raw.get("value")
            levels = raw.get("levels") or ()
            if isinstance(value, str):
                return _LevelRef(_ordinal_of(levels, value), tuple(levels)) if levels else value
            if isinstance(value, int):
                if isinstance(levels, (list, tuple)) and 0 <= value < len(levels):
                    return _LevelRef(value, tuple(levels))
            return value
    baseline = _read_attribute(entity, "sexual", default=None)
    if baseline is None:
        return None
    if not isinstance(baseline, Mapping) or not isinstance(baseline.get(field), str):
        raise StatusQueryError(f"sexual state {field!r} is malformed")
    return baseline[field]


def _ordinal_of(levels: tuple[str, ...], label: str) -> int:
    try:
        return levels.index(label)
    except ValueError as error:
        raise StatusQueryError(f"unknown level {label!r}") from error


_INTIMATE_LEVEL_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("wetness", WETNESS_LEVELS),
    ("shame", SHAME_LEVELS),
    ("exposure", EXPOSURE_LEVELS),
    ("climax_phase", CLIMAX_PHASE_LEVELS),
)


def _sexual_counter(entity: Any, field: str) -> int | None:
    """Read one sexual counter trait in memory without a handler.

    Reads the materialized ``sexual_traits`` entry the same way
    ``_require_static_trait`` prefers ``raw.get("current", raw.get("base"))``.
    Absent a materialized record, falls back to the baseline's ``climax_today``
    (default ``0`` when the key is missing), or ``None`` when no record exists
    at all. A present-but-malformed record fails closed. Never creates
    ``entity.sexual``.
    """
    traits = _read_attribute(
        entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    if isinstance(traits, Mapping) and field in traits:
        raw = traits[field]
        if not isinstance(raw, Mapping):
            raise StatusQueryError(f"sexual counter {field!r} is malformed")
        value = raw.get("current", raw.get("base"))
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise StatusQueryError(f"sexual counter {field!r} is malformed")
        return value
    baseline = _read_attribute(entity, "sexual", default=None)
    if baseline is None:
        return None
    if not isinstance(baseline, Mapping):
        raise StatusQueryError("sexual baseline is malformed")
    value = baseline.get(field, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StatusQueryError(f"sexual baseline {field!r} is malformed")
    return value


def _validate_intimate_level_entry(raw: Any, vocabulary: tuple[str, ...]) -> str:
    """Strictly validate one materialized ordered-level entry, fail-closed."""
    if not isinstance(raw, Mapping):
        raise StatusQueryError("materialized sexual level entry is malformed")
    levels = raw.get("levels")
    # Evennia deserializes nested lists as `_SaverList` (a MutableSequence,
    # not a list/tuple), so accept any non-str sequence and compare its
    # contents against the field's fixed vocabulary.
    if isinstance(levels, str) or not isinstance(levels, Sequence) or tuple(levels) != vocabulary:
        raise StatusQueryError(
            f"materialized sexual level entry levels do not match the fixed vocabulary"
        )
    value = raw.get("value")
    if isinstance(value, bool):
        raise StatusQueryError("materialized sexual level value must not be a boolean")
    if isinstance(value, int) and 0 <= value < len(vocabulary):
        return vocabulary[value]
    if isinstance(value, str) and value in vocabulary:
        return value
    raise StatusQueryError("materialized sexual level value is malformed")


def _effective_exposure_label(entity: Any, stored_label: str) -> str:
    """Return the effective exposure label, falling back to the stored one.

    The equipment overlay (P4 D4) never fails closed on the panel: strict
    stored validation has already passed when this runs, so a view that
    cannot be resolved simply keeps the stored label.
    """
    view = effective_exposure(entity)
    if isinstance(view, StoredLevel) and tuple(view.levels) == EXPOSURE_LEVELS:
        return view.levels[view.value]
    return stored_label


def _read_intimate(entity: Any) -> IntimateView | None:
    """Build the intimate view from no-create-safe readers, or return None.

    A materialized ``sexual_traits`` record must be complete (the ``SexualState``
    handler always writes every intimate entry, so a missing entry is
    corruption that fails the panel closed, never a silent baseline fallback).
    Absent a materialized record, level fields resolve from the import-time
    baseline; absent both, the whole view is ``None``.

    The exposure row renders the EFFECTIVE level (stored ordinal plus worn
    equipment ``exposure_bias``, clamped) while the stored trait is never
    touched; every other row keeps the stored value.
    """
    traits = _read_attribute(
        entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    if isinstance(traits, Mapping):
        required = ("pleasure", "climax_today") + tuple(field for field, _ in _INTIMATE_LEVEL_FIELDS)
        for field in required:
            if field not in traits:
                raise StatusQueryError(f"materialized sexual state is missing {field!r}")
        pleasure = traits["pleasure"]
        if not isinstance(pleasure, Mapping):
            raise StatusQueryError("materialized pleasure counter is malformed")
        base = pleasure.get("base")
        if isinstance(base, bool) or not isinstance(base, int) or not 0 <= base <= 100:
            raise StatusQueryError("materialized pleasure counter base is malformed")
        values = {"arousal": AROUSAL_LEVELS[PLEASURE_CONFIG.ordinal_for(base)]}
        for field, vocabulary in _INTIMATE_LEVEL_FIELDS:
            values[field] = _validate_intimate_level_entry(traits[field], vocabulary)
        return IntimateView(
            arousal=values["arousal"],
            wetness=values["wetness"],
            shame=values["shame"],
            exposure=_effective_exposure_label(entity, values["exposure"]),
            climax_phase=values["climax_phase"],
            climax_today=_sexual_counter(entity, "climax_today"),
        )
    baseline = _read_attribute(entity, "sexual", default=None)
    if baseline is None:
        return None
    if not isinstance(baseline, Mapping):
        raise StatusQueryError("sexual baseline is malformed")
    values = {}
    for field, vocabulary in (("arousal", AROUSAL_LEVELS), *_INTIMATE_LEVEL_FIELDS):
        value = baseline.get(field)
        if value is None:
            raise StatusQueryError(f"sexual baseline is missing {field!r}")
        if isinstance(value, str) and value in vocabulary:
            values[field] = value
        else:
            raise StatusQueryError(f"sexual baseline {field!r} is malformed")
    climax_today = _sexual_counter(entity, "climax_today")
    if climax_today is None:
        return None
    return IntimateView(
        arousal=values["arousal"],
        wetness=values["wetness"],
        shame=values["shame"],
        exposure=_effective_exposure_label(entity, values["exposure"]),
        climax_phase=values["climax_phase"],
        climax_today=climax_today,
    )


def _sexual_condition_context(entity: Any) -> dict[str, Any]:
    """Build the combat-modifier condition context from read-only state.

    The exposure slot carries the EFFECTIVE level (stored plus worn equipment
    bias, clamped) as this module's own immutable ``_LevelRef`` view, so the
    panel's condition chips can never disagree with what combat resolution
    actually matches (add-equipment-sexual-effects D4).
    """
    context: dict[str, Any] = {"active_buffs": {key for key, _ in _active_buff_entries(entity)}}
    for field, levels in (
        ("arousal", AROUSAL_LEVELS),
        ("climax_phase", CLIMAX_PHASE_LEVELS),
    ):
        value = _sexual_level(entity, field)
        if isinstance(value, str) and value in levels:
            context[field] = _LevelRef(_ordinal_of(levels, value), levels)
        elif isinstance(value, _LevelRef):
            context[field] = value
    exposure = effective_exposure(entity)
    if isinstance(exposure, StoredLevel) and exposure.levels == EXPOSURE_LEVELS:
        context["exposure"] = _LevelRef(exposure.value, EXPOSURE_LEVELS)
    context["entity"] = entity
    context["dual_wielding"] = dual_wielding_from_storage(entity)
    return context


def _read_combat(entity: Any) -> tuple[str, int] | None:
    """Read the persistent combat-session record without resolving entities."""
    raw = _read_attribute(entity, "active_combat", default=None)
    if raw is None:
        return None
    if not isinstance(raw, dict) and not isinstance(raw, Mapping):
        raise StatusQueryError("active combat record is malformed")
    mode = raw.get("mode")
    rounds = raw.get("rounds_elapsed")
    if mode not in {"hostile", "guild_exam"}:
        raise StatusQueryError("active combat mode is invalid")
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
        raise StatusQueryError("active combat round is invalid")
    return mode, rounds


def build_status_read_model(entity: Any) -> StatusReadModel:
    """Build the frozen read model or raise :class:`StatusQueryError`.

    Requires exactly the HP, MP, and SP gauges; other required data that is
    missing or malformed also fails closed so the presenter shows unavailable
    rather than fabricating values.
    """
    traits_data = _read_attribute(
        entity, "traits", default=None, category="traits"
    )
    if not isinstance(traits_data, Mapping):
        raise StatusQueryError("trait storage is unavailable")
    traits_data = dict(traits_data)
    resources = {key: _require_gauge(traits_data, key) for key in _GAUGE_KEYS}

    conditions: list[ConditionValue] = []
    for buff_key, cache in _active_buff_entries(entity):
        definition_key = cache.get("definition_key")
        if not isinstance(definition_key, str) or definition_key not in BUFF_DEFINITIONS:
            raise StatusQueryError(f"buff {buff_key!r} has an unknown definition")
        display = display_for(definition_key)
        conditions.append(
            ConditionValue(
                code=definition_key,
                label=display.label,
                severity=display.severity,
                remaining_seconds=cache.get("remaining_seconds"),
                modifiers={},
            )
        )

    # Deterministic combat-modifier matches, read-only.
    context = _sexual_condition_context(entity)
    for rule_id, adjustments in matched_combat_modifiers(entity, context=context):
        display = display_for(rule_id)
        conditions.append(
            ConditionValue(
                code=rule_id,
                label=display.label,
                severity=display.severity,
                remaining_seconds=None,
                modifiers=dict(adjustments),
            )
        )

    combat = _read_combat(entity)
    identity = str(entity.pk)
    location = getattr(entity, "location", None)
    return StatusReadModel(
        actor_name=str(getattr(entity, "key", "?")),
        actor_identity=identity,
        location_label=None if location is None else str(location.key),
        location_identity=None if location is None else str(location.pk),
        resources=resources,
        conditions=tuple(conditions),
        disguise_active=bool(_read_attribute(entity, "disguised_stats", default=None)),
        combat_mode=None if combat is None else combat[0],
        combat_round=None if combat is None else combat[1],
        creation_pending=bool(getattr(entity, "creation_pending", False)),
    )


def _require_static_trait(traits_data: dict[str, Any], key: str) -> int:
    raw = traits_data.get(key)
    if not isinstance(raw, Mapping):
        raise StatusQueryError(f"trait {key!r} is missing")
    base = raw.get("current", raw.get("base"))
    if isinstance(base, bool) or not isinstance(base, int):
        raise StatusQueryError(f"trait {key!r} base is not an integer")
    return base


def _read_guild_merit(traits_data: dict[str, Any]) -> int:
    merit = _require_static_trait(traits_data, "guild_merit")
    if merit < 0:
        raise StatusQueryError("guild_merit is negative")
    return merit


def _split_active_passive_keys(entity: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split the entity's owned skill keys into active and passive buckets.

    Pure no-create read: base owned keys come from the stored
    ``entity.db.skills`` lists plus the innate grants (the same set
    ``SkillHandler.base_owned_keys()`` returns), and the unlocked sexual acts
    are computed from the registry and the materialized counters via
    ``unlocked_act_keys_for`` — without ever mounting ``entity.skills`` or
    ``entity.sexual``. Each key is routed by its registry ``SkillKind``; a
    key absent from ``SKILL_REGISTRY`` stays in whichever stored bucket it
    was actually recorded in (defaulting to passive), matching the
    pre-change raw-list semantics so unknown keys degrade rather than raise.
    A key that is neither registry-known, nor stored, nor innate is dropped:
    it can only come from a malformed stored list (for example
    ``"passive": "none"``), and must never surface as junk rows.
    """
    raw = entity.db.skills
    if not isinstance(raw, Mapping):
        raw = {}
    raw_active = raw.get("active")
    raw_passive = raw.get("passive")
    if not _is_list_like(raw_active):
        raw_active = ()
    if not _is_list_like(raw_passive):
        raw_passive = ()
    stored_keys = {
        key for key in (*raw_active, *raw_passive) if isinstance(key, str) and key
    }
    raw_active_keys = {key for key in raw_active if isinstance(key, str) and key}

    base_keys: list[str] = [
        key for key in (*raw_active, *raw_passive) if isinstance(key, str) and key
    ]
    base_keys.extend(INNATE_SKILL_ORDER)

    # Act-unlock counters: a materialized ``sexual_traits`` record supplies
    # ``climax_today`` and the lifetime counters (``current`` wins over
    # ``base``); an unmaterialized state reads every counter as zero. A
    # present-but-malformed counter value fails closed, matching the
    # intimate reader's discipline.
    traits = _read_attribute(
        entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    counter_values: dict[str, int] = {}
    if isinstance(traits, Mapping):
        for field in ("climax_today", *_LIFETIME_COUNTER_KEYS):
            entry = traits.get(field)
            if entry is None:
                continue
            if not isinstance(entry, Mapping):
                raise StatusQueryError(f"sexual counter {field!r} is malformed")
            value = entry.get("current", entry.get("base"))
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise StatusQueryError(f"sexual counter {field!r} is malformed")
            counter_values[field] = value

    unlocked = sorted(unlocked_act_keys_for(base_keys, counter_values))
    seen: set[str] = set()
    active: list[str] = []
    passive: list[str] = []
    for key in (*base_keys, *unlocked):
        if not isinstance(key, str) or not key or key in seen:
            continue
        skill = SKILL_REGISTRY.get(key)
        if skill is None and key not in stored_keys and key not in INNATE_SKILL_KEYS:
            continue
        seen.add(key)
        if skill is not None:
            (active if skill.kind is SkillKind.ACTIVE else passive).append(key)
        elif key in raw_active_keys:
            active.append(key)
        else:
            passive.append(key)
    return tuple(active), tuple(passive)


def _is_list_like(value: Any) -> bool:
    """Whether ``value`` behaves like a bounded sequence of elements.

    Evennia deserializes stored lists as ``_SaverList`` (a
    ``MutableSequence``, not a ``list`` subclass), so the check must accept any
    non-string sequence.
    """
    from collections.abc import Sequence

    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def group_skill_keys(keys: Sequence[str]) -> tuple[CharacterCategoryGroupView, ...]:
    """Group plain skill keys into the character panel's category structure.

    Category order follows ``SkillCategory``'s declaration order; sub-group
    order within ``elemental_magic`` follows ``ELEMENT_REGISTRY``'s declaration
    order and ``sexual_act`` follows first-seen ``group`` order among the given
    keys. Every other category emits exactly one ``group=None`` sub-group, and
    each row's ``label`` is the registry label. Categories and sub-groups with
    zero matching keys are omitted. Keys absent from ``SKILL_REGISTRY`` land in
    one synthetic ``unknown`` category appended after every real category, with
    each row's ``label`` equal to its own key — never raising, mirroring the
    presenter's existing unknown-key degradation.
    """
    buckets: dict[str, dict[str | None, list[SkillDef]]] = {}
    unregistered: list[str] = []
    for key in keys:
        skill = SKILL_REGISTRY.get(key)
        if skill is None:
            unregistered.append(key)
            continue
        buckets.setdefault(skill.category.value, {}).setdefault(skill.group, []).append(skill)

    views: list[CharacterCategoryGroupView] = []
    for category in SkillCategory:
        category_buckets = buckets.get(category.value)
        if not category_buckets:
            continue
        if category is SkillCategory.ELEMENTAL_MAGIC:
            ordered_groups = [group for group in ELEMENT_REGISTRY if group in category_buckets]
        elif category is SkillCategory.SEXUAL_ACT:
            ordered_groups = list(category_buckets)
        else:
            ordered_groups = [None]
        views.append(
            CharacterCategoryGroupView(
                category=category.value,
                label=_CATEGORY_LABELS[category],
                groups=tuple(
                    CharacterSkillGroupView(
                        group=group_key,
                        label=_group_label(category, group_key),
                        skills=tuple(
                            CharacterSkillRow(key=skill.key, label=skill.label)
                            for skill in category_buckets[group_key]
                        ),
                    )
                    for group_key in ordered_groups
                ),
            )
        )
    if unregistered:
        views.append(
            CharacterCategoryGroupView(
                category=_UNKNOWN_CATEGORY,
                label=_UNKNOWN_CATEGORY_LABEL,
                groups=(
                    CharacterSkillGroupView(
                        group=None,
                        label=None,
                        skills=tuple(
                            CharacterSkillRow(key=key, label=key) for key in unregistered
                        ),
                    ),
                ),
            )
        )
    return tuple(views)


def _group_label(category: SkillCategory, group: str | None) -> str | None:
    """Return the display label for one sub-group key, if any."""
    if group is None:
        return None
    if category is SkillCategory.ELEMENTAL_MAGIC:
        element = ELEMENT_REGISTRY.get(group)
        if element is not None:
            return element.display_name_zh
    return group


def _read_equipment(entity: Any) -> tuple[CharacterEquipmentView, ...]:
    raw = entity.db.equipment
    if not isinstance(raw, Mapping):
        return ()
    rows: list[CharacterEquipmentView] = []
    for slot in _EQUIPMENT_SLOTS:
        value = raw.get(slot)
        if isinstance(value, str) and value:
            rows.append(CharacterEquipmentView(slot, value))
    accessories = raw.get("accessories")
    if _is_list_like(accessories):
        for value in accessories:
            if isinstance(value, str) and value:
                rows.append(CharacterEquipmentView("accessory", value))
    return tuple(rows)


def _read_disguise(entity: Any) -> tuple[bool, tuple[tuple[str, int], ...]]:
    raw = _read_attribute(entity, "disguised_stats", default=None)
    if raw is None:
        return False, ()
    if not isinstance(raw, Mapping):
        raise StatusQueryError("disguised_stats is malformed")
    displayed: list[tuple[str, int]] = []
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            raise StatusQueryError("disguised_stats key is malformed")
        if isinstance(value, bool) or not isinstance(value, int):
            raise StatusQueryError(f"disguised_stats {key!r} is not an integer")
        displayed.append((key, value))
    displayed.sort(key=lambda entry: entry[0])
    return True, tuple(displayed)


def _read_wallet(entity: Any) -> int:
    raw = entity.db.wallet
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise StatusQueryError("wallet is malformed")
    return raw


def build_character_read_model(entity: Any) -> CharacterReadModel:
    """Build the frozen character read model or raise :class:`StatusQueryError`.

    Reads the same canonical trait dict the status model reads, so the expanded
    character surface and the compact status surface agree on every shared
    value. Equipment, disguise, guild, wallet, and the intimate view are read
    strictly and fail closed when malformed; no handler is materialized and
    nothing is written.
    """
    traits_data = _read_attribute(
        entity, "traits", default=None, category="traits"
    )
    if not isinstance(traits_data, Mapping):
        raise StatusQueryError("trait storage is unavailable")
    traits_data = dict(traits_data)

    traits: list[CharacterTraitView] = []
    for key in _GAUGE_KEYS:
        gauge = _require_gauge(traits_data, key)
        traits.append(CharacterTraitView(key, gauge.current, gauge.maximum))
    for key in _STATIC_KEYS + _COUNTER_KEYS:
        traits.append(CharacterTraitView(key, _require_static_trait(traits_data, key), None))

    disguise_active, disguise_displayed = _read_disguise(entity)
    # The intimate view is read before the skill path so a corrupted (partial)
    # materialized record fails the completeness check before anything else in
    # the model build can observe or repair it.
    intimate = _read_intimate(entity)
    active_keys, passive_keys = _split_active_passive_keys(entity)
    return CharacterReadModel(
        traits=tuple(traits),
        active_keys=active_keys,
        passive_keys=passive_keys,
        equipment=_read_equipment(entity),
        disguise_active=disguise_active,
        disguise_displayed=disguise_displayed,
        guild_rank=getattr(entity, "guild_rank", None),
        guild_merit=_read_guild_merit(traits_data),
        wallet=_read_wallet(entity),
        intimate=intimate,
    )
