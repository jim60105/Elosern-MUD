"""Deterministic defeat aftermath (defeat-aftermath-core).

Runs inside ``settle_session``'s ``transaction.atomic()`` for every
hostile-mode ``outcome == "defeat"`` settlement, on the deterministic-core
side of the single-writer boundary (parent design §4.1). The writer floors
the defeated player at the nonlethal HP floor, marks the knockout, departs
the living violators (population despawn; quest-bound monsters retained with
precedence), mounts the weak debuff, and records the defeat EventLog kinds.
The violation-sequence hook point is a guarded no-op registry entry the adult
changes fill; with ``DEFEAT_ADULT_SCENES`` off the hook is never called and
the core-only behavior is the entire settlement.

Rollback contract (design D-C5): the database rows restore through the
transaction, but Evennia's idmapper cache is not transaction-aware, so every
in-process surface the writer touches (actor trait/buff attributes, the
transient battlefield knockout set, the departed monsters' marker and
bookkeeping) is snapshotted at entry and restored by the idempotent
``undo`` closure on every exception boundary — the writer's own, the
settlement's commit/exit failure, and a later outer round-transaction
rollback (armed via :func:`register_pending_undo` because Django has no
rollback hook).

Departure contract (design D-C3, two-phase): the logical departure (marker
clear + bookkeeping drop) commits inside the settlement transaction; the
physical deletion is scheduled through ``transaction.on_commit`` so it runs
only after the outermost durable commit — a rolled-back round discards it.
A post-commit delete failure reverts the logical departure deterministically;
only a process crash in the post-commit window leaves a marker-less live
monster (the parent design's accepted restart-refresh risk).
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

from world.observability import log_error, log_info, log_warn
from world.rules.action import (
    _attribute_snapshot,
    _restore_attribute,
    _stored_trait_value,
)
from world.rules.buffs import _add_buff
from world.rules.event_log import EventEntry, EventLog
from world.rules.player_messages import defeat_aftermath_template

_DEFEAT_AFTERMATH_PATH = Path(__file__).parent / "rulebook" / "defeat_aftermath.yaml"
_OWNED_SECTIONS = frozenset({"pg_lines", "weak_debuff"})


@dataclass(frozen=True)
class DefeatAftermathResult:
    """The writer's full handoff to ``settle_session``.

    ``session`` and ``logs`` feed the persisted record and the settlement
    result; ``undo`` is the caller's failure-boundary restoration hook;
    ``departed`` lists the violators whose departure committed and whose
    physical deletion runs post-commit (exam-opponent shape).
    """

    session: Any
    logs: tuple[EventLog, ...]
    undo: Callable[[], None]
    departed: tuple[Any, ...]


class DefeatAftermathRulebook:
    """Validated per-section rulebook data owned by this change."""

    __slots__ = ("pg_lines", "weak_debuff_buff_key")

    def __init__(self, pg_lines: tuple[str, ...], weak_debuff_buff_key: str) -> None:
        self.pg_lines = pg_lines
        self.weak_debuff_buff_key = weak_debuff_buff_key


def load_defeat_aftermath_sections(path: Path) -> DefeatAftermathRulebook:
    """Load the defeat-aftermath rulebook, validating owned sections.

    Unknown sections belong to downstream changes and are ignored with one
    ``log_warn`` (design D-C8); a malformed owned section fails closed at
    load like every other rulebook.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a YAML mapping of sections")
    unknown = sorted(str(key) for key in set(raw) - _OWNED_SECTIONS)
    if unknown:
        log_warn(
            "defeat_aftermath_unknown_section_ignored",
            context={"path": str(path), "sections": ", ".join(unknown)},
        )
    pg_lines = raw.get("pg_lines")
    if (
        not isinstance(pg_lines, list)
        or not pg_lines
        or any(not isinstance(line, str) or not line.strip() for line in pg_lines)
    ):
        raise ValueError(
            f"{path}: section 'pg_lines' must be a nonempty list of nonempty strings"
        )
    weak_debuff = raw.get("weak_debuff")
    if not isinstance(weak_debuff, dict) or not isinstance(
        weak_debuff.get("buff_key"), str
    ):
        raise ValueError(
            f"{path}: section 'weak_debuff' must be a mapping with a string 'buff_key'"
        )

    from world.rules.buffs import BUFF_DEFINITIONS

    if weak_debuff["buff_key"] not in BUFF_DEFINITIONS:
        raise ValueError(
            f"{path}: weak_debuff buff_key {weak_debuff['buff_key']!r} "
            "is not a rulebook buff"
        )
    return DefeatAftermathRulebook(
        pg_lines=tuple(pg_lines),
        weak_debuff_buff_key=weak_debuff["buff_key"],
    )


DEFEAT_AFTERMATH_RULEBOOK = load_defeat_aftermath_sections(_DEFEAT_AFTERMATH_PATH)

_VIOLATION_HOOK: Callable[..., None] | None = None
_PENDING_OUTER_UNDOS: list[Callable[[], None]] = []


def register_pending_undo(undo: Callable[[], None]) -> None:
    """Arm the aftermath undo for a later outer-transaction rollback.

    A defeat settled inside a nested round transaction (the ordinary
    submission path) can still be rolled back by the enclosing transaction
    AFTER ``settle_session`` returned, and Django has no rollback hook. The
    round wrapper drains and runs the armed undo on its failure boundary and
    discards it on success; ``undo`` is idempotent.
    """
    _PENDING_OUTER_UNDOS.append(undo)


def drain_pending_undos() -> list[Callable[[], None]]:
    """Return and clear every armed undo (run them, or discard on commit)."""
    pending = list(_PENDING_OUTER_UNDOS)
    _PENDING_OUTER_UNDOS.clear()
    return pending


def register_violation_hook(hook: Callable[..., None]) -> None:
    """Register the violation-sequence body contributed by an adult change.

    A single registration point: a second distinct registration fails loudly
    instead of silently replacing an adult phase; re-registering the
    identical callable is accepted so idempotent boot registration stays
    possible.
    """
    global _VIOLATION_HOOK
    if not callable(hook):
        raise ValueError("the defeat violation hook must be callable")
    if _VIOLATION_HOOK is not None and _VIOLATION_HOOK is not hook:
        raise RuntimeError("the defeat violation hook is already registered")
    _VIOLATION_HOOK = hook


def _call_violation_hook(battlefield: Any, session: Any) -> None:
    """Run the guarded violation hook point (design D-C4).

    Pure guard: with ``DEFEAT_ADULT_SCENES`` off the hook is never called and
    the core-only settlement is the entire behavior; with the flag on but no
    adult body registered the call is a no-op.
    """
    if not settings.DEFEAT_ADULT_SCENES:
        return
    if _VIOLATION_HOOK is not None:
        _VIOLATION_HOOK(battlefield, session)


def run_defeat_aftermath(
    actor: Any,
    session: Any,
    battlefield: Any | None,
) -> DefeatAftermathResult:
    """Apply the deterministic defeat aftermath inside the caller's transaction.

    Phase order (tasks 1.2): HP floor + knockout mark -> guarded violation
    hook -> violator departure -> weak debuff -> EventLog. The caller persists
    the returned session record and clears the session afterwards. Nothing
    here rolls dice, so a rolled-back retry re-derives the identical aftermath
    (design D-C5). Returns a :class:`DefeatAftermathResult`: the
    knockout-marked session record, the aftermath EventLog the caller
    appends to the settlement result, and an idempotent callable that undoes
    every in-process surface the writer touched. The caller MUST run
    ``undo`` on its own failure boundary before the exception propagates:
    the transaction restores the database rows, but the idmapper cache is
    not transaction-aware, and a failure after this writer returns (the
    marker persist, the session clear) must still leave no half-applied
    aftermath (design D-C5).
    """
    hp_before = _stored_trait_value(actor.traits.hp)
    trait_snapshot = _attribute_snapshot(actor, "traits", "traits")
    buff_snapshot = _attribute_snapshot(actor, "buffs")
    knocked_out_before = (
        str(actor.key) in battlefield.knocked_out
        if battlefield is not None
        else False
    )
    restores: list[Callable[[], None]] = []
    entries: list[EventEntry] = []
    departed: list[Any] = []

    def undo() -> None:
        """Undo every in-process aftermath surface; idempotent on re-run."""
        for restore in reversed(restores):
            restore()
        _restore_aftermath_surfaces(
            actor,
            battlefield,
            hp_before,
            trait_snapshot,
            buff_snapshot,
            knocked_out_before,
        )

    try:
        # Phase 1: the nonlethal floor (design D-C1). Unconditional on every
        # hostile defeat: a defeated or surrendered player is never persisted
        # at 0 HP, and the floor is the declared writer-owned write.
        actor.traits.hp.current = 1
        if battlefield is not None:
            battlefield.knocked_out.add(str(actor.key))
        if int(actor.pk) not in session.knocked_out_ids:
            session = replace(
                session,
                knocked_out_ids=(*session.knocked_out_ids, int(actor.pk)),
            )
        entries.append(
            EventEntry(
                kind="defeat_settle",
                actor=str(actor.key),
                target=None,
                data={
                    "wake": DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0],
                    "hp_after": 1,
                },
                text_template=defeat_aftermath_template("defeat_settle"),
            )
        )
        # Phase 2: the guarded violation hook point (design D-C4). No core
        # on-branch; the body is contributed by the adult changes.
        _call_violation_hook(battlefield, session)
        # Phase 3: violator departure (design D-C3).
        entries.extend(
            _depart_violators(actor, session, battlefield, restores, departed)
        )
        # Phase 4: the weak debuff (design D-C2).
        _add_buff(actor, DEFEAT_AFTERMATH_RULEBOOK.weak_debuff_buff_key)
        entries.append(
            EventEntry(
                kind="weak_granted",
                actor=str(actor.key),
                target=None,
                data={"buff": DEFEAT_AFTERMATH_RULEBOOK.weak_debuff_buff_key},
                text_template=defeat_aftermath_template("weak_granted"),
            )
        )
    except Exception:
        undo()
        raise
    _schedule_boundary_event(actor)
    return DefeatAftermathResult(
        session=session,
        logs=(
            EventLog(
                actor=str(actor.key),
                skill_key="defeat_aftermath",
                targets=(),
                entries=tuple(entries),
                time_cost_seconds=0,
            ),
        ),
        undo=undo,
        departed=tuple(departed),
    )


def _living_foes(actor: Any, session: Any, battlefield: Any | None) -> list[Any]:
    """Return the living, non-fled foe-team members of the settled session.

    The battlefield roster is preferred; the degraded recovery path (no
    reconstructible battlefield) resolves the durable record's enemy dbrefs
    instead, discarding missing, fled, or dead objects, so a recovered defeat
    still departs its resolvable population winner (review D4).
    """
    if battlefield is not None:
        player_team = battlefield.team_of(str(actor.key))
        foe_team = next(
            team for team in battlefield.teams if team != player_team
        )
        return [
            entity
            for key in battlefield.teams[foe_team]
            if key in battlefield.roster
            and key not in battlefield.fled
            and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
            for entity in (battlefield.roster[key],)
        ]
    from evennia.objects.models import ObjectDB

    foes: list[Any] = []
    for enemy_id in session.enemy_ids:
        if enemy_id in session.fled_ids:
            continue
        entity = ObjectDB.objects.filter(id=enemy_id).first()
        if entity is None or _stored_trait_value(entity.traits.hp) <= 0:
            continue
        foes.append(entity)
    return foes


def _depart_violators(
    actor: Any,
    session: Any,
    battlefield: Any | None,
    restores: list[Callable[[], None]],
    departed: list[Any],
) -> list[EventEntry]:
    """Depart every living winning violator (design D-C3).

    Quest-bound monsters (pk in the settling player's persisted quest
    records' ``objective_target_ids``) are never removed: quest retention
    outranks the population marker, and removing an extermination target
    would be disguised record loss. Marker-carrying population monsters
    departure through the population service's public primitive; foreign
    monsters stay untouched. One ``violator_depart`` entry is recorded per
    departure; the physical deletion of the departed runs post-commit via
    :func:`finalize_departure`.
    """
    from world.quests.runtime import read_records

    quest_bound = {
        target_id
        for record in read_records(actor)
        for target_id in record.objective_target_ids
    }
    entries: list[EventEntry] = []
    for violator in _living_foes(actor, session, battlefield):
        if int(violator.pk) in quest_bound:
            continue
        if not violator.db.population_key:
            continue
        from world.maps.wilderness_population import depart_population_monster

        wilderness = getattr(
            getattr(violator, "location", None), "wilderness", None
        )
        if wilderness is None:
            log_warn(
                "defeat_aftermath_despawn_without_wilderness",
                context={"monster": str(violator), "char": str(actor.key)},
            )
            continue
        ticket = depart_population_monster(wilderness, violator)
        restores.append(ticket.revert)
        departed.append(ticket)
        entries.append(
            EventEntry(
                kind="violator_depart",
                actor=str(violator.key),
                target=str(actor.key),
                data={"mode": "population"},
                text_template=defeat_aftermath_template("violator_depart"),
            )
        )
    return entries


def finalize_departure(actor: Any, tickets: tuple[Any, ...]) -> None:
    """Delete the departed violators after the OUTERMOST transaction committed.

    Scheduled through ``transaction.on_commit`` from inside the settlement
    transaction, so the physical deletion runs only after the durable commit
    and a rolled-back outer round discards it. Best effort with deterministic
    recovery: a failed delete reverts the logical departure (marker and
    bookkeeping restored, the monster stays a normal reconcilable population
    monster) and logs at error level; only a process crash in the post-commit
    window leaves a marker-less live monster — the accepted restart-refresh
    risk the parent design already carries.
    """
    for ticket in tickets:
        try:
            ticket.monster.delete()
        except Exception as error:
            try:
                ticket.revert()
            except Exception as revert_error:
                log_error(
                    "defeat_aftermath_depart_revert_failed",
                    exc=revert_error,
                    context={
                        "char": str(actor.key),
                        "monster": str(ticket.monster),
                    },
                )
            log_error(
                "defeat_aftermath_depart_delete_failed",
                exc=error,
                context={"char": str(actor.key), "monster": str(ticket.monster)},
            )


def _restore_aftermath_surfaces(
    actor: Any,
    battlefield: Any | None,
    hp_before: float,
    trait_snapshot: tuple[bool, Any],
    buff_snapshot: tuple[bool, Any],
    knocked_out_before: bool,
) -> None:
    """Undo every in-process surface the writer touched after a rollback.

    The database rows restore through the transaction; the idmapper cache is
    not transaction-aware, so each surface is put back explicitly before the
    exception propagates (design D-C5).
    """
    _restore_attribute(actor, "buffs", buff_snapshot)
    _restore_attribute(actor, "traits", trait_snapshot, category="traits")
    # The trait handler caches its data dict; rebind it to the restored
    # attribute and drop the per-trait cache (same reset as _restore_entity_state).
    actor.traits.trait_data = actor.attributes.get(
        "traits", default={}, category="traits"
    )
    actor.traits._cache.clear()
    if battlefield is not None and not knocked_out_before:
        battlefield.knocked_out.discard(str(actor.key))


def _schedule_boundary_event(actor: Any) -> None:
    """Schedule the ``defeat_aftermath`` boundary info event (design D-C6).

    Fires only on the outermost durable commit, like ``settlement_done``; the
    context is snapshotted as primitives so the callback carries no live
    objects.
    """
    from django.db import transaction

    from world.rules.clock import get_world_clock

    boundary = {
        "char": str(actor.key),
        "room": str(actor.location.pk) if actor.location is not None else None,
        "tick": get_world_clock().tick,
        "hp_after": _stored_trait_value(actor.traits.hp),
    }
    transaction.on_commit(
        lambda boundary=boundary: log_info("defeat_aftermath", context=boundary)
    )
