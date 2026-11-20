"""City voluntary-sleep policy and deterministic patrol settlement.

Location policy is resolved from authored identity only: a permanent interior's
published room tag and its exterior settlement, a settlement grid node's
published map and authored ``AnchorKind``, or a generated lodging guest room's
explicit place key. Display names, room prose and artwork are never consulted,
and a village/hamlet is never treated as a city.

The clock applies city patrols deterministically from the authored rulebook:
one patrol at a fixed phase after each game-day start and then at a fixed
interval. A patrol that reaches an active voluntary street nap ends it, credits
only the elapsed prefix, records the remaining-day refusal for the canonical
party owner and street, and never touches a forced sleeper. Patrol times are
never disclosed to the player.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from django.db import transaction

from world.observability import log_info
from world.rules.clock import (
    CLOCK_YAML,
    ScheduledEvent,
    SurfaceSnapshot,
    current_advance_scope,
    register_event_source,
    settle_gauge_regeneration,
)
from world.rules.fatigue import (
    FATIGUE_ATTRIBUTE_SURFACES,
    FatigueActivity,
    FatigueInterval,
    IntervalCompletion,
    SleepPosture,
    project_fatigue_status,
    read_optional_fatigue_state,
    settle_fatigue_intervals,
    write_fatigue_state,
)
from world.rules.rest_bonuses import (
    SURFACES as REST_BONUS_SURFACES,
    clear_paid_sleep,
    clear_street_nap,
    read_street_nap,
    record_street_refusal,
    street_refused,
)
from world.rules.rulebook.schema import SectionedRule, load_sectioned_rules
from world.rules.sleep_receipt import (
    KIND_VOLUNTARY,
    SLEEP_RECEIPT_SURFACES,
    STATE_INTERRUPTED,
    SleepReceipt,
    SleepReceiptError,
    read_sleep_receipt,
    recovery_target_tick,
    write_sleep_receipt,
)
from world.rules.surfaces import attribute_snapshot

RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "inn_lodging.yaml"

#: Tag category and key naming every body with an active street nap. The clock
#: source uses it to discover naps without scanning every character.
STREET_NAP_TAG_CATEGORY = "city_sleep"
STREET_NAP_TAG = "street_nap"

#: The authored settlement kinds whose streets and interiors follow the city
#: policy. Villages and hamlets deliberately do not.
CITY_ANCHOR_KINDS = frozenset({"capital", "city", "port", "town"})

_DAY_SECONDS = int(CLOCK_YAML["seconds_per_hour"]) * int(CLOCK_YAML["hours_per_day"])

_PATROL_EVENT = "street_nap_interrupted"


class CitySleepError(ValueError):
    """The shipped policy rulebook violates its contract."""


class SleepLocation(StrEnum):
    """The voluntary-sleep classification of one authored location."""

    OPEN = "open"
    STREET = "street"
    LODGING_LOBBY = "lodging_lobby"
    GUEST_ROOM = "guest_room"
    REFUSED = "refused"


@dataclass(frozen=True)
class SleepPlace:
    """One classified location, with the authored identities that decided it."""

    kind: SleepLocation
    place_key: str | None = None
    settlement_key: str | None = None
    street: str | None = None


@dataclass(frozen=True)
class CitySleepPolicy:
    """The validated, immutable policy loaded from ``inn_lodging.yaml``."""

    messages: Mapping[str, str]
    price_per_guest_copper: int
    well_rested_allowance_seconds: int
    patrol_interval_seconds: int
    patrol_phase_offset_seconds: int


def _require_int(where: str, data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CitySleepError(f"{where}: {key} must be an integer")
    return value


def _build_policy(rows: list[SectionedRule]) -> CitySleepPolicy:
    ints: dict[str, int] = {}
    messages: dict[str, str] = {}
    for row in rows:
        where = f"row {row.id!r}"
        if row.section in ("price", "allowance", "patrol"):
            if set(row.data) != {"value"}:
                raise CitySleepError(f"{where}: carries exactly value")
            ints[row.id] = _require_int(where, row.data, "value")
        elif row.section == "message":
            if set(row.data) != {"value"}:
                raise CitySleepError(f"{where}: carries exactly value")
            value = row.data.get("value")
            if not isinstance(value, str) or not value.strip():
                raise CitySleepError(f"{where}: message must be non-empty text")
            messages[row.id] = value
        else:
            raise CitySleepError(f"{where}: unknown section {row.section!r}")
    required_ints = {
        "price_per_guest_copper",
        "well_rested_allowance_seconds",
        "patrol_interval_seconds",
        "patrol_phase_offset_seconds",
    }
    if set(ints) != required_ints:
        raise CitySleepError(
            f"integer rows must be exactly {sorted(required_ints)}, got {sorted(ints)}"
        )
    required_messages = {
        "street_warning",
        "street_refusal",
        "city_sleep_refused",
        "lobby_requires_booking",
        "guest_sleep_requires_booking",
        "guest_sleep_spent",
        "camp_in_city",
        "booking_overlap",
        "quote_stale",
        "blocked_guest",
        "unauthorized_entry",
        "quote_line",
        "checkin_confirmed",
        "no_lodging_service",
        "payer_absent",
        "street_interrupted",
    }
    if set(messages) != required_messages:
        raise CitySleepError(
            "message rows must be exactly "
            f"{sorted(required_messages)}, got {sorted(messages)}"
        )
    if ints["price_per_guest_copper"] <= 0:
        raise CitySleepError("price_per_guest_copper must be positive")
    if not 0 < ints["well_rested_allowance_seconds"] <= 86400:
        raise CitySleepError("well_rested_allowance_seconds must be within one day")
    interval = ints["patrol_interval_seconds"]
    offset = ints["patrol_phase_offset_seconds"]
    if interval <= 0 or interval > _DAY_SECONDS or _DAY_SECONDS % interval:
        raise CitySleepError(
            "patrol_interval_seconds must tile one game day exactly"
        )
    if not 0 <= offset < interval:
        raise CitySleepError(
            "patrol_phase_offset_seconds must lie within one patrol interval"
        )
    return CitySleepPolicy(
        messages=messages,
        price_per_guest_copper=ints["price_per_guest_copper"],
        well_rested_allowance_seconds=ints["well_rested_allowance_seconds"],
        patrol_interval_seconds=interval,
        patrol_phase_offset_seconds=offset,
    )


def load_policy(path: Path | None = None) -> CitySleepPolicy:
    """Load and fail-closed validate the inn/city policy rulebook."""
    rulebook_path = RULEBOOK_PATH if path is None else Path(path)
    try:
        return _build_policy(load_sectioned_rules(rulebook_path))
    except (OSError, ValueError) as error:
        raise CitySleepError(str(error)) from error


_POLICY: CitySleepPolicy | None = None


def get_policy() -> CitySleepPolicy:
    """Return the validated policy singleton."""
    global _POLICY
    if _POLICY is None:
        _POLICY = load_policy()
    return _POLICY


def message(key: str) -> str:
    """Return one authored player-facing policy message."""
    return get_policy().messages[key]


# -- calendar and patrol arithmetic -----------------------------------------


def day_index(tick: int) -> int:
    """The zero-based game-day index of ``tick``."""
    return int(tick) // _DAY_SECONDS


def next_patrol_tick(tick: int) -> int:
    """The first patrol tick strictly after ``tick``."""
    policy = get_policy()
    tick = int(tick)
    day_start = tick - (tick % _DAY_SECONDS)
    candidate = day_start + policy.patrol_phase_offset_seconds
    if candidate <= tick:
        interval = policy.patrol_interval_seconds
        steps = (tick - candidate) // interval + 1
        candidate += steps * interval
    return candidate


# -- authored location classification --------------------------------------


def _published_interiors() -> Any | None:
    from world.maps import interiors

    if not interiors.is_published():
        return None
    return interiors.current()


def _interior_room_id(room: Any, snapshot: Any) -> str | None:
    tags = getattr(room, "tags", None)
    all_tags = getattr(tags, "all", None)
    if not callable(all_tags) or snapshot is None:
        return None
    present = set(all_tags())
    for room_id in snapshot.rooms:
        if room_id in present:
            return room_id
    return None


def _city_location(location_key: str | None) -> bool:
    if not isinstance(location_key, str) or not location_key:
        return False
    from world.maps import geography

    if not geography.is_published():
        return False
    anchor = geography.current().anchors.get(location_key)
    if anchor is None:
        return False
    return anchor.kind.value in CITY_ANCHOR_KINDS


def _place_for_room(room: Any, room_id: str | None) -> Any | None:
    if room_id is None:
        return None
    from world.lore.settlements import PLACE_REGISTRY

    return PLACE_REGISTRY.get(room_id)


def _place_is_lodging(place: Any) -> bool:
    from world.lore.settlements.places import place_capabilities

    return bool(place_capabilities(place, "lodging"))


def _street_identity(room: Any) -> str | None:
    try:
        xyz = getattr(room, "xyz", None)
    except Exception:  # observability: ignore R2: a room without grid identity is simply not a settlement street
        return None
    if not xyz or len(xyz) < 3:
        return None
    map_id = str(xyz[2])
    node_id = getattr(room, "sparse_node_id", None)
    if not isinstance(node_id, str) or not node_id:
        node_id = f"room:{getattr(room, 'pk', '?')}"
    return f"{map_id}:{node_id}"


def _street_settlement(map_id: str) -> str | None:
    from world.maps import map_data

    if not map_data.is_published():
        return None
    document = map_data.current().settlements.get(map_id)
    return None if document is None else document.location_ref


def classify_room(room: Any) -> SleepPlace:
    """Classify one authored room for voluntary-sleep policy (pure read).

    Generated lodging guest rooms carry their own explicit place key. A
    permanent interior resolves through its published room tag to the place
    registry (for lodging) and to its authored exterior settlement (for the
    city rule). A settlement grid node resolves through its published map and
    the authored geographic ``AnchorKind``. Everything else keeps the existing
    open behavior.
    """
    if room is None:
        return SleepPlace(SleepLocation.OPEN)
    guest_place = getattr(room, "lodging_place_key", None)
    if isinstance(guest_place, str) and guest_place:
        return SleepPlace(SleepLocation.GUEST_ROOM, place_key=guest_place)
    snapshot = _published_interiors()
    room_id = _interior_room_id(room, snapshot)
    place = _place_for_room(room, room_id)
    if place is not None:
        if _place_is_lodging(place):
            return SleepPlace(
                SleepLocation.LODGING_LOBBY,
                place_key=place.key,
                settlement_key=place.settlement_key,
            )
        if _city_location(place.settlement_key):
            return SleepPlace(
                SleepLocation.REFUSED,
                place_key=place.key,
                settlement_key=place.settlement_key,
            )
        return SleepPlace(SleepLocation.OPEN, place_key=place.key)
    if room_id is not None and snapshot is not None:
        from world.maps import interiors

        exterior = interiors.exterior_for(room_id)
        settlement = None if exterior is None else exterior.settlement
        if _city_location(settlement):
            return SleepPlace(SleepLocation.REFUSED, settlement_key=settlement)
        return SleepPlace(SleepLocation.OPEN)
    street = _street_identity(room)
    if street is not None:
        settlement = _street_settlement(street.split(":", 1)[0])
        if _city_location(settlement):
            return SleepPlace(
                SleepLocation.STREET, settlement_key=settlement, street=street
            )
    return SleepPlace(SleepLocation.OPEN)


def sleep_location_warning(entity: Any) -> str | None:
    """The generic, schedule-free warning a street nap shows, if any."""
    place = classify_room(getattr(entity, "location", None))
    if place.kind is SleepLocation.STREET:
        return message("street_warning")
    return None


# -- voluntary-sleep admission ----------------------------------------------


def _party_owner(entity: Any) -> Any:
    try:
        from world.rules.party_scope import resolve_commander

        return resolve_commander(entity)
    except Exception:  # observability: ignore R2: a body outside any resolvable party is its own owner for the refusal record
        return entity


def require_voluntary_sleep(
    entity: Any, *, transport: str = "sleep"
) -> SleepPlace:
    """Refuse one entrant's voluntary sleep under the shared location policy.

    ``transport='camp'`` is the whole-party wilderness camp: a city street,
    city interior or guest room refuses it exactly like any other city
    location. Forced sleep and awake rest/wait never pass through this gate.
    The guest-room booking and paid-entitlement checks live with the lodging
    owner and are imported lazily.
    """
    from world.rules.time_skip import SleepRefused

    place = classify_room(getattr(entity, "location", None))
    if transport == "camp":
        if place.kind is not SleepLocation.OPEN:
            raise SleepRefused("camp_refused_city", message("camp_in_city"))
        return place
    if place.kind is SleepLocation.REFUSED:
        raise SleepRefused("city_sleep_refused", message("city_sleep_refused"))
    if place.kind is SleepLocation.LODGING_LOBBY:
        raise SleepRefused(
            "lodging_requires_booking", message("lobby_requires_booking")
        )
    if place.kind is SleepLocation.GUEST_ROOM:
        from world.rules.lodging import LodgingError, require_booked_sleep

        try:
            require_booked_sleep(entity, place)
        except LodgingError as error:
            raise SleepRefused(error.code, error.message) from error
        return place
    if place.kind is SleepLocation.STREET:
        from world.rules.clock import read_world_clock

        clock = read_world_clock()
        tick = 0 if clock is None else int(clock.tick)
        owner = _party_owner(entity)
        assert place.street is not None
        if street_refused(owner, place.street, day_index(tick)):
            raise SleepRefused("street_nap_refused", message("street_refusal"))
    return place


def street_nap_binding(receipt: SleepReceipt, place: SleepPlace, tick: int) -> dict[str, Any]:
    """The durable binding an accepted street nap writes (never a schedule hint)."""
    assert place.street is not None
    patrol = next_patrol_tick(tick)
    return {
        "sleep_id": receipt.sleep_id,
        "street": place.street,
        "patrol_tick": patrol,
        "day": day_index(patrol),
    }


# -- street-nap interruption -------------------------------------------------


def _interrupt_state(
    entity: Any, receipt: SleepReceipt, tick: int, *, street: str
) -> None:
    """Write one street nap's terminal AWAKE/interrupted state at ``tick``.

    The caller has already credited the elapsed prefix (or the clock settled
    it as part of the accepted advance). This owner writes no physiology here;
    it revokes the entitlement, records the remaining-day refusal for the party
    owner and emits the committed boundary.
    """
    state = read_optional_fatigue_state(entity)
    if state is not None and state.posture is SleepPosture.VOLUNTARY:
        write_fatigue_state(entity, state.reserve_units, SleepPosture.AWAKE)
        project_fatigue_status(entity)
    write_sleep_receipt(
        entity,
        receipt.with_progress(
            settled_through_tick=max(int(tick), receipt.settled_through_tick),
            state=STATE_INTERRUPTED,
            partial=True,
        ),
    )
    owner = _party_owner(entity)
    record_street_refusal(owner, street, day_index(tick))
    clear_paid_sleep(entity)
    clear_street_nap(entity, sleep_id=receipt.sleep_id)
    unmark_street_napper(entity)
    from world.rules.time_skip import _revoke_sleep_continuations

    _revoke_sleep_continuations(entity)
    context = {
        "char": str(getattr(entity, "pk", "?")),
        "street": street,
        "sleep": receipt.sleep_id,
        "tick": int(tick),
    }
    transaction.on_commit(
        lambda context=context: log_info("street_nap_interrupted", context=context)
    )
    transaction.on_commit(
        lambda entity=entity: entity.msg(message("street_interrupted"))
    )


def interrupt_active_street_nap(
    entity: Any, receipt: SleepReceipt, tick: int
) -> bool:
    """Interrupt ``receipt`` when its street patrol has been reached.

    Used by the clock's receipt reconciliation for a napper already inside the
    advancing scope. Returns ``True`` only when this call actually ended an
    active street nap, so a receipt whose natural deadline came first keeps the
    ordinary completion path.
    """
    if not receipt.sleeping or receipt.kind != KIND_VOLUNTARY:
        return False
    try:
        nap = read_street_nap(entity)
    except ValueError:  # observability: ignore R2: a malformed nap binding cannot authorize an interruption; the receipt keeps its ordinary path
        return False
    if nap is None or nap["sleep_id"] != receipt.sleep_id:
        return False
    if int(tick) < nap["patrol_tick"]:
        return False
    if recovery_target_tick(entity, receipt, int(tick)) < nap["patrol_tick"]:
        # The authored deadline came before the patrol; complete normally.
        return False
    _interrupt_state(
        entity, receipt, int(nap["patrol_tick"]), street=nap["street"]
    )
    return True


# -- clock event source ------------------------------------------------------


def mark_street_napper(entity: Any) -> None:
    """Tag one body so the clock patrol source can discover its nap."""
    tags = getattr(entity, "tags", None)
    if tags is not None:
        tags.add(STREET_NAP_TAG, category=STREET_NAP_TAG_CATEGORY)


def unmark_street_napper(entity: Any) -> None:
    tags = getattr(entity, "tags", None)
    if tags is not None:
        tags.remove(STREET_NAP_TAG, category=STREET_NAP_TAG_CATEGORY)


def _tagged_nappers() -> tuple[Any, ...]:
    from evennia.objects.models import ObjectDB

    try:
        return tuple(
            ObjectDB.objects.filter(
                db_tags__db_key=STREET_NAP_TAG,
                db_tags__db_category=STREET_NAP_TAG_CATEGORY,
            ).distinct()
        )
    except Exception:  # observability: ignore R2: the settlement query must never fail an unrelated advance; a failed discovery settles nothing
        return ()


def _settle_out_of_scope_nap(body: Any, start_tick: int, end_tick: int) -> ScheduledEvent | None:
    """Settle one napper whose body is outside the advancing scope."""
    try:
        receipt = read_sleep_receipt(body)
        nap = read_street_nap(body)
    except (SleepReceiptError, ValueError):  # observability: ignore R2: an unusable nap record is cleared below rather than guessed at
        unmark_street_napper(body)
        return None
    if receipt is None or nap is None or not receipt.sleeping:
        unmark_street_napper(body)
        return None
    if nap["sleep_id"] != receipt.sleep_id or receipt.kind != KIND_VOLUNTARY:
        unmark_street_napper(body)
        clear_street_nap(body)
        return None
    patrol = int(nap["patrol_tick"])
    natural = recovery_target_tick(
        body, receipt, int(start_tick), cap_street=False
    )
    target = min(patrol, natural)
    if target > int(end_tick):
        # This advance does not reach the nap's own next boundary; the nap's
        # cursor and recovery stay for the interval that actually commits.
        return None
    state = read_optional_fatigue_state(body)
    if state is None or state.posture is not SleepPosture.VOLUNTARY:
        unmark_street_napper(body)
        clear_street_nap(body)
        return None
    from_tick = max(int(receipt.settled_through_tick), int(receipt.entry_tick))
    if target > from_tick:
        settle_gauge_regeneration((body,), target - from_tick)
        settle_fatigue_intervals(
            (
                FatigueInterval(
                    body,
                    FatigueActivity.SLEEP,
                    target - from_tick,
                    state,
                    IntervalCompletion.INTERRUPTIBLE,
                ),
            ),
            context={"stage": "street_patrol"},
            start_tick=from_tick,
        )
    receipt = read_sleep_receipt(body)
    if receipt is None:
        return None
    if natural < patrol:
        # The accepted deadline came first; complete the ordinary wake.
        from world.rules.clock import _reconcile_sleep_receipt

        _reconcile_sleep_receipt(body, target)
        clear_street_nap(body, sleep_id=receipt.sleep_id)
        unmark_street_napper(body)
        return None
    _interrupt_state(body, receipt, target, street=nap["street"])
    return ScheduledEvent(
        _PATROL_EVENT,
        target,
        {
            "char": int(getattr(body, "pk", 0) or 0),
            "street": nap["street"],
            "sleep": receipt.sleep_id,
        },
    )


def settle_city_patrols(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    """Settle every active street nap the advancing scope does not own.

    Bodies inside the current advance scope are settled by the ordinary clock
    passes (their accepted interval was truncated at the patrol boundary); this
    source credits and interrupts only a napper another body's clock advance
    would otherwise carry past the patrol.
    """
    scope = set(current_advance_scope())
    events: list[ScheduledEvent] = []
    for body in _tagged_nappers():
        if int(getattr(body, "pk", 0) or 0) in scope:
            continue
        event = _settle_out_of_scope_nap(body, start_tick, end_tick)
        if event is not None:
            events.append(event)
    return events


def city_patrol_surfaces(
    start_tick: int, end_tick: int
) -> Mapping[int, SurfaceSnapshot]:
    """Snapshot every durable surface the patrol settlement may write."""
    surfaces: dict[int, SurfaceSnapshot] = {}
    for body in _tagged_nappers():
        attributes: dict[tuple[str, str | None], tuple[bool, Any]] = {}
        for key, category in (
            tuple(FATIGUE_ATTRIBUTE_SURFACES)
            + tuple(SLEEP_RECEIPT_SURFACES)
            + tuple(REST_BONUS_SURFACES)
            + (("traits", "traits"),)
        ):
            attributes[(key, category)] = attribute_snapshot(body, key, category)
        surfaces[id(body)] = SurfaceSnapshot(attributes=attributes)
        owner = _party_owner(body)
        if owner is not body and id(owner) not in surfaces:
            refusal_key = "city_street_refusals"
            surfaces[id(owner)] = SurfaceSnapshot(
                attributes={
                    (refusal_key, None): attribute_snapshot(owner, refusal_key),
                    ("sleep_view_decision", None): attribute_snapshot(
                        owner, "sleep_view_decision"
                    ),
                    ("sleep_camp_operation", None): attribute_snapshot(
                        owner, "sleep_camp_operation"
                    ),
                }
            )
    return surfaces


def register_city_sleep_source() -> None:
    """Register the ``city_sleep_patrol`` clock source idempotently."""
    register_event_source(
        "city_sleep_patrol",
        settle_city_patrols,
        city_patrol_surfaces,
        interactive=False,
    )


register_city_sleep_source()


__all__ = [
    "CITY_ANCHOR_KINDS",
    "CitySleepError",
    "CitySleepPolicy",
    "STREET_NAP_TAG",
    "STREET_NAP_TAG_CATEGORY",
    "SleepLocation",
    "SleepPlace",
    "city_patrol_surfaces",
    "classify_room",
    "day_index",
    "get_policy",
    "interrupt_active_street_nap",
    "mark_street_napper",
    "message",
    "next_patrol_tick",
    "register_city_sleep_source",
    "require_voluntary_sleep",
    "settle_city_patrols",
    "sleep_location_warning",
    "street_nap_binding",
    "unmark_street_napper",
]
