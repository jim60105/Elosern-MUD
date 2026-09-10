"""Field-combat-initiation tests: exploration casts become combat's opening move.

Covers the ``field-combat-initiation`` capability (design §§4-9): target
classification, the two-part routing rule, candidate-battlefield validation
under a combat context, AREA room expansion, the single failure boundary
spanning ``engage_group()`` and ``submit_opening_action()`` (including the
idmapper-cache and skip-safety restorations a database rollback cannot
reach), the world-time ownership handoff, the boundary event, and the cast
command's routing.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.objects.objects import DefaultObject
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from commands.action import CmdCast
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import RejectReason
from world.rules.clock import read_world_clock
from world.rules.combat import Relation
from world.rules.combat_initiation import (
    _candidate_record,
    field_combat_target,
    initiate_field_combat,
)
from world.rules.combat_session import (
    _context_for,
    engage_group,
    read_session,
    reconstruct_battlefield,
)
from world.rules.dialogue import open_or_refresh_dialogue
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.party import join_party
from world.rules.player_messages import rejection_message
from world.rules.skip_safety import _BATTLEFIELDS
from world.skills.registry import SKILL_REGISTRY

from ._combat_session_helpers import SEAM_AREA_KEY, _monster, _player
from .combat_fixtures import BattlefieldIsolation, grant_lineage

_MONSTER_TARGET = (
    "field-combat-initiation::a-skill-aimed-at-a-co-located-hostile-monster-from"
    "-exploration-always-initiates-combat"
)
_DAMAGE_ROUTER = (
    "field-combat-initiation::a-damaging-skill-aimed-at-anything-other-than-a"
    "-co-located-hostile-monster-is-rejected-at-the-entry"
)
_AVAILABILITY = (
    "field-combat-initiation::the-skill-s-out-of-combat-availability-is-checked"
    "-explicitly-before-anything-else"
)
_CANDIDATE = (
    "field-combat-initiation::validation-runs-against-a-candidate-battlefield-that"
    "-is-never-persisted-under-a-combat-context"
)
_LINEUP = (
    "field-combat-initiation::a-single-skill-opens-against-the-named-monster-and-an"
    "-area-skill-opens-against-every-living-hostile-monster-in-the-room"
)
_BOUNDARY = (
    "field-combat-initiation::session-creation-and-the-opening-action-share-one"
    "-failure-boundary"
)
_TIME = (
    "field-combat-initiation::the-opening-cast-charges-combat-time-never-command-time"
)
_EVENT = "field-combat-initiation::a-committed-field-initiation-emits-one-boundary-event"
_COMMAND = (
    "field-combat-initiation::the-command-routes-an-exploration-cast-by-target-and"
    "-its-documentation-says-so"
)


def _dominant_player(key):
    """A player that dominates floor-tier monsters (compression fixture)."""
    player = _player(key)
    for trait_key in ("atk_phys", "agility", "defense", "magic_power"):
        getattr(player.traits, trait_key).base = 200
    player.traits.hp.base = 2000
    player.traits.hp.current = 2000
    return player


class FieldCombatTargetTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="classification field")
        self.player = _player("classifier")
        self.player.location = self.room

    @covers_requirement(_MONSTER_TARGET)
    def test_positive_case_is_the_living_co_located_monster(self):
        monster = _monster("classified wolf")
        monster.location = self.room
        self.assertIs(field_combat_target(self.player, monster), monster)

    @covers_requirement(_MONSTER_TARGET)
    def test_every_negative_case_returns_none(self):
        npc = create_object(NPC, key="classified npc", location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        companion = create_object(NPC, key="classified companion", location=self.room)
        companion.race = "human"
        companion.apply_race_baseline()
        join_party(companion, self.player)
        object_thing = create_object(DefaultObject, key="classified rock", location=self.room)
        remote_room = create_object(Room, key="classification elsewhere")
        remote = _monster("remote wolf")
        remote.location = remote_room
        dead = _monster("dead wolf", hp=1)
        dead.location = self.room
        dead.traits.hp.current = 0
        stranger = _monster("stray wolf")
        stranger.location = remote_room
        cases = [
            ("npc", npc),
            ("companion", companion),
            ("self", self.player),
            ("object", object_thing),
            ("other-room monster", remote),
            ("zero-hp monster", dead),
            ("None", None),
        ]
        for label, candidate in cases:
            with self.subTest(case=label):
                self.assertIsNone(field_combat_target(self.player, candidate))
        self.assertIsNotNone(stranger)

    @covers_requirement(_MONSTER_TARGET)
    def test_two_unlocated_entities_are_not_co_located(self):
        player = _player("nowhere hunter")
        monster = _monster("nowhere wolf")
        self.assertIsNone(player.location)
        self.assertIsNone(monster.location)
        self.assertIsNone(field_combat_target(player, monster))


class InitiationRoutingTests(
    BattlefieldIsolation, QuestRegistryIsolation, EvenniaTestCase
):
    def setUp(self):
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="initiation field")
        self.player = _player("field opener")
        self.player.location = self.room
        for trait_key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, trait_key).base = 10

    def tearDown(self):
        # Openings that continue the fight leave a live session; release it
        # so each test engages a fresh battlefield.
        from world.rules.combat_session import clear_session

        clear_session(self.player)
        super().tearDown()

    @covers_requirement(_MONSTER_TARGET)
    def test_damage_skill_opens_and_resolves_as_the_opening_action(self):
        monster = _monster("opening wolf", hp=2000, atk=1)
        monster.location = self.room
        hp_before = monster.traits.hp.current
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = initiate_field_combat(self.player, "basic_attack", monster)
        self.assertEqual(result["outcome"], "round")
        self.assertIsNotNone(read_session(self.player))
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertTrue(
            any(
                entry.kind == "damage"
                for log in result["logs"]
                for entry in log.entries
            )
        )
        self.assertLess(int(monster.traits.hp.current), hp_before)

    @covers_requirement(_MONSTER_TARGET)
    def test_non_damaging_skills_open_and_run_exactly_one_round(self):
        grant_lineage(self.player, ["water_shield", "heal", "purify", "weaken"])
        for skill_key in ("water_shield", "heal", "purify", "weaken", "combat_tease"):
            with self.subTest(skill=skill_key):
                monster = _monster(f"target {skill_key}", hp=2000, atk=1)
                monster.location = self.room
                with patch("world.rules.combat.roll_d100", return_value=50), patch(
                    "world.rules.action.roll_d100", return_value=1
                ):
                    result = initiate_field_combat(self.player, skill_key, monster)
                self.assertEqual(result["outcome"], "round", skill_key)
                self.assertEqual(result["rounds_elapsed"], 1, skill_key)
                self.assertIsNotNone(read_session(self.player), skill_key)
                # A non-damaging opening never settles in one shot.
                self.assertEqual(read_session(self.player).rounds_elapsed, 1, skill_key)
                # Release the session so the next subTest can engage again.
                from world.rules.combat_session import clear_session

                clear_session(self.player)

    @covers_requirement(_MONSTER_TARGET)
    def test_healing_a_monster_starts_the_fight_and_heals_it(self):
        grant_lineage(self.player, ["heal"])
        monster = _monster("wounded wolf", hp=2000, atk=1)
        monster.location = self.room
        monster.traits.hp.current = 100
        # The wounded monster sits at its archetype's flee boundary, so pin
        # the flee predicate: this scenario is about the fight opening and
        # the heal landing, not about a random escape roll ending it.
        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            patch("world.rules.monster_behaviour._should_flee", return_value=False),
        ):
            result = initiate_field_combat(self.player, "heal", monster)
        self.assertEqual(result["outcome"], "round")
        self.assertIsNotNone(read_session(self.player))
        self.assertGreater(int(monster.traits.hp.current), 100)

    @covers_requirement(_DAMAGE_ROUTER)
    def test_the_entry_enforces_its_own_target_contract_even_for_area_skills(self):
        # An AREA skill picks its line-up from the room, so a direct caller
        # aiming at a non-target must not be able to open the room fight.
        grant_lineage(self.player, [SEAM_AREA_KEY])
        wolf = _monster("contract wolf", hp=2000, atk=1)
        wolf.location = self.room
        npc = create_object(NPC, key="contract npc", location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        far_room = create_object(Room, key="contract elsewhere")
        far_monster = _monster("contract far wolf", hp=2000, atk=1)
        far_monster.location = far_room
        mp_before = self.player.traits.mp.value
        for label, bad_target in (
            ("self", self.player),
            ("npc", npc),
            ("remote monster", far_monster),
            ("None", None),
        ):
            with self.subTest(target=label):
                result = initiate_field_combat(
                    self.player, SEAM_AREA_KEY, bad_target
                )
                self.assertEqual(result["outcome"], "rejected", label)
                self.assertEqual(
                    result["reason"],
                    RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET,
                    label,
                )
                self.assertIsNone(read_session(self.player), label)
        self.assertEqual(self.player.traits.mp.value, mp_before)
        self.assertIsNone(read_session(self.player))

    @covers_requirement(_AVAILABILITY)
    def test_flee_cannot_open_a_fight(self):
        monster = _monster("flee wolf", hp=2000, atk=1)
        monster.location = self.room
        with patch("world.rules.combat_initiation.reconstruct_battlefield") as rebuild:
            result = initiate_field_combat(self.player, FLEE_SKILL_KEY, monster)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT)
        rebuild.assert_not_called()
        self.assertIsNone(read_session(self.player))

    @covers_requirement(_AVAILABILITY)
    def test_unusable_skill_is_refused_before_the_candidate_is_built(self):
        monster = _monster("locked wolf", hp=2000, atk=1)
        monster.location = self.room
        self.addCleanup(SKILL_REGISTRY.pop, "test_locked_skill", None)
        SKILL_REGISTRY["test_locked_skill"] = SKILL_REGISTRY["basic_attack"].__class__(
            key="test_locked_skill",
            label="測試鎖定技能",
            description="僅供測試的戰鬥內限定技能。",
            kind=SKILL_REGISTRY["basic_attack"].kind,
            target_spec=SKILL_REGISTRY["basic_attack"].target_spec,
            cost={},
            usable_out_of_combat=False,
            element=None,
            effects=["damage:physical:physical"],
            category=SKILL_REGISTRY["basic_attack"].category,
        )
        self.player.db.skills = {"active": ["test_locked_skill"], "passive": []}
        with patch("world.rules.combat_initiation.reconstruct_battlefield") as rebuild:
            result = initiate_field_combat(self.player, "test_locked_skill", monster)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT)
        self.assertEqual(result["detail"], "test_locked_skill")
        rebuild.assert_not_called()
        self.assertIsNone(read_session(self.player))


class CandidateValidationTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="candidate field")
        self.player = _player("candidate opener")
        self.player.location = self.room

    @covers_requirement(_CANDIDATE)
    def test_candidate_validation_rejection_touches_nothing(self):
        # Unowned skill: revalidate_submission rejects inside the entry, so
        # the failure lands on the candidate path (not the availability gate).
        monster = _monster("candidate wolf", hp=2000, atk=1)
        monster.location = self.room
        self.player.db.skills = {"active": [], "passive": []}
        mp_before = self.player.traits.mp.value
        with patch.dict(_BATTLEFIELDS, {}, clear=True):
            result = initiate_field_combat(self.player, "fire_ball", monster)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.UNKNOWN_SKILL)
        self.assertIsNone(read_session(self.player))
        self.assertEqual(self.player.traits.mp.value, mp_before)
        singleton = read_world_clock()
        self.assertTrue(singleton is None or singleton.tick == 0)
        self.assertEqual(
            [key for key, field in _BATTLEFIELDS.items() if key == str(self.player.pk)],
            [],
        )

    @covers_requirement(_CANDIDATE)
    def test_candidate_roster_matches_the_persisted_session(self):
        companion = create_object(NPC, key="candidate companion", location=self.room)
        companion.race = "human"
        companion.apply_race_baseline()
        companion.traits.hp.base = 500
        companion.traits.hp.current = 500
        join_party(companion, self.player)
        m1 = _monster("cand m1", hp=2000, atk=1)
        m2 = _monster("cand m2", hp=2000, atk=1)
        m1.location = self.room
        m2.location = self.room
        targets = sorted([m1, m2], key=lambda m: int(m.pk))
        candidate = reconstruct_battlefield(
            self.player, _candidate_record(self.player, targets)
        )
        engaged = engage_group(self.player, targets)
        persisted = reconstruct_battlefield(self.player, engaged["record"])
        self.assertEqual(candidate.roster.keys(), persisted.roster.keys())
        self.assertEqual(candidate.teams, persisted.teams)

    @covers_requirement(_CANDIDATE)
    def test_validation_context_reports_the_room_monster_as_an_enemy(self):
        monster = _monster("faction wolf", hp=2000, atk=1)
        monster.location = self.room
        record = _candidate_record(self.player, [monster])
        battlefield = reconstruct_battlefield(self.player, record)
        context = _context_for(battlefield, record)
        self.assertEqual(
            context.relation_to(self.player, monster), Relation.ENEMY
        )


class LineUpSelectionTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="lineup field")
        self.player = _player("lineup opener")
        self.player.location = self.room

    @covers_requirement(_LINEUP)
    def test_area_opens_against_every_living_room_monster(self):
        grant_lineage(self.player, [SEAM_AREA_KEY])
        monsters = [
            _monster(f"pack {index}", hp=2000, atk=1) for index in range(3)
        ]
        for monster in monsters:
            monster.location = self.room
        dead = _monster("pack dead", hp=1)
        dead.location = self.room
        dead.traits.hp.current = 0
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = initiate_field_combat(
                self.player, SEAM_AREA_KEY, monsters[0]
            )
        self.assertEqual(result["outcome"], "round")
        record = read_session(self.player)
        self.assertEqual(
            set(record.enemy_ids),
            {int(monster.pk) for monster in monsters},
        )
        self.assertNotIn(int(dead.pk), record.enemy_ids)

    @covers_requirement(_LINEUP)
    def test_single_opens_against_only_the_named_monster(self):
        monsters = [
            _monster(f"room {index}", hp=2000, atk=1) for index in range(3)
        ]
        for monster in monsters:
            monster.location = self.room
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = initiate_field_combat(self.player, "basic_attack", monsters[1])
        self.assertEqual(result["outcome"], "round")
        record = read_session(self.player)
        self.assertEqual(record.enemy_ids, (int(monsters[1].pk),))

    @covers_requirement(_LINEUP)
    def test_area_in_a_one_monster_room_takes_the_same_path(self):
        grant_lineage(self.player, [SEAM_AREA_KEY])
        monster = _monster("lone pack wolf", hp=2000, atk=1)
        monster.location = self.room
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = initiate_field_combat(self.player, SEAM_AREA_KEY, monster)
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).enemy_ids, (int(monster.pk),))


class FailureBoundaryTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="failure field")
        self.player = _player("failed opener")
        self.player.location = self.room
        self.monster = _monster("failure wolf", hp=2000, atk=1)
        self.monster.location = self.room

    def _force_opening_failure(self):
        with (
            patch(
                "world.rules.combat_initiation.submit_opening_action",
                side_effect=RuntimeError("injected opening failure"),
            ),
            self.assertRaises(RuntimeError),
            self.captureOnCommitCallbacks(execute=True),
        ):
            initiate_field_combat(self.player, "basic_attack", self.monster)

    @covers_requirement(_BOUNDARY)
    def test_raising_opening_action_leaves_no_trace(self):
        mp_before = self.player.traits.mp.value
        hp_before = self.player.traits.hp.value
        with patch.dict(_BATTLEFIELDS, {}, clear=True):
            self._force_opening_failure()
        self.assertIsNone(read_session(self.player))
        self.assertEqual(
            [
                key
                for key, field in _BATTLEFIELDS.items()
                if field.roster.get(self.player.key) is self.player
            ],
            [],
        )
        self.assertEqual(self.player.traits.mp.value, mp_before)
        self.assertEqual(self.player.traits.hp.value, hp_before)
        singleton = read_world_clock()
        self.assertTrue(singleton is None or singleton.tick == 0)

    @covers_requirement(_BOUNDARY)
    def test_read_session_is_none_in_process_after_the_rollback(self):
        self._force_opening_failure()
        # Same process, no reload: the idmapper cache must have been
        # restored, not left at the engaged value the rollback erased.
        self.assertIsNone(read_session(self.player))

    @covers_requirement(_BOUNDARY)
    def test_dialogue_session_survives_a_rolled_back_initiation(self):
        npc = create_object(NPC, key="dialogue npc", location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        open_or_refresh_dialogue(self.player, npc, "保持著的那句話")
        self._force_opening_failure()
        session = self.player.db.dialogue_session
        self.assertIsNotNone(session)
        self.assertEqual(session["npc_id"], int(npc.pk))

    @covers_requirement(_BOUNDARY)
    def test_committed_initiation_retires_the_dialogue_session(self):
        npc = create_object(NPC, key="retired dialogue npc", location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        open_or_refresh_dialogue(self.player, npc, "即將隨開戰結束的一句話")
        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = initiate_field_combat(self.player, "basic_attack", self.monster)
        self.assertEqual(result["outcome"], "round")
        self.assertIsNone(self.player.db.dialogue_session)


class WorldTimeTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="time field")
        self.player = _dominant_player("timed opener")
        self.player.location = self.room
        grant_lineage(self.player, ["fire_ball"])

    @covers_requirement(_TIME)
    def test_opening_round_charges_no_command_time(self):
        monster = _monster("patient wolf", hp=8000, atk=1)
        monster.location = self.room
        for trait_key in ("atk_phys", "agility"):
            getattr(self.player.traits, trait_key).base = 10
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = initiate_field_combat(self.player, "fire_ball", monster)
        self.assertEqual(result["outcome"], "round")
        # Combat time stays unsettled in the session until the terminal
        # outcome; no AdvanceSource.COMMAND charge was taken for the cast:
        # the singleton never advanced.
        singleton = read_world_clock()
        self.assertTrue(singleton is None or singleton.tick == 0)

    @covers_requirement(_TIME)
    def test_field_initiation_that_ends_the_fight_settles_once(self):
        monster = _monster("doomed wolf", hp=100, atk=10)
        monster.location = self.room
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.combat_session.log_info") as session_info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = initiate_field_combat(self.player, "fire_ball", monster)
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(read_session(self.player))
        settlements = [
            call for call in session_info.call_args_list if call.args
            and call.args[0] == "settlement_done"
        ]
        self.assertEqual(len(settlements), 1)
        singleton = read_world_clock()
        self.assertIsNotNone(singleton)
        self.assertGreater(singleton.tick, 0)


class BoundaryEventTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="event field")

    def _events(self, info):
        return [call for call in info.call_args_list if call.args
                and call.args[0] == "field_combat_initiated"]

    @covers_requirement(_EVENT)
    def test_committed_initiation_logs_one_matching_event(self):
        player = _dominant_player("event opener")
        player.location = self.room
        grant_lineage(player, ["fire_ball"])
        monster = _monster("event wolf", hp=100, atk=10)
        monster.location = self.room
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.combat_initiation.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = initiate_field_combat(player, "fire_ball", monster)
        self.assertEqual(result["outcome"], "victory")
        (event,) = self._events(info)
        (_, kwargs) = event
        context = kwargs["context"]
        self.assertEqual(context["char"], str(player.pk))
        self.assertEqual(context["room"], str(self.room.pk))
        self.assertEqual(context["skill"], "fire_ball")
        self.assertEqual(context["enemy_count"], 1)
        self.assertEqual(context["opening"], "overwhelm")
        self.assertIn("tick", context)

    @covers_requirement(_EVENT)
    def test_ordinary_opening_logs_the_round_dispatch(self):
        player = _player("round opener")
        player.location = self.room
        monster = _monster("durable wolf", hp=2000, atk=1)
        monster.location = self.room
        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            patch("world.rules.combat_initiation.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = initiate_field_combat(player, "basic_attack", monster)
        self.assertEqual(result["outcome"], "round")
        (event,) = self._events(info)
        (_, kwargs) = event
        self.assertEqual(kwargs["context"]["opening"], "round")
        self.assertEqual(kwargs["context"]["enemy_count"], 1)

    @covers_requirement(_EVENT)
    def test_rejected_and_rolled_back_initiations_log_nothing(self):
        player = _player("silent opener")
        player.location = self.room
        monster = _monster("silent wolf", hp=2000, atk=1)
        monster.location = self.room
        with (
            patch("world.rules.combat_initiation.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            rejected = initiate_field_combat(player, FLEE_SKILL_KEY, monster)
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertEqual(self._events(info), [])
        with (
            patch(
                "world.rules.combat_initiation.submit_opening_action",
                side_effect=RuntimeError("injected opening failure"),
            ),
            patch("world.rules.combat_initiation.log_info") as info,
            self.assertRaises(RuntimeError),
            self.captureOnCommitCallbacks(execute=True),
        ):
            initiate_field_combat(player, "basic_attack", monster)
        self.assertEqual(self._events(info), [])


class FieldCombatCommandTests(
    BattlefieldIsolation, QuestRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest
):
    def setUp(self):
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="command field")
        self.char1.location = self.room
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.monster = _monster("command wolf", hp=2000, atk=1)
        self.monster.location = self.room

    @covers_requirement(_COMMAND)
    def test_command_routes_a_monster_targeted_cast_into_combat(self):
        with patch("world.rules.combat.roll_d100", return_value=50):
            self.call(
                CmdCast(),
                "basic_attack=command wolf",
                None,
            )
        self.assertIsNotNone(read_session(self.char1))
        # No AdvanceSource.COMMAND charge: a continuing round charges nothing,
        # and the singleton (created by engagement's session id) never moved.
        clock = read_world_clock()
        self.assertTrue(clock is None or clock.tick == 0)

    @covers_requirement(_DAMAGE_ROUTER)
    def test_damaging_skill_aimed_at_an_npc_is_refused_with_nothing_spent(self):
        npc = create_object(NPC, key="command npc", location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        npc.traits.hp.base = 500
        npc.traits.hp.current = 500
        mp_before = self.char1.traits.mp.value
        self.call(
            CmdCast(),
            "basic_attack=command npc",
            rejection_message(RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET),
        )
        self.assertIsNone(read_session(self.char1))
        self.assertEqual(self.char1.traits.mp.value, mp_before)
        singleton = read_world_clock()
        self.assertTrue(singleton is None or singleton.tick == 0)
        self.assertEqual(int(npc.traits.hp.current), 500)

    @covers_requirement(_DAMAGE_ROUTER)
    def test_resistible_sexual_act_aimed_at_an_npc_is_unchanged(self):
        npc = create_object(NPC, key="teased npc", location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        npc.traits.hp.base = 500
        npc.traits.hp.current = 500
        with (
            patch("world.rules.action.roll_d100", return_value=1),
            patch(
                "world.rules.cast_settlement._scan_out_of_combat_sexual_coercion",
                wraps=__import__(
                    "world.rules.cast_settlement",
                    fromlist=["_scan_out_of_combat_sexual_coercion"],
                )._scan_out_of_combat_sexual_coercion,
            ) as scan,
        ):
            self.call(
                CmdCast(),
                "combat_tease=teased npc",
                None,
            )
        scan.assert_called_once()
        self.assertIsNone(read_session(self.char1))
        # Command time is charged exactly as before this change.
        singleton = read_world_clock()
        self.assertIsNotNone(singleton)
        self.assertGreater(singleton.tick, 0)

    @covers_requirement(_EVENT)
    def test_sexual_act_aimed_at_a_monster_runs_the_in_combat_scan(self):
        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            patch("world.rules.action.roll_d100", return_value=1),
            patch(
                "world.rules.combat_session._scan_sexual_coercion",
                wraps=__import__(
                    "world.rules.combat_session",
                    fromlist=["_scan_sexual_coercion"],
                )._scan_sexual_coercion,
            ) as combat_scan,
            patch(
                "world.rules.cast_settlement._scan_out_of_combat_sexual_coercion",
            ) as out_of_combat_scan,
        ):
            self.call(
                CmdCast(),
                "combat_tease=command wolf",
                None,
            )
        combat_scan.assert_called_once()
        out_of_combat_scan.assert_not_called()
        self.assertIsNotNone(read_session(self.char1))
        singleton = read_world_clock()
        self.assertTrue(singleton is None or singleton.tick == 0)

    @covers_requirement(_COMMAND)
    def test_non_damaging_self_cast_keeps_the_existing_route(self):
        self.char1.db.skills = {"active": ["status_disguise"], "passive": []}
        self.char1.db.disguised_stats = {"atk_phys": 1}
        self.call(CmdCast(), "status_disguise", f"{self.char1.key} 改變了")
        singleton = read_world_clock()
        self.assertIsNotNone(singleton)
        self.assertGreater(singleton.tick, 0)
        self.assertIsNone(read_session(self.char1))
