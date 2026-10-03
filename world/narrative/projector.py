"""Narrative event projection selector for combat and actions."""

from typing import Any, Iterable

from world.narrative.events import build_encounter_source_id, record_narrative_event
from world.rules.combat_session.records import CombatSessionRecord


def select_and_record_protection_event(
    *,
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Any,
    outcome: str,
    opening: str = "round",
    rounds_elapsed: int = 0,
    settled_tick: int = 0,
) -> bool:
    """Select whether this encounter represents a covered protection event and record it durably.

    Criteria for W1 protection encounter:
    1. A protected participant exists on the actor's side (e.g. nonlethal companion / allied non-player participant).
    2. The encounter outcome is victory (or successful completion) while the protected participant was not knocked out or fled.
    3. Source ID is built stably from encounter session_id and kind ('settlement' or 'compressed_opening').
    """
    if outcome != "victory":
        return False

    allied_nonlethal_keys = set()
    if battlefield is not None:
        if hasattr(battlefield, "nonlethal_keys"):
            allied_nonlethal_keys = set(battlefield.nonlethal_keys)
        elif hasattr(record, "mode") and record.mode == "hostile":
            # In hostile sessions, allied non-player roster members are nonlethal protected companions
            player_team = battlefield.team_of(str(actor.key)) if hasattr(battlefield, "team_of") else None
            for key in battlefield.roster:
                if key != str(actor.key) and (player_team is None or battlefield.team_of(key) == player_team):
                    allied_nonlethal_keys.add(key)

    # Collect participants that qualify for protection
    protected_keys = set()
    for key in allied_nonlethal_keys:
        if key in battlefield.roster and key != str(actor.key):
            # Check if this participant fled or was knocked out
            if key not in battlefield.fled and key not in battlefield.knocked_out:
                protected_keys.add(key)

    if not protected_keys:
        return False

    # Durable participant identities: actor PK plus protected entity PKs
    participant_pks: list[str] = [str(actor.pk)]
    for key in sorted(protected_keys):
        entity = battlefield.roster[key]
        if hasattr(entity, "pk") and entity.pk:
            participant_pks.append(str(entity.pk))
        else:
            participant_pks.append(str(key))

    source_kind = "settlement" if opening == "round" else "compressed_settlement"
    source_id = build_encounter_source_id(
        session_id=record.session_id,
        kind=source_kind,
        ordinal=rounds_elapsed,
    )

    room_loc = str(record.room_id)
    content = {
        "encounter_outcome": outcome,
        "opening": opening,
        "protected_keys": sorted(list(protected_keys)),
        "mode": record.mode,
        "rounds_elapsed": rounds_elapsed,
    }

    record_narrative_event(
        source_id=source_id,
        event_type="encounter_protection",
        content=content,
        participants=participant_pks,
        location=room_loc,
        tick=int(settled_tick),
        visibility="public",
        salience=2,
    )
    return True
