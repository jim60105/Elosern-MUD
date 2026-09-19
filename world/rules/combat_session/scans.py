"""Post-round consequence scans for one resolved player round.

The friendly-fire and sexual-coercion scans read the round's ``EventLog``s and
apply the rulebook affinity penalties through the sole affinity writer, inside
the round's outer transaction. They return auto-leave notification lines; the
caller delivers them only after the transaction commits (the writer never
notifies).
"""

from typing import Any

from world.rules.combat import Battlefield


def _scan_friendly_fire(
    actor: Any,
    battlefield: Battlefield,
    logs: list[Any],
) -> tuple[str, ...]:
    """Apply per-hit friendly-fire penalties for one resolved player round.

    Scans the round's damage events produced by the player's own action
    (EventLogs whose ``actor`` is the player) against ally-side companion
    NPCs: a hit qualifies when the target is an NPC in the snapshotted
    ``player.db.party`` set and present on the battlefield. Each qualifying
    hit calls the sole affinity writer once with the ``friendly_fire`` source
    and the rulebook penalty, inside one transaction that also covers every
    resulting auto-leave -- a failure rolls the whole round's affinity effects
    back. Returns the auto-leave notification lines; the caller delivers them
    only after the transaction commits (the writer never notifies).
    """
    from django.db import transaction

    from typeclasses.npcs import NPC
    from world.rules.affinity import AffinitySource, apply_affinity_change
    from world.rules.affinity_config import get_config
    from world.rules.party import party_ids

    companion_pks = set(party_ids(actor))
    if not companion_pks:
        return ()
    player_key = str(actor.key)
    hits: list[Any] = []
    for event_log in logs:
        if event_log.actor != player_key:
            continue
        for entry in event_log.entries:
            if entry.kind != "damage":
                continue
            target = battlefield.roster.get(entry.target)
            if (
                target is None
                or not isinstance(target, NPC)
                or int(target.pk) not in companion_pks
            ):
                continue
            hits.append(target)
    if not hits:
        return ()
    penalty = get_config().friendly_fire_penalty_per_hit
    notifications: list[str] = []
    party_before = list(actor.db.party or ())
    members_before = {
        int(target.pk): target.db.party_member for target in hits
    }
    relations_before = {
        int(target.pk): target.db.relations_data for target in hits
    }
    try:
        with transaction.atomic():
            for target in hits:
                outcome = apply_affinity_change(
                    target, actor, AffinitySource.FRIENDLY_FIRE, -penalty
                )
                if outcome.auto_leave_notification is not None:
                    notifications.append(outcome.auto_leave_notification)
    except Exception:
        # The round's transaction rolled the database back; restore the
        # in-process attribute surfaces so readers never observe the
        # rolled-back values (the idmapper cache is not transaction-aware).
        from world.rules.affinity import restore_relations_surfaces
        from world.rules.party import restore_membership_surfaces

        restore_membership_surfaces(actor, party_before, members_before)
        restore_relations_surfaces(relations_before)
        raise
    return tuple(notifications)


def _scan_sexual_coercion(
    actor: Any,
    battlefield: Battlefield,
    logs: list[Any],
) -> tuple[str, ...]:
    """Apply per-forced-act coercion penalties for one resolved player round.

    Scans the round's ``EventLog``s for the resist-outcome contract
    ``sexual-act-effects`` emits (``EventEntry(kind="sexual_resist", data=
    {"resisted": bool, "auto_comply": bool, "roll": int | None})``, documented
    in ``sexual-act-resolution-design.md`` §3.4). Only the player's own action
    logs are scanned (mirroring ``_scan_friendly_fire``'s actor filter), so a
    future non-player emitter -- a companion's or monster's own cast -- can
    never charge the player's affinity for someone else's act. Only an entry
    recording a forced outcome -- ``resisted is False`` and ``auto_comply is
    False`` -- costs the target's affinity toward the actor; a compliance
    (rolled or automatic) and a successful resistance apply no penalty. Each
    qualifying entry calls the sole affinity writer once with the
    ``sexual_forced`` source and the rulebook penalty, inside one transaction
    that also covers every resulting auto-leave -- a failure rolls the whole
    round's affinity effects back. A target that resolves to no roster member
    or to a non-``NPC`` applies no penalty (mirroring
    ``apply_affinity_change``'s own owner rejection without needing to call
    it). Returns the auto-leave notification lines; the caller delivers them
    only after the transaction commits (the writer never notifies).
    """
    from django.db import transaction

    from typeclasses.npcs import NPC
    from world.rules.affinity import AffinitySource, apply_affinity_change
    from world.rules.affinity_config import get_config

    player_key = str(actor.key)
    forced: list[Any] = []
    for event_log in logs:
        if event_log.actor != player_key:
            continue
        for entry in event_log.entries:
            if entry.kind != "sexual_resist":
                continue
            if not isinstance(entry.data, dict):
                # Fail closed on a malformed payload: never penalize, never
                # crash the round over a bad record.
                continue
            # ``is False``, not falsy-truthiness: a missing or mistyped key
            # must read as "do not penalize" rather than accidentally matching.
            if entry.data.get("resisted") is not False:
                continue
            if entry.data.get("auto_comply") is not False:
                continue
            target = battlefield.roster.get(entry.target)
            if target is None or not isinstance(target, NPC):
                continue
            forced.append(target)
    if not forced:
        return ()
    penalty = get_config().sexual_forced_penalty
    notifications: list[str] = []
    party_before = list(actor.db.party or ())
    members_before = {
        int(target.pk): target.db.party_member for target in forced
    }
    relations_before = {
        int(target.pk): target.db.relations_data for target in forced
    }
    try:
        with transaction.atomic():
            for target in forced:
                outcome = apply_affinity_change(
                    target, actor, AffinitySource.SEXUAL_FORCED, -penalty
                )
                if outcome.auto_leave_notification is not None:
                    notifications.append(outcome.auto_leave_notification)
    except Exception:
        # The round's transaction rolled the database back; restore the
        # in-process attribute surfaces so readers never observe the
        # rolled-back values (the idmapper cache is not transaction-aware).
        from world.rules.affinity import restore_relations_surfaces
        from world.rules.party import restore_membership_surfaces

        restore_membership_surfaces(actor, party_before, members_before)
        restore_relations_surfaces(relations_before)
        raise
    return tuple(notifications)
