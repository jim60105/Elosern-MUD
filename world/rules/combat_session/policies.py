"""Deterministic action providers for one persistent session's rounds.

Supplies the queued player request and the deterministic enemy/basic-attack
policies consumed by ``run_round()`` and ``resolve_overwhelm()``, each built
with the session's combat context.
"""

from typing import Any

from world.rules import combat
from world.rules.action import ActionRequest, _stored_trait_value
from world.rules.combat import Battlefield
from world.rules.combat_session.ai_tuning import record_session_ai_tuning
from world.rules.combat_session.battlefield import _context_for
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.monster_behaviour import monster_behaviour_policy

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
    *,
    scale: float = 1.0,
):
    """Return one deterministic enemy action with the session's combat context.

    ``monster_behaviour_policy`` falls back to ``default_attack_policy`` for
    non-Monster combatants, so a guild-examination NPC opponent (which has no
    ``threat_tier``) still acts through its profile skills. The settlement
    context is built from the session record BEFORE selection and handed to
    the decision, so examination opponents fight with ordinary lethal
    semantics inside the simulated battle and an overwhelm round keeps the
    companion non-lethal policy while it is being decided.

    The decision boundary is also where one monster's immutable, startup-
    validated AI tuning is recorded for its session (nothing durable, nothing
    per-entity): the recording is what a terminal cleanup or a restarted
    process later replaces. The recorded resolution is what the decision
    scores against, so the selection seed's configuration fingerprint is the
    tuning this session actually recorded.

    The decision's own request is returned unchanged: its ``targets`` keep the
    authored representation (a recognized AREA shorthand stays a string) and
    its ``scale`` is preserved, because the supplied context already is the
    session's settlement context. ``scale`` is the authored cast magnitude the
    decision is authorized to plan with; production passes the plain magnitude
    (``1.0``) until a monster casts scaled.
    """
    decision = record_session_ai_tuning(record.session_id, entity)
    return monster_behaviour_policy(
        entity,
        battlefield,
        context=_context_for(battlefield, record),
        scale=scale,
        decision=decision,
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


def _party_round_provider(
    requests_by_actor_id: dict[int, "combat.RoundRequest"],
    battlefield: Battlefield,
    record: CombatSessionRecord,
):
    """Supply each eligible allied actor's selected request exactly once and deterministic enemy policies.

    Interactive allied action slots are capped at 1 selected command slot per round;
    subsequent requests for the same allied actor return None.
    """
    used_allies: set[int] = set()

    def provider(entity, field):
        pk = getattr(entity, "pk", None)
        if pk is not None:
            try:
                pk_int = int(pk)
            except (TypeError, ValueError):
                pk_int = None
        else:
            pk_int = None

        if pk_int is not None and pk_int in record.player_ids:
            # Interactive ally
            if pk_int in used_allies:
                return None
            used_allies.add(pk_int)
            return requests_by_actor_id.get(pk_int)

        # Enemy combatant
        return _enemy_policy(entity, field, record)

    def is_interactive_ally(entity) -> bool:
        pk = getattr(entity, "pk", None)
        if pk is None:
            return False
        return int(pk) in record.player_ids

    provider.is_interactive_ally = is_interactive_ally
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
