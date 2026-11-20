"""Whole-party inn check-in, private guest rooms and paid sleep entitlement.

The innkeeper's whole service is deterministic: one quote over the canonical
present-party roster, one atomic confirmation that charges every present guest,
authorizes the roster, and relocates it into the inn's one persistent guest
room. No sleep starts, no clock advances, and no bed assignment or room number
exists.

The booking lives on the inn's authored lobby room; the guest room id and the
per-body access entitlement are independent durable records. The guest room is
a real persistent ``LodgingGuestRoom`` reached by a tagged exit pair, and entry
is authorized at the relocation boundary (including party followers) while the
way out is never gated.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from uuid import uuid4

from django.db import transaction
from evennia.objects.models import ObjectDB

from world.observability import log_info
from world.rules.rest_bonuses import (
    clear_access,
    clear_paid_sleep,
    read_access,
    read_paid_sleep,
    write_access,
    write_paid_sleep,
)
from world.rules.surfaces import (
    attribute_snapshot,
    flush_orphan_instances,
    restore_attribute_best_effort,
)

#: The booking record on the inn's lobby room.
BOOKING_ATTRIBUTE = "lodging_booking"
#: The inn's one persistent guest-room primary key.
ROOM_ID_ATTRIBUTE = "lodging_guest_room_id"
#: The player's pending quote (no state change until confirmation).
PENDING_QUOTE_ATTRIBUTE = "lodging_quote"
#: Tag category/key owning an inn's guest room and its exit pair.
LODGING_ROOM_TAG_CATEGORY = "lodging_guest_room"
LODGING_EXIT_TAG_CATEGORY = "lodging_topology"
#: The service schedule kind a lodging host obeys.
SERVICE_SCHEDULE_KIND = "service_lodging"

GUEST_ROOM_KEY = "客房"
GUEST_ROOM_DESC = (
    "旅店的客房，門在你身後闔上，把大廳的燈火與人聲留在外頭。"
    "一張床、一只臉盆，還有一道扣得住的門閂。"
)
GUEST_ENTRANCE_KEY = "上樓"
GUEST_ENTRANCE_ALIASES = ("客房", "房間")
GUEST_RETURN_KEY = "下樓"
GUEST_RETURN_ALIASES = ("大廳", "樓下")

_BOOKING_FIELDS = frozenset(
    {"booking_id", "place_key", "room_id", "guest_ids", "paid", "entry_tick"}
)
_QUOTE_FIELDS = frozenset(
    {
        "version",
        "quote_id",
        "npc_id",
        "place_key",
        "room_id",
        "guest_ids",
        "unit_price",
        "total",
        "tick",
    }
)
_MAX_GUESTS = 64
_MAX_NAME = 64


class LodgingError(RuntimeError):
    """One whole-party check-in or booking operation is refused."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


class _WalletReadError(ValueError):
    """The shared wallet reader's fail-closed error for an unusable wallet."""


@dataclass(frozen=True)
class LodgingQuote:
    """One read-only whole-party check-in quote."""

    quote_id: str
    npc_id: int
    place_key: str
    room_id: int | None
    unit_price: int
    total: int
    wallet: int
    guest_ids: tuple[int, ...]
    guest_names: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "quote_id": self.quote_id,
            "npc_id": self.npc_id,
            "place_key": self.place_key,
            "unit_price": self.unit_price,
            "total": self.total,
            "wallet": self.wallet,
            "guests": [
                {"id": identity, "name": name}
                for identity, name in zip(self.guest_ids, self.guest_names)
            ],
        }


@dataclass(frozen=True)
class LodgingCheckIn:
    """The committed check-in: booking, room and the exact charged quote."""

    booking_id: str
    place_key: str
    room_id: int
    quote: LodgingQuote


def _policy() -> Any:
    from world.rules.city_sleep import get_policy

    return get_policy()


def _message(key: str) -> str:
    from world.rules.city_sleep import message

    return message(key)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _room_by_pk(pk: Any) -> Any | None:
    if not _is_int(pk) or pk <= 0:
        return None
    return ObjectDB.objects.filter(pk=int(pk)).first()


def _lobby_place_key(lobby: Any) -> str:
    from world.lore.settlements import PLACE_REGISTRY

    tags = getattr(lobby, "tags", None)
    all_tags = getattr(tags, "all", None)
    present = set(all_tags()) if callable(all_tags) else set()
    matches = sorted(key for key in PLACE_REGISTRY if key in present)
    if len(matches) != 1:
        raise LodgingError(
            "no_lodging_service", _message("no_lodging_service")
        )
    return matches[0]


def _place_room(place_key: str) -> Any | None:
    from typeclasses.rooms import Room

    for obj in ObjectDB.objects.filter(
        db_tags__db_key=place_key,
        db_tags__db_category__isnull=True,
    ).distinct():
        if isinstance(obj, Room):
            return obj
    return None


def _lobby_for_place(place_key: str) -> Any | None:
    return _place_room(place_key)


# -- booking persistence -----------------------------------------------------


def read_booking(lobby: Any) -> dict[str, Any] | None:
    """Return the lobby's validated active booking, or ``None``."""
    attributes = getattr(lobby, "attributes", None)
    if attributes is None or not callable(getattr(attributes, "has", None)):
        return None
    if not attributes.has(BOOKING_ATTRIBUTE):
        return None
    raw = attributes.get(BOOKING_ATTRIBUTE)
    if not isinstance(raw, Mapping) or set(raw) != _BOOKING_FIELDS:
        raise LodgingError("malformed_booking", _message("no_lodging_service"))
    booking_id = raw.get("booking_id")
    place_key = raw.get("place_key")
    room_id = raw.get("room_id")
    guest_ids = raw.get("guest_ids")
    paid = raw.get("paid")
    entry_tick = raw.get("entry_tick")
    if (
        not isinstance(booking_id, str)
        or not booking_id
        or not isinstance(place_key, str)
        or not place_key
        or not _is_int(room_id)
        or room_id <= 0
        or not _is_int(entry_tick)
        or entry_tick < 0
        or not isinstance(guest_ids, Sequence)
        or isinstance(guest_ids, (str, bytes))
        or not guest_ids
        or len(guest_ids) > _MAX_GUESTS
        or any(not _is_int(item) or item <= 0 for item in guest_ids)
        or not isinstance(paid, Mapping)
        or any(
            not isinstance(key, str)
            or not key.isascii()
            or not key.isdigit()
            or not isinstance(value, str)
            for key, value in paid.items()
        )
    ):
        raise LodgingError("malformed_booking", _message("no_lodging_service"))
    return {
        "booking_id": booking_id,
        "place_key": place_key,
        "room_id": int(room_id),
        "guest_ids": [int(item) for item in guest_ids],
        "paid": {str(key): str(value) for key, value in paid.items()},
        "entry_tick": int(entry_tick),
    }


def write_booking(lobby: Any, booking: Mapping[str, Any]) -> dict[str, Any]:
    clean = read_booking(_BookingCarrier(booking))
    attributes = getattr(lobby, "attributes", None)
    if attributes is None:
        raise LodgingError("malformed_booking", _message("no_lodging_service"))
    attributes.add(BOOKING_ATTRIBUTE, dict(clean))
    return clean


class _BookingCarrier:
    """A minimal attribute carrier used to validate a booking before writing."""

    __slots__ = ("attributes",)

    def __init__(self, booking: Mapping[str, Any]) -> None:
        self.attributes = _OneAttribute(booking)


class _OneAttribute:
    __slots__ = ("_value",)

    def __init__(self, value: Mapping[str, Any]) -> None:
        self._value = value

    def has(self, key: str, category: str | None = None) -> bool:
        return key == BOOKING_ATTRIBUTE

    def get(self, key: str, category: str | None = None, default: Any = None) -> Any:
        return self._value if key == BOOKING_ATTRIBUTE else default


def clear_booking(lobby: Any) -> None:
    attributes = getattr(lobby, "attributes", None)
    if attributes is not None and callable(getattr(attributes, "remove", None)):
        attributes.remove(BOOKING_ATTRIBUTE)


def read_guest_room(lobby: Any, place_key: str) -> Any | None:
    """Return the inn's persistent guest room, provisioning nothing."""
    attributes = getattr(lobby, "attributes", None)
    if attributes is not None and callable(getattr(attributes, "has", None)):
        if attributes.has(ROOM_ID_ATTRIBUTE):
            room = _room_by_pk(attributes.get(ROOM_ID_ATTRIBUTE))
            if room is not None:
                return room
    from typeclasses.rooms import LodgingGuestRoom

    for obj in ObjectDB.objects.filter(
        db_tags__db_key=place_key,
        db_tags__db_category=LODGING_ROOM_TAG_CATEGORY,
    ).distinct():
        if isinstance(obj, LodgingGuestRoom):
            return obj
    return None


def ensure_guest_room(lobby: Any, place_key: str) -> Any:
    """Create or reuse the inn's one persistent guest room and its exits."""
    room = read_guest_room(lobby, place_key)
    if room is None:
        from evennia.utils.create import create_object
        from typeclasses.rooms import LodgingGuestRoom

        room = create_object(
            LodgingGuestRoom,
            key=GUEST_ROOM_KEY,
            location=None,
            tags=[(place_key, LODGING_ROOM_TAG_CATEGORY)],
        )
        room.db.desc = GUEST_ROOM_DESC
    room.lodging_place_key = place_key
    room.lodging_lobby_id = int(lobby.pk)
    lobby.attributes.add(ROOM_ID_ATTRIBUTE, int(room.pk))
    _ensure_exit(
        lobby,
        room,
        place_key,
        key=GUEST_ENTRANCE_KEY,
        aliases=GUEST_ENTRANCE_ALIASES,
    )
    _ensure_exit(
        room,
        lobby,
        place_key,
        key=GUEST_RETURN_KEY,
        aliases=GUEST_RETURN_ALIASES,
    )
    return room


def _ensure_exit(
    location: Any,
    destination: Any,
    place_key: str,
    *,
    key: str,
    aliases: Sequence[str],
) -> Any:
    from evennia.utils.create import create_object
    from typeclasses.exits import Exit

    owned = [
        exit_obj
        for exit_obj in getattr(location, "exits", ())
        if exit_obj.tags.has(place_key, category=LODGING_EXIT_TAG_CATEGORY)
        and exit_obj.destination is destination
    ]
    if owned:
        keep = owned[0]
        if keep.key != key:
            keep.key = key
            keep.save()
        return keep
    created = create_object(
        Exit,
        key=key,
        aliases=list(aliases),
        location=location,
        destination=destination,
    )
    created.tags.add(place_key, category=LODGING_EXIT_TAG_CATEGORY)
    return created


# -- quote -------------------------------------------------------------------


def _provider_component(actor: Any, host: Any) -> Any:
    from typeclasses.components import Lodging
    from world.rules.npc_schedules import interaction_reason
    from world.rules.service_gate import service_available

    component = host.components.get(Lodging.get_component_slot())
    if component is None:
        raise LodgingError("no_lodging_service", _message("no_lodging_service"))
    verdict = service_available(actor, host, component)
    if not verdict.allowed:
        raise LodgingError("no_lodging_service", _message("no_lodging_service"))
    blocked = interaction_reason(host, SERVICE_SCHEDULE_KIND)
    if blocked is not None:
        raise LodgingError("schedule_blocked", blocked)
    lobby = getattr(actor, "location", None)
    if lobby is None or getattr(host, "location", None) is not lobby:
        raise LodgingError("no_lodging_service", _message("no_lodging_service"))
    return component


def _commander(actor: Any) -> Any:
    from world.rules.party_scope import PartyScopeError, resolve_commander

    try:
        return resolve_commander(actor)
    except PartyScopeError as error:  # observability: ignore R2: the stable party refusal is the player-facing reason
        raise LodgingError("party_unavailable", str(error)) from error


def _present_guests(commander: Any, lobby: Any) -> list[Any]:
    from world.rules.party_scope import PartyScopeError, present_party_scope

    if getattr(commander, "location", None) is not lobby:
        raise LodgingError("payer_absent", _message("payer_absent"))
    try:
        members = present_party_scope(commander)
    except PartyScopeError as error:  # observability: ignore R2: the stable party refusal is the player-facing reason
        raise LodgingError("party_unavailable", str(error)) from error
    guests: list[Any] = []
    seen: set[int] = set()
    for member in members:
        if getattr(member, "_is_deleted", False):
            continue
        identity = int(getattr(member, "pk", 0) or 0)
        if identity <= 0 or identity in seen:
            continue
        seen.add(identity)
        guests.append(member)
    if not guests or len(guests) > _MAX_GUESTS:
        raise LodgingError("party_unavailable", _message("blocked_guest").format(member="?"))
    return guests


def _wallet(commander: Any) -> int:
    from world.rules.wallet import read_wallet

    try:
        return read_wallet(commander, _WalletReadError)
    except _WalletReadError as error:  # observability: ignore R2: the stable malformed-wallet refusal is the player-facing reason
        raise LodgingError("wallet_malformed", "你的錢袋出了問題，無法結帳。") from error


def _guest_name(member: Any) -> str:
    name = str(getattr(member, "key", "") or "").strip()
    return (name or str(getattr(member, "pk", "?")))[:_MAX_NAME]


def _quote_id(
    npc_id: int, place_key: str, guest_ids: Sequence[int], unit_price: int, total: int
) -> str:
    raw = "|".join(
        [
            str(npc_id),
            place_key,
            ",".join(str(item) for item in guest_ids),
            str(unit_price),
            str(total),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _build_quote(commander: Any, host: Any) -> LodgingQuote:
    _provider_component(commander, host)
    lobby = getattr(commander, "location", None)
    place_key = _lobby_place_key(lobby)
    booking = read_booking(lobby)
    if booking is not None:
        raise LodgingError("booking_overlap", _message("booking_overlap"))
    guests = _present_guests(commander, lobby)
    unit_price = int(_policy().price_per_guest_copper)
    total = unit_price * len(guests)
    wallet = _wallet(commander)
    guest_ids = tuple(int(member.pk) for member in guests)
    room = read_guest_room(lobby, place_key)
    return LodgingQuote(
        quote_id=_quote_id(
            int(host.pk), place_key, guest_ids, unit_price, total
        ),
        npc_id=int(host.pk),
        place_key=place_key,
        room_id=None if room is None else int(room.pk),
        unit_price=unit_price,
        total=total,
        wallet=wallet,
        guest_ids=guest_ids,
        guest_names=tuple(_guest_name(member) for member in guests),
    )


def quote_for(actor: Any, host: Any) -> LodgingQuote:
    """Build and remember one whole-party quote for the acting player.

    The stored quote is the text and web confirmation identity; it carries no
    authority and every confirmation recomputes the roster and price.
    """
    commander = _commander(actor)
    quote = _build_quote(commander, host)
    _write_pending_quote(commander, quote)
    return quote


def quote_message(quote: LodgingQuote, host_name: str) -> str:
    """Render one quote in the shared text/web wording."""
    return _message("quote_line").format(
        host=host_name,
        price=quote.unit_price,
        names="、".join(quote.guest_names),
        count=len(quote.guest_ids),
        total=quote.total,
        wallet=quote.wallet,
    )


# -- pending quote -----------------------------------------------------------


def _read_pending_quote(commander: Any) -> dict[str, Any] | None:
    attributes = getattr(commander, "attributes", None)
    if attributes is None or not callable(getattr(attributes, "has", None)):
        return None
    if not attributes.has(PENDING_QUOTE_ATTRIBUTE):
        return None
    raw = attributes.get(PENDING_QUOTE_ATTRIBUTE)
    if not isinstance(raw, Mapping) or set(raw) != _QUOTE_FIELDS:
        return None
    return dict(raw)


def _write_pending_quote(commander: Any, quote: LodgingQuote) -> None:
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    attributes = getattr(commander, "attributes", None)
    if attributes is None:
        raise LodgingError("no_lodging_service", _message("no_lodging_service"))
    attributes.add(
        PENDING_QUOTE_ATTRIBUTE,
        {
            "version": 1,
            "quote_id": quote.quote_id,
            "npc_id": quote.npc_id,
            "place_key": quote.place_key,
            "room_id": quote.room_id,
            "guest_ids": list(quote.guest_ids),
            "unit_price": quote.unit_price,
            "total": quote.total,
            "tick": 0 if clock is None else int(clock.tick),
        },
    )


def clear_pending_quote(commander: Any) -> None:
    attributes = getattr(commander, "attributes", None)
    if attributes is not None and callable(getattr(attributes, "remove", None)):
        attributes.remove(PENDING_QUOTE_ATTRIBUTE)


# -- confirmation ------------------------------------------------------------


def _lock_rows(pks: Sequence[int]) -> None:
    ids = sorted({int(pk) for pk in pks if _is_int(pk) and int(pk) > 0})
    if ids:
        list(
            ObjectDB.objects.select_for_update()
            .filter(id__in=ids)
            .order_by("id")
            .values_list("id", flat=True)
        )


def _can_enter(member: Any) -> bool:
    from world.rules.fatigue import SleepPosture, read_optional_fatigue_state

    if getattr(member, "_is_deleted", False):
        return False
    try:
        hp = float(getattr(member.traits.hp, "current", member.traits.hp.value))
    except Exception:  # observability: ignore R2: a body with unreadable traits cannot be admitted; this read writes nothing
        return False
    if hp <= 0:
        return False
    state = read_optional_fatigue_state(member)
    return state is None or state.posture is SleepPosture.AWAKE


def _restore_contents(room: Any) -> None:
    cache = getattr(room, "contents_cache", None)
    if cache is not None and callable(getattr(cache, "init", None)):
        try:
            cache.init()
        except Exception:  # observability: ignore R2: best-effort cache refresh on a rollback path
            pass


def confirm_check_in(
    actor: Any, host: Any, *, quote_id: str | None = None
) -> LodgingCheckIn:
    """Confirm the pending whole-party quote atomically.

    Revalidates the exact provider, roster, quote, funds, booking absence and
    every guest's ability to enter under row locks. One transaction provisions
    or reuses the room, writes the booking and entitlements, debits the payer
    and relocates the roster. Any failure restores every in-process cache and
    leaves funds, locations, sleep and the clock unchanged.
    """
    commander = _commander(actor)
    pending = _read_pending_quote(commander)
    if pending is None:
        raise LodgingError("quote_stale", _message("quote_stale"))
    if quote_id is not None and pending["quote_id"] != str(quote_id):
        raise LodgingError("quote_stale", _message("quote_stale"))
    _provider_component(commander, host)
    lobby = getattr(commander, "location", None)
    place_key = _lobby_place_key(lobby)
    if pending["place_key"] != place_key or pending["npc_id"] != int(host.pk):
        raise LodgingError("quote_stale", _message("quote_stale"))
    quote = _build_quote(commander, host)
    if quote.quote_id != pending["quote_id"]:
        raise LodgingError("quote_stale", _message("quote_stale"))
    guests = _present_guests(commander, lobby)
    guest_ids = [int(member.pk) for member in guests]
    if quote.guest_ids != tuple(guest_ids) or quote.total > quote.wallet:
        raise LodgingError(
            "insufficient_funds" if quote.total > quote.wallet else "quote_stale",
            "你的銅幣不足。"
            if quote.total > quote.wallet
            else _message("quote_stale"),
        )
    for member in guests:
        if not _can_enter(member):
            raise LodgingError(
                "blocked_guest",
                _message("blocked_guest").format(member=_guest_name(member)),
            )
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    tick = 0 if clock is None else int(clock.tick)
    booking_id = uuid4().hex
    snapshot = {
        "wallet": attribute_snapshot(commander, "wallet"),
        "booking": attribute_snapshot(lobby, BOOKING_ATTRIBUTE),
        "room_id": attribute_snapshot(lobby, ROOM_ID_ATTRIBUTE),
        "members": {
            id(member): (
                member,
                attribute_snapshot(member, "lodging_guest_access"),
                attribute_snapshot(member, "lodging_paid_sleep"),
                getattr(member, "location", None),
            )
            for member in guests
        },
    }
    room = None
    try:
        with transaction.atomic():
            _lock_rows(
                [int(lobby.pk), int(host.pk), int(commander.pk), *guest_ids]
            )
            # Re-read the roster and funds under the locks: another check-in,
            # a party change or a wallet spend must invalidate the quote
            # instead of being overwritten.
            locked_guests = _present_guests(commander, lobby)
            if [int(member.pk) for member in locked_guests] != guest_ids:
                raise LodgingError("quote_stale", _message("quote_stale"))
            current_booking = read_booking(lobby)
            if current_booking is not None:
                raise LodgingError("booking_overlap", _message("booking_overlap"))
            if _wallet(commander) < quote.total:
                raise LodgingError("insufficient_funds", "你的銅幣不足。")
            room = ensure_guest_room(lobby, place_key)
            commander.db.wallet = _wallet(commander) - quote.total
            booking = {
                "booking_id": booking_id,
                "place_key": place_key,
                "room_id": int(room.pk),
                "guest_ids": guest_ids,
                "paid": {},
                "entry_tick": tick,
            }
            write_booking(lobby, booking)
            for member in guests:
                write_access(
                    member,
                    booking_id=booking_id,
                    place_key=place_key,
                    room_id=int(room.pk),
                )
            for member in guests:
                if not may_enter_guest_room(member, room):
                    raise LodgingError(
                        "blocked_guest",
                        _message("blocked_guest").format(member=_guest_name(member)),
                    )
                if not member.move_to(room, quiet=True, move_hooks=False):
                    raise LodgingError(
                        "move_failed",
                        _message("blocked_guest").format(member=_guest_name(member)),
                    )
            clear_pending_quote(commander)
    except Exception:
        for member, access, paid, original in snapshot["members"].values():
            restore_attribute_best_effort(member, "lodging_guest_access", access)
            restore_attribute_best_effort(member, "lodging_paid_sleep", paid)
            try:
                member.location = original
            except Exception:  # observability: ignore R2: best-effort location restore; the durable rows rolled back with the transaction
                pass
        restore_attribute_best_effort(lobby, BOOKING_ATTRIBUTE, snapshot["booking"])
        restore_attribute_best_effort(lobby, ROOM_ID_ATTRIBUTE, snapshot["room_id"])
        restore_attribute_best_effort(commander, "wallet", snapshot["wallet"])
        if room is not None:
            _restore_contents(room)
        _restore_contents(lobby)
        flush_orphan_instances()
        raise
    context = {
        "char": str(getattr(commander, "pk", "?")),
        "place": place_key,
        "room": int(room.pk),
        "guests": len(guests),
        "total": quote.total,
        "tick": tick,
    }
    transaction.on_commit(
        lambda context=context: log_info("lodging_checked_in", context=context)
    )
    return LodgingCheckIn(
        booking_id=booking_id,
        place_key=place_key,
        room_id=int(room.pk),
        quote=quote,
    )


def check_in_message(result: LodgingCheckIn, host_name: str) -> str:
    """Render the committed check-in in the shared text/web wording."""
    return _message("checkin_confirmed").format(
        host=host_name,
        count=len(result.quote.guest_ids),
        total=result.quote.total,
    )


# -- access and paid entitlement --------------------------------------------


def _booking_for_place(place_key: str) -> tuple[Any | None, dict[str, Any] | None]:
    lobby = _lobby_for_place(place_key)
    if lobby is None:
        return None, None
    try:
        return lobby, read_booking(lobby)
    except LodgingError:  # observability: ignore R2: a malformed booking denies access and never authorizes a stay
        return lobby, None


def may_enter_guest_room(entity: Any, room: Any) -> bool:
    """Whether ``entity`` may be in this guest room right now (read-only)."""
    place_key = getattr(room, "lodging_place_key", None)
    if not isinstance(place_key, str) or not place_key:
        return False
    identity = int(getattr(entity, "pk", 0) or 0)
    if identity <= 0:
        return False
    lobby_id = getattr(room, "lodging_lobby_id", None)
    lobby = _room_by_pk(lobby_id)
    if lobby is None:
        return False
    try:
        booking = read_booking(lobby)
    except LodgingError:  # observability: ignore R2: a malformed booking denies entry
        return False
    return bool(
        booking is not None
        and booking["place_key"] == place_key
        and booking["room_id"] == int(getattr(room, "pk", 0) or 0)
        and identity in booking["guest_ids"]
    )


def require_booked_sleep(entity: Any, place: Any) -> tuple[Any, dict[str, Any]]:
    """Validate one guest's paid sleeping entitlement in a booked room."""
    if place.kind.value != "guest_room" or place.place_key is None:
        raise LodgingError(
            "guest_sleep_requires_booking", _message("guest_sleep_requires_booking")
        )
    try:
        access = read_access(entity)
    except ValueError:  # observability: ignore R2: an unusable access record authorizes no sleep
        access = None
    if access is None or access["place_key"] != place.place_key:
        raise LodgingError(
            "guest_sleep_requires_booking", _message("guest_sleep_requires_booking")
        )
    lobby, booking = _booking_for_place(access["place_key"])
    room = getattr(entity, "location", None)
    if (
        lobby is None
        or booking is None
        or booking["booking_id"] != access["booking_id"]
        or booking["room_id"] != access["room_id"]
        or int(getattr(room, "pk", 0) or 0) != access["room_id"]
        or int(entity.pk) not in booking["guest_ids"]
    ):
        raise LodgingError(
            "guest_sleep_requires_booking", _message("guest_sleep_requires_booking")
        )
    if str(int(entity.pk)) in booking["paid"]:
        raise LodgingError("guest_sleep_spent", _message("guest_sleep_spent"))
    return lobby, booking


def paid_sleep_context(entity: Any) -> tuple[Any, dict[str, Any]] | None:
    """The lobby and active booking that still owe ``entity`` one paid sleep."""
    try:
        return require_booked_sleep(
            entity, _ClassificationProxy(getattr(entity, "location", None))
        )
    except LodgingError:  # observability: ignore R2: an absent paid entitlement is the ordinary no-booking answer, not an I/O failure
        return None


class _ClassificationProxy:
    """The minimal classified-place shape ``require_booked_sleep`` reads."""

    __slots__ = ("kind", "place_key")

    def __init__(self, room: Any) -> None:
        from world.rules.city_sleep import SleepLocation

        place_key = getattr(room, "lodging_place_key", None)
        self.kind = SleepLocation.GUEST_ROOM
        self.place_key = place_key if isinstance(place_key, str) else None


def bind_paid_sleep(
    entity: Any, receipt: Any, *, lobby: Any, booking: Mapping[str, Any]
) -> None:
    """Bind one accepted receipt to the booking's single paid sleep."""
    paid = dict(booking["paid"])
    paid[str(int(entity.pk))] = receipt.sleep_id
    updated = dict(booking)
    updated["paid"] = paid
    write_booking(lobby, updated)
    write_paid_sleep(
        entity,
        sleep_id=receipt.sleep_id,
        booking_id=updated["booking_id"],
        place_key=updated["place_key"],
        room_id=int(updated["room_id"]),
    )


def release_access_on_departure(entity: Any, *, destination: Any = None) -> None:
    """Release one guest's entitlement after it leaves the booked room.

    Sleep completion alone never calls this: waking keeps access. Only a real
    relocation out of the room removes the guest; the booking closes when its
    last guest leaves. A guest that never had access is a no-op.
    """
    try:
        access = read_access(entity)
    except ValueError:  # observability: ignore R2: an unusable access record is cleared below rather than acted on
        access = None
    if access is None:
        return
    location = destination if destination is not None else getattr(entity, "location", None)
    if int(getattr(location, "pk", 0) or 0) == access["room_id"]:
        return
    lobby = _lobby_for_place(access["place_key"])
    if lobby is None:
        clear_access(entity)
        clear_paid_sleep(entity)
        return
    with transaction.atomic():
        _lock_rows([int(lobby.pk), int(entity.pk)])
        booking = read_booking(lobby)
        if (
            booking is None
            or booking["booking_id"] != access["booking_id"]
            or booking["room_id"] != access["room_id"]
            or int(entity.pk) not in booking["guest_ids"]
        ):
            clear_access(entity)
            clear_paid_sleep(entity)
            return
        remaining = [
            identity
            for identity in booking["guest_ids"]
            if identity != int(entity.pk)
        ]
        paid = {
            key: value
            for key, value in booking["paid"].items()
            if key != str(int(entity.pk))
        }
        if remaining:
            updated = dict(booking)
            updated["guest_ids"] = remaining
            updated["paid"] = paid
            write_booking(lobby, updated)
        else:
            clear_booking(lobby)
        clear_access(entity)
        clear_paid_sleep(entity)
    context = {
        "char": str(getattr(entity, "pk", "?")),
        "place": access["place_key"],
        "room": access["room_id"],
    }
    transaction.on_commit(
        lambda context=context: log_info("lodging_departed", context=context)
    )


__all__ = [
    "BOOKING_ATTRIBUTE",
    "GUEST_ROOM_DESC",
    "GUEST_ROOM_KEY",
    "LODGING_EXIT_TAG_CATEGORY",
    "LODGING_ROOM_TAG_CATEGORY",
    "LodgingCheckIn",
    "LodgingError",
    "LodgingQuote",
    "PENDING_QUOTE_ATTRIBUTE",
    "ROOM_ID_ATTRIBUTE",
    "SERVICE_SCHEDULE_KIND",
    "bind_paid_sleep",
    "check_in_message",
    "clear_booking",
    "clear_pending_quote",
    "confirm_check_in",
    "ensure_guest_room",
    "may_enter_guest_room",
    "paid_sleep_context",
    "quote_for",
    "quote_message",
    "read_booking",
    "read_guest_room",
    "release_access_on_departure",
    "require_booked_sleep",
    "write_booking",
]
