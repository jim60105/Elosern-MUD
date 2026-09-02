"""Boundary-event assertions for the migrated rules core (batch 2).

Targets the three delta requirements of ``migrate-rules-maps-observability``:
``clock_advance`` + ``rollback_restore_failed`` (world-clock),
``combat_round_settled`` + ``settlement_done`` (player-combat-session), and
``action_commit`` (action-resolution-pipeline). The delta requirement ids are
deliberately NOT ``covers_requirement``-annotated yet:
``tools.spec_traceability`` indexes only main specs, so active-delta ids would
fail ``check`` with ``unknown-requirement-id``; the annotations land together
with the archive sync (same intentional timing as add-observability-lint-gate
task 6.3).

Boundary events fire through ``transaction.on_commit``, so the tests capture
on-commit callbacks (executed only on real commit) and patch the migrated
module's facade binding; the rollback scenarios assert the callback is
discarded, not that the facade was unreachable.
"""

import unittest
from unittest.mock import Mock, patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import PendingEffect, _commit
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.combat_session import engage, forfeit, submit_player_action
from world.rules.surfaces import restore_attribute_best_effort

from ._combat_session_helpers import _monster, _player
from .combat_fixtures import BattlefieldIsolation


class ClockBoundaryEventTests(EvenniaTest):
    """``clock_advance`` fires once per committed advance, never on rollback."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()

    def test_committed_advance_emits_exactly_one_clock_advance(self):
        clock = get_world_clock()
        before = clock.tick
        with (
            patch("world.rules.clock.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            clock.advance(60, AdvanceSource.SKIP, [self.player])
        info.assert_called_once()
        (event,), kwargs = info.call_args
        self.assertEqual(event, "clock_advance")
        context = kwargs["context"]
        self.assertEqual(context["tick_from"], before)
        self.assertEqual(context["tick_to"], before + 60)
        self.assertEqual(context["scope"], 1)

    def test_rolled_back_advance_emits_no_clock_advance(self):
        clock = get_world_clock()
        with (
            patch("world.rules.clock.log_info") as info,
            patch(
                "world.rules.clock._settle_buffs_and_decay",
                side_effect=RuntimeError("simulated mid-advance failure"),
            ),
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            clock.advance(60, AdvanceSource.SKIP, [self.player])
        events = [call.args[0] for call in info.call_args_list if call.args]
        self.assertNotIn("clock_advance", events)


class RestoreFailureEventTests(unittest.TestCase):
    """Swallowed restore failures become ``rollback_restore_failed`` warns."""

    def test_registry_restore_failure_event_carries_key_obj_and_exc(self):
        from world.rules.clock import _restore_registry_attribute

        obj = Mock()
        obj.attributes.add.side_effect = RuntimeError("injected write failure")
        obj.attributes.reset_cache.side_effect = RuntimeError("cache reset fails")
        with patch("world.rules.clock.log_warn") as warn:
            _restore_registry_attribute(obj, "traits", "traits", (True, {"hp": 1}))
        warn.assert_called_once()
        (event,), kwargs = warn.call_args
        self.assertEqual(event, "rollback_restore_failed")
        self.assertIsInstance(kwargs["exc"], RuntimeError)
        self.assertEqual(kwargs["context"]["key"], "traits")
        self.assertIn("obj", kwargs["context"])
        # The swallow keeps its best-effort degradation.
        obj.attributes.reset_cache.assert_called_once()

    def test_shared_attribute_restore_failure_event_carries_key_and_exc(self):
        obj = Mock()
        obj.attributes.add.side_effect = RuntimeError("injected write failure")
        obj.attributes.reset_cache.side_effect = RuntimeError("cache reset fails")
        with patch("world.rules.surfaces.log_warn") as warn:
            restore_attribute_best_effort(obj, "quest_log", (True, {"q": 1}))
        warn.assert_called_once()
        (event,), kwargs = warn.call_args
        self.assertEqual(event, "rollback_restore_failed")
        self.assertIsInstance(kwargs["exc"], RuntimeError)
        self.assertEqual(kwargs["context"]["key"], "quest_log")


class ActionCommitEventTests(EvenniaTest):
    """``action_commit`` fires once per durable commit, never on rollback."""

    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="commit-event")
        self.entity.race = "human"
        self.entity.apply_race_baseline()

    def test_committed_effects_emit_action_commit_once(self):
        before = int(self.entity.traits.atk_phys.value)
        effects = [
            PendingEffect(
                self.entity,
                "boost",
                frozenset({"traits"}),
                lambda: setattr(self.entity.traits.atk_phys, "value", before + 5),
            ),
        ]
        with (
            patch("world.rules.action.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            _commit(effects, char="commit-event", action="fire_ball")
        info.assert_called_once()
        (event,), kwargs = info.call_args
        self.assertEqual(event, "action_commit")
        self.assertEqual(kwargs["context"]["char"], "commit-event")
        self.assertEqual(kwargs["context"]["action"], "fire_ball")
        self.assertIsInstance(kwargs["context"]["ms"], int)

    def test_rolled_back_commit_emits_no_action_commit(self):
        effects = [
            PendingEffect(
                self.entity,
                "failing",
                frozenset({"traits"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with (
            patch("world.rules.action.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(Exception):
                _commit(effects, char="commit-event", action="fire_ball")
        events = [call.args[0] for call in info.call_args_list if call.args]
        self.assertNotIn("action_commit", events)


class CombatBoundaryEventTests(BattlefieldIsolation, EvenniaTest):
    """``combat_round_settled`` / ``settlement_done`` at committed boundaries."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="event arena")
        self.player = _player("event player")
        self.player.location = self.room
        self.player.traits.hp.base = 500
        self.player.traits.hp.current = 500
        self.monster = _monster("event wolf", hp=500, atk=1)
        self.monster.location = self.room

    def test_committed_ordinary_round_emits_one_round_boundary(self):
        engage(self.player, self.monster)
        with (
            patch("world.rules.combat_session.log_info") as info,
            patch("world.rules.combat.roll_d100", return_value=100),
            self.captureOnCommitCallbacks(execute=True),
        ):
            submit_player_action(self.player, "basic_attack", [self.monster])
        settle_calls = [
            call for call in info.call_args_list if call.args
            and call.args[0] == "combat_round_settled"
        ]
        self.assertEqual(len(settle_calls), 1)
        (_, kwargs), = settle_calls
        context = kwargs["context"]
        self.assertEqual(context["char"], str(self.player.pk))
        self.assertEqual(context["opponent"], int(self.monster.pk))
        self.assertEqual(context["hp_before"], 500)
        self.assertIn("hp_after", context)
        self.assertIn("tick", context)

    def test_rolled_back_round_emits_no_round_boundary(self):
        engage(self.player, self.monster)
        with (
            patch("world.rules.combat_session.log_info") as info,
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session._persist",
                side_effect=RuntimeError("injected persist failure"),
            ),
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            submit_player_action(self.player, "basic_attack", [self.monster])
        events = [call.args[0] for call in info.call_args_list if call.args]
        self.assertNotIn("combat_round_settled", events)

    def test_committed_forfeit_settlement_emits_settlement_done(self):
        engage(self.player, self.monster)
        with (
            patch("world.rules.combat_session.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        settle_calls = [
            call for call in info.call_args_list if call.args
            and call.args[0] == "settlement_done"
        ]
        self.assertEqual(len(settle_calls), 1)
        (_, kwargs), = settle_calls
        context = kwargs["context"]
        self.assertEqual(context["char"], str(self.player.pk))
        self.assertIsInstance(context["ms"], int)
        self.assertEqual(context["notifications"], 0)

    def test_failed_settlement_emits_no_settlement_done(self):
        engage(self.player, self.monster)
        with (
            patch("world.rules.combat_session.log_info") as info,
            patch(
                "world.rules.combat_session._persist",
                side_effect=RuntimeError("injected settlement failure"),
            ),
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        events = [call.args[0] for call in info.call_args_list if call.args]
        self.assertNotIn("settlement_done", events)
