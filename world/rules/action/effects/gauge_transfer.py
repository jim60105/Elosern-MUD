"""The gauge_transfer effect handler.

Drain/restore components route MP through ``mp_flow`` and HP through the
attributed hp-loss write path so the canonical reaction dispatchers fire from
inside the staged apply closures. Registration lives next to the handler.
"""

from typing import Any

from world.skills.effects import parse_effect

from world.rules.action.contracts import (
    _entity_key,
    register_effect_handler,
    PendingEffect,
)
from world.rules.action.gates import _stored_trait_value, stored_gauge_pair


def _handle_gauge_transfer(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Execute one gauge_transfer effect component across validated targets.

    Routes MP mutations through mp_flow (dispatching mp_zero on positive-to-zero
    crossing), HP drain through the attributed hp-loss write path (dispatching
    hp_loss, with death settlement handled by the combat/defeat pipeline).
    Caster share is computed on actual drain and paid in the same gauge to the
    caster, folding any recovery_share_bonus from combat modifiers additively.
    Restores apply to MP only, adding per-stack bonuses for active caster markers.
    """
    del scale
    if not targets:
        return []

    eff = parse_effect(effect_id)
    resolved = context.get("resolved_effect")
    policy = resolved.policy if resolved is not None else None
    transfer_policy = policy.transfer if policy is not None else None
    skill = resolved.source_skill if resolved is not None else None
    skill_key = skill.key if skill is not None else None
    from world.rules.mp_flow import _resolve_source_tier
    skill_tier = _resolve_source_tier(skill_key, None)

    pending: list[PendingEffect] = []

    if eff.direction == "drain":
        actual_drained_box = [0]

        for target in targets:
            def apply_target_drain(target=target) -> None:
                traits = getattr(target, "traits", None)
                if traits is None or not hasattr(traits, eff.gauge):
                    return
                current, _ = stored_gauge_pair(target, eff.gauge)
                if current <= 0:
                    return
                if eff.magnitude_mode == "all":
                    requested = current
                elif eff.magnitude_mode == "fixed":
                    requested = min(int(eff.magnitude), current)
                elif eff.magnitude_mode == "fraction":
                    requested = min(round(current * eff.magnitude), current)
                else:
                    requested = 0

                if requested <= 0:
                    return

                actual = 0
                if eff.gauge == "mp":
                    from world.rules.mp_flow import apply_mp_change, remove_mp
                    if eff.magnitude_mode == "all":
                        actual_delta = remove_mp(target, source_skill=skill_key, source_tier=skill_tier)
                    else:
                        actual_delta = apply_mp_change(
                            target, -requested, source_skill=skill_key, source_tier=skill_tier
                        )
                    actual = abs(actual_delta)
                elif eff.gauge == "hp":
                    session_nonlethal = bool(context.get("nonlethal", False))
                    nonlethal_keys = frozenset(context.get("nonlethal_keys", ()))
                    key = str(target.key)
                    protected = session_nonlethal or key in nonlethal_keys
                    before = _stored_trait_value(target.traits.hp)
                    if not protected:
                        from world.rules.combat import _apply_hp_delta
                        _apply_hp_delta(target, -requested)
                    else:
                        from world.rules.combat import _apply_hp_delta_nonlethal
                        _apply_hp_delta_nonlethal(target, -requested)
                    after = _stored_trait_value(target.traits.hp)
                    actual = max(0, int(before - max(0.0, after)))
                    if actual > 0:
                        from world.rules.state_reactions import dispatch_outcome_reaction
                        dispatch_outcome_reaction(target, "hp_loss", source_tier=skill_tier)

                actual_drained_box[0] += actual

            traits = getattr(target, "traits", None)
            current, _ = stored_gauge_pair(target, eff.gauge) if traits is not None and hasattr(traits, eff.gauge) else (0, 0)
            if eff.magnitude_mode == "all":
                preview_req = current
            elif eff.magnitude_mode == "fixed":
                preview_req = min(int(eff.magnitude), current)
            elif eff.magnitude_mode == "fraction":
                preview_req = min(round(current * eff.magnitude), current)
            else:
                preview_req = 0

            pending.append(
                PendingEffect(
                    target,
                    f"gauge_transfer|{_entity_key(target)}|{eff.gauge}|drain|{preview_req}",
                    frozenset({"traits"}),
                    apply_target_drain,
                )
            )

        from world.rules.combat_modifiers import evaluate_combat_modifiers
        bundle_bonus = float(evaluate_combat_modifiers(actor).get("recovery_share_bonus", 0.0))
        authored_share = transfer_policy.caster_recovery_share if transfer_policy is not None else 0.0
        effective_share = min(1.0, authored_share + bundle_bonus)

        if effective_share > 0.0:
            def apply_actor_share(actor=actor) -> None:
                traits = getattr(actor, "traits", None)
                if traits is None or not hasattr(traits, eff.gauge):
                    return
                total_drained = actual_drained_box[0]
                if total_drained <= 0:
                    return
                share_amount = min(total_drained, round(total_drained * effective_share))
                if share_amount <= 0:
                    return
                if eff.gauge == "mp":
                    from world.rules.mp_flow import apply_mp_change
                    apply_mp_change(actor, share_amount, source_skill=skill_key, source_tier=skill_tier)
                elif eff.gauge == "hp":
                    current_hp, max_hp = stored_gauge_pair(actor, "hp")
                    if current_hp <= 0:
                        return
                    new_hp = min(max_hp, current_hp + share_amount)
                    if hasattr(actor.traits.hp, "current"):
                        actor.traits.hp.current = new_hp
                    else:
                        actor.traits.hp.value = new_hp

            pending.append(
                PendingEffect(
                    actor,
                    f"gauge_transfer_actor|{_entity_key(actor)}|{eff.gauge}|drain|0",
                    frozenset({"traits"}),
                    apply_actor_share,
                )
            )

    elif eff.direction == "restore":
        bonus = 0
        if transfer_policy is not None and transfer_policy.restore_bonus_per_stack:
            from world.rules.buffs import active_stack_count
            for marker_key, per_stack in transfer_policy.restore_bonus_per_stack:
                count = active_stack_count(actor, marker_key)
                bonus += count * per_stack

        for target in targets:
            def apply_target_restore(target=target) -> None:
                traits = getattr(target, "traits", None)
                if traits is None or not hasattr(traits, "mp"):
                    return
                current, maximum = stored_gauge_pair(target, "mp")
                if eff.magnitude_mode == "fixed":
                    base = int(eff.magnitude)
                elif eff.magnitude_mode == "fraction":
                    base = round(current * eff.magnitude)
                elif eff.magnitude_mode == "all":
                    base = max(0, maximum - current)
                else:
                    base = 0
                total_restore = max(0, base + bonus)
                if total_restore > 0:
                    from world.rules.mp_flow import apply_mp_change
                    apply_mp_change(target, total_restore, source_skill=skill_key, source_tier=skill_tier)

            traits = getattr(target, "traits", None)
            current, maximum = stored_gauge_pair(target, "mp") if traits is not None and hasattr(traits, "mp") else (0, 0)
            if eff.magnitude_mode == "fixed":
                preview_base = int(eff.magnitude)
            elif eff.magnitude_mode == "fraction":
                preview_base = round(current * eff.magnitude)
            elif eff.magnitude_mode == "all":
                preview_base = max(0, maximum - current)
            else:
                preview_base = 0

            pending.append(
                PendingEffect(
                    target,
                    f"gauge_transfer|{_entity_key(target)}|mp|restore|{preview_base + bonus}",
                    frozenset({"traits"}),
                    apply_target_restore,
                )
            )

    return pending


register_effect_handler(
    "gauge_transfer",
    _handle_gauge_transfer,
    frozenset({"traits"}),
    requires_event_context=frozenset(),
)
