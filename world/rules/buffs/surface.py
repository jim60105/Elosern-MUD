"""The apply/read/remove/cleanse surface.

Extracted from :mod:`world.rules.buffs` as the surface layer of the package:
the single public grant entry point, the read-only active-buff accessors, the
selector-driven removal vocabulary, the marker/growth-rate helpers, and the
``cleanse:status`` effect handler.
"""

from typing import Any
from math import isfinite

from .buff_class import RulebookBuff
from .definitions import (
    BUFF_DEFINITIONS,
    BLOCKING_BUFF_KEYS,
    _REMOVE_SELECTORS,
    _parse_percent_value,
    get_recovery_policy,
)
from .rates import _active_buff_instances


def apply_buff(
    entity, definition_key: str, *, instance_key: str | None = None, **data
) -> None:
    from world.rules.equipment_effects import equipment_immune_buff_keys

    definition = BUFF_DEFINITIONS[definition_key]
    if (
        definition.polarity == "debuff"
        and definition_key in equipment_immune_buff_keys(entity)
    ):
        # Defense-in-depth no-write backstop (P3 D1): the action workflow
        # already stages a visible neutralization event before this point;
        # this gate refuses the write for any direct caller so an immune
        # debuff can never silently half-apply. Grant-time-only semantics:
        # already-applied debuffs are untouched. The import is function-local
        # because ``equipment_effects`` imports this module at module level.
        return
    if definition.stacking == "unique_per_source" and "source_key" not in data:
        raise ValueError(f"buff {definition_key!r} requires source_key")
    if definition.marker == "positional":
        battlefield = data.pop("battlefield", None)
        event_context = data.pop("event_context", None)
        # Design D3: refuse mounting on an impossible recipient, zero writes.
        traits = getattr(entity, "traits", None)
        if traits is not None and hasattr(traits, "hp"):
            from world.rules.action import _stored_trait_value

            try:
                if _stored_trait_value(traits.hp) <= 0:
                    return
            except Exception:  # observability: ignore R2: fail-closed default on unreadable hp
                pass
        if battlefield is None and getattr(entity, "pk", None) is not None:
            if isinstance(event_context, dict):
                battlefield = event_context.get("battlefield")
            from world.rules.skip_safety import _active_battlefield_for

            battlefield = _active_battlefield_for(entity)
        if battlefield is not None:
            roster_key = str(getattr(entity, "key", ""))
            if roster_key in getattr(battlefield, "fled", ()):
                return
            is_ko = getattr(battlefield, "is_knocked_out", None)
            if callable(is_ko) and is_ko(roster_key):
                return
            if roster_key in getattr(battlefield, "knocked_out", ()):
                return
            from world.rules.combat_session import CombatSessionError, read_session

            try:
                record = read_session(entity) if hasattr(getattr(entity, "db", None), "active_combat") else None
            except (CombatSessionError, AttributeError):  # observability: ignore R2: non-player or unparseable session falls back to unrecorded
                record = None
            if record is not None:
                pk = getattr(entity, "pk", None)
                if pk in record.fled_ids or pk in record.knocked_out_ids:
                    return
        # Design D5: mounting a positional row first sweeps the recipient's
        # ground markers (blown off the hazard), logged on commit.
        swept = remove_ground_markers(entity)
        if swept:
            from django.db import transaction

            from world.observability import log_info

            boundary: dict[str, Any] = {
                "char": str(getattr(entity, "pk", "")),
                "count": swept,
                "reason": "displaced_mount",
            }
            transaction.on_commit(lambda b=boundary: log_info("combat_marker_swept", context=b))
    # These mount-path consult inputs must never persist into any buff's cache.
    data.pop("battlefield", None)
    data.pop("event_context", None)
    target_key = instance_key or definition_key
    existing = (
        entity.buffs.all.get(target_key)
        if hasattr(getattr(entity, "buffs", None), "all")
        else None
    )
    is_refresh = (
        existing is not None
        and not getattr(existing, "paused", False)
        and getattr(existing, "stacks", 1) > 0
        and (
            getattr(existing, "remaining_seconds", None) is None
            or existing.remaining_seconds > 0
        )
    )
    source_tier = data.get("source_tier")
    if source_tier is None:
        source_tier = "學徒"
    data["source_tier"] = source_tier
    recovery_policy = get_recovery_policy(definition)
    if recovery_policy is not None:
        # Normalize snapshot data with neutral defaults
        raw_heal_gain = data.get("snapshot_heal_gain", 0.0)
        raw_grace = data.get("snapshot_grace_multiplier", 1.0)
        data["snapshot_heal_gain"] = _parse_percent_value(raw_heal_gain)
        if isinstance(raw_grace, bool) or not isinstance(raw_grace, (int, float)) or not isfinite(raw_grace) or raw_grace < 0:
            raise ValueError(f"invalid snapshot_grace_multiplier: {raw_grace!r}")
        data["snapshot_grace_multiplier"] = float(raw_grace)
    cache = {
        "definition_key": definition_key,
        "tick_interval": definition.tick_interval,
        "remaining_seconds": definition.duration,
        "tick_elapsed_seconds": 0,
        **data,
    }
    if "divert" in definition.modifiers and not is_refresh and "divert_consumed" not in data:
        cache["divert_consumed"] = 0
    entity.buffs.add(
        RulebookBuff,
        key=instance_key or definition_key,
        duration=-1,
        to_cache=cache,
    )
    if definition.polarity == "debuff" and not is_refresh:
        from world.rules.state_reactions import dispatch_outcome_reaction

        dispatch_outcome_reaction(
            entity, "negative_buff_added", source_tier=source_tier
        )


def entity_active_buffs(entity) -> set[str]:
    """Return logical definition keys for every active buff instance."""
    return {buff.definition_key for buff in _active_buff_instances(entity)}


def active_buff_keys_from_storage(entity) -> set[str]:
    """Return active definition keys from stored buff cache without a handler.

    Presentation and preview paths must never materialize ``entity.buffs``.
    This read-only accessor mirrors :func:`entity_active_buffs` against the
    persisted buff attribute, skipping paused, zero-stack, and expired entries.
    """
    from collections.abc import Mapping

    cache = entity.attributes.get("buffs", default={})
    if cache is None:
        return set()
    if not isinstance(cache, Mapping):
        raise TypeError("buff cache storage is malformed")
    active: set[str] = set()
    for buff_cache in cache.values():
        if not isinstance(buff_cache, Mapping):
            raise TypeError("buff cache entry is malformed")
        if buff_cache.get("paused"):
            continue
        stacks = buff_cache.get("stacks")
        if not isinstance(stacks, int) or stacks <= 0:
            continue
        remaining = buff_cache.get("remaining_seconds")
        if isinstance(remaining, int) and remaining <= 0:
            continue
        definition_key = buff_cache.get("definition_key")
        if isinstance(definition_key, str):
            active.add(definition_key)
    return active


def has_positional_marker(entity: Any) -> bool:
    """Return the canonical out-of-position fact (design D1/D2).

    True iff the entity carries a live (unpaused, unexpired) instance of a
    definition declaring ``marker: positional`` — the fact consults only the
    clause, never element/skill/definition-key identity.
    """
    if hasattr(entity, "attributes") and entity.attributes.has("buffs"):
        active_keys = active_buff_keys_from_storage(entity)
    elif hasattr(entity, "buffs"):
        active_keys = entity_active_buffs(entity)
    else:
        return False
    return any(
        (defn := BUFF_DEFINITIONS.get(key)) is not None and defn.marker == "positional"
        for key in active_keys
    )


def active_stack_count(arg1: Any, arg2: Any) -> int:
    """Return the total active stacks for a buff definition key on an entity.

    Accepts either (entity, definition_key) or (definition_key, entity) for
    ergonomics. Reads stored state without materializing entity.buffs if possible,
    so preview paths remain side-effect-free.
    """
    if isinstance(arg1, str) and not isinstance(arg2, str):
        definition_key, entity = arg1, arg2
    else:
        entity, definition_key = arg1, str(arg2)

    from collections.abc import Mapping

    if hasattr(entity, "attributes") and entity.attributes.has("buffs"):
        cache = entity.attributes.get("buffs", default={})
        if isinstance(cache, Mapping):
            total = 0
            for buff_cache in cache.values():
                if not isinstance(buff_cache, Mapping):
                    continue
                if buff_cache.get("paused"):
                    continue
                if buff_cache.get("definition_key") != definition_key:
                    continue
                stacks = buff_cache.get("stacks")
                if not isinstance(stacks, int) or stacks <= 0:
                    continue
                remaining = buff_cache.get("remaining_seconds")
                if isinstance(remaining, int) and remaining <= 0:
                    continue
                total += stacks
            return total

    if hasattr(entity, "buffs") and hasattr(entity.buffs, "all"):
        total = 0
        for buff in entity.buffs.all.values():
            if getattr(buff, "paused", False):
                continue
            if getattr(buff, "definition_key", None) != definition_key:
                continue
            if getattr(buff, "remaining_seconds", None) is not None and buff.remaining_seconds <= 0:
                continue
            stacks = getattr(buff, "stacks", 0)
            if isinstance(stacks, int) and stacks > 0:
                total += stacks
        return total

    return 0


def blocks_action(entity) -> bool:
    """Report whether a marker buff forbids action, without resolving one."""
    return bool(entity_active_buffs(entity) & BLOCKING_BUFF_KEYS)


def grant_conferred_growth_rate(entity, source_key: str, scale: float) -> None:
    """Persist an unconditional source-qualified growth-rate conferral."""
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        raise ValueError("growth-rate scale must be a finite non-negative number")
    if not isfinite(scale) or scale < 0:
        raise ValueError("growth-rate scale must be a finite non-negative number")
    apply_buff(
        entity,
        "conferred_growth_rate",
        instance_key=f"conferred_growth_rate:{source_key}",
        source_key=source_key,
        scale=float(scale),
    )


def growth_rate_multiplier(entity) -> float:
    """Return the product of all active conferred growth-rate scales."""
    multiplier = 1.0
    for buff in _active_buff_instances(entity):
        if buff.definition_key == "conferred_growth_rate":
            multiplier *= buff.scale
    return multiplier


def clear_conferred_growth_rates(entity) -> int:
    """Remove every live conferred growth-rate buff instance; return the count.

    Selection resolves against live buff **instances**, so distinct instance
    keys (one per conferring source) all lose their instances — revocation is
    total, never per-source. Every removal routes through the same
    ``dispel=True`` external-removal path the cleanse handler and the
    ``remove_by_selector`` vocabulary use; nothing is written when no
    conferred instance is live (``0`` is a legitimate outcome, not an error).
    """
    keys = tuple(
        buff.buffkey
        for buff in _active_buff_instances(entity)
        if buff.definition_key == "conferred_growth_rate"
    )
    if not keys:
        return 0
    _remove_buff_keys(entity, keys)
    return len(keys)


def _remove_buff_keys(entity, keys: tuple[str, ...]) -> None:
    """Dispel one active buff instance per key; missing keys are no-ops.

    ``dispel=True`` routes the removal through Evennia's external-removal
    hooks (``at_dispel`` then ``at_remove``) rather than the bare remove path:
    a cleanse is a forced external removal, not a natural expiry. ``RulebookBuff``
    defines neither hook today, so this is a recorded semantic contract for
    future buffs that need "cleansed" cleanup.
    """
    for key in keys:
        entity.buffs.remove(key, dispel=True)


def remove_by_selector(entity, selector: str) -> int:
    """Remove every live buff instance one selector names; return the count.

    The selector vocabulary is exactly a concrete ``buffs.yaml`` definition
    key or one of the polarity-wide words ``all`` / ``positive`` /
    ``negative`` (``_REMOVE_SELECTORS``); an unrecognized selector fails
    closed rather than silently removing nothing. Selection resolves against
    live buff **instances**, so a definition with several live instances
    (distinct instance keys) loses all of them, and every removal routes
    through the same ``dispel=True`` external-removal path the cleanse
    handler already uses. A selector matching nothing writes nothing and
    returns ``0``. An empty result is a legitimate outcome, not an error.
    """
    if selector not in _REMOVE_SELECTORS and selector not in BUFF_DEFINITIONS:
        raise ValueError(f"unknown buff removal selector {selector!r}")

    def _matches(definition_key: str) -> bool:
        if selector == "all":
            return True
        if selector == "negative":
            return BUFF_DEFINITIONS[definition_key].polarity == "debuff"
        if selector == "positive":
            return BUFF_DEFINITIONS[definition_key].polarity == "buff"
        return definition_key == selector

    keys = tuple(
        buff.buffkey
        for buff in _active_buff_instances(entity)
        if _matches(buff.definition_key)
    )
    if not keys:
        return 0
    _remove_buff_keys(entity, keys)
    return len(keys)


def cleanse_debuffs(entity) -> int:
    """Remove every active debuff-polarity buff and return the count removed.

    The shipped ``negative`` alias of :func:`remove_by_selector`, so
    holy-water settlement and the cleanse effect handler share one
    semantics. Returns 0 when nothing is active (and writes nothing).
    """
    return remove_by_selector(entity, "negative")


def remove_ground_markers(entity) -> int:
    """Remove every live ground-marker buff on an entity; return the count removed.

    Consults only definitions declaring marker: ground.
    Never touches non-marker buff instances. Zero damage or revive side effects.
    """
    keys = tuple(
        buff.buffkey
        for buff in _active_buff_instances(entity)
        if (defn := BUFF_DEFINITIONS.get(buff.definition_key)) is not None
        and defn.marker == "ground"
    )
    if not keys:
        return 0
    _remove_buff_keys(entity, keys)
    return len(keys)


def remove_positional_markers(entity) -> int:
    """Remove every live positional-marker buff on an entity; return the count removed.

    Consults only definitions declaring marker: positional.
    Never touches non-marker buff instances. Zero damage or revive side effects.
    """
    keys = tuple(
        buff.buffkey
        for buff in _active_buff_instances(entity)
        if (defn := BUFF_DEFINITIONS.get(buff.definition_key)) is not None
        and defn.marker == "positional"
    )
    if not keys:
        return 0
    _remove_buff_keys(entity, keys)
    return len(keys)


def _handle_cleanse(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[Any]:
    """Stage removal of every active debuff-polarity buff on each target.

    ``PendingEffect`` is imported lazily to keep ``world.rules.action``'s
    top-level import of this module from forming an import cycle.
    """
    del actor, context, scale
    scope = effect_id.partition(":")[2]
    if scope != "status":
        raise ValueError(f"cleanse effect must be cleanse:status, got {effect_id!r}")
    from world.rules.action import PendingEffect

    pending: list[Any] = []
    for target in targets:
        debuffs = tuple(
            buff
            for buff in _active_buff_instances(target)
            if BUFF_DEFINITIONS[buff.definition_key].polarity == "debuff"
        )
        if not debuffs:
            continue
        keys = tuple(buff.buffkey for buff in debuffs)
        pending.append(
            PendingEffect(
                entity=target,
                description=f"buffs_cleansed|{target.key}|{len(keys)}",
                surfaces=frozenset(),
                # The stage-time selection above exists only for the effect
                # description and the skip-when-empty check; applying through
                # the shared selector keeps the cleanse effect and every
                # other debuff-clearing caller on one removal (delta trace
                # scenario) instead of replaying a snapshot key tuple.
                apply=lambda target=target: remove_by_selector(target, "negative"),
            )
        )
    return pending
