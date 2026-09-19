"""The digest phase and its wake-line rendering.

First-match rulebook digest per selected participant, wake-line
rewrites, bystander observations (defeat-aftermath-digest-narrative).

Part of the :mod:`world.rules.defeat_aftermath` package split; the package
re-exports the historical public surface.
"""
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from world.observability import log_info
from world.lore.sexual_vocab import SENSITIVITY_LEVELS
from world.rules.action import _attribute_snapshot, _restore_attribute
from world.rules.buffs import apply_buff
from world.rules.defeat_aftermath.contracts import (
    DigestOutcome,
    DigestRow,
    ViolationOutcome,
    WakeObservation,
)
from world.rules.defeat_aftermath.rulebook import DEFEAT_AFTERMATH_RULEBOOK
from world.rules.defeat_aftermath.violation import (
    _rewrite_wake_line,
    _violation_pool,
)
from world.rules.event_log import EventEntry
from world.rules.player_messages import defeat_aftermath_template


def _max_sensitivity_label(entity: Any) -> str:
    """The entity's own most sensitive materialized channel (D-D1).

    Reads only the sensitivity traits already present — ``items()`` never
    lazily creates traits, so the digest performs no storage write. An
    entity with no seeded channel reads 普通.
    """
    traits = list(entity.sexual.sensitivity.items())
    if not traits:
        return SENSITIVITY_LEVELS[0]
    return SENSITIVITY_LEVELS[max(trait.value for _, trait in traits)]


def _digest_snapshot(entity: Any, outcome: "ViolationOutcome") -> dict[str, Any]:
    """One participant's terminal digest inputs (D-D1).

    Own-body observations only: the entity's sexual state plus the
    sequence's in-memory outcome handoff. No affinity value, no other
    entity's state, no persisted digest input.
    """
    return {
        "sensitivity_level": _max_sensitivity_label(entity),
        "shame_level": entity.sexual.shame.level,
        "arousal_ordinal": entity.sexual.arousal.value,
        "outcome.climax_count": outcome.climax_delta,
        "outcome.zero_landed": outcome.zero_landed,
    }


def _digest_row_matches(row: DigestRow, snapshot: dict[str, Any]) -> bool:
    """Evaluate one row's normalized conditions against the snapshot."""
    for key, condition in row.when.items():
        value = snapshot[key]
        if isinstance(condition, bool):
            if value is not condition:
                return False
        elif isinstance(condition[0], str):
            if value not in condition:
                return False
        else:
            low, high = condition
            if not low <= value <= high:
                return False
    return True


def _match_digest_row(entity: Any, outcome: "ViolationOutcome") -> DigestRow:
    """First matching digest row for one participant (D-D2).

    The loader guarantees the final row is the empty-``when`` fallback, so
    the loop below always returns; the ``LookupError`` documents the
    invariant rather than guarding a reachable path.
    """
    snapshot = _digest_snapshot(entity, outcome)
    for row in DEFEAT_AFTERMATH_RULEBOOK.digest.rows:
        if _digest_row_matches(row, snapshot):
            return row
    raise LookupError("digest rulebook shipped without its fallback row")


def _rewrite_companion_wake(
    entries: list[EventEntry], victim_key: str, wake_line: str
) -> None:
    """Reselect one selected companion's wake line by digest (D-D3).

    The ``companion_wake`` entry stays the companion's sole wake-up
    record; only its line family changes, so no duplicate wake entry is
    rendered (D-D5's no-duplication discipline). The entry is rebuilt
    because ``EventEntry`` is frozen.
    """
    for index, entry in enumerate(entries):
        if entry.kind == "companion_wake" and entry.actor == victim_key:
            entries[index] = replace(entry, text_template=wake_line)
            return


def _digest_bystanders(
    actor: Any,
    session: Any,
    battlefield: Any | None,
    violation: dict[str, "ViolationOutcome"],
) -> list[Any]:
    """Conscious companions who were never selected (D-D7).

    Mirror of the violation pool's two resolution paths restricted to
    companions neither knocked out nor fled and absent from the outcome
    handoff: an untouched knocked-out companion was unconscious (D-P3's
    wake contract keeps it silent) and the defeated player's wake prose
    is the settlement's own, so neither can be a bystander.
    """
    selected = set(violation)
    actor_key = str(actor.key)
    if battlefield is not None:
        player_team = battlefield.team_of(actor_key)
        ally_keys = (
            battlefield.teams.get(player_team, set())
            if player_team is not None
            else set()
        )
        return [
            battlefield.roster[key]
            for key in ally_keys
            if key != actor_key
            and key not in battlefield.fled
            and key not in battlefield.knocked_out
            and key not in selected
            and key in battlefield.roster
        ]
    from evennia.objects.models import ObjectDB

    return [
        entity
        for dbref in session.player_ids
        if dbref != int(actor.pk)
        and dbref not in session.fled_ids
        and dbref not in session.knocked_out_ids
        for entity in (ObjectDB.objects.filter(id=dbref).first(),)
        if entity is not None and str(entity.key) not in selected
    ]


def _schedule_digest_boundary(
    actor: Any,
    digests: list[DigestOutcome],
    wake_observations: list[WakeObservation],
) -> None:
    """Schedule the digest phase's boundary info event (observability)."""
    from django.db import transaction

    from world.rules.clock import get_world_clock

    boundary = {
        "char": str(actor.key),
        "room": str(actor.location.pk) if actor.location is not None else None,
        "tick": get_world_clock().tick,
        "selected": len(digests),
        "residue": sum(digest.digest == "residue" for digest in digests),
        "humiliated": sum(digest.digest == "humiliated" for digest in digests),
        "none": sum(digest.digest == "none" for digest in digests),
        "bystanders": len(wake_observations),
    }
    transaction.on_commit(
        lambda boundary=boundary: log_info(
            "defeat_aftermath_digest", context=boundary
        )
    )


def _run_digest_phase(
    actor: Any,
    session: Any,
    battlefield: Any | None,
    entries: list[EventEntry],
    restores: list[Callable[[], None]],
    violation: dict[str, "ViolationOutcome"],
) -> tuple[tuple[DigestOutcome, ...], tuple[WakeObservation, ...]]:
    """The digest phase (defeat-aftermath-digest-narrative D-D1/D-D6).

    Runs after the recovery advance: one first-match rulebook row per
    selected participant reads only its own terminal sexual state plus the
    sequence's in-memory outcome handoff. ``residue``/``humiliated`` mount
    their buff through the shipped attach path (companion snapshots join
    the writer's undo registry; the actor's own buffs are already covered
    by the run-entry snapshot), every participant gets one
    ``digest_outcome`` entry, and a digest other than ``none`` reselects
    the participant's wake-line family. Conscious unselected companions
    get a ``wake_observation`` entry and a ``WakeObservation`` row —
    never a digest row or a buff (D-D7).
    """
    entities = {
        str(entity.key): entity
        for entity in _violation_pool(actor, session, battlefield)
    }
    digests: list[DigestOutcome] = []
    wake_observations: list[WakeObservation] = []
    for key, outcome in violation.items():
        entity = entities[key]
        row = _match_digest_row(entity, outcome)
        if row.buff is not None:
            if entity is not actor:
                snapshot = _attribute_snapshot(entity, "buffs")

                def _restore_digest_buffs(
                    entity=entity, snapshot=snapshot
                ) -> None:
                    _restore_attribute(entity, "buffs", snapshot)

                restores.append(_restore_digest_buffs)
            apply_buff(entity, row.buff)
        if entity is actor:
            if row.outcome != "none":
                _rewrite_wake_line(
                    entries,
                    defeat_aftermath_template(f"wake_self_{row.outcome}"),
                )
        elif row.outcome != "none":
            _rewrite_companion_wake(
                entries,
                key,
                defeat_aftermath_template(f"wake_companion_{row.outcome}"),
            )
        digests.append(
            DigestOutcome(participant=key, digest=row.outcome, buff=row.buff)
        )
        entries.append(
            EventEntry(
                kind="digest_outcome",
                actor=key,
                target=None,
                data={"digest": row.outcome, "buff": row.buff},
                text_template=defeat_aftermath_template(
                    "digest_outcome"
                    if entity is actor
                    else "digest_outcome_companion"
                ),
            )
        )
    for entity in _digest_bystanders(actor, session, battlefield, violation):
        key = str(entity.key)
        template = defeat_aftermath_template("wake_bystander")
        wake_observations.append(
            WakeObservation(
                participant=key,
                line=template.format(actor=key, target=None, data={}),
            )
        )
        entries.append(
            EventEntry(
                kind="wake_observation",
                actor=key,
                target=None,
                data={},
                text_template=template,
            )
        )
    _schedule_digest_boundary(actor, digests, wake_observations)
    return tuple(digests), tuple(wake_observations)
