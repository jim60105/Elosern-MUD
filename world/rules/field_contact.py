"""Authored field-contact authority: evaluate, admit and continue one encounter.

A player-driven advance and a committed relocation are the only sources of
real arrival time. This module turns an authored aggressive activity
declaration into one ordinary whole-cell encounter at such a boundary: it
never creates a second scheduler, never admits from a read/preview, and never
runs an enemy round inside a clock source. The clock source persists the
session and returns an interactive event; the owning rules action drains
``continue_incapacitated_hostile_rounds`` after the accepted
``WorldClock.advance`` returned, inside the same outer durable operation.

Ownership split (see ``combat_session.lifecycle``):

* ``evaluate_field_contact`` is a pure read. It selects the *triggers* whose
  authored condition holds and reports the stable commander location; roster
  membership is always the whole living local cell, never the trigger set.
* ``admit_field_contact`` is the writer. It revalidates under the serialized
  combat writer, interrupts voluntary sleep through its owner, persists the
  session with explicit ``hostile_contact`` authority and stages the committed
  ``field_contact_admitted`` event. It never advances the clock.
* ``admit_field_contact_at`` is the owning-action convenience: evaluate,
  admit, then drain the predecessor continuation once the advance is over.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from django.db import transaction

from typeclasses.characters import PlayerCharacter
from world.observability import log_error, log_info
from world.rules.action import _attribute_snapshot, _restore_attribute
from world.rules.clock import (
    ScheduledEvent,
    SurfaceSnapshot,
    current_advance_scope,
    daypart_at,
    next_daypart_boundary,
    read_world_clock,
)
from world.rules.combat_session.writer import serialized_combat_write
from world.rules.fatigue import FATIGUE_ATTRIBUTE_SURFACES
from world.rules.movement_edges import LocationRef, LocationRefError, location_ref
from world.rules.sleep_receipt import SLEEP_RECEIPT_SURFACES

#: The closed source vocabulary of one admission. It names the boundary that
#: observed the contact; it never selects roster membership.
SOURCE_FIELD = "field"
SOURCE_MOVEMENT = "movement"
SOURCE_BIRTH_OR_ARRIVAL = "birth_or_arrival"
SOURCE_PRE_ACTION = "pre_action"
SOURCE_SOURCE = "source"

#: Committed event kind emitted by a source and consumed by the owning action.
CONTACT_EVENT = "field_contact_admitted"

#: Durable attributes the admission itself may write on one participant, in
#: addition to the physiology/receipt surfaces interrupted sleep writes.
_ADMISSION_SURFACES: tuple[tuple[str, str | None], ...] = (
    ("active_combat", None),
    ("combat_encounter_seq", None),
    ("dialogue_session", None),
) + tuple(FATIGUE_ATTRIBUTE_SURFACES) + tuple(SLEEP_RECEIPT_SURFACES)


@dataclass(frozen=True)
class FieldContact:
    """One evaluated authored contact at an exact game-time tick.

    ``trigger_ids`` are the living local individuals whose authored condition
    admitted the contact; the encounter roster is still the whole living local
    cell. ``location`` is the commander's stable physical locator at ``tick``.
    """

    commander_id: int
    location: LocationRef
    tick: int
    trigger_ids: tuple[int, ...]
    source_id: str


def _wilderness() -> Any | None:
    from world.maps import regional_population

    return regional_population.live_wilderness()


def _group_for(wilderness: Any, individual_id: int) -> Any | None:
    if wilderness is None:
        return None
    from world.maps import monster_activity

    return monster_activity.group_of_member(wilderness, individual_id)


def _declaration_for(group: Any) -> Any | None:
    if group is None:
        return None
    from world.lore.monster_activity import MONSTER_ACTIVITY_REGISTRY

    return MONSTER_ACTIVITY_REGISTRY.get(group.activity_key)


def _daypart_admits(condition: Any, tick: int) -> bool:
    declared = tuple(condition.dayparts)
    return not declared or daypart_at(tick) in declared


def _cell_of(wilderness: Any, body: Any) -> tuple[int, int] | None:
    from world.maps import regional_population

    if wilderness is None:
        return None
    return regional_population.actual_cell(wilderness, body)


def _defended_area_admits(
    declaration: Any, group: Any, wilderness: Any, body: Any
) -> bool:
    from world.lore.monster_activity import ACTIVITY_AREA_REGISTRY

    area = ACTIVITY_AREA_REGISTRY.get(declaration.aggression.area_key)
    if area is None:
        return False
    home = group.home
    if home.kind == "room":
        return area.home_radius == 0 and getattr(
            getattr(body, "location", None), "pk", None
        ) == home.id
    cell = _cell_of(wilderness, body)
    if cell is None or home.kind != "wilderness":
        return False
    if area.home_radius is not None:
        return max(abs(cell[0] - home.x), abs(cell[1] - home.y)) <= area.home_radius
    return any(
        x_min <= cell[0] <= x_max and y_min <= cell[1] <= y_max
        for x_min, x_max, y_min, y_max in area.rectangles
    )


def _admits_contact(monster: Any, wilderness: Any, tick: int) -> bool:
    """Whether one individual's authored declaration admits contact now."""
    from world.rules.movement_settlement import field_presence, in_passage

    if not field_presence(monster, tick) or in_passage(monster, tick):
        return False
    group = _group_for(wilderness, int(monster.pk))
    if group is None or group.journey_id is not None:
        return False
    declaration = _declaration_for(group)
    if declaration is None:
        # A staged/unpublished binding has no authored aggression condition;
        # it is passive by construction, never inferred from a name.
        return False
    condition = declaration.aggression
    if condition.kind == "passive":
        return False
    if condition.kind == "contact":
        return _daypart_admits(condition, tick)
    if condition.kind == "defended_area":
        return _daypart_admits(condition, tick) and _defended_area_admits(
            declaration, group, wilderness, monster
        )
    return False


def evaluate_field_contact(
    commander: Any, *, tick: int
) -> FieldContact | None:
    """Return the authored contact this party admits at ``tick``, or ``None``.

    Pure: it reads the commander's stable position, the living local Monster
    roster, the authored activity declarations and the calendar. It writes
    nothing, creates nothing and advances no clock. A commander in a committed
    traversal's passage is not ordinary field presence and never contacts.
    """
    if not isinstance(commander, PlayerCharacter):
        return None
    if getattr(commander, "location", None) is None:
        return None
    from world.rules.combat_initiation import field_enemy_roster
    from world.rules.movement_settlement import field_presence, in_passage

    if not field_presence(commander, tick) or in_passage(commander, tick):
        return None
    try:
        location = location_ref(commander)
    except (LocationRefError, ValueError):  # observability: ignore R2: an unrepresentable position is simply not a contact location; the evaluator is a pure predicate and reports nothing
        return None
    roster = field_enemy_roster(commander)
    if not roster:
        return None
    wilderness = _wilderness()
    triggers = tuple(
        sorted(
            int(monster.pk)
            for monster in roster
            if _admits_contact(monster, wilderness, tick)
        )
    )
    if not triggers:
        return None
    return FieldContact(
        commander_id=int(commander.pk),
        location=location,
        tick=int(tick),
        trigger_ids=triggers,
        source_id=SOURCE_FIELD,
    )


def _owned_elsewhere(wilderness: Any, monster: Any) -> bool:
    """Whether another persisted session already owns this map individual."""
    group = _group_for(wilderness, int(monster.pk))
    if group is None:
        return False
    member = group.member_time.get(str(int(monster.pk)))
    return member is not None and member.session_id is not None


def _party_bodies(commander: Any) -> tuple[Any, ...]:
    from world.rules.party import combat_companions

    return (commander, *combat_companions(commander))


def _snapshot_participants(bodies: tuple[Any, ...]) -> dict[int, tuple[Any, list[Any]]]:
    return {
        id(body): (
            body,
            [(key, category, _attribute_snapshot(body, key, category))
             for key, category in _ADMISSION_SURFACES],
        )
        for body in bodies
    }


def _restore_participants(snapshot: dict[int, tuple[Any, list[Any]]]) -> None:
    for body, surfaces in snapshot.values():
        for key, category, captured in surfaces:
            _restore_attribute(body, key, captured, category)


@serialized_combat_write
def admit_field_contact(commander: Any, contact: FieldContact) -> dict[str, Any] | None:
    """Persist one authored contact under the serialized combat writer.

    Revalidates the actual location, tick and authored condition before any
    write; an existing active session or a roster another encounter already
    owns deduplicates the admission. Voluntary sleepers are interrupted
    through ``time_skip.interrupt_sleep_for_contact`` (their owner writer)
    before the session records its roster, so the body keeps the real
    recovered reserve and its receipt becomes interrupted at ``contact.tick``.
    Forced sleep and defeated bodies are never woken or revived. The session
    is created with explicit ``hostile_contact`` authority and *without* the
    predecessor continuation: a clock source must never advance the clock.
    """
    if not isinstance(commander, PlayerCharacter):
        return None
    tick = int(contact.tick)
    fresh = evaluate_field_contact(commander, tick=tick)
    if fresh is None or fresh.location != contact.location:
        return None
    from world.rules.combat_session import read_session
    from world.rules.combat_session.lifecycle import (
        create_hostile_contact_session,
    )

    if read_session(commander) is not None:
        return None
    from world.rules.combat_initiation import field_enemy_roster

    wilderness = _wilderness()
    roster = tuple(
        monster
        for monster in field_enemy_roster(commander)
        if not _owned_elsewhere(wilderness, monster)
    )
    if not roster:
        return None
    bodies = _party_bodies(commander)
    snapshot = _snapshot_participants(bodies)
    operation_id = f"contact:{contact.source_id}:{int(commander.pk)}:{tick}"
    try:
        from world.rules.time_skip import interrupt_sleep_for_contact

        for body in bodies:
            interrupt_sleep_for_contact(
                body, tick=tick, operation_id=operation_id
            )
        result = create_hostile_contact_session(
            commander, roster, started_tick=tick
        )
    except Exception:
        # The owning boundary (``admit_field_contact_at``) restores the same
        # participants after its transaction rolled back and reports the one
        # ``field_contact_failed`` event, so a nested failure is never
        # reported twice.
        _restore_participants(snapshot)
        raise
    record = result["record"]
    boundary = {
        "char": str(int(commander.pk)),
        "source_id": contact.source_id,
        "session": record.session_id,
        "engagement": record.engagement_id or record.session_id,
        "tick": tick,
        "room": str(record.room_id),
        "triggers": ",".join(str(pk) for pk in contact.trigger_ids),
        "enemies": ",".join(str(pk) for pk in record.enemy_ids),
        "location": _location_context(contact.location),
    }
    transaction.on_commit(
        lambda boundary=boundary: log_info(
            "field_contact_admitted", context=boundary
        )
    )
    return {
        "record": record,
        "session": record.session_id,
        "commander": int(commander.pk),
        "tick": tick,
        "source_id": contact.source_id,
        "trigger_ids": tuple(contact.trigger_ids),
        "enemy_ids": tuple(record.enemy_ids),
        "continuation": None,
        "continuation_required": True,
    }


def _location_context(location: LocationRef) -> str:
    if location.kind == "wilderness":
        return f"{location.map}:{location.x},{location.y}"
    return f"room:{location.id}"


def continue_admitted_contacts(
    commander: Any, events: Any
) -> list[dict[str, Any]]:
    """Drain the predecessor continuation for every admission in ``events``.

    Only the owning rules action calls this, after the accepted
    ``WorldClock.advance`` returned and persisted its endpoint. An admission
    already terminated by the same interval, or one naming another commander,
    is skipped without running a round.
    """
    from world.rules.combat_session import read_session
    from world.rules.combat_session.rounds import (
        continue_incapacitated_hostile_rounds,
    )

    commander_id = int(getattr(commander, "pk", 0) or 0)
    results: list[dict[str, Any]] = []
    seen: set[int] = set()
    for event in events:
        if getattr(event, "kind", None) != CONTACT_EVENT:
            continue
        payload = getattr(event, "payload", None) or {}
        try:
            subject = int(payload.get("commander"))
        except (TypeError, ValueError):  # observability: ignore R2: a malformed event payload names no commander and therefore drains no session
            continue
        if subject != commander_id or subject in seen:
            continue
        seen.add(subject)
        if read_session(commander) is None:
            continue
        results.append(continue_incapacitated_hostile_rounds(commander))
    return results


def admit_field_contact_at(
    commander: Any, *, source_id: str, tick: int | None = None, settle: bool = True
) -> dict[str, Any] | None:
    """Evaluate, admit and (when requested) continue one contact.

    Used by owning actions that are *not* inside a clock source: a committed
    relocation and a pre-exploration action. ``settle=False`` is for a caller
    that owns a different continuation policy.
    """
    if not isinstance(commander, PlayerCharacter):
        return None
    if tick is None:
        clock = read_world_clock()
        tick = 0 if clock is None else int(clock.tick)
    contact = evaluate_field_contact(commander, tick=int(tick))
    if contact is None:
        return None
    contact = replace(contact, source_id=source_id)
    # The owning pre-action/relocation boundary has no enclosing transaction
    # of its own: interruption, session persistence, deferred registration and
    # the automatic rounds form one durable unit here. A late failure restores
    # the participant surfaces after the rollback and emits the contact
    # failure boundary, so an interrupted receipt or a committed encounter can
    # never survive a failed action.
    snapshot = _snapshot_participants(_party_bodies(commander))
    try:
        with transaction.atomic():
            result = admit_field_contact(commander, contact)
            if result is None:
                return None
            if settle:
                from world.rules.combat_session import read_session
                from world.rules.combat_session.rounds import (
                    continue_incapacitated_hostile_rounds,
                )

                if read_session(commander) is not None:
                    result["continuation"] = (
                        continue_incapacitated_hostile_rounds(commander)
                    )
    except Exception as error:
        _restore_participants(snapshot)
        log_error(
            "field_contact_failed",
            exc=error,
            context={
                "char": str(int(commander.pk)),
                "source_id": source_id,
                "tick": int(tick),
                "room": str(getattr(getattr(commander, "location", None), "pk", "")),
                "triggers": ",".join(str(pk) for pk in contact.trigger_ids),
            },
        )
        raise
    return result


# ---------------------------------------------------------------------------
# Clock source: conservative boundary query, endpoint admission, snapshot
# ---------------------------------------------------------------------------


def _scope_commanders() -> tuple[PlayerCharacter, ...]:
    """The player commanders the running advance settles time for."""
    scope = current_advance_scope()
    if not scope:
        return ()
    from evennia.objects.models import ObjectDB
    from world.rules.party_scope import resolve_commander

    bodies = ObjectDB.objects.filter(id__in=scope)
    commanders: dict[int, PlayerCharacter] = {}
    for body in bodies:
        try:
            commander = resolve_commander(body)
        except Exception:  # observability: ignore R2: a body outside any resolvable party simply has no commander to admit for
            continue
        if isinstance(commander, PlayerCharacter):
            commanders[int(commander.pk)] = commander
    return tuple(commanders[pk] for pk in sorted(commanders))


def settle_field_contact_at(
    start_tick: int, end_tick: int
) -> list[ScheduledEvent]:
    """Admit any authored contact at the interval endpoint (source writer).

    The endpoint is the only tick at which physiology has been settled to the
    same instant, so a contact is never admitted after a later recovery. The
    session is persisted here; the owning action drains its continuation after
    ``WorldClock.advance`` returned.
    """
    if end_tick <= start_tick:
        return []
    events: list[ScheduledEvent] = []
    for commander in _scope_commanders():
        result = admit_field_contact_at(
            commander, source_id=SOURCE_SOURCE, tick=int(end_tick), settle=False
        )
        if result is None:
            continue
        events.append(
            ScheduledEvent(
                CONTACT_EVENT,
                int(end_tick),
                {
                    "commander": str(result["commander"]),
                    "session": result["session"],
                    "source_id": result["source_id"],
                    "triggers": ",".join(str(pk) for pk in result["trigger_ids"]),
                    "tick": int(result["tick"]),
                },
                interactive=True,
            )
        )
    return events


def settle_population_contact_at(
    wilderness: Any, tick: int, end_tick: int
) -> list[ScheduledEvent]:
    """Admit endpoint contact for scope parties at one population boundary.

    Called by the merged population coordinator *after* lawful arrivals and
    births and *before* idle departures, so a same-tick contact cannot be
    avoided by iterating a departure first. Only the advance endpoint is
    evaluated: an interior tick was settled by physiology and a past contact
    is never admitted retrospectively.
    """
    if int(tick) != int(end_tick):
        return []
    del wilderness
    events: list[ScheduledEvent] = []
    for commander in _scope_commanders():
        result = admit_field_contact_at(
            commander, source_id=SOURCE_BIRTH_OR_ARRIVAL, tick=int(end_tick),
            settle=False,
        )
        if result is None:
            continue
        events.append(
            ScheduledEvent(
                CONTACT_EVENT,
                int(end_tick),
                {
                    "commander": str(result["commander"]),
                    "session": result["session"],
                    "source_id": result["source_id"],
                    "triggers": ",".join(str(pk) for pk in result["trigger_ids"]),
                    "tick": int(result["tick"]),
                },
                interactive=True,
            )
        )
    return events


def next_field_contact_boundary(start_tick: int, end_tick: int) -> int | None:
    """The conservative next contact-capable boundary inside the window.

    Until the forecast successor replaces these conservative returns with the
    first relevant contact, every next daypart and population
    activity/arrival/birth/decision tick is a boundary: an interruptible skip
    therefore stops before a contact it might otherwise run past.
    """
    from world.maps.population_lifecycle import (
        next_population_lifecycle_boundary,
    )

    candidates = [
        next_daypart_boundary(int(start_tick), int(end_tick)),
        next_population_lifecycle_boundary(int(start_tick), int(end_tick)),
    ]
    inside = [
        candidate
        for candidate in candidates
        if candidate is not None
        and int(start_tick) < int(candidate) <= int(end_tick)
    ]
    return min(inside) if inside else None


def _snapshot_entity(body: Any) -> SurfaceSnapshot:
    return SurfaceSnapshot(
        attributes={
            (key, category): _attribute_snapshot(body, key, category)
            for key, category in _ADMISSION_SURFACES
        }
    )


def snapshot_field_contact_surfaces(
    start_tick: int, end_tick: int
) -> dict[int, SurfaceSnapshot]:
    """The clock advance-surface contract of this source (pure read).

    Discovers the same scope commanders its settlement admits for, plus every
    body in their parties, so an outer rollback after a later stage failure
    restores the session, encounter counter, dialogue, interrupted receipt and
    physiology surfaces together. Map surfaces are supplied by the population
    and activity owners' own contracts.
    """
    del start_tick, end_tick
    registry: dict[int, SurfaceSnapshot] = {}
    for commander in _scope_commanders():
        for body in _party_bodies(commander):
            if not hasattr(body, "attributes"):
                continue
            registry.setdefault(id(body), _snapshot_entity(body))
    return registry


def register_field_contact_stage() -> None:
    """Install the field-contact clock source (idempotent)."""
    from world.rules.clock import register_event_source

    register_event_source(
        "field_contact",
        settle_field_contact_at,
        snapshot_field_contact_surfaces,
        next_boundary=next_field_contact_boundary,
    )


__all__ = [
    "CONTACT_EVENT",
    "FieldContact",
    "SOURCE_BIRTH_OR_ARRIVAL",
    "SOURCE_FIELD",
    "SOURCE_MOVEMENT",
    "SOURCE_PRE_ACTION",
    "SOURCE_SOURCE",
    "admit_field_contact",
    "admit_field_contact_at",
    "continue_admitted_contacts",
    "evaluate_field_contact",
    "next_field_contact_boundary",
    "register_field_contact_stage",
    "settle_field_contact_at",
    "settle_population_contact_at",
    "snapshot_field_contact_surfaces",
]
