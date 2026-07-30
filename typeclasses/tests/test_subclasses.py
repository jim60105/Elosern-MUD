"""Tests for subclass-specific declared seams."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC


class SubclassTests(EvenniaTest):
    def test_player_fields_have_safe_defaults(self):
        first = create_object(PlayerCharacter, key="first")
        second = create_object(PlayerCharacter, key="second")
        self.assertIsNone(first.guild_rank)
        self.assertEqual(first.quest_log, [])
        self.assertEqual(first.wallet, 0)
        first.quest_log.append("quest")
        self.assertEqual(second.quest_log, [])

    def test_npc_fields_are_declared_only(self):
        npc = create_object(NPC, key="npc")
        self.assertIsNone(npc.dialogue_memory)
        self.assertIsNone(npc.schedule)

    def test_monster_fields_are_declared_and_tier_is_required_for_population(self):
        monster = create_object(Monster, key="monster")
        self.assertIsNone(monster.threat_tier)
        self.assertEqual(monster.loot_table, [])
        self.assertIsNone(monster.behaviour_tree)
        with self.assertRaisesRegex(ValueError, "threat_tier"):
            monster.apply_monster_tier()

