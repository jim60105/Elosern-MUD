"""Round mechanics: submissions, round bookkeeping, and the round transaction.

Active-session submissions edit one persistent party draft. Its final valid
confirmation commits admission before resolving one ordinary round. Effects,
metadata, draft consumption and terminal settlement share the round transaction.
The exploration opening is one such submission: it seeds the initiating actor's
entry and waits for every remaining required actor, so no entry point
compresses an interactive encounter.
"""

from dataclasses import replace
from typing import Any

from world.observability import log_info
from world.rules import combat
from world.rules.action import ActionRequest, ActionResolver, _stored_trait_value
from world.rules.action_preview import revalidate_submission
from world.rules.combat import Battlefield, ExecutionScopeBase, run_round
from world.rules.combat_beats import RoundRecord, capture_round_hp
from world.rules.clock import read_world_clock
from world.rules.combat_session.battlefield import (
    _commandable_required_actors,
    _context_for,
    _session_policy,
    authorize_combat_actor,
    reconstruct_battlefield,
)
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.writer import (
    durable_combat_atomic,
    serialized_combat_write,
)
from world.rules.combat_session.policies import _party_round_provider
from world.rules.combat_session.lifecycle import _persist
from world.rules.combat_session.records import (
    CombatSessionRecord,
    read_session,
    read_session_uncached,
    read_last_combat_receipt,
    write_last_combat_receipt,
)
from world.rules.combat_session.scans import (
    _scan_friendly_fire,
    _scan_sexual_coercion,
)
from world.rules.combat_session.settlement import _continue_or_settle
from world.rules.combat_session.snapshot import (
    _restore_exam_host,
    _restore_round_touched,
    _snapshot_exam_host,
    _snapshot_party_surfaces,
    _snapshot_round_touched,
)
from django.db import transaction
from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort
from world.rules.items import ItemUseRequest, preflight_item_use
from world.rules.progression import (
    restore_practice_dedupe,
    snapshot_practice_dedupe,
)
from world.rules.skip_safety import register_active_battlefield


def _knocked_out_ids(logs, battlefield) -> tuple[int, ...]:
    """Return the dbrefs of entities marked knocked out by the round.

    Merges the round's ``target_knocked_out`` log identities with the
    battlefield's in-round ``knocked_out`` markings, so exam-flag knockouts
    (persisted from logs only) and per-entity companion knockouts (marked at
    damage-commit time) both survive the round-end persistence.
    """
    knocked = set()
    for event_log in logs:
        for entry in event_log.entries:
            if entry.kind != "target_knocked_out":
                continue
            target_id = entry.data.get("target_id")
            if isinstance(target_id, int):
                knocked.add(target_id)
    for key in battlefield.knocked_out:
        entity = battlefield.roster.get(key)
        if entity is not None:
            knocked.add(int(entity.pk))
    return tuple(sorted(knocked))


def _primary_opponent_id(battlefield: Battlefield, record: CombatSessionRecord) -> Any:
    """Return one deterministic opponent identity for a round boundary event.

    The durable record's ``enemy_ids`` are session-stable dbrefs (never empty
    for an engaged session); the lowest pk labels multi-foe encounters
    deterministically. A record without enemies is unexpected and reported as
    ``None``.
    """
    if record.enemy_ids:
        return min(record.enemy_ids)
    return None


def _current_tick() -> int | None:
    """Read the world-clock tick for a boundary event without creating state.

    Uses the non-creating ``read_world_clock`` accessor: telemetry must never
    create the clock Script (``get_world_clock`` would); an absent clock is
    reported as ``None``.
    """
    clock = read_world_clock()
    return clock.tick if clock is not None else None


@serialized_combat_write
def submit_player_action(
    actor: Any,
    skill_key: str,
    targets_or_shorthand: list[Any] | str,
    scale: float = 1.0,
    *,
    commanded_actor: Any | None = None,
) -> dict[str, Any]:
    """Admit one player or commanded companion skill selection into the draft.

    ``actor`` is the authenticated commander. ``commanded_actor`` is the
    authorized action actor (defaulting to ``actor``).

    ``targets_or_shorthand`` is either a concrete list of live participant
    objects or one approved AREA shorthand (``all-enemies``, ``all-allies``,
    ``all``). Player-facing NONE and SELF input must be an empty list; SELF is
    bound to the actor inside the rules layer. ``scale`` is the optional
    freeform magnitude modifier (default ``1.0``), threaded into the preview,
    preflight, and the round's ``ActionRequest``; a scale the deterministic
    gate forbids rejects before initiative and consumes no round or world
    time. The facade revalidates the
    submitted target value through the shared side-effect-free preview, runs
    ``ActionResolver.preflight()``, and only then admits the entry into the
    persistent draft under the current session/revision/draft-version CAS.
    Anything short of the confirmation that completes every required actor
    returns ``outcome="draft"`` with per-member reselection progress and
    resolves nothing; that final confirmation resolves exactly one ordinary
    round and never compresses -- whatever ``classify_overwhelm()`` decides
    for the session. No interactive entry point compresses
    (party-combat-opening-routing). A rejection returns before initiative and
    consumes no round or world time.
    """
    record, battlefield, request, rejection = _preflight_skill_submission(
        submit_player_action, actor, skill_key, targets_or_shorthand, scale=scale, commanded_actor=commanded_actor
    )
    if rejection is not None:
        return rejection
    effective_actor = actor if commanded_actor is None else commanded_actor
    targets = targets_or_shorthand if isinstance(targets_or_shorthand, str) else [
        int(target.pk) for target in targets_or_shorthand
    ]
    return confirm_actor_command(
        actor, record.session_id, record.round_revision, record.draft_version,
        int(effective_actor.pk),
        {"kind": "skill", "payload": {
            "skill_key": skill_key, "targets_or_shorthand": targets, "scale": scale,
        }},
    )


def _preflight_skill_submission(
    entry: Any,
    actor: Any,
    skill_key: str,
    targets_or_shorthand: list[Any] | str,
    scale: float = 1.0,
    *,
    commanded_actor: Any | None = None,
) -> tuple[CombatSessionRecord, Battlefield, "ActionRequest | None", "dict[str, Any] | None"]:
    """Shared session read, reconstruction, preview, and resolver preflight.

    ``submit_player_action()`` and ``submit_opening_action()`` run the
    identical side-effect-free validation through this one body (combat-
    session-opening-dispatch D-2): session presence, reconstruction
    freshness, recovery validity, target-shape and roster-membership
    rejection, ``revalidate_submission()``, and ``ActionResolver.preflight()``.
    Returns ``(record, battlefield, request, rejection)``; ``rejection`` is
    the caller-returnable rejection dict when validation stopped the
    submission, else ``None`` (and then ``request`` is built and
    preflight-approved). Raises ``TypeError`` for a non-list/non-shorthand
    target value and ``CombatSessionError`` for a missing session, invalid
    recovery, or an off-roster target, naming the public ``entry`` in the
    shape message.
    """
    name = getattr(entry, "__name__", str(entry))
    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    battlefield = reconstruct_battlefield(actor, record)
    if _stored_trait_value(actor.traits.hp) <= 0:
        raise CombatSessionError(SessionReason.INVALID_RECOVERY)
    effective_actor = actor if commanded_actor is None else commanded_actor
    authorize_combat_actor(actor, effective_actor, record, battlefield)
    if not isinstance(targets_or_shorthand, (list, str)):
        raise TypeError(f"{name} requires an explicit target list or shorthand")
    if not isinstance(targets_or_shorthand, str) and not all(
        str(target.key) in battlefield.roster
        for target in targets_or_shorthand
    ):
        raise CombatSessionError(SessionReason.NOT_PRESENT)

    context = _context_for(battlefield, record)
    preview = revalidate_submission(
        effective_actor, skill_key, context, targets_or_shorthand, scale=scale
    )
    if not preview.enabled:
        return (
            record,
            battlefield,
            None,
            {
                "outcome": "rejected",
                "reason": preview.reason,
                "detail": preview.detail,
            },
        )

    request = ActionRequest(
        actor=effective_actor,
        skill_key=skill_key,
        targets=targets_or_shorthand,
        context=context,
        scale=scale,
    )
    preflight = ActionResolver.preflight(request)
    if preflight.outcome == "rejected":
        return (
            record,
            battlefield,
            None,
            {
                "outcome": "rejected",
                "reason": preflight.reason,
                "detail": preflight.detail,
            },
        )
    return record, battlefield, request, None


@serialized_combat_write
def submit_opening_action(
    actor: Any,
    skill_key: str,
    targets: list[Any],
    scale: float = 1.0,
    *,
    nested: bool = False,
) -> dict[str, Any]:
    """Seed the exploration opening's selection as the initiating draft entry.

    The canonical opening path ``field-combat-initiation``'s routing drives.
    Runs the identical session read, reconstruction,
    ``revalidate_submission()`` and ``ActionResolver.preflight()`` as
    ``submit_player_action()``, then admits the selection into the same
    persistent party draft and, only when that admission leaves no required
    actor unconfirmed, resolves exactly one ordinary round. A multi-actor
    opening therefore returns ``outcome="draft"`` with per-member progress,
    running no action and consuming no round or world time while companions
    still have to choose; no interactive opening ever compresses.
    ``opening_first_actor`` is already durable on the session (written by
    ``engage_group()``), so the initiating actor keeps the first action of
    that first complete round without any caller-supplied override.

    Skills only -- no item request may reach this entry. Only a concrete
    list of participant objects is accepted: the AREA line-up is expanded by
    the initiation before it seeds, so an approved shorthand
    (``all-enemies``/``all-allies``/``all``) is a caller error and is
    rejected before initiative. Off-roster targets reject exactly as
    ``submit_player_action()`` does.
    """
    if isinstance(targets, str):
        # Rejected before any admission, but only after the session-presence
        # check so a caller with no session still gets NO_ACTIVE_SESSION,
        # exactly as submit_player_action reports it.
        if read_session(actor) is None:
            raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
        raise TypeError(
            "submit_opening_action requires a concrete target list; the "
            f"shorthand {targets!r} cannot seed an opening entry"
        )
    record, battlefield, request, rejection = _preflight_skill_submission(
        submit_opening_action, actor, skill_key, targets, scale=scale
    )
    if rejection is not None:
        return rejection
    return confirm_actor_command(
        actor,
        record.session_id,
        record.round_revision,
        record.draft_version,
        int(actor.pk),
        {"kind": "skill", "payload": {
            "skill_key": skill_key,
            "targets_or_shorthand": [int(target.pk) for target in targets],
            "scale": scale,
        }},
        nested=nested,
    )


@serialized_combat_write
def submit_player_item_use(
    actor: Any, item_key: str, *, target: Any | None = None, commanded_actor: Any | None = None
) -> dict[str, Any]:
    """Admit one commanded actor's held-item selection into the draft.

    ``actor`` is the authenticated commander. ``commanded_actor`` is the
    authorized action actor (defaulting to ``actor``).

    The facade revalidates the request through the shared item preflight
    with combat allowed, and only then admits the entry under the same
    session/revision/draft-version CAS as ``submit_player_action``, exactly
    like a skill selection: a consumable is an ordinary selection and no
    interactive dispatch compresses. A rejection returns before initiative
    and consumes no round or world time; the item is consumed exactly once
    when the complete draft's final confirmation resolves the round, on the
    commander's turn, and its journal is merged into the session's outer
    rollback safety net.

    ``target`` is the player's one explicit choice (add-item-effect-targeting
    design D1): the session's battlefield context resolves it — and every
    group scope — through the same roster validators a skill's targets pass;
    ``run_round`` rebuilds the identical context from the battlefield itself.
    """
    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    battlefield = reconstruct_battlefield(actor, record)
    if _stored_trait_value(actor.traits.hp) <= 0:
        raise CombatSessionError(SessionReason.INVALID_RECOVERY)
    effective_actor = actor if commanded_actor is None else commanded_actor
    authorize_combat_actor(actor, effective_actor, record, battlefield)
    if not isinstance(item_key, str):
        raise TypeError("submit_player_item_use requires an item key string")
    preflight = preflight_item_use(
        ItemUseRequest(actor=effective_actor, item_key=item_key, target=target),
        in_combat=True,
        context=_context_for(battlefield, record),
    )
    if not preflight.allowed:
        return {
            "outcome": "rejected",
            "reason": preflight.reason.value if preflight.reason else None,
            "detail": preflight.detail,
        }
    return confirm_actor_command(
        actor, record.session_id, record.round_revision, record.draft_version,
        int(effective_actor.pk),
        {"kind": "item", "payload": {
            "item_key": item_key, "target_id": int(target.pk) if target is not None else None,
        }},
    )


def _eligible_taunt_target(
    battlefield: Battlefield,
    record: CombatSessionRecord,
    target_id: Any,
) -> Any | None:
    """Return one Taunt declaration's living eligible enemy, or ``None``.

    A Taunt names exactly one living enemy on the opposing team. Admission and
    preflight share this predicate -- and the battlefield's own capability rule
    (:meth:`Battlefield.is_eligible`) -- so an absent, fled, knocked-out or
    defeated participant is never a legal declaration target, and the two
    boundaries cannot drift.
    """
    target = next(
        (
            entity
            for entity in battlefield.roster.values()
            if getattr(entity, "pk", None) == target_id
        ),
        None,
    )
    if target is None or int(target.pk) not in record.enemy_ids:
        return None
    if not battlefield.is_eligible(str(target.key)):
        return None
    return target


def preflight_draft_entries(
    commander: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
) -> dict[str, Any]:
    """Pure all-command preflight returning retained valid entries and member-specific reselection reasons.

    Does NOT roll dice, apply tactical effects, deduct resources, consume items, run upkeep, or advance time.

    The required set is the COMMANDABLE one: a participant the commander may no
    longer command (a companion that left the party, moved away or was
    dismissed) is dropped from membership instead of reported as an unfillable
    reselection, so a changed roster pauses collection only until the next
    explicit confirmation re-derives it.
    """
    required_actors = _commandable_required_actors(commander, record, battlefield)
    if not required_actors:
        membership_changed = bool(record.confirmed_actors) and (record.confirmed_actors != ())
        return {
            "is_complete": False,
            "empty_required": True,
            "reason": "no_eligible_actors",
            "required_actors": (),
            "valid_entries": {},
            "reselection_reasons": {},
            "missing_actors": (),
            "needs_reselection": False,
            "membership_changed": membership_changed,
        }

    valid_entries: dict[int, dict[str, Any]] = {}
    reselection_reasons: dict[int, dict[str, Any]] = {}
    context = _context_for(battlefield, record)

    draft_entries = record.draft_entries or {}
    for actor_id, entry in draft_entries.items():
        if actor_id not in required_actors:
            # No longer required (e.g. knocked out / fled / incapacitated)
            continue
        actor_obj = next((e for e in battlefield.roster.values() if getattr(e, "pk", None) == actor_id), None)
        if actor_obj is None:
            reselection_reasons[actor_id] = {"reason": "actor_missing", "detail": "actor not on battlefield"}
            continue
        try:
            authorize_combat_actor(commander, actor_obj, record, battlefield)
        except CombatSessionError as auth_err:  # observability: ignore R2: expected authorization rejection is returned as a member-specific reselection reason
            reselection_reasons[actor_id] = {
                "reason": "forbidden_actor",
                "detail": str(auth_err.args[0]),
            }
            continue

        kind = entry.get("kind")
        payload = entry.get("payload", {})
        if kind == "skill":
            skill_key = payload.get("skill_key")
            targets_or_shorthand = payload.get("targets_or_shorthand")
            scale = float(payload.get("scale", 1.0))
            # Map integer dbrefs back to live participant objects if list
            if isinstance(targets_or_shorthand, (list, tuple)) or hasattr(targets_or_shorthand, "__iter__") and not isinstance(targets_or_shorthand, str):
                resolved_targets = []
                missing_target = False
                for tid in targets_or_shorthand:
                    t_obj = next((e for e in battlefield.roster.values() if getattr(e, "pk", None) == tid), None)
                    if t_obj is None:
                        missing_target = True
                        break
                    resolved_targets.append(t_obj)
                if missing_target:
                    reselection_reasons[actor_id] = {"reason": "target_missing", "detail": "target not on battlefield"}
                    continue
                effective_targets = resolved_targets
            else:
                effective_targets = targets_or_shorthand

            preview = revalidate_submission(actor_obj, skill_key, context, effective_targets, scale=scale)
            if not preview.enabled:
                reselection_reasons[actor_id] = {"reason": preview.reason, "detail": preview.detail}
            else:
                valid_entries[actor_id] = entry
        elif kind == "item":
            item_key = payload.get("item_key")
            target_id = payload.get("target_id")
            target_obj = None
            if target_id is not None:
                target_obj = next((e for e in battlefield.roster.values() if getattr(e, "pk", None) == target_id), None)
                if target_obj is None:
                    reselection_reasons[actor_id] = {"reason": "target_missing", "detail": "item target not on battlefield"}
                    continue
            preflight = preflight_item_use(
                ItemUseRequest(actor=actor_obj, item_key=item_key, target=target_obj),
                in_combat=True,
                context=context,
            )
            if not preflight.allowed:
                reselection_reasons[actor_id] = {
                    "reason": preflight.reason.value if preflight.reason else "item_rejected",
                    "detail": preflight.detail,
                }
            else:
                valid_entries[actor_id] = entry
        elif kind == "tactical":
            tactical_key = payload.get("tactical_key")
            if tactical_key not in {"defend", "dodge", "taunt"}:
                reselection_reasons[actor_id] = {"reason": "invalid_tactical_key", "detail": f"unsupported tactical action: {tactical_key}"}
                continue
            target_id = payload.get("target_id")
            if tactical_key == "taunt":
                if target_id is None:
                    reselection_reasons[actor_id] = {"reason": "target_required", "detail": "taunt requires enemy target"}
                    continue
                if _eligible_taunt_target(battlefield, record, target_id) is None:
                    reselection_reasons[actor_id] = {"reason": "target_invalid", "detail": "taunt target is not a living enemy"}
                    continue
            valid_entries[actor_id] = entry
        else:
            reselection_reasons[actor_id] = {"reason": "unknown_kind", "detail": f"unknown command kind {kind}"}

    missing_actors = tuple(aid for aid in required_actors if aid not in valid_entries)
    # Membership change guard:
    # If required_actors differs from record.confirmed_actors (and confirmed_actors was set),
    # a changed required set requires fresh explicit confirmation rather than executing an old draft.
    membership_changed = bool(record.confirmed_actors) and (tuple(required_actors) != tuple(record.confirmed_actors))
    is_complete = (len(missing_actors) == 0 and len(reselection_reasons) == 0 and not membership_changed)

    return {
        "is_complete": is_complete,
        "empty_required": False,
        "required_actors": required_actors,
        "valid_entries": valid_entries,
        "reselection_reasons": reselection_reasons,
        "missing_actors": missing_actors,
        "membership_changed": membership_changed,
    }


@serialized_combat_write
def confirm_actor_command(
    commander: Any,
    session_id: str,
    round_revision: int,
    draft_version: int,
    actor_id: int,
    command: dict[str, Any],
    *,
    nested: bool = False,
) -> dict[str, Any]:
    """Commit one draft edit, then resolve the round once the draft completes.

    Runs entirely under the shared combat writer. The edit is admitted in
    its own durable transaction against the caller's
    session/revision/draft-version token; whenever the admitted draft does
    not cover every required actor, the result is ``outcome="draft"`` (or
    ``"rejected"`` for an unadmitted edit) carrying per-member reselection
    progress and resolving nothing. Only the edit that completes the draft
    proceeds into the durable round transaction, so a duplicate, stale or
    concurrent confirmation can never resolve the same revision twice.
    """
    result = _admit_actor_command(
        commander,
        session_id,
        round_revision,
        draft_version,
        actor_id,
        command,
        nested=nested,
    )
    if not result.get("ok") or not result.get("is_complete"):
        result["outcome"] = "draft" if result.get("ok") else "rejected"
        return result
    record = read_session_uncached(commander)
    battlefield = reconstruct_battlefield(commander, record)
    return _submit_request(commander, record, battlefield, nested=nested)


def _admit_actor_command(
    commander: Any,
    session_id: str,
    round_revision: int,
    draft_version: int,
    actor_id: int,
    command: dict[str, Any],
    *,
    nested: bool = False,
) -> dict[str, Any]:
    """Admit or replace one actor's command in the persistent session draft under deterministic CAS."""
    combat_snapshot = attribute_snapshot(commander, "active_combat")
    try:
        with durable_combat_atomic(nested=nested):
            record = read_session_uncached(commander)
            if record is None:
                receipt = read_last_combat_receipt(commander)
                if receipt is not None and receipt.get("session_id") == session_id:
                    return {
                        "ok": False,
                        "reason": "already_committed",
                        "receipt": receipt,
                        "session_id": session_id,
                        "round_revision": round_revision,
                    }
                raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
            if record.session_id != session_id:
                raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
            if record.round_revision != round_revision:
                return {
                    "ok": False,
                    "reason": "stale_round_revision",
                    "current_round_revision": record.round_revision,
                    "draft_version": record.draft_version,
                    "session_id": record.session_id,
                    "receipt": read_last_combat_receipt(commander),
                }
            if record.draft_version != draft_version:
                # Stale edit CAS rejection
                battlefield = reconstruct_battlefield(commander, record)
                progress = preflight_draft_entries(commander, record, battlefield)
                return {
                    "ok": False,
                    "reason": "stale_draft_version",
                    "current_draft_version": record.draft_version,
                    "round_revision": record.round_revision,
                    "session_id": record.session_id,
                    "progress": progress,
                }

            battlefield = reconstruct_battlefield(commander, record)
            actor_obj = next((e for e in battlefield.roster.values() if getattr(e, "pk", None) == actor_id), None)
            if actor_obj is None:
                raise CombatSessionError(SessionReason.FORBIDDEN_ACTOR)
            authorize_combat_actor(commander, actor_obj, record, battlefield)

            # Validate the proposed new command
            context = _context_for(battlefield, record)
            kind = command.get("kind")
            payload = command.get("payload", {})
            if kind == "skill":
                skill_key = payload.get("skill_key")
                targets_or_shorthand = payload.get("targets_or_shorthand")
                scale = float(payload.get("scale", 1.0))
                if isinstance(targets_or_shorthand, (list, tuple)) or hasattr(targets_or_shorthand, "__iter__") and not isinstance(targets_or_shorthand, str):
                    resolved_targets = []
                    for tid in targets_or_shorthand:
                        t_obj = next((e for e in battlefield.roster.values() if getattr(e, "pk", None) == tid), None)
                        if t_obj is None:
                            return {"ok": False, "reason": "target_missing", "detail": "target not on battlefield"}
                        resolved_targets.append(t_obj)
                    effective_targets = resolved_targets
                else:
                    effective_targets = targets_or_shorthand
                preview = revalidate_submission(actor_obj, skill_key, context, effective_targets, scale=scale)
                if not preview.enabled:
                    return {"ok": False, "reason": preview.reason, "detail": preview.detail}
            elif kind == "item":
                item_key = payload.get("item_key")
                target_id = payload.get("target_id")
                target_obj = None
                if target_id is not None:
                    target_obj = next((e for e in battlefield.roster.values() if getattr(e, "pk", None) == target_id), None)
                    if target_obj is None:
                        return {"ok": False, "reason": "target_missing", "detail": "item target not on battlefield"}
                preflight = preflight_item_use(
                    ItemUseRequest(actor=actor_obj, item_key=item_key, target=target_obj),
                    in_combat=True,
                    context=context,
                )
                if not preflight.allowed:
                    return {
                        "ok": False,
                        "reason": preflight.reason.value if preflight.reason else "item_rejected",
                        "detail": preflight.detail,
                    }
            elif kind == "tactical":
                tactical_key = payload.get("tactical_key")
                if tactical_key not in {"defend", "dodge", "taunt"}:
                    return {"ok": False, "reason": "invalid_tactical_key", "detail": f"unknown {tactical_key}"}
                if tactical_key == "taunt":
                    target_id = payload.get("target_id")
                    if _eligible_taunt_target(battlefield, record, target_id) is None:
                        return {"ok": False, "reason": "target_invalid", "detail": "taunt requires a living enemy target"}
            else:
                return {"ok": False, "reason": "unknown_kind", "detail": f"unknown command kind {kind}"}

            # Now run all-command preflight on current draft to find valid entries and reselection reasons
            pre = preflight_draft_entries(commander, record, battlefield)
            new_valid = dict(pre["valid_entries"])
            # Admit / replace the newly confirmed command
            new_valid[actor_id] = command
            new_reselection = {aid: reason for aid, reason in pre["reselection_reasons"].items() if aid != actor_id}
            # Always the preflight's own SET, never the eligibility-only
            # roster: the preflight's set is the commandable one, and this
            # record's ``confirmed_actors`` is what the next preflight compares
            # against to detect a changed roster. Storing an uncommandable
            # member here would leave the session uncompletable.
            required_actors = pre["required_actors"]

            new_record = replace(
                record,
                draft_version=record.draft_version + 1,
                draft_entries=new_valid,
                confirmed_actors=required_actors,
            )
            _persist(commander, new_record)

            missing = tuple(aid for aid in required_actors if aid not in new_valid)
            is_complete = (len(missing) == 0 and len(new_reselection) == 0 and bool(required_actors))

            return {
                "ok": True,
                "session_id": new_record.session_id,
                "round_revision": new_record.round_revision,
                "draft_version": new_record.draft_version,
                "draft_entries": new_valid,
                "required_actors": required_actors,
                "missing_actors": missing,
                "reselection_reasons": new_reselection,
                "is_complete": is_complete,
                "empty_required": pre.get("empty_required", False),
            }
    except Exception:
        restore_attribute_best_effort(commander, "active_combat", combat_snapshot)
        raise


def _draft_requests(record: CombatSessionRecord, battlefield: Battlefield) -> dict[int, combat.RoundRequest]:
    """Bind persisted selections to this round's authoritative roster.

    A ``defend``/``dodge``/``taunt`` draft entry is a round-start tactical
    declaration, not an ordinary action: it is activated through
    ``run_round(tactical_declarations=...)``/``run_round(taunt_declarations=...)``
    and its actor consumes its selected action by receiving no request here
    (the party provider returns ``None`` for it), so this binding deliberately
    skips it. Every other command kind without a resolver still fails loudly
    rather than silently consuming an action.
    """
    entities = {int(entity.pk): entity for entity in battlefield.roster.values()}
    context = _context_for(battlefield, record)
    requests = {}
    for actor_id, entry in (record.draft_entries or {}).items():
        entity = entities[actor_id]
        payload = entry["payload"]
        if entry["kind"] == "skill":
            targets = payload["targets_or_shorthand"]
            if not isinstance(targets, str):
                targets = [entities[target_id] for target_id in targets]
            requests[actor_id] = ActionRequest(
                entity, payload["skill_key"], targets, context,
                scale=float(payload.get("scale", 1.0)),
            )
        elif entry["kind"] == "item":
            requests[actor_id] = ItemUseRequest(
                actor=entity, item_key=payload["item_key"],
                target=entities.get(payload.get("target_id")),
            )
        elif (
            entry["kind"] == "tactical"
            and payload.get("tactical_key") in {"defend", "dodge", "taunt"}
        ):
            # Round-start declaration: activated by run_round, not an action.
            continue
        else:
            raise ValueError(f"No round resolver registered for command kind {entry['kind']}")
    return requests


def _draft_tactical_declarations(
    record: CombatSessionRecord, battlefield: Battlefield
) -> dict[str, str]:
    """Return the round's accepted allied Defend/Dodge declarations by roster key.

    A pure projection of the persistent draft: each tactical entry whose key
    is ``defend`` or ``dodge`` contributes the bound actor's roster key and its
    verb. Taunt is a different declaration shape (:func:`_draft_taunt_declarations`),
    so it contributes nothing here; every tactical key is still resolved by
    :func:`_draft_requests`, which raises for an unknown one.
    """
    keys_by_actor = {
        int(entity.pk): str(entity.key) for entity in battlefield.roster.values()
    }
    declarations: dict[str, str] = {}
    for actor_id, entry in (record.draft_entries or {}).items():
        if entry["kind"] != "tactical":
            continue
        tactical_key = entry["payload"].get("tactical_key")
        if tactical_key in {"defend", "dodge"} and actor_id in keys_by_actor:
            declarations[keys_by_actor[actor_id]] = tactical_key
    return declarations


def _draft_taunt_declarations(
    record: CombatSessionRecord, battlefield: Battlefield
) -> dict[str, str]:
    """Return the round's accepted allied Taunt declarations by roster key.

    A pure projection of the persistent draft: each ``taunt`` tactical entry
    contributes its declaring actor's roster key mapped to the taunted enemy's
    roster key (the draft payload's bound enemy dbref). Exactly one enemy per
    taunter, so the mapping direction is taunter -> enemy; the winning taunter
    per enemy is resolved later from the round's initiative sequence, not here.
    An entry whose actor or enemy is no longer on the roster contributes
    nothing: the enemy is then simply unrestricted. Eligibility itself is
    already enforced by the immediately preceding :func:`preflight_draft_entries`
    in the round builder, which rejects an ineligible taunt target before any
    declaration is projected; this helper only binds identities.
    """
    keys_by_actor = {
        int(entity.pk): str(entity.key) for entity in battlefield.roster.values()
    }
    enemy_keys = {
        int(entity.pk): str(entity.key)
        for entity in battlefield.roster.values()
        if int(entity.pk) in record.enemy_ids
    }
    declarations: dict[str, str] = {}
    for actor_id, entry in (record.draft_entries or {}).items():
        if entry["kind"] != "tactical":
            continue
        if entry["payload"].get("tactical_key") != "taunt":
            continue
        taunter_key = keys_by_actor.get(actor_id)
        enemy_key = enemy_keys.get(entry["payload"].get("target_id"))
        if taunter_key is not None and enemy_key is not None:
            declarations[taunter_key] = enemy_key
    return declarations


def _submit_request(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
    *,
    nested: bool = False,
) -> dict[str, Any]:
    """Run the completed draft's one ordinary round and its settlement.

    The single entry every complete party draft resolves through, whether the
    completing confirmation was an in-session command or the exploration
    opening's seed. This body never chooses a dispatch: it resolves exactly
    one ``run_round()`` and never compresses, whatever ``classify_overwhelm()``
    decides (party-combat-opening-routing).

    The encounter's durable opening-order policy supplies the round's
    ``first_actor``: the initiating actor acts before every other combatant in
    the first complete round, and the persisted value is cleared in the same
    unit, so later rounds always use ordinary initiative. Item journals
    produced inside the outer transaction are collected through the sink so
    the except-path restoration covers the actually-deleted mirrors
    (fix-combat-settlement-recovery D1 extended by add-inventory-item-actions
    D2).

    The frozen :class:`~world.rules.combat_beats.RoundRecord` of that round
    rides ``result["round_record"]`` (round and terminal results alike): the
    roster identities, every participant's stored HP before the round and at
    its committed end, the round's own event logs, and the round number. The
    slot is internal: the presentation layer reads it into the read context
    and the result normalizer drops it before any send.
    """
    from world.rules.combat_session.snapshot import _snapshot_round_clock, _restore_round_clock

    clock_before = _snapshot_round_clock(record, battlefield)
    touched, extra = _snapshot_round_touched(actor, battlefield, record)
    exam_host_before = _snapshot_exam_host(record)
    party_before, members_before, relations_before = _snapshot_party_surfaces(
        actor, battlefield
    )
    from django.db import transaction

    notifications: tuple[str, ...] = ()
    item_journals: list[Any] = []
    grant_notifications: list[str] = []
    tactical_declarations: dict[str, str] | None = None
    taunt_declarations: dict[str, str] | None = None
    simulated, nonlethal_keys = _session_policy(battlefield, record)
    dedupe_before = snapshot_practice_dedupe()
    hp_before = _stored_trait_value(actor.traits.hp)
    opponent = _primary_opponent_id(battlefield, record)
    try:
        with durable_combat_atomic(nested=nested):
            current = read_session_uncached(actor)
            if current is None or (
                current.session_id, current.round_revision
            ) != (record.session_id, record.round_revision):
                # A concurrent writer consumed this revision between
                # admission and resolution. Report it in the facade's
                # result shape: every caller renders ``outcome``.
                return {
                    "ok": False,
                    "outcome": "rejected",
                    "reason": "stale_round_revision",
                }
            record = current
            preflight = preflight_draft_entries(actor, record, battlefield)
            if not preflight["is_complete"]:
                return {
                    "ok": False,
                    "outcome": "draft",
                    "reason": "draft_incomplete",
                    "progress": preflight,
                }
            requests = _draft_requests(record, battlefield)
            tactical_declarations = _draft_tactical_declarations(record, battlefield)
            taunt_declarations = _draft_taunt_declarations(record, battlefield)
            # The encounter's durable opening-order policy, consumed here: the
            # initiating actor acts first in this first complete round, and
            # the persisted value is cleared below in the same unit, so no
            # later round inherits an override.
            first_actor = record.opening_first_actor
            # Shared outer transaction (fix-combat-settlement-recovery D1):
            # round effects, friendly-fire and coercion penalties, session
            # metadata, and the terminal settlement commit (or roll back) as
            # one unit, so a process termination can never leave half-round
            # durable state.
            # Later combat changes that edit this seam (roster-and-overwhelm,
            # friendly-fire reachability) must keep edits inside this block.
            # Every completed draft resolves exactly one ordinary round,
            # whatever the verdict, so the player always keeps per-round
            # agency and no interactive entry compresses
            # (party-combat-opening-routing). The session's simulated/
            # nonlethal policy threads into resolution so upkeep-settled ticks
            # honor the same credit rules as direct damage
            # (fix-dot-kill-credit D4). The round carries the encounter's real
            # decision identity (monster-ai-attack-selection): the durable
            # session id and the actual round number this resolution consumes,
            # counted from the record's committed rounds.
            scope_base = ExecutionScopeBase(
                session_id=record.session_id,
                round_index=record.rounds_elapsed + 1,
            )
            # The round also records its own beats inputs (combat-beats-panel
            # D1): the roster identities and every participant's stored HP
            # before the round.
            round_identities, round_hp_before = capture_round_hp(battlefield)
            provider = _party_round_provider(requests, battlefield, record)
            logs = run_round(
                battlefield,
                provider,
                simulated=simulated,
                nonlethal_keys=nonlethal_keys,
                journal_sink=item_journals,
                notifications_sink=grant_notifications,
                first_actor=first_actor,
                decision_scope_base=scope_base,
                tactical_declarations=tactical_declarations,
                taunt_declarations=taunt_declarations,
            )
            # Boundary event for the committed ordinary round: the on_commit
            # callback fires once the OUTERMOST transaction commits and is
            # discarded if this unit rolls back, so a rolled-back round never
            # leaves a boundary line behind. Every value is snapshotted NOW,
            # at the round's durable boundary: a nested caller's later work
            # must not shift the tick/HP this line describes, and the callback
            # itself does zero computation so it can never raise after a
            # commit.
            boundary = {
                "char": str(actor.pk),
                "opponent": opponent,
                "tick": _current_tick(),
                "hp_before": hp_before,
                "hp_after": _stored_trait_value(actor.traits.hp),
            }
            transaction.on_commit(
                lambda boundary=boundary: log_info(
                    "combat_round_settled", context=boundary
                )
            )

            notifications = _scan_friendly_fire(actor, battlefield, logs)
            notifications += _scan_sexual_coercion(actor, battlefield, logs)
            notifications += tuple(grant_notifications)

            # The committed end-of-round HP (combat-beats-panel D1): read
            # after the scans and before ``_continue_or_settle``, so a
            # terminal settlement's regeneration, exam restoration, and
            # defeat aftermath can never move the values the beats are
            # checked against.
            _, round_hp_after = capture_round_hp(battlefield)

            knocked = _knocked_out_ids(logs, battlefield)
            new_fled_ids = tuple(
                sorted(
                    int(battlefield.roster[key].pk)
                    for key in battlefield.fled
                    if key in battlefield.roster
                )
            )
            new_knocked_out_ids = tuple(sorted(set(record.knocked_out_ids) | set(knocked)))
            # Compose the round-end record from the LIVE durable record, not
            # the pre-round snapshot: mid-round writers (the martyrdom-vow
            # session_stamp effect, church design §5.8) commit their own
            # active_combat rewrite inside this same atomic unit, and a
            # replace() over the stale pre-round record would silently wipe
            # those fields. The live read is the single writer's current
            # state; the round deltas (fled/knocked-out/elapsed) land on it.
            current = read_session(actor)
            base = current if current is not None else record
            new_record = replace(
                base,
                fled_ids=new_fled_ids,
                knocked_out_ids=new_knocked_out_ids,
                rounds_elapsed=base.rounds_elapsed + 1,
                # One completed draft is consumed exactly once: the consumed
                # revision, the emptied draft and the spent opening-order
                # policy all land together with the round they belong to.
                round_revision=base.round_revision + 1,
                draft_version=0,
                draft_entries={},
                confirmed_actors=(),
                opening_first_actor=None,
            )
            _persist(actor, new_record)

            from world.rules.buffs import remove_ground_markers, remove_positional_markers

            newly_fled_pks = set(new_fled_ids) - set(record.fled_ids)
            if newly_fled_pks:
                for entity in battlefield.roster.values():
                    if int(entity.pk) in newly_fled_pks:
                        removed = remove_ground_markers(entity) + remove_positional_markers(entity)
                        if removed:
                            boundary = {
                                "char": str(entity.pk),
                                "count": removed,
                                "reason": "fled",
                            }
                            transaction.on_commit(
                                lambda b=boundary: log_info(
                                    "combat_marker_swept", context=b
                                )
                            )

            newly_knocked_pks = set(new_knocked_out_ids) - set(record.knocked_out_ids)
            if newly_knocked_pks:
                for entity in battlefield.roster.values():
                    if int(entity.pk) in newly_knocked_pks:
                        removed = remove_ground_markers(entity) + remove_positional_markers(entity)
                        if removed:
                            boundary = {
                                "char": str(entity.pk),
                                "count": removed,
                                "reason": "knocked_out",
                            }
                            transaction.on_commit(
                                lambda b=boundary: log_info(
                                    "combat_marker_swept", context=b
                                )
                            )

            result = _continue_or_settle(
                actor, new_record, battlefield, logs, notification_count=len(notifications)
            )
            receipt = {
                "session_id": record.session_id,
                "round_revision": record.round_revision,
                "rounds_elapsed": new_record.rounds_elapsed,
                "outcome": result.get("outcome"),
            }
            write_last_combat_receipt(actor, receipt)
            result["receipt"] = receipt
            result["ok"] = True
            # Internal slot only: the dispatcher reads it into the
            # presentation context and ``_normalize_result`` drops it, so
            # it never reaches the wire (combat-beats-panel D2).
            result["round_record"] = RoundRecord(
                session_id=record.session_id,
                number=new_record.rounds_elapsed,
                logs=tuple(logs),
                identities=round_identities,
                hp_before=round_hp_before,
                hp_after=round_hp_after,
            )
            # Mark every observation journal entry whose savepoint rolled back
            # as dead while the transaction is still open, so the commit-time
            # publication never resurrects failed work
            # (monster-ai-observation-lifecycle).
            from world.rules.combat_session.observations import (
                reconcile_session_memory,
            )

            reconcile_session_memory(record.session_id)
    except Exception:
        # A defeat settled inside this transaction armed its undo; run it
        # BEFORE the round restore below so the pre-round values win (the
        # undo restores the writer's post-round entry state, the round
        # restore the pre-round state the database rolled back to).
        from world.rules.defeat_aftermath import drain_pending_undos

        for undo in drain_pending_undos():
            undo()
        # The outer transaction rolled the database back; restore the item
        # journals first (they cover the actually-deleted mirrors and the
        # HP surface written by the item resolver), then the in-process
        # attribute surfaces so readers never observe the rolled-back values
        # (the idmapper cache is not transaction-aware), and re-register
        # skip safety because clear_session ran in-process.
        for journal in item_journals:
            journal.restore()
        _restore_round_clock(clock_before)
        _restore_round_touched(
            actor,
            touched,
            extra,
            party_before,
            members_before,
            relations_before,
        )
        # The host's exam lifecycle surfaces last: the settlement restores
        # the persistent host inside this transaction (outfit, effects, hold).
        _restore_exam_host(exam_host_before)
        # Resolved rounds inside a rolled-back outer transaction kept their
        # practice-dedupe claims (the resolve-level release only covers an
        # INNER rolled-back commit); restore the pre-round state so a
        # same-tick retry after the failed round accrues normally.
        restore_practice_dedupe(dedupe_before)
        register_active_battlefield(battlefield)
        raise
    # The outer transaction committed: any armed aftermath undo is moot (the
    # physical departure is scheduled via on_commit); drop it.
    from world.rules.defeat_aftermath import drain_pending_undos

    drain_pending_undos()
    # Deliver auto-leave notices only after the whole round committed, so a
    # rolled-back round never shows a fake disengagement notification.
    for line in notifications:
        actor.msg(line)
    return result
