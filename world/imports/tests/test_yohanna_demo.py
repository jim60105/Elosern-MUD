"""Data-contract test: authored Yohanna import card and real protection setup contract

Mechanics are covered independently with synthetic records in narrative tests.
"""

import json
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from world.imports.validate import validate_batch
from world.lore.npc_card import normalize_card
from world.rules.combat_session import read_session
from world.rules.protection_demo import prepare_protection_demo
from world.rules.tests._combat_session_helpers import _player
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from typeclasses.rooms import Room


class AuthoredProtectionDemoContractTests(BattlefieldIsolation, EvenniaTestCase):
    def test_authored_record_is_complete_and_route_reaches_real_combat(self):
        path = Path(__file__).parents[1] / "examples/yohanna_cooper.json"
        report = validate_batch([path])
        self.assertTrue(report.all_valid, str(report))
        self.assertFalse(report.records[0].warnings)
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["key"], "尤漢娜‧庫柏")
        card = normalize_card(record["persona"])
        self.assertIn("Cooper", card.life_story)
        self.assertIn("世代製桶", card.life_story)
        self.assertIn("公會工匠圈", card.identity.public)
        self.assertTrue(all((card.appearance, card.personality, card.speech_style,
                             card.habit, card.social_connection)))
        player = _player("展示旅人")
        player.location = create_object(Room, key="展示入口")
        with patch("world.rules.protection_demo.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                npc, enemy = prepare_protection_demo(player)
        self.assertEqual(npc.key, record["key"])
        self.assertEqual(npc.db.persona["life_story"], card.life_story)
        self.assertEqual(npc.location, player.location)
        self.assertEqual(enemy.location, player.location)
        session = read_session(player)
        self.assertIn(npc.pk, session.player_ids)
        self.assertIn(enemy.pk, session.enemy_ids)
        self.assertEqual(logged.call_args.args[0], "protection_demo_prepared")
        self.assertNotIn(card.life_story, repr(logged.call_args_list))
