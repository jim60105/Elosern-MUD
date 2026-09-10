"""Tests for the canonical-inventory mirror helpers (fix-inventory-model-unification).

Data-independent (migrate-rules-equipment-item-tests-off-real-data): every
registry membership the helpers resolve is a synthetic kit row opened in a
scope; unregistered keys are invented synthetic keys, never shipped data.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from world.rules.equipment import (
    materialize_registry_object,
    registry_key_for_object,
)

from ._combat_session_helpers import open_synthetic_scope

# Synthetic kit rows (registered inside the scope) and invented unregistered
# keys (never present in any registry, scoped or shipped).
_ATTR_KEY = "t_ember_spray"
_OBJECT_KEY = "t_iron_fang"
_UNMARKED_KEY = "t_unmarked_crate"
_UNREGISTERED_ATTR = "t_forged_seal"


class RegistryKeyForObjectTests(EvenniaTest):
    """The explicit ``registry_key`` attribute wins over the object key."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "items")

    def test_attribute_mapping_beats_object_key(self):
        obj = create_object(
            "typeclasses.objects.Object",
            key=_OBJECT_KEY,
            attributes=[("registry_key", _ATTR_KEY)],
            location=self.char1,
        )
        self.assertEqual(registry_key_for_object(obj), _ATTR_KEY)

    def test_object_key_mapping_without_attribute(self):
        obj = create_object(
            "typeclasses.objects.Object", key=_ATTR_KEY, location=self.char1
        )
        self.assertEqual(registry_key_for_object(obj), _ATTR_KEY)

    def test_non_registry_object_maps_to_none(self):
        obj = create_object(
            "typeclasses.objects.Object", key=_UNMARKED_KEY, location=self.char1
        )
        self.assertIsNone(registry_key_for_object(obj))

    def test_unregistered_attribute_maps_to_none(self):
        obj = create_object(
            "typeclasses.objects.Object",
            key=_UNMARKED_KEY,
            attributes=[("registry_key", _UNREGISTERED_ATTR)],
            location=self.char1,
        )
        self.assertIsNone(registry_key_for_object(obj))


class MaterializeRegistryObjectTests(EvenniaTest):
    """Materialized mirrors carry both the object key and the attribute."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "items")

    def test_materialized_object_is_contained_and_resolvable(self):
        materialize_registry_object(self.char1, _ATTR_KEY)
        contained = [o for o in self.char1.contents if o.key == _ATTR_KEY]
        self.assertEqual(len(contained), 1)
        self.assertEqual(registry_key_for_object(contained[0]), _ATTR_KEY)
        self.assertEqual(contained[0].db.registry_key, _ATTR_KEY)

    def test_materialization_targets_any_container(self):
        room_obj = materialize_registry_object(self.room1, _OBJECT_KEY)
        self.assertIs(room_obj.location, self.room1)
        self.assertEqual(registry_key_for_object(room_obj), _OBJECT_KEY)
