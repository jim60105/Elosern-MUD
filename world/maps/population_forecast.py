"""Read-only chronological forecast of the first authored field contact.

The committed lifecycle (``world.maps.population_lifecycle``) is the only
writer of population time. An interruptible skip must nevertheless *stop* at
the first tick at which a relevant contact becomes real, and that tick can be
created by an intermediate birth or by a journey an existing group has not
departed on yet. This module answers exactly that question without writing
anything:

* :func:`capture_activity_snapshot` captures every planning input at the
  interval start through the real owners' pure readers (detached groups,
  journeys, presence, zone and site selection state, protection intervals,
  sited room protection and physiology).
* :func:`project_activity_window` replays the coordinator's documented
  chronological order — completed arrivals, site decisions, zone recoveries,
  contact, then idle departures — over detached records. It calls the same
  pure planners the writer calls (``regional_population.plan_population_wave_from``,
  ``monster_sites.site_occurrence_groups``, ``monster_activity.plan_group_decision``,
  ``quote_edge`` / ``build_journey_plan`` and the shared
  ``field_contact.contact_condition_admits`` rule), so forecast and commit
  cannot drift into two formulas.

Hard purity contract: no constructor, settlement, session, room, draw cursor
or generation sequence is touched, and no database rollback is used as
simulation. A prospective individual token created by a projected birth or
arrival is internal to this call; it is never returned as an identity,
presence or target.

Known bound (recorded in ``docs/development/monster-field-behaviour.md``):
each existing group contributes at most its *next* idle decision, and groups a
projected birth creates contribute none — a second decision needs committed
selection state a read-only pass must not invent. The projection therefore
answers with the next such maintenance boundary as its conservative stop
instead of guessing past it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from world.rules.movement_edges import LocationRef

#: The bounded number of projected boundaries one forecast may settle before
#: it answers conservatively with the next maintenance boundary.
MAX_PROJECTION_STEPS = 2048

#: The closed contact-source vocabulary this forecast reports.
FORECAST_SOURCE_BIRTH = "birth_or_arrival"
FORECAST_SOURCE_CONDITION = "field"


@dataclass(frozen=True, slots=True)
class FieldObserver:
    """One party the running skip settles time for, at its logical position.

    ``traversing_until`` is the committed arrival tick of an in-progress
    physical edge: through that instant the party is in passage and is never
    ordinary field presence.
    """

    commander_id: int
    location: LocationRef
    traversing_until: int | None = None

    def present_at(self, tick: int) -> bool:
        return self.traversing_until is None or int(tick) >= int(self.traversing_until)


@dataclass(frozen=True, slots=True)
class ContactForecast:
    """The first relevant contact inside one projected window, if any."""

    first_tick: int | None
    contact_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ActivityGroupSnapshot:
    """One durable movement group, deep-frozen for read-only projection."""

    group_id: str
    member_ids: tuple[int, ...]
    home_owner: tuple[str, str]
    activity_key: str
    home: LocationRef
    position: LocationRef | None
    journey_id: str | None
    next_decision_tick: int
    sequence: int
    seed: int
    member_time: tuple[tuple[str, Any], ...]

    @classmethod
    def from_group(cls, group: Any) -> "ActivityGroupSnapshot":
        """Freeze one owner record; ``MemberTime`` and ``LocationRef`` are frozen."""
        return cls(
            group_id=group.group_id,
            member_ids=tuple(group.member_ids),
            home_owner=tuple(group.home_owner),
            activity_key=group.activity_key,
            home=group.home,
            position=group.position,
            journey_id=group.journey_id,
            next_decision_tick=int(group.next_decision_tick),
            sequence=int(group.sequence),
            seed=int(group.seed),
            member_time=tuple(sorted(group.member_time.items())),
        )


@dataclass(frozen=True, slots=True)
class JourneySnapshot:
    """One committed passage, deep-frozen for read-only projection."""

    journey_id: str
    group_id: str
    member_ids: tuple[int, ...]
    source: LocationRef
    destination: LocationRef
    depart_tick: int
    arrival_tick: int
    retry_tick: int | None
    seconds: int

    @classmethod
    def from_journey(cls, journey: Any) -> "JourneySnapshot":
        return cls(
            journey_id=journey.journey_id,
            group_id=journey.group_id,
            member_ids=tuple(journey.member_ids),
            source=journey.source,
            destination=journey.destination,
            depart_tick=int(journey.depart_tick),
            arrival_tick=int(journey.arrival_tick),
            retry_tick=None if journey.retry_tick is None else int(journey.retry_tick),
            seconds=int(journey.plan.seconds),
        )

    @property
    def due_tick(self) -> int:
        return self.arrival_tick if self.retry_tick is None else self.retry_tick


@dataclass(frozen=True, slots=True)
class ProjectedZone:
    """One initialized zone's selection state at the interval start."""

    key: str
    seed: int
    generation_sequence: int
    recovery_due_tick: int | None
    settled_through_tick: int


@dataclass(frozen=True, slots=True)
class ProjectedSite:
    """One authored site's complete lifecycle state at the interval start."""

    key: str
    seed: int | None
    generation_sequence: int | None
    member_ids: tuple[int, ...]
    populated: bool
    cleared: bool
    cleared_at_tick: int | None
    recovery_due_tick: int | None
    composition_key: str
    activity_key: str | None


@dataclass(frozen=True, slots=True)
class RoomProtectionSnapshot:
    """One sited room's protected interval, as the activity owner records it."""

    session_id: str
    location: LocationRef
    start_tick: int
    end_tick: int | None


@dataclass(frozen=True, slots=True)
class ActivitySnapshot:
    """Every planning input of one forecast window, captured at its start.

    Values are detached: no live Evennia object is reachable from here, and
    nothing in this record changes across a projection.
    """

    groups: tuple[ActivityGroupSnapshot, ...]
    journeys: tuple[JourneySnapshot, ...]
    presence: tuple[tuple[int | str, Any], ...]
    zones: tuple[ProjectedZone, ...]
    sites: tuple[ProjectedSite, ...]
    protection: tuple[Any, ...]
    room_protection: tuple[RoomProtectionSnapshot, ...]
    physiology: tuple[tuple[int | str, Any], ...]
    condition_ticks: tuple[int, ...]
    wilderness: str | None = None


# ---------------------------------------------------------------------------
# Snapshot capture (pure reads through the real owners)
# ---------------------------------------------------------------------------


def capture_activity_snapshot(*, start_tick: int) -> ActivitySnapshot:
    """Capture the projection inputs at ``start_tick`` through the owners."""
    from world.maps import monster_activity, monster_sites, regional_population

    # The owner's own binding, so the projection plans exactly the sites the
    # committed settlement will settle (a published subset is never assumed).
    from world.maps.monster_sites import MONSTER_SITE_REGISTRY

    wilderness = regional_population.live_wilderness()
    if wilderness is None:
        return ActivitySnapshot((), (), (), (), (), (), (), (), ())
    name = getattr(wilderness, "db_key", None)
    presence: tuple[tuple[int | str, Any], ...] = ()
    protection: tuple[Any, ...] = ()
    if regional_population.population_provisioned(wilderness):
        timeline = regional_population.read_population_timeline(wilderness)
        presence = tuple(
            sorted(
                regional_population.presence_at(
                    wilderness, at_tick=int(start_tick)
                ).items()
            )
        )
        protection = tuple(timeline.protection)
    zones = tuple(
        ProjectedZone(
            key=state.zone_key,
            seed=state.seed,
            generation_sequence=state.generation_sequence,
            recovery_due_tick=state.recovery_due_tick,
            settled_through_tick=state.settled_through_tick,
        )
        for state in regional_population.zone_states(wilderness).values()
    )
    sites: list[ProjectedSite] = []
    for key in sorted(MONSTER_SITE_REGISTRY):
        site = MONSTER_SITE_REGISTRY[key]
        state = monster_sites.site_state(key, wilderness=wilderness)
        if state is None:
            sites.append(
                ProjectedSite(
                    key=key,
                    seed=None,
                    generation_sequence=None,
                    member_ids=(),
                    populated=False,
                    cleared=False,
                    cleared_at_tick=None,
                    recovery_due_tick=None,
                    composition_key=site.composition_key,
                    activity_key=site.activity_key,
                )
            )
            continue
        sites.append(
            ProjectedSite(
                key=key,
                seed=state.seed,
                generation_sequence=state.generation_sequence,
                member_ids=tuple(state.member_ids),
                populated=state.state == monster_sites.SITE_STATE_POPULATED,
                cleared=state.state == monster_sites.SITE_STATE_CLEARED,
                cleared_at_tick=state.cleared_at_tick,
                recovery_due_tick=(
                    None
                    if state.cleared_at_tick is None
                    else int(state.cleared_at_tick) + site.recover_after_ticks
                ),
                composition_key=site.composition_key,
                activity_key=site.activity_key,
            )
        )
    groups: tuple[ActivityGroupSnapshot, ...] = ()
    journeys: tuple[JourneySnapshot, ...] = ()
    room_protection: tuple[RoomProtectionSnapshot, ...] = ()
    if monster_activity.activity_provisioned(wilderness):
        record = monster_activity.read_monster_activity(wilderness)
        groups = tuple(
            ActivityGroupSnapshot.from_group(record.groups[key])
            for key in sorted(record.groups)
        )
        journeys = tuple(
            JourneySnapshot.from_journey(record.journeys[key])
            for key in sorted(record.journeys)
        )
        room_protection = tuple(
            RoomProtectionSnapshot(
                entry.session_id,
                entry.location,
                int(entry.start_tick),
                None if entry.end_tick is None else int(entry.end_tick),
            )
            for entry in record.room_protection
        )
    return ActivitySnapshot(
        groups=groups,
        journeys=journeys,
        presence=presence,
        zones=zones,
        sites=tuple(sites),
        protection=protection,
        room_protection=room_protection,
        physiology=(),
        condition_ticks=(),
        wilderness=name if isinstance(name, str) and name else None,
    )


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _GroupState:
    group_id: str
    activity_key: str
    home: LocationRef
    position: LocationRef | None
    journey_id: str | None
    next_decision_tick: int
    sequence: int
    seed: int
    member_ids: tuple[int | str, ...]
    decision_projected: bool = False


@dataclass(slots=True)
class _ZoneState:
    key: str
    seed: int
    generation_sequence: int
    recovery_due_tick: int | None


@dataclass(slots=True)
class _SiteState:
    key: str
    seed: int | None
    generation_sequence: int | None
    populated: bool
    cleared: bool
    cleared_at_tick: int | None
    recovery_due_tick: int | None
    composition_key: str
    activity_key: str | None


class _Projection:
    """One immutable-input, mutable-working forecast pass."""

    def __init__(
        self,
        snapshot: ActivitySnapshot,
        *,
        start_tick: int,
        wilderness: str,
        observers: tuple[FieldObserver, ...],
    ) -> None:
        self.start_tick = int(start_tick)
        self.wilderness = wilderness
        self.observers = tuple(observers)
        self.presence: dict[int | str, Any] = dict(snapshot.presence)
        self.groups: dict[str, _GroupState] = {
            group.group_id: _GroupState(
                group_id=group.group_id,
                activity_key=group.activity_key,
                home=group.home,
                position=group.position,
                journey_id=group.journey_id,
                next_decision_tick=int(group.next_decision_tick),
                sequence=int(group.sequence),
                seed=int(group.seed),
                member_ids=tuple(group.member_ids),
            )
            for group in snapshot.groups
        }
        self.member_group: dict[int | str, str] = {
            member: group.group_id
            for group in snapshot.groups
            for member in group.member_ids
        }
        self.member_source: dict[int | str, str] = {}
        self.journeys: dict[str, JourneySnapshot] = {
            journey.journey_id: journey for journey in snapshot.journeys
        }
        self.zones: dict[str, _ZoneState] = {
            zone.key: _ZoneState(
                key=zone.key,
                seed=zone.seed,
                generation_sequence=zone.generation_sequence,
                recovery_due_tick=zone.recovery_due_tick,
            )
            for zone in snapshot.zones
        }
        self.sites: dict[str, _SiteState] = {
            site.key: _SiteState(
                key=site.key,
                seed=site.seed,
                generation_sequence=site.generation_sequence,
                populated=site.populated,
                cleared=site.cleared,
                cleared_at_tick=site.cleared_at_tick,
                recovery_due_tick=site.recovery_due_tick,
                composition_key=site.composition_key,
                activity_key=site.activity_key,
            )
            for site in snapshot.sites
        }
        self.protection = tuple(snapshot.protection)
        self.room_protection = tuple(snapshot.room_protection)
        self.tokens = 0

    # -- detached presence -------------------------------------------------
    def _token(self, owner_kind: str, owner_key: str, sequence: int) -> str:
        self.tokens += 1
        return f"forecast:{owner_kind}:{owner_key}:{sequence}:{self.tokens}"

    def _place(
        self,
        *,
        group_id: str,
        activity_key: str,
        home: LocationRef,
        cell: tuple[int, int],
        count: int,
        owner_kind: str,
        owner_key: str,
        sequence: int,
        next_decision_tick: int,
        seed: int,
        home_zone: str | None,
        site_key: str | None,
    ) -> None:
        from world.maps.regional_population import PopulationPosition, PopulationPresence

        members: list[int | str] = []
        for _ in range(count):
            token = self._token(owner_kind, owner_key, sequence)
            self.presence[token] = PopulationPresence(
                True,
                PopulationPosition(self.wilderness, cell[0], cell[1]),
                home_zone,
                site_key,
            )
            self.member_group[token] = group_id
            self.member_source[token] = FORECAST_SOURCE_BIRTH
            members.append(token)
        self.groups[group_id] = _GroupState(
            group_id=group_id,
            activity_key=activity_key,
            home=home,
            position=LocationRef.wilderness(self.wilderness, cell[0], cell[1]),
            journey_id=None,
            next_decision_tick=next_decision_tick,
            sequence=0,
            seed=seed,
            member_ids=tuple(members),
        )

    # -- projected reads ---------------------------------------------------
    def _protected_cells(self, tick: int) -> frozenset[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for protection in self.protection:
            cell = protection.cell
            if cell.wilderness != self.wilderness:
                continue
            if protection.start_tick > tick:
                continue
            if protection.end_tick is not None and protection.end_tick < tick:
                continue
            cells.add((cell.x, cell.y))
        return frozenset(cells)

    def _counts(self, zone_key: str) -> Any:
        from world.maps.regional_population import counts_from_presence

        return counts_from_presence(
            zone_key, self.presence, wilderness=self.wilderness
        )

    # -- projection order --------------------------------------------------
    def _settle_arrivals(self, tick: int) -> None:
        for journey_id in sorted(self.journeys):
            journey = self.journeys.get(journey_id)
            if journey is None or journey.due_tick > tick:
                continue
            del self.journeys[journey_id]
            group = self.groups.get(journey.group_id)
            if group is not None:
                self._arrive(journey, group)

    def _arrive(self, journey: JourneySnapshot, group: _GroupState) -> None:
        from world.maps.monster_activity import activity_decision_interval
        from world.maps.regional_population import PopulationPosition, PopulationPresence

        destination = journey.destination
        group.journey_id = None
        group.position = destination
        group.next_decision_tick = int(journey.due_tick) + activity_decision_interval(
            group.activity_key
        )
        group.sequence += 1
        position = (
            PopulationPosition(self.wilderness, destination.x, destination.y)
            if destination.kind == "wilderness"
            else None
        )
        for member in journey.member_ids:
            previous = self.presence.get(member)
            self.presence[member] = PopulationPresence(
                True,
                position,
                None if previous is None else previous.home_zone,
                None if previous is None else previous.site_key,
            )
            self.member_source[member] = FORECAST_SOURCE_BIRTH

    def _note_zone_boundary(self, tick: int) -> None:
        from world.maps.regional_population import (
            ECOLOGY_ZONE_REGISTRY,
            zone_counts_from_presence,
            zone_lower_bound,
        )

        counts = zone_counts_from_presence(
            sorted(self.zones), self.presence, wilderness=self.wilderness
        )
        for key in sorted(self.zones):
            state = self.zones[key]
            if len(counts[key].local_ids) >= zone_lower_bound(key):
                state.recovery_due_tick = None
            elif state.recovery_due_tick is None:
                state.recovery_due_tick = (
                    tick + ECOLOGY_ZONE_REGISTRY[key].recovery_delay
                )

    def _settle_sites(self, tick: int) -> None:
        from world.lore.monster_activity import movement_units
        from world.lore.monster_placement import composition_row_bindings
        from world.maps.monster_activity import activity_decision_interval
        from world.maps.monster_sites import (
            ENCOUNTER_COMPOSITION_REGISTRY,
            MONSTER_SITE_REGISTRY,
            recovery_condition_matured,
            site_occurrence_groups,
        )

        protected = self._protected_cells(tick)
        for key in sorted(self.sites):
            state = self.sites[key]
            if state.populated or state.seed is None:
                # A populated site is only cleared by a real defeat, which no
                # skip runs; an uninitialized site is created at the interval
                # start, which a later projection never invents.
                continue
            site = MONSTER_SITE_REGISTRY[key]
            if site.one_shot or site.coordinates in protected:
                continue
            if not recovery_condition_matured(state.key, state.cleared_at_tick, tick):
                continue
            groups = site_occurrence_groups(
                site, seed=int(state.seed), sequence=int(state.generation_sequence or 0) + 1
            )
            composition = ENCOUNTER_COMPOSITION_REGISTRY[state.composition_key]
            units = movement_units(
                groups, composition_row_bindings(composition, site=site)
            )
            if not units:
                continue
            sequence = int(state.generation_sequence or 0) + 1
            for ordinal, unit in enumerate(units):
                self._place(
                    group_id=f"site:{key}:{sequence}#{ordinal}",
                    activity_key=unit.activity_key,
                    home=LocationRef.wilderness(self.wilderness, *site.coordinates),
                    cell=site.coordinates,
                    count=len(unit.member_indices),
                    owner_kind="site",
                    owner_key=key,
                    sequence=sequence,
                    next_decision_tick=tick
                    + activity_decision_interval(unit.activity_key),
                    seed=int(state.seed),
                    home_zone=None,
                    site_key=key,
                )
            self.sites[key] = _SiteState(
                key=key,
                seed=state.seed,
                generation_sequence=sequence,
                populated=True,
                cleared=False,
                cleared_at_tick=None,
                recovery_due_tick=None,
                composition_key=state.composition_key,
                activity_key=state.activity_key,
            )

    def _settle_zone_recoveries(self, tick: int) -> None:
        from world.lore.monster_activity import movement_units
        from world.lore.monster_placement import composition_row_bindings
        from world.maps.monster_activity import activity_decision_interval
        from world.maps.regional_population import (
            ECOLOGY_ZONE_REGISTRY,
            ENCOUNTER_COMPOSITION_REGISTRY,
            ZonePopulationState,
            plan_population_wave_from,
            zone_lower_bound,
        )

        protected = self._protected_cells(tick)
        for key in sorted(self.zones):
            state = self.zones[key]
            due = state.recovery_due_tick
            if due is None or due > tick:
                continue
            lower = zone_lower_bound(key)
            counts = self._counts(key)
            if len(counts.local_ids) >= lower:
                state.recovery_due_tick = None
                continue
            plan = plan_population_wave_from(
                key,
                state=ZonePopulationState(
                    key,
                    state.seed,
                    state.generation_sequence,
                    state.recovery_due_tick,
                    tick,
                ),
                counts=counts,
                protected=protected,
                tick=tick,
            )
            zone = ECOLOGY_ZONE_REGISTRY[key]
            if plan.is_blocked:
                state.recovery_due_tick = tick + zone.replenishment_interval
                continue
            placement = plan.placements[0]
            sequence = state.generation_sequence + 1
            composition = ENCOUNTER_COMPOSITION_REGISTRY[placement.composition_key]
            units = movement_units(
                placement.groups,
                composition_row_bindings(composition),
            )
            for ordinal, unit in enumerate(units):
                self._place(
                    group_id=f"zone:{key}:{sequence}#{ordinal}",
                    activity_key=unit.activity_key,
                    home=LocationRef.wilderness(self.wilderness, *placement.cell),
                    cell=placement.cell,
                    count=len(unit.member_indices),
                    owner_kind="zone",
                    owner_key=key,
                    sequence=sequence,
                    next_decision_tick=tick
                    + activity_decision_interval(unit.activity_key),
                    seed=state.seed,
                    home_zone=key,
                    site_key=None,
                )
            state.generation_sequence = sequence
            state.recovery_due_tick = (
                tick + zone.replenishment_interval
                if len(self._counts(key).local_ids) < lower
                else None
            )

    def _settle_decisions(self, tick: int) -> None:
        """Project the next idle decision of every group already present.

        Only groups whose members exist at the window start are planned: the
        planner reads the committed record and the members' real bodies, which
        a projected birth cannot reproduce read-only.
        """
        for group_id in sorted(self.groups):
            group = self.groups[group_id]
            if group.journey_id is not None or group.decision_projected:
                continue
            if not group.member_ids or not isinstance(group.member_ids[0], int):
                continue
            if group.next_decision_tick > tick:
                continue
            group.decision_projected = True
            self._plan_decision(group, tick)

    def _plan_decision(self, group: _GroupState, tick: int) -> None:
        from world.maps import monster_activity
        from world.maps.regional_population import live_wilderness
        from world.rules.movement_edges import quote_edge
        from world.rules.world_escape import build_journey_plan

        wilderness = live_wilderness()
        interval = monster_activity.activity_decision_interval(group.activity_key)
        group.next_decision_tick = tick + interval
        group.sequence = group.sequence + 1
        if wilderness is None:
            return
        try:
            decision = monster_activity.plan_group_decision(
                wilderness, group.group_id, tick=tick
            )
        except Exception:  # observability: ignore R2: the committed planner's refusal is this group's lawful stay for the read-only pass
            return
        if decision.edge is None:
            group.next_decision_tick = tick + monster_activity.stay_decision_interval(
                group.activity_key, decision.reason
            )
            return
        try:
            bodies = monster_activity.living_member_bodies(wilderness, group.group_id)
            # The planner prices the projected physiology; the commitment
            # writes that same idle prefix before it prices the same route.
            states = monster_activity.projected_member_states(
                wilderness, group.group_id, tick=tick
            )
            resolution = quote_edge(bodies[0], decision.edge, bodies, states=states)
            committed = build_journey_plan(bodies, resolution, states)
        except Exception:  # observability: ignore R2: an unpriceable projected departure selects the group's stay; the commitment revalidates it
            return
        seconds = int(committed.get("seconds", 0))
        journey_id = f"forecast:journey:{group.group_id}:{group.sequence}"
        self.journeys[journey_id] = JourneySnapshot(
            journey_id=journey_id,
            group_id=group.group_id,
            member_ids=tuple(int(member) for member in group.member_ids),
            source=decision.edge.source,
            destination=decision.edge.destination,
            depart_tick=tick,
            arrival_tick=tick + seconds,
            retry_tick=None,
            seconds=seconds,
        )
        group.journey_id = journey_id
        group.position = decision.edge.source
        for member in group.member_ids:
            previous = self.presence.get(member)
            if previous is not None:
                # A committed passage is ordinary presence at neither endpoint.
                self.presence[member] = replace(previous, position=None)

    # -- contact -----------------------------------------------------------
    def _contact_at(self, tick: int) -> ContactForecast | None:
        from world.lore.monster_activity import MONSTER_ACTIVITY_REGISTRY
        from world.rules.field_contact import contact_condition_admits

        for observer in self.observers:
            if not observer.present_at(tick):
                continue
            location = observer.location
            if location.kind != "wilderness":
                continue
            cell = (location.x, location.y)
            sources: set[str] = set()
            for member, fact in self.presence.items():
                if not fact.alive or fact.position is None:
                    continue
                if fact.position.wilderness != self.wilderness:
                    continue
                if (fact.position.x, fact.position.y) != cell:
                    continue
                group_id = self.member_group.get(member)
                if group_id is None:
                    continue
                group = self.groups.get(group_id)
                if group is None or group.journey_id is not None:
                    continue
                declaration = MONSTER_ACTIVITY_REGISTRY.get(group.activity_key)
                if declaration is None:
                    continue
                if contact_condition_admits(
                    declaration,
                    tick=int(tick),
                    cell=cell,
                    room_id=(
                        group.position.id
                        if group.position is not None and group.position.kind == "room"
                        else None
                    ),
                    home=group.home,
                ):
                    sources.add(
                        self.member_source.get(member, FORECAST_SOURCE_CONDITION)
                    )
                    return ContactForecast(int(tick), tuple(sorted(sources)))
        return None

    # -- scheduling --------------------------------------------------------
    def _next_boundary(self, tick: int, end_tick: int) -> int | None:
        from world.rules.clock import next_daypart_boundary

        candidates: list[int] = []
        for journey in self.journeys.values():
            if tick < journey.due_tick <= end_tick:
                candidates.append(journey.due_tick)
        for group in self.groups.values():
            if group.journey_id is not None or group.decision_projected:
                continue
            if not group.member_ids or not isinstance(group.member_ids[0], int):
                continue
            if tick < group.next_decision_tick <= end_tick:
                candidates.append(group.next_decision_tick)
        for state in self.zones.values():
            due = state.recovery_due_tick
            if due is not None and tick < due <= end_tick:
                candidates.append(due)
        for state in self.sites.values():
            due = state.recovery_due_tick
            if state.populated or due is None:
                continue
            if tick < due <= end_tick:
                candidates.append(due)
        daypart = next_daypart_boundary(tick, end_tick)
        if daypart is not None:
            candidates.append(daypart)
        return min(candidates) if candidates else None

    def run(self, *, end_tick: int) -> ContactForecast:
        tick = self.start_tick
        for _step in range(MAX_PROJECTION_STEPS):
            if tick > end_tick:
                return ContactForecast(None)
            self._settle_arrivals(tick)
            self._note_zone_boundary(tick)
            self._settle_sites(tick)
            self._note_zone_boundary(tick)
            self._settle_zone_recoveries(tick)
            if tick > self.start_tick:
                contact = self._contact_at(tick)
                if contact is not None:
                    return contact
            self._settle_decisions(tick)
            # A zero-duration committed departure arrives at this same tick.
            self._settle_arrivals(tick)
            self._note_zone_boundary(tick)
            following = self._next_boundary(tick, end_tick)
            if following is None:
                return ContactForecast(None)
            tick = following
        # The bounded pass ran out: answer with the next maintenance boundary
        # so a skip never runs past a contact the projection did not reach.
        return ContactForecast(self._next_boundary(self.start_tick, end_tick))


def project_activity_window(
    snapshot: ActivitySnapshot,
    *,
    start_tick: int,
    end_tick: int,
    observers: tuple[FieldObserver, ...],
    wilderness: str | None = None,
) -> ContactForecast:
    """Return the first relevant authored contact in ``(start_tick, end_tick]``.

    Pure: it consumes no draw, creates no entity/room/session, moves nothing
    and writes no attribute. A window without a provisioned wilderness, without
    observers, or with no projected fact answers ``ContactForecast(None)``.
    """
    if not observers or end_tick <= start_tick:
        return ContactForecast(None)
    # The window's wilderness is a capture input, never inferred from a
    # presence row: a window whose only future fact is a birth has no living
    # individual at its start.
    name = wilderness if wilderness is not None else snapshot.wilderness
    if not name:
        return ContactForecast(None)
    projection = _Projection(
        snapshot,
        start_tick=int(start_tick),
        wilderness=name,
        observers=observers,
    )
    return projection.run(end_tick=int(end_tick))


__all__ = [
    "ActivityGroupSnapshot",
    "ActivitySnapshot",
    "ContactForecast",
    "FieldObserver",
    "JourneySnapshot",
    "MAX_PROJECTION_STEPS",
    "ProjectedSite",
    "ProjectedZone",
    "RoomProtectionSnapshot",
    "capture_activity_snapshot",
    "project_activity_window",
]
