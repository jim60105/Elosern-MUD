"""Frozen no-create status read model for the WebClient status presenter.

Presentation must never materialize lazy handlers or default state. This module
reads only the persistent trait attribute, optional buff cache, sexual baseline
or materialized traits, creation flag, disguise record, and combat-session
record, and interprets them in memory. It never constructs ``entity.traits``,
``entity.buffs``, or ``entity.sexual`` and never writes to storage.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat_modifiers import (
    _merge_adjustments,
    _PERCENT_RE,
    matched_combat_modifiers,
)
from world.rules.equipment_effects import (
    effective_exposure,
    equipment_adjustments,
    equipment_modifier_layers,
    worn_item_keys,
)
from world.skills.effects import StatMultiplyEffect
from world.rules.sexual_state import PLEASURE_CONFIG, _LIFETIME_COUNTER_KEYS
from world.rules.status_display import display_for
from world.rules.stored_sexual_reads import StoredLevel
from world.rules.titles import MAX_FULL_TITLE_CODE_POINTS, compose_full_title
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
    "magic_power": "魔力",
    "guild_merit": "功績",
}

_GAUGE_KEYS = ("hp", "mp", "sp")
_STATIC_KEYS = ("atk_phys", "agility", "defense", "magic_power")
_COUNTER_KEYS = ("guild_merit",)
_EQUIPMENT_SLOTS = ("weapon_main", "weapon_off", "armor")
_BUFF_CACHE_KEY = "buffs"
_SEXUAL_TRAITS_KEY = "sexual_traits"
_SEXUAL_TRAITS_CATEGORY = "traits"

# Breakdown vocabulary (expose-stat-breakdown-read-model D1): the eight panel
# rows in display order and the closed layer alphabets/bounds mirrored by the
# wire validators.
_BREAKDOWN_ROW_ORDER = (
    "hp",
    "mp",
    "sp",
    "atk_phys",
    "agility",
    "defense",
    "magic_power",
    "guild_merit",
)
_LAYER_SOURCES = ("skill", "condition", "equipment")
_LAYER_KINDS = ("mult", "flat", "pct")
MAX_BREAKDOWN_ROWS = 32
MAX_LAYERS_PER_STAT = 16


@dataclass(frozen=True)
class StatLayer:
    """One named contribution to a stat, from a closed source/kind alphabet.

    ``amount`` is signed and non-zero: ``mult`` carries the multiplier factor
    itself (e.g. ``1.1``), ``flat`` the additive amount (int, or the exact
    fractional float a scaled rule-table grant produces), ``pct`` the signed
    percentage number (e.g. ``-10`` for ``-10%``).
    """

    source: str
    name: str
    kind: str
    amount: int | float


@dataclass(frozen=True)
class StatBreakdownRow:
    """One breakdown row: literal base, accounting-complete layers, effective.

    ``effective`` is composed FROM the layers' sources replaying the shipped
    authoritative operations bit-for-bit (see the breakdown section at the end
    of this module). For gauges the layers decompose the ``maximum`` and
    ``effective`` equals that maximum; gauge ``current`` is persisted resource
    state and carries no layers. On every row ``current`` mirrors the
    displayed total.
    """

    key: str
    base: int
    current: int | float
    effective: int | float
    layers: tuple[StatLayer, ...]


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
    full_title: str
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
    """The complete read-only inputs of the version-5 ``character`` panel.

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
    full_title: str
    intimate: IntimateView | None
    breakdown: tuple[StatBreakdownRow, ...]


def _read_attribute(entity: Any, key: str, default=None, category: str | None = None) -> Any:
    return entity.attributes.get(key, default=default, category=category)


def _read_full_title(entity: Any) -> str:
    """Compose the live full title, fail-closed on malformed title state.

    The empty string means no title (consumers fall back to the character's
    own name); malformed persisted title state degrades the whole panel to
    ``presentation_unavailable`` rather than fabricating a title.
    """
    try:
        composed = compose_full_title(entity)
    except Exception as error:
        raise StatusQueryError(f"title state is malformed: {error}") from error
    # The wire validator bounds this field; an over-long composed title is
    # corrupt state and degrades the panel exactly like a malformed record
    # instead of being serialized into a panel the client would reject whole.
    if len(composed) > MAX_FULL_TITLE_CODE_POINTS:
        raise StatusQueryError("composed full title exceeds the wire bound")
    return composed


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


def _require_gauge_record(
    data: dict[str, Any], key: str
) -> tuple[GaugeValue, Any, Any]:
    """Return ``_require_gauge``'s value plus the raw ``mod``/``mult`` fields.

    The breakdown section needs the stored modifiers to prove the layer
    decomposition accounts for them exactly; validation is shared with the
    shipped reader so the two can never drift.
    """
    raw = data.get(key)
    if not isinstance(raw, Mapping):
        raise StatusQueryError(f"missing gauge trait {key!r}")
    return _require_gauge(data, key), raw.get("mod", 0), raw.get("mult", 1)


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


_BUFF_RULE_CLASSIFICATION: tuple[Any, frozenset[str]] | None = None


def _buff_active_rule_ids() -> frozenset[str]:
    """Return the rule ids whose ``when`` is a bare ``buff_active`` check.

    Pure rule-table data, classified once per load (the module-level ``_RULES``
    tuple is replaced wholesale on reload, so object identity is the cache
    key). The classification only orders condition layers deterministically
    (``buff`` before ``rule``); buff cache entries themselves never feed stat
    layers directly — a buff reaches a stat row exclusively through such a
    rule-table row.
    """
    global _BUFF_RULE_CLASSIFICATION
    from world.rules.combat_modifiers import _RULES

    cached = _BUFF_RULE_CLASSIFICATION
    if cached is not None and cached[0] is _RULES:
        return cached[1]
    ids = frozenset(
        rule.id
        for rule in _RULES
        if set(rule.when) == {"buff_active"}
        and isinstance(rule.when.get("buff_active"), str)
    )
    _BUFF_RULE_CLASSIFICATION = (_RULES, ids)
    return ids


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
    # Neither read model may materialize ``entity.skills``: every
    # condition-evaluation consumer reads skills through the positional
    # subject or ``context["entity"]``, and both are always the pure
    # stored-snapshot facade (expose-stat-breakdown-read-model D4). The two
    # pre-set equipment facts keep ``matched_combat_modifiers``' setdefaults
    # away from the real entity as well.
    facade = _StoredSkillsFacade(entity)
    context["entity"] = facade
    context["dual_wielding"] = dual_wielding_from_storage(facade)
    context["worn_item_keys"] = worn_item_keys(facade)
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
    assembly = _assemble(entity)
    conditions: list[ConditionValue] = []
    for buff_key, cache in assembly.buff_entries:
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

    # Deterministic combat-modifier matches — the SAME matches the breakdown
    # composes from (D3: one assembly per read, no second evaluation path).
    for rule_id, adjustments in assembly.matches:
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

    combat = assembly.combat
    identity = str(entity.pk)
    location = getattr(entity, "location", None)
    return StatusReadModel(
        actor_name=str(getattr(entity, "key", "?")),
        actor_identity=identity,
        full_title=_read_full_title(entity),
        location_label=None if location is None else str(location.key),
        location_identity=None if location is None else str(location.pk),
        resources={key: assembly.gauges[key] for key in _GAUGE_KEYS},
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


# ---------------------------------------------------------------------------
# Stat breakdown (expose-stat-breakdown-read-model)
#
# This section composes each panel stat FROM its named layers while replaying
# the shipped authoritative operations bit-for-bit:
# ``SkillHandler.effective_value`` (stored-list skill fold + single final
# ``round``), ``combat._adjusted_attack``/``_adjusted_defense`` (skill
# effective value + merged rule-table flats), ``combat_modifiers``' agility
# pipeline (percent merge through ``_merge_adjustments``, then percent, then
# flat, floored at 0 — the ``adjusted_agility`` shape), and the gauge-ceiling
# reader ``_require_gauge``. ``_merge_adjustments`` and ``_PERCENT_RE`` are
# imported from their shipped homes as the parity anchors — never a parallel
# reimplementation.
# ---------------------------------------------------------------------------


class _StoredSkillsFacade:
    """Pure ``skills``-view facade over stored snapshots (design D4).

    Exposes exactly the ``owned_keys()``/``conferred_grants()`` surface
    ``matched_combat_modifiers``, ``_conferred_rule_scale`` and
    ``evaluate_condition`` consume, computed from ``entity.db`` and the
    registries with the same no-create discipline as
    ``_split_active_passive_keys``. ``db`` delegates to the real entity so the
    pure storage readers (``dual_wielding_from_storage``, ``worn_item_keys``)
    keep working on the facade. Never mounts ``entity.skills`` (or any other
    handler) and never writes.
    """

    __slots__ = ("entity",)

    def __init__(self, entity: Any):
        self.entity = entity

    @property
    def db(self) -> Any:
        return self.entity.db

    @property
    def skills(self) -> "_StoredSkillsFacade":
        return self

    def _stored_list(self, field: str) -> tuple[str, ...]:
        raw = self.entity.db.skills
        if not isinstance(raw, Mapping):
            return ()
        value = raw.get(field)
        if not _is_list_like(value):
            return ()
        return tuple(key for key in value if isinstance(key, str) and key)

    def base_owned_keys(self) -> list[str]:
        """Stored active+passive keys plus innate grants, in stored order."""
        return [*self._stored_list("active"), *self._stored_list("passive"), *INNATE_SKILL_ORDER]

    def _counter_values(self) -> dict[str, int]:
        """Lifetime counters from storage, or empty when unmaterialized.

        Mirrors ``_split_active_passive_keys`` exactly: a materialized
        ``sexual_traits`` record supplies ``climax_today`` and the lifetime
        counters (``current`` wins over ``base``); a present-but-malformed
        entry fails closed; no record means every counter is zero, which is
        what the shipped handler assumes for an unmaterialized state.
        """
        traits = _read_attribute(
            self.entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
        )
        counters: dict[str, int] = {}
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
                counters[field] = value
        return counters

    def owned_keys(self) -> list[str]:
        """Base keys plus unlocked acts — the materialization-aware handler rule.

        The shipped ``SkillHandler.owned_keys`` derives unlocked acts from a
        zero-counter baseline while ``sexual`` is unmaterialized and from the
        live handler afterwards; the live handler's counters are exactly the
        materialized record, so reading every counter from storage reproduces
        both branches without mounting one.
        """
        base = self.base_owned_keys()
        return [*base, *sorted(unlocked_act_keys_for(base, self._counter_values()))]

    def conferred_grants(self) -> list[Any]:
        """Stored grants verbatim (``list(entity.db.skill_grants or [])``)."""
        return list(self.entity.db.skill_grants or [])


def _stored_skill_fold(entity: Any) -> tuple[str, ...]:
    """Stored ownership keys in the shipped fold order (``effective_value``).

    Deliberately the raw ``db.skills`` lists only — NOT ``owned_keys()`` and
    NOT the innate keys: the shipped skill fold iterates ``dict.fromkeys``
    over the stored active+passive lists alone, so the replay can never drift
    even if an unlocked act or innate key were to carry a stat multiplier.
    """
    raw = entity.db.skills
    if not isinstance(raw, Mapping):
        raw = {}
    active = raw.get("active")
    passive = raw.get("passive")
    if not _is_list_like(active):
        active = ()
    if not _is_list_like(passive):
        passive = ()
    return tuple(dict.fromkeys((*active, *passive)))


def _matching_stat_multiplier(skill: SkillDef, stat_key: str) -> float | None:
    """The skill's single matching stat multiplier, fail-loud on duplicates.

    The ``StatusQueryError`` wrapper over the shipped handler's ``ValueError``
    keeps the duplicate-definition failure on the panel's fail-closed path.
    """
    multipliers = [
        effect.multiplier
        for effect in skill.parsed_effects
        if isinstance(effect, StatMultiplyEffect) and effect.trait == stat_key
    ]
    if not multipliers:
        return None
    if len(multipliers) > 1:
        raise StatusQueryError(
            f"skill {skill.key!r} defines duplicate stat multipliers for trait {stat_key!r}"
        )
    return multipliers[0]


def _grant_fields(grant: Any) -> tuple[str, str, float] | None:
    """Read one grant's ``(source_key, skill_key, scale)`` from dataclass or mapping.

    The shipped writer stores ``ConferredSkillGrant`` dataclasses; mapping
    fixtures ride the same fields. A malformed grant returns ``None`` so the
    fold skips it exactly as the shipped fold skips an unknown skill key.
    """
    source_key = getattr(grant, "source_key", None)
    skill_key = getattr(grant, "skill_key", None)
    scale = getattr(grant, "scale", None)
    if isinstance(grant, Mapping):
        source_key = grant.get("source_key", source_key)
        skill_key = grant.get("skill_key", skill_key)
        scale = grant.get("scale", scale)
    if not isinstance(source_key, str) or not isinstance(skill_key, str):
        return None
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        return None
    return source_key, skill_key, float(scale)


@dataclass(frozen=True)
class _Assembly:
    """One read's shared, fully validated inputs (design D3: assembled once)."""

    entity: Any
    traits_data: dict[str, Any]
    gauges: dict[str, GaugeValue]
    gauge_records: dict[str, tuple[Any, Any]]
    trait_values: dict[str, int]
    buff_entries: tuple[tuple[str, dict[str, Any]], ...]
    matches: tuple[tuple[str, dict[str, Any]], ...]
    equipment: tuple[CharacterEquipmentView, ...]
    combat: tuple[str, int] | None


def _assemble(entity: Any) -> _Assembly:
    """Parse every read-model input once, fail-closed, with no handler mounted."""
    traits_data = _read_attribute(entity, "traits", default=None, category="traits")
    if not isinstance(traits_data, Mapping):
        raise StatusQueryError("trait storage is unavailable")
    traits_data = dict(traits_data)
    gauges: dict[str, GaugeValue] = {}
    gauge_records: dict[str, tuple[Any, Any]] = {}
    for key in _GAUGE_KEYS:
        gauges[key], mod, mult = _require_gauge_record(traits_data, key)
        gauge_records[key] = (mod, mult)
    trait_values = {
        key: _require_static_trait(traits_data, key) for key in _STATIC_KEYS + _COUNTER_KEYS
    }
    buff_entries = tuple(_active_buff_entries(entity))
    # The positional subject must be the facade too: ``matched_combat_modifiers``
    # reads ``entity.skills.owned_keys()`` directly for the ``skill_owned``
    # grant fallback, in addition to ``context["entity"]``.
    context = _sexual_condition_context(entity)
    matches = matched_combat_modifiers(context["entity"], context=context)
    return _Assembly(
        entity=entity,
        traits_data=traits_data,
        gauges=gauges,
        gauge_records=gauge_records,
        trait_values=trait_values,
        buff_entries=buff_entries,
        matches=matches,
        equipment=_read_equipment(entity),
        combat=_read_combat(entity),
    )


def _merged_bundle(assembly: _Assembly) -> dict[str, Any]:
    """Merge matched rule bundles then the equipment bundle, shipped order.

    Byte-identical to ``combat_modifiers.evaluate_combat_modifiers`` for the
    same storage: ``_merge_adjustments`` (the shipped merge) over
    ``assembly.matches`` (the shipped matches) plus
    ``equipment_adjustments`` (the shipped pure gear read).
    """
    merged: dict[str, Any] = {}
    for _, adjustments in assembly.matches:
        merged = _merge_adjustments(merged, dict(adjustments))
    return _merge_adjustments(merged, dict(equipment_adjustments(assembly.entity)))


def _skill_layers(entity: Any, stat_key: str) -> tuple[list[StatLayer], float]:
    """Replay the shipped ``effective_value`` fold as named layers.

    Factors multiply into the running product in the shipped fold order; the
    returned DISPLAY list is sorted by ``(skill_key, source_key)`` (design D2)
    after the product is complete, which never moves a factor across the
    single final ``round``. A grant's layer carries ``（scale）`` so two grants
    of one skill stay distinct and non-zero-summing.
    """
    product = 1.0
    keyed: list[tuple[str, str, StatLayer]] = []
    for skill_key in _stored_skill_fold(entity):
        skill = SKILL_REGISTRY.get(skill_key)
        if skill is None:
            continue
        multiplier = _matching_stat_multiplier(skill, stat_key)
        if multiplier is not None:
            product *= multiplier
            keyed.append(
                (skill_key, "", StatLayer("skill", skill.label, "mult", multiplier))
            )
    for grant in entity.db.skill_grants or []:
        fields = _grant_fields(grant)
        if fields is None:
            continue
        source_key, skill_key, scale = fields
        source_skill = SKILL_REGISTRY.get(skill_key)
        if source_skill is None:
            continue
        source_multiplier = _matching_stat_multiplier(source_skill, stat_key)
        if source_multiplier is None:
            continue
        factor = source_multiplier * scale
        product *= factor
        name = f"{source_skill.label}（{scale:g}）"
        keyed.append(
            (skill_key, source_key, StatLayer("skill", name, "mult", factor))
        )
    keyed.sort(key=lambda entry: (entry[0], entry[1]))
    return [layer for _, _, layer in keyed], product


def _condition_layers(
    assembly: _Assembly, stat_key: str
) -> list[StatLayer]:
    """Per-rule named layers for one stat's matched rule-table contributions.

    Buff cache entries never feed stat layers directly (buff modifiers are
    rate/bounds/decay only); a buff reaches a stat row exclusively through a
    ``buff_active`` rule-table row, whose id classifies the layer's source
    kind as ``buff`` (sorted before ``rule``). Amounts ride exactly as the
    bundle holds them — already grant-scaled by ``matched_combat_modifiers``.
    """
    buff_rules = _buff_active_rule_ids()
    if stat_key == "agility":
        fields: tuple[str, ...] = ("agility", "agility_flat")
    elif stat_key in ("atk_phys", "defense", "magic_power"):
        fields = (stat_key,)
    else:
        return []
    entries: list[tuple[str, str, int | float, str]] = []
    for rule_id, adjustments in assembly.matches:
        for field in fields:
            value = adjustments.get(field)
            if value is None:
                continue
            kind = "pct" if isinstance(value, str) else "flat"
            entries.append(
                (
                    "buff" if rule_id in buff_rules else "rule",
                    rule_id,
                    float(value[:-1]) if kind == "pct" else value,
                    kind,
                )
            )
    entries.sort()
    layers: list[StatLayer] = []
    for _source_kind, rule_id, amount, kind in entries:
        try:
            label = display_for(rule_id).label
        except ValueError as error:
            # MissingDisplayMetadataError is a ValueError subclass; an
            # unresolvable label makes the row not accounting-complete.
            raise StatusQueryError(
                f"combat modifier rule {rule_id!r} has no display label"
            ) from error
        layers.append(StatLayer("condition", label, kind, amount))
    return layers


def _worn_gear(assembly: _Assembly) -> list[tuple[int, str, Any, Any]]:
    """Resolved ``(slot-order index, item_key, definition, layers)`` for worn gear.

    Mirrors the shipped fold's source exactly (``_worn_rules``): the pure
    ``normalized_equipment`` read, whose malformed-storage branch reads as
    "nothing worn" — the same zero contribution the combat bundle takes, so
    layers and effective can never disagree. Normalization also guarantees
    registry membership and slot fit; a missing definition or effect rule
    past that guard is an invariant break and fails closed. Per-item effect
    data comes exclusively through the capability's
    ``equipment_modifier_layers`` accessor (single-source guard). Rows sort
    by ``(slot order, item key)`` for display.
    """
    from world.rules.equipment import normalized_equipment

    equipment = normalized_equipment(assembly.entity)
    if equipment is None:
        return []
    worn: list[tuple[str, str]] = [
        (slot, equipment[slot])
        for slot in _EQUIPMENT_SLOTS
        if equipment[slot] is not None
    ]
    worn.extend(("accessory", key) for key in equipment["accessories"])
    resolved: list[tuple[int, str, Any, Mapping[str, tuple[str, int]]]] = []
    slot_index = {slot: index for index, slot in enumerate((*_EQUIPMENT_SLOTS, "accessory"))}
    for slot, item_key in worn:
        definition = ITEM_REGISTRY.get(item_key)
        if definition is None:
            raise StatusQueryError(f"worn equipment {item_key!r} is not registry-declared")
        if not definition.display_name_zh:
            raise StatusQueryError(f"equipment {item_key!r} has no display name")
        modifier_key = definition.modifier_key
        if modifier_key is None:
            continue
        layers = equipment_modifier_layers(modifier_key)
        if layers is None:  # pragma: no cover - loader/registry cross invariant
            raise StatusQueryError(
                f"equipment {item_key!r} effect rule {modifier_key!r} is missing"
            )
        resolved.append((slot_index[slot], item_key, definition, layers))
    resolved.sort(key=lambda entry: (entry[0], entry[1]))
    return resolved


def _equipment_layers(assembly: _Assembly, stat_key: str) -> list[StatLayer]:
    """Named layers for one stat's worn-equipment contributions (slot order)."""
    layers: list[StatLayer] = []
    for _index, _item_key, definition, item_layers in _worn_gear(assembly):
        contribution = item_layers.get(stat_key)
        if contribution is not None:
            kind, amount = contribution
            layers.append(StatLayer("equipment", definition.display_name_zh, kind, amount))
    return layers


def _require_number(value: Any, label: str) -> None:
    """Fail closed on a non-finite or zero numeric layer amount."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StatusQueryError(f"{label} amount is not numeric")
    if isinstance(value, float) and not math.isfinite(value):
        raise StatusQueryError(f"{label} amount is not finite")
    if value == 0:
        raise StatusQueryError(f"{label} amount must be non-zero")


def _validated_row(row: StatBreakdownRow) -> StatBreakdownRow:
    """Enforce the closed alphabets and per-stat bound, fail-closed."""
    for layer in row.layers:
        if layer.source not in _LAYER_SOURCES:  # pragma: no cover - builder invariant
            raise StatusQueryError(f"breakdown layer source {layer.source!r} is invalid")
        if layer.kind not in _LAYER_KINDS:  # pragma: no cover - builder invariant
            raise StatusQueryError(f"breakdown layer kind {layer.kind!r} is invalid")
        if not isinstance(layer.name, str) or not layer.name:
            raise StatusQueryError("breakdown layer name is missing")
        _require_number(layer.amount, f"breakdown layer {layer.name!r}")
    if len(row.layers) > MAX_LAYERS_PER_STAT:
        raise StatusQueryError(
            f"stat {row.key!r} exceeds the {MAX_LAYERS_PER_STAT}-layer bound"
        )
    return row


def _stored_literal(traits_data: dict[str, Any], key: str, fallback: int) -> int:
    """The literal stored ``base`` when valid, else the reader's value.

    The breakdown ``base`` is the never-skill-baked import value; every
    shipped writer leaves the static/counter ``base`` key intact, so the
    fallback only matters for hand-forced fixtures.
    """
    raw = traits_data.get(key)
    if isinstance(raw, Mapping):
        base = raw.get("base")
        if not isinstance(base, bool) and isinstance(base, int):
            return base
    return fallback


def _require_untouched_modifiers(traits_data: dict[str, Any], key: str) -> None:
    """Fail closed when a static/counter carries unattributable modifiers.

    No shipped writer sets ``mod``/``mult`` on a static or counter trait
    (the gauge sync owns gauge ``mod`` alone), and no consumer of these two
    read models folds them in — so a nonzero value is storage drift the panel
    must not silently display as if it were the effective value.
    """
    raw = traits_data[key]
    if raw.get("mod", 0) != 0 or raw.get("mult", 1) != 1:
        raise StatusQueryError(f"trait {key!r} carries unattributable storage modifiers")


def _gauge_breakdown(assembly: _Assembly, key: str) -> StatBreakdownRow:
    """Decompose one gauge maximum; the ceiling reader stays authoritative.

    Skill layers are structurally impossible for gauges (stat multipliers
    exist only on body traits — ``world/skills/registry._BODY_TRAITS``), and
    ``sync_equipment_gauge_limits`` is the sole writer of gauge ``mod``, so
    the equipment flats must explain it exactly. Anything else is unexplained
    storage and fails closed, keeping the panel maximum identical to the
    heal-clamp ceiling the shipped reader computes.
    """
    gauge = assembly.gauges[key]
    mod, mult = assembly.gauge_records[key]
    base = _stored_literal(assembly.traits_data, key, gauge.maximum)
    if mult != 1:
        raise StatusQueryError(
            f"gauge {key!r} multiplier is not attributable to any named layer"
        )
    layers = _equipment_layers(assembly, key)
    equipment_total = sum(layer.amount for layer in layers)
    if equipment_total != mod:
        raise StatusQueryError(
            f"gauge {key!r} stored modifier is not explained by worn equipment caps"
        )
    if round(base + equipment_total) != gauge.maximum:
        raise StatusQueryError(
            f"gauge {key!r} maximum decomposition disagrees with the ceiling reader"
        )
    return StatBreakdownRow(
        key=key,
        base=base,
        current=gauge.current,
        effective=gauge.maximum,
        layers=tuple(layers),
    )


def _flat_stat_breakdown(assembly: _Assembly, stat_key: str) -> StatBreakdownRow:
    """attack/defense/magic_power: shipped skill fold, then merged flats.

    Parity anchor ``combat._adjusted_attack``/``_adjusted_defense``:
    ``float(effective_value(key)) + merged flat``, where the merged flat is
    the shipped merge of matched rule-table amounts and the equipment bucket
    — the exact merged-bundle read, so associativity cannot drift either. A
    percentage-shaped bundle for these stats has no shipped consumer and
    fails closed.
    """
    base = assembly.trait_values[stat_key]
    _require_untouched_modifiers(assembly.traits_data, stat_key)
    base_literal = _stored_literal(assembly.traits_data, stat_key, base)
    skill_layers, product = _skill_layers(assembly.entity, stat_key)
    after_skill = round(base * product)
    condition_layers = _condition_layers(assembly, stat_key)
    equipment_layers = _equipment_layers(assembly, stat_key)
    merged_flat = _merged_bundle(assembly).get(stat_key, 0)
    if isinstance(merged_flat, str):
        raise StatusQueryError(
            f"bundle percentage for {stat_key!r} has no shipped consumer"
        )
    if merged_flat != sum(layer.amount for layer in condition_layers) + sum(
        layer.amount for layer in equipment_layers
    ):  # pragma: no cover - per-source layering is exhaustive by construction
        raise StatusQueryError(
            f"stat {stat_key!r} flat amounts are not accounting-complete"
        )
    effective = float(after_skill) + merged_flat
    return StatBreakdownRow(
        key=stat_key,
        base=base_literal,
        current=effective,
        effective=effective,
        layers=(*skill_layers, *condition_layers, *equipment_layers),
    )


def _agility_breakdown(assembly: _Assembly) -> StatBreakdownRow:
    """Agility replays the shipped pipeline exactly, floor at zero included.

    ``combat_modifiers.adjusted_agility`` shape: percent first (the merged
    ``+g`` percent string — rule-table matches merged in ``_RULES`` order,
    then the gear bucket's ``:+d%`` rendering, all through the shipped
    ``_merge_adjustments``), then the flat addend, then ``max(0.0, …)``.

    The static row's total-display ``current`` equals ``effective`` even when
    a percent scale leaves it fractional — the shipped ``adjusted_agility``
    returns a float, and the v5 wire rejects any static row where the two
    diverge.
    """
    base = assembly.trait_values["agility"]
    _require_untouched_modifiers(assembly.traits_data, "agility")
    base_literal = _stored_literal(assembly.traits_data, "agility", base)
    skill_layers, product = _skill_layers(assembly.entity, "agility")
    after_skill = round(base * product)
    bundle = _merged_bundle(assembly)
    agility = float(after_skill)
    percent = bundle.get("agility")
    if percent is not None:
        if not isinstance(percent, str) or _PERCENT_RE.fullmatch(percent) is None:
            raise StatusQueryError(f"invalid agility percentage {percent!r}")
        agility *= 1 + float(percent[:-1]) / 100
    agility += float(bundle.get("agility_flat", 0))
    effective = max(0.0, agility)
    condition_layers = _condition_layers(assembly, "agility")
    equipment_layers = _equipment_layers(assembly, "agility")
    return StatBreakdownRow(
        key="agility",
        base=base_literal,
        current=effective,
        effective=effective,
        layers=(*skill_layers, *condition_layers, *equipment_layers),
    )


def _merit_breakdown(assembly: _Assembly) -> StatBreakdownRow:
    """guild_merit: an integer counter with no shipped modifier source at all."""
    merit = _read_guild_merit(assembly.traits_data)
    _require_untouched_modifiers(assembly.traits_data, "guild_merit")
    return StatBreakdownRow(
        key="guild_merit",
        base=_stored_literal(assembly.traits_data, "guild_merit", merit),
        current=merit,
        effective=merit,
        layers=(),
    )


def build_stat_breakdown(
    entity: Any, assembly: _Assembly | None = None
) -> tuple[StatBreakdownRow, ...]:
    """Return the eight breakdown rows composed from named sources (tasks 1.1–1.4).

    Composition replays the shipped operations exactly (design D1): gauges
    decompose the ceiling reader's ``(base + mod) × mult`` form; skill stats
    fold ``round(base × Π mults)`` in shipped order; attack/defense and
    magic_power add merged rule-table flats after the skill fold; agility
    replays the percent-then-flat pipeline floored at zero. Every accounting
    amount that cannot be attributed to a named, registry-labelled layer
    fails the whole read closed.
    """
    if assembly is None:
        assembly = _assemble(entity)
    rows: list[StatBreakdownRow] = []
    for key in _BREAKDOWN_ROW_ORDER:
        if key in _GAUGE_KEYS:
            rows.append(_gauge_breakdown(assembly, key))
        elif key == "agility":
            rows.append(_agility_breakdown(assembly))
        elif key in ("atk_phys", "defense", "magic_power"):
            rows.append(_flat_stat_breakdown(assembly, key))
        else:
            rows.append(_merit_breakdown(assembly))
    if len(rows) > MAX_BREAKDOWN_ROWS:  # pragma: no cover - closed 8-key vocabulary
        raise StatusQueryError("breakdown exceeds the row bound")
    return tuple(_validated_row(row) for row in rows)


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
    assembly = _assemble(entity)
    traits: list[CharacterTraitView] = []
    for key in _GAUGE_KEYS:
        gauge = assembly.gauges[key]
        traits.append(CharacterTraitView(key, gauge.current, gauge.maximum))
    for key in _STATIC_KEYS + _COUNTER_KEYS:
        traits.append(CharacterTraitView(key, assembly.trait_values[key], None))

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
        equipment=assembly.equipment,
        disguise_active=disguise_active,
        disguise_displayed=disguise_displayed,
        guild_rank=getattr(entity, "guild_rank", None),
        guild_merit=_read_guild_merit(assembly.traits_data),
        wallet=_read_wallet(entity),
        full_title=_read_full_title(entity),
        intimate=intimate,
        breakdown=build_stat_breakdown(entity, assembly),
    )
