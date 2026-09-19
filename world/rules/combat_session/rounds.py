"""Round mechanics: submissions, round bookkeeping, and the round transaction.

Every preflight-valid player action drives exactly one ordinary round --
compression is reachable only through ``submit_opening_action``, the sole
sanctioned requester -- inside one shared outer transaction that commits (or
rolls back) the round effects, the post-round scans, session metadata, and the
terminal settlement as one unit (fix-combat-settlement-recovery D1).
"""

from dataclasses import replace
from typing import Any, Literal

from world.observability import log_info
from world.rules import combat
from world.rules.action import ActionRequest, ActionResolver, _stored_trait_value
from world.rules.action_preview import revalidate_submission
from world.rules.combat import Battlefield, run_round
from world.rules.clock import read_world_clock
from world.rules.combat_session.battlefield import (
    _context_for,
    _session_policy,
    reconstruct_battlefield,
)
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.policies import (
    _overwhelm_provider,
    _round_provider,
)
from world.rules.combat_session.lifecycle import _persist
from world.rules.combat_session.records import CombatSessionRecord, read_session
from world.rules.combat_session.scans import (
    _scan_friendly_fire,
    _scan_sexual_coercion,
)
from world.rules.combat_session.settlement import _continue_or_settle
from world.rules.combat_session.snapshot import (
    _restore_round_touched,
    _snapshot_party_surfaces,
    _snapshot_round_touched,
)
from world.rules.items import ItemUseRequest, preflight_item_use
from world.rules.overwhelm import (
    classify_overwhelm,
    commanded_damage_reaches_enemy,
    resolve_overwhelm,
)
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


def submit_player_action(
    actor: Any,
    skill_key: str,
    targets_or_shorthand: list[Any] | str,
    scale: float = 1.0,
) -> dict[str, Any]:
    """Run one ordinary round for one player action.

    ``targets_or_shorthand`` is either a concrete list of live participant
    objects or one approved AREA shorthand (``all-enemies``, ``all-allies``,
    ``all``). Player-facing NONE and SELF input must be an empty list; SELF is
    bound to the actor inside the rules layer. ``scale`` is the optional
    freeform magnitude modifier (default ``1.0``), threaded into the preview,
    preflight, and the round's ``ActionRequest``; a scale the deterministic
    gate forbids rejects before initiative and consumes no round or world
    time. The facade revalidates the
    submitted target value through the shared side-effect-free preview, runs
    ``ActionResolver.preflight()``, and only then starts exactly one ordinary
    round -- whatever ``classify_overwhelm()`` decides for the session. A
    submission made inside an already-active session never compresses;
    compression is reachable only by opening a fight from exploration through
    ``submit_opening_action()`` (combat-session-opening-dispatch D-1/D-2). A
    rejection returns before initiative and consumes no round or world time.
    """
    record, battlefield, request, rejection = _preflight_skill_submission(
        submit_player_action, actor, skill_key, targets_or_shorthand, scale=scale
    )
    if rejection is not None:
        return rejection
    return _submit_request(
        actor,
        record,
        battlefield,
        request,
        commanded_kind="skill",
        commanded_key=skill_key,
    )


def _preflight_skill_submission(
    entry: Any,
    actor: Any,
    skill_key: str,
    targets_or_shorthand: list[Any] | str,
    scale: float = 1.0,
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
    if not isinstance(targets_or_shorthand, (list, str)):
        raise TypeError(f"{name} requires an explicit target list or shorthand")
    if not isinstance(targets_or_shorthand, str) and not all(
        str(target.key) in battlefield.roster
        for target in targets_or_shorthand
    ):
        raise CombatSessionError(SessionReason.NOT_PRESENT)

    context = _context_for(battlefield, record)
    preview = revalidate_submission(
        actor, skill_key, context, targets_or_shorthand, scale=scale
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
        actor=actor,
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


def submit_opening_action(
    actor: Any,
    skill_key: str,
    targets: list[Any],
    scale: float = 1.0,
) -> dict[str, Any]:
    """Open the fight's first action: the sole production requester of compression.

    Its production consumer is ``field-combat-initiation``'s routing; the
    seam ships callerless until then (combat-session-opening-dispatch D-7).
    Runs the identical session read, reconstruction,
    ``revalidate_submission()`` and ``ActionResolver.preflight()`` as
    ``submit_player_action()``, then owns the two-part dispatch judgement
    (D-2): select ``opening="overwhelm"`` if and only if
    ``classify_overwhelm()`` decides for the actor's team **and**
    ``overwhelm.commanded_damage_reaches_enemy()`` reports the submitted
    skill damages a member of the opposing team; every other case selects
    ``opening="round"``. Both selections pass ``first_actor`` equal to the
    actor's roster key (D-3): the player who chose to start the fight acts
    before any other combatant in the opening round.

    Skills only -- no item request may reach this entry. Only a concrete
    list of participant objects is accepted: an approved AREA shorthand
    (``all-enemies``/``all-allies``/``all``) is rejected before initiative
    even though ``submit_player_action()`` accepts one, because
    ``commanded_damage_reaches_enemy()`` reads concrete roster keys and a
    shorthand reaching it would silently answer ``False`` and disable
    one-shot settlement with no diagnostic. Off-roster targets reject
    exactly as ``submit_player_action()`` does.
    """
    if isinstance(targets, str):
        # Rejected before any initiative or dispatch, but only after the
        # session-presence check so a caller with no session still gets
        # NO_ACTIVE_SESSION, exactly as submit_player_action reports it.
        if read_session(actor) is None:
            raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
        raise TypeError(
            "submit_opening_action requires a concrete target list; the "
            f"shorthand {targets!r} cannot be resolved to roster keys for the "
            "compression predicate"
        )
    record, battlefield, request, rejection = _preflight_skill_submission(
        submit_opening_action, actor, skill_key, targets, scale=scale
    )
    if rejection is not None:
        return rejection
    target_keys = [str(target.key) for target in targets]
    compress = classify_overwhelm(battlefield) == battlefield.team_of(
        str(actor.key)
    ) and commanded_damage_reaches_enemy(
        battlefield, str(actor.key), skill_key, target_keys
    )
    return _submit_request(
        actor,
        record,
        battlefield,
        request,
        opening="overwhelm" if compress else "round",
        first_actor=str(actor.key),
        commanded_kind="skill",
        commanded_key=skill_key,
    )


def submit_player_item_use(
    actor: Any, item_key: str, *, target: Any | None = None
) -> dict[str, Any]:
    """Run one ordinary combat round whose player turn consumes one held item.

    The facade revalidates the request through the shared item preflight
    with combat allowed, and only then starts exactly one ordinary round
    whatever ``classify_overwhelm()`` decides, exactly like
    ``submit_player_action`` (combat-session-opening-dispatch D-5: a
    consumable is not an attack, so item submissions lose the compression
    branch outright rather than gaining the opening gate). A rejection
    returns before initiative and consumes no round or world time; a
    successful use resolves on the player's turn and the item journal is
    merged into the session's outer rollback safety net.

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
    if not isinstance(item_key, str):
        raise TypeError("submit_player_item_use requires an item key string")
    preflight = preflight_item_use(
        ItemUseRequest(actor=actor, item_key=item_key, target=target),
        in_combat=True,
        context=_context_for(battlefield, record),
    )
    if not preflight.allowed:
        return {
            "outcome": "rejected",
            "reason": preflight.reason.value if preflight.reason else None,
            "detail": preflight.detail,
        }
    return _submit_request(
        actor,
        record,
        battlefield,
        ItemUseRequest(actor=actor, item_key=item_key, target=target),
        commanded_kind="item",
        commanded_key=item_key,
    )


def _submit_request(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
    request: "combat.RoundRequest",
    *,
    opening: Literal["round", "overwhelm"] = "round",
    first_actor: str | None = None,
    commanded_kind: str,
    commanded_key: str,
) -> dict[str, Any]:
    """Run the shared round/overwhelm/settlement body for one request.

    The request is a member of the closed round-request union;
    ``commanded_kind``/``commanded_key`` carry the selected action's identity
    into overwhelm compression for log marking only. Item journals produced
    inside the outer transaction are collected through the sink so the
    except-path restoration covers the actually-deleted mirrors
    (fix-combat-settlement-recovery D1 extended by add-inventory-item-actions
    D2).

    ``opening`` (combat-session-opening-dispatch D-1) is the caller's
    dispatch decision, never this body's: the default ``"round"`` means one
    ordinary ``run_round()``, and the only sanctioned way to request the
    ``"overwhelm"`` compression is ``submit_opening_action()``. This body
    never consults ``classify_overwhelm()`` to choose; ``first_actor`` is
    forwarded to whichever entry the opening selects.
    """
    touched, extra = _snapshot_round_touched(actor, battlefield, record)
    party_before, members_before, relations_before = _snapshot_party_surfaces(
        actor, battlefield
    )
    from django.db import transaction

    notifications: tuple[str, ...] = ()
    item_journals: list[Any] = []
    grant_notifications: list[str] = []
    simulated, nonlethal_keys = _session_policy(battlefield, record)
    dedupe_before = snapshot_practice_dedupe()
    hp_before = _stored_trait_value(actor.traits.hp)
    opponent = _primary_opponent_id(battlefield, record)
    try:
        with transaction.atomic():
            # Shared outer transaction (fix-combat-settlement-recovery D1):
            # round effects, friendly-fire and coercion penalties, session
            # metadata, and the terminal settlement commit (or roll back) as
            # one unit, so a process termination can never leave half-round
            # durable state.
            # Later combat changes that edit this seam (roster-and-overwhelm,
            # friendly-fire reachability) must keep edits inside this block.
            # Compression is opt-in (combat-session-opening-dispatch D-1/D-2):
            # only ``submit_opening_action()`` may pass ``opening =
            # "overwhelm"``, and only after its own two-part player-direction
            # plus damage-reaches-enemy judgement. Every in-session
            # submission takes the default ``"round"`` -- one ordinary round
            # per submission, whatever the verdict, so the player always
            # keeps per-round agency. The session's simulated/nonlethal
            # policy threads into both entries so upkeep-settled ticks honor
            # the same credit rules as direct damage (fix-dot-kill-credit D4).
            if opening == "overwhelm":
                provider = _overwhelm_provider(actor, request, battlefield, record)
                result = resolve_overwhelm(
                    battlefield,
                    provider,
                    max_rounds=12,
                    commanded_actor=str(actor.key),
                    commanded_action_kind=commanded_kind,
                    commanded_action_key=commanded_key,
                    simulated=simulated,
                    nonlethal_keys=nonlethal_keys,
                    journal_sink=item_journals,
                    notifications_sink=grant_notifications,
                    first_actor=first_actor,
                )
                logs = result.event_logs
                gained = result.rounds_elapsed
            else:
                # The default: one ordinary round.
                provider = _round_provider(actor, request, battlefield, record)
                logs = run_round(
                    battlefield,
                    provider,
                    simulated=simulated,
                    nonlethal_keys=nonlethal_keys,
                    journal_sink=item_journals,
                    notifications_sink=grant_notifications,
                    first_actor=first_actor,
                )
                gained = 1
                # Boundary event for a committed ordinary round only: the
                # on_commit callback fires once the OUTERMOST transaction
                # commits and is discarded if this unit rolls back, so a
                # rolled-back round never leaves a boundary line behind. The
                # event is bound to this ``opening == "round"`` path only
                # (combat-session-opening-dispatch D-6): the compression
                # opening is not one ordinary round.
                # Every value is snapshotted NOW, at the round's durable
                # boundary: a nested caller's later work must not shift the
                # tick/HP this line describes, and the callback itself does
                # zero computation so it can never raise after a commit.
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

            knocked = _knocked_out_ids(logs, battlefield)
            new_fled_ids = tuple(
                sorted(
                    int(battlefield.roster[key].pk)
                    for key in battlefield.fled
                    if key in battlefield.roster
                )
            )
            new_knocked_out_ids = tuple(sorted(set(record.knocked_out_ids) | set(knocked)))
            new_record = replace(
                record,
                fled_ids=new_fled_ids,
                knocked_out_ids=new_knocked_out_ids,
                rounds_elapsed=record.rounds_elapsed + gained,
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
        _restore_round_touched(
            actor,
            touched,
            extra,
            party_before,
            members_before,
            relations_before,
        )
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
