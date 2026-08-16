"""Tests for subclass-specific declared seams."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC


class SubclassTests(EvenniaTestCase):
    @covers_requirement("living-entity-hierarchy::playercharacter-npc-and-monster-subclass-livingentity-with-their-documented-extra-fields", "living-entity-hierarchy::quest-logs-dialogue-memory-loot-tables-and-behaviour-trees-are-not-built")
    def test_player_fields_have_safe_defaults(self):
        first = create_object(PlayerCharacter, key="first")
        second = create_object(PlayerCharacter, key="second")
        self.assertIsNone(first.guild_rank)
        self.assertEqual(first.quest_log, [])
        self.assertEqual(first.wallet, 0)
        self.assertIsNone(first.age)
        self.assertIsNone(first.apparent_age)
        self.assertFalse(first.creation_pending)
        first.quest_log.append("quest")
        self.assertEqual(second.quest_log, [])

    @covers_requirement("living-entity-hierarchy::playercharacter-npc-and-monster-subclass-livingentity-with-their-documented-extra-fields", "living-entity-hierarchy::quest-logs-dialogue-memory-loot-tables-and-behaviour-trees-are-not-built")
    def test_npc_fields_are_declared_only(self):
        npc = create_object(NPC, key="npc")
        self.assertIsNone(npc.dialogue_memory)
        self.assertIsNone(npc.schedule)

    @covers_requirement("living-entity-hierarchy::playercharacter-npc-and-monster-subclass-livingentity-with-their-documented-extra-fields", "living-entity-hierarchy::quest-logs-dialogue-memory-loot-tables-and-behaviour-trees-are-not-built")
    def test_monster_fields_are_declared_and_tier_is_required_for_population(self):
        monster = create_object(Monster, key="monster")
        self.assertIsNone(monster.threat_tier)
        self.assertEqual(monster.loot_table, [])
        self.assertIsNone(monster.behaviour_tree)
        with self.assertRaisesRegex(ValueError, "threat_tier"):
            monster.apply_monster_tier()
