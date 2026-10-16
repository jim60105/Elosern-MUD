"""The bounded round loop: initiative-driven provisioning and upkeep.

``run_round`` resolves one action per capable combatant through the shared
resolver, folds in-round order operations, and settles end-of-round upkeep
inside the same outer transaction. ``run_battle`` drives the loop to a
terminal predicate or the round cap.
"""

from collections.abc import Mapping
from typing import Any

from world.rules.action import ActionRequest, ActionResolver, _stored_trait_value
from world.rules.buffs import TickRecord, tick_buffs, has_positional_marker
from world.rules.combat.battlefield import (
    COMBAT_YAML,
    ActionProvider,
    Battlefield,
    BattlefieldActionContext,
    BattleResult,
    RoundTactical,
    _MAX_ACTIONS_PER_TURN,
    _stored_hp,
    is_battle_over,
    roll_initiative,
)
from world.rules.combat.decision_scope import (
    ExecutionScopeBase,
    decision_scope,
    decision_scope_for,
    stable_actor_id,
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
    # An active Taunt winner (party-combat-taunt-constraints) is the enemy's
    # forced target when it is ordinarily legal for this damage strike: the
    # winner mapping is one of the ordinary candidates already, so a winner a
    # mandatory restriction excluded (fled, knocked out, or stripped as a
    # displaced target) grants no exception and changes nothing. This
    # delegated policy is the non-``Monster`` enemy path; Monsters route
    # through ``monster_behaviour_policy``, which applies the same constraint
    # in its legacy and utility bodies.
    winner = battlefield.taunt_winner(str(entity.key))
    if winner is not None and any(candidate is winner for candidate in candidates):
        candidates = [winner]
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
    decision_scope_base: ExecutionScopeBase | None = None,
    tactical_declarations: Mapping[str, str] | None = None,
    taunt_declarations: Mapping[str, str] | None = None,
) -> list[EventLog]:
    """Resolve one round inside its round-start tactical scope.

    The keyword-only ``tactical_declarations`` (party-combat-defend-dodge) is
    the round's accepted allied Defend/Dodge declarations, keyed by roster key
    (``"defend"`` or ``"dodge"``). ``run_round`` is the sole writer of the
    round execution context: it computes the round's initiative sequence once,
    resolves the ``taunt_declarations`` winners against it, activates the
    declarations and winners on ``battlefield.tactical`` before
    :func:`_resolve_round` runs any action, and clears the context in a
    ``finally`` so no activated effect leaks past the round (or survives a
    technically failed round) and none stacks across rounds. The context is
    transient in-battle state, never a durable buff. An omitted or empty
    declaration mapping leaves that part of the context unset, so callers
    without declarations are byte-identical to the pre-parameter behaviour.

    The keyword-only ``taunt_declarations`` (party-combat-taunt-constraints) is
    the round's accepted allied Taunt declarations, keyed by the taunter's
    roster key with the taunted enemy's roster key as the value. The winner per
    enemy is the first such taunter in the round's own initiative sequence
    (:func:`_resolve_taunt_winners`); Taunt costs no resource, rolls no dice and
    consumes the taunter's selected action (the session provider returns no
    request for it). The winner mapping rides ``RoundTactical.taunt_winners``
    and expires with the rest of the context at round end.

    The initiative sequence is rolled exactly once here -- Taunt winner ranking
    adds no draw -- and handed to :func:`_resolve_round`, so the reordering and
    the execution order it drives cannot disagree with the sequence Taunt was
    ranked against.

    Every other contract (the closed request union, the shared resolver, upkeep
    settlement, the decision scope, and the outer transaction boundary) lives
    on :func:`_resolve_round`, the body this scope wraps.
    """
    order = _initiative_order(battlefield, first_actor)
    declarations = dict(tactical_declarations or {})
    taunt_winners = _resolve_taunt_winners(taunt_declarations, order, battlefield)
    battlefield.tactical = (
        RoundTactical(declarations, taunt_winners)
        if declarations or taunt_winners
        else None
    )
    try:
        return _resolve_round(
            battlefield,
            action_provider,
            simulated=simulated,
            nonlethal_keys=nonlethal_keys,
            journal_sink=journal_sink,
            notifications_sink=notifications_sink,
            decision_scope_base=decision_scope_base,
            initiative=order,
        )
    finally:
        battlefield.tactical = None


def _initiative_order(battlefield: Battlefield, first_actor: str | None) -> list[str]:
    """Return the round's one initiative sequence, with the opening reorder.

    The keyword-only ``first_actor`` is the round's reorder-only initiative
    override (combat-opening-seams D-1): ``roll_initiative()`` still computes
    the sequence exactly as before, and the named key is then moved to the head
    of that returned sequence with every other key's relative order unchanged.
    It never re-rolls, re-scores, or bypasses ``roll_initiative()``, never
    grants the named combatant an additional action, and never skips another
    combatant. A key absent from the rolled sequence is a silent no-op.

    ``run_round`` is the only caller, so this is the round's single dice draw
    for initiative and the one sequence both Taunt winner ranking and
    :func:`_resolve_round`'s turn order read.
    """
    order = roll_initiative(battlefield)
    if first_actor is not None and first_actor in order:
        order = [first_actor] + [key for key in order if key != first_actor]
    return order


def _resolve_taunt_winners(
    taunt_declarations: "Mapping[str, str] | None",
    order: "list[str]",
    battlefield: Battlefield,
) -> dict[str, str]:
    """Return one winning taunter's roster key per taunted enemy.

    ``taunt_declarations`` maps each declaring taunter's roster key to the
    taunted enemy's roster key. The winner of one enemy is the taunter that
    appears first in the round's already-computed initiative ``order`` -- the
    sequence returned by :func:`_initiative_order`, before any per-slot
    ``round_order`` fold -- so declaration entry order and confirmation order
    have no influence and no extra dice are drawn. Exactly one winner is kept
    per enemy, so no runner-up is ever promoted.

    A taunter absent from ``order`` (already unable to act) or absent from the
    roster is not a winner, and an unknown enemy is ignored: the enemy is then
    simply unrestricted.
    """
    if not taunt_declarations:
        return {}
    rank = {key: index for index, key in enumerate(order)}
    winners: dict[str, str] = {}
    for taunter_key, enemy_key in taunt_declarations.items():
        if enemy_key not in battlefield.roster or taunter_key not in rank:
            continue
        current = winners.get(enemy_key)
        if current is None or rank[taunter_key] < rank[current]:
            winners[enemy_key] = taunter_key
    return winners


def _resolve_round(
    battlefield: Battlefield,
    action_provider: ActionProvider,
    *,
    simulated: bool = False,
    nonlethal_keys: frozenset[str] = frozenset(),
    journal_sink: "list[object] | None" = None,
    notifications_sink: "list[str] | None" = None,
    decision_scope_base: ExecutionScopeBase | None = None,
    initiative: "list[str] | None" = None,
) -> list[EventLog]:
    """Resolve one action per capable combatant, then perform upkeep.

    The keyword-only ``initiative`` is the round's own pre-computed initiative
    sequence (:func:`_initiative_order`), supplied by ``run_round`` so the
    sequence Taunt winner ranking used and the sequence this body iterates are
    the same list. When omitted, this body rolls its own via ``roll_initiative``
    exactly as before, so a direct caller keeps the pre-parameter behaviour.
    The sequence is never re-sorted or re-rolled here.

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

    ``decision_scope_base`` (monster-ai-attack-selection) is the encounter
    identity this round's decisions are numbered from: the persistent
    session's id, the actual round number and the resolved context mode. Each
    provider call runs inside its own
    :class:`~world.rules.combat.decision_scope.ExecutionScope`, adding the
    acting combatant's stable identity and the zero-based index of the action
    slot being provisioned — so two slots of one actor, and the same slot of
    two rounds, are distinct decisions. The provider is still called with
    exactly two arguments, and the scope is restored on normal return and on
    any exception. An omitted base uses the canonical empty encounter
    identity: this call is one round whose numbering its caller owns.

    The entire round resolution stays within one outer database transaction
    (the session's existing boundary); multiple action slots provisioned for a
    single combatant execute sequentially inside that same transaction.
    """
    logs: list[EventLog] = []
    session_id = "" if decision_scope_base is None else decision_scope_base.session_id
    round_index = 0 if decision_scope_base is None else decision_scope_base.round_index
    observe = None
    if session_id:
        # Local import: the session-owned observation memory lives in
        # ``world.rules.combat_session``, which already depends on this
        # package, so the dependency may only be resolved at call time.
        from world.rules.combat_session.observations import observe_action

        def observe(event_log: EventLog) -> None:
            observe_action(
                session_id,
                round_index,
                event_log,
                roster=battlefield.roster,
                battlefield=battlefield,
            )

    remaining = list(roll_initiative(battlefield) if initiative is None else initiative)
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

        is_interactive_ally_fn = getattr(action_provider, "is_interactive_ally", None)
        if is_interactive_ally_fn is not None and is_interactive_ally_fn(entity):
            count = min(count, 1)

        count = min(count, _MAX_ACTIONS_PER_TURN)

        for slot_index in range(count):
            if (
                key in battlefield.fled
                or battlefield.is_knocked_out(key)
                or _stored_hp(entity) <= 0
            ):
                break
            with decision_scope(
                decision_scope_for(
                    decision_scope_base,
                    actor_id=stable_actor_id(entity),
                    slot_index=slot_index,
                )
            ):
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
                        if observe is not None:
                            observe(item_result.event_log)
                continue
            result = ActionResolver.resolve(request)
            if result.outcome == "rejected":
                # Distinguish technical failure (CommitFailed) from gameplay invalidation
                from world.rules.action import RejectReason
                if result.reason in {
                    RejectReason.COMMIT_FAILED,
                    RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE,
                    RejectReason.EVENT_LOG_CONSTRUCTION_FAILED,
                }:
                    raise RuntimeError(f"technical failure during round execution: {result.reason} ({result.detail})")
                continue
            if result.outcome == "success" and result.event_log is not None:
                logs.append(result.event_log)
                if observe is not None:
                    observe(result.event_log)
            # The action provider is a duck-typed seam: a result without the
            # notification field (an injected double, or a pre-notification
            # provider) simply stages nothing.
            notifications = getattr(result, "notifications", ())
            if notifications and notifications_sink is not None:
                notifications_sink.extend(notifications)
    records_by_key = _end_of_round_upkeep(battlefield)
    upkeep_logs = settle_upkeep(
        battlefield,
        records_by_key,
        simulated=simulated,
        nonlethal_keys=nonlethal_keys,
    )
    if observe is not None:
        for log in upkeep_logs:
            observe(log)
    logs.extend(upkeep_logs)
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
    """Run a bounded encounter and report, but do not settle, elapsed time.

    The encounter has no persistent session, so every round carries the
    canonical empty session id and its own real round number: a decision made
    in round two is never the same decision as round one. This numbering is
    zero-based while the persistent session path numbers from its durable
    ``rounds_elapsed + 1``; the two conventions coexist deliberately and can
    never collide, because the empty session id is a different encounter
    namespace from a durable one (``combat_session.rounds._submit_request``).
    """
    if max_rounds < 0:
        raise ValueError("max_rounds must be non-negative")
    logs: list[EventLog] = []
    rounds = 0
    while rounds < max_rounds and not is_battle_over(battlefield):
        logs.extend(
            run_round(
                battlefield,
                action_provider,
                decision_scope_base=ExecutionScopeBase(round_index=rounds),
            )
        )
        rounds += 1
    return BattleResult(
        event_logs=tuple(logs),
        rounds_elapsed=rounds,
        total_seconds=rounds * int(COMBAT_YAML["round"]["seconds"]),
        completed=is_battle_over(battlefield),
    )


# Combat is the production composition root for combat-owned effect handlers.
from world.rules import disengage as _disengage  # noqa: E402,F401