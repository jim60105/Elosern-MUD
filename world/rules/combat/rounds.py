"""The bounded round loop: initiative-driven provisioning and upkeep.

``run_round`` resolves one action per capable combatant through the shared
resolver, folds in-round order operations, and settles end-of-round upkeep
inside the same outer transaction. ``run_battle`` drives the loop to a
terminal predicate or the round cap.
"""

from typing import Any

from world.rules.action import ActionRequest, ActionResolver, _stored_trait_value
from world.rules.buffs import TickRecord, tick_buffs, has_positional_marker
from world.rules.combat.battlefield import (
    COMBAT_YAML,
    ActionProvider,
    Battlefield,
    BattlefieldActionContext,
    BattleResult,
    _MAX_ACTIONS_PER_TURN,
    _stored_hp,
    is_battle_over,
    roll_initiative,
)
from world.rules.combat_modifiers import (
    evaluate_combat_modifiers,
    matched_combat_modifiers,
)
from world.rules.dice import roll_d100
from world.rules.event_log import EventEntry, EventLog
from world.rules.items import ItemUseRequest, resolve_item_use
from world.rules.progression import can_use_skill
from world.rules.sexual_state import climax_settlement_action, decay_tick
from world.rules.sexual_transitions import apply_event
from world.rules.upkeep import settle_upkeep
from world.skills.registry import SKILL_REGISTRY, SkillKind


def default_attack_policy(
    entity: Any,
    battlefield: Battlefield,
) -> ActionRequest | None:
    """Placeholder for Monster.behaviour_tree: attack the weakest enemy."""
    enemy_team = next(
        (
            members
            for team, members in battlefield.teams.items()
            if team != battlefield.team_of(entity.key)
        ),
        frozenset(),
    )
    candidates = [
        battlefield.roster[key]
        for key in enemy_team
        if key not in battlefield.fled
        and key in battlefield.roster
        and not battlefield.is_knocked_out(key)
        and _stored_hp(battlefield.roster[key]) > 0
    ]
    if not candidates:
        return None
    skill_key = next(
        (
            key
            for key in entity.skills.owned_keys()
            if key in SKILL_REGISTRY
            and SKILL_REGISTRY[key].kind is SkillKind.ACTIVE
            and can_use_skill(entity, SKILL_REGISTRY[key])
            and any(
                effect.startswith("damage:")
                for effect in SKILL_REGISTRY[key].effects
            )
            and all(
                _stored_trait_value(getattr(entity.traits, resource)) >= amount
                for resource, amount in SKILL_REGISTRY[key].cost.items()
            )
        ),
        None,
    )
    if skill_key is None:
        return None
    skill = SKILL_REGISTRY[skill_key]
    from world.rules.spell_conditions import is_strike_class

    if is_strike_class(skill):
        candidates = [c for c in candidates if not has_positional_marker(c)]
        if not candidates:
            return None
    target = min(
        candidates,
        key=lambda candidate: (_stored_hp(candidate), candidate.key),
    )
    return ActionRequest(
        actor=entity,
        skill_key=skill_key,
        targets=[target],
        context=BattlefieldActionContext(battlefield),
    )


def _action_skipped_event_log(
    entity: Any, data: dict[str, Any] | None = None
) -> EventLog:
    key = str(entity.key)
    entry = EventEntry(
        kind="action_skipped",
        actor=key,
        target=None,
        data=dict(data) if data is not None else {},
        text_template="{actor} 無法行動。",
    )
    return EventLog(key, "", (), (entry,), 0)


def _entity_round_order_op(entity: Any) -> str | None:
    """Return the active round_order action verb for entity, or None.

    Scans active buff instances in apply order; the last declared round_order
    marker instance wins.
    """
    from world.rules.buffs import BUFF_DEFINITIONS, _active_buff_instances

    last_op: str | None = None
    for buff in _active_buff_instances(entity):
        definition = BUFF_DEFINITIONS.get(buff.definition_key)
        if definition is None or not definition.round_order:
            continue
        last_op = definition.round_order.get("action")
    return last_op


def _fold_round_order(remaining: list[str], battlefield: Battlefield) -> list[str]:
    """Fold pending in-round order operations across the remaining not-yet-acted tail."""
    order = list(remaining)
    for key in list(order):
        if (
            key not in battlefield.roster
            or key in battlefield.fled
            or battlefield.is_knocked_out(key)
        ):
            continue
        entity = battlefield.roster[key]
        if _stored_hp(entity) <= 0:
            continue
        op = _entity_round_order_op(entity)
        if op == "advance_to_head":
            order = [key] + [k for k in order if k != key]
        elif op == "retreat_to_tail":
            order = [k for k in order if k != key] + [key]
    return order


def _end_of_round_upkeep(
    battlefield: Battlefield,
) -> dict[str, tuple[TickRecord, ...]]:
    """Run per-round upkeep and return the damaging tick records per entity.

    ``tick_buffs`` always returns a tuple; a patched non-tuple return (a
    test seam or an out-of-combat caller) is treated as no ticks so existing
    ``world.rules.combat.tick_buffs`` patches stay green.
    """
    seconds = int(COMBAT_YAML["round"]["seconds"])
    records_by_key: dict[str, tuple[TickRecord, ...]] = {}
    for key, entity in battlefield.roster.items():
        if key in battlefield.fled or _stored_hp(entity) <= 0:
            continue
        records = tick_buffs(entity, seconds)
        records_by_key[key] = records if isinstance(records, tuple) else ()
        decay_tick(entity, seconds)
        action = climax_settlement_action(entity)
        if action == "extend":
            apply_event(entity, "climax_extended")
        elif action == "end":
            apply_event(entity, "climax_ends")
    return records_by_key


def run_round(
    battlefield: Battlefield,
    action_provider: ActionProvider,
    *,
    simulated: bool = False,
    nonlethal_keys: frozenset[str] = frozenset(),
    journal_sink: "list[object] | None" = None,
    notifications_sink: "list[str] | None" = None,
    first_actor: str | None = None,
) -> list[EventLog]:
    """Resolve one action per capable combatant, then perform upkeep.

    The keyword-only ``first_actor`` is a reorder-only initiative override
    (combat-opening-seams D-1): ``roll_initiative()`` still computes the
    sequence exactly as today, and the named key is then moved to the head of
    that returned sequence with every other key's relative order unchanged.
    It never re-rolls, re-scores, or bypasses ``roll_initiative()``, never
    grants the named combatant an additional action, and never skips another
    combatant. A key absent from the rolled sequence — dead, fled, knocked
    out, or not in the roster — is a silent no-op. ``None`` (every existing
    call site) leaves the iteration byte-identical to the pre-parameter
    behaviour.

    The round's upkeep settlement (fix-dot-kill-credit D3) turns the damaging
    tick records into defeat crossings, kill XP, and quest effects inside the
    same round; the keyword-only policy flags mirror the session's
    ``simulated`` (guild examination) and companion ``nonlethal_keys``
    policies, and default to the plain combat behavior. The provider supplies
    the closed deterministic request union: ``ItemUseRequest`` members settle
    through ``resolve_item_use`` (whose item journal is appended to
    ``journal_sink`` when provided, so an outer rollback can restore the
    actually-deleted mirrors), and every other request resolves as an
    ``ActionRequest``.

    ``notifications_sink`` collects player-facing notification lines staged
    by committed effects (e.g. title grant toasts) for delivery by the outer
    settlement boundary after its commit; ``run_round`` itself never sends.

    The entire round resolution stays within one outer database transaction
    (the session's existing boundary); multiple action slots provisioned for a
    single combatant execute sequentially inside that same transaction.
    """
    logs: list[EventLog] = []
    order = roll_initiative(battlefield)
    if first_actor is not None and first_actor in order:
        order = [first_actor] + [key for key in order if key != first_actor]
    remaining = list(order)
    while remaining:
        remaining = _fold_round_order(remaining, battlefield)
        key = remaining.pop(0)
        if key not in battlefield.roster:
            continue
        entity = battlefield.roster[key]
        if (
            key in battlefield.fled
            or battlefield.is_knocked_out(key)
            or _stored_hp(entity) <= 0
        ):
            continue
        modifiers = evaluate_combat_modifiers(entity)
        if "actions_per_turn" in modifiers:
            matched = matched_combat_modifiers(entity)
            zero_rules = [adj for _, adj in matched if adj.get("actions_per_turn") == 0]

            if zero_rules or modifiers.get("actions_per_turn") == 0:
                certain = any("chance" not in adj for adj in zero_rules) if zero_rules else True
                if certain:
                    logs.append(_action_skipped_event_log(entity))
                    continue
                max_chance = max(int(adj["chance"]) for adj in zero_rules)
                roll = roll_d100()
                if roll <= max_chance:
                    logs.append(
                        _action_skipped_event_log(
                            entity, data={"chance": max_chance, "roll": roll}
                        )
                    )
                    continue
                count = max(1, int(modifiers.get("actions_per_turn", 1)))
            else:
                raw_count = modifiers.get("actions_per_turn", 1)
                if raw_count == 0:
                    logs.append(_action_skipped_event_log(entity))
                    continue
                count = max(1, int(raw_count))
        else:
            count = 1

        count = min(count, _MAX_ACTIONS_PER_TURN)

        for _ in range(count):
            if (
                key in battlefield.fled
                or battlefield.is_knocked_out(key)
                or _stored_hp(entity) <= 0
            ):
                break
            request = action_provider(entity, battlefield)
            if request is None:
                continue
            if isinstance(request, ItemUseRequest):
                # The battlefield doubles as the action context (design D2):
                # every scope — self, single, and group — resolves against the
                # same roster presence/relation/range validators a skill's
                # targets pass. The resulting multi-entity journal rides the
                # existing sink, whose restore() walks every captured entity
                # (design D3), so the outer rollback contract already covers
                # companion traits, buffs, and sexual state.
                item_result = resolve_item_use(
                    request,
                    in_combat=True,
                    context=BattlefieldActionContext(battlefield),
                )
                if item_result.outcome == "success":
                    if item_result.journal is not None and journal_sink is not None:
                        journal_sink.append(item_result.journal)
                    if item_result.event_log is not None:
                        logs.append(item_result.event_log)
                continue
            result = ActionResolver.resolve(request)
            if result.outcome == "success" and result.event_log is not None:
                logs.append(result.event_log)
            # The action provider is a duck-typed seam: a result without the
            # notification field (an injected double, or a pre-notification
            # provider) simply stages nothing.
            notifications = getattr(result, "notifications", ())
            if notifications and notifications_sink is not None:
                notifications_sink.extend(notifications)
    records_by_key = _end_of_round_upkeep(battlefield)
    logs.extend(
        settle_upkeep(
            battlefield,
            records_by_key,
            simulated=simulated,
            nonlethal_keys=nonlethal_keys,
        )
    )
    return logs


def is_battle_over(battlefield: Battlefield) -> bool:
    """Return whether either team has no living, non-fled combatants."""
    return any(
        not any(
            key not in battlefield.fled
            and key in battlefield.roster
            and not battlefield.is_knocked_out(key)
            and _stored_hp(battlefield.roster[key]) > 0
            for key in members
        )
        for members in battlefield.teams.values()
    )


def run_battle(
    battlefield: Battlefield,
    action_provider: ActionProvider = default_attack_policy,
    max_rounds: int = 100,
) -> BattleResult:
    """Run a bounded encounter and report, but do not settle, elapsed time."""
    if max_rounds < 0:
        raise ValueError("max_rounds must be non-negative")
    logs: list[EventLog] = []
    rounds = 0
    while rounds < max_rounds and not is_battle_over(battlefield):
        logs.extend(run_round(battlefield, action_provider))
        rounds += 1
    return BattleResult(
        event_logs=tuple(logs),
        rounds_elapsed=rounds,
        total_seconds=rounds * int(COMBAT_YAML["round"]["seconds"]),
        completed=is_battle_over(battlefield),
    )


# Combat is the production composition root for combat-owned effect handlers.
from world.rules import disengage as _disengage  # noqa: E402,F401