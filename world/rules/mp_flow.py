"""Canonical MP mutation writer and depletion outcome dispatcher.

Owns apply_mp_change and remove_mp per water-mp-depletion-reaction design D1.
All authored MP mutations (buff ticks, cast cost deductions, future transfers)
route through this module. Clamps to gauge bounds and dispatches mp_zero
outcome reaction exactly once when MP crosses from positive to zero via a decrease.
"""

from typing import Any


def _write_mp(entity: Any, value: int) -> None:
    trait = getattr(entity.traits, "mp")
    if hasattr(trait, "current"):
        trait.current = value
    else:
        trait.value = value


def _resolve_source_tier(source_skill: str | None, source_tier: str | None) -> str:
    if source_tier is not None and str(source_tier).strip():
        return str(source_tier)
    if source_skill is not None:
        try:
            from world.skills.registry import SKILL_REGISTRY
            from world.skills.cost_tiers import spell_tier_for

            skill = SKILL_REGISTRY.get(source_skill)
            if skill is not None:
                resolved = spell_tier_for(skill)
                if resolved:
                    return resolved
        except Exception:
            pass
    return "學徒"


def apply_mp_change(
    entity: Any,
    delta: int,
    *,
    source_skill: str | None = None,
    source_tier: str | None = None,
) -> int:
    """Apply an authored MP change, clamping to gauge bounds.

    Returns the actual signed delta applied.
    Dispatches 'mp_zero' outcome reaction if and only if stored MP crossed
    from positive to zero on a negative delta.
    """
    if not isinstance(delta, int) or isinstance(delta, bool):
        raise TypeError(f"delta must be an integer, got {delta!r}")

    from world.rules.action import stored_gauge_pair

    current, maximum = stored_gauge_pair(entity, "mp")
    desired = max(0, min(maximum, current + delta))
    _write_mp(entity, desired)
    after, _ = stored_gauge_pair(entity, "mp")
    actual_delta = after - current

    if current > 0 and after == 0 and delta < 0 and actual_delta < 0:
        from world.rules.state_reactions import dispatch_outcome_reaction

        tier = _resolve_source_tier(source_skill, source_tier)
        dispatch_outcome_reaction(
            entity,
            "mp_zero",
            source_tier=tier,
            source_skill=source_skill,
        )

    return actual_delta


def remove_mp(
    entity: Any,
    *,
    source_skill: str | None = None,
    source_tier: str | None = None,
) -> int:
    """Drain all stored MP down to zero through the canonical writer.

    Returns the actual signed delta applied (e.g. -current).
    """
    from world.rules.action import stored_gauge_pair

    current, _ = stored_gauge_pair(entity, "mp")
    return apply_mp_change(
        entity,
        -current,
        source_skill=source_skill,
        source_tier=source_tier,
    )
