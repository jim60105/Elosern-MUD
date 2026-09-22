"""Lifetime counters, climax-cycle guard, decay, and settlement functions."""

from world.rules.sexual_state.pleasure import PLEASURE_CONFIG
from world.rules.sexual_state.traits import _STATE_CATEGORY
from world.rules.skill_ownership import owns_stored_skill

_LIFETIME_COUNTER_KEYS = (
    "masturbation_count",
    "toy_use_count",
    "exposure_act_count",
    "watched_count",
    "duo_act_count",
    "group_act_count",
    "hostile_act_count",
    "restraint_count",
    "interspecies_act_count",
    "climax_count",
    "climax_extension_count",
)

_VALID_CLIMAX_TRANSITIONS = {
    "未達": {"接近"},
    "接近": {"進行中", "未達"},
    "進行中": {"餘韻"},
    "餘韻": {"未達", "接近"},
}

# The arousal level a 聖女容器 (saintess_vessel) holder never decays below
# (saintess-vessel D2a: 聖光涓流 keeps the gauge inside 微興奮～中等).
_VESSEL_IDLE_LEVEL = "微興奮"


def _apply_climax_phase_set(entity, target_level: str) -> str | None:
    """Apply a valid edge in the climax cycle, otherwise leave state unchanged."""
    current = entity.sexual.climax_phase.level
    if target_level not in _VALID_CLIMAX_TRANSITIONS.get(current, set()):
        return None
    entity.sexual.climax_phase.value = target_level
    # Route through the phase_hooks leaf — importing the reaction engine here
    # would drag the whole cast pipeline into world.rules.pleasure's import
    # closure. The dispatcher is registered at bootstrap (see
    # server/conf/at_server_startstop.py); an unregistered edge proceeds
    # without reactions, since empowerment is additive.
    from world.rules.phase_hooks import dispatch_phase_reaction

    dispatch_phase_reaction(entity, from_phase=current, to_phase=target_level)
    return "cycle"


DECAY_CONFIG = {
    "pleasure": {"interval_seconds": 1800, "floor": "平靜"},
    "wetness": {"interval_seconds": 900, "floor": "乾燥"},
    "shame": {"interval_seconds": 1800, "floor": "無"},
    "climax_phase": {
        "interval_seconds": 300,
        "floor": "未達",
        "only_from": "餘韻",
    },
}


def decay_tick(entity, elapsed_seconds: int) -> None:
    """Apply at most one decay step per configured field.

    Future buffs may address a field by its ``DECAY_CONFIG`` key, or a
    sensitivity entry as ``sensitivity__<part>``. Their rate, bounds, and
    decay levers are intentionally not implemented by this change.
    """
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")

    for field, config in DECAY_CONFIG.items():
        accumulator_key = f"decay_elapsed__{field}"
        trait = getattr(entity.sexual, field)
        only_from = config.get("only_from")
        if only_from is not None and trait.level != only_from:
            entity.attributes.add(
                accumulator_key,
                0,
                category=_STATE_CATEGORY,
            )
            continue
        accumulated = entity.attributes.get(
            accumulator_key,
            default=0,
            category=_STATE_CATEGORY,
        )
        accumulated += elapsed_seconds
        interval = config["interval_seconds"]
        if accumulated < interval:
            entity.attributes.add(
                accumulator_key,
                accumulated,
                category=_STATE_CATEGORY,
            )
            continue

        if field == "climax_phase":
            _apply_climax_phase_set(entity, config["floor"])
        elif field == "pleasure":
            current_band_floor = PLEASURE_CONFIG.floor_for(trait.value)
            if owns_stored_skill(entity, "saintess_vessel"):
                # 聖光涓流 (saintess-vessel D2a): a 聖女容器 holder's decay
                # target never drops below the 微興奮 floor, and a holder at
                # or below it with decay due is a no-op (the accumulator
                # still resets below, like any fired step). The per-advance
                # trickle step (world.rules.pleasure) owns the sub-floor
                # pin-up; decay itself can never leave a holder in 平靜.
                idle_floor = PLEASURE_CONFIG.floor_for_level(_VESSEL_IDLE_LEVEL)
                if trait.base > idle_floor:
                    trait.base = max(idle_floor, current_band_floor - 1)
            else:
                trait.base = max(0, current_band_floor - 1)
        else:
            floor = trait._ordinal_of(config["floor"])
            trait.value = max(floor, trait.value - 1)
        entity.attributes.add(
            accumulator_key,
            0,
            category=_STATE_CATEGORY,
        )


def reset_daily_counters(entity) -> None:
    """Reset the daily climax count without changing any other field."""
    entity.sexual._traits.climax_today.base = 0


def climax_settlement_action(entity) -> str | None:
    """Advance climax-turn bookkeeping and report which settlement action to take.

    Returns ``"extend"`` when a staged extension is consumed, ``"end"`` when
    the entity must resolve its climax normally, or ``None`` when
    ``climax_phase`` is not 進行中 (``climax_turns`` is reset to ``0`` in this
    case, if it was nonzero).

    This performs every mutation that does not require the ``sexual.yaml``
    rule cascade: ``climax_turns`` and ``pending_climax_extension``
    bookkeeping, and the two lifetime counter increments. It does NOT call
    ``apply_event()`` — the caller (``combat.py`` or ``clock.py``) does that,
    using the returned action to choose between ``"climax_extended"`` and
    ``"climax_ends"``.
    """
    sexual = getattr(entity, "sexual", None)
    if sexual is None:
        return None
    if sexual.climax_phase.level != "進行中":
        if sexual.climax_turns != 0:
            entity.attributes.add(
                "climax_turns",
                0,
                category=_STATE_CATEGORY,
            )
        if sexual.pending_climax_extension != 0:
            entity.attributes.add(
                "pending_climax_extension",
                0,
                category=_STATE_CATEGORY,
            )
        return None
    entity.attributes.add(
        "climax_turns",
        sexual.climax_turns + 1,
        category=_STATE_CATEGORY,
    )
    if sexual.pending_climax_extension > 0:
        entity.attributes.add(
            "pending_climax_extension",
            sexual.pending_climax_extension - 1,
            category=_STATE_CATEGORY,
        )
        sexual.record_climax_extension()
        return "extend"
    sexual.record_climax_count()
    return "end"
