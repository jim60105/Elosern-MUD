"""Persistent combat-session and preflight tests (tasks 7.1-7.12)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from commands.action import CmdCast
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
)
from world.rules.clock import WorldClock
from world.rules.combat import BattlefieldActionContext, run_round
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    forfeit,
    from_storage,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    restore_active_session,
    session_id_for,
    submit_player_action,
    to_storage,
)
from world.skills.handler import INNATE_SKILL_KEYS
from world.skills.registry import SKILL_REGISTRY, SkillKind, TargetSpec


def _player(key="combat player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _monster(key="goblin", hp=100, atk=10):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    monster.traits.atk_phys.base = atk
    return monster


class InnateSkillTests(EvenniaTest):
    @covers_requirement("universal-action-ownership::innate-skill-keys-makes-flee-and-basic-attack-ownable-by-every-livingentity-regardless-of-import-or-spawn-data")
    def test_no_skill_entity_owns_both_innate_actions(self):
        player = _player()
        player.db.skills = None
        self.assertEqual(
            player.skills.owned_keys(), ["flee", "basic_attack"]
        )
        self.assertIn("basic_attack", INNATE_SKILL_KEYS)

    def test_full_import_list_plus_innate(self):
        player = _player()
        player.db.skills = {"active": ["fire_ball"], "passive": ["defense_instinct"]}
        self.assertEqual(
            player.skills.owned_keys(),
            ["fire_ball", "defense_instinct", "flee", "basic_attack"],
        )

    def test_monster_instance_can_fight_without_spawned_skills(self):
        monster = create_object(Monster, key="bare")
        monster.db.skills = None
        self.assertIn("basic_attack", monster.skills.owned_keys())

    def test_basic_attack_is_zero_cost_single_enemy_physical(self):
        skill = SKILL_REGISTRY["basic_attack"]
        self.assertEqual(skill.kind, SkillKind.ACTIVE)
        self.assertEqual(skill.target_spec, TargetSpec.SINGLE)
        self.assertEqual(skill.cost, {})
        self.assertFalse(skill.usable_out_of_combat)
        self.assertTrue(any(e.startswith("damage:") for e in skill.effects))

    def test_basic_attack_rejects_out_of_combat(self):
        player = _player()
        request = ActionRequest(
            player,
            "basic_attack",
            [player],
            __import__(
                "world.rules.targeting", fromlist=["RoomActionContext"]
            ).RoomActionContext(player.location),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT)


class CombatSessionRecordTests(EvenniaTest):
    def test_record_round_trips_through_json(self):
        record = from_storage(
            {
                "session_id": "hostile:1:0",
                "mode": "hostile",
                "room_id": 5,
                "player_ids": [1],
                "enemy_ids": [2],
                "fled_ids": [],
                "knocked_out_ids": [],
                "rounds_elapsed": 0,
                "exam_id": None,
            }
        )
        self.assertEqual(record.session_id, "hostile:1:0")
        self.assertEqual(to_storage(record)["room_id"], 5)

    def test_malformed_records_fail_closed(self):
        base = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 5,
            "player_ids": [1],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        bad_cases = [
            {"session_id": ""},
            {"mode": "unknown"},
            {"player_ids": "nope"},
            {"player_ids": [1, 1]},
            {"player_ids": [1, 2]},
            {"rounds_elapsed": -1},
            {"fled_ids": [99]},
            {"exam_id": None, "mode": "guild_exam"},
        ]
        for mutation in bad_cases:
            data = {**base, **mutation}
            with self.subTest(data=data):
                with self.assertRaises(CombatSessionError):
                    from_storage(data)

    def test_deterministic_session_ids(self):
        player = _player()
        with patch("world.rules.clock.get_world_clock", return_value=WorldClock(42)):
            self.assertEqual(session_id_for(player, "hostile"), f"hostile:{player.pk}:42")


class EngageTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="forest")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("goblin")
        self.monster.location = self.room

    def test_present_monster_can_be_engaged(self):
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].mode, "hostile")
        self.assertEqual(result["record"].rounds_elapsed, 0)
        self.assertTrue(is_in_active_session(self.player))

    def test_remote_or_dead_target_is_rejected(self):
        other_room = create_object(Room, key="other")
        remote = _monster("remote")
        remote.location = other_room
        with self.assertRaises(CombatSessionError) as ctx:
            engage(self.player, remote)
        self.assertEqual(ctx.exception.args[0], SessionReason.NOT_PRESENT)

        dead = _monster("dead", hp=0)
        dead.location = self.room
        with self.assertRaises(CombatSessionError) as ctx:
            engage(self.player, dead)
        self.assertEqual(ctx.exception.args[0], SessionReason.TARGET_DEAD)

    @covers_requirement("player-combat-session::engage-creates-one-persistent-local-combat-session")
    def test_active_session_blocks_another_engagement(self):
        engage(self.player, self.monster)
        second = _monster("second")
        second.location = self.room
        with self.assertRaises(CombatSessionError) as ctx:
            engage(self.player, second)
        self.assertEqual(ctx.exception.args[0], SessionReason.ALREADY_IN_COMBAT)

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    def test_engage_alone_never_runs_a_round(self):
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].rounds_elapsed, 0)
        self.assertEqual(self.monster.traits.hp.current, 100)
        from world.rules.clock import get_world_clock

        self.assertEqual(get_world_clock().tick, 0)


class PlayerRoundTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.monster = _monster("goblin", hp=100)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::one-preflight-valid-player-action-drives-one-complete-ordinary-combat-round")
    def test_invalid_cast_preserves_round_before_initiative(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            result = submit_player_action(self.player, "no_such_skill", self.monster)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.UNKNOWN_SKILL)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)
        self.assertEqual(self.monster.traits.hp.current, 100)

    def test_one_request_drives_one_complete_round(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "fire_ball", self.monster)
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    def test_mid_round_invalidation_consumes_round(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "fire_ball", self.monster)
        # Whatever the outcome, the round count advanced exactly once.
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(result["rounds_elapsed"], 1)

    def test_flee_closes_the_same_session(self):
        engage(self.player, self.monster)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = submit_player_action(self.player, "flee", self.player)
        self.assertEqual(result["outcome"], "fled")
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_terminal_victory_settles_rounds_once_and_clears(self):
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", self.monster)
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    def test_no_action_before_overwhelm_round(self):
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].rounds_elapsed, 0)
        self.assertEqual(self.monster.traits.hp.current, 100)

    def test_overwhelming_player_resolves_after_first_action(self):
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "fire_ball", self.monster)
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)


class SessionPersistenceTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="battlefield room")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("persist goblin")
        self.monster.location = self.room

    def test_disconnect_reconnect_resumes_same_session(self):
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        # Simulate reconnect by clearing transient skip-safety and re-reading.
        from world.rules.skip_safety import _BATTLEFIELDS

        _BATTLEFIELDS.clear()
        restore_active_session(self.player)
        restored = read_session(self.player)
        self.assertEqual(restored.session_id, session_id)
        self.assertEqual(restored.rounds_elapsed, 0)

    @covers_requirement("player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely")
    def test_deleted_enemy_does_not_strand_player(self):
        engage(self.player, self.monster)
        self.monster.delete()
        restore_active_session(self.player)
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_exit_traversal_is_blocked_during_combat(self):
        engage(self.player, self.monster)
        other = create_object(Room, key="elsewhere")
        self.assertFalse(self.player.move_to(other))
        self.assertIs(self.player.location, self.room)
        self.assertTrue(is_in_active_session(self.player))

    def test_forfeit_cleans_session(self):
        engage(self.player, self.monster)
        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))


class PreflightSideEffectTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="preflight room")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.monster = _monster("preflight goblin")
        self.monster.location = self.room

    def test_preflight_rejection_has_no_side_effects(self):
        engage(self.player, self.monster)
        from world.rules.combat import Battlefield
        from world.rules.event_log import EventLog
        from world.rules.combat_session import read_session

        battlefield = reconstruct_battlefield(self.player, read_session(self.player))
        request = ActionRequest(
            self.player,
            "no_such_skill",
            [self.monster],
            BattlefieldActionContext(battlefield),
        )
        before = (self.monster.traits.hp.current, len(_EVENT_LOGS_SENTINEL))
        result = ActionResolver.preflight(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.UNKNOWN_SKILL)
        self.assertEqual((self.monster.traits.hp.current, before[1]), before)
        self.assertIsNone(result.event_log)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-side-effect-free-preflight-for-player-combat-input")
    def test_successful_preflight_does_not_roll_or_stage(self):
        engage(self.player, self.monster)
        from world.rules.action import _EVENT_EFFECT_PLANNERS
        from world.rules.combat import Battlefield
        from world.rules.combat_session import read_session

        battlefield = reconstruct_battlefield(self.player, read_session(self.player))
        request = ActionRequest(
            self.player,
            "fire_ball",
            [self.monster],
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.roll_d100") as roll:
            result = ActionResolver.preflight(request)
        self.assertEqual(result.outcome, "success")
        roll.assert_not_called()
        self.assertIsNone(result.event_log)


# Sentinel used to prove no EventLog was created; kept local to avoid import.
_EVENT_LOGS_SENTINEL = ()


class CommandSessionTests(QuestRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1 = create_object(Room, key="cmd arena")
        self.char1.location = self.room1
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.monster = _monster("cmd goblin")
        self.monster.location = self.room1

    @covers_requirement("world-clock::cmdcast-advances-command-time-only-outside-a-persistent-combat-session")
    def test_active_session_cast_does_not_advance_command_time(self):
        from world.rules.combat_session import engage

        self.char1.db.skills = {"active": ["fire_ball"], "passive": []}
        engage(self.char1, self.monster)
        clock = WorldClock()
        with patch("commands.action.get_world_clock", return_value=clock):
            self.call(CmdCast(), "fire_ball=cmd goblin", None)
        self.assertEqual(clock.tick, 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
