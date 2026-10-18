"""Field-combat initiation: turn one exploration cast into a combat's opening seed.

Single purpose (field-combat-initiation D-2): classify the cast's target,
open the session, and seed the cast as the initiating actor's draft entry,
which the ordinary party-command path then resolves. This
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
    authorize_combat_actor,
    engage_group,
    reconstruct_battlefield,
    session_id_for,
    submit_opening_action,
)
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
    commander: Any,
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

    ``commander`` is the session owner, never the caster: a companion's
    opening is persisted under the commander's ``active_combat``, so the
    candidate must describe that same party and room.
    """
    from world.rules.party import combat_companions

    companions = [int(companion.pk) for companion in combat_companions(commander)]
    return CombatSessionRecord(
        session_id=(
            session_id
            if session_id is not None
            else session_id_for(commander, "hostile")
        ),
        mode="hostile",
        room_id=int(commander.location.pk),
        player_ids=(int(commander.pk), *companions),
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
        party_reason: The stable party-scope rejection code when the caster
            is not an authorized acting member of the commander's party
            (``reason`` is then ``None``), else ``None``.
    """

    enabled: bool
    reason: RejectReason | None
    detail: str | None
    targets: tuple[Any, ...]
    battlefield: Any = None
    context: Any = None
    session_reason: str | None = None
    party_reason: str | None = None


def _opening_line_up(commander: Any, skill: Any, target: Any) -> list[Any]:
    """The enemy line-up an opening cast engages (field-combat-initiation D-5).

    AREA opens against the whole room as an explicit concrete list (never a
    shorthand — ``commanded_damage_reaches_enemy()`` reads concrete keys);
    anything else (SINGLE, and NONE/SELF which then reject on shape) opens
    against the named monster alone. The room is the session owner's: the
    caster is authorized into that same room before the line-up is chosen.
    """
    if skill is not None and skill.target_spec is TargetSpec.AREA:
        return _room_monsters(commander)
    return [target]


def _prepare_opening(
    actor: Any,
    skill_key: str,
    target: Any,
    scale: float = 1.0,
    *,
    session_id: str | None = None,
    commander: Any | None = None,
) -> FieldOpeningPreview:
    """Run every pre-mutation initiation gate in the execution order.

    Shared verbatim by ``initiate_field_combat`` (which then engages) and
    the read-only ``preview_field_opening`` (which stops here), so a preview
    can never advertise an opening the initiation would refuse. Nothing here
    persists, registers, or advances anything: the candidate record is
    reconstructed, then dropped.

    ``actor`` is the caster; ``commander`` is the authenticated session owner
    (default: the commander behind ``actor``). The candidate battlefield, its
    room and its player side belong to the commander, while every caster-side
    gate — party membership, presence, eligibility, owned skill, resources and
    preflight — runs against ``actor``. The caster is re-authorized here,
    before any clock or candidate work, so a forged, absent, knocked-out or
    stale caster is refused without touching the clock, a session or a roll.
    """
    if commander is None:
        from world.rules.party_scope import resolve_commander

        commander = resolve_commander(actor)
    # The initiation API enforces its own target contract: an AREA skill's
    # line-up is chosen from the room, so without this check a direct caller
    # could open a fight and fire the room-wide action while nominally
    # aiming at nothing (self, an NPC, an absent monster). AREA expansion
    # (D-5) applies only once a legitimate field-combat target anchors the
    # initiation. (Aim decides the fight; damage decides the settlement —
    # the reason names the mistake a caller of THIS entry can make.)
    if field_combat_target(commander, target) is None:
        return FieldOpeningPreview(
            False, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET, str(skill_key), ()
        )
    skill = SKILL_REGISTRY.get(skill_key)
    targets = _opening_line_up(commander, skill, target)
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
    # Party authority before any clock or candidate work: the caster must be
    # the commander or an effective companion present in the commander's room,
    # and (for a companion) able to act. Raises the shared ``PartyScopeError``
    # codes instead of spending a session or a roll on a forged identity.
    from world.rules.party_scope import PURPOSE_ACT, authorize_member

    caster = authorize_member(
        commander, getattr(actor, "pk", None), PURPOSE_ACT, anchor=actor
    )
    record = _candidate_record(commander, targets, session_id=session_id)
    battlefield = reconstruct_battlefield(commander, record)
    # The candidate already lists the commander's player side; this re-checks
    # the caster against it with the same guard the persisted submission uses,
    # so the preview and the initiation can never disagree about the caster.
    authorize_combat_actor(commander, caster, record, battlefield)
    context = _context_for(battlefield, record)
    preview = revalidate_submission(caster, skill_key, context, targets, scale=scale)
    if not preview.enabled:
        return FieldOpeningPreview(
            False, preview.reason, preview.detail, tuple(targets), battlefield, context
        )
    preflight = ActionResolver.preflight(
        ActionRequest(
            actor=caster,
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
    *,
    commander: Any | None = None,
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

    ``actor`` is the caster and ``commander`` the authenticated session owner
    (default: the commander behind ``actor``). A caster that party authority
    refuses reports a disabled opening carrying the stable party reason
    (``party_reason``) instead of raising, exactly as the candidate-battlefield
    failures do; the real initiation path still raises that same rejection.
    """
    from world.rules.combat_session.records import format_session_id
    from world.rules.party_scope import PartyScopeError, resolve_commander

    if commander is None:
        try:
            commander = resolve_commander(actor)
        except PartyScopeError as error:  # observability: ignore R2: the party refusal is the reported disabled verdict, not a swallowed failure
            return FieldOpeningPreview(
                False, None, None, (target,), party_reason=error.reason
            )
    clock = read_world_clock()
    session_id = format_session_id(
        commander, "hostile", clock.tick if clock is not None else 0
    )
    try:
        return _prepare_opening(
            actor,
            skill_key,
            target,
            scale=scale,
            session_id=session_id,
            commander=commander,
        )
    except PartyScopeError as error:  # observability: ignore R2: the party refusal is the reported disabled verdict, not a swallowed failure
        # Party authority is a pre-mutation verdict like the candidate build:
        # report it as a disabled opening rather than blanking the preview.
        return FieldOpeningPreview(
            False, None, None, (target,), party_reason=error.reason
        )
    except CombatSessionError as error:  # observability: ignore R2: a candidate battlefield that cannot be built is a read-only disabled verdict carrying the stable session reason; the preview surface reports it, and the real initiation path still raises
        skill = SKILL_REGISTRY.get(skill_key)
        try:
            line_up = tuple(_opening_line_up(commander, skill, target))
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
    *,
    commander: Any | None = None,
) -> dict[str, Any]:
    """Open combat with one skill as the player's opening draft selection.

    Returns the same shape as ``submit_player_action()`` — a rejection, a
    waiting draft, an ordinary round, or a terminal outcome — so the command
    layer and the webclient adapter share ``combat_result.settle_to_messages()``.

    Routing by target alone: combat starts when the target is a living
    co-located hostile ``Monster``, whatever the skill does. The named skill
    is persisted as the initiating actor's draft entry together with the
    encounter's opening-order policy, and the fight then follows ordinary
    party-command semantics: no action and no world time before every
    required actor has confirmed, and never a compressed settlement. A
    rejection at any gate costs nothing: no session, no resource, no roll,
    no world time.

    ``actor`` is the caster and ``commander`` the authenticated session owner
    (default: the commander behind ``actor``, which is the actor itself for the
    commander). A companion's opening is the commander's encounter: the
    session, its active-session check, its room and its rollback snapshots are
    keyed on the commander, while the opening draft entry is seeded for the
    caster and the caster acts first. ``commander`` is trusted internal
    context threaded from the party boundary (``cast_as_member``), never a
    caller-supplied identity.
    """
    if commander is None:
        from world.rules.party_scope import resolve_commander

        commander = resolve_commander(actor)
    preview = _prepare_opening(
        actor, skill_key, target, scale=scale, commander=commander
    )
    if not preview.enabled:
        return {
            "outcome": "rejected",
            "reason": preview.reason,
            "detail": preview.detail,
        }
    targets = list(preview.targets)
    clock = read_world_clock()
    boundary = {
        "char": str(commander.pk),
        "caster": str(actor.pk),
        "room": str(commander.location.pk),
        "tick": clock.tick if clock is not None else None,
        "skill": skill_key,
        "enemy_count": len(targets),
        # Filled in from the committed outcome below, before the callback is
        # staged: the seed either waits for remaining actors ("draft") or,
        # when it completed a solo draft, ran one ordinary round ("round").
        "opening": "round",
    }

    # The submission body's own _snapshot_round_touched() cannot cover
    # this: it snapshots active_combat at its own entry, which in this
    # flow is already AFTER engage_group() wrote the engaged record, so
    # restoring from it would reinstate the engaged session instead of the
    # pre-engagement absence. Both attributes are snapshotted here, before
    # engagement (D-7). The session lives on the commander; a distinct caster
    # only ever loses dialogue state to the engagement, so that is the one
    # extra surface snapshotted for it.
    active_combat_before = _attribute_snapshot(commander, "active_combat")
    dialogue_before = _attribute_snapshot(commander, "dialogue_session")
    caster_dialogue_before: tuple[bool, Any] | None = None
    if actor is not commander:
        caster_dialogue_before = _attribute_snapshot(actor, "dialogue_session")
    engaged_record: CombatSessionRecord | None = None
    rejection: dict[str, Any] | None = None
    try:
        with transaction.atomic():
            # The nested atomic() inside _submit_request() degrades to a
            # savepoint, and every transaction.on_commit callback staged
            # inside it (the round-boundary event, the terminal
            # settlement's post-commit work) fires on THIS outer commit —
            # exactly as that body's own on_commit comment states.
            # Engagement persists the encounter's opening-order policy with
            # the session, so the initiating actor keeps the first action of
            # the first complete round while companions still have to choose.
            engaged = engage_group(
                commander, targets, opening_first_actor=str(actor.key)
            )
            engaged_record = engaged["record"]
            if actor is not commander:
                # Hostility ends a conversation for every participant, not
                # only for the session owner (webclient-align-07).
                from world.rules.dialogue import clear_dialogue_session

                clear_dialogue_session(actor)
            # ``nested=True``: this outer ``transaction.atomic()`` owns the
            # whole unit, so the seed's own durable boundary degrades to a
            # savepoint of it instead of raising (writer.durable_combat_atomic).
            result = submit_opening_action(
                commander,
                skill_key,
                targets,
                scale=scale,
                nested=True,
                commanded_actor=actor,
            )
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
                # The dispatch actually taken is read from the committed
                # outcome -- a waiting seed or one resolved ordinary round --
                # so the value is settled here, at staging time; the callback
                # itself performs no computation (D-9).
                boundary["opening"] = (
                    "draft" if result.get("outcome") == "draft" else "round"
                )
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
            commander,
            actor,
            engaged_record,
            active_combat_before,
            dialogue_before,
            caster_dialogue_before,
        )
        raise
    if rejection is not None:
        # The database rolled back above; reconcile the in-process surfaces
        # now, after the rollback, matching the cast_settlement precedent's
        # order (DB rollback first, then idmapper restoration).
        _restore_initiation_state(
            commander,
            actor,
            engaged_record,
            active_combat_before,
            dialogue_before,
            caster_dialogue_before,
        )
        return rejection
    return result


def _restore_initiation_state(
    commander: Any,
    caster: Any,
    engaged_record: CombatSessionRecord | None,
    active_combat_before: tuple[bool, Any],
    dialogue_before: tuple[bool, Any],
    caster_dialogue_before: tuple[bool, Any] | None = None,
) -> None:
    """Undo everything ``engage_group()`` left outside the rollback's reach.

    A database rollback does not reach the process-memory skip-safety
    registration or Evennia's non-transaction-aware idmapper cache, so
    both attribute surfaces are restored to their pre-engagement values
    and the participants are unregistered (D-7; the idmapper reason
    ``cast_settlement._restore_settlement_state`` and
    ``combat_session._restore_round_touched`` exist for). The session
    attribute belongs to the commander; a distinct caster only carries the
    dialogue snapshot the engagement cleared.
    """
    _restore_attribute(commander, "active_combat", active_combat_before)
    _restore_attribute(commander, "dialogue_session", dialogue_before)
    if caster_dialogue_before is not None:
        _restore_attribute(caster, "dialogue_session", caster_dialogue_before)
    if engaged_record is not None:
        unregister_participants((*engaged_record.player_ids, *engaged_record.enemy_ids))
