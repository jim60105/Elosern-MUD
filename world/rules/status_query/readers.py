"""Strict no-create attribute readers shared by every status read-model builder.

Each helper interprets persisted storage in memory and fails closed with
:class:`StatusQueryError`; none ever constructs ``entity.traits``,
``entity.buffs``, or ``entity.sexual``, and none writes to storage.
"""

from collections.abc import Mapping
from typing import Any

from world.rules.titles import MAX_FULL_TITLE_CODE_POINTS, compose_full_title
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.skills.handler import INNATE_SKILL_KEYS, INNATE_SKILL_ORDER
from world.skills.registry import SKILL_REGISTRY, SkillKind
from world.skills.sexual_acts import unlocked_act_keys_for

from .models import (
    _BUFF_CACHE_KEY,
    _EQUIPMENT_SLOTS,
    _SEXUAL_TRAITS_CATEGORY,
    _SEXUAL_TRAITS_KEY,
    CharacterEquipmentView,
    GaugeValue,
    StatusQueryError,
)


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
