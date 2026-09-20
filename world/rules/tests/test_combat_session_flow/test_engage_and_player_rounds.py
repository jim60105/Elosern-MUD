"""Slice of ``test_combat_session_flow``: EngageTests and PlayerRoundTests.
"""
from tools.spec_traceability import covers_requirement
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch
from dataclasses import replace
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.action import CmdCast
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.clock import WorldClock
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    engage_group,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
    submit_opening_action,
)
from world.rules.overwhelm import classify_overwhelm
from world.rules.event_log import render_plain_text
from world.rules.party import join_party
from world.rules.combat_session import BASIC_ATTACK_KEY
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill
from .._combat_session_helpers import (
    BattlefieldIsolation,
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from ..combat_fixtures import grant_lineage


from ._support import (
    _T_CAST,
    _open_scope,
)


class EngageTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        _open_scope(self)
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


class PlayerRoundTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
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
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    def test_mid_round_invalidation_consumes_round(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
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
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    def test_no_action_before_overwhelm_round(self):
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].rounds_elapsed, 0)
        self.assertEqual(self.monster.traits.hp.current, 100)

    @covers_requirement("player-combat-session::one-submission-inside-an-active-session-is-one-ordinary-round-by-default-and-structurally")
    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    def test_overwhelming_player_resolves_after_first_action(self):
        # combat-session-opening-dispatch: an in-session submission under a
        # player-overwhelming verdict resolves exactly one ordinary round and
        # never dispatches the compressed resolver. The synthetic cast kills the
        # weak monster inside that single round, so the session still settles
        # as a victory -- but through one round, not compression.
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        engage(self.player, self.monster)
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.rounds.resolve_overwhelm",
                side_effect=AssertionError(
                    "an in-session submission must never dispatch compression"
                ),
            ) as resolver,
        ):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
        resolver.assert_not_called()
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertIsNone(self.player.db.active_combat)
