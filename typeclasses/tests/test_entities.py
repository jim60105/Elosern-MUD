"""Integration tests for the living-entity hierarchy."""

from tools.spec_traceability import covers_requirement

from evennia.utils import lazy_property
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from evennia.contrib.rpg.buffs import BuffHandler

from typeclasses.characters import PlayerCharacter
from typeclasses.entities import LivingEntity
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.objects import ObjectParent
from world.rules.affinity import RelationHandler
from world.rules.persona import PersonaStore
from world.skills.equipment import EquipmentHandler
from world.skills.handler import SkillHandler
from world.rules.sexual_state import SexualState
from world.tests.synthetic_data import (
    SYNTH_MONSTER_TIERS,
    SYNTH_RACES,
    SYNTH_SUBRACES,
    synthetic_registries,
)


class LivingEntityTests(EvenniaTestCase):
    @covers_requirement("living-entity-hierarchy::livingentity-is-the-shared-base-for-characters-npcs-and-monsters", "living-entity-hierarchy::livingentity-non-trait-handlers-are-working-implementations-including-persona")
    def test_every_subclass_instantiates_and_exposes_handlers(self):
        for typeclass in (LivingEntity, PlayerCharacter, NPC, Monster):
            with self.subTest(typeclass=typeclass.__name__):
                entity = create_object(typeclass, key=typeclass.__name__)
                self.assertIsInstance(entity, ObjectParent)
                self.assertIsNotNone(entity.components)
                self.assertIsNotNone(entity.signals)
                self.assertIsNone(entity.race)
                self.assertIsNone(entity.subrace)
                self.assertIsInstance(entity.sexual, SexualState)
                self.assertIsInstance(entity.relations, RelationHandler)
                self.assertIsInstance(entity.persona, PersonaStore)
                self.assertIsInstance(entity.buffs, BuffHandler)
                self.assertIsInstance(entity.equipment, EquipmentHandler)
                self.assertIsInstance(entity.skills, SkillHandler)
                self.assertEqual(entity.traits.all(), [])
                self.assertIsNone(entity.db.disguised_stats)

    @covers_requirement("living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other")
    def test_sex_defaults_to_other_on_a_fresh_entity(self):
        for typeclass in (LivingEntity, PlayerCharacter, NPC, Monster):
            with self.subTest(typeclass=typeclass.__name__):
                entity = create_object(typeclass, key=typeclass.__name__)
                self.assertEqual(entity.sex, "other")

    @covers_requirement("living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other")
    def test_monster_reads_the_default_with_no_specific_override(self):
        monster = create_object(Monster, key="generic monster")
        self.assertEqual(monster.sex, "other")
        self.assertNotIn("sex", Monster.__dict__)

    @covers_requirement("living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other")
    def test_sex_declared_type_is_str_not_optional(self):
        from typing import get_type_hints

        self.assertIs(get_type_hints(LivingEntity)["sex"], str)

    @covers_requirement("persona-store::livingentity-persona-mounts-the-personastore-handler")
    @covers_requirement("living-entity-hierarchy::livingentity-non-trait-handlers-are-working-implementations-including-persona")
    def test_persona_mount_is_a_readonly_handler_over_the_db_record(self):
        entity = create_object(PlayerCharacter, key="persona-less")
        self.assertIsInstance(entity.persona, PersonaStore)
        self.assertIsNone(entity.persona.flatten())
        self.assertIsNone(entity.persona.get("personality"))
        entity.db.persona = {"personality": "Terse.", "habit": None}
        self.assertEqual(entity.persona.get("personality"), "Terse.")
        self.assertEqual(entity.persona.flatten(), "性格：Terse.")
        self.assertIsInstance(LivingEntity.persona, lazy_property)

    @covers_requirement("living-entity-hierarchy::livingentity-carries-race-and-subrace-as-lore-registry-key-attributes")
    def test_representative_entities_resolve_all_eight_traits(self):
        # Kit rows only: the race/subrace keys and the monster tier resolve
        # through patched catalogs (no monster combat rounds run here, so
        # the monster_tiers scope is safe).
        race_key = next(iter(SYNTH_RACES))
        subrace_key = next(iter(SYNTH_SUBRACES))
        tier_key = next(iter(SYNTH_MONSTER_TIERS))
        with synthetic_registries(
            "races", "subraces", "static_tiers", "elements", "monster_tiers"
        ):
            player = create_object(PlayerCharacter, key="kit-holder")
            player.race = race_key
            player.subrace = subrace_key
            player.apply_race_baseline()

            npc = create_object(NPC, key="kit-npc")
            npc.race = race_key
            npc.apply_race_baseline()

            monster = create_object(Monster, key="kit-monster")
            monster.threat_tier = tier_key
            monster.apply_monster_tier()

        expected = {
            "hp",
            "mp",
            "sp",
            "atk_phys",
            "agility",
            "defense",
            "magic_power",
            "guild_merit",
        }
        for entity in (player, npc, monster):
            self.assertEqual(set(entity.traits.all()), expected)
