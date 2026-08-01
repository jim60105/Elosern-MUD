"""Integration tests for the living-entity hierarchy."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from evennia.contrib.rpg.buffs import BuffHandler

from typeclasses.characters import PlayerCharacter
from typeclasses.entities import LivingEntity
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.objects import ObjectParent
from world.skills.equipment import EquipmentHandler
from world.skills.handler import SkillHandler
from world.rules.sexual_state import SexualState


class LivingEntityTests(EvenniaTest):
    @covers_requirement("living-entity-hierarchy::livingentity-is-the-shared-base-for-characters-npcs-and-monsters", "living-entity-hierarchy::non-trait-livingentity-handlers-are-declared-seams-not-implementations")
    def test_every_subclass_instantiates_and_exposes_handlers_and_remaining_seams(self):
        for typeclass in (LivingEntity, PlayerCharacter, NPC, Monster):
            with self.subTest(typeclass=typeclass.__name__):
                entity = create_object(typeclass, key=typeclass.__name__)
                self.assertIsInstance(entity, ObjectParent)
                self.assertIsNotNone(entity.components)
                self.assertIsNotNone(entity.signals)
                self.assertIsNone(entity.race)
                self.assertIsNone(entity.subrace)
                self.assertIsInstance(entity.sexual, SexualState)
                for seam in ("relations", "persona"):
                    self.assertIsNone(getattr(entity, seam))
                self.assertIsInstance(entity.buffs, BuffHandler)
                self.assertIsInstance(entity.equipment, EquipmentHandler)
                self.assertIsInstance(entity.skills, SkillHandler)
                self.assertEqual(entity.traits.all(), [])
                self.assertIsNone(entity.db.disguised_stats)

    @covers_requirement("living-entity-hierarchy::livingentity-carries-race-and-subrace-as-lore-registry-key-attributes")
    def test_representative_entities_resolve_all_eight_traits(self):
        player = create_object(PlayerCharacter, key="elf")
        player.race = "elf"
        player.subrace = "ciaran"
        player.apply_race_baseline()

        npc = create_object(NPC, key="foxkin")
        npc.race = "beastfolk"
        npc.subrace = "foxkin"
        npc.apply_race_baseline()

        monster = create_object(Monster, key="calamity")
        monster.threat_tier = "calamity"
        monster.apply_monster_tier()

        expected = {
            "hp",
            "mp",
            "sp",
            "atk_phys",
            "agility",
            "defense",
            "magic_level",
            "guild_merit",
        }
        for entity in (player, npc, monster):
            self.assertEqual(set(entity.traits.all()), expected)
