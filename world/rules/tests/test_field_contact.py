"""Authored field contact admits immediate whole-cell combat.

Every test drives a production boundary, never the evaluator in isolation:
a committed relocation through ``settle_movement``, the registered clock
source (``WorldClock.advance`` with the population/field-contact stages), the
owning skip/cast writers, or the real terminal settlement. The assertions
cover the whole-cell A+A+B roster, the forced-sleep wake threshold, voluntary
and forced receipts, the pre-action boundary, protection and re-co-location,
and a late-failure rollback of every admission surface.
"""

from __future__ import annotations

from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.rooms import Room
from world.maps import regional_population
from world.maps.monster_activity import create_group
from world.maps.population_lifecycle import register_regional_population
from world.maps.regional_population import initialize_population_seed
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)
from world.rules.action import RejectReason
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    clear_session,
    get_required_combat_actors,
    read_session,
    reconstruct_battlefield,
    forfeit,
)
from world.rules.fatigue import (
    SleepPosture,
    project_fatigue_status,
    read_optional_fatigue_state,
    write_fatigue_state,
)
from world.rules.field_contact import (
    CONTACT_EVENT,
    SOURCE_MOVEMENT,
    admit_field_contact_at,
    continue_admitted_contacts,
    evaluate_field_contact,
    register_field_contact_stage,
)
from world.rules.field_cast import cast_in_field
from world.rules.mental_time import plan_for
from world.rules.monster_individual import construct_species_individual
from world.rules.movement_edges import LocationRef
from world.rules.movement_settlement import settle_movement
from world.rules.sleep_receipt import (
    KIND_FORCED,
    MODE_FORCED_THRESHOLD,
    STATE_INTERRUPTED,
    STATE_SLEEPING,
    SleepReceipt,
    read_sleep_receipt,
    write_sleep_receipt,
)
from world.rules.time_skip import SkipRefused, advance_wait, begin_sleep, interrupt_sleep_for_contact
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries

from ._combat_session_helpers import BattlefieldIsolation, _monster, _player

_PROBE = (500, 700)
_SEED = 11
_CONTACT = "t_whisper_quail_group_activity"
_PASSIVE = "t_whisper_quail_solitary_activity"


def _write(entity, reserve, posture):
    write_fatigue_state(entity, reserve, posture)
    project_fatigue_status(entity)


class _ContactBase(BattlefieldIsolation, EvenniaTestCase):
    """A provisioned wilderness with a plain destination room for arrivals."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "activity_areas",
                "monster_activities",
                "encounter_compositions",
                "ecology_zones",
                "monster_sites",
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(self.wilderness, seed=_SEED, tick=0)
        register_regional_population()
        from world.maps import population_lifecycle
        from world.rules import clock as clock_module

        self.addCleanup(
            clock_module._EVENT_SOURCES.pop, population_lifecycle.STAGE_KIND, None
        )
        register_field_contact_stage()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, "field_contact", None)
        self.origin = create_object(Room, key="contact origin")
        self.destination = create_object(Room, key="contact destination")
        self.player = _player("contact player")
        self.player.location = self.origin
        self.player.traits.hp.base = 5000
        self.player.traits.hp.current = 5000
        _write(self.player, 360000, SleepPosture.AWAKE)

    def _enemy(self, key, activity_key, *, hp=1000, cell=_PROBE):
        species = next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key
        enemy = construct_species_individual(
            species, next(iter(SYNTH_MONSTER_VARIANTS))
        )
        enemy.key = key
        enemy.traits.hp.base = hp
        enemy.traits.hp.current = hp
        enemy.location = self.destination
        self.destination.contents_cache.add(enemy)
        self.wilderness.db.itemcoordinates[enemy] = cell
        _write(enemy, 360000, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id=f"contact:{key}:{enemy.pk}",
            owner_kind="zone",
            owner_key="t_zone",
            activity_key=activity_key,
            home=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            position=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            member_ids=(enemy.pk,),
            seed=_SEED,
            tick=0,
        )
        return enemy

    def _walk_in(self):
        return settle_movement(
            self.player,
            self.origin,
            destination=self.destination,
            traverse=lambda: self.player.move_to(self.destination, quiet=True),
            route=None,
        )


class WholeCellArrivalTests(_ContactBase):
    """A real relocation admits one session with every living local monster."""

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_an_arrival_admits_a_a_b_once_with_no_free_opening_attack(self):
        first = self._enemy("A", _CONTACT)
        second = self._enemy("A", _CONTACT)
        passive = self._enemy("B", _PASSIVE)
        hp_before = {
            int(enemy.pk): float(enemy.traits.hp.current)
            for enemy in (first, second, passive)
        }
        tick_before = get_world_clock().tick
        with patch("world.rules.field_contact.log_info") as info, (
            self.captureOnCommitCallbacks(execute=True)
        ):
            self._walk_in()
        admitted = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "field_contact_admitted"
        ]
        self.assertEqual(len(admitted), 1)
        context = admitted[0].kwargs["context"]
        self.assertEqual(context["source_id"], SOURCE_MOVEMENT)
        self.assertEqual(context["tick"], tick_before)
        self.assertEqual(
            context["enemies"],
            ",".join(
                str(pk)
                for pk in sorted(int(e.pk) for e in (first, second, passive))
            ),
        )
        record = read_session(self.player)
        self.assertIsNotNone(record)
        self.assertEqual(
            record.enemy_ids, tuple(sorted(int(e.pk) for e in (first, second, passive)))
        )
        # No free opening action or time: the encounter is an ordinary
        # interactive session, no round elapsed and no enemy lost HP.
        self.assertEqual((record.rounds_elapsed, record.settled_rounds), (0, 0))
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertIn(
            int(self.player.pk),
            get_required_combat_actors(
                record, reconstruct_battlefield(self.player, record)
            ),
        )
        for enemy in (first, second, passive):
            self.assertEqual(
                float(enemy.traits.hp.current), hp_before[int(enemy.pk)]
            )
        self.assertEqual(record.started_tick, tick_before)
        self.assertEqual(record.session_id, f"hostile:{self.player.pk}:{tick_before}")

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_passive_and_defended_conditions_do_not_admit(self):
        passive = self._enemy("passive", _PASSIVE)
        self.assertIsNone(evaluate_field_contact(self.player, tick=0))
        result = admit_field_contact_at(self.player, source_id=SOURCE_MOVEMENT)
        self.assertIsNone(result)
        self.assertIsNone(read_session(self.player))
        self.assertTrue(passive.pk)

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_a_read_preview_never_admits(self):
        self._enemy("A", _CONTACT)
        from world.rules.combat_initiation import preview_field_opening

        preview = preview_field_opening(self.player, BASIC_ATTACK_KEY, None)
        self.assertFalse(preview.enabled)
        self.assertIsNone(read_session(self.player))


class ForcedWakeThroughAdmissionTests(_ContactBase):
    """The predecessor continuation runs after the owning admission returns."""

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_forced_71928_reaches_72000_after_one_real_enemy_round(self):
        from world.rules.combat_session import policies as session_policies

        enemy = self._enemy("forced wake goblin", _CONTACT)
        self.player.location = self.destination
        _write(self.player, 71928, SleepPosture.FORCED)
        tick_before = get_world_clock().tick
        with (
            patch.object(
                session_policies,
                "_enemy_policy",
                side_effect=lambda entity, field, record: (
                    session_policies._basic_attack_request(entity, field, record)
                ),
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            result = admit_field_contact_at(self.player, source_id=SOURCE_MOVEMENT)
        self.assertIsNotNone(result)
        continuation = result["continuation"]
        self.assertEqual(continuation["continued_rounds"], 1)
        record = read_session(self.player)
        self.assertEqual((record.rounds_elapsed, record.settled_rounds), (1, 1))
        self.assertEqual(get_world_clock().tick, tick_before + 6)
        state = read_optional_fatigue_state(self.player)
        self.assertEqual(state.reserve_units, 72000)
        self.assertIs(state.posture, SleepPosture.AWAKE)
        self.assertIsNotNone(read_session(self.player))
        self.assertIn(int(enemy.pk), record.enemy_ids)


class ConditionAuthorityTests(_ContactBase):
    """Declared dayparts and defended areas decide admission, not rarity."""

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_daypart_gated_contact_admits_only_in_its_declared_region(self):
        from world.lore.monster_activity import (
            ActivityArea,
            AggressionCondition,
            MonsterActivity,
        )

        activity = MonsterActivity(
            "t_dawn_contact",
            "solitary_roaming",
            "t_contact_ground",
            60,
            AggressionCondition("contact", dayparts=("dawn",)),
        )
        area = ActivityArea(
            "t_contact_ground", "t_bramble_wold", ((500, 519, 700, 719),)
        )
        self._enemy("dawn hunter", "t_dawn_contact")
        self.player.location = self.destination
        with (
            patch(
                "world.lore.monster_activity.MONSTER_ACTIVITY_REGISTRY",
                {"t_dawn_contact": activity},
            ),
            patch(
                "world.lore.monster_activity.ACTIVITY_AREA_REGISTRY",
                {"t_contact_ground": area},
            ),
        ):
            self.assertIsNone(evaluate_field_contact(self.player, tick=0))
            dawn = 6 * 3600
            contact = evaluate_field_contact(self.player, tick=dawn)
            self.assertIsNotNone(contact)
            self.assertEqual(contact.source_id, "field")

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_defended_area_admits_only_inside_its_geometry(self):
        from world.lore.monster_activity import (
            ActivityArea,
            AggressionCondition,
            MonsterActivity,
        )

        activity = MonsterActivity(
            "t_nest_guard",
            "stationary",
            "t_nest_home",
            60,
            AggressionCondition("defended_area", "t_nest_ring"),
        )
        home = ActivityArea("t_nest_home", home_radius=0)
        ring = ActivityArea("t_nest_ring", home_radius=0)
        enemy = self._enemy("nest guard", "t_nest_guard")
        self.player.location = self.destination
        registries = (
            patch(
                "world.lore.monster_activity.MONSTER_ACTIVITY_REGISTRY",
                {"t_nest_guard": activity},
            ),
            patch(
                "world.lore.monster_activity.ACTIVITY_AREA_REGISTRY",
                {"t_nest_home": home, "t_nest_ring": ring},
            ),
        )
        with registries[0], registries[1]:
            self.assertIsNotNone(evaluate_field_contact(self.player, tick=0))
            self.wilderness.db.itemcoordinates[enemy] = (501, 700)
            self.assertIsNone(evaluate_field_contact(self.player, tick=0))


class SleepInterruptionTests(_ContactBase):
    """Voluntary sleep interrupts through its owner; forced sleep stays."""

    def _voluntary(self, seconds=600):
        outcome = begin_sleep(
            self.player, mode="duration", seconds=seconds, allow_continue=False
        )
        self.assertIsNotNone(outcome.entry)
        self.assertIs(read_optional_fatigue_state(self.player).posture,
                      SleepPosture.VOLUNTARY)

    @covers_requirement(
        "hostile-field-contact::hostile-sleep-interruption-preserves-accepted-body-state"
    )
    def test_voluntary_receipt_interrupts_without_refill_or_resume(self):
        _write(self.player, 100000, SleepPosture.AWAKE)
        self._voluntary()
        receipt_before = read_sleep_receipt(self.player)
        self.assertIsNotNone(receipt_before)
        reserve_before = read_optional_fatigue_state(self.player).reserve_units
        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        tick = int(get_world_clock().tick) + 60
        from world.rules.combat_session import policies as session_policies

        with (
            patch.object(
                session_policies,
                "_enemy_policy",
                side_effect=lambda entity, field, record: (
                    session_policies._basic_attack_request(entity, field, record)
                ),
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            outcome = admit_field_contact_at(
                self.player, source_id=SOURCE_MOVEMENT, tick=tick
            )
        self.assertIsNotNone(outcome)
        state = read_optional_fatigue_state(self.player)
        self.assertIs(state.posture, SleepPosture.AWAKE)
        # Partial actual recovery only (sleep rate), never a refill.
        self.assertGreater(state.reserve_units, reserve_before)
        self.assertLess(state.reserve_units, 252000)
        receipt = read_sleep_receipt(self.player)
        self.assertEqual(receipt.state, STATE_INTERRUPTED)
        self.assertEqual(receipt.settled_through_tick, tick)
        self.assertIsNotNone(read_session(self.player))

    @covers_requirement(
        "hostile-field-contact::hostile-sleep-interruption-preserves-accepted-body-state"
    )
    def test_forced_receipt_keeps_its_posture_and_threshold(self):
        receipt = SleepReceipt(
            sleep_id="forced:test:0",
            body_id=int(self.player.pk),
            owner_id=None,
            kind=KIND_FORCED,
            mode=MODE_FORCED_THRESHOLD,
            entry_tick=0,
            target_tick=10000,
            limit_tick=10000,
            settled_through_tick=0,
            revision=0,
            state=STATE_SLEEPING,
            accepted_seconds=10000,
            partial=False,
        )
        _write(self.player, 50000, SleepPosture.FORCED)
        write_sleep_receipt(self.player, receipt)
        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        tick = int(get_world_clock().tick) + 60
        from world.rules.combat_session import policies as session_policies

        with (
            patch.object(
                session_policies,
                "_enemy_policy",
                side_effect=lambda entity, field, record: (
                    session_policies._basic_attack_request(entity, field, record)
                ),
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            outcome = admit_field_contact_at(
                self.player, source_id=SOURCE_MOVEMENT, tick=tick
            )
        self.assertIsNotNone(outcome)
        self.assertIs(read_optional_fatigue_state(self.player).posture,
                      SleepPosture.FORCED)
        persisted = read_sleep_receipt(self.player)
        self.assertEqual(persisted.state, STATE_SLEEPING)
        self.assertEqual(persisted.target_tick, 10000)
        # Only the real six-second enemy round's sleep recovery is paid; the
        # forced posture, target and threshold contract are untouched.
        self.assertEqual(
            read_optional_fatigue_state(self.player).reserve_units, 50000 + 7200
        )


class PreActionBoundaryTests(_ContactBase):
    """A co-located authored contact admits before any exploration spend."""

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_wait_admits_and_spends_no_time(self):
        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        tick_before = get_world_clock().tick
        reserve_before = read_optional_fatigue_state(self.player).reserve_units
        with self.assertRaises(SkipRefused):
            advance_wait(self.player, 600)
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertEqual(
            read_optional_fatigue_state(self.player).reserve_units, reserve_before
        )
        self.assertIsNotNone(read_session(self.player))

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_ordinary_cast_reports_the_admitted_encounter(self):
        from world.tests.synthetic_data import make_skill
        from world.skills.registry import SkillCategory, TargetSpec
        from .test_combat_session_flow._support import _open_scope

        skill = make_skill(
            "t_contact_lookout",
            label="警戒",
            description="看清周圍。",
            target_spec=TargetSpec.SELF,
            cost={},
            effects=[],
            category=SkillCategory.ENHANCEMENT,
        )
        _open_scope(self, **{skill.key: skill})
        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        tick_before = get_world_clock().tick
        outcome = cast_in_field(self.player, skill.key)
        self.assertEqual(outcome.route, "rejected")
        self.assertIs(outcome.reason, RejectReason.ACTIVE_COMBAT)
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertIsNotNone(read_session(self.player))

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_all_party_sleep_admits_before_its_safety_refusal(self):
        from world.rules.sleep_control import begin_all_party_sleep
        from world.rules.time_skip import SleepRefused

        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        tick_before = get_world_clock().tick
        with self.assertRaises(SleepRefused):
            begin_all_party_sleep(self.player, mode="duration", seconds=600)
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertIsNotNone(read_session(self.player))


class ClockSourceAdmissionTests(_ContactBase):
    """The registered source persists; the owning action drains continuation."""

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_source_admits_at_the_endpoint_and_returns_an_event(self):
        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        clock = get_world_clock()
        start = int(clock.tick)
        events = clock.advance(
            60, AdvanceSource.SKIP, (self.player,), mental=plan_for((self.player,))
        )
        contact_events = [event for event in events if event.kind == CONTACT_EVENT]
        self.assertTrue(contact_events)
        self.assertEqual(int(contact_events[0].due_tick), start + 60)
        record = read_session(self.player)
        self.assertIsNotNone(record)
        self.assertEqual(record.started_tick, start + 60)
        # The source never advances the clock for enemy rounds.
        self.assertEqual(int(clock.tick), start + 60)
        continue_admitted_contacts(self.player, events)
        self.assertEqual(int(clock.tick), start + 60)

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_transit_is_not_contact(self):
        from world.rules.movement_settlement import TraversalScope, traversal_scope

        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        scope = TraversalScope(
            member_ids=(int(self.player.pk),),
            source=LocationRef.room(int(self.origin.pk)),
            destination=LocationRef.room(int(self.destination.pk)),
            departure_tick=0,
            arrival_tick=60,
        )
        with traversal_scope(scope):
            self.assertIsNone(evaluate_field_contact(self.player, tick=30))


class ProtectionTests(_ContactBase):
    """The active cell is protected; re-co-location creates a fresh encounter."""

    def _enter_wilderness_player(self):
        player = _player("mapped contact player")
        self.assertTrue(
            enter_wilderness(player, coordinates=_PROBE, name=WILDERNESS_NAME)
        )
        player.traits.hp.base = 5000
        player.traits.hp.current = 5000
        _write(player, 360000, SleepPosture.AWAKE)
        return player

    @covers_requirement(
        "hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat"
    )
    def test_active_session_protects_the_cell_and_history_blocks_catch_up(self):
        player = self._enter_wilderness_player()
        room = player.location
        enemy = self._enemy("mapped contact enemy", _CONTACT)
        enemy.location = room
        room.contents_cache.add(enemy)
        tick = int(get_world_clock().tick)
        result = admit_field_contact_at(player, source_id=SOURCE_MOVEMENT, tick=tick)
        self.assertIsNotNone(result)
        self.assertIn(_PROBE, regional_population.protected_cells(
            self.wilderness, at_tick=tick
        ))
        # A real terminal settlement closes the historical interval.
        forfeit(player)
        self.assertIsNone(read_session(player))
        self.assertIn(_PROBE, regional_population.protected_cells(
            self.wilderness, at_tick=tick
        ))
        # Re-co-location after the closed encounter admits a fresh session:
        # no immunity and no reused session identity.
        fresh = self._enter_wilderness_player()
        fresh.location = room
        room.contents_cache.add(fresh)
        fresh_enemy = self._enemy("fresh mapped contact enemy", _CONTACT)
        fresh_enemy.location = room
        room.contents_cache.add(fresh_enemy)
        again = admit_field_contact_at(
            fresh, source_id=SOURCE_MOVEMENT, tick=tick + 600
        )
        self.assertIsNotNone(again)
        self.assertNotEqual(
            read_session(fresh).session_id, result["session"]
        )


class FaultRestorationTests(_ContactBase):
    """A late admission failure restores receipt, physiology and session."""

    def test_session_write_failure_restores_the_interrupted_receipt(self):
        _write(self.player, 100000, SleepPosture.AWAKE)
        begin_sleep(self.player, mode="duration", seconds=600, allow_continue=False)
        receipt_before = read_sleep_receipt(self.player)
        state_before = read_optional_fatigue_state(self.player)
        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        tick = int(get_world_clock().tick) + 60
        with patch(
            "world.rules.combat_session.lifecycle._persist",
            side_effect=RuntimeError("injected session write failure"),
        ), patch("world.rules.field_contact.log_error") as logged:
            with self.assertRaises(RuntimeError):
                admit_field_contact_at(
                    self.player, source_id=SOURCE_MOVEMENT, tick=tick
                )
        self.assertIsNone(read_session(self.player))
        self.assertEqual(read_optional_fatigue_state(self.player), state_before)
        self.assertEqual(read_sleep_receipt(self.player), receipt_before)
        events = [call.args[0] for call in logged.call_args_list if call.args]
        self.assertIn("field_contact_failed", events)

    def test_interrupt_owner_is_a_no_op_without_a_voluntary_receipt(self):
        interrupt_sleep_for_contact(
            self.player, tick=10, operation_id="t:noop"
        )
        self.assertIsNone(read_sleep_receipt(self.player))

    def test_a_continuation_failure_rolls_back_the_whole_encounter(self):
        self._enemy("A", _CONTACT)
        self.player.location = self.destination
        _write(self.player, 50000, SleepPosture.FORCED)
        state_before = read_optional_fatigue_state(self.player)
        tick = int(get_world_clock().tick) + 60
        with patch(
            "world.rules.combat_session.rounds.continue_incapacitated_hostile_rounds",
            side_effect=RuntimeError("injected continuation failure"),
        ), patch("world.rules.field_contact.log_error") as logged:
            with self.assertRaises(RuntimeError):
                admit_field_contact_at(
                    self.player, source_id=SOURCE_MOVEMENT, tick=tick
                )
        self.assertIsNone(read_session(self.player))
        self.assertEqual(read_optional_fatigue_state(self.player), state_before)
        events = [call.args[0] for call in logged.call_args_list if call.args]
        self.assertEqual(events.count("field_contact_failed"), 1)
