"""Validated replacement operations for quest-log and instance-pin state (D-6).

Every lifecycle transition -- accept, abandon, bind, stage advance, deadline
failure, and protected-entity failure -- follows one order: parse and validate
the current records, compute the replacement list plus the required pin delta
without writing, then apply both inside one ``transaction.atomic()`` block with
pre-operation snapshot/restore so Evennia's in-process attribute cache agrees
with the database rollback.

This module is the lowest quest-runtime layer and must not import
``world.quests.runtime`` at module scope: runtime lifecycle operations import
these helpers, so the record serializer is resolved lazily instead.
"""

from copy import deepcopy
from typing import Any, Iterable

from django.db import transaction
from evennia.objects.models import ObjectDB

from world.observability import log_info, log_warn


def _record_signature(entry: Any) -> tuple | None:
    """The observable lifecycle identity of one storage dict, or ``None``.

    Parsed with the SAME strict reader the lifecycle itself uses
    (``runtime.from_storage``, lazily imported to keep the module-scope
    cycle-free contract): ``(definition_key, state, stage_index, bound)``.
    Any entry the lifecycle would reject — bad field types, unknown state,
    coercion-looking values such as ``state=None`` or ``stage_index='0'`` —
    yields ``None`` so the caller skips the whole diff instead of inventing
    a fictitious boundary from untrusted storage.
    """
    from world.quests.runtime import from_storage

    try:
        record = from_storage(dict(entry))
    except Exception:  # observability: ignore R2: an entry the strict reader rejects (or a non-mapping blob) returns None so the caller skips the whole diff; the lifecycle write itself is the contract here
        return None
    return (
        record.definition_key,
        record.state.value,
        record.stage_index,
        record.stage_room_id is not None,
    )


def _format_stage(state: str, stage_index: int, bound: bool) -> str:
    return f"{state}:{stage_index}:{'bound' if bound else 'unbound'}"


def _schedule_transition_events(
    actor: Any, old_entries: list[Any], new_records: list[Any]
) -> None:
    """Emit one ``quest_transition`` per changed quest on durable commit.

    Shared by ALL three quest-log writers (replacement, delta, and the
    pending-effect seam) so every lifecycle write path — accept, bind, stage
    advance, abandon, deadline/protected-entity failure, DEFEAT completion —
    emits its events. Every event context names the governing commission via
    ``issuer`` (new records carry it on the record; removals carry it from the
    pre-write stored entry, which the strict signature reader has already
    validated). ``old_entries`` is the raw stored log captured BEFORE the
    write; callbacks registered through ``transaction.on_commit`` fire only on
    the outermost commit and are discarded on rollback, so a rolled-back
    operation leaves no event behind. Malformed logs skip the diff:
    observability must never affect a lifecycle write.
    """
    try:
        before: dict[str, tuple] = {}
        before_issuers: dict[str, str] = {}
        for entry in (old_entries or []):
            signature = _record_signature(entry)
            if signature is None:
                return
            quest_id = str(entry["quest_id"])
            if quest_id in before:
                # A duplicated quest_id is corrupt storage the diff must not
                # arbitrate between — skip the whole diff.
                return
            before[quest_id] = signature
            before_issuers[quest_id] = str(entry["issuer_key"])
        events: list[dict[str, Any]] = []
        after_ids: set[str] = set()
        for record in new_records:
            quest_id = str(record.quest_id)
            after_ids.add(quest_id)
            to_stage = _format_stage(
                record.state.value, record.stage_index, record.stage_room_id is not None
            )
            previous = before.get(quest_id)
            if previous is None:
                from_stage = "none"
            elif previous[1:] == (
                record.state.value,
                record.stage_index,
                record.stage_room_id is not None,
            ):
                continue
            else:
                from_stage = _format_stage(*previous[1:])
            events.append(
                {
                    "char": str(actor.pk),
                    "quest": str(record.definition_key),
                    "issuer": str(record.issuer_key),
                    "stage_from": from_stage,
                    "stage_to": to_stage,
                }
            )
        for quest_id, previous in before.items():
            if quest_id not in after_ids:
                events.append(
                    {
                        "char": str(actor.pk),
                        "quest": previous[0],
                        "issuer": before_issuers[quest_id],
                        "stage_from": _format_stage(*previous[1:]),
                        "stage_to": "removed",
                    }
                )
    except Exception:  # observability: ignore R2: diff failures silently skip events; observability must never alter a quest write
        return
    for context in sorted(events, key=lambda item: item["quest"]):
        transaction.on_commit(
            lambda context=context: log_info("quest_transition", context=context)
        )


def stage_pin_reason(character_id: int, quest_id: str, stage_index: int) -> str:
    """Return the deterministic quest pin reason for one active stage."""
    return f"quest:{character_id}:{quest_id}:stage:{stage_index}"


def release_stage_binding(
    actor: Any,
    record: Any,
) -> tuple[tuple[Any, tuple[str, ...], tuple[str, ...]], ...]:
    """Return pin operations releasing the record's current stage pin.

    A missing or already-deleted bound room is treated as already unpinned, so
    a terminal transition never crashes on an absent instance (D-3).
    """
    if record.stage_room_id is None:
        return ()
    room = ObjectDB.objects.filter(id=record.stage_room_id).first()
    if room is None:
        return ()
    reason = stage_pin_reason(actor.pk, record.quest_id, record.stage_index)
    return ((room, (), (reason,)),)


def _attribute_snapshot(entity: Any, key: str) -> tuple[bool, Any]:
    exists = entity.attributes.has(key)
    value = deepcopy(entity.attributes.get(key)) if exists else None
    return exists, value


def _restore_attribute(entity: Any, key: str, snapshot: tuple[bool, Any]) -> None:
    existed, value = snapshot
    if existed:
        entity.attributes.add(key, deepcopy(value))
    else:
        entity.attributes.remove(key)


def _restore_attribute_best_effort(
    entity: Any,
    key: str,
    snapshot: tuple[bool, Any],
) -> None:
    """Restore one attribute, degrading to a cache reset when the write fails.

    The database transaction has already rolled back; if re-writing the
    pre-operation value also fails, invalidating Evennia's in-process attribute
    cache makes the next read repopulate from the rolled-back database so the
    process never serves a value that disagrees with persistence.
    """
    try:
        _restore_attribute(entity, key, snapshot)
    except Exception as error:
        try:
            entity.attributes.reset_cache()
        except Exception:  # observability: ignore R2: best-effort cache reset after the rollback_restore_failed warn below; a failed reset must not mask the primary failure
            pass
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"key": key, "entity": str(entity)},
        )


def snapshot_quest_log(actor: Any) -> tuple[bool, Any]:
    """Snapshot only the player's quest-log attribute (D-6 surface handler)."""
    return _attribute_snapshot(actor, "quest_log")


def restore_quest_log(actor: Any, snapshot: tuple[bool, Any]) -> None:
    _restore_attribute_best_effort(actor, "quest_log", snapshot)


def snapshot_pin_reasons(room: Any) -> tuple[bool, Any]:
    """Snapshot only the room's pin-reasons attribute (D-6 surface handler)."""
    return _attribute_snapshot(room, "pin_reasons")


def restore_pin_reasons(room: Any, snapshot: tuple[bool, Any]) -> None:
    _restore_attribute_best_effort(room, "pin_reasons", snapshot)


def _apply_pin_operations(
    pin_operations: Iterable[tuple[Any, tuple[str, ...], tuple[str, ...]]],
) -> None:
    for room, adds, removes in pin_operations:
        reasons = list(room.db.pin_reasons or [])
        changed = False
        for reason in removes:
            if reason in reasons:
                reasons.remove(reason)
                changed = True
        for reason in adds:
            if reason not in reasons:
                reasons.append(reason)
                changed = True
        if changed:
            room.db.pin_reasons = reasons


#: Upper bound on one readable identity label copied into completion evidence.
_IDENTITY_LABEL_LIMIT = 64


def _push_title_notifications(actor: Any, lines: tuple[str, ...]) -> None:
    """Push one OOB grant line per newly banked title after the owner commits.

    Presentation only: a delivery failure is logged and never turns a
    committed completion into a failed one.
    """
    for line in lines:
        try:
            actor.msg(line)
        except Exception as error:  # noqa: BLE001 - presentation is best-effort
            log_warn(
                "quest_title_notification_failed",
                context={"char": str(getattr(actor, "pk", "") or "")},
                exc=error,
            )


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _serialize_destination(destination: Any) -> dict[str, Any] | None:
    """Serialize a QuestObjective's RoomLocator into a JSON-safe payload."""
    if destination is None:
        return None
    payload: dict[str, Any] = {"kind": _enum_value(destination.kind)}
    anchor_key = getattr(destination, "anchor_key", None)
    if anchor_key is not None:
        payload["anchor_key"] = str(anchor_key)
    xyz = getattr(destination, "xyz", None)
    if xyz is not None:
        payload["xyz"] = [int(xyz[0]), int(xyz[1]), str(xyz[2])]
    return payload


def _serialize_objective(objective: Any) -> dict[str, Any]:
    """Serialize a QuestObjective into a JSON-safe fact payload."""
    if objective is None:
        return {}
    payload: dict[str, Any] = {
        "kind": _enum_value(objective.kind),
        "quantity": int(getattr(objective, "quantity", 1)),
    }
    for field in (
        "monster_tier",
        "item_key",
        "region_key",
        "species_key",
        "site_key",
    ):
        val = getattr(objective, field, None)
        if val is not None:
            payload[field] = val
    if getattr(objective, "countable_variant_keys", None):
        payload["countable_variant_keys"] = list(objective.countable_variant_keys)
    if getattr(objective, "requires_bound_targets", False):
        payload["requires_bound_targets"] = True
    destination = _serialize_destination(getattr(objective, "destination", None))
    if destination is not None:
        payload["destination"] = destination
    if getattr(objective, "protected_role_refs", ()):
        payload["protected_role_refs"] = list(objective.protected_role_refs)
    if getattr(objective, "meeting_role_refs", ()):
        payload["meeting_role_refs"] = list(objective.meeting_role_refs)
    relation = getattr(objective, "relation", None)
    if relation is not None:
        payload["relation"] = [str(part) for part in relation]
    if getattr(objective, "completion", None) is not None:
        payload["completion"] = _enum_value(objective.completion)
    return payload


def _identity_labels(identities: Iterable[int]) -> dict[int, str]:
    """Return one readable label per still-existing identity, in one query."""
    unique = tuple(dict.fromkeys(int(value) for value in identities))
    if not unique:
        return {}
    rows = ObjectDB.objects.filter(pk__in=unique).values_list("id", "db_key")
    return {
        int(pk): str(key or "")[:_IDENTITY_LABEL_LIMIT] for pk, key in rows
    }


def _target_role(objective: Any) -> str:
    """The readable role a plain ``objective_target_ids`` binding carries."""
    from .definitions import ObjectiveKind

    if getattr(objective, "kind", None) is ObjectiveKind.DELIVER:
        return "recipient"
    return "target"


def _bound_identities(source: Any, objective: Any) -> list[dict[str, Any]]:
    """The satisfied objective's bound identities with readable roles.

    ``source`` is the authoritative pre-completion record, so the retained
    protected role bindings and the declared meeting roles resolve to the
    exact identities the objective bound before the terminal transition
    cleared them. A declared meeting role resolves through the published
    package's role binding — the same lookup the rendezvous predicate used.
    Exact ``(role, identity)`` pairs appear once; one identity may carry
    several distinct roles (a protected escortee that a rendezvous meets).
    """
    from .scene_store import get_role_binding

    pairs: list[tuple[str, int]] = [
        (_target_role(objective), int(identity))
        for identity in source.objective_target_ids
    ]
    if source.protected_roles:
        pairs.extend(
            (str(role), int(identity)) for role, identity in source.protected_roles
        )
    else:
        pairs.extend(("protected", int(identity)) for identity in source.protected_entity_ids)
    package_id = getattr(source, "package_id", None)
    if package_id:
        for role in objective.meeting_role_refs:
            binding = get_role_binding(package_id, role)
            if binding is not None:
                pairs.append((f"meeting:{role}", int(binding.npc_id)))
    pairs = list(dict.fromkeys(pairs))
    labels = _identity_labels(identity for _, identity in pairs)
    return [
        {"role": role, "identity": identity, "label": labels.get(identity, "")}
        for role, identity in pairs
    ]


def _pre_completion_records(entries: Iterable[Any]) -> dict[str, Any]:
    """Map each stored quest id to its strictly parsed pre-completion record.

    The completion diff (``just_completed_records``) rejects the whole
    boundary on any entry the strict reader would refuse, so every entry here
    has already been proven parseable.
    """
    from world.quests.runtime import from_storage

    return {
        str(record.quest_id): record
        for record in (from_storage(dict(entry)) for entry in entries or ())
    }


def _completion_objective_payload(record: Any, source: Any) -> dict[str, Any]:
    """The finalized ``completed_objective`` payload of one completion fact.

    A quest completes only on its final stage, so the satisfied objective is
    the definition's last stage no matter how many intermediate stages one
    automatic chain advanced inside this boundary. The runtime bindings come
    from ``source`` — the pre-completion record — and only when it still names
    that same stage; an objective with no bindings therefore degrades to the
    terminal record's (already empty) binding set instead of borrowing a
    previous stage's.
    """
    from world.quests.runtime import definition_for

    definition = definition_for(record)
    stage_index = min(int(record.stage_index), len(definition.stages) - 1)
    objective = definition.stages[stage_index].objective
    binding_source = (
        source
        if source is not None and int(source.stage_index) == stage_index
        else record
    )
    payload = _serialize_objective(objective)
    payload["stage_index"] = stage_index
    payload["destination_room_id"] = getattr(binding_source, "stage_room_id", None)
    payload["bound_identities"] = _bound_identities(binding_source, objective)
    return payload


def _settle_quest_completion_events(
    actor: Any,
    old_entries: list[Any],
    completed_records: Iterable[Any],
) -> None:
    """Record the completion facts and schedule the owner notification.

    The immutable fact is finalized HERE, in the owner's transaction and from
    the authoritative pre-completion entries, before the terminal bindings are
    gone from storage. Quest-completed fixed titles are settled FIRST, through
    the unified automatic award entry point and under that completion
    occurrence's own source, so the finalized envelope already holds every new
    grant when the fact is first committed. A source that already committed
    keeps its original results untouched: replay returns them before any
    reevaluation, so it neither grants again nor loses the occurrence's
    suppression effect. Notification is then dispatched through an outer
    ``transaction.on_commit`` callback that supplies the canonical source
    identity and the finalized receipt, so an inventory, delivery, arrival or
    action plan that predicted the completion but never wrote it notifies
    nothing, a rollback discards every pending notification, and an unchanged
    terminal replacement or replayed completion (``created`` is ``False``)
    schedules no second attempt.
    """
    completed = list(completed_records)
    if not completed:
        return
    from world.quests.runtime import (
        QuestCompletionReceipt,
        dispatch_quest_completion,
    )
    from world.rules.clock import get_world_clock
    from world.rules.titles.awards import settle_quest_completion_awards
    from world.narrative.events import get_committed_award_results, record_narrative_event

    current_tick = get_world_clock().tick
    location_str = str(getattr(getattr(actor, "location", None), "pk", "") or "")
    before = _pre_completion_records(old_entries)
    for record in completed:
        objective_payload = _completion_objective_payload(
            record, before.get(str(record.quest_id))
        )
        source_id = f"quest:{record.quest_id}:completion:{actor.pk}"
        committed_awards = get_committed_award_results(source_id)
        settled_now = committed_awards is None
        if settled_now:
            committed_awards = settle_quest_completion_awards(
                actor,
                source_id=source_id,
                completed_quest_keys=(str(record.definition_key),),
                tick=current_tick,
            )

        _event, _progress, created = record_narrative_event(
            source_id=source_id,
            event_type="quest_completion",
            content={
                "quest_id": str(record.quest_id),
                "definition_key": str(record.definition_key),
                "completed_objective": objective_payload,
                "outcome": "completed",
            },
            participants=[str(actor.pk)],
            location=location_str,
            tick=current_tick,
            visibility="public",
            salience=1,
            award_results=committed_awards,
        )
        if not created:
            # The fact already exists: this is an unchanged terminal
            # replacement or a replay, and neither may admit another attempt.
            continue
        if settled_now and committed_awards:
            # One OOB grant line per newly banked title, pushed only after the
            # enclosing owner commits; a rollback discards it with the grant.
            lines = tuple(
                f"獲得稱號：{award.display_name}" for award in committed_awards
            )
            transaction.on_commit(
                lambda lines=lines: _push_title_notifications(actor, lines),
                robust=True,
            )
        receipt = QuestCompletionReceipt(
            source_id=source_id,
            actor=actor,
            actor_id=int(actor.pk),
            quest_id=str(record.quest_id),
            definition_key=str(record.definition_key),
            issuer_key=str(record.issuer_key),
            objective=dict(objective_payload),
            awards=tuple(committed_awards),
        )
        transaction.on_commit(
            lambda receipt=receipt: dispatch_quest_completion(receipt)
        )


def apply_quest_log_replacement(
    actor: Any,
    new_records: list[Any],
    pin_operations: Iterable[tuple[Any, tuple[str, ...], tuple[str, ...]]] = (),
) -> None:
    """Commit a replacement and terminal escort release as one control unit."""
    from .escort_lifecycle import escort_transaction, release_escort_bindings
    from .escort import resolve_protected_actors
    from .runtime import QuestState

    terminal = [
        record for record in new_records
        if record.protected_roles and record.state is not QuestState.IN_PROGRESS
    ]
    if not terminal:
        _replace_quest_log(actor, new_records, pin_operations)
        return
    actors = tuple({
        entity.pk: entity for record in terminal
        for _, entity in resolve_protected_actors(record)
    }.values())
    with escort_transaction(actor, actors):
        _replace_quest_log(actor, new_records, pin_operations)
        for record in terminal:
            release_escort_bindings(actor, record.quest_id)


def _replace_quest_log(
    actor: Any,
    new_records: list[Any],
    pin_operations: Iterable[tuple[Any, tuple[str, ...], tuple[str, ...]]] = (),
) -> None:
    """Replace one quest log and apply a pin delta atomically with restore.

    Records that just reached COMPLETED under an ``AUTO`` issuance settle
    inside the same transaction (quest-auto-settlement): the plan is computed
    against the pre-write state, the reward surfaces join the snapshot/restore
    set only when the plan pays, and the ACQUIRE completions the paid items
    trigger are written as a follow-up replacement in the same
    ``transaction.atomic()`` block. Completion settlement also banks
    quest-completed fixed titles on the actor, so the title collection and
    equipped record join the snapshot/restore set whenever this write finalizes
    a completion; the enclosing transaction remains the only commit boundary.
    """
    from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort
    from world.quests.runtime import to_storage
    from world.quests.settlement import (
        commit_auto_settlement,
        just_completed_records,
        plan_auto_settlement_chain,
    )

    pin_operations = tuple(pin_operations)
    old_entries = list(actor.db.quest_log or [])
    plan = plan_auto_settlement_chain(actor, old_entries, new_records)
    completing = just_completed_records(old_entries, new_records)
    pre_chain_entries = [to_storage(record) for record in new_records]
    chain_completing = (
        just_completed_records(
            pre_chain_entries, list(plan.chain_records)
        )
        if plan.chain_records is not None
        else []
    )
    actor_snapshot = snapshot_quest_log(actor)
    room_snapshots = {
        id(room): snapshot_pin_reasons(room) for room, _, _ in pin_operations
    }
    completion_snapshots = [
        (key, attribute_snapshot(actor, key))
        for key in ("title_collection", "title_equipped")
    ] if completing or chain_completing else []
    settlement_snapshots = [
        (key, attribute_snapshot(actor, key))
        for key in ("wallet", "inventory", "guild_reward_claims")
    ] if plan.entries else []
    settlement_pin_snapshots = [
        (room, snapshot_pin_reasons(room)) for room, _, _ in plan.chain_pins
    ]
    try:
        with transaction.atomic():
            actor.db.quest_log = [to_storage(record) for record in new_records]
            _apply_pin_operations(pin_operations)
            commit_auto_settlement(actor, plan)
            if plan.chain_records is not None:
                actor.db.quest_log = [
                    to_storage(record) for record in plan.chain_records
                ]
                _apply_pin_operations(plan.chain_pins)
            _settle_quest_completion_events(actor, old_entries, completing)
            _settle_quest_completion_events(
                actor, pre_chain_entries, chain_completing
            )
    except Exception:
        restore_quest_log(actor, actor_snapshot)
        for room, _, _ in pin_operations:
            restore_pin_reasons(room, room_snapshots[id(room)])
        for key, snapshot in completion_snapshots:
            restore_attribute_best_effort(actor, key, snapshot)
        for key, snapshot in settlement_snapshots:
            restore_attribute_best_effort(actor, key, snapshot)
        for room, snapshot in settlement_pin_snapshots:
            restore_pin_reasons(room, snapshot)
        raise
    _schedule_transition_events(actor, old_entries, new_records)
    if plan.chain_records is not None:
        _schedule_transition_events(
            actor,
            [to_storage(record) for record in new_records],
            list(plan.chain_records),
        )


def apply_quest_log_delta(
    actor: Any,
    new_records: list[Any],
    pin_operations: Iterable[tuple[Any, tuple[str, ...], tuple[str, ...]]] = (),
) -> None:
    """Apply a quest-log replacement inside the CALLER's transaction.

    Performs no nested transaction and no snapshot/restore of its own: the
    surrounding operation (an inventory plan, reward settlement, or shop
    purchase) has already snapshotted every surface it owns and will restore
    them together on failure. Callers must pass this only between their own
    ``transaction.atomic()`` enter and exit.

    Caller contract (quest-auto-settlement): a record completing under an
    ``AUTO`` issuance settles inside this call, so the caller's snapshot set
    MUST also cover the actor's ``wallet``, ``inventory``, and
    ``guild_reward_claims``, and a raise from this function must abort the
    whole surrounding operation. A completing record also banks its
    quest-completed fixed titles on that actor, so the caller's snapshot set
    MUST cover ``title_collection`` and ``title_equipped`` as well: this
    function performs no restore of its own, so an outer owner that fails after
    it returns is the only place those caches can be returned to their prior
    values. The ACQUIRE completions the paid items trigger release stage pins
    on rooms the caller cannot know; those rooms are snapshotted and restored
    here. Completion notification follows the same rule: it is registered on
    the caller's transaction, so the caller's atomic block is what makes the
    notification a post-commit effect.
    """
    from world.quests.settlement import (
        commit_auto_settlement,
        just_completed_records,
        plan_auto_settlement_chain,
    )
    from world.quests.runtime import to_storage

    old_entries = list(actor.db.quest_log or [])
    plan = plan_auto_settlement_chain(actor, old_entries, new_records)
    completing = just_completed_records(old_entries, new_records)
    pre_chain_entries = [to_storage(record) for record in new_records]
    chain_completing = (
        just_completed_records(
            pre_chain_entries, list(plan.chain_records)
        )
        if plan.chain_records is not None
        else []
    )
    settlement_pin_snapshots = [
        (room, snapshot_pin_reasons(room)) for room, _, _ in plan.chain_pins
    ]
    actor.db.quest_log = [to_storage(record) for record in new_records]
    _apply_pin_operations(pin_operations)
    try:
        commit_auto_settlement(actor, plan)
        if plan.chain_records is not None:
            actor.db.quest_log = [
                to_storage(record) for record in plan.chain_records
            ]
            _apply_pin_operations(plan.chain_pins)
        _settle_quest_completion_events(actor, old_entries, completing)
        _settle_quest_completion_events(actor, pre_chain_entries, chain_completing)
    except Exception:
        for room, snapshot in settlement_pin_snapshots:
            restore_pin_reasons(room, snapshot)
        raise
    _schedule_transition_events(actor, old_entries, new_records)
    if plan.chain_records is not None:
        _schedule_transition_events(
            actor,
            [to_storage(record) for record in new_records],
            list(plan.chain_records),
        )


def pending_effects_for_transition(
    actor: Any,
    new_records: list[Any],
    pin_operations: Iterable[tuple[Any, tuple[str, ...], tuple[str, ...]]] = (),
) -> list[Any]:
    """Expose a computed transition as action ``PendingEffect`` values.

    Produces one ``quest_log`` effect for ``actor`` and one ``instance_pin``
    effect per touched room — plus, when the transition completes quests
    under an ``AUTO`` issuance, one settlement effect carrying the wallet,
    inventory, and reward-claim writes — so ``ActionResolver`` commits them
    atomically with the originating action's own effects (D-4/D-6). The
    settlement's ACQUIRE chain is folded into the quest-log and pin effects
    at planning time, so the resolver writes the final record state exactly
    once. Nothing is notified at planning time: a discarded or rejected plan
    leaves no trace, and the effects finalize the completion fact and register
    its notification only when the resolver applies them inside its own
    atomic block.
    """
    from world.quests.settlement import (
        just_completed_records,
        plan_auto_settlement_chain,
        settlement_pending_effect,
    )
    from world.quests.runtime import to_storage
    from world.rules.action import PendingEffect

    pin_operations = tuple(pin_operations)
    old_entries = list(actor.db.quest_log or [])
    plan = plan_auto_settlement_chain(actor, old_entries, new_records)
    final_records = (
        list(new_records) if plan.chain_records is None else list(plan.chain_records)
    )
    merged_pins = [*pin_operations, *plan.chain_pins]
    # A transition that finalizes a completion also banks that completion's
    # quest-completed fixed titles, so the effect must declare the ``titles``
    # surface: ``ActionResolver`` then snapshots and restores the collection
    # and equipped record together with the log on a failed commit.
    completing = just_completed_records(old_entries, final_records)
    quest_log_surfaces = (
        frozenset({"quest_log", "titles"})
        if completing
        else frozenset({"quest_log"})
    )

    def _apply_quest_log(actor: Any, records: list[Any]) -> None:
        """Write the log and schedule its diff at APPLY time (inside commit)."""
        old_entries = list(actor.db.quest_log or [])
        completing = just_completed_records(old_entries, records)
        actor.db.quest_log = [to_storage(record) for record in records]
        _settle_quest_completion_events(actor, old_entries, completing)
        _schedule_transition_events(actor, old_entries, records)

    effects: list[Any] = [
        PendingEffect(
            actor,
            f"quest_log|{actor.pk}",
            quest_log_surfaces,
            lambda actor=actor, records=final_records: _apply_quest_log(actor, records),
        )
    ]
    for room, adds, removes in merged_pins:
        effects.append(
            PendingEffect(
                room,
                f"instance_pin|{room.pk}",
                frozenset({"instance_pin"}),
                lambda room=room, adds=adds, removes=removes: _apply_pin_operations(
                    ((room, adds, removes),)
                ),
            )
        )
    settlement_effect = settlement_pending_effect(actor, plan)
    if settlement_effect is not None:
        effects.append(settlement_effect)
    return effects