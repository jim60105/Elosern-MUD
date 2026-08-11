"""Tests for the canonical-inventory mirror helpers (fix-inventory-model-unification)."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.equipment import (
    materialize_registry_object,
    registry_key_for_object,
)


class RegistryKeyForObjectTests(EvenniaTest):
    """The explicit ``registry_key`` attribute wins over the object key."""

    def test_attribute_mapping_beats_object_key(self):
        obj = create_object(
            "typeclasses.objects.Object",
            key="meal",
            attributes=[("registry_key", "plain_sword")],
            location=self.char1,
        )
        self.assertEqual(registry_key_for_object(obj), "plain_sword")

    def test_object_key_mapping_without_attribute(self):
        obj = create_object("typeclasses.objects.Object", key="meal", location=self.char1)
        self.assertEqual(registry_key_for_object(obj), "meal")

    def test_non_registry_object_maps_to_none(self):
        obj = create_object("typeclasses.objects.Object", key="銅幣", location=self.char1)
        self.assertIsNone(registry_key_for_object(obj))

    def test_unregistered_attribute_maps_to_none(self):
        obj = create_object(
            "typeclasses.objects.Object",
            key="銅幣",
            attributes=[("registry_key", "iron_ore")],
            location=self.char1,
        )
        self.assertIsNone(registry_key_for_object(obj))


class MaterializeRegistryObjectTests(EvenniaTest):
    """Materialized mirrors carry both the object key and the attribute."""

    def test_materialized_object_is_contained_and_resolvable(self):
        materialize_registry_object(self.char1, "meal")
        contained = [o for o in self.char1.contents if o.key == "meal"]
        self.assertEqual(len(contained), 1)
        self.assertEqual(registry_key_for_object(contained[0]), "meal")
        self.assertEqual(contained[0].db.registry_key, "meal")

    def test_materialization_targets_any_container(self):
        room_obj = materialize_registry_object(self.room1, "healing_potion")
        self.assertIs(room_obj.location, self.room1)
        self.assertEqual(registry_key_for_object(room_obj), "healing_potion")
