"""The ``damage`` effect handler: d100 hit resolution and hp-delta staging.

Everything here stages through the resolver's commit semantics: the handler
computes hit and damage at staging time and returns pending effects whose
closures are the only writers. The module consumes the rulebook and the
read-only stat helpers owned by :mod:`world.rules.combat.battlefield`.
"""

from math import floor as math_floor
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.rules.action import (
    PendingEffect,
    _stored_trait_value,
    register_effect_handler,
    stored_gauge_pair,
)
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    get_divert_consumed,
    update_divert_consumed,
    _active_buff_instances,
)
from world.rules.combat.battlefield import (
    COMBAT_YAML,
    _adjusted_attack,
    _adjusted_defense,
    _max_hp,
)
from world.rules.combat_modifiers import adjusted_agility, evaluate_combat_modifiers
from world.rules.action_evidence import has_action_evidence
from world.rules.dice import roll_d100
from world.rules.mp_flow import apply_mp_change
from world.rules.progression import scaled_magnitude
from world.rules.state_reactions import dispatch_outcome_reaction
from world.rules.target_facts import matches_target_predicate
from world.skills.effects import (
    DamageEffect,
    DamagePolicy,
    EffectPolicy,
    ResolvedEffect,
    parse_effect,
)


def _extract_effect_coefficient(event_context: dict[str, Any] | None) -> float:
    """Extract the trusted potency coefficient or fall back to identity 1.0.

    When invoked through ActionResolver, ``event_context`` carries the trusted
    ``ResolvedEffect`` synthesized for this effect ordinal. Direct invocations
    without the binding or with an unverified object use identity semantics.
    """
    if not event_context:
        return 1.0
    resolved = event_context.get("resolved_effect")
    if isinstance(resolved, ResolvedEffect) and isinstance(resolved.policy, EffectPolicy):
        return resolved.policy.coefficient
    return 1.0


def _extract_damage_policy(event_context: dict[str, Any] | None) -> DamagePolicy | None:
    """Extract the trusted DamagePolicy or None if not configured.

    When invoked through ActionResolver, ``event_context`` carries the trusted
    ``ResolvedEffect`` synthesized for this effect ordinal. Direct invocations
    without the binding or with an unverified object return None.
    """
    if not event_context:
        return None
    resolved = event_context.get("resolved_effect")
    if (
        isinstance(resolved, ResolvedEffect)
        and isinstance(resolved.policy, EffectPolicy)
        and isinstance(resolved.policy.damage, DamagePolicy)
    ):
        return resolved.policy.damage
    return None


def _roll_multiplier(raw_roll: int, margin: float) -> float:
    damage = COMBAT_YAML["damage"]
    if raw_roll == 100:
        return float(damage["crit_multiplier"])
    if margin >= damage["solid_hit_margin"]:
        return float(damage["solid_hit_multiplier"])
    return float(damage["base_multiplier"])


def _to_hit(
    attacker: Any,
    defender: Any,
    raw_roll: int,
) -> tuple[bool, float]:
    attacker_mods = evaluate_combat_modifiers(attacker)
    defender_mods = evaluate_combat_modifiers(defender)
    attacker_agility = adjusted_agility(attacker, attacker_mods)
    defender_agility = adjusted_agility(defender, defender_mods)
    attack_score = (
        raw_roll + attacker_agility + attacker_mods.get("accuracy", 0)
    )
    threshold = (
        COMBAT_YAML["to_hit"]["defender_constant"] + defender_agility
    )
    margin = attack_score - threshold
    return margin >= 0, margin


def _parse_damage_effect(effect_id: str) -> DamageEffect:
    """Parse and fully validate one damage effect for cast-time resolution.

    Delegates the string grammar to the canonical ``parse_effect`` (the
    registry-load-time parser) instead of re-splitting the shape here, and
    layers the one cast-time-only check ``parse_effect`` deliberately
    excludes: a non-``None`` element must be a real ``ELEMENT_REGISTRY``
    key. ``None`` (the elementless sentinel) is always legal and is never
    checked against the registry.
    """
    parsed = parse_effect(effect_id)
    if not isinstance(parsed, DamageEffect):
        raise ValueError(f"expected damage effect, got {effect_id!r}")
    if parsed.element is not None and parsed.element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown damage element {parsed.element!r}")
    return parsed


def _apply_hp_delta(entity: Any, delta: int) -> None:
    trait = entity.traits.hp
    if hasattr(trait, "current"):
        trait.current = _stored_trait_value(trait) + delta
    else:
        trait.value = _stored_trait_value(trait) + delta


def _apply_hp_delta_nonlethal(entity: Any, delta: int) -> None:
    """Apply damage with a knockout floor: a lethal crossing stops at 1 HP.

    The projection applies the ordinary delta, then any positive-to-zero-or-
    below crossing is clamped to 1 instead of reaching zero, so the target is
    knocked out rather than defeated (guild-economy D-7).
    """
    trait = entity.traits.hp
    current = _stored_trait_value(trait)
    projected = current + delta
    if current > 0 and projected <= 0:
        projected = 1
    if hasattr(trait, "current"):
        trait.current = projected
    else:
        trait.value = projected


def _noop() -> None:
    """Commit-time no-op for a staged miss."""


def _handle_damage(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    event_context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage d100 hit and damage results; commit only the computed hp delta.

    The nonlethal policy is per-damaged-target (party-combat D-3): the
    session-wide ``nonlethal`` flag (examinations) protects every target, while
    ``nonlethal_keys`` protects only the named entities (allied companions in a
    hostile session). A protected crossing floors HP at 1; a crossing protected
    by the per-entity key set also stages a battlefield ``knocked_out`` mark
    inside the same commit, so the in-round initiative, targeting, overwhelm,
    and terminal consumers observe the knockout through the shared predicate.

    The final per-target amount is scaled by ``scaled_magnitude`` and clamped
    at the unscaled ``combat.yaml`` damage floor (the floor itself is never
    scaled, so even a 1/4 cast lands its minimum hit).
    """
    school = _parse_damage_effect(effect_id).school
    attack_key = "atk_phys" if school == "physical" else "magic_power"
    coefficient = _extract_effect_coefficient(event_context)
    damage_policy = _extract_damage_policy(event_context)
    session_nonlethal = bool(event_context.get("nonlethal", False))
    nonlethal_keys = frozenset(event_context.get("nonlethal_keys", ()))
    battlefield = event_context.get("battlefield")
    now = event_context.get("now") if event_context is not None else None
    floor = int(COMBAT_YAML["damage"]["floor"])
    source_tier = "學徒"
    resolved = event_context.get("resolved_effect") if event_context is not None else None
    source_skill = getattr(resolved, "source_skill", None)
    if source_skill is not None:
        try:
            from world.skills.cost_tiers import spell_tier_for

            resolved_tier = spell_tier_for(source_skill)
            if resolved_tier:
                source_tier = resolved_tier
        except Exception:  # observability: ignore R2: nonspell or out-of-tier skill safely falls back to apprentice rung
            source_tier = "學徒"
    pending: list[PendingEffect] = []
    for target in targets:
        key = str(target.key)
        protected = session_nonlethal or key in nonlethal_keys
        marked: list[str] = []
        extra = (
            damage_policy is not None
            and damage_policy.extra_strikes > 0
            and (
                damage_policy.repeat_when is None
                or has_action_evidence(target, damage_policy.repeat_when, now=now)
            )
        )
        total_strikes = 1 + damage_policy.extra_strikes if extra else 1
        planned_cap_spend: dict[str, int] = {}
        planned_gauge_spend: dict[str, int] = {}

        for _ in range(total_strikes):
            raw_roll = roll_d100()
            hit, margin = _to_hit(actor, target, raw_roll)
            amount = 0
            if hit:
                multiplier = _roll_multiplier(raw_roll, margin)
                attack = _adjusted_attack(actor, attack_key)
                if damage_policy is not None:
                    matched = matches_target_predicate(target, damage_policy.predicate)
                    matched_mult = damage_policy.attack_multiplier if matched else 1.0
                    defense = (
                        0
                        if (
                            damage_policy.unconditional_defense_bypass
                            or (damage_policy.bypass_defense and (matched or not damage_policy.predicate))
                        )
                        else _adjusted_defense(target)
                    )
                    max_hp_frac = damage_policy.max_hp_fraction
                else:
                    matched_mult = 1.0
                    defense = _adjusted_defense(target)
                    max_hp_frac = 0.0
                attack_part = round(attack * multiplier * coefficient * matched_mult)
                post_defense = attack_part - defense
                rider = math_floor(round(_max_hp(target) * max_hp_frac, 6))
                base_amount = int(max(post_defense + rider, floor))
                amount = max(scaled_magnitude(base_amount, scale), floor)
                amount = int(amount)

            residual = amount
            planned_diverts: list[tuple[Any, int, str, str | None, str | None]] = []
            if hit and amount > 0:
                active_diverts = [
                    buff
                    for buff in _active_buff_instances(target)
                    if BUFF_DEFINITIONS.get(buff.definition_key) is not None
                    and "divert" in BUFF_DEFINITIONS[buff.definition_key].modifiers
                ]
                active_diverts.sort(
                    key=lambda b: (
                        b.definition_key,
                        getattr(b, "buffkey", b.definition_key),
                    )
                )
                for buff in active_diverts:
                    if residual <= 0:
                        break
                    spec = BUFF_DEFINITIONS[buff.definition_key].modifiers["divert"]
                    target_gauge = spec["target"]
                    fraction = float(spec["fraction"])
                    cap = int(spec["cap"])
                    buff_id = getattr(buff, "buffkey", buff.definition_key)
                    consumed = get_divert_consumed(buff)
                    already_spent_cap = planned_cap_spend.get(buff_id, 0)
                    remaining_cap = max(0, cap - consumed - already_spent_cap)
                    current_gauge, _ = stored_gauge_pair(target, target_gauge)
                    already_spent_gauge = planned_gauge_spend.get(target_gauge, 0)
                    available_gauge = max(0, current_gauge - already_spent_gauge)

                    diverted = min(
                        round(residual * fraction), remaining_cap, available_gauge
                    )
                    diverted = max(0, int(diverted))
                    if diverted > 0:
                        residual -= diverted
                        planned_cap_spend[buff_id] = already_spent_cap + diverted
                        planned_gauge_spend[target_gauge] = already_spent_gauge + diverted
                        src_skill = getattr(buff, "source_skill", None)
                        src_tier = getattr(buff, "source_tier", None) or "學徒"
                        planned_diverts.append(
                            (buff, diverted, target_gauge, src_skill, src_tier)
                        )
            residual = max(0, residual)

            def apply(
                target=target,
                amount=residual,
                hit=hit,
                key=key,
                protected=protected,
                marked=marked,
                source_tier=source_tier,
                school=school,
                actor=actor,
                source_skill=source_skill,
                session_nonlethal=session_nonlethal,
                nonlethal_keys=nonlethal_keys,
                battlefield=battlefield,
            ) -> None:
                if not hit:
                    _noop()
                    return
                before = _stored_trait_value(target.traits.hp)
                if not protected:
                    _apply_hp_delta(target, -amount)
                else:
                    _apply_hp_delta_nonlethal(target, -amount)
                    if before > 0 and before - amount <= 0 and key in nonlethal_keys:
                        if key not in marked:
                            marked.append(key)
                after = _stored_trait_value(target.traits.hp)
                actual_loss = max(0, int(before - max(0.0, after)))
                if actual_loss > 0:
                    skill_key = getattr(source_skill, "key", source_skill)
                    dispatch_outcome_reaction(
                        target,
                        "hp_loss",
                        source_tier=source_tier,
                        hp_loss_amount=actual_loss,
                    )
                    if school == "physical":
                        dispatch_outcome_reaction(
                            target,
                            "physical_hit",
                            source_tier=source_tier,
                            source_skill=skill_key,
                            source=actor,
                            nonlethal=session_nonlethal,
                            nonlethal_keys=nonlethal_keys,
                            battlefield=battlefield,
                        )

            pending.append(
                PendingEffect(
                    entity=target,
                    description=(
                        f"damage|{key}|{raw_roll}|{int(hit)}|{residual}"
                    ),
                    surfaces=frozenset({"traits", "buffs"}),
                    apply=apply,
                )
            )
            for buff, diverted, target_gauge, src_skill, src_tier in planned_diverts:
                def make_divert_apply(
                    b=buff,
                    div=diverted,
                    g_key=target_gauge,
                    s_skill=src_skill,
                    s_tier=src_tier,
                    cap=int(BUFF_DEFINITIONS[buff.definition_key].modifiers["divert"]["cap"]),
                ):
                    def apply_divert() -> None:
                        buff_key = getattr(b, "buffkey", getattr(b, "definition_key", None))
                        live_buff = b
                        if hasattr(target, "buffs") and hasattr(target.buffs, "all"):
                            live_buff = target.buffs.all.get(buff_key, b)
                        cur_consumed = get_divert_consumed(live_buff)
                        rem_cap = max(0, cap - cur_consumed)
                        to_pay = min(div, rem_cap)
                        if to_pay <= 0:
                            return
                        if g_key == "mp":
                            actual_delta = apply_mp_change(
                                target,
                                -to_pay,
                                source_skill=s_skill,
                                source_tier=s_tier,
                            )
                            paid = abs(actual_delta)
                        elif g_key == "hp":
                            trait = getattr(target.traits, "hp")
                            before = _stored_trait_value(trait)
                            _apply_hp_delta(target, -to_pay)
                            after = _stored_trait_value(trait)
                            paid = max(0, int(before - max(0.0, after)))
                        else:
                            raise NotImplementedError(
                                f"divert target {g_key!r} is not supported"
                            )
                        update_divert_consumed(live_buff, cur_consumed + paid)
                        if live_buff is not b:
                            update_divert_consumed(b, cur_consumed + paid)

                    return apply_divert

                pending.append(
                    PendingEffect(
                        entity=target,
                        description=(
                            f"damage_divert|{key}|{buff.definition_key}|{diverted}"
                        ),
                        surfaces=frozenset({"traits", "buffs"}),
                        apply=make_divert_apply(),
                    )
                )
        if key in nonlethal_keys and battlefield is not None:
            # One battlefield-shaped effect per protected target: the commit's
            # duck-typed snapshot/restore dispatch captures ``fled`` and
            # ``knocked_out`` by shape, so a later commit failure rolls the
            # mark back with the HP floor (battlefield-commit-surface).
            pending.append(
                PendingEffect(
                    entity=battlefield,
                    description=f"knocked_out_mark|{key}",
                    surfaces=frozenset(),
                    apply=lambda marked=marked: (
                        battlefield.knocked_out.update(marked)
                    ),
                )
            )
    if (
        battlefield is not None
        and nonlethal_keys
        and not any(e.entity is battlefield for e in pending)
    ):
        pending.append(
            PendingEffect(
                entity=battlefield,
                description="knocked_out_mark|battlefield",
                surfaces=frozenset(),
                apply=_noop,
            )
        )
    return pending


register_effect_handler(
    "damage",
    _handle_damage,
    surfaces=frozenset({"traits", "buffs"}),
    requires_event_context=frozenset(),
)
