"""Battlefield reconstruction and the session's combat policy.

Resolves one session's persisted dbrefs into a live ``Battlefield`` for one
action, and derives the ``(simulated, nonlethal_keys)`` policy every round
entry point shares (fix-dot-kill-credit D4, party-combat D-3).
"""

from typing import Any

from evennia.objects.models import ObjectDB

from world.rules.action import _stored_trait_value
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.buffs import active_buff_keys_from_storage, BLOCKING_BUFF_KEYS
from world.rules.combat_modifiers import evaluate_combat_modifiers_no_create
from world.rules.party import bound_owner_of, is_companion
from world.rules.combat_session.records import CombatSessionRecord


def reconstruct_battlefield(actor: Any, record: CombatSessionRecord) -> Battlefield:
    """Resolve a session's dbrefs into a live battlefield for one action."""
    room = ObjectDB.objects.filter(id=record.room_id).first()
    if room is None:
        raise CombatSessionError(SessionReason.ROOM_MISSING)
    if actor.location is not room:
        raise CombatSessionError(SessionReason.MOVED)
    player_ids = list(record.player_ids)
    if actor.pk not in player_ids:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    player_id = actor.pk

    def resolve(dbref):
        return ObjectDB.objects.filter(id=dbref).first()

    entities = {}
    key_by_pk = {}
    for dbref in player_ids:
        entity = resolve(dbref)
        if entity is None:
            raise CombatSessionError(
                SessionReason.MISSING_PARTICIPANT, f"player dbref {dbref} missing"
            )
        if str(entity.key) in entities:
            raise CombatSessionError(
                SessionReason.DUPLICATE_PARTICIPANT,
                f"participant key {entity.key!r} is not unique",
            )
        entities[entity.key] = entity
        key_by_pk[dbref] = entity.key
    for dbref in record.enemy_ids:
        entity = resolve(dbref)
        if entity is None:
            raise CombatSessionError(
                SessionReason.MISSING_PARTICIPANT, f"enemy dbref {dbref} missing"
            )
        if str(entity.key) in entities:
            raise CombatSessionError(
                SessionReason.DUPLICATE_PARTICIPANT,
                f"participant key {entity.key!r} is not unique",
            )
        entities[entity.key] = entity
        key_by_pk[dbref] = entity.key

    player_entity = resolve(player_id)
    if player_entity is None or _stored_trait_value(player_entity.traits.hp) <= 0:
        raise CombatSessionError(SessionReason.INVALID_RECOVERY)
    teams = {
        "party": frozenset(key_by_pk[dbref] for dbref in player_ids),
        "foes": frozenset(key_by_pk[dbref] for dbref in record.enemy_ids),
    }
    battlefield = Battlefield(teams, entities)
    battlefield.fled = {
        key_by_pk[dbref]
        for dbref in record.fled_ids
        if dbref in key_by_pk
    }
    battlefield.knocked_out = {
        key_by_pk[dbref]
        for dbref in record.knocked_out_ids
        if dbref in key_by_pk
    }
    return battlefield


def is_actor_eligible_to_act(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
) -> bool:
    """Return whether ``actor`` is currently controllable and able to act.

    An eligible actor must be:
    - Present in the session's allied roster (``player_ids``).
    - In the session room and matching the battlefield roster.
    - Not fled (neither in ``record.fled_ids`` nor ``battlefield.fled``).
    - Not knocked out (neither in ``record.knocked_out_ids`` nor ``battlefield.knocked_out``).
    - Alive (stored HP > 0).
    - Not blocked by a blocking buff.
    - Not action-forbidden (``actions_per_turn`` > 0).
    """
    actor_pk = getattr(actor, "pk", None)
    if actor_pk is None or actor_pk not in record.player_ids:
        return False
    actor_key = str(getattr(actor, "key", ""))
    if actor_key not in battlefield.roster:
        return False
    if actor_pk in record.fled_ids or actor_key in battlefield.fled:
        return False
    if actor_pk in record.knocked_out_ids or actor_key in battlefield.knocked_out:
        return False
    if _stored_trait_value(getattr(actor.traits, "hp", None)) <= 0:
        return False
    # Ability-to-act check
    blocked = bool(active_buff_keys_from_storage(actor) & BLOCKING_BUFF_KEYS)
    if blocked:
        return False
    modifiers = evaluate_combat_modifiers_no_create(actor)
    if modifiers.get("actions_per_turn", 1) == 0:
        return False
    return True


def get_required_combat_actors(
    record: CombatSessionRecord,
    battlefield: Battlefield,
) -> tuple[int, ...]:
    """Return the actor dbrefs currently ELIGIBLE to submit round commands.

    Evaluates all participants in ``record.player_ids`` in deterministic sorted order
    and checks whether each is currently eligible to act via ``is_actor_eligible_to_act``.
    This is the eligibility half only: it is a ``commander``-free predicate, so it
    cannot see whether the commander may actually command a participant (party
    binding and co-location live in ``authorize_combat_actor``). Draft completeness
    needs both halves; use ``_commandable_required_actors`` for that, or an actor
    nobody may command becomes a hole no submission can fill.
    """
    required: list[int] = []
    for pk in sorted(record.player_ids):
        entity = next((e for e in battlefield.roster.values() if getattr(e, "pk", None) == pk), None)
        if entity is not None and is_actor_eligible_to_act(entity, record, battlefield):
            required.append(pk)
    return tuple(required)


def authorize_combat_actor(
    commander: Any,
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
) -> Any:
    """Authorize ``actor`` under authenticated ``commander`` for a combat command.

    Returns the authorized live entity or raises ``CombatSessionError(SessionReason.FORBIDDEN_ACTOR)``.
    derive authorization from:
    1. Commander's active session: ``commander.pk`` must be in ``record.player_ids``.
    2. If ``actor is commander`` (or ``actor.pk == commander.pk``): commander must be eligible to act.
    3. If ``actor`` is a companion:
       - Must be in ``record.player_ids``.
       - Must be bound to ``commander`` (``is_companion(actor, commander)`` or ``bound_owner_of(actor) is commander``).
       - Must be co-located with commander.
       - Must be eligible to act (not fled, not knocked out, HP > 0, ability to act).
    4. Otherwise, rejects with ``FORBIDDEN_ACTOR``.
    """
    if commander.pk not in record.player_ids:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    if getattr(actor, "pk", None) not in record.player_ids:
        raise CombatSessionError(SessionReason.FORBIDDEN_ACTOR)
    is_self = actor is commander or actor.pk == commander.pk
    if not is_self:
        # Bound party membership validation
        owner = bound_owner_of(actor)
        if not (is_companion(actor, commander) or (owner is not None and owner.pk == commander.pk)):
            raise CombatSessionError(SessionReason.FORBIDDEN_ACTOR)
        if actor.location is not commander.location:
            raise CombatSessionError(SessionReason.FORBIDDEN_ACTOR)
        if not is_actor_eligible_to_act(actor, record, battlefield):
            raise CombatSessionError(SessionReason.FORBIDDEN_ACTOR)
    return actor


def _commandable_required_actors(
    commander: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
) -> tuple[int, ...]:
    """Return the required actors ``commander`` may currently command.

    The authoritative required set for draft completeness: participants the
    commander cannot command are excluded, so a companion that left the party,
    moved away or was dismissed never becomes a hole no submission can fill.
    Only ``FORBIDDEN_ACTOR`` is filtered: every other authorization reason
    (``UNKNOWN_SESSION_ID`` and the ``CombatSessionError``s raised inside
    eligibility) reports a broken session invariant and propagates.

    ``get_required_combat_actors`` already only reports pks whose roster
    entity it resolved, so the entity here is always the live participant.
    """
    commandable: list[int] = []
    for pk in get_required_combat_actors(record, battlefield):
        entity = next((e for e in battlefield.roster.values() if getattr(e, "pk", None) == pk), None)
        try:
            authorize_combat_actor(commander, entity, record, battlefield)
        except CombatSessionError as error:
            if error.args[0] is not SessionReason.FORBIDDEN_ACTOR:
                raise
            continue
        commandable.append(pk)
    return tuple(commandable)


def _session_policy(
    battlefield: Battlefield,
    record: CombatSessionRecord,
) -> tuple[bool, frozenset[str]]:
    """Return the session's ``(simulated, nonlethal_keys)`` combat policy.

    Guild examinations run as simulated combat (no companion protection);
    hostile sessions with companions carry the per-entity ``nonlethal_keys``
    set naming the allied companions (party-combat D-3). ``_context_for``
    and the round/overwhelm entry points derive the same policy from this
    one helper (fix-dot-kill-credit D4).
    """
    if record.mode == "guild_exam":
        return True, frozenset()
    if len(record.player_ids) > 1:
        companion_pks = set(record.player_ids[1:])
        return False, frozenset(
            key
            for key, entity in battlefield.roster.items()
            if int(entity.pk) in companion_pks
        )
    return False, frozenset()


def _context_for(battlefield: Battlefield, record: CombatSessionRecord) -> BattlefieldActionContext:
    """Build the session's action context with its damage and reward policy.

    Hostile sessions carry ``nonlethal_keys`` naming the allied companions, so
    damage floors companions at 1 HP and marks them knocked out per target
    while monsters stay lethal (party-combat D-3). Guild examinations run as
    ordinary lethal combat with a ``simulated`` marker instead of a nonlethal
    policy: defeats are real HP crossings, but kill-credit consumers treat
    them as simulation outcomes (exam-simulated-battle-redesign D1/D4).
    """
    simulated, nonlethal_keys = _session_policy(battlefield, record)
    event_context: dict[str, Any] = {"battlefield": battlefield}
    if simulated:
        event_context["simulated"] = True
    elif nonlethal_keys:
        event_context["nonlethal_keys"] = nonlethal_keys
    return BattlefieldActionContext(battlefield, event_context=event_context)
