"""Pure construction and Evennia integration tests for entity traits."""

from tools.spec_traceability import covers_requirement

from evennia.contrib.rpg.traits import CounterTrait, GaugeTrait, StaticTrait
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.races import RACE_REGISTRY
from world.rules.traits import STATIC_KEYS, build_initial_traits


class TraitIntegrationTests(EvenniaTestCase):
    def _entity(self, race_key):
        entity = create_object(PlayerCharacter, key=race_key)
        entity.race = race_key
        entity.apply_race_baseline()
        return entity

    @covers_requirement("entity-trait-scales::guild-merit-starts-at-zero-with-no-upper-bound", "entity-trait-scales::livingentity-mounts-traithandler-with-the-setting-s-eight-key-trait-set")
    def test_all_eight_traits_have_the_required_types_and_properties(self):
        entity = self._entity("human")
        self.assertEqual(set(entity.traits.all()), {
            "hp", "mp", "sp", "atk_phys", "agility", "defense",
            "magic_level", "guild_merit",
        })
        for key in ("hp", "mp", "sp"):
            trait = getattr(entity.traits, key)
            self.assertIsInstance(trait, GaugeTrait)
            self.assertIsNotNone(trait.max)
            self.assertIsNotNone(trait.rate)
            self.assertIsNone(trait._data["last_update"])
        for key in STATIC_KEYS:
            trait = getattr(entity.traits, key)
            self.assertIsInstance(trait, StaticTrait)
            self.assertEqual(trait.value, trait.base + trait.mod)
        for key in ("magic_level", "guild_merit"):
            self.assertIsInstance(getattr(entity.traits, key), CounterTrait)

    def test_species_floor_static_values_stay_in_registry_bands(self):
        for race_key, race in RACE_REGISTRY.items():
            entity = self._entity(race_key)
            for key in STATIC_KEYS:
                lower, upper = getattr(race.static_baseline, key)
                self.assertLessEqual(lower, getattr(entity.traits, key).base)
                self.assertLessEqual(getattr(entity.traits, key).base, upper)

    @covers_requirement("entity-trait-scales::every-stored-static-trait-value-is-a-base-value-never-a-skill-multiplied-value")
    def test_every_subrace_is_the_exact_documented_post_baseline_adjustment(self):
        from world.lore.races import SUBRACE_REGISTRY

        for subrace_key, subrace in SUBRACE_REGISTRY.items():
            baseline = build_initial_traits(subrace.race_key)
            adjusted = build_initial_traits(subrace.race_key, subrace_key)
            for key in STATIC_KEYS:
                expected = round(
                    baseline[key] * (1 + getattr(subrace.static_modifiers, key))
                )
                self.assertEqual(adjusted[key], expected)

    def test_trait_replacement_rolls_back_when_handler_rejects_config(self):
        entity = self._entity("human")
        before = {
            key: dict(entity.traits.trait_data[key])
            for key in entity.traits.all()
        }
        invalid = {
            "broken": {"trait_type": "not-a-real-trait-type", "base": 1}
        }
        with self.assertRaises(Exception):
            entity._apply_trait_config(invalid)
        self.assertEqual(set(entity.traits.all()), set(before))
        for key, properties in before.items():
            self.assertEqual(dict(entity.traits.trait_data[key]), properties)
