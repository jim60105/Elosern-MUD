from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.imports.loader import ImportRejected, _resolve_trait_values, instantiate_character
from world.imports.tests.helpers import example_record
from world.lore.races import RACE_REGISTRY
from world.rules.traits import race_floor


class LoaderTraitTests(EvenniaTest):
    def test_literal_values_win_and_omissions_use_race_floor(self):
        record = example_record()
        del record["stats"]["guild_merit"]
        values = _resolve_trait_values(record)
        self.assertEqual(values["atk_phys"], 88)
        self.assertEqual(
            values["guild_merit"], race_floor(RACE_REGISTRY["elf"])["guild_merit"]
        )

    def test_loaded_traits_and_raw_seams_are_verbatim(self):
        record = example_record()
        entity = instantiate_character(record)
        self.assertIsInstance(entity, NPC)
        for key, value in record["stats"].items():
            self.assertEqual(getattr(entity.traits, key).value, value)
        self.assertEqual(entity.db.persona, record["persona"])
        self.assertEqual(entity.db.sexual, record["sexual_baseline"])
        self.assertEqual(
            entity.db.skills,
            {"active": record["skills"], "passive": record["passives"]},
        )
        self.assertEqual(entity.db.equipment, record["equipment"])
        self.assertEqual(entity.db.inventory, record["inventory"])
        self.assertEqual(entity.db.disguised_stats, record["disguised_stats"])

    def test_explicit_nonzero_guild_merit_is_stored_literally(self):
        record = example_record()
        record["stats"]["guild_merit"] = 37
        entity = instantiate_character(record)
        self.assertEqual(entity.traits.guild_merit.base, 37)
        self.assertEqual(entity.traits.guild_merit.value, 37)

    def test_explicit_player_typeclass_has_no_account_side_effect(self):
        entity = instantiate_character(example_record(), PlayerCharacter)
        self.assertIsInstance(entity, PlayerCharacter)
        self.assertIsNone(entity.account)

    def test_public_constructor_cannot_bypass_age_gate(self):
        record = example_record()
        record["age"] = 17
        with self.assertRaises(ImportRejected):
            instantiate_character(record)

    def test_warning_only_static_prodigy_is_stored_literally(self):
        record = example_record()
        record["stats"]["atk_phys"] = 1000
        entity = instantiate_character(record)
        self.assertEqual(entity.traits.atk_phys.value, 1000)

    def test_magic_above_race_cap_is_rejected_before_trait_clamping(self):
        record = example_record()
        record["stats"]["magic_level"] = RACE_REGISTRY["elf"].magic_cap + 1
        with self.assertRaises(ImportRejected):
            instantiate_character(record)
