"""Retained developer smoke for the monster field-behaviour chain.

Run only against a disposable configured database (see
``server/conf/monster_field_behaviour_smoke_settings.py``)::

    MUD_SMOKE_DB=/tmp/mud-field-smoke.sqlite3 \
        uv run --locked evennia migrate \
        --settings server.conf.monster_field_behaviour_smoke_settings --noinput
    MUD_SMOKE_DB=/tmp/mud-field-smoke.sqlite3 \
        uv run --locked evennia shell \
        --settings monster_field_behaviour_smoke_settings -i python \
        -c "from tools.monster_field_behaviour_smoke import run; run()"

Evennia 6.1's ``shell`` has no ``--plain`` flag and a freshly migrated
disposable database has no superuser, so the runner first creates one
(``MUD_SMOKE_DB=... DJANGO_SETTINGS_MODULE=server.conf.monster_field_behaviour_smoke_settings
uv run --locked python -c "...create_superuser(...)"``).

The script drives the real owners: the shipped map world, the wilderness
provider script, the synthetic-data kit's species/variant catalogs, the
regional population owner, the map-owned activity/journey record, the
authored field-contact authority and the confirmed retreat boundary. It
reports a real group move, a live hostile arrival that interrupts a wait, a
failed post-attempt energy admission, a paid party retreat, an actual enemy
flee journey, immediate re-engagement at the destination and a committed
reload. Every printed claim is an observed value; a failed boundary raises.
"""

from __future__ import annotations

import json
from contextlib import ExitStack
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.monster_activity import (
    ActivityArea,
    AggressionCondition,
    MonsterActivity,
)
from world.lore.races import RACE_REGISTRY
from world.maps import monster_activity, regional_population
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.rules.combat_session import (
    PARTY_EXIT_RETREAT,
    confirm_party_exit,
    forfeit,
    read_session,
    request_party_exit,
)
from world.rules.combat_session.lifecycle import _persist
from world.rules.combat_session.rounds import reconstruct_battlefield
from world.rules.clock import get_world_clock
from world.rules.fatigue import SleepPosture, write_fatigue_state
from world.rules.field_contact import (
    SOURCE_MOVEMENT,
    admit_field_contact_at,
    register_field_contact_stage,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.movement_edges import (
    LocationRef,
    PhysicalEdge,
    location_ref,
    record_completed_edge,
)
from world.rules.party import join_party
from world.rules.time_skip import advance_wait
from world.rules.world_escape import (
    WorldEscapeContext,
    plan_individual_escape,
    plan_party_retreat,
)
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries

_ANCHOR = (500, 700)
_SEED = 7
_CONTACT = "smoke_contact"
_MOVE = "smoke_move"
_GROUND = "smoke_ground"
_VARIANT = next(iter(SYNTH_MONSTER_VARIANTS))
_SPECIES = SYNTH_MONSTER_VARIANTS[_VARIANT].species_key


def _activity(key: str, *, aggression: AggressionCondition, interval: int = 20):
    return MonsterActivity(key, "solitary_roaming", _GROUND, interval, aggression)


def _same_region_pair() -> tuple[tuple[int, int], tuple[int, int]]:
    here = region_for_coordinates(*_ANCHOR)
    for step in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
        cell = (_ANCHOR[0] + step[0], _ANCHOR[1] + step[1])
        if region_for_coordinates(*cell) == here:
            return _ANCHOR, cell
    raise RuntimeError("smoke: no adjacent cell shares the anchor's region")


def _monster(key: str):
    body = construct_species_individual(_SPECIES, _VARIANT)
    body.key = key
    return body


def _group(
    wilderness,
    *,
    operation_id: str,
    activity_key: str,
    home,
    position,
    members,
    tick: int,
) -> str:
    group_id = monster_activity.group_id_for(operation_id, 0)
    monster_activity.create_group(
        wilderness,
        operation_id=operation_id,
        owner_kind="zone",
        owner_key="smoke",
        activity_key=activity_key,
        home=home,
        position=position,
        member_ids=members,
        seed=_SEED,
        tick=tick,
    )
    return group_id


def _move_group_into_cell(wilderness, body, cell) -> None:
    wilderness.move_obj(body, cell)
    body.db_location = body.location


def run():
    """Execute the retained smoke and print one complete observed report."""
    with ExitStack() as stack:
        publish_shipped_map_world()
        stack.enter_context(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "encounter_compositions",
            )
        )
        probe, neighbour = _same_region_pair()
        region = region_for_coordinates(*probe)
        ground = ActivityArea(
            _GROUND,
            region,
            (
                (
                    min(probe[0], neighbour[0]),
                    max(probe[0], neighbour[0]),
                    min(probe[1], neighbour[1]),
                    max(probe[1], neighbour[1]),
                ),
            ),
        )
        stack.enter_context(
            patch(
                "world.lore.monster_activity.MONSTER_ACTIVITY_REGISTRY",
                {
                    _CONTACT: _activity(
                        _CONTACT, aggression=AggressionCondition("contact")
                    ),
                    _MOVE: _activity(
                        _MOVE, aggression=AggressionCondition("passive")
                    ),
                },
            )
        )
        stack.enter_context(
            patch(
                "world.lore.monster_activity.ACTIVITY_AREA_REGISTRY",
                {_GROUND: ground},
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        regional_population.initialize_population_seed(
            wilderness, seed=_SEED, tick=0
        )
        register_field_contact_stage()
        clock = get_world_clock()
        clock._persist(0)
        clock.tick = 0
        # A disposable database has no Limbo (#2) yet; give Evennia's default
        # home a real room for this run only (never a shipped setting change).
        from django.conf import settings as django_settings

        django_settings.DEFAULT_HOME = None
        django_settings.DEFAULT_START_LOCATION = None
        limbo = create_object(Room, key="smoke limbo")
        django_settings.DEFAULT_HOME = f"#{limbo.pk}"
        django_settings.DEFAULT_START_LOCATION = f"#{limbo.pk}"

        report: dict[str, object] = {"probe": probe, "neighbour": neighbour}

        player = create_object(PlayerCharacter, key="smoke traveller")
        player.race = next(iter(RACE_REGISTRY))
        player.apply_race_baseline()
        player.traits.hp.base = 1000
        player.traits.hp.current = 1000
        player.traits.agility.base = 20
        enter_wilderness(player, coordinates=probe, name=WILDERNESS_NAME)
        companion = create_object(
            NPC, key="smoke companion", location=player.location
        )
        companion.race = player.race
        companion.apply_race_baseline()
        companion.traits.hp.base = 500
        companion.traits.hp.current = 500
        join_party(companion, player)
        enter_wilderness(companion, coordinates=probe, name=WILDERNESS_NAME)
        enter_wilderness(player, coordinates=probe, name=WILDERNESS_NAME)
        write_fatigue_state(player, 360000, SleepPosture.AWAKE)
        write_fatigue_state(companion, 360000, SleepPosture.AWAKE)

        # -- 1. a clean wait on a cell with no hostile presence --------------
        clean = advance_wait(player, 60, operation_id="smoke:wait:clean")
        report["clean_wait"] = {
            "requested": clean.requested_seconds,
            "elapsed": clean.elapsed_seconds,
        }

        # -- 2. a real group move -------------------------------------------
        mover = _monster("smoke mover")
        _move_group_into_cell(wilderness, mover, neighbour)
        move_group = _group(
            wilderness,
            operation_id="smoke:move",
            activity_key=_MOVE,
            home=LocationRef.wilderness(WILDERNESS_NAME, *neighbour),
            position=LocationRef.wilderness(WILDERNESS_NAME, *neighbour),
            members=(mover.pk,),
            tick=clock.tick,
        )
        decision = None
        for tick in (clock.tick + 20, clock.tick + 40, clock.tick + 60,
                     clock.tick + 80, clock.tick + 100, clock.tick + 120):
            candidate = monster_activity.plan_group_decision(
                wilderness, move_group, tick=tick
            )
            if candidate.edge is not None:
                decision = candidate
                break
        if decision is None:
            raise RuntimeError("smoke: the group never chose a lawful move")
        monster_activity.commit_group_decision(wilderness, decision)
        journey = None
        after = decision.tick
        for _ in range(8):
            boundary = monster_activity.next_monster_activity_boundary(
                wilderness, after, after + 10**6
            )
            if boundary is None:
                break
            monster_activity.settle_monster_activity_at(wilderness, boundary)
            after = boundary
            group = monster_activity.group(wilderness, move_group)
            if group is not None and group.position != LocationRef.wilderness(
                WILDERNESS_NAME, *neighbour
            ):
                journey = group.position
                break
        if journey is None:
            group = monster_activity.group(wilderness, move_group)
            raise RuntimeError(
                f"smoke: group move never committed (position={group.position})"
            )
        report["group_move"] = {
            "group": move_group,
            "from": f"{neighbour[0]},{neighbour[1]}",
            "to": f"{journey.x},{journey.y}",
            "reason": decision.reason,
        }
        # The mover's own journey is reported; it must not join the later
        # contact roster, so retire the staging group and its body.
        monster_activity.release_group(wilderness, move_group)
        mover.delete()

        # -- 3. a wait interrupted by live contact ---------------------------
        contact_body = _monster("smoke contact")
        _move_group_into_cell(wilderness, contact_body, probe)
        engagement_tick = regional_population.current_population_tick()
        _group(
            wilderness,
            operation_id="smoke:contact",
            activity_key=_CONTACT,
            home=LocationRef.wilderness(WILDERNESS_NAME, *probe),
            position=LocationRef.wilderness(WILDERNESS_NAME, *probe),
            members=(contact_body.pk,),
            # The member cursor must equal the session's own start tick.
            tick=engagement_tick,
        )
        interrupted = None
        try:
            advance_wait(player, 60, operation_id="smoke:wait:contact")
        except Exception as error:  # the wait is refused after contact admission
            interrupted = type(error).__name__
        session = read_session(player)
        if session is None:
            raise RuntimeError("smoke: live contact admitted no combat session")
        report["interrupted_wait"] = {
            "requested": 60,
            "elapsed": 0,
            "refusal": interrupted,
            "session": session.session_id,
        }

        # -- 3. post-attempt energy failure ---------------------------------
        write_fatigue_state(player, 10, SleepPosture.AWAKE)
        write_fatigue_state(companion, 10, SleepPosture.AWAKE)
        battlefield = reconstruct_battlefield(player, session)
        failed_plan = plan_party_retreat(
            player,
            session,
            battlefield,
            operation_id="smoke:retreat:plan",
            preferred=None,
        )
        if failed_plan is not None:
            raise RuntimeError("smoke: exhausted reserve still produced a route")
        report["failed_energy"] = {"route": None, "reserve": 10}
        write_fatigue_state(player, 360000, SleepPosture.AWAKE)
        write_fatigue_state(companion, 360000, SleepPosture.AWAKE)

        # -- 4. paid retreat into an aggressive arrival cell ----------------
        destination = neighbour
        arrival_body = _monster("smoke arrival")
        _move_group_into_cell(wilderness, arrival_body, destination)
        arrival_tick = regional_population.current_population_tick()
        _group(
            wilderness,
            operation_id="smoke:arrival",
            activity_key=_CONTACT,
            home=LocationRef.wilderness(WILDERNESS_NAME, *destination),
            position=LocationRef.wilderness(WILDERNESS_NAME, *destination),
            members=(arrival_body.pk,),
            tick=arrival_tick,
        )
        source_ref = location_ref(player)
        target = None
        from world.rules.movement_edges import legal_edges, resolve_direction_edge
        from world.rules.travel_plan import DIRECTION_ORDER

        for edge in legal_edges(player, source_ref, (player, companion)):
            if edge.destination.kind != "wilderness":
                continue
            if (edge.destination.x, edge.destination.y) == destination:
                target = edge
                break
        if target is None:
            raise RuntimeError("smoke: no lawful edge into the arrival cell")
        for direction in DIRECTION_ORDER:
            reverse = resolve_direction_edge(
                target.destination,
                (target.destination.x, target.destination.y),
                direction,
            )
            if reverse is not None and reverse.destination == target.source:
                record_completed_edge(
                    player,
                    PhysicalEdge(
                        source=target.destination,
                        destination=target.source,
                        route=f"direction:{direction}",
                    ),
                )
                break
        else:
            raise RuntimeError("smoke: the retreat edge has no reverse")
        record = read_session(player)
        prompt = request_party_exit(
            player,
            record.session_id,
            record.round_revision,
            PARTY_EXIT_RETREAT,
        )
        tick_before = int(get_world_clock().tick)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = confirm_party_exit(
                player,
                prompt["session_id"],
                prompt["round_revision"],
                prompt["operation"],
                prompt["confirmation_token"],
            )
        travel = result.get("travel") or {}
        if result.get("outcome") != "fled" or not travel:
            raise RuntimeError(f"smoke: retreat did not travel ({result!r})")
        if location_ref(player) != target.destination:
            raise RuntimeError("smoke: the party did not arrive at the edge target")
        report["paid_retreat"] = {
            "outcome": result["outcome"],
            "from": f"{target.source.x},{target.source.y}",
            "to": f"{target.destination.x},{target.destination.y}",
            "travel_seconds": travel.get("seconds"),
            "clock_delta": int(get_world_clock().tick) - tick_before,
            "companion_at_destination": location_ref(companion)
            == target.destination,
        }

        # -- 5. immediate re-engagement at the destination ------------------
        reengaged = read_session(player)
        if reengaged is None:
            raise RuntimeError("smoke: the aggressive arrival admitted no session")
        report["reengagement"] = {
            "session": reengaged.session_id,
            "old_session": session.session_id,
            "different": reengaged.session_id != session.session_id,
            "enemies": list(reengaged.enemy_ids),
        }

        # -- 6. an actual enemy flee journey --------------------------------
        fleer = _monster("smoke fleer")
        fleer_cell = (probe[0] - 1, probe[1])
        _move_group_into_cell(wilderness, fleer, fleer_cell)
        fleer_group = _group(
            wilderness,
            operation_id="smoke:flee",
            activity_key=_MOVE,
            home=LocationRef.wilderness(WILDERNESS_NAME, *fleer_cell),
            position=LocationRef.wilderness(WILDERNESS_NAME, *fleer_cell),
            members=(fleer.pk,),
            tick=clock.tick,
        )
        del fleer_group
        escape = plan_individual_escape(
            fleer,
            None,
            WorldEscapeContext(
                session_id="smoke:flee",
                occurred_tick=int(clock.tick),
                source=LocationRef.wilderness(WILDERNESS_NAME, *fleer_cell),
                operation_id="smoke:flee",
            ),
        )
        if escape is None:
            raise RuntimeError("smoke: the flee had no lawful route")
        journey_id = monster_activity.commit_monster_departure(wilderness, escape)
        post_flee = monster_activity.journey(wilderness, journey_id)
        if post_flee is None:
            raise RuntimeError("smoke: the flee journey did not commit")
        monster_activity.settle_monster_activity_at(
            wilderness, post_flee.arrival_tick
        )
        arrived = ObjectDB.objects.get(id=fleer.pk)
        arrived_ref = location_ref(arrived)
        if arrived_ref == LocationRef.wilderness(WILDERNESS_NAME, *fleer_cell):
            raise RuntimeError("smoke: the enemy journey never arrived")
        report["enemy_journey"] = {
            "journey": journey_id,
            "arrived": f"{arrived_ref.x},{arrived_ref.y}",
            "tick": post_flee.arrival_tick,
        }

        # -- 7. committed reload --------------------------------------------
        reloaded = ObjectDB.objects.get(id=player.pk)
        reloaded_session = read_session(reloaded)
        if reloaded_session is None or reloaded_session.session_id != reengaged.session_id:
            raise RuntimeError("smoke: the committed session did not survive reload")
        report["committed_reload"] = {
            "session": reloaded_session.session_id,
            "enemies": list(reloaded_session.enemy_ids),
        }

        # Leave the disposable world without an active combat for a clean
        # report; the smoke itself made no shipped claim.
        forfeit(player)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return report
