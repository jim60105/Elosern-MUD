"""Field-combat initiation: turn one exploration cast into a combat's opening move.

Single purpose (field-combat-initiation D-2): classify the cast's target,
open the session, and play the cast as the fight's first action. This
exploration-side routing deliberately does not live in
the ``world/rules/combat_session`` package; the
dependency direction is one-way — ``combat_initiation`` imports
``combat_session``, never the reverse.
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from typeclasses.monsters import Monster
from world.observability import log_info
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    _attribute_snapshot,
    _restore_attribute,
    _stored_trait_value,
)
from world.rules.action_preview import revalidate_submission
from world.rules.clock import read_world_clock
from world.rules.combat_session import (
    CombatSessionError,
    CombatSessionRecord,
    _context_for,
    engage_group,
    reconstruct_battlefield,
    session_id_for,
    submit_opening_action,
)
from world.rules.overwhelm import classify_overwhelm, commanded_damage_reaches_enemy
from world.rules.skip_safety import unregister_participants
from world.skills.registry import SKILL_REGISTRY, TargetSpec


def field_combat_target(actor: Any, target: Any) -> Monster | None:
    """Return ``target`` when it is a living, co-located, hostile Monster.

    Hostility is expressed exactly as ``engage()`` already expresses it —
    being a ``Monster`` instance — so this predicate introduces no second
    notion of hostility. Co-location requires the actor to actually be
    somewhere: two unlocated entities are not in one room (the predicate
    mirrors ``engage_group()``'s own location check, which rejects a
    ``None`` location rather than comparing ``None is None``).
    """
    if not isinstance(target, Monster):
        return None
    if actor.location is None or target.location is not actor.location:
        return None
    try:
        living = _stored_trait_value(target.traits.hp) > 0
    except (AttributeError, KeyError, TypeError):
        # observability: ignore R2: a target whose traits fail to parse is simply not a field-combat target; engage_group's own reads surface any real error downstream, and this routing predicate never reports them
        living = False
    return target if living else None


def _room_monsters(actor: Any) -> list[Monster]:
    """Every living Monster in the actor's room, deterministic (sorted-pk) order."""
    monsters = [
        occupant
        for occupant in getattr(actor.location, "contents", ())
        if field_combat_target(actor, occupant) is not None
    ]
    return sorted(monsters, key=lambda monster: int(monster.pk))


def _candidate_record(
    actor: Any,
    targets: list[Any],
    *,
    session_id: str | None = None,
) -> CombatSessionRecord:
    """Build the engagement record without persisting it.

    Mirrors ``engage_group()``'s record construction step for step (same
    ``session_id_for`` mode, ``combat_companions()`` party collection, and
    sorted-pk enemy ordering), stopping short of ``_persist`` — the
    candidate battlefield is "reconstruct, then stop" (design §5, D-3).
    A read-only preview passes its own ``session_id`` so building the
    candidate never creates the world-clock script (``session_id_for``
    reads the clock through the creating accessor).
    """
    from world.rules.party import combat_companions

    companions = [int(companion.pk) for companion in combat_companions(actor)]
    return CombatSessionRecord(
        session_id=session_id if session_id is not None else session_id_for(actor, "hostile"),
        mode="hostile",
        room_id=int(actor.location.pk),
        player_ids=(int(actor.pk), *companions),
        enemy_ids=tuple(sorted(int(target.pk) for target in targets)),
        fled_ids=(),
        knocked_out_ids=(),
        rounds_elapsed=0,
        exam_id=None,
    )


@dataclass(frozen=True)
class FieldOpeningPreview:
    """One side-effect-free verdict on opening combat with one cast.

    Attributes:
        enabled: Whether ``initiate_field_combat`` would pass every
            pre-mutation gate right now.
        reason: The stable rejection reason when disabled, else ``None``.
        detail: The rejection detail when disabled, else ``None``.
        targets: The concrete enemy line-up the opening would engage: the
            anchor alone for a non-AREA skill, every living co-located
            monster (sorted pk) for an AREA skill. Filled even when a later
            gate disables the opening, so a disclosure can name the line-up.
        battlefield: The unpersisted candidate battlefield, when built.
        context: The candidate battlefield's action context, when built.
        session_reason: The stable ``SessionReason`` value when the
            candidate battlefield itself could not be built (``reason`` is
            then ``None``), else ``None``.
    """

    enabled: bool
    reason: RejectReason | None
    detail: str | None
    targets: tuple[Any, ...]
    battlefield: Any = None
    context: Any = None
    session_reason: str | None = None


def _opening_line_up(actor: Any, skill: Any, target: Any) -> list[Any]:
    """The enemy line-up an opening cast engages (field-combat-initiation D-5).

    AREA opens against the whole room as an explicit concrete list (never a
    shorthand — ``commanded_damage_reaches_enemy()`` reads concrete keys);
    anything else (SINGLE, and NONE/SELF which then reject on shape) opens
    against the named monster alone.
    """
    if skill is not None and skill.target_spec is TargetSpec.AREA:
        return _room_monsters(actor)
    return [target]


def _prepare_opening(
    actor: Any,
    skill_key: str,
    target: Any,
    scale: float = 1.0,
    *,
    session_id: str | None = None,
) -> FieldOpeningPreview:
    """Run every pre-mutation initiation gate in the execution order.

    Shared verbatim by ``initiate_field_combat`` (which then engages) and
    the read-only ``preview_field_opening`` (which stops here), so a preview
    can never advertise an opening the initiation would refuse. Nothing here
    persists, registers, or advances anything: the candidate record is
    reconstructed, then dropped.
    """
    # The initiation API enforces its own target contract: an AREA skill's
    # line-up is chosen from the room, so without this check a direct caller
    # could open a fight and fire the room-wide action while nominally
    # aiming at nothing (self, an NPC, an absent monster). AREA expansion
    # (D-5) applies only once a legitimate field-combat target anchors the
    # initiation. (Aim decides the fight; damage decides the settlement —
    # the reason names the mistake a caller of THIS entry can make.)
    if field_combat_target(actor, target) is None:
        return FieldOpeningPreview(
            False, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET, str(skill_key), ()
        )
    skill = SKILL_REGISTRY.get(skill_key)
    targets = _opening_line_up(actor, skill, target)
    # Explicit gate, first (D-4): validation deliberately supplies a
    # battlefield, so world/rules/action.py's own usable_out_of_combat gate
    # would pass. Checking here is what keeps the skill-field-availability
    # audit meaningful; it runs before the candidate battlefield exists so
    # its answer cannot be masked by anything downstream.
    if skill is not None and not skill.usable_out_of_combat:
        return FieldOpeningPreview(
            False,
            RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT,
            skill_key,
            tuple(targets),
        )
    record = _candidate_record(actor, targets, session_id=session_id)
    battlefield = reconstruct_battlefield(actor, record)
    context = _context_for(battlefield, record)
    preview = revalidate_submission(
        actor, skill_key, context, targets, scale=scale
    )
    if not preview.enabled:
        return FieldOpeningPreview(
            False, preview.reason, preview.detail, tuple(targets), battlefield, context
        )
    preflight = ActionResolver.preflight(
        ActionRequest(
            actor=actor,
            skill_key=skill_key,
            targets=targets,
            context=context,
            scale=scale,
        )
    )
    if preflight.outcome == "rejected":
        return FieldOpeningPreview(
            False,
            preflight.reason,
            preflight.detail,
            tuple(targets),
            battlefield,
            context,
        )
    return FieldOpeningPreview(True, None, None, tuple(targets), battlefield, context)


def preview_field_opening(
    actor: Any,
    skill_key: str,
    target: Any,
    scale: float = 1.0,
) -> FieldOpeningPreview:
    """Read-only availability of opening combat against ``target``.

    Applies the identical gates ``initiate_field_combat`` applies before it
    engages, against an unpersisted candidate battlefield. It never creates
    the world-clock script (the candidate session ID reads the existing clock
    or tick 0), never persists a session, never registers skip-safety, and
    never rolls. A candidate that cannot be reconstructed (for example two
    line-up participants sharing one key) reports a disabled opening with a
    stable reason instead of raising, so one awkward room never blanks a
    whole preview.
    """
    from world.rules.combat_session.records import format_session_id

    clock = read_world_clock()
    session_id = format_session_id(actor, "hostile", clock.tick if clock is not None else 0)
    try:
        return _prepare_opening(
            actor, skill_key, target, scale=scale, session_id=session_id
        )
    except CombatSessionError as error:  # observability: ignore R2: a candidate battlefield that cannot be built is a read-only disabled verdict carrying the stable session reason; the preview surface reports it, and the real initiation path still raises
        skill = SKILL_REGISTRY.get(skill_key)
        try:
            line_up = tuple(_opening_line_up(actor, skill, target))
        except Exception:  # observability: ignore R2: the line-up only decorates an already-disabled verdict; the CombatSessionError is the reported reason
            line_up = (target,)
        session_reason = str(error.args[0]) if error.args else "malformed_session"
        return FieldOpeningPreview(
            False, None, session_reason, line_up, session_reason=session_reason
        )


def initiate_field_combat(
    actor: Any,
    skill_key: str,
    target: Any,
    scale: float = 1.0,
) -> dict[str, Any]:
    """Open combat with one skill as the player's first action.

    Returns the same shape as ``submit_player_action()`` — a rejection, an
    ordinary round, or a terminal outcome — so the command layer and a
    future webclient adapter share ``combat_result.settle_to_messages()``.

    Two-part routing (D-1): whether combat starts is decided by the target
    (a living co-located hostile ``Monster``); whether the encounter is
    settled in one shot is decided inside ``submit_opening_action()`` from
    the skill's damage. A rejection at any gate costs nothing: no session,
    no resource, no roll, no world time.
    """
    preview = _prepare_opening(actor, skill_key, target, scale=scale)
    if not preview.enabled:
        return {
            "outcome": "rejected",
            "reason": preview.reason,
            "detail": preview.detail,
        }
    targets = list(preview.targets)
    battlefield = preview.battlefield
    # Freeze the dispatch BEFORE anything executes (D-9): the same
    # two-part judgement submit_opening_action() applies, computed over the
    # pre-action candidate battlefield and the concrete target keys.
    # Recomputing it after the action would read post-damage HP and could
    # name the wrong dispatch; classify_overwhelm() is state-sensitive.
    opening = "round"
    if (
        classify_overwhelm(battlefield) == battlefield.team_of(str(actor.key))
        and commanded_damage_reaches_enemy(
            battlefield, str(actor.key), skill_key, [str(t.key) for t in targets]
        )
    ):
        opening = "overwhelm"
    clock = read_world_clock()
    boundary = {
        "char": str(actor.pk),
        "room": str(actor.location.pk),
        "tick": clock.tick if clock is not None else None,
        "skill": skill_key,
        "enemy_count": len(targets),
        "opening": opening,
    }

    # The submission body's own _snapshot_round_touched() cannot cover
    # this: it snapshots active_combat at its own entry, which in this
    # flow is already AFTER engage_group() wrote the engaged record, so
    # restoring from it would reinstate the engaged session instead of the
    # pre-engagement absence. Both attributes are snapshotted here, before
    # engagement (D-7).
    active_combat_before = _attribute_snapshot(actor, "active_combat")
    dialogue_before = _attribute_snapshot(actor, "dialogue_session")
    engaged_record: CombatSessionRecord | None = None
    rejection: dict[str, Any] | None = None
    try:
        with transaction.atomic():
            # The nested atomic() inside _submit_request() degrades to a
            # savepoint, and every transaction.on_commit callback staged
            # inside it (the round-boundary event, the terminal
            # settlement's post-commit work) fires on THIS outer commit —
            # exactly as that body's own on_commit comment states.
            engaged = engage_group(actor, targets)
            engaged_record = engaged["record"]
            result = submit_opening_action(actor, skill_key, targets, scale=scale)
            if result.get("outcome") == "rejected":
                # Candidate/persisted divergence: roll the session back
                # and surface the rejection with nothing persisted.
                rejection = result
                transaction.set_rollback(True)
                # set_rollback unwinds the atomic; the shared restoration
                # below runs once the database rollback is complete, and
                # the rejection is returned after the with-block exits.
            else:
                # Staged only after the action actually executed, so a
                # rolled back or divergent initiation leaves no record.
                # Every value was snapshotted above at staging time; the
                # callback itself performs no computation (D-9).
                transaction.on_commit(
                    lambda boundary=boundary: log_info(
                        "field_combat_initiated", context=boundary
                    )
                )
    except Exception:
        # The outer transaction rolled the database back; restore the
        # in-process surfaces only now, AFTER the rollback, following the
        # cast_settlement precedent's order (never write inside the
        # transaction being unwound).
        _restore_initiation_state(
            actor, engaged_record, active_combat_before, dialogue_before
        )
        raise
    if rejection is not None:
        # The database rolled back above; reconcile the in-process surfaces
        # now, after the rollback, matching the cast_settlement precedent's
        # order (DB rollback first, then idmapper restoration).
        _restore_initiation_state(
            actor, engaged_record, active_combat_before, dialogue_before
        )
        return rejection
    return result


def _restore_initiation_state(
    actor: Any,
    engaged_record: CombatSessionRecord | None,
    active_combat_before: tuple[bool, Any],
    dialogue_before: tuple[bool, Any],
) -> None:
    """Undo everything ``engage_group()`` left outside the rollback's reach.

    A database rollback does not reach the process-memory skip-safety
    registration or Evennia's non-transaction-aware idmapper cache, so
    both attribute surfaces are restored to their pre-engagement values
    and the participants are unregistered (D-7; the idmapper reason
    ``cast_settlement._restore_settlement_state`` and
    ``combat_session._restore_round_touched`` exist for).
    """
    _restore_attribute(actor, "active_combat", active_combat_before)
    _restore_attribute(actor, "dialogue_session", dialogue_before)
    if engaged_record is not None:
        unregister_participants((*engaged_record.player_ids, *engaged_record.enemy_ids))
