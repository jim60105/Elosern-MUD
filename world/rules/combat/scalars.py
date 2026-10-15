"""The one expression of the scalar combat arithmetic settlement stages.

The damage, heal and self_heal handlers used to own this arithmetic inline;
extracting it here means settlement and effect estimation cannot drift, because
both call the same expression instead of one of them restating the formula.
Every function is a pure function of scalars and the loaded combat rulebook:
nothing here rolls dice, reads an entity, mounts a handler, writes state, pays a
cost or emits an event. The caller supplies every entity-derived number it read
through its own read path -- settlement through the live combat accessors, the
monster-AI estimator through its no-create decision read set.

The three outcome shapes settlement depends on live here together, because they
are the ones an estimator most easily gets wrong:

- the d100 multiplier ladder and the hit margin (:func:`damage_multiplier`,
  :func:`hit_margin`, :func:`strike_lands`);
- the staged strike amount, including ratio defense mitigation, the
  ``max_hp_fraction`` rider, the rulebook floor and the authored scale
  (:func:`strike_amount`, :func:`damage_rider`);
- the staged heal amount and the capacity caps that decide how much of a staged
  amount one recipient actually takes (:func:`heal_amount`,
  :func:`staged_restoration`, :func:`nonlethal_projection`,
  :func:`crosses_knockout`).
"""

from math import floor as math_floor

from world.rules.combat.battlefield import COMBAT_YAML
from world.rules.combat_modifiers import apply_cost_modifier
from world.rules.progression import scaled_magnitude


def damage_multiplier(raw_roll: int, margin: float) -> float:
    """Return the rulebook damage multiplier of one d100 strike outcome.

    A natural 100 is the critical hit and always wins; otherwise a margin at or
    above the rulebook's solid-hit margin is a solid hit; every other landing
    strike is a base hit.
    """
    damage = COMBAT_YAML["damage"]
    if raw_roll == 100:
        return float(damage["crit_multiplier"])
    if margin >= damage["solid_hit_margin"]:
        return float(damage["solid_hit_multiplier"])
    return float(damage["base_multiplier"])


def hit_margin(
    raw_roll: float,
    *,
    attacker_agility: float,
    attacker_accuracy: float,
    defender_agility: float,
) -> float:
    """Return one strike's margin over the defender's to-hit threshold.

    The threshold is the rulebook's defender constant plus the defender's
    adjusted agility; the attack score is the raw roll plus the attacker's
    adjusted agility plus the attacker's accuracy bundle bonus.
    """
    attack_score = raw_roll + attacker_agility + attacker_accuracy
    threshold = COMBAT_YAML["to_hit"]["defender_constant"] + defender_agility
    return attack_score - threshold


def strike_lands(margin: float) -> bool:
    """Return whether one strike's margin lands it (a non-negative margin)."""
    return margin >= 0


def damage_rider(maximum_hp: float, max_hp_fraction: float) -> int:
    """Return the ``max_hp_fraction`` devastation rider of one strike.

    The rider is added after ratio defense mitigation on any successful hit,
    regardless of whether a damage predicate is configured or matched, and it
    is zero for the ordinary ``max_hp_fraction=0.0`` policy.
    """
    return math_floor(round(maximum_hp * max_hp_fraction, 6))


def strike_amount(
    *,
    attack: float,
    multiplier: float,
    coefficient: float,
    defense: float,
    rider: int = 0,
    matched_multiplier: float = 1.0,
    scale: float = 1.0,
    weapon_multiplier: float = 1.0,
) -> int:
    """Return one landing strike's staged damage amount.

    ``round(attack x multiplier x coefficient x matched_multiplier x weapon_multiplier)`` is the
    pre-mitigation hit; ratio retention ``K / (K + max(0, defense))`` scales
    that hit (where ``K`` is ``damage.mitigation_k`` from the combat rulebook),
    the rider is added, and the result never falls below the rulebook damage
    floor. That
    unscaled amount is then scaled by the authored cast magnitude, and the
    rulebook floor is re-applied so even a fractional cast lands its minimum
    hit -- the floor itself is never scaled.
    """
    floor = int(COMBAT_YAML["damage"]["floor"])
    k = float(COMBAT_YAML["damage"]["mitigation_k"])
    attack_part = round(
        attack * multiplier * coefficient * matched_multiplier * weapon_multiplier
    )
    defense_used = max(0.0, float(defense))
    base_amount = int(max(attack_part * k / (k + defense_used) + rider, floor))
    return int(max(scaled_magnitude(base_amount, scale), floor))


def heal_amount(
    *,
    magic_power: float,
    coefficient: float = 1.0,
    heal_gain: str | None = None,
    scale: float = 1.0,
) -> int:
    """Return one heal's staged HP restoration.

    A healing coefficient substitutes for damage's roll-derived multiplier and
    healing is never mitigated, so the magnitude is the caster's magic power
    times the rulebook heal multiplier times the occurrence coefficient,
    floored at the rulebook heal floor, then amplified by the merged
    ``heal_gain`` percentage with floor rounding (the configured floor always
    wins), then scaled by the authored cast magnitude.
    """
    floor = int(COMBAT_YAML["heal"]["floor"])
    base_amount = max(
        round(magic_power * float(COMBAT_YAML["heal"]["multiplier"]) * coefficient),
        floor,
    )
    return scaled_magnitude(max(apply_cost_modifier(base_amount, heal_gain), floor), scale)


def staged_restoration(*, amount: int, current: float, maximum: float) -> int:
    """Return how much of a staged heal its recipient can take right now.

    Settlement stages a heal against the recipient's HP gap **before any part
    of the action commits**, so a recipient already at its maximum stages no
    restoration at all even when an earlier effect in the same action damaged
    it, and a heal never revives a recipient that is not alive. The result is
    always an integer: a cap computed from float gauge storage must never leak
    a fractional amount into a staged log or an applied delta.
    """
    if current <= 0:
        return 0
    return int(min(amount, max(0.0, maximum - current)))


def crosses_knockout(*, current: float, loss: float) -> bool:
    """Return whether one HP loss crosses a living recipient out of the fight.

    The crossing test is the pre-floor one settlement applies: a recipient with
    positive stored HP whose projected value reaches zero or below is knocked
    out (or defeated) whether or not a nonlethal policy then floors its stored
    HP at one.
    """
    return current > 0 and current - loss <= 0


def nonlethal_projection(*, current: float, loss: float) -> float:
    """Return the stored HP one loss leaves on a recipient floored at one.

    A protected recipient's lethal crossing stops at exactly one stored HP
    instead of reaching zero, so the recipient is knocked out rather than
    defeated. Every other loss applies unchanged and may leave any non-negative
    value.
    """
    projected = current - loss
    if crosses_knockout(current=current, loss=loss):
        return 1.0
    return projected
