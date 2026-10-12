"""Durable exclusive-group state and consumed escort events (escort design §7).

The quest package owns these two records directly, exactly as it owns the scene
package rows (AGENTS.md single-writer boundary). Both are database-unique, which
is why they are Django rows rather than another ``db`` list:

* ``ExclusiveOutcomeGroup`` — one resolution row per ``(owner, package, group)``,
  carrying the committed source, the winner or the explicit no-commission
  result, and the monotonic ``next_sequence`` from which acceptance sequences
  are allocated (world tick alone cannot order two acceptances in one tick);
* ``EscortEventTransition`` — one row per ``(owner, record, source)`` actually
  consumed, so a pre-follow receive and a post-follow recheck, or a replayed
  settled movement after a committed reload, can never advance a record twice.

Every uniqueness-bearing write goes through ``get_or_create`` or an
integrity-guarded insert instead of a "check then write": SQLite serializes
writers, so the database constraint is the arbiter and no list scan stands in
for it. Reads are plain queries. Nothing here arbitrates a result — the store
only persists what its owner decides.
"""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from world.observability import log_info

from .models import EscortEventTransition, ExclusiveOutcomeGroup


def get_or_create_group(
    *,
    owner_id: int,
    package_id: str,
    group_id: str,
    tick: int = 0,
) -> ExclusiveOutcomeGroup:
    """Return the one durable group row for this identity, creating it once.

    ``(owner_id, package_id, group_id)`` is database-unique, so two concurrent
    creators converge on one row: the insert is attempted and an
    ``IntegrityError`` is resolved by re-reading the committed identity rather
    than by trusting a prior read.
    """
    identity = {
        "owner_id": int(owner_id),
        "package_id": str(package_id),
        "group_id": str(group_id),
    }
    row = ExclusiveOutcomeGroup.objects.filter(**identity).first()
    if row is not None:
        return row
    try:
        with transaction.atomic():
            row = ExclusiveOutcomeGroup.objects.create(
                **identity, next_sequence=1, updated_tick=int(tick)
            )
    except IntegrityError:  # observability: ignore R2: the unique constraint is the arbiter here; the committed row is re-read and returned, so no failure is hidden
        row = ExclusiveOutcomeGroup.objects.filter(**identity).first()
        if row is None:  # pragma: no cover - the constraint implies the row exists
            raise
        return row
    log_info(
        "escort_outcome_group_created",
        context={
            "owner": str(identity["owner_id"]),
            "package": identity["package_id"],
            "group": identity["group_id"],
            "tick": str(tick),
        },
    )
    return row


def read_group(
    *,
    owner_id: int,
    package_id: str,
    group_id: str,
) -> ExclusiveOutcomeGroup | None:
    """Read one owner's group state without mutating anything."""
    return ExclusiveOutcomeGroup.objects.filter(
        owner_id=int(owner_id),
        package_id=str(package_id),
        group_id=str(group_id),
    ).first()


def allocate_acceptance_sequence(
    *,
    owner_id: int,
    package_id: str,
    group_id: str,
    tick: int = 0,
) -> int:
    """Allocate the group's next monotonic acceptance sequence.

    The read-and-increment runs inside one ``transaction.atomic()` block against
    the unique group row, so two acceptances in the same world tick still get
    distinct, ordered sequences. The group is created on first use.
    """
    identity = {
        "owner_id": int(owner_id),
        "package_id": str(package_id),
        "group_id": str(group_id),
    }
    with transaction.atomic():
        row = (
            ExclusiveOutcomeGroup.objects.select_for_update()
            .filter(**identity)
            .first()
        )
        if row is None:
            row = get_or_create_group(**identity, tick=tick)
            row.refresh_from_db()
        sequence = int(row.next_sequence)
        row.next_sequence = sequence + 1
        row.updated_tick = int(tick)
        row.save(update_fields=["next_sequence", "updated_tick"])
    return sequence


def mark_group_resolved(
    *,
    owner_id: int,
    package_id: str,
    group_id: str,
    resolution_source: str,
    winner_quest_id: str = "",
    no_commission: bool = False,
    tick: int = 0,
) -> ExclusiveOutcomeGroup:
    """Persist one group's committed resolution state.

    The caller owns the arbitration decision; this writer only records it, so a
    resolved group always names its committed source and either its winning
    accepted record or the explicit no-commission result. ``no_commission`` and
    ``winner_quest_id`` are mutually exclusive: an unaccepted physical result
    has no winning record.
    """
    if no_commission and winner_quest_id:
        raise ValueError(
            "a resolved group records either a winning record or an explicit "
            "no-commission result, never both"
        )
    if not resolution_source:
        raise ValueError("a resolved group must name its committed source")
    row = get_or_create_group(
        owner_id=owner_id, package_id=package_id, group_id=group_id, tick=tick
    )
    if row.resolved:
        return row
    row.resolved = True
    row.resolution_source = str(resolution_source)
    row.winner_quest_id = str(winner_quest_id or "")
    row.no_commission = bool(no_commission)
    row.updated_tick = int(tick)
    row.save(
        update_fields=[
            "resolved",
            "resolution_source",
            "winner_quest_id",
            "no_commission",
            "updated_tick",
        ]
    )
    log_info(
        "escort_outcome_group_resolved",
        context={
            "owner": str(int(owner_id)),
            "package": str(package_id),
            "group": str(group_id),
            "source": str(resolution_source),
            "winner": str(winner_quest_id or ""),
            "no_commission": "1" if no_commission else "0",
            "tick": str(tick),
        },
    )
    return row


def consume_transition(
    *,
    owner_id: int,
    record_id: str,
    source_key: str,
    tick: int = 0,
) -> bool:
    """Consume one ``(owner, record, source)`` transition identity.

    Returns ``True`` when this call consumed the identity for the first time and
    ``False`` when it was already consumed — the evaluator inserts a row only
    when a stage advanced or a resolution was attributed, so a repeat of the
    same stable source advances nothing. The uniqueness is the database's, not a
    prior read's.
    """
    identity = {
        "owner_id": int(owner_id),
        "record_id": str(record_id),
        "source_key": str(source_key),
    }
    try:
        with transaction.atomic():
            EscortEventTransition.objects.create(**identity, consumed_tick=int(tick))
    except IntegrityError:  # observability: ignore R2: an already-consumed identity is the normal replay path, reported to the caller as False rather than as an error
        return False
    return True


def transition_consumed(
    *,
    owner_id: int,
    record_id: str,
    source_key: str,
) -> bool:
    """Whether one transition identity is already consumed (read-only)."""
    return (
        EscortEventTransition.objects.filter(
            owner_id=int(owner_id),
            record_id=str(record_id),
            source_key=str(source_key),
        ).first()
        is not None
    )


def list_owner_groups(owner_id: int) -> tuple[Any, ...]:
    """Every group row this owner holds, in identity order (read-only)."""
    return tuple(
        ExclusiveOutcomeGroup.objects.filter(owner_id=int(owner_id)).order_by(
            "package_id", "group_id"
        )
    )


def package_owner_ids(package_id: str) -> tuple[int, ...]:
    """Read durable group reverse references after process restart."""
    return tuple(ExclusiveOutcomeGroup.objects.filter(
        package_id=package_id,
    ).values_list("owner_id", flat=True).distinct())


def has_resolved_group(package_id: str) -> bool:
    """Whether any exclusive group of ``package_id`` has committed a result.

    Read-only and owner-agnostic: the committed result is a package-level fact
    the persistent story roles select their acknowledgment phase from
    (escort-rendezvous §7).
    """
    return ExclusiveOutcomeGroup.objects.filter(
        package_id=str(package_id), resolved=True,
    ).exists()


__all__ = [
    "allocate_acceptance_sequence",
    "consume_transition",
    "get_or_create_group",
    "has_resolved_group",
    "list_owner_groups",
    "mark_group_resolved",
    "read_group",
    "transition_consumed",
]