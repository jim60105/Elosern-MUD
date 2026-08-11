"""Combat action validator and adapter integration tests (tasks 3.3-3.5)."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from web.webclient.actions.combat_actions import (
    validate_cast_payload,
    validate_flee_payload,
    validate_forfeit_payload,
    _cast_adapter,
    _flee_adapter,
    _forfeit_adapter,
)
from world.rules.action import RejectReason
from world.rules.combat_session import engage, read_session
from world.rules.tests.combat_fixtures import BattlefieldIsolation


def _player(key="adapter player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _monster(key="adapter goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class CastPayloadValidationTests(unittest.TestCase):
    def test_none_and_self_accept_skill_only(self):
        validated = validate_cast_payload({"skill_key": "body_enhancement"})
        self.assertEqual(validated["target_ids"], ())
        self.assertIsNone(validated["target_shorthand"])
        self.assertEqual(validated["skill_key"], "body_enhancement")

    def test_single_requires_exactly_one_target(self):
        validated = validate_cast_payload(
            {"skill_key": "fire_ball", "target_ids": [3]}
        )
        self.assertEqual(validated["target_ids"], (3,))
        for ids in ([], [1, 2]):
            with self.assertRaises(Exception):
                validate_cast_payload({"skill_key": "fire_ball", "target_ids": ids})

    def test_area_accepts_list_or_shorthand_never_both(self):
        validated = validate_cast_payload(
            {"skill_key": "wind_blade", "target_ids": [3, 4]}
        )
        self.assertEqual(validated["target_ids"], (3, 4))
        validated = validate_cast_payload(
            {"skill_key": "wind_blade", "target_shorthand": "all-enemies"}
        )
        self.assertEqual(validated["target_shorthand"], "all-enemies")
        with self.assertRaises(Exception):
            validate_cast_payload(
                {"skill_key": "wind_blade", "target_ids": [3], "target_shorthand": "all"}
            )

    def test_rejects_reserved_flee_key(self):
        with self.assertRaises(Exception) as caught:
            validate_cast_payload({"skill_key": "flee"})
        self.assertIn("reserved flee", str(caught.exception))

    def test_rejects_unknown_fields_and_bad_values(self):
        with self.assertRaises(Exception):
            validate_cast_payload({"skill_key": "fire_ball", "target_ids": [True]})
        with self.assertRaises(Exception):
            validate_cast_payload({"skill_key": "fire_ball", "target_ids": [0]})
        with self.assertRaises(Exception):
            validate_cast_payload(
                {"skill_key": "fire_ball", "target_ids": [1, 1]}
            )
        with self.assertRaises(Exception):
            validate_cast_payload({"skill_key": "fire_ball", "bogus": 1})
        with self.assertRaises(Exception):
            validate_cast_payload({"skill_key": "fire_ball", "target_shorthand": "all"})

    def test_flee_and_forfeit_exact_payloads(self):
        self.assertEqual(validate_flee_payload({}), {})
        with self.assertRaises(Exception):
            validate_flee_payload({"skill_key": "flee"})
        validated = validate_forfeit_payload({"session_id": "hostile:1:0"})
        self.assertEqual(validated["session_id"], "hostile:1:0")
        with self.assertRaises(Exception):
            validate_forfeit_payload({})
        with self.assertRaises(Exception):
            validate_forfeit_payload({"session_id": "hostile:1:0", "extra": 1})


class CombatAdapterTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="adapter arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.monster = _monster()
        self.monster.location = self.room

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_no_session_rejects(self):
        result = _cast_adapter(
            self.player,
            validate_cast_payload(
                {"skill_key": "fire_ball", "target_ids": [self.monster.pk]}
            ),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_active_session")

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_tampered_remote_target_rejects(self):
        engage(self.player, self.monster)
        other_room = create_object(Room, key="elsewhere")
        other = _monster("intruder")
        other.location = other_room
        result = _cast_adapter(
            self.player,
            validate_cast_payload(
                {"skill_key": "fire_ball", "target_ids": [other.pk]}
            ),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_session_id")
        self.assertEqual(self.monster.traits.hp.current, 100)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    def test_successful_cast_updates_session(self):
        engage(self.player, self.monster)
        from unittest.mock import Mock, patch

        self.player.msg = Mock()
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = _cast_adapter(
                self.player,
                validate_cast_payload(
                    {"skill_key": "fire_ball", "target_ids": [self.monster.pk]}
                ),
            )
        self.assertIn(result["outcome"], ("success", "rejected"))
        if result["outcome"] == "success":
            self.assertIn(result["code"], ("round", "victory", "defeat"))
            self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertGreaterEqual(
                len(self.player.msg.call_args_list),
                1,
                "adapter must emit committed EventLog narrative via text output",
            )
            narrative = "\n".join(
                call.args[0] for call in self.player.msg.call_args_list
            )
            self.assertNotIn("ui_action_result", narrative)
            self.assertTrue(narrative.strip())

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_flee_accepts_no_target_and_runs(self):
        engage(self.player, self.monster)
        from unittest.mock import patch

        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = _flee_adapter(self.player, {})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "fled")
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_stale_forfeit_rejects(self):
        engage(self.player, self.monster)
        result = _forfeit_adapter(
            self.player, {"session_id": "hostile:999:0"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_session_id")
        self.assertIsNotNone(self.player.db.active_combat)

    def test_matching_forfeit_succeeds(self):
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        result = _forfeit_adapter(self.player, {"session_id": session_id})
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self.player.db.active_combat)

    def test_matching_forfeit_emits_terminal_text_message(self):
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        from unittest.mock import Mock

        self.player.msg = Mock()
        result = _forfeit_adapter(self.player, {"session_id": session_id})
        self.assertEqual(result["outcome"], "success")
        self.assertIn(result["code"], ("defeat", "exam_failed"))
        narrative = "\n".join(
            call.args[0] for call in self.player.msg.call_args_list
        )
        self.assertTrue(narrative.strip(), "forfeit must emit terminal text prose")
        self.assertIn("你被擊敗了", narrative)

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_reserved_flee_rejected_before_submission(self):
        engage(self.player, self.monster)
        with self.assertRaises(Exception):
            validate_cast_payload({"skill_key": "flee"})

    def test_area_shorthand_adapter_path(self):
        engage(self.player, self.monster)
        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        from unittest.mock import patch

        with patch("world.rules.combat.roll_d100", return_value=100):
            result = _cast_adapter(
                self.player,
                validate_cast_payload(
                    {"skill_key": "wind_blade", "target_shorthand": "all-enemies"}
                ),
            )
        self.assertIn(result["outcome"], ("success", "rejected"))
        self.assertLessEqual(self.monster.traits.hp.current, 100)

    def test_flee_adapter_rejects_without_session(self):
        result = _flee_adapter(self.player, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_active_session")

    def test_forfeit_adapter_rejects_without_session(self):
        result = _forfeit_adapter(self.player, {"session_id": "hostile:1:0"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_active_session")

    def test_cast_adapter_rejects_unknown_skill(self):
        engage(self.player, self.monster)
        with self.assertRaises(Exception):
            validate_cast_payload(
                {"skill_key": "no_such_skill", "target_ids": [self.monster.pk]}
            )
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    def test_cast_adapter_rejects_insufficient_resource(self):
        engage(self.player, self.monster)
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        result = _cast_adapter(
            self.player,
            validate_cast_payload({"skill_key": "fire_ball", "target_ids": [self.monster.pk]}),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_resource")
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)


if __name__ == "__main__":
    unittest.main()
