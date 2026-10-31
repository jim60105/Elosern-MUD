"""Commit-qualified structured travel notices (wilderness-travel-log-ui).

The deterministic owners of a committed wilderness step, an explicit time skip
and a successful room look are the only places a travel notice may be produced.
This module is their narrow, read-only helper:

- :func:`capture_travel_facts` copies the primitive facts of one position
  (region, woodland, ford, landmarks, lit districts, the live-sight hostile
  observations, the visible distant sources and the travelling party's
  fatigue rows) into an immutable :class:`TravelCapture`. Sightings are read
  from the same canonical sight and population functions the area map and
  the interrupts consume (wilderness-travel-window-ui); their internal
  observation and source identities stay inside the capture.
  Every read failure is reported and yields ``None``, so a broken read can
  never fail the operation it observes.
- :func:`build_travel_events` is a pure comparison of two captures. It returns
  immutable :class:`TravelEvent` drafts whose zh-TW text the server template
  renders; the browser never infers importance from prose. A sighting notice
  fires for an observation identity present after and absent before (no
  permanent sighting memory), and dusk/nightfall for every light-phase entry
  inside the committed charged interval.
- :func:`record_travel_fact` allocates the stable identities once, at the
  source, and registers the delivery with ``on_publication_commit`` inside the
  owning transaction, under the operation's causal publication group. A
  rolled-back operation therefore delivers nothing, and every watcher
  coordinator receives the same immutable, already-identified fact.

Event ids are ``<group_id>:<fact token>.<index>``: the fact token is drawn once
per recorded fact and the index is the event's position inside it, so a
replayed or fanned-out fact keeps exactly its ids. Nothing is persisted, no
clock is advanced and no knowledge is written here.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

from django.db import transaction

from world.observability import log_warn
from world.rules.presentation_events import (
    current_publication_group,
    new_publication_group,
    on_publication_commit,
    publication_group,
)

__all__ = [
    "MAX_FACT_BYTES",
    "MAX_FACT_EVENTS",
    "MAX_PROSE_CODE_POINTS",
    "TRAVEL_EVENT_KINDS",
    "TravelCapture",
    "TravelEvent",
    "TravelLogFact",
    "TravellerRow",
    "build_travel_events",
    "capture_travel_facts",
    "clear_travel_observers",
    "emit_travel_fact",
    "look_summary",
    "record_room_look",
    "record_travel_fact",
    "register_travel_observer",
]

#: The closed travel notice vocabulary (design: Commit-qualified event transport).
TRAVEL_EVENT_KINDS = (
    "region_entered",
    "woodland_entered",
    "ford_crossed",
    "hostile_sighted",
    "landmark_sighted",
    "landmark_reached",
    "fatigue_stage",
    "dusk",
    "nightfall",
    "camp_result",
    "look",
)

#: One fact carries at most as many events as one wire batch.
MAX_FACT_EVENTS = 64
#: One fact's canonical UTF-8 bytes stay inside the batch ceiling.
MAX_FACT_BYTES = 65_536
#: Prose rides the global JSON string bound of the presentation protocol; the
#: complete appearance always stays in the ordinary full-log narration.
MAX_PROSE_CODE_POINTS = 2_048
#: The one-line look summary's prose budget (before the prefix).
_SUMMARY_CODE_POINTS = 96
_NAME_CODE_POINTS = 256

_FACT_TOKEN_BYTES = 4


@dataclass(frozen=True)
class TravelEvent:
    """One immutable, already-identified travel notice."""

    id: str
    kind: str
    params: Mapping[str, Any]
    text: str
    tick: int
    day: int
    time: str

    def as_wire(self) -> dict[str, Any]:
        """The exact wire entry ``{id, kind, tick, day, time, text, params}``."""
        return {
            "id": self.id,
            "kind": self.kind,
            "tick": self.tick,
            "day": self.day,
            "time": self.time,
            "text": self.text,
            "params": _plain(self.params),
        }


@dataclass(frozen=True)
class TravelLogFact:
    """One committed source fact: an ordered, immutable batch of notices."""

    actor_id: int
    group_id: str
    fact_id: str
    events: tuple[TravelEvent, ...]


@dataclass(frozen=True)
class TravellerRow:
    """One travelling member's committed fatigue stage at a captured position."""

    identity: str
    name: str
    stage: str
    label: str


@dataclass(frozen=True)
class TravelCapture:
    """The primitive facts of one position, copied before any later write.

    ``cell`` is ``None`` off the wilderness. ``landmarks`` pairs each district
    key whose exact landmark node is this cell with its display name;
    ``hostiles`` holds ``(observation key, label, threat)`` for each hostile in
    live sight on revealed ground; ``distant`` holds ``(source key, bearing,
    distance_km, name)`` for each visible distant source (``name`` only for a
    lit district); ``travellers`` are the source-present party's fatigue rows.
    The keys are comparison identities only and never leave the capture.
    """

    cell: tuple[int, int] | None
    tick: int
    region_key: str | None = None
    region_name: str | None = None
    woodland: bool = False
    ford: bool = False
    landmarks: tuple[tuple[str, str], ...] = ()
    lit_districts: frozenset[str] = frozenset()
    hostiles: tuple[tuple[str, str, str | None], ...] = ()
    distant: tuple[tuple[str, str, int, str | None], ...] = ()
    travellers: tuple[TravellerRow, ...] = ()


@dataclass(frozen=True)
class _Draft:
    kind: str
    params: Mapping[str, Any]
    text: str
    tick: int


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return value


def _frozen(params: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(params))


# -- clock rendering ---------------------------------------------------------
def _day_seconds() -> int:
    from world.rules.clock import _DAY_SECONDS

    return int(_DAY_SECONDS)


def day_and_time(tick: int) -> tuple[int, str]:
    """The absolute 1-based day and the ``HH:MM`` clock text of ``tick``."""
    from world.rules.clock import WorldDateTime

    calendar = WorldDateTime.from_tick(int(tick))
    return int(tick) // _day_seconds() + 1, f"{calendar.hour:02d}:{calendar.minute:02d}"


# -- text templates ----------------------------------------------------------
_TEMPLATES: dict[str, Callable[[Mapping[str, Any]], str]] = {
    "region_entered": lambda p: f"進入{p['name']}。",
    "woodland_entered": lambda p: f"走進{p['name']}的林地。",
    "ford_crossed": lambda p: f"涉過{p['name']}的淺灘。",
    "hostile_sighted": lambda p: (
        f"發現{p['name']}" + (f" ×{p['count']}" if p["count"] > 1 else "")
        + (f"（{p['threat']}）" if p["threat"] else "") + "。"
    ),
    "landmark_sighted": lambda p: (
        f"望見{p['bearing']}方約 {p['distance_km']} 公里處的"
        f"{p['name'] if p['name'] else '地標'}。"
    ),
    "landmark_reached": lambda p: (
        f"抵達{p['name']}。" + (f"{p['lit_district']}已探明。" if p["lit_district"] else "")
    ),
    "fatigue_stage": lambda p: f"{p['name']}：{p['label']}。",
    "dusk": lambda p: "暮色降臨。",
    "nightfall": lambda p: "入夜了。",
    "camp_result": lambda p: str(p["summary"]),
    "look": lambda p: look_summary(p["prose"]),
}


def _strip_markup(text: str) -> str:
    try:
        from evennia.utils.ansi import strip_ansi

        return strip_ansi(text)
    except Exception as error:  # observability: R2 reported here; the literal text still renders
        log_warn("travel_events_markup_strip_failed", context={"surface": "travel"}, exc=error)
        return text


def look_summary(prose: str) -> str:
    """The one-line server summary of a look's full appearance."""
    lines = [" ".join(line.split()) for line in _strip_markup(str(prose)).splitlines()]
    lines = [line for line in lines if line]
    # An appearance opens with the place's name line; the scenery that
    # follows it is what the summary quotes.
    first = lines[1] if len(lines) > 1 else (lines[0] if lines else "")
    if len(first) > _SUMMARY_CODE_POINTS:
        first = first[: _SUMMARY_CODE_POINTS - 1] + "…"
    return f"環顧四周：{first}" if first else "環顧四周。"


def _bounded_prose(prose: Any) -> str:
    text = str(prose or "")
    if len(text) > MAX_PROSE_CODE_POINTS:
        text = text[: MAX_PROSE_CODE_POINTS - 1] + "…"
    return text


def _bounded_name(value: Any) -> str:
    return str(value)[:_NAME_CODE_POINTS]


def _draft(kind: str, params: Mapping[str, Any], tick: int) -> _Draft:
    return _Draft(kind=kind, params=_frozen(params), text=_TEMPLATES[kind](params), tick=tick)


# -- pure comparison ---------------------------------------------------------
def build_travel_events(
    before: TravelCapture | None,
    after: TravelCapture,
    cause: str,
    *,
    landmark_prose: str | None = None,
    landmark_artwork: Mapping[str, Any] | None = None,
    arrival_node: str | None = None,
    look_prose: str | None = None,
) -> tuple[_Draft, ...]:
    """Compare two committed captures into ordered notice drafts.

    ``cause`` is ``move`` (a settled step), ``skip`` (a positive explicit
    interval) or ``look`` (a successful room look). A missing ``before`` is an
    unreadable source: only the facts that need no comparison are emitted (a
    look, an actual ford or landmark arrival), never an invented change.
    """
    tick = int(after.tick)
    drafts: list[_Draft] = []
    if cause == "look":
        if look_prose is not None:
            drafts.append(_draft("look", {"prose": _bounded_prose(look_prose)}, tick))
        return tuple(drafts)
    if cause == "move":
        if (
            before is not None
            and after.region_key is not None
            and after.region_key != before.region_key
        ):
            drafts.append(
                _draft("region_entered", {"name": _bounded_name(after.region_name or "")}, tick)
            )
        if before is not None and after.woodland and not before.woodland:
            drafts.append(
                _draft("woodland_entered", {"name": _bounded_name(after.region_name or "")}, tick)
            )
        if after.ford:
            drafts.append(
                _draft("ford_crossed", {"name": _bounded_name(after.region_name or "")}, tick)
            )
        newly_lit = after.lit_districts - (before.lit_districts if before is not None else after.lit_districts)
        for key, name in after.landmarks:
            if arrival_node is None:
                break
            drafts.append(
                _draft(
                    "landmark_reached",
                    {
                        "arrival_node": arrival_node,
                        "name": _bounded_name(name),
                        "lit_district": _bounded_name(name) if key in newly_lit else None,
                        "prose": _bounded_prose(landmark_prose),
                        "artwork": landmark_artwork,
                    },
                    tick,
                )
            )
    if cause not in ("move", "skip") or before is None:
        return tuple(drafts)
    # Light-phase entries happened inside the interval, before the arrival
    # and the sightings it ends with: they lead the batch, so ticks never
    # decrease within it.
    drafts[:0] = _phase_drafts(before.tick, tick)
    seen_hostiles = {key for key, _label, _threat in before.hostiles}
    counts: dict[tuple[str, str | None], int] = {}
    for key, label, threat in after.hostiles:
        if key in seen_hostiles:
            continue
        counts[(label, threat)] = counts.get((label, threat), 0) + 1
    for (label, threat), count in counts.items():
        drafts.append(
            _draft(
                "hostile_sighted",
                {"name": _bounded_name(label), "count": count, "threat": None if threat is None else _bounded_name(threat)},
                tick,
            )
        )
    seen_sources = {key for key, *_rest in before.distant}
    for key, bearing, distance_km, name in after.distant:
        if key in seen_sources:
            continue
        drafts.append(
            _draft(
                "landmark_sighted",
                {
                    "name": None if name is None else _bounded_name(name),
                    "bearing": _bounded_name(bearing),
                    "distance_km": int(distance_km),
                },
                tick,
            )
        )
    stages = {row.identity: row.stage for row in before.travellers}
    for row in after.travellers:
        previous = stages.get(row.identity)
        if previous is None or previous == row.stage:
            continue
        drafts.append(
            _draft(
                "fatigue_stage",
                {
                    "member_id": row.identity[:64],
                    "name": _bounded_name(row.name),
                    "stage": row.stage,
                    "label": _bounded_name(row.label),
                },
                tick,
            )
        )
    return tuple(drafts)


_SECONDS_PER_HOUR = 3600
_PHASE_EVENTS = {"dusk": "dusk", "night": "nightfall"}


def _phase_drafts(start: int, end: int) -> list[_Draft]:
    """Dusk and nightfall drafts for each phase entry inside ``(start, end]``.

    The sight rulebook's phases begin on whole hours, so the comparison is
    made at every absolute hour boundary of the committed charged interval
    (the planner's own scan): same-phase endpoints that span a boundary still
    report it, several entries keep their chronological order, and a
    zero-charge interval reports nothing. Each draft carries its boundary's
    tick. The scan is bounded by the owners' own interval caps (a step's
    charge, ``time_skip.MAX_SKIP_SECONDS`` for a skip), so it stays a few
    dozen hour boundaries and well inside the fact's event bound.
    """
    if end <= start:
        return []
    from world.rules import sight
    from world.rules.clock import WorldDateTime

    drafts: list[_Draft] = []
    current = sight.light_phase(WorldDateTime.from_tick(start))
    boundary = (start // _SECONDS_PER_HOUR + 1) * _SECONDS_PER_HOUR
    while boundary <= end:
        phase = sight.light_phase(WorldDateTime.from_tick(boundary))
        kind = _PHASE_EVENTS.get(phase)
        if kind is not None and phase != current:
            drafts.append(_draft(kind, {}, boundary))
        current = phase
        boundary += _SECONDS_PER_HOUR
    return drafts


# -- read-only capture -------------------------------------------------------
def _wilderness_cell(location: Any) -> tuple[int, int] | None:
    from world.rules.travel_interrupts import wilderness_cell

    return wilderness_cell(location)


def _traveller_rows(members: Iterable[Any]) -> tuple[TravellerRow, ...]:
    from world.rules.fatigue import read_optional_fatigue_state
    from world.rules.status_query.fatigue import build_fatigue_subject

    rows: list[TravellerRow] = []
    seen: set[str] = set()
    for member in members:
        identity = str(getattr(member, "pk", "") or "")
        if not identity or identity in seen:
            continue
        seen.add(identity)
        if read_optional_fatigue_state(member) is None:
            continue
        view = build_fatigue_subject(member)
        rows.append(TravellerRow(view.identity, view.name, view.stage, view.label))
    return tuple(rows)


def _hostiles_in_sight(
    location: Any, cell: tuple[int, int], calendar: Any, owner: Any
) -> tuple[tuple[str, str, str | None], ...]:
    """The live-sight hostile observations on revealed ground around ``cell``.

    The canonical live disc and population view (shared with the
    interrupts), restricted to the knowledge owner's revealed cells exactly as
    the area map publishes its entities, so a notice never names a hostile
    the map does not draw.
    """
    from world.maps.wilderness_population import threat_label
    from world.rules.map_knowledge import revealed_in_bounds
    from world.rules.travel_interrupts import live_hostile_facts, live_sight_disc

    disc = live_sight_disc(cell, calendar)
    if not disc:
        return ()
    xs = [x for x, _y in disc]
    ys = [y for _x, y in disc]
    revealed = set(revealed_in_bounds(owner, (min(xs), min(ys), max(xs), max(ys)))) | {tuple(cell)}
    return tuple(
        (fact.observation_key, fact.label, threat_label(fact.threat_tier, fact.danger_grade))
        for fact in live_hostile_facts(location, [c for c in disc if c in revealed])
    )


def _distant_in_sight(
    cell: tuple[int, int], calendar: Any, lit: frozenset[str]
) -> tuple[tuple[str, str, int, str | None], ...]:
    """The visible distant sources around ``cell`` with their wire facts.

    The single visibility decision behind the area map's markers and the
    interrupts' comparison; the name follows the markers' rule (a lit
    district's landmark name, else anonymous).
    """
    from world.lore.map_districts import current as districts_current
    from world.maps.wilderness_provider import WILDERNESS_KM_PER_CELL
    from world.rules import sight

    names = {key: row.landmark_name_zh for key, row in districts_current().districts.items()}
    out = []
    for source, _silhouette, distance_km in sight.visible_distant_sources(
        cell,
        calendar,
        sight.published_distant_sources(),
        inputs=sight.published_ground_inputs(cell),
        cell_size_km=WILDERNESS_KM_PER_CELL,
    ):
        name = names.get(source.district_key) if source.district_key in lit else None
        out.append(
            (
                source.source_key,
                sight.bearing_label(cell, source.cell),
                sight.rounded_distance_km(distance_km),
                name,
            )
        )
    return tuple(sorted(out))


def _landmarks_at(cell: tuple[int, int]) -> tuple[tuple[str, str], ...]:
    from world.lore.map_districts import current
    from world.rules.travel_interrupts import landmark_keys_at

    districts = current().districts
    return tuple(
        (key, districts[key].district_name_zh)
        for key in sorted(landmark_keys_at(cell))
        if key in districts
    )


def capture_travel_facts(
    actor: Any,
    *,
    location: Any = None,
    knowledge_owner: Any = None,
    members: Iterable[Any] | None = None,
) -> TravelCapture | None:
    """Copy one position's primitive travel facts, or ``None`` when unreadable."""
    from world.rules.clock import read_world_clock

    try:
        # A savepoint keeps a failed read from breaking an owner's enclosing
        # transaction (a sleep interval reads these inside its own atomic).
        with transaction.atomic():
            return _capture(actor, location, knowledge_owner, members, read_world_clock)
    except Exception as error:  # observability: R2 reported here; a travel notice read never fails the observed operation
        log_warn(
            "travel_events_capture_failed",
            context={"char": str(getattr(actor, "pk", "?"))},
            exc=error,
        )
        return None


def on_wilderness(actor: Any) -> bool:
    """Whether ``actor`` stands on a wilderness cell (the only notice scope)."""
    try:
        return _wilderness_cell(getattr(actor, "location", None)) is not None
    except Exception as error:  # observability: R2 reported here; an unreadable position records nothing
        log_warn("travel_events_capture_failed", context={"char": str(getattr(actor, "pk", "?"))}, exc=error)
        return False


def _capture(actor, location, knowledge_owner, members, read_world_clock):
    location = location if location is not None else getattr(actor, "location", None)
    clock = read_world_clock()
    tick = 0 if clock is None else int(clock.tick)
    cell = _wilderness_cell(location)
    if members is None:
        from world.rules.travel_cost import source_present_members

        members = () if location is None else source_present_members(actor, location, cell)
    travellers = _traveller_rows(members)
    if cell is None:
        return TravelCapture(cell=None, tick=tick, travellers=travellers)
    from world.maps import wilderness_provider
    from world.lore.wilderness_regions import regions
    from world.rules.map_district_lighting import lit_district_keys

    region_key = wilderness_provider.region_for_coordinates(*cell)
    region = regions().get(region_key)
    fords = wilderness_provider.terrain_definition().waterway_fords
    owner = knowledge_owner if knowledge_owner is not None else actor
    lit = frozenset(lit_district_keys(owner))
    calendar = None if clock is None else clock.calendar
    return TravelCapture(
        cell=cell,
        tick=tick,
        region_key=region_key,
        region_name=region.display_name_zh if region is not None else region_key,
        woodland=wilderness_provider.sight_terrain_class(cell) == "woodland",
        ford=any(tuple(cell) in {tuple(c) for c in cells} for cells in fords.values()),
        landmarks=_landmarks_at(cell),
        lit_districts=lit,
        hostiles=() if calendar is None else _hostiles_in_sight(location, cell, calendar, owner),
        distant=() if calendar is None else _distant_in_sight(cell, calendar, lit),
        travellers=travellers,
    )


# -- delivery ----------------------------------------------------------------
_observers: list[Callable[[TravelLogFact], None]] = []


def register_travel_observer(callback: Callable[[TravelLogFact], None]) -> None:
    """Register one committed travel-fact observer (idempotent per callback)."""
    if not callable(callback):
        raise TypeError("a travel observer must be callable")
    if callback not in _observers:
        _observers.append(callback)


def clear_travel_observers() -> None:
    """Forget every registered observer (test seam)."""
    _observers.clear()


def emit_travel_fact(fact: TravelLogFact) -> None:
    """Deliver one committed fact to every observer, isolating each failure."""
    if not isinstance(fact, TravelLogFact):
        raise TypeError("emit_travel_fact requires a TravelLogFact")
    for observer in tuple(_observers):
        try:
            observer(fact)
        except Exception as error:  # observability: R2 reported below; the remaining observers still receive the fact
            log_warn(
                "travel_fact_delivery_failed",
                context={"surface": "presentation", "actor": str(fact.actor_id), "fact": fact.fact_id},
                exc=error,
            )


def _event_bytes(event: TravelEvent) -> int:
    import json

    return len(
        json.dumps(event.as_wire(), ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


def record_travel_fact(actor: Any, drafts: Iterable[_Draft]) -> TravelLogFact | None:
    """Identify ``drafts`` once and deliver them when the owner commits.

    The ids are allocated here, before any fan-out, under the operation's
    causal publication group. Drafts beyond the batch's event or byte bound
    are dropped (reported), never truncated into apparent validity.
    """
    drafts = tuple(drafts)
    actor_id = getattr(actor, "pk", None)
    if not drafts or isinstance(actor_id, bool) or not isinstance(actor_id, int):
        return None
    with publication_group():
        group = current_publication_group() or new_publication_group()
        token = secrets.token_hex(_FACT_TOKEN_BYTES)
        events: list[TravelEvent] = []
        total = 0
        dropped = 0
        for index, draft in enumerate(drafts):
            day, time = day_and_time(draft.tick)
            event = TravelEvent(
                id=f"{group.id}:{token}.{index}",
                kind=draft.kind,
                params=draft.params,
                text=draft.text,
                tick=draft.tick,
                day=day,
                time=time,
            )
            size = _event_bytes(event)
            if len(events) >= MAX_FACT_EVENTS or total + size > MAX_FACT_BYTES - 1024:
                dropped += 1
                continue
            total += size
            events.append(event)
        if dropped:
            log_warn(
                "travel_events_overflow",
                context={"char": str(actor_id), "dropped": dropped, "kept": len(events)},
            )
        if not events:
            return None
        fact = TravelLogFact(
            actor_id=actor_id,
            group_id=group.id,
            fact_id=f"{group.id}:{token}",
            events=tuple(events),
        )
        on_publication_commit(lambda: emit_travel_fact(fact))
        return fact


def record_room_look(actor: Any, appearance: Any) -> TravelLogFact | None:
    """Record one successful wilderness room look's notice (no time charge)."""
    try:
        if _wilderness_cell(getattr(actor, "location", None)) is None:
            return None
        from world.rules.clock import read_world_clock

        clock = read_world_clock()
        tick = 0 if clock is None else int(clock.tick)
        after = TravelCapture(cell=None, tick=tick)
        return record_travel_fact(
            actor, build_travel_events(None, after, "look", look_prose=str(appearance))
        )
    except Exception as error:  # observability: R2 reported here; a notice never fails the look
        log_warn("travel_events_record_failed", context={"char": str(getattr(actor, "pk", "?")), "cause": "look"}, exc=error)
        return None


def record_position_change(
    actor: Any,
    before: TravelCapture | None,
    cause: str,
    *,
    knowledge_owner: Any = None,
    members: Iterable[Any] | None = None,
) -> TravelLogFact | None:
    """Capture the committed after-position and record its notices.

    Used by the movement and explicit-skip owners only after their operation
    settled. Nothing is recorded off the wilderness, and every failure is
    reported instead of raised.
    """
    try:
        # A savepoint: a failed read or record rolls back only itself (and the
        # delivery it registered), never the owner's enclosing transaction.
        with transaction.atomic():
            return _record_position_change(actor, before, cause, knowledge_owner, members)
    except Exception as error:  # observability: R2 reported here; a notice never fails a committed operation
        log_warn(
            "travel_events_record_failed",
            context={"char": str(getattr(actor, "pk", "?")), "cause": cause},
            exc=error,
        )
        return None


def _record_position_change(actor, before, cause, knowledge_owner, members):
    location = getattr(actor, "location", None)
    cell = _wilderness_cell(location)
    if cell is None:
        return None
    after = capture_travel_facts(
        actor, location=location, knowledge_owner=knowledge_owner, members=members
    )
    if after is None:
        return None
    prose = artwork = node = None
    if cause == "move" and after.landmarks:
        from world.maps.wilderness_provider import WILDERNESS_NAME
        from world.rules.map_knowledge import encode_wild

        node = encode_wild(WILDERNESS_NAME, cell[0], cell[1])
        # The reached room's ordinary appearance through the read-only
        # look seam: current-cell scenery, no authored landmark prose, no
        # LLM and no look charge.
        prose = actor.at_look(location)
        artwork = _scene_artwork(location)
    return record_travel_fact(
        actor,
        build_travel_events(
            before,
            after,
            cause,
            landmark_prose=prose,
            landmark_artwork=artwork,
            arrival_node=node,
        ),
    )


def _scene_artwork(location: Any) -> Mapping[str, Any] | None:
    """The reached room's existing scene descriptor, or ``None``."""
    try:
        from world.art.presenter import describe_scene
        from world.rules.art_view import scene_target_for

        return describe_scene(scene_target_for(location))
    except Exception as error:  # observability: R2 reported here; a missing card image degrades to none
        log_warn("travel_events_artwork_failed", context={"room": str(getattr(location, "pk", "?"))}, exc=error)
        return None
