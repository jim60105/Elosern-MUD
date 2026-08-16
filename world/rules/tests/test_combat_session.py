"""Persistent combat-session and preflight tests (tasks 7.1-7.12)."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.action import CmdCast
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
)
from world.rules.clock import WorldClock
from world.rules.combat import BattlefieldActionContext, run_round
from world.rules.event_log import render_plain_text
from world.rules.overwhelm import classify_overwhelm
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
from world.rules.party import join_party
from world.skills.handler import INNATE_SKILL_KEYS
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillKind,
    TargetSpec,
)
from .combat_fixtures import BattlefieldIsolation


def _player(key="combat player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    # Human starting magic level (術師 tier) so element-gated spell casts pass.
    player.traits.magic_level.base = 30
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
            player.skills.owned_keys(),
            [
                "flee",
                "basic_attack",
                *sorted(
                    key
                    for key, act in SEXUAL_ACT_REGISTRY.items()
                    if not act.unlock
                ),
            ],
        )
        self.assertIn("basic_attack", INNATE_SKILL_KEYS)

    def test_full_import_list_plus_innate(self):
        player = _player()
        player.db.skills = {"active": ["fire_ball"], "passive": ["defense_instinct"]}
        self.assertEqual(
            player.skills.owned_keys(),
            [
                "fire_ball",
                "defense_instinct",
                "flee",
                "basic_attack",
                *sorted(
                    key
                    for key, act in SEXUAL_ACT_REGISTRY.items()
                    if not act.unlock
                ),
            ],
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


class CombatSessionRecordTests(unittest.TestCase):
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

    def test_settled_tick_is_optional_and_round_trips(self):
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
        # Older durable records without the marker stay valid (default None).
        self.assertIsNone(from_storage(base).settled_tick)
        marked = from_storage({**base, "settled_tick": 42})
        self.assertEqual(marked.settled_tick, 42)
        self.assertEqual(to_storage(marked)["settled_tick"], 42)

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
            {"settled_tick": "six"},
            {"settled_tick": -1},
        ]
        for mutation in bad_cases:
            data = {**base, **mutation}
            with self.subTest(data=data):
                with self.assertRaises(CombatSessionError):
                    from_storage(data)


class CombatSessionIdTests(EvenniaTest):
    def test_deterministic_session_ids(self):
        player = _player()
        with patch("world.rules.clock.get_world_clock", return_value=WorldClock(42)):
            self.assertEqual(session_id_for(player, "hostile"), f"hostile:{player.pk}:42")


class EngageTests(BattlefieldIsolation, EvenniaTest):
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


class PlayerRoundTests(BattlefieldIsolation, EvenniaTest):
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
            result = submit_player_action(self.player, "no_such_skill", [self.monster])
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.UNKNOWN_SKILL)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)
        self.assertEqual(self.monster.traits.hp.current, 100)

    def test_one_request_drives_one_complete_round(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    def test_mid_round_invalidation_consumes_round(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        # Whatever the outcome, the round count advanced exactly once.
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(result["rounds_elapsed"], 1)

    def test_flee_closes_the_same_session(self):
        engage(self.player, self.monster)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = submit_player_action(self.player, "flee", [])
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
            result = submit_player_action(self.player, "fire_ball", [self.monster])
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
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)


class CommandedActionAttributionTests(BattlefieldIsolation, EvenniaTest):
    """overwhelm-log-attribution: the compressed log of a player-overwhelming
    session marks the player's commanded action and keeps every attack's own
    roll line, so a self-commanded basic attack can never be misread as the
    attack that damaged the enemy. Self-targeting damage stays legal: the
    commanded action resolves against the actor."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="attribution arena")
        self.player = _player("attribution player")
        self.player.location = self.room
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.monster = _monster("attribution goblin", hp=100)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    def test_commanded_self_attack_is_marked_and_rolls_stay_attributable(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=44):
            result = submit_player_action(
                self.player, "basic_attack", [self.player]
            )
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(result["rounds_elapsed"], 2)
        # The self-commanded basic attack resolved against the actor (a miss
        # against the player's own agility), leaving the player unharmed.
        self.assertEqual(self.player.traits.hp.current, 2000)
        marker = "你施展了「基本攻擊」。"
        self_miss = (
            f"{self.player.key} 對 {self.player.key} 的攻擊擲出了 44。"
        )
        self.assertIn(marker, "\n".join(render_plain_text(log) for log in result["logs"]))
        commanded_logs = [
            render_plain_text(log)
            for log in result["logs"]
            if log.actor == str(self.player.key)
            and log.skill_key == "basic_attack"
            and str(log.targets[0]) == str(self.player.key)
        ]
        self.assertEqual(len(commanded_logs), 1)
        self.assertTrue(commanded_logs[0].startswith(marker))
        self.assertIn(self_miss, commanded_logs[0])
        # The compression's auto basic attack against the enemy keeps its own
        # roll line immediately before its damage line.
        auto_logs = [
            render_plain_text(log)
            for log in result["logs"]
            if log.actor == str(self.player.key)
            and log.skill_key == "basic_attack"
            and str(log.targets[0]) == str(self.monster.key)
        ]
        self.assertEqual(len(auto_logs), 1)
        auto_lines = auto_logs[0].splitlines()
        self.assertEqual(
            auto_lines[0],
            f"{self.player.key} 對 {self.monster.key} 的攻擊擲出了 44。",
        )
        self.assertTrue(
            auto_lines[1].startswith(
                f"{self.player.key} 對 {self.monster.key} 造成了 "
            )
        )


class ExplicitTargetContractTests(BattlefieldIsolation, EvenniaTest):
    """Regression tests for the explicit-list facade contract (tasks 2.2-2.3)."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="explicit arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["wind_blade", "fire_ball"], "passive": []}
        self.monster_a = _monster("alpha", hp=100)
        self.monster_b = _monster("beta", hp=100)
        self.monster_a.location = self.room
        self.monster_b.location = self.room

    @covers_requirement(
        "player-combat-session::player-combat-submission-accepts-one-explicit-target-value"
    )
    def test_explicit_area_targets_drive_one_round(self):
        engage(self.player, self.monster_a)
        record = read_session(self.player)
        from world.rules.combat_session import to_storage

        record = from_storage(
            {
                **to_storage(record),
                "enemy_ids": [self.monster_a.pk, self.monster_b.pk],
            }
        )
        from world.rules.combat_session import _persist

        _persist(self.player, record)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, "wind_blade", [self.monster_a, self.monster_b]
            )
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)

    def test_approved_shorthand_reaches_ordinary_targeting(self):
        engage(self.player, self.monster_a)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "wind_blade", "all-enemies")
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertLessEqual(self.monster_a.traits.hp.current, 99)
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)

    def test_duplicate_explicit_target_rejects_before_initiative(self):
        engage(self.player, self.monster_a)
        clock = WorldClock()
        with (
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch("world.rules.combat.roll_d100") as roll,
        ):
            result = submit_player_action(
                self.player, "wind_blade", [self.monster_a, self.monster_a]
            )
        roll.assert_not_called()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.TARGET_SPEC_MISMATCH)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)

    def test_remote_participant_rejects_before_initiative(self):
        engage(self.player, self.monster_a)
        other_room = create_object(Room, key="remote")
        remote = _monster("remote", hp=50)
        remote.location = other_room
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            with self.assertRaises(CombatSessionError) as ctx:
                submit_player_action(
                    self.player, "fire_ball", [self.monster_a, remote]
                )
        self.assertEqual(ctx.exception.args[0], SessionReason.NOT_PRESENT)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)

    def test_ally_is_a_valid_target_for_any_skill(self):
        engage(self.player, self.monster_a)
        ally = _player("ally")
        ally.location = self.room
        from world.rules.combat_session import to_storage

        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "player_ids": (self.player.pk, ally.pk),
            }
        )
        from world.rules.combat_session import _persist

        _persist(self.player, record)
        # Freely-targetable (ANY) skills accept an ally as an explicit target;
        # the round resolves and the ally takes the damage instead of the
        # faction check rejecting it (friendly-fire reachability).
        result = submit_player_action(self.player, "fire_ball", [ally])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    def test_old_single_object_input_is_rejected(self):
        engage(self.player, self.monster_a)
        with self.assertRaises(TypeError):
            submit_player_action(self.player, "fire_ball", self.monster_a)

    def test_self_facade_requires_empty_list(self):
        engage(self.player, self.monster_a)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = submit_player_action(self.player, "flee", [])
        self.assertEqual(result["outcome"], "fled")
        self.assertIsNone(self.player.db.active_combat)


class SessionPersistenceTests(BattlefieldIsolation, EvenniaTest):
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


class MalformedSessionNormalizationTests(BattlefieldIsolation, EvenniaTest):
    """fix-malformed-combat-recovery: raw-conversion failures fail closed.

    ``read_session`` normalizes every raw-conversion or strict-parsing
    failure of the persisted payload into ``CombatSessionError`` with the
    ``malformed_session`` reason, and every active-session query or command
    inherits the normalization without leaking a bare ``TypeError`` or
    ``ValueError``.
    """

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="malformed arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("malformed goblin")
        self.monster.location = self.room

    def test_read_session_normalizes_malformed_payloads(self):
        for payload in ({"not": "a valid record"}, 7, "not a dict"):
            self.player.db.active_combat = payload
            with self.assertRaises(CombatSessionError) as raised:
                read_session(self.player)
            self.assertEqual(
                raised.exception.args[0], SessionReason.MALFORMED_SESSION
            )
            self.assertFalse(is_in_active_session(self.player))
            if not isinstance(payload, dict):
                # Raw-conversion failures chain the original conversion error
                # for traceability (fix-malformed-combat-recovery D1).
                self.assertIsInstance(
                    raised.exception.__cause__, (TypeError, ValueError)
                )

    @covers_requirement("player-combat-session::malformed-session-payloads-fail-closed-without-unhandled-conversion-errors")
    def test_engage_and_forfeit_reject_persisted_malformed_payload(self):
        for payload in ({"not": "a valid record"}, 7, "not a dict"):
            self.player.db.active_combat = payload
            with self.assertRaises(CombatSessionError) as raised:
                engage(self.player, self.monster)
            self.assertEqual(
                raised.exception.args[0], SessionReason.MALFORMED_SESSION
            )
            with self.assertRaises(CombatSessionError) as raised:
                forfeit(self.player)
            self.assertEqual(
                raised.exception.args[0], SessionReason.MALFORMED_SESSION
            )


class MalformedSessionRecoveryTests(BattlefieldIsolation, EvenniaTest):
    """fix-malformed-combat-recovery: startup clears unparseable records.

    An unparseable persisted record is cleared with a diagnostic, never
    settled: no world time advances and no participant effects derive from
    the untrusted fields, and the player stays unblocked for ordinary hostile
    engagement. Unrelated settlement failures leave a valid record intact.
    """

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="malformed recovery arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("malformed recovery goblin")
        self.monster.location = self.room

    @covers_requirement("player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely")
    def test_restore_active_session_clears_malformed_record(self):
        engage(self.player, self.monster)
        self.player.db.active_combat = {"not": "a valid record"}
        self.player.ndb.action_context = {"stale": True}
        from world.rules.skip_safety import _BATTLEFIELDS

        self.assertIn(str(self.player.pk), _BATTLEFIELDS)
        clock = WorldClock()
        with (
            patch("world.rules.combat_session.get_world_clock", return_value=clock),
            patch("world.rules.combat_session.settle_combat_result") as settle,
        ):
            restore_active_session(self.player)
        settle.assert_not_called()
        self.assertIsNone(self.player.db.active_combat)
        self.assertIsNone(self.player.ndb.action_context)
        self.assertNotIn(str(self.player.pk), _BATTLEFIELDS)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely")
    def test_startup_clears_malformed_record_and_engage_succeeds(self):
        from world.rules.guild_economy import restore_persisted_sessions

        self.player.db.active_combat = {"not": "a valid record"}
        restore_persisted_sessions()
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].mode, "hostile")
        self.assertIsNotNone(read_session(self.player))

    def test_unrelated_settlement_failure_propagates_with_record_intact(self):
        # A well-formed terminal session whose settlement raises is never
        # re-settled as a defeat: the exception propagates (the startup
        # wrapper logs it) with the durable record intact for exactly one
        # retry and zero re-settlement attempts.
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        self.monster.traits.hp.current = 0
        clock = WorldClock()
        with (
            patch("world.rules.combat_session.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session.settle_combat_result",
                side_effect=RuntimeError("clock write failed"),
            ) as settle,
        ):
            with self.assertRaises(RuntimeError):
                restore_active_session(self.player)
        settle.assert_called_once()
        self.assertEqual(clock.tick, 0)
        self.assertIsNotNone(self.player.db.active_combat)
        self.assertTrue(is_in_active_session(self.player))


class SettlementRecoveryTests(BattlefieldIsolation, EvenniaTest):
    """fix-combat-settlement-recovery: settled marker and atomic round chain."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="recovery arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.monster = _monster("recovery goblin", hp=100)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_restored_marked_session_is_not_settled_twice(self):
        # A terminal hostile session whose settlement committed (marker and
        # clock) but whose clear never ran is settled exactly once by
        # restoration -- never a second time (task 4.1, simulated restart
        # after the clock-commit-before-clear window).
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        record = read_session(self.player)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)
        # Fabricate the durable mid-window state a restart would read: the
        # settlement (marker + clock) committed, the session clear did not.
        from world.rules.combat_session import _persist

        _persist(
            self.player,
            from_storage({**to_storage(record), "settled_tick": clock.tick}),
        )
        restore_active_session(self.player)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_settlement_failure_rolls_back_the_whole_round(self):
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session.settle_combat_result",
                side_effect=RuntimeError("clock write failed"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "fire_ball", [self.monster])
        # Round effects, session metadata, clock tick, and clearing all
        # rolled back together; the session survives for exactly one retry.
        self.assertEqual(self.monster.traits.hp.current, 1)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)
        self.assertIsNotNone(self.player.db.active_combat)
        # The retry runs the round again and settles exactly once.
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    def test_termination_between_effects_and_persist_leaves_no_half_round(self):
        # A process termination between the round effects and the session
        # metadata write leaves either the full round durable or none of it:
        # here the metadata write fails, so the effects roll back with it.
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session._persist",
                side_effect=RuntimeError("terminated"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(self.monster.traits.hp.current, 100)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_three_round_victory_advances_eighteen_seconds_once(self):
        # A hostile session that ends after three completed rounds settles
        # exactly 18 seconds with the combat source and never an extra cast
        # cost per command: rounds 1-2 advance nothing, round 3 settles 3x6s.
        for key, value in {
            "atk_phys": 2,
            "agility": 30,
            "defense": 50,
            "magic_level": 90,
        }.items():
            getattr(self.player.traits, key).base = value
        self.player.traits.hp.base = 500
        self.player.traits.hp.current = 500
        self.monster.traits.hp.base = 405
        self.monster.traits.hp.current = 405
        for key, value in {"atk_phys": 1, "agility": 30, "defense": 0}.items():
            getattr(self.monster.traits, key).base = value
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch("world.rules.monster_behaviour._should_flee", return_value=False),
        ):
            for expected_rounds in (1, 2):
                result = submit_player_action(
                    self.player, "fire_ball", [self.monster]
                )
                self.assertEqual(result["outcome"], "round")
                self.assertEqual(clock.tick, 0)
                self.assertEqual(
                    read_session(self.player).rounds_elapsed, expected_rounds
                )
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(clock.tick, 18)
        self.assertIsNone(self.player.db.active_combat)

    def test_flee_settlement_failure_rolls_back_and_retry_flees(self):
        # The flee terminal source shares the same atomic seam: a failed
        # settlement rolls the flee, the round effects, and the metadata back
        # together, and the retry can flee again and settle exactly once.
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.disengage.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session.settle_combat_result",
                side_effect=RuntimeError("clock write failed"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "flee", [])
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)
        self.assertNotIn(str(self.player.key), read_session(self.player).fled_ids)
        self.assertEqual(self.monster.traits.hp.current, 100)
        with (
            patch("world.rules.disengage.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "flee", [])
        self.assertEqual(result["outcome"], "fled")
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_solo_defeat_settlement_never_revives_the_player(self):
        # A hostile defeat settles the dead player at 0 HP: the roster scope
        # excludes HP-0 members and the actor-alive fallback guard means the
        # settlement never regenerates a corpse (kill semantics), while the
        # world clock still advances the accumulated rounds exactly once.
        self.monster.traits.atk_phys.base = 100
        self.player.traits.hp.base = 100
        self.player.traits.hp.current = 1
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.player.traits.hp.current, 0)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_restored_dead_player_session_never_revives_the_player(self):
        # A terminal hostile session restored with the player dead at 0 HP
        # (the durable pre-settlement crash window) settles through the
        # recovery fallback: the roster is unavailable, but the actor-alive
        # guard keeps the corpse at 0 HP while the clock still advances.
        self.monster.traits.atk_phys.base = 100
        self.player.traits.hp.base = 100
        self.player.traits.hp.current = 1
        engage(self.player, self.monster)
        record = read_session(self.player)
        from world.rules.combat_session import _persist

        _persist(
            self.player,
            from_storage(
                {
                    **to_storage(record),
                    "rounds_elapsed": 1,
                }
            ),
        )
        self.player.traits.hp.current = 0
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            restore_active_session(self.player)
        self.assertEqual(self.player.traits.hp.current, 0)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)


class UpkeepTickCreditTests(BattlefieldIsolation, EvenniaTest):
    """fix-dot-kill-credit: upkeep-settled tick kills commit with the round."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="upkeep tick arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.monster = _monster("upkeep tick goblin", hp=100)
        self.monster.location = self.room
        from world.rules.buffs import _add_buff

        _add_buff(self.monster, "fire_scorch", source_pk=int(self.player.pk))
        self.monster.traits.hp.base = 3
        self.monster.traits.hp.current = 3
        # The 10-second rate tick fires on the first upkeep accumulation
        # (round seconds are 6; pre-arming the tick elapsed makes the first
        # upkeep's 6 seconds cross the interval).
        self.monster.buffs.all["fire_scorch"].tick_elapsed_seconds = 10

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_dot_tick_kill_of_final_foe_commits_victory_and_one_xp(self):
        from world.rules.progression import COMBAT_KILL_XP_TABLE

        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = submit_player_action(self.player, "basic_attack", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        upkeep_logs = [log for log in result["logs"] if log.skill_key == "combat_upkeep"]
        self.assertTrue(upkeep_logs)
        kinds = [entry.kind for log in upkeep_logs for entry in log.entries]
        self.assertIn("damage", kinds)
        self.assertEqual(kinds.count("target_defeated"), 1)
        self.assertEqual(self.player.db.magic_xp, COMBAT_KILL_XP_TABLE["low"])
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_upkeep_settlement_failure_rolls_back_the_whole_round(self):
        from world.rules.action import _EVENT_EFFECT_PLANNERS

        engage(self.player, self.monster)

        def boom(request, log):
            raise RuntimeError("injected upkeep planner failure")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch.dict(_EVENT_EFFECT_PLANNERS, {"boom": boom}),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "basic_attack", [self.monster])
        # Tick HP, round count, and session metadata all rolled back.
        self.assertEqual(self.monster.traits.hp.current, 3)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertIsNotNone(self.player.db.active_combat)
        self.assertIsNone(self.player.db.magic_xp)
        # The retry without the failing planner settles normally.
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = submit_player_action(self.player, "basic_attack", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)


class OverwhelmDirectionTests(BattlefieldIsolation, EvenniaTest):
    """fix-combat-session-roster-and-overwhelm D2: player-direction compression.

    A foe-overwhelming verdict is informational only: each player submission
    drives exactly one ordinary round and the compressed resolver is never
    invoked, so the player keeps full per-round agency (skill choice and
    flee) and no fight is an unavoidable compressed defeat. The
    player-overwhelming path still dispatches the resolver.
    """

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="overwhelm direction arena")
        self.player = _player("direction player")
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        # Foe team overwhelming by the power-ratio rule alone (>= 100x):
        # monster power = (20+50+100) x 3000 = 510000 vs the player's
        # (1+51+1) x 45 = 2385 (~214x), with a ~4.8-round estimate. The
        # player acts first (agility 51 vs 50), survives the monster's
        # roll-100 crit (2.0x = 39 damage: 45 -> 6), and the flee contest
        # (100 + 51 >= 51 + 50) succeeds comfortably on the second round.
        self.monster = _monster("overwhelming goblin", hp=3000, atk=20)
        self.monster.traits.agility.base = 50
        self.monster.traits.defense.base = 100
        self.monster.location = self.room

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    @covers_requirement("player-combat-session::overwhelm-compression-is-player-direction-only")
    @covers_requirement("single-shot-resolution::the-session-never-dispatches-compression-for-the-foe-overwhelming-direction")
    def test_foe_overwhelming_plays_one_round_per_submission_never_compressed(self):
        self.player.traits.hp.base = 45
        self.player.traits.hp.current = 45
        self.player.traits.agility.base = 51
        engage(self.player, self.monster)
        self.assertEqual(
            classify_overwhelm(
                reconstruct_battlefield(self.player, read_session(self.player))
            ),
            "foes",
        )
        clock = WorldClock()
        with (
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=AssertionError(
                    "the compressed resolver must never dispatch for a "
                    "foe-overwhelming verdict"
                ),
            ) as resolver,
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.monster_behaviour._should_flee",
                return_value=False,
            ),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
            resolver.assert_not_called()
            self.assertEqual(result["outcome"], "round")
            self.assertEqual(result["overwhelming_team"], "foes")
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertEqual(clock.tick, 0)
            # The player retains full agency: flee stays available next
            # round, and the foe-overwhelming verdict still never compresses.
            with patch("world.rules.disengage.roll_d100", return_value=100):
                result = submit_player_action(self.player, "flee", [])
            resolver.assert_not_called()
        self.assertEqual(result["outcome"], "fled")
        self.assertEqual(clock.tick, 12)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    @covers_requirement("player-combat-session::overwhelm-compression-is-player-direction-only")
    def test_player_overwhelming_still_dispatches_the_resolver(self):
        weak = _monster("weak goblin", hp=100, atk=10)
        weak.location = self.room
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        engage(self.player, weak)
        self.assertEqual(
            classify_overwhelm(
                reconstruct_battlefield(self.player, read_session(self.player))
            ),
            "party",
        )
        from world.rules.overwhelm import resolve_overwhelm as real_resolve

        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=real_resolve,
            ) as resolver,
            patch("world.rules.clock.get_world_clock", return_value=WorldClock()),
        ):
            result = submit_player_action(self.player, "fire_ball", [weak])
        resolver.assert_called_once()
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)


class PreflightSideEffectTests(BattlefieldIsolation, EvenniaTest):
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

    @covers_requirement("action-resolution-pipeline::preflight-rejects-missing-handler-context-before-any-round-cost")
    def test_missing_effect_context_rejects_without_a_round_or_enemy_action(self):
        self.player.db.skills = {
            "active": ["status_disguise", "dominion_art"],
            "passive": [],
        }
        engage(self.player, self.monster)
        from world.rules.clock import WorldClock
        from world.rules.combat_session import read_session

        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            for skill_key in ("status_disguise", "dominion_art"):
                with self.subTest(skill_key=skill_key):
                    result = submit_player_action(
                        self.player, skill_key, [self.monster]
                    )
                    self.assertEqual(result["outcome"], "rejected")
                    self.assertIs(
                        result["reason"], RejectReason.MISSING_EFFECT_CONTEXT
                    )
                    self.assertEqual(
                        read_session(self.player).rounds_elapsed, 0
                    )
                    self.assertEqual(clock.tick, 0)
                    self.assertEqual(self.monster.traits.hp.current, 100)


# Sentinel used to prove no EventLog was created; kept local to avoid import.
_EVENT_LOGS_SENTINEL = ()


# Shipped ANY-faction AREA damage skill: with free target selection the
# player's own action can hit an ally-side companion in the seam flow.
SEAM_AREA_KEY = "wind_blade"


class RoundSettlementSeamTests(BattlefieldIsolation, EvenniaTest):
    """Cross-cutting regression tests for the shared round seam (task 3.2).

    One session flow exercises every seam phase in order -- a preflight
    rejection (no round), a reverse-overwhelm ordinary round, a friendly-fire
    penalty rollback on a failed terminal settlement, and the terminal
    settlement itself -- so later changes to ``submit_player_action``/
    ``settle_session`` cannot silently break the shared outer transaction.
    """

    def setUp(self):
        super().setUp()
        register_catalog()
        # Shipped ANY area skill; the player needs its 24 MP cost, set below.
        self.room = create_object(Room, key="seam arena")
        self.player = _player("seam player")
        self.player.location = self.room
        # wind_mastery keeps the 術師-tier wind_blade castable at the tuned
        # magic level 2 (the gate is satisfied by direct mastery, damage is
        # unaffected).
        self.player.db.skills = {
            "active": [SEAM_AREA_KEY],
            "passive": ["wind_mastery"],
        }
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.player.traits, key).base = 2
        self.player.traits.hp.base = 390
        self.player.traits.hp.current = 390
        self.companion = create_object(NPC, key="誤傷夥伴", location=self.room)
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.companion.traits, key).base = 2
        self.companion.traits.hp.base = 100
        self.companion.traits.hp.current = 100
        join_party(self.companion, self.player)
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(
            self.companion, self.player, AffinitySource.QUEST_COMPLETION, 10
        )
        # Foe team overwhelming by the power-ratio rule alone (>= 100x):
        # power = stat sum x hp = (200+30+100) x 1300 = 429000 vs player team
        # 3920, with a <= 5-round estimate (198 base damage at a 0.78 hit
        # rate). Monster magic_level is a counter trait capped at 0, so the
        # attack/agility/defense carry the power. The monster's d100 margin
        # (77) stays below the critical threshold: its solid hit lands for
        # 298 damage, flooring the companion but leaving the player standing.
        self.monster = create_object(Monster, key="seam goblin")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")
        for key, value in {
            "atk_phys": 200,
            "agility": 30,
            "defense": 100,
        }.items():
            getattr(self.monster.traits, key).base = value
        self.monster.traits.hp.base = 1300
        self.monster.traits.hp.current = 1300
        self.monster.location = self.room

    def tearDown(self):

        super().tearDown()

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_one_session_flow_covers_all_seam_phases(self):
        engage(self.player, self.monster)
        from world.rules.overwhelm import classify_overwhelm

        # Reverse overwhelm: the FOE team is the overwhelming one, so the
        # player's action runs one ordinary round, never the compression.
        self.assertEqual(
            classify_overwhelm(
                reconstruct_battlefield(self.player, read_session(self.player))
            ),
            "foes",
        )
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            # 1. A preflight rejection consumes no round and no world time.
            result = submit_player_action(
                self.player, "no_such_skill", [self.monster]
            )
            self.assertEqual(result["outcome"], "rejected")
            self.assertEqual(read_session(self.player).rounds_elapsed, 0)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(self.monster.traits.hp.current, 1300)

            # 2. The reverse-overwhelm action drives one ordinary round: the
            #    monster's solid hit floors the companion nonlethally, and
            #    the player's area attack hits both the monster and the
            #    companion, so the friendly-fire penalty applies (-1 per hit)
            #    inside the seam.
            with patch("world.rules.combat.roll_d100", return_value=100):
                result = submit_player_action(
                    self.player,
                    SEAM_AREA_KEY,
                    [self.monster, self.companion],
                )
            self.assertEqual(result["outcome"], "round")
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(
                self.companion.relations.affinity_for(self.player), 9
            )
            self.assertEqual(self.player.traits.hp.current, 390)
            self.assertEqual(self.companion.traits.hp.current, 1)

            # 3. A terminal settlement failure rolls the round back,
            #    including the fresh friendly-fire penalty (party/relations
            #    surfaces are restored with the round). The player's attack
            #    kills the pinned monster, so the settlement step runs and
            #    fails; the monster is held from fleeing so the round stays
            #    on the kill path.
            self.monster.traits.hp.current = 1
            with (
                patch("world.rules.combat.roll_d100", return_value=100),
                patch(
                    "world.rules.combat_session.settle_combat_result",
                    side_effect=RuntimeError("clock write failed"),
                ),
                patch(
                    "world.rules.monster_behaviour._should_flee",
                    return_value=False,
                ),
            ):
                with self.assertRaises(RuntimeError):
                    submit_player_action(
                        self.player,
                        SEAM_AREA_KEY,
                        [self.monster, self.companion],
                    )
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(self.monster.traits.hp.current, 1)
            self.assertEqual(
                self.companion.relations.affinity_for(self.player), 9
            )
            self.assertEqual(self.player.traits.hp.current, 390)

            # 4. A player-defeat round settles exactly once and clears the
            #    session: the monster's solid hit floors the weakened player
            #    on its initiative turn. Both elapsed rounds settle (12 s).
            self.player.traits.hp.current = 40
            with (
                patch("world.rules.combat.roll_d100", return_value=100),
                patch(
                    "world.rules.monster_behaviour._should_flee",
                    return_value=False,
                ),
            ):
                result = submit_player_action(
                    self.player,
                    SEAM_AREA_KEY,
                    [self.monster, self.companion],
                )
            self.assertEqual(result["outcome"], "defeat")
            self.assertEqual(clock.tick, 12)
            self.assertIsNone(self.player.db.active_combat)
            self.assertFalse(is_in_active_session(self.player))


class CommandSessionTests(BattlefieldIsolation, QuestRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
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
        with patch("world.rules.cast_settlement.get_world_clock", return_value=clock):
            self.call(CmdCast(), "fire_ball=cmd goblin", None)
        self.assertEqual(clock.tick, 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
