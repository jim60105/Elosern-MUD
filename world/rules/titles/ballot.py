"""Epithet nomination ballot: reads, suppression, and the ballot writers (D4, change G).

The pending ballot is a plain list of ``{"display", "basis"}`` mappings
(1..3, never expiring); the decline log is a bounded newest-first list of
``{"tick", "displays"}`` records — the single durable source for both the
day-boundary cooldown and the Director's softly-learned "recently declined"
digest (no programmatic blacklist: the digest is prompt context only, never a
filter rule).
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from django.db import transaction

from world.lore.titles import NOMINATION_COOLDOWN_DAYS
from world.rules.clock import get_world_clock
from world.rules.event_log import EventEntry, EventLog
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
)
from world.rules.titles.state import (
    BALLOT_BASIS_MAX_CHARS,
    DECLINED_LOG_KEY,
    MAX_BALLOT_CANDIDATES,
    MAX_DECLINE_RECORDS,
    MAX_EPITHET_DISPLAY_CODE_POINTS,
    PENDING_BALLOT_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    TitleDataError,
    _DAY_SECONDS,
    _require_identifier,
    _require_tick,
    bank_epithet,
    banked_epithets,
)
# ---------------------------------------------------------------------------
# Epithet nomination: ballot reads and the rules-layer writers (D4, change G).
# ---------------------------------------------------------------------------
# The ONLY ballot writers are ``persist_nomination_ballot``,
# ``accept_epithet``, and ``decline_epithet_ballot``. The ``world/ai`` layer
# proposes filtered candidates and never touches an attribute; the server-
# side composition-root service schedules the call and hands survivors here
# (single-writer boundary, design §14).


class TitleBallotReason(StrEnum):
    """Stable ballot-answer rejection codes (design §13 error table)."""

    NO_PENDING_BALLOT = "title_no_pending_ballot"
    BALLOT_INDEX_OUT_OF_RANGE = "title_ballot_index_out_of_range"


class TitleBallotError(ValueError):
    """A ballot answer hit a stable reason; no state changed."""

    def __init__(self, reason: TitleBallotReason, detail: str | None = None) -> None:
        super().__init__(detail or reason.value)
        self.reason = reason


def _parse_ballot_entry(entry: Any, index: int) -> dict[str, Any]:
    label = f"pending_title_ballot[{index}]"
    if not isinstance(entry, Mapping):
        raise TitleDataError(f"{label} must be a mapping")
    if set(entry) != {"display", "basis"}:
        raise TitleDataError(f"{label} must hold exactly display/basis")
    display = _require_identifier(entry["display"], f"{label} display")
    basis = _require_identifier(entry["basis"], f"{label} basis")
    if len(display) > MAX_EPITHET_DISPLAY_CODE_POINTS:
        raise TitleDataError(
            f"{label} display exceeds {MAX_EPITHET_DISPLAY_CODE_POINTS} code points"
        )
    if len(basis) > BALLOT_BASIS_MAX_CHARS:
        raise TitleDataError(f"{label} basis exceeds {BALLOT_BASIS_MAX_CHARS}")
    return {"display": display, "basis": basis}


def read_pending_ballot(entity: Any) -> tuple[dict[str, Any], ...]:
    """Strict read of ``pending_title_ballot``; absent or empty reads ``()``.

    Present-but-malformed state raises ``TitleDataError`` (fail closed), the
    same discipline as ``read_title_state``. A stored ballot never expires:
    there is no time-based transition anywhere on this face.
    """
    raw = entity.attributes.get(PENDING_BALLOT_KEY, default=None)
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TitleDataError("pending_title_ballot must be a list")
    if len(raw) > MAX_BALLOT_CANDIDATES:
        raise TitleDataError(
            f"pending_title_ballot holds more than {MAX_BALLOT_CANDIDATES} entries"
        )
    return tuple(_parse_ballot_entry(entry, index) for index, entry in enumerate(raw))


def safe_pending_ballot(entity: Any) -> tuple[dict[str, Any], ...]:
    """Presentation-facing ballot read that degrades to ``()`` on bad state."""
    try:
        return read_pending_ballot(entity)
    except TitleDataError:
        return ()


def decline_records(entity: Any) -> tuple[dict[str, Any], ...]:
    """Strict read of the bounded decline log (newest-first storage order)."""
    raw = entity.attributes.get(DECLINED_LOG_KEY, default=None)
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TitleDataError("title_nomination_declines must be a list")
    if len(raw) > MAX_DECLINE_RECORDS:
        raise TitleDataError(
            f"title_nomination_declines exceeds the {MAX_DECLINE_RECORDS}-record cap"
        )
    records: list[dict[str, Any]] = []
    for index, record in enumerate(raw):
        label = f"title_nomination_declines[{index}]"
        if not isinstance(record, Mapping) or set(record) != {"tick", "displays"}:
            raise TitleDataError(f"{label} must hold exactly tick/displays")
        tick = _require_tick(record["tick"], f"{label} tick")
        displays = record["displays"]
        if (
            not isinstance(displays, Sequence)
            or isinstance(displays, (str, bytes))
            or not 1 <= len(displays) <= MAX_BALLOT_CANDIDATES
        ):
            raise TitleDataError(
                f"{label} displays must be a 1..{MAX_BALLOT_CANDIDATES} list"
            )
        items = tuple(
            _require_identifier(display, f"{label} display") for display in displays
        )
        records.append({"tick": tick, "displays": items})
    return tuple(records)


def nomination_cooldown_active(entity: Any, now_tick: int | None = None) -> bool:
    """Whether the decline-derived cooldown still suppresses nomination.

    Cooldown is derived from the newest decline record: it is active while
    fewer than ``NOMINATION_COOLDOWN_DAYS`` day boundaries have passed since
    the decline (same day and the next day suppressed; nominations resume on
    the second boundary). Accepting a ballot never records a decline, so an
    accepted ballot never starts a cooldown.
    """
    records = decline_records(entity)
    if not records:
        return False
    tick = get_world_clock().tick if now_tick is None else now_tick
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise TitleDataError("now_tick must be a non-negative integer")
    declined_day = max(record["tick"] for record in records) // _DAY_SECONDS
    return tick // _DAY_SECONDS - declined_day < NOMINATION_COOLDOWN_DAYS


def nomination_suppressed(entity: Any, now_tick: int | None = None) -> bool:
    """Single-ballot + cooldown suppression, fail-closed on malformed state.

    A corrupt nomination face suppresses the writer silently (the ballot was
    never ours to guess) while presentation still degrades to an empty menu
    through ``safe_pending_ballot``.
    """
    try:
        if read_pending_ballot(entity):
            return True
        return nomination_cooldown_active(entity, now_tick)
    except TitleDataError:
        return True


def owned_epithet_displays(entity: Any) -> frozenset[str]:
    """Live collection epithet displays for the collision filter.

    Deleted names are absent here by construction, so they are renominable
    (D5 collision semantics; no blacklist exists anywhere).
    """
    return frozenset(
        entry["display"] for entry in banked_epithets(entity)
    )


def declined_digest(entity: Any, limit: int = MAX_DECLINE_RECORDS) -> tuple[str, ...]:
    """Distinct recent decline-log displays for the prompt's soft-learning
    digest (newest record first). Malformed history degrades to empty; this
    is prompt context only and never a filter rule.
    """
    try:
        records = decline_records(entity)
    except TitleDataError:
        return ()
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("declined_digest limit must be a non-negative int")
    seen: set[str] = set()
    digest: list[str] = []
    for record in records[:limit]:
        for display in record["displays"]:
            if display not in seen:
                seen.add(display)
                digest.append(display)
    return tuple(digest)


def persist_nomination_ballot(entity: Any, candidates: Any) -> bool:
    """The rules-layer-only ballot persist (DG2): re-check suppression after
    the proposal returns, then persist in one all-or-nothing step.

    Validates the wire shape (1..3 ``{display, basis}`` entries within the
    storage caps); anything invalid, a suppressed entity, or a failed write
    returns ``False`` and leaves no partial proposal.
    """
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return False
    if not 1 <= len(candidates) <= MAX_BALLOT_CANDIDATES:
        return False
    normalized: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        try:
            normalized.append(_parse_ballot_entry(candidate, index))
        except TitleDataError:
            return False
    now_tick = get_world_clock().tick
    if nomination_suppressed(entity, now_tick):
        return False
    ballot_snapshot = attribute_snapshot(entity, PENDING_BALLOT_KEY)
    try:
        with transaction.atomic():
            entity.attributes.add(PENDING_BALLOT_KEY, normalized)
    except Exception:
        restore_attribute_best_effort(
            entity, PENDING_BALLOT_KEY, ballot_snapshot
        )
        return False
    return True


def accept_epithet(entity: Any, index: int) -> tuple[str, bool]:
    """Adopt the 1-based ballot candidate (D4 §7.2-6).

    One atomic, snapshot-registered transaction banks the entry
    (display, ``origin_quote = basis``, granted_tick), auto-equips the
    epithet slot only when empty (bank_epithet's D8 discipline), and clears
    the ballot. Returns ``(display, newly_banked)``; ``newly_banked`` is
    ``False`` when an identical display entered the collection between the
    ballot and the answer (the bank dedupes; the ballot is consumed either
    way). Stable ``TitleBallotError`` reasons change nothing.
    """
    ballot = read_pending_ballot(entity)
    if not ballot:
        raise TitleBallotError(TitleBallotReason.NO_PENDING_BALLOT)
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 1 <= index <= len(ballot)
    ):
        raise TitleBallotError(TitleBallotReason.BALLOT_INDEX_OUT_OF_RANGE)
    entry = ballot[index - 1]
    tick = get_world_clock().tick
    collection_snapshot = attribute_snapshot(entity, TITLE_COLLECTION_KEY)
    equipped_snapshot = attribute_snapshot(entity, TITLE_EQUIPPED_KEY)
    ballot_snapshot = attribute_snapshot(entity, PENDING_BALLOT_KEY)
    try:
        with transaction.atomic():
            banked = bank_epithet(entity, entry["display"], entry["basis"], tick)
            entity.attributes.remove(PENDING_BALLOT_KEY)
    except Exception:
        restore_attribute_best_effort(
            entity, TITLE_COLLECTION_KEY, collection_snapshot
        )
        restore_attribute_best_effort(
            entity, TITLE_EQUIPPED_KEY, equipped_snapshot
        )
        restore_attribute_best_effort(
            entity, PENDING_BALLOT_KEY, ballot_snapshot
        )
        raise
    return entry["display"], banked


def decline_epithet_ballot(entity: Any) -> EventLog:
    """Discard the batch, start the cooldown, and record what was declined.

    The declined displays persist to the bounded decline log — the single
    durable feed the nomination prompt digests so the Director's future
    summaries see what the player rejected (soft learning; there is no
    programmatic blacklist) — and are returned as a
    ``title_epithet_declined`` EventLog for the answering surface to render
    and for the EventLog consumers. Raises ``TitleBallotError`` when no
    ballot is pending; malformed decline history raises ``TitleDataError``
    and changes NOTHING (fail-closed — the corrupt cooldown source is never
    silently overwritten by a player answer).
    """
    ballot = read_pending_ballot(entity)
    if not ballot:
        raise TitleBallotError(TitleBallotReason.NO_PENDING_BALLOT)
    displays = tuple(entry["display"] for entry in ballot)
    tick = get_world_clock().tick
    record = {"tick": tick, "displays": list(displays)}
    history = [dict(entry) for entry in decline_records(entity)]
    log_snapshot = attribute_snapshot(entity, DECLINED_LOG_KEY)
    ballot_snapshot = attribute_snapshot(entity, PENDING_BALLOT_KEY)
    try:
        with transaction.atomic():
            entity.attributes.add(
                DECLINED_LOG_KEY, [record, *history][:MAX_DECLINE_RECORDS]
            )
            entity.attributes.remove(PENDING_BALLOT_KEY)
    except Exception:
        restore_attribute_best_effort(entity, DECLINED_LOG_KEY, log_snapshot)
        restore_attribute_best_effort(
            entity, PENDING_BALLOT_KEY, ballot_snapshot
        )
        raise
    entry = EventEntry(
        kind="title_epithet_declined",
        actor=str(entity.key),
        target=None,
        data={"displays": list(displays), "joined": "、".join(displays)},
        text_template="{actor}拒絕了異名提名：{data[joined]}",
    )
    return EventLog(
        actor=str(entity.key),
        skill_key="title",
        targets=(),
        entries=(entry,),
        time_cost_seconds=0,
    )

