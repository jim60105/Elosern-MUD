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
    emits its events. ``old_entries`` is the raw stored log captured BEFORE
    the write; callbacks registered through ``transaction.on_commit`` fire only
    on the outermost commit and are discarded on rollback, so a rolled-back
    operation leaves no event behind. Malformed logs skip the diff:
    observability must never affect a lifecycle write.
    """
    try:
        before: dict[str, tuple] = {}
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


def apply_quest_log_replacement(
    actor: Any,
    new_records: list[Any],
    pin_operations: Iterable[tuple[Any, tuple[str, ...], tuple[str, ...]]] = (),
) -> None:
    """Replace one quest log and apply a pin delta atomically with restore."""
    from world.quests.runtime import to_storage

    pin_operations = tuple(pin_operations)
    actor_snapshot = snapshot_quest_log(actor)
    room_snapshots = {
        id(room): snapshot_pin_reasons(room) for room, _, _ in pin_operations
    }
    old_entries: list[Any] = []
    try:
        with transaction.atomic():
            old_entries = list(actor.db.quest_log or [])
            actor.db.quest_log = [to_storage(record) for record in new_records]
            _apply_pin_operations(pin_operations)
    except Exception:
        restore_quest_log(actor, actor_snapshot)
        for room, _, _ in pin_operations:
            restore_pin_reasons(room, room_snapshots[id(room)])
        raise
    _schedule_transition_events(actor, old_entries, new_records)


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
    """
    from world.quests.runtime import to_storage

    old_entries = list(actor.db.quest_log or [])
    actor.db.quest_log = [to_storage(record) for record in new_records]
    _apply_pin_operations(pin_operations)
    _schedule_transition_events(actor, old_entries, new_records)


def pending_effects_for_transition(
    actor: Any,
    new_records: list[Any],
    pin_operations: Iterable[tuple[Any, tuple[str, ...], tuple[str, ...]]] = (),
) -> list[Any]:
    """Expose a computed transition as action ``PendingEffect`` values.

    Produces one ``quest_log`` effect for ``actor`` and one ``instance_pin``
    effect per touched room so ``ActionResolver`` can commit them atomically
    with the originating action's own effects (D-4/D-6).
    """
    from world.quests.runtime import to_storage
    from world.rules.action import PendingEffect

    pin_operations = tuple(pin_operations)

    def _apply_quest_log(actor: Any, records: list[Any]) -> None:
        """Write the log and schedule its diff at APPLY time (inside commit)."""
        old_entries = list(actor.db.quest_log or [])
        actor.db.quest_log = [to_storage(record) for record in records]
        _schedule_transition_events(actor, old_entries, records)

    effects: list[Any] = [
        PendingEffect(
            actor,
            f"quest_log|{actor.pk}",
            frozenset({"quest_log"}),
            lambda actor=actor, records=new_records: _apply_quest_log(actor, records),
        )
    ]
    for room, adds, removes in pin_operations:
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
    return effects