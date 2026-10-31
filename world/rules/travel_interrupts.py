"""Stateless wilderness travel interrupt flags (wilderness-travel-interrupts).

One committed ``explore.move`` step compares two immutable fact records — the
position it left and the position it reached — and reports the ordered flags
the browser stops a walk on. Nothing here stores walking state, writes game
state, or ticks the clock: :func:`read_movement_facts` is a pure read
projection over the canonical owners (map knowledge, sight, the read-only
population view, the fatigue policy), and :func:`movement_flags` is a pure
comparison.

The flags are exactly the approved design's §7.3 table, in its stable order:

``landmark_reached``, ``district_lit``, ``landmark_sighted``,
``hostile_in_sight``, ``pace_threshold``, ``nightfall``, ``member_asleep``.

``pace_threshold`` mirrors ``world.rules.travel_plan``'s first-legal-step
stop: a member at or beyond the pace's stage after the step raises it, so a
traveller already at the threshold before the step still raises it. ``forced``
has no threshold, and ``nightfall`` uses the planner's absolute hour-boundary
scan, so a flight-waived zero-charge step can never cross a time boundary.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Mapping

from world.maps.wilderness_provider import WILDERNESS_NAME, is_valid_wilderness_cell
from world.rules import sight
from world.rules.clock import read_world_clock
from world.rules.fatigue import (
    FatigueStage,
    SleepPosture,
    fatigue_stage,
    read_optional_fatigue_state,
)
from world.rules.travel_plan import (
    PACE_STOP_STAGES,
    _STAGE_RANK,
    _night_entry_offset,
)

#: The approved stable output order (design §7.3).
FLAG_ORDER: tuple[str, ...] = (
    "landmark_reached",
    "district_lit",
    "landmark_sighted",
    "hostile_in_sight",
    "pace_threshold",
    "nightfall",
    "member_asleep",
)

_AWAKE = SleepPosture.AWAKE


@dataclass(frozen=True, slots=True)
class TravellerFact:
    """One traveller's committed fatigue/posture at a captured position.

    ``stage`` and ``asleep`` are ``None`` when the body carries no fatigue
    state at all (a non-physiological fixture), which the canonical movement
    preflight also treats as absent rather than as an awake body.
    """

    member_id: int | None
    stage: FatigueStage | None
    asleep: bool | None


@dataclass(frozen=True, slots=True)
class MovementFacts:
    """The immutable facts of one position, captured around a committed step.

    ``cell`` is the wilderness coordinate (``None`` on a non-wilderness
    position such as a grid room before a gate entry). The spawn keys are
    stable observation identities, never labels or object identities:
    ``landmarks`` are district keys whose exact canonical node is this cell,
    ``distant_sources`` are the sight sources' internal source keys,
    ``hostiles`` are the population view's live hostile observation keys, and
    ``travellers`` are the source-present party's physiology.
    """

    cell: tuple[int, int] | None
    tick: int
    landmarks: frozenset[str]
    lit_districts: frozenset[str]
    distant_sources: frozenset[str]
    hostiles: frozenset[str]
    travellers: tuple[TravellerFact, ...]


# -- read-only fact capture -------------------------------------------------
def wilderness_cell(location: Any) -> tuple[int, int] | None:
    """The roster wilderness coordinate of one location, or ``None``.

    Only a wilderness terrain room carries a wilderness cell: a grid room's
    contrib coordinates describe its own grid, never the wilderness frame, so
    they never leak into a wilderness comparison.
    """
    from typeclasses.rooms import TerrainRoom

    if not isinstance(location, TerrainRoom):
        return None
    from world.rules.travel_cost import _wilderness_coordinates

    return _wilderness_coordinates(location)


def landmark_keys_at(cell: tuple[int, int]) -> frozenset[str]:
    """The district keys whose exact canonical landmark node is ``cell``."""
    from world.lore.map_districts import current as districts_current
    from world.lore.map_districts import landmark_node_ids
    from world.rules.map_knowledge import encode_wild

    node = encode_wild(WILDERNESS_NAME, cell[0], cell[1])
    return frozenset(
        key
        for key, landmark_node in landmark_node_ids(
            districts_current().districts
        ).items()
        if landmark_node == node
    )


def _source_present_members(
    actor: Any,
    location: Any,
    cell: tuple[int, int] | None,
) -> tuple[Any, ...]:
    """The canonical traversing cohort of the source position.

    The exit's own preflight record wins (it is the same tuple the charge and
    the follow step settle); a direct settlement call outside an exit lineage
    falls back to the shared source-present scope.
    """
    from world.rules.travel_cost import (
        active_traversal_members,
        source_present_members,
    )

    recorded = active_traversal_members(actor, location)
    if recorded is not None:
        return recorded
    return source_present_members(actor, location, cell)


def _traveller_facts(members: Iterable[Any]) -> tuple[TravellerFact, ...]:
    facts: list[TravellerFact] = []
    for member in members:
        member_id = getattr(member, "pk", None)
        state = read_optional_fatigue_state(member)
        if state is None:
            facts.append(TravellerFact(member_id=member_id, stage=None, asleep=None))
            continue
        facts.append(
            TravellerFact(
                member_id=member_id,
                stage=fatigue_stage(state),
                asleep=state.posture is not _AWAKE,
            )
        )
    return tuple(facts)


def _hostile_keys(location: Any, cell: tuple[int, int], calendar: Any) -> frozenset[str]:
    """The population view's live hostile observation keys in the ground disc.

    The disc is the canonical live-sight geometry (``in_ground_disc`` over the
    committed radius); the knowledge-revealed filter of the presentation
    window is deliberately not applied, because an interrupt describes live
    sight, not what the map has drawn. The view only reads: it never
    materializes a prospective slot.
    """
    from world.maps.wilderness_population import population_view

    wilderness = getattr(location, "wilderness", None)
    if wilderness is None:
        return frozenset()
    radius = sight.ground_radius_at(cell, calendar)
    disc = [
        (cell[0] + dx, cell[1] + dy)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if sight.in_ground_disc(cell, (cell[0] + dx, cell[1] + dy), radius)
        and is_valid_wilderness_cell((cell[0] + dx, cell[1] + dy))
    ]
    return frozenset(
        fact.observation_key
        for fact in population_view(wilderness, disc)
        if fact.hostile and fact.kind == "monster"
    )


def read_movement_facts(
    actor: Any,
    location: Any,
    *,
    cell: tuple[int, int] | None = None,
    knowledge_owner: Any = None,
    members: Sequence[Any] | None = None,
) -> MovementFacts:
    """Capture one position's immutable interrupt facts.

    ``knowledge_owner`` is the authorized ``PlayerCharacter`` knowledge owner
    (the commander behind a possessed body); ``members`` freezes the traversing
    cohort so the after capture can never reselect a different party. A
    corrupt knowledge record raises (:class:`world.rules.map_knowledge.
    KnowledgeError`) instead of degrading: the collector logs the failed
    comparison and returns no flags, so an unreadable lighting record can never
    fabricate a newly lit district.
    """
    from world.rules.map_district_lighting import lit_district_keys

    owner = knowledge_owner if knowledge_owner is not None else actor
    if cell is None:
        cell = wilderness_cell(location)
    clock = read_world_clock()
    tick = 0 if clock is None else int(clock.tick)
    if members is None:
        members = _source_present_members(actor, location, cell)

    if cell is None:
        landmarks: frozenset[str] = frozenset()
        distant_sources: frozenset[str] = frozenset()
        hostiles: frozenset[str] = frozenset()
    else:
        calendar = None if clock is None else clock.calendar
        landmarks = landmark_keys_at(cell)
        if calendar is None:
            distant_sources = frozenset()
            hostiles = frozenset()
        else:
            from world.maps.wilderness_provider import WILDERNESS_KM_PER_CELL

            distant_sources = sight.visible_distant_source_keys(
                cell,
                calendar,
                sight.published_distant_sources(),
                inputs=sight.published_ground_inputs(cell),
                cell_size_km=WILDERNESS_KM_PER_CELL,
            )
            hostiles = _hostile_keys(location, cell, calendar)

    return MovementFacts(
        cell=cell,
        tick=tick,
        landmarks=landmarks,
        lit_districts=lit_district_keys(owner),
        distant_sources=distant_sources,
        hostiles=hostiles,
        travellers=_traveller_facts(members),
    )


# -- pure comparison --------------------------------------------------------
def _walk_pace(walk: Mapping[str, Any] | None) -> str | None:
    if not isinstance(walk, Mapping):
        return None
    pace = walk.get("pace")
    return pace if isinstance(pace, str) else None


def _stop_at_night(walk: Mapping[str, Any] | None) -> bool:
    return isinstance(walk, Mapping) and walk.get("stop_at_night") is True


def pace_threshold_reached(
    before: MovementFacts, after: MovementFacts, pace: str | None
) -> bool:
    """Whether a traveller is at or beyond ``pace``'s stop stage after the step.

    The comparison is the planner's own: the committed after-step stage at or
    beyond the pace's threshold. Foot travel never lowers a stage, so a
    traveller already at the threshold before this legal step still raises it,
    exactly as the paired ``travel.plan`` first-step stop does. ``forced`` has
    no threshold and never raises.
    """
    threshold = PACE_STOP_STAGES.get(pace) if pace is not None else None
    if threshold is None:
        return False
    rank = _STAGE_RANK[threshold]
    return any(
        fact.stage is not None and _STAGE_RANK[fact.stage] >= rank
        for fact in after.travellers
    )


def nightfall_crossed(before: MovementFacts, after: MovementFacts) -> bool:
    """Whether the positive charged interval crossed a non-night -> night entry."""
    charged = after.tick - before.tick
    if charged <= 0:
        return False
    return _night_entry_offset(before.tick, charged) is not None


def member_fell_asleep(before: MovementFacts, after: MovementFacts) -> bool:
    """Whether one explicitly awake traveller became voluntarily/forced asleep.

    Only a member observed awake before and asleep after counts: an absent or
    unreadable before fact is never read as "awake".
    """
    awake_before = {
        fact.member_id
        for fact in before.travellers
        if fact.member_id is not None and fact.asleep is False
    }
    return any(
        fact.member_id in awake_before and fact.asleep is True
        for fact in after.travellers
    )


def movement_flags(
    before: MovementFacts,
    after: MovementFacts,
    *,
    walk: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    """The ordered, duplicate-free interrupt flags of one committed step."""
    raised = {
        "landmark_reached": bool(after.landmarks),
        "district_lit": bool(after.lit_districts - before.lit_districts),
        "landmark_sighted": bool(after.distant_sources - before.distant_sources),
        "hostile_in_sight": bool(after.hostiles - before.hostiles),
        "pace_threshold": pace_threshold_reached(before, after, _walk_pace(walk)),
        "nightfall": _stop_at_night(walk) and nightfall_crossed(before, after),
        "member_asleep": member_fell_asleep(before, after),
    }
    return tuple(flag for flag in FLAG_ORDER if raised[flag])


__all__ = [
    "FLAG_ORDER",
    "MovementFacts",
    "TravellerFact",
    "landmark_keys_at",
    "member_fell_asleep",
    "movement_flags",
    "nightfall_crossed",
    "pace_threshold_reached",
    "read_movement_facts",
    "wilderness_cell",
]
