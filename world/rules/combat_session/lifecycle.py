"""Session lifecycle: engagement, persistence, and clearing.

``engage``/``engage_group`` create one persistent hostile session and wait for
player input; ``_persist`` writes the record; ``clear_session`` retires the
session, its skip-safety registration, and its ground/positional markers.
"""

from typing import Any

from evennia.objects.models import ObjectDB

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.observability import log_info
from world.rules.action import _stored_trait_value
from world.rules.combat import Battlefield
from world.rules.combat_session.battlefield import reconstruct_battlefield
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.records import (
    CombatSessionRecord,
    read_session,
    session_id_for,
    to_storage,
)
from world.rules.overwhelm import classify_overwhelm
from world.rules.skip_safety import (
    register_active_battlefield,
    unregister_active_battlefield,
)


def _persist(actor: Any, record: CombatSessionRecord) -> None:
    actor.db.active_combat = to_storage(record)


def clear_session(
    actor: Any,
    battlefield: Battlefield | None = None,
    record: CombatSessionRecord | None = None,
) -> None:
    """Clear session/context state and skip-safety registration.

    Every persisted participant is unregistered (party-combat D-5): when the
    battlefield cannot be reconstructed, the record's participant dbrefs still
    release surviving companions and monsters from skip safety, and the
    participant scan purges even a deleted participant's stale key, so no
    registration of the session survives settlement.
    """
    from world.rules.skip_safety import unregister_participants

    actor.db.active_combat = None
    actor.ndb.action_context = None
    unregister_active_battlefield(actor)
    if battlefield is not None:
        for key in list(battlefield.roster):
            unregister_active_battlefield(battlefield.roster[key])
    if record is not None:
        unregister_participants((*record.player_ids, *record.enemy_ids))

    from django.db import transaction
    from world.rules.buffs import remove_ground_markers, remove_positional_markers

    participants: set[Any] = set()
    if battlefield is not None:
        participants.update(battlefield.roster.values())
    if record is not None:
        for dbref in (*record.player_ids, *record.enemy_ids):
            obj = ObjectDB.objects.filter(id=dbref).first()
            if obj is not None:
                participants.add(obj)
    participants.add(actor)
    for entity in participants:
        removed = remove_ground_markers(entity) + remove_positional_markers(entity)
        if removed:
            boundary = {
                "char": str(entity.pk),
                "count": removed,
                "reason": "session_end",
            }
            transaction.on_commit(
                lambda b=boundary: log_info("combat_marker_swept", context=b)
            )


def engage(actor: Any, target: Any) -> dict[str, Any]:
    """Create one persistent hostile session for a present living monster.

    Thin single-target wrapper (combat-session-opening-dispatch D-4): every
    step lives in :func:`engage_group`, so ``engage``'s signature, return
    shape, and raised ``CombatSessionError`` reasons are unchanged for its
    existing call sites.
    """
    return engage_group(actor, [target])


def engage_group(actor: Any, targets: Any) -> dict[str, Any]:
    """Create one persistent hostile session against several present monsters.

    Carries every step single-target engagement performed before this change
    (combat-session-opening-dispatch D-4): the PlayerCharacter check, the
    no-active-session check, the per-target living-hostile-``Monster``-in-room
    checks in their established order and reasons, ``combat_companions()``
    collection, record construction with one dbref per supplied target in
    deterministic (sorted-pk) order, battlefield reconstruction, persistence,
    skip-safety registration, and dialogue clearing. Any single invalid
    target rejects the whole group before anything is persisted or
    registered, and a repeated target dbref is rejected as
    ``DUPLICATE_PARTICIPANT``. The informational ``classify_overwhelm``
    verdict is computed once over the complete multi-enemy roster and is
    never consulted for dispatch here (single-shot-resolution): engagement
    runs no action before the player chooses one.
    """
    if not isinstance(actor, PlayerCharacter):
        raise CombatSessionError(SessionReason.NOT_A_PLAYER)
    if read_session(actor) is not None:
        raise CombatSessionError(SessionReason.ALREADY_IN_COMBAT)
    if isinstance(targets, (str, bytes)) or not hasattr(targets, "__iter__"):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "engage_group requires a sequence of targets",
        )
    targets = list(targets)
    if not targets:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "engage_group requires at least one target",
        )
    seen_pks: set[Any] = set()
    for target in targets:
        pk = getattr(target, "pk", None)
        if pk is not None and pk in seen_pks:
            raise CombatSessionError(
                SessionReason.DUPLICATE_PARTICIPANT,
                f"target dbref {pk} is supplied more than once",
            )
        seen_pks.add(pk)
    for target in targets:
        if not isinstance(target, Monster):
            raise CombatSessionError(SessionReason.NOT_HOSTILE)
        if actor.location is None or target.location is not actor.location:
            raise CombatSessionError(SessionReason.NOT_PRESENT)
        if _stored_trait_value(target.traits.hp) <= 0:
            raise CombatSessionError(SessionReason.TARGET_DEAD)

    from world.rules.party import combat_companions

    companions = [
        int(companion.pk) for companion in combat_companions(actor)
    ]
    record = CombatSessionRecord(
        session_id=session_id_for(actor, "hostile"),
        mode="hostile",
        room_id=int(actor.location.pk),
        player_ids=(int(actor.pk), *companions),
        enemy_ids=tuple(sorted(int(target.pk) for target in targets)),
        fled_ids=(),
        knocked_out_ids=(),
        rounds_elapsed=0,
        exam_id=None,
    )
    battlefield = reconstruct_battlefield(actor, record)
    _persist(actor, record)
    register_active_battlefield(battlefield)
    # Hostility ends a conversation (webclient-align-07): the session is
    # retired in the same deterministic-core path that persisted the session,
    # so no snapshot can ever render dialogue mode over a live combat session.
    from world.rules.dialogue import clear_dialogue_session

    clear_dialogue_session(actor)
    return {
        "record": record,
        "overwhelming_team": classify_overwhelm(battlefield),
    }
