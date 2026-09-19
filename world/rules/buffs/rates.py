"""Rate/recovery tick machinery.

Extracted from :mod:`world.rules.buffs` as the rates layer of the package:
applying one rate modifier, the sustained-recovery tick, the damaging-rate
predicates, the caster-share credit path, and the game-time ``tick_buffs``
settlement.
"""

from math import floor
from typing import Any

from world.rules.traits import GAUGE_KEYS

from .buff_class import RulebookBuff
from .definitions import (
    BUFF_DEFINITIONS,
    _NO_OP_RATE_TARGETS,
    RecoveryRatePolicy,
    TickRecord,
    get_recovery_policy,
)


def _is_damaging_gauge_rate(rate: dict[str, Any] | None) -> bool:
    """Return whether one rate modifier damages a gauge (HP or MP, negative delta)."""
    if not isinstance(rate, dict):
        return False
    return (
        rate.get("target") in ("hp", "mp")
        and isinstance(rate.get("delta"), (int, float))
        and not isinstance(rate.get("delta"), bool)
        and rate["delta"] < 0
    )


def _is_damaging_rate(rate: dict[str, Any] | None) -> bool:
    """Return whether one rate modifier damages HP (negative delta)."""
    return _is_damaging_gauge_rate(rate) and isinstance(rate, dict) and rate.get("target") == "hp"


def _resolve_source_origin(entity: Any, source_pk: int | None) -> Any | None:
    """Resolve a tick's cached source dbref to a live entity, or ``None``.

    Consults active battlefields first (roster-then-dbref posture matching
    upkeep credit resolver), falling back to ObjectDB.
    """
    if source_pk is None:
        return None
    from world.rules.skip_safety import _active_battlefield_for

    battlefield = _active_battlefield_for(entity)
    if battlefield is not None:
        for member in battlefield.roster.values():
            pk = getattr(member, "pk", None)
            if isinstance(pk, int) and pk == source_pk:
                return member
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(id=source_pk).first()


def _credit_caster_share(origin: Any, amount: int) -> None:
    """Credit HP to a living origin caster, clamped at max HP, without reviving or dispatching."""
    if amount <= 0:
        return
    traits = getattr(origin, "traits", None)
    if traits is None or not hasattr(traits, "hp"):
        return
    from world.rules.action import stored_gauge_pair

    current_hp, max_hp = stored_gauge_pair(origin, "hp")
    if current_hp <= 0:
        return
    new_hp = min(max_hp, current_hp + amount)
    hp_trait = origin.traits.hp
    if hasattr(hp_trait, "current"):
        hp_trait.current = new_hp
    else:
        hp_trait.value = new_hp


def _apply_rate_modifier(
    entity,
    rate_mod: dict[str, Any],
    source_tier: str | None = None,
    source_skill: str | None = None,
    source_pk: int | None = None,
) -> None:
    """Apply one rate tick.

    ``skill_practice`` (the ``conferred_growth_rate`` buff's declared rate
    target) intentionally does nothing here: change 11b's
    ``growth_rate_multiplier(entity)`` reads it by pull at the moment
    progression is computed. Applying it on tick as well would double-apply
    the conferred scale.
    """
    target = rate_mod["target"]
    if target in _NO_OP_RATE_TARGETS:
        return
    if target not in GAUGE_KEYS:
        raise NotImplementedError(
            f"buff rate target {target!r} belongs to its owning future change"
        )
    delta = rate_mod["delta"]
    if target == "mp":
        from world.rules.mp_flow import apply_mp_change

        apply_mp_change(
            entity,
            delta,
            source_skill=source_skill,
            source_tier=source_tier,
        )
        return

    trait = getattr(entity.traits, target)
    current = getattr(trait, "current", None)
    if current is not None:
        before = float(current)
        if target == "hp" and before <= 0:
            return
        trait.current = current + delta
        after = float(getattr(trait, "current", 0))
    else:
        before = float(getattr(trait, "value", 0))
        if target == "hp" and before <= 0:
            return
        trait.value = getattr(trait, "value", 0) + delta
        after = float(getattr(trait, "value", 0))

    if target == "hp" and delta < 0:
        actual_loss = max(0, int(before - max(0.0, after)))
        if actual_loss > 0:
            from world.rules.state_reactions import dispatch_outcome_reaction

            tier = source_tier or "學徒"
            dispatch_outcome_reaction(
                entity, "hp_loss", source_tier=tier, hp_loss_amount=actual_loss
            )

        caster_share = rate_mod.get("caster_share")
        if caster_share is not None and actual_loss > 0 and source_pk is not None:
            credit = floor(actual_loss * float(caster_share))
            if credit > 0:
                origin = _resolve_source_origin(entity, source_pk)
                if origin is not None:
                    _credit_caster_share(origin, credit)


def _apply_recovery_tick(entity, buff: RulebookBuff, policy: RecoveryRatePolicy) -> None:
    """Execute one sustained recovery tick according to the RecoveryRatePolicy.

    Restores living recipients:
    amount = max(0, floor(base * (1 + 0.1 * exposure_ordinal) * (1 + snapshot_heal_gain / 100) * snapshot_grace_multiplier))
    clamped to living HP gap. Never revives dead recipients.
    """
    trait = getattr(getattr(entity, "traits", None), policy.target, None)
    if trait is None:
        return
    current = getattr(trait, "current", None)
    if current is None:
        current = getattr(trait, "value", None)
    if current is None or current <= 0:
        # Dead recipient or missing HP gauge: never revive or tick
        return

    max_hp = getattr(trait, "max", None)
    if max_hp is None:
        max_hp = getattr(trait, "max_value", None)
    if max_hp is None:
        return

    # Live recipient effective exposure
    from world.rules.equipment_effects import effective_exposure
    from world.rules.sexual_state import EXPOSURE_LEVELS
    from world.rules.stored_sexual_reads import StoredLevel

    exposure = effective_exposure(entity)
    ordinal = 0
    if isinstance(exposure, StoredLevel) and tuple(exposure.levels) == EXPOSURE_LEVELS:
        ordinal = int(exposure.value)
    elif isinstance(exposure, str) and exposure in EXPOSURE_LEVELS:
        ordinal = EXPOSURE_LEVELS.index(exposure)
    elif isinstance(exposure, StoredLevel):
        ordinal = int(exposure.value)

    snap_heal_gain = float(getattr(buff, "snapshot_heal_gain", 0.0) or 0.0)
    snap_grace = float(getattr(buff, "snapshot_grace_multiplier", 1.0) or 1.0)

    exposure_factor = 1.0 + policy.exposure_percent_per_ordinal * ordinal
    heal_gain_factor = 1.0 + (snap_heal_gain / 100.0)
    raw_amount = floor(policy.base * exposure_factor * heal_gain_factor * snap_grace)
    amount = max(0, raw_amount)

    hp_gap = max(0, int(max_hp) - int(current))
    actual_heal = min(amount, hp_gap)
    if actual_heal > 0:
        trait.current = current + actual_heal


def _active_buff_instances(entity) -> tuple[RulebookBuff, ...]:
    """Return unpaused game-time-unexpired buff instances with positive stacks."""
    if not hasattr(entity, "buffs"):
        return ()
    if hasattr(entity, "attributes") and not entity.attributes.has("buffs"):
        return ()
    buffs = getattr(entity, "buffs", None)
    if buffs is None or not hasattr(buffs, "all"):
        return ()
    return tuple(
        buff
        for buff in buffs.all.values()
        if not getattr(buff, "paused", False)
        and getattr(buff, "stacks", 1) > 0
        and (
            getattr(buff, "remaining_seconds", None) is None
            or buff.remaining_seconds > 0
        )
    )


def tick_buffs(
    entity, elapsed_seconds: int | None = None
) -> tuple[TickRecord, ...]:
    """Settle rulebook buffs from explicit game seconds, never wall time.

    Returns one ordered ``TickRecord`` per damaging rate tick that actually
    fired, in application order. Marker and growth-rate buffs apply as today
    and yield no records; a caller that ignores the return value observes
    exactly the pre-change state changes.

    Even finite rulebook durations use Evennia's non-expiring handler mode;
    ``remaining_seconds`` is the sole authority for expiry.
    """
    if elapsed_seconds is not None and elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    records: list[TickRecord] = []
    for buff in _active_buff_instances(entity):
        interval = getattr(buff, "tick_interval", None)
        elapsed = interval if elapsed_seconds is None else elapsed_seconds
        remaining = getattr(buff, "remaining_seconds", None)
        applied_elapsed = elapsed if remaining is None else min(elapsed, remaining)
        if interval is not None:
            accumulated = buff.tick_elapsed_seconds + applied_elapsed
            while accumulated >= interval:
                rate = BUFF_DEFINITIONS[buff.definition_key].modifiers.get("rate")
                if _is_damaging_rate(rate):
                    records.append(
                        TickRecord(
                            definition_key=buff.definition_key,
                            source_pk=getattr(buff, "source_pk", None),
                            delta=int(rate["delta"]),
                            hp_before=float(entity.traits.hp.current),
                        )
                    )
                buff.at_tick(initial=False)
                recovery_policy = get_recovery_policy(BUFF_DEFINITIONS[buff.definition_key])
                if recovery_policy is not None:
                    _apply_recovery_tick(entity, buff, recovery_policy)
                accumulated -= interval
            buff.tick_elapsed_seconds = accumulated
        if remaining is not None:
            buff.remaining_seconds = max(0, remaining - elapsed)
    return tuple(records)
