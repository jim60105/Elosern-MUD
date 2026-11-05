"""Behaviour tests for the map-owned monster activity record and journeys.

The synthetic species/variant/zone/composition seams are injected into the
owner's own bindings, and every individual is constructed through the real
construction owner, so no shipped placement, count or prose value is pinned
here. Assertions establish ownership, identity, exact elapsed physiology and
real presence rather than fixture wording.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    WeightedComposition,
    variant_species_key,
)
from world.maps import monster_activity, regional_population as owner
from world.maps.monster_activity import (
    ACTIVITY_AWAKE_COMBAT,
    MONSTER_ACTIVITY_ATTRIBUTE,
    MonsterActivityError,
    MonsterActivityOperationInvalid,
    MonsterActivityStateInvalid,
    begin_monster_journey,
    commit_monster_departure,
    create_group,
    group,
    group_of_member,
    initialize_monster_activity,
    read_monster_activity,
    state_from_dict,
    state_to_dict,
)
from world.maps.regional_population import (
    commit_population_wave,
    initialize_population_seed,
    plan_population_wave,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.fatigue import SleepPosture, write_fatigue_state
from world.rules.monster_individual import construct_species_individual
from world.rules.movement_edges import LocationRef, PhysicalEdge
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries

PROBE = (500, 700)
ORDINARY = next(iter(SYNTH_MONSTER_VARIANTS))
SEED = 11
RESERVE = 360000
LOCAL = tuple((510 + offset, 700) for offset in range(4))


def _composition(key: str, activity: str, *ranges: tuple[int, int]) -> EncounterComposition:
    return EncounterComposition(
        key,
        activity,
        tuple(
            CompositionMember(ORDINARY, minimum, maximum)
            for minimum, maximum in ranges
        ),
    )


def _zone(
    key: str,
    *,
    pool: tuple[tuple[str, int], ...],
    lower: int = 60,
    upper: int = 90,
    capacity: int = 3,
    budget: int = 3,
) -> EcologyZone:
    return EcologyZone(
        key,
        "t_region_placeholder",
        ((0, 0, 0, 0),),
        tuple(WeightedComposition(composition_key, weight) for composition_key, weight in pool),
        lower,
        upper,
        capacity,
        recovery_delay=3600,
        replenishment_interval=600,
        wave_budget=budget,
    )


class ActivityRecordTests(RegistryIsolationMixin, EvenniaTest):
    """The strict record, its initialization gate and its codecs."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_activities",
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.region = region_for_coordinates(*PROBE)

    def _seed(self, seed: int = SEED) -> None:
        initialize_population_seed(self.wilderness, seed=seed, tick=0)

    def test_initialization_writes_one_empty_record_and_never_replaces_it(self):
        self.assertFalse(monster_activity.activity_provisioned(self.wilderness))
        self.assertRaises(
            MonsterActivityStateInvalid, read_monster_activity, self.wilderness
        )

        initialize_monster_activity(self.wilderness, tick=4)
        state = read_monster_activity(self.wilderness)
        self.assertEqual((state.groups, state.journeys, state.receipts), ({}, {}, {}))
        self.assertEqual(state.settled_through_tick, 4)

        self.wilderness.db.monster_activity = {**state_to_dict(state)}
        saved = dict(self.wilderness.db.monster_activity)
        initialize_monster_activity(self.wilderness, tick=9)
        self.assertEqual(dict(self.wilderness.db.monster_activity), saved)

    def test_missing_and_malformed_state_refuse_without_reset(self):
        self._seed()
        self.assertTrue(monster_activity.activity_provisioned(self.wilderness))
        saved = dict(self.wilderness.db.monster_activity)

        for malformed in (
            {**saved, "groups": []},
            {**saved, "unknown": 1},
            {**saved, "settled_through_tick": True},
        ):
            with self.subTest(malformed=malformed):
                self.wilderness.db.monster_activity = malformed
                self.assertRaises(
                    MonsterActivityStateInvalid,
                    read_monster_activity,
                    self.wilderness,
                )
        self.wilderness.db.monster_activity = saved
        self.assertEqual(state_to_dict(read_monster_activity(self.wilderness)), saved)

    @covers_requirement(
        "monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay"
    )
    def test_codec_roundtrip_is_exact_and_rejects_unknown_shape(self):
        self._seed()
        cell = LOCAL[0]
        ref = LocationRef.wilderness(WILDERNESS_NAME, *cell)
        group_id = create_group(
            self.wilderness,
            operation_id="op:1",
            owner_kind="zone",
            owner_key="t_zone",
            activity_key="t_whisper_quail_solitary_activity",
            home=ref,
            position=ref,
            member_ids=(101, 102),
            seed=SEED,
            tick=3,
        )
        state = read_monster_activity(self.wilderness)
        encoded = state_to_dict(state)
        self.assertEqual(state_to_dict(state_from_dict(encoded)), encoded)
        self.assertEqual(
            encoded["groups"][group_id]["home"],
            {"kind": "wilderness", "map": WILDERNESS_NAME, "x": cell[0], "y": cell[1]},
        )
        broken = state_to_dict(read_monster_activity(self.wilderness))
        broken["groups"][group_id]["member_time"]["999"] = broken["groups"][group_id][
            "member_time"
        ]["101"]
        self.assertRaises(MonsterActivityStateInvalid, state_from_dict, broken)

    def test_a_member_in_two_groups_is_rejected(self):
        self._seed()
        ref = LocationRef.wilderness(WILDERNESS_NAME, *LOCAL[0])
        first = create_group(
            self.wilderness,
            operation_id="first",
            owner_kind="explicit",
            owner_key="test",
            activity_key=monster_activity.STAGED_STATIONARY_ACTIVITY,
            home=ref,
            position=ref,
            member_ids=(101,),
            seed=SEED,
            tick=0,
        )
        second = create_group(
            self.wilderness,
            operation_id="second",
            owner_kind="explicit",
            owner_key="test",
            activity_key=monster_activity.STAGED_STATIONARY_ACTIVITY,
            home=ref,
            position=ref,
            member_ids=(102,),
            seed=SEED,
            tick=0,
        )
        broken = state_to_dict(read_monster_activity(self.wilderness))
        broken["groups"][second]["member_ids"] = [101]
        broken["groups"][second]["member_time"] = {"101": broken["groups"][first]["member_time"]["101"]}
        self.assertRaises(MonsterActivityStateInvalid, state_from_dict, broken)


class GroupConstructionTests(RegistryIsolationMixin, EvenniaTest):
    """Construction owners create the one initial group per occurrence."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_activities",
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.region = region_for_coordinates(*PROBE)
        self.compositions = {
            "t_three_a": _composition(
                "t_three_a", "t_whisper_quail_group_activity", (3, 3)
            ),
            "t_three_b": _composition(
                "t_three_b", "t_whisper_quail_solitary_activity", (3, 3)
            ),
        }
        self.enterContext(
            patch.object(
                owner,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(dict(self.compositions)),
            )
        )
        self.enterContext(
            patch.object(owner, "SETTLEMENT_BIRTH_POLICY_REGISTRY", MappingProxyType({}))
        )
        self.enterContext(
            patch.object(owner, "eligible_birth_cells", lambda *a, **k: LOCAL)
        )
        self.enterContext(
            patch.object(owner, "_region_cells", lambda zone: frozenset(LOCAL))
        )

    def _use(
        self, zone: EcologyZone, *, cells: tuple[tuple[int, int], ...] = LOCAL
    ) -> EcologyZone:
        zone = EcologyZone(
            zone.key,
            self.region,
            zone.rectangles,
            zone.pool,
            zone.lower_density,
            zone.upper_density,
            zone.cell_capacity,
            zone.recovery_delay,
            zone.replenishment_interval,
            zone.wave_budget,
        )
        self.enterContext(
            patch.object(
                owner, "ECOLOGY_ZONE_REGISTRY", MappingProxyType({zone.key: zone})
            )
        )
        self.enterContext(
            patch.object(owner, "eligible_birth_cells", lambda *a, **k: cells)
        )
        self.enterContext(
            patch.object(owner, "_region_cells", lambda scope: frozenset(cells))
        )
        return zone

    def _seed(self) -> None:
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)

    def _initialize_state(self, zone: EcologyZone, *, tick: int = 0) -> None:
        states = dict(self.wilderness.db.regional_population or {})
        states[zone.key] = {
            "initialized": True,
            "seed": SEED,
            "generation_sequence": 0,
            "recovery_due_tick": None,
            "settled_through_tick": tick,
        }
        self.wilderness.db.regional_population = states

    def test_identical_member_rows_keep_their_own_selected_binding(self):
        zone = self._use(
            _zone(
                "t_zone",
                pool=(("t_three_a", 1),),
            )
        )
        self._seed()
        self._initialize_state(zone)
        plan = plan_population_wave(self.wilderness, zone.key, tick=0)
        self.assertEqual(plan.placements[0].composition_key, "t_three_a")
        self.assertEqual(
            plan.placements[0].activity_key, "t_whisper_quail_group_activity"
        )
        created = commit_population_wave(self.wilderness, plan)
        self.assertEqual(len(created), 3)

        first = read_monster_activity(self.wilderness)
        self.assertEqual(len(first.groups), 1)
        (first_group,) = first.groups.values()
        self.assertEqual(set(first_group.member_ids), set(created))
        self.assertEqual(
            first_group.activity_key, "t_whisper_quail_group_activity"
        )
        self.assertEqual(first_group.home_owner, ("zone", zone.key))

        other = self._use(
            _zone(
                "t_zone_b",
                pool=(("t_three_b", 1),),
            ),
            cells=tuple((520 + offset, 700) for offset in range(4)),
        )
        self._initialize_state(other)
        other_plan = plan_population_wave(self.wilderness, other.key, tick=0)
        self.assertEqual(
            other_plan.placements[0].activity_key,
            "t_whisper_quail_solitary_activity",
        )
        commit_population_wave(self.wilderness, other_plan)
        second = read_monster_activity(self.wilderness)
        # The solitary three-member wave disperses into three one-member
        # groups, so one cohesive group plus three solitary ones stand here.
        self.assertEqual(len(second.groups), 4)
        self.assertEqual(
            {entry.activity_key for entry in second.groups.values()},
            {
                "t_whisper_quail_group_activity",
                "t_whisper_quail_solitary_activity",
            },
        )
        solitary = [
            entry
            for entry in second.groups.values()
            if entry.activity_key == "t_whisper_quail_solitary_activity"
        ]
        self.assertEqual(len(solitary), 3)
        self.assertTrue(all(len(entry.member_ids) == 1 for entry in solitary))

    def test_a_replayed_commit_cannot_replace_a_foreign_group(self):
        zone = self._use(_zone("t_zone", pool=(("t_three_a", 1),)))
        self._seed()
        self._initialize_state(zone)
        plan = plan_population_wave(self.wilderness, zone.key, tick=0)
        commit_population_wave(self.wilderness, plan)
        before = state_to_dict(read_monster_activity(self.wilderness))
        from world.maps.regional_population import PopulationPlanStale

        self.assertRaises(
            PopulationPlanStale,
            commit_population_wave,
            self.wilderness,
            plan,
        )
        self.assertEqual(
            state_to_dict(read_monster_activity(self.wilderness)), before
        )

    def test_a_group_collision_refuses_instead_of_absorbing_identities(self):
        self._seed()
        ref = LocationRef.wilderness(WILDERNESS_NAME, *LOCAL[0])
        create_group(
            self.wilderness,
            operation_id="op",
            owner_kind="explicit",
            owner_key="gm:1",
            activity_key=monster_activity.STAGED_STATIONARY_ACTIVITY,
            home=ref,
            position=ref,
            member_ids=(1,),
            seed=SEED,
            tick=0,
        )
        self.assertRaises(
            MonsterActivityOperationInvalid,
            create_group,
            self.wilderness,
            operation_id="op",
            owner_kind="explicit",
            owner_key="gm:2",
            activity_key=monster_activity.STAGED_STATIONARY_ACTIVITY,
            home=ref,
            position=ref,
            member_ids=(2,),
            seed=SEED,
            tick=0,
        )
        (group_record,) = read_monster_activity(self.wilderness).groups.values()
        self.assertEqual(group_record.member_ids, (1,))
        self.assertEqual(group_record.home_owner, ("explicit", "gm:1"))

    def test_membership_survives_a_member_standing_away_until_it_moves_group(self):
        zone = self._use(_zone("t_zone", pool=(("t_three_a", 1),)))
        self._seed()
        self._initialize_state(zone)
        plan = plan_population_wave(self.wilderness, zone.key, tick=0)
        created = commit_population_wave(self.wilderness, plan)
        member = ObjectDB.objects.get(id=created[0])
        member.db.site_key = None
        # A coordinate change is not a group change: membership is durable.
        self.wilderness.db.itemcoordinates[member] = LOCAL[1]
        found = group_of_member(self.wilderness, member.pk)
        self.assertIsNotNone(found)
        self.assertIn(member.pk, found.member_ids)


class MappedFleeIntegrationTests(EvenniaTest):
    """A real enemy flee through departure, arrival and re-engagement."""

    def setUp(self):
        super().setUp()
        from world.rules.tests.test_combat_session_flow._support import _open_scope

        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        _open_scope(self)
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        self.assertTrue(
            enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        )
        self.room = self.char1.location
        neighbours = (
            (PROBE[0] + 1, PROBE[1]),
            (PROBE[0] + 1, PROBE[1] + 1),
            (PROBE[0], PROBE[1] + 1),
            (PROBE[0] - 1, PROBE[1] + 1),
            (PROBE[0] - 1, PROBE[1]),
            (PROBE[0] - 1, PROBE[1] - 1),
            (PROBE[0], PROBE[1] - 1),
            (PROBE[0] + 1, PROBE[1] - 1),
        )
        for cell in neighbours:
            enter_wilderness(self.char1, coordinates=cell, name=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location

    def _enemy(self, key: str):
        individual = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        individual.key = key
        individual.traits.hp.base = 100000
        individual.traits.hp.current = 100000
        individual.location = self.room
        self.room.contents_cache.add(individual)
        self.wilderness.db.itemcoordinates[individual] = PROBE
        write_fatigue_state(individual, RESERVE, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id=f"enemy:{key}",
            owner_kind="zone",
            owner_key="t_zone",
            activity_key="t_whisper_quail_solitary_activity",
            home=LocationRef.wilderness(WILDERNESS_NAME, *PROBE),
            position=LocationRef.wilderness(WILDERNESS_NAME, *PROBE),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=0,
        )
        return individual

    @covers_requirement(
        "monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure",
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence",
    )
    def test_a_two_enemy_rounds_flee_departs_and_reengages_the_same_identity(self):
        from unittest.mock import patch

        from world.rules.action import ActionRequest
        from world.rules.combat_session import (
            BASIC_ATTACK_KEY,
            engage_group,
            read_session,
            submit_player_action,
        )
        from world.rules.combat_session.policies import _enemy_policy
        from world.rules.disengage import FLEE_SKILL_KEY
        from world.rules.fatigue import read_optional_fatigue_state

        from world.rules.tests._combat_session_helpers import _player

        actor = _player("mapped hunter")
        actor.location = self.room
        for key in ("atk_phys", "agility", "defense"):
            getattr(actor.traits, key).base = 200
        actor.traits.hp.base = 2000
        actor.traits.hp.current = 2000
        fleeing = self._enemy("fleeing")
        remaining = self._enemy("remaining")
        start_reserve = read_optional_fatigue_state(fleeing)
        engage_group(actor, [fleeing, remaining])
        record = read_session(actor)
        self.assertIsNotNone(record)
        flee_round = {"value": False}

        def policy(entity, battlefield, *, context=None, scale=1.0, decision=None):
            if flee_round["value"] and entity.pk == fleeing.pk:
                return ActionRequest(entity, FLEE_SKILL_KEY, [entity], context)
            return ActionRequest(entity, BASIC_ATTACK_KEY, [actor], context)

        with (
            patch(
                "world.rules.combat_session.policies.monster_behaviour_policy",
                side_effect=policy,
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            first = submit_player_action(actor, BASIC_ATTACK_KEY, [remaining])
            self.assertEqual(first["outcome"], "round")
            flee_round["value"] = True
            with patch(
                "world.rules.disengage._attempt_flee",
                return_value=(
                    True,
                    {
                        "roll": 100,
                        "actor_agility": 200.0,
                        "pursuer_agility": 200.0,
                    },
                ),
            ):
                second = submit_player_action(actor, BASIC_ATTACK_KEY, [remaining])
        self.assertEqual(second["outcome"], "round", second)
        attempts = [
            entry
            for log in second["logs"]
            for entry in log.entries
            if entry.kind == "disengage_attempt"
        ]
        self.assertTrue(attempts, second)
        self.assertTrue(attempts[0].data["success"], attempts[0].data)
        session = read_session(actor)
        self.assertIn(int(fleeing.pk), session.fled_ids)
        self.assertNotIn(int(remaining.pk), session.fled_ids)
        # Only the chosen enemy departed, with its home ownership intact.
        journey = next(
            iter(read_monster_activity(self.wilderness).journeys.values())
        )
        self.assertEqual(journey.member_ids, (fleeing.pk,))
        self.assertEqual(journey.depart_tick, session.started_tick + 12)
        self.assertNotIn(fleeing, self.wilderness.db.itemcoordinates)
        self.assertIsNone(fleeing.location)
        self.assertEqual(
            group_of_member(self.wilderness, remaining.pk).home_owner,
            ("zone", "t_zone"),
        )
        # The departed enemy paid exactly the two rounds of combat in which it
        # fought, and remains alive with that reduced reserve.
        from world.rules.fatigue import (
            FatigueActivity,
            IntervalCompletion,
            predict_interval,
        )

        expected = predict_interval(
            start_reserve,
            FatigueActivity.AWAKE_COMBAT,
            12,
            completion=IntervalCompletion.INDIVISIBLE,
        ).end.reserve_units
        self.assertEqual(read_optional_fatigue_state(fleeing).reserve_units, expected)
        # The journey is settled by real game time, not by the enemy action.
        monster_activity.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        destination = (journey.destination.x, journey.destination.y)
        self.assertEqual(
            self.wilderness.db.itemcoordinates.get(fleeing), destination
        )
        from world.rules.combat_session import forfeit

        forfeit(actor)
        self.assertIsNone(read_session(actor))
        enter_wilderness(actor, coordinates=destination, name=WILDERNESS_NAME)
        self.assertIs(fleeing.location, actor.location)
        engaged = engage_group(actor, [fleeing])
        self.assertIn(int(fleeing.pk), engaged["record"].enemy_ids)
        self.assertTrue(ObjectDB.objects.filter(pk=fleeing.pk).exists())

    def test_a_rejected_opening_restores_admission_activity_and_physiology(self):
        from unittest.mock import patch

        from world.rules import combat_initiation
        from world.rules.combat_session import BASIC_ATTACK_KEY
        from world.rules.fatigue import read_optional_fatigue_state
        from world.rules.tests._combat_session_helpers import _player

        actor = _player("rollback hunter")
        actor.location = self.room
        for key in ("atk_phys", "agility", "defense"):
            getattr(actor.traits, key).base = 200
        actor.traits.hp.base = 2000
        actor.traits.hp.current = 2000
        enemy = self._enemy("rollback")
        from world.rules.clock import get_world_clock

        get_world_clock().tick = 30
        before = monster_activity.state_to_dict(
            read_monster_activity(self.wilderness)
        )
        before_reserve = read_optional_fatigue_state(enemy).reserve_units
        with patch.object(
            combat_initiation,
            "submit_opening_action",
            return_value={"outcome": "rejected", "reason": "synthetic"},
        ) as submit:
            result = combat_initiation.initiate_field_combat(
                actor, BASIC_ATTACK_KEY, enemy
            )
        self.assertEqual(result["outcome"], "rejected")
        submit.assert_called_once()
        self.assertEqual(
            monster_activity.state_to_dict(read_monster_activity(self.wilderness)),
            before,
        )
        self.assertEqual(
            read_optional_fatigue_state(enemy).reserve_units, before_reserve
        )
        self.assertIsNone(actor.db.active_combat)

    def test_a_partial_admission_failure_restores_the_activity_record(self):
        from unittest.mock import patch

        from world.rules.combat_session import engage_group
        from world.rules.tests._combat_session_helpers import _player

        actor = _player("partial hunter")
        actor.location = self.room
        first = self._enemy("partial-a")
        second = self._enemy("partial-b")
        before = monster_activity.state_to_dict(
            read_monster_activity(self.wilderness)
        )
        real = monster_activity.begin_member_combat
        calls = {"count": 0}

        def fail_second(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("synthetic partial admission failure")
            return real(*args, **kwargs)

        with patch.object(
            monster_activity, "begin_member_combat", side_effect=fail_second
        ):
            with self.assertRaises(RuntimeError):
                engage_group(actor, [first, second])
        self.assertEqual(
            monster_activity.state_to_dict(read_monster_activity(self.wilderness)),
            before,
        )
        self.assertIsNone(actor.db.active_combat)


class MappedPresenceConsumerTests(EvenniaTest):
    """Transit is absent from every actual-presence consumer."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        self.assertTrue(
            enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        )
        self.room = self.char1.location
        neighbours = (
            (PROBE[0] + 1, PROBE[1]),
            (PROBE[0] + 1, PROBE[1] + 1),
            (PROBE[0], PROBE[1] + 1),
            (PROBE[0] - 1, PROBE[1] + 1),
            (PROBE[0] - 1, PROBE[1]),
            (PROBE[0] - 1, PROBE[1] - 1),
            (PROBE[0], PROBE[1] - 1),
            (PROBE[0] + 1, PROBE[1] - 1),
        )
        for cell in neighbours:
            enter_wilderness(self.char1, coordinates=cell, name=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location

    def _departing_monster(self):
        from world.rules.fatigue import write_fatigue_state
        from world.rules.world_escape import (
            WorldEscapeContext,
            plan_individual_escape,
        )

        individual = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        individual.location = self.room
        self.room.contents_cache.add(individual)
        self.wilderness.db.itemcoordinates[individual] = PROBE
        write_fatigue_state(individual, RESERVE, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id="consumer",
            owner_kind="zone",
            owner_key="t_zone",
            activity_key="t_whisper_quail_solitary_activity",
            home=LocationRef.wilderness(WILDERNESS_NAME, *PROBE),
            position=LocationRef.wilderness(WILDERNESS_NAME, *PROBE),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=0,
        )
        context = WorldEscapeContext(
            session_id="hostile:3:0",
            occurred_tick=6,
            source=LocationRef.wilderness(WILDERNESS_NAME, *PROBE),
            operation_id="consumer:escape",
        )
        plan = plan_individual_escape(individual, None, context)
        journey_id = commit_monster_departure(self.wilderness, plan)
        journey = read_monster_activity(self.wilderness).journeys[journey_id]
        return individual, journey

    @covers_requirement(
        "wilderness-population-view::population-reads-report-actual-living-registrations"
    )
    def test_population_view_and_gm_inspection_never_show_transit_at_either_endpoint(self):
        from world.maps.wilderness_population import population_view
        from world.rules.travel_interrupts import live_hostile_facts
        from web.gm.readers import monsters as reader

        individual, journey = self._departing_monster()
        destination = (journey.destination.x, journey.destination.y)
        cells = [PROBE, destination]
        facts = population_view(self.wilderness, cells)
        self.assertNotIn(
            f"object:{individual.pk}",
            {fact.observation_key for fact in facts},
        )
        self.assertEqual(
            [
                fact
                for fact in live_hostile_facts(self.room, cells)
                if fact.observation_key == f"object:{individual.pk}"
            ],
            [],
        )
        section = reader.placement_section(individual)
        labels = {entry["label"] for entry in section["rows"]}
        self.assertIn("旅程", labels)
        self.assertNotIn("所在房間", labels)
        # A stale text or browser lookup by name/contents finds no present body.
        self.assertFalse(self.room.search(individual.key))
        self.assertNotIn(individual, self.room.contents)

        monster_activity.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        after = population_view(self.wilderness, [destination])
        self.assertIn(
            f"object:{individual.pk}",
            {fact.observation_key for fact in after if fact.cell == destination},
        )
        section = reader.placement_section(individual)
        labels = {entry["label"] for entry in section["rows"]}
        self.assertNotIn("旅程", labels)
