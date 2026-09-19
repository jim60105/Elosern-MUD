"""Epithet removal (change H, title-system D5 §8) — the ONLY delete path.

The bounded newest-first removal log is the durable Director-facing feed
mirroring the decline log: ``{tick, display}`` records the nomination prompt
digests as soft-learning context (prompt context only, never a filter rule —
the removed name is renominatable through the live-collection filter).

The two-gated removal deletes exactly one epithet collection entry, never a
fixed entry and never an equipped-identifier list, and leaves the equipment
slots byte-identical; the D8 invariant stays structurally unbreakable. No
module-level callable other than ``remove_epithet`` deletes a title entry (the
structural-absence boundary test guards this).
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from django.db import transaction

from world.rules.clock import get_world_clock
from world.rules.event_log import EventEntry, EventLog
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
)
from world.rules.titles.state import (
    MAX_REMOVAL_RECORDS,
    REMOVALS_LOG_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    TitleDataError,
    _EPITHET_KIND,
    _require_identifier,
    _require_tick,
    _write_title_state,
    read_title_state,
)

# ---------------------------------------------------------------------------
# Epithet removal (change H, title-system D5 §8) — the ONLY delete path.
# ---------------------------------------------------------------------------


class TitleRemovalReason(StrEnum):
    """Stable removal-gate rejection codes (design §13 error table)."""

    TARGET_UNKNOWN = "title_removal_target_unknown"
    LAST_EPITHET = "title_last_epithet"
    EQUIPPED_UNREMOVABLE = "title_equipped_unremovable"


class TitleRemovalError(ValueError):
    """A removal attempt hit a stable gate; no state changed."""

    def __init__(self, reason: TitleRemovalReason, detail: str | None = None) -> None:
        super().__init__(detail or reason.value)
        self.reason = reason


def epithet_removal_gate(
    entity: Any, display: Any
) -> TitleRemovalReason | None:
    """Pure two-gate verdict; ``None`` means the removal may proceed.

    Gate precedence (design DH1): unknown/wrong-kind first, then
    ``LAST_EPITHET``, then ``EQUIPPED_UNREMOVABLE`` — a sole epithet is
    necessarily equipped (D8), and the spec scenario demands LAST for that
    row, so LAST is evaluated before EQUIPPED. Malformed title state
    propagates ``TitleDataError`` (fail closed).
    """
    if isinstance(display, bool) or not isinstance(display, str) or not display:
        return TitleRemovalReason.TARGET_UNKNOWN
    collection, equipped = read_title_state(entity)
    epithets = [entry for entry in collection if entry["kind"] == _EPITHET_KIND]
    if not any(entry["display"] == display for entry in epithets):
        return TitleRemovalReason.TARGET_UNKNOWN
    if len(epithets) <= 1:
        return TitleRemovalReason.LAST_EPITHET
    if display == equipped["epithet"]:
        return TitleRemovalReason.EQUIPPED_UNREMOVABLE
    return None


def removal_records(entity: Any) -> tuple[dict[str, Any], ...]:
    """Strict read of the bounded removal log (newest-first storage order)."""
    raw = entity.attributes.get(REMOVALS_LOG_KEY, default=None)
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TitleDataError("title_epithet_removals must be a list")
    if len(raw) > MAX_REMOVAL_RECORDS:
        raise TitleDataError(
            f"title_epithet_removals exceeds the {MAX_REMOVAL_RECORDS}-record cap"
        )
    records: list[dict[str, Any]] = []
    for index, record in enumerate(raw):
        label = f"title_epithet_removals[{index}]"
        if not isinstance(record, Mapping) or set(record) != {"tick", "display"}:
            raise TitleDataError(f"{label} must hold exactly tick/display")
        records.append(
            {
                "tick": _require_tick(record["tick"], f"{label} tick"),
                "display": _require_identifier(
                    record["display"], f"{label} display"
                ),
            }
        )
    return tuple(records)


def removal_digest(
    entity: Any, limit: int = MAX_REMOVAL_RECORDS
) -> tuple[str, ...]:
    """Distinct recent removal-log displays for the nomination prompt's
    soft-learning digest (newest record first). Malformed history degrades to
    empty; this is prompt context only and never a filter rule — a removed
    name stays renominatable through the live-collection collision filter.
    """
    try:
        records = removal_records(entity)
    except TitleDataError:
        return ()
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("removal_digest limit must be a non-negative int")
    seen: set[str] = set()
    digest: list[str] = []
    for record in records[:limit]:
        display = record["display"]
        if display not in seen:
            seen.add(display)
            digest.append(display)
    return tuple(digest)


def remove_epithet(entity: Any, display: Any) -> EventLog:
    """Delete exactly one banked epithet; the ONLY delete path in the surface.

    One gate pass executes (answering surfaces re-validate at execution
    time): a gated target raises ``TitleRemovalError`` and a malformed state
    raises ``TitleDataError``, each with NOTHING changed. On success the
    collection shrinks by exactly the one entry, the durable bounded removal
    log gains a newest-first ``{tick, display}`` record in the same
    transaction, and the equipment slots are written back unchanged — a
    removal can never empty a slot or orphan an identifier, so the D8
    invariant is structurally unbreakable here. Returns a renderable
    ``title_epithet_removed`` EventLog (``decline_epithet_ballot`` shape)
    for the answering surface and the EventLog consumers.
    """
    reason = epithet_removal_gate(entity, display)
    if reason is not None:
        raise TitleRemovalError(reason)
    tick = get_world_clock().tick
    collection, equipped = read_title_state(entity)
    new_collection = [
        entry
        for entry in collection
        if not (entry["kind"] == _EPITHET_KIND and entry["display"] == display)
    ]
    record = {"tick": tick, "display": display}
    history = [dict(entry) for entry in removal_records(entity)]
    collection_snapshot = attribute_snapshot(entity, TITLE_COLLECTION_KEY)
    equipped_snapshot = attribute_snapshot(entity, TITLE_EQUIPPED_KEY)
    removals_snapshot = attribute_snapshot(entity, REMOVALS_LOG_KEY)
    try:
        with transaction.atomic():
            _write_title_state(entity, new_collection, equipped)
            entity.attributes.add(
                REMOVALS_LOG_KEY, [record, *history][:MAX_REMOVAL_RECORDS]
            )
    except Exception:
        restore_attribute_best_effort(
            entity, TITLE_COLLECTION_KEY, collection_snapshot
        )
        restore_attribute_best_effort(
            entity, TITLE_EQUIPPED_KEY, equipped_snapshot
        )
        restore_attribute_best_effort(
            entity, REMOVALS_LOG_KEY, removals_snapshot
        )
        raise
    entry = EventEntry(
        kind="title_epithet_removed",
        actor=str(entity.key),
        target=None,
        data={"display": display, "tick": tick},
        text_template="{actor}放下了異名：{data[display]}",
    )
    return EventLog(
        actor=str(entity.key),
        skill_key="title",
        targets=(),
        entries=(entry,),
        time_cost_seconds=0,
    )