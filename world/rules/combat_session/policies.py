"""Deterministic action providers for one persistent session's rounds.

Supplies the queued player request and the deterministic enemy/basic-attack
policies consumed by ``run_round()`` and ``resolve_overwhelm()``, each built
with the session's combat context.
"""

from typing import Any

from world.rules import combat
from world.rules.action import ActionRequest, _stored_trait_value
from world.rules.combat import Battlefield
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.combat_session.battlefield import _context_for

BASIC_ATTACK_KEY = "basic_attack"


def _basic_attack_request(
    entity: Any,
    battlefield: Battlefield,
    record: CombatSessionRecord,
) -> ActionRequest | None:
    """Return a deterministic ``basic_attack`` against the lowest-HP living enemy."""
    from world.rules.buffs import has_positional_marker

    enemy_keys = next(
        (
            members
            for team, members in battlefield.teams.items()
            if team != battlefield.team_of(str(entity.key))
        ),
        frozenset(),
    )
    candidates = [
        battlefield.roster[key]
        for key in enemy_keys
        if key in battlefield.roster
        and key not in battlefield.fled
        and not battlefield.is_knocked_out(key)
        and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
        and not has_positional_marker(battlefield.roster[key])
    ]
    if not candidates:
        return None
    target = min(
        candidates,
        key=lambda enemy: (_stored_trait_value(enemy.traits.hp), str(enemy.key)),
    )
    context = _context_for(battlefield, record)
    return ActionRequest(entity, BASIC_ATTACK_KEY, [target], context)


def _enemy_policy(
    entity: Any,
    battlefield: Battlefield,
    record: CombatSessionRecord,
):
    """Return one deterministic enemy action with the session's combat context.

    ``monster_behaviour_policy`` falls back to ``default_attack_policy`` for
    non-Monster combatants, so a guild-examination NPC opponent (which has no
    ``threat_tier``) still acts through its profile skills. The request context
    is rebuilt from the session record, so examination opponents fight with
    ordinary lethal semantics inside the simulated battle.
    """
    request = monster_behaviour_policy(entity, battlefield)
    if request is None:
        return None
    return ActionRequest(
        actor=request.actor,
        skill_key=request.skill_key,
        targets=list(request.targets),
        context=_context_for(battlefield, record),
    )


def _round_provider(actor: Any, request: "combat.RoundRequest", battlefield: Battlefield, record: CombatSessionRecord):
    """Supply the queued player request exactly once and deterministic enemy policies."""
    used = False

    def provider(entity, field):
        nonlocal used
        if entity.key == actor.key:
            if used:
                return None
            used = True
            return request
        return _enemy_policy(entity, field, record)

    return provider


def _overwhelm_provider(actor: Any, first_request: "combat.RoundRequest", battlefield: Battlefield, record: CombatSessionRecord):
    """Supply the selected request once, then deterministic basic attacks."""
    used = False

    def provider(entity, field):
        nonlocal used
        if entity.key == actor.key:
            if not used:
                used = True
                return first_request
            return _basic_attack_request(entity, field, record)
        return _enemy_policy(entity, field, record)

    return provider
