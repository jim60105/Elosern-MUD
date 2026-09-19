"""The ``heal`` and ``self_heal`` effect handlers.

Magnitude is caster-stat-derived at staging time (mirroring ``damage``), the
restoration is clamped to the target's remaining hp gap at both staging and
commit time, and healing never revives a fallen entity.
"""

from typing import Any

from world.rules.action import (
    PendingEffect,
    _stored_trait_value,
    register_effect_handler,
)
from world.rules.combat.battlefield import COMBAT_YAML, _adjusted_attack, _max_hp
from world.rules.combat.damage import _extract_effect_coefficient
from world.rules.combat_modifiers import apply_cost_modifier, evaluate_combat_modifiers
from world.rules.progression import scaled_magnitude
from world.skills.effects import SelfHealEffect, parse_effect


def _heal_magnitude(actor: Any, coefficient: float = 1.0) -> int:
    """Return the caster-stat-derived HP restoration amount for one heal.

    Substitutes a healing coefficient for damage's roll-derived multiplier and
    drops the defense-mitigation term entirely (healing is not mitigated), so
    the magnitude shares damage's ``round(effective value x multiplier)``
    shape without inheriting its to-hit or defense assumptions (design.md
    magnitude decision). The caster stat reads through the equipment-aware
    attack path (a ``magic_power``-granting robe heals harder), and the
    unamplified base is then scaled by the merged ``heal_gain`` percent with
    the normative formula ``max(floor(base x (1 + pct/100)), heal.floor)``
    (wire-equipment-combat-modifiers D4): flooring, not banker-rounding, and
    the configured floor always wins. Item-use healing keeps its flat
    rulebook amount and is never scaled here.
    """
    multiplier = float(COMBAT_YAML["heal"]["multiplier"])
    floor = int(COMBAT_YAML["heal"]["floor"])
    magic = _adjusted_attack(actor, "magic_power")
    base_amount = max(round(magic * multiplier * coefficient), floor)
    heal_gain = evaluate_combat_modifiers(actor).get("heal_gain")
    return max(apply_cost_modifier(base_amount, heal_gain), floor)


def _parse_heal_effect(effect_id: str) -> str:
    parts = effect_id.split(":")
    if len(parts) != 2 or parts[0] != "heal" or parts[1] not in {"single", "area"}:
        raise ValueError("heal effect must be heal:single or heal:area")
    return parts[1]


def _parse_self_heal_effect(effect_id: str) -> SelfHealEffect:
    parsed = parse_effect(effect_id)
    if not isinstance(parsed, SelfHealEffect):
        raise ValueError(f"expected self_heal effect, got {effect_id!r}")
    return parsed


def _restored_amount(entity: Any, amount: int) -> int:
    """Return how much of a heal actually applies to one entity right now.

    An entity that is not alive restores nothing (a heal never revives), and
    the restoration is capped by the remaining gap to the entity's maximum so
    the staged event log reflects the real HP increase. The result is always
    an integer: a cap computed from float gauge storage must never leak a
    fractional amount into the staged log or the applied delta.
    """
    current = _stored_trait_value(entity.traits.hp)
    if current <= 0:
        return 0
    return int(min(amount, max(0, _max_hp(entity) - current)))


def _apply_heal(entity: Any, amount: int) -> None:
    """Restore HP clamped to the entity's maximum; never revives or decreases.

    The commit-time alive guard keeps the no-revival invariant even when an
    earlier effect in the same action reduced the entity below 1 HP after
    staging: such an entity stays knocked out.
    """
    trait = entity.traits.hp
    current = _stored_trait_value(trait)
    if current <= 0:
        return
    clamped = min(_max_hp(entity), current + amount)
    if hasattr(trait, "current"):
        trait.current = clamped
    else:
        trait.value = clamped


def _handle_heal(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    event_context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one HP-restoring pending effect per already-validated target.

    The magnitude is computed at staging time from caster stats, mirroring
    ``damage`` (and scaled by ``scale`` the same way); the per-target
    restoration is clamped by that target's current HP gap so the staged event
    log reports the real increase, and the commit-time closure re-checks
    aliveness and the cap.
    """
    _parse_heal_effect(effect_id)
    coefficient = _extract_effect_coefficient(event_context)
    amount = scaled_magnitude(_heal_magnitude(actor, coefficient), scale)
    pending: list[PendingEffect] = []
    for target in targets:
        key = str(target.key)
        restored = _restored_amount(target, amount)
        pending.append(
            PendingEffect(
                entity=target,
                description=f"heal|{key}|{restored}",
                surfaces=frozenset(),
                apply=lambda target=target, restored=restored: _apply_heal(
                    target, restored
                ),
            )
        )
    return pending


def _handle_self_heal(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    event_context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one HP-restoring pending effect bound to the caster.

    Mirrors ``self_buff_apply``'s actor-binding pattern: a target-list-driven
    heal cannot express "the caster heals themself while the same cast also
    damages an enemy", so this effect binds the actor instead of ``targets``.
    """
    del targets
    parsed = _parse_self_heal_effect(effect_id)
    if parsed.basis == "stat":
        coefficient = _extract_effect_coefficient(event_context)
        amount = scaled_magnitude(_heal_magnitude(actor, coefficient), scale)
    elif parsed.basis == "missing_fraction":
        current = _stored_trait_value(actor.traits.hp)
        missing_hp = max(0.0, _max_hp(actor) - current) if current > 0 else 0.0
        base_amount = int(round(missing_hp * parsed.fraction))
        amount = scaled_magnitude(base_amount, scale) if base_amount > 0 else 0
    else:
        raise ValueError(f"unsupported self_heal basis: {parsed.basis!r}")
    restored = _restored_amount(actor, amount)
    return [
        PendingEffect(
            entity=actor,
            description=f"self_heal|{str(actor.key)}|{restored}",
            surfaces=frozenset(),
            apply=lambda: _apply_heal(actor, restored),
        )
    ]


register_effect_handler(
    "heal",
    _handle_heal,
    surfaces=frozenset({"traits"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "self_heal",
    _handle_self_heal,
    surfaces=frozenset({"traits"}),
    requires_event_context=frozenset(),
)
