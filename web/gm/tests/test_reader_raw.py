"""Fixed-fixture reader tests: the universal raw inventory (task 1.2 / 6.1).

Establishes the delta requirement "Universal Evennia raw inspection": every
Evennia object — curated or not — exposes all Attributes with key/category and
converted value, categorized tags, the existing components and their field
Attributes, the typeclass path, the location and the creation date. Object
references serialize as ``$ref`` and values JSON cannot carry serialize as a
bounded ``$unserializable`` marker without preventing the rest of the
inventory from rendering. Non-Evennia records expose their stored fields as
raw data instead of pretending to have Attributes. The ``gm-runtime-state``
requirement annotations were attached when the delta spec synced into the main
spec at archive.
"""

from __future__ import annotations

from datetime import datetime

from evennia.objects.objects import DefaultObject
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from web.gm.readers import raw
from web.gm.readers._json import MAX_REPR_CHARS, json_value


class JsonConversionTests(EvenniaTest):
    """``json_value`` is total: no value can break the whole inventory."""

    @covers_requirement("gm-runtime-state::universal-evennia-raw-inspection")
    def test_object_references_become_ref_markers(self):
        self.assertEqual(
            json_value(self.obj1),
            {
                "$ref": f"#{self.obj1.pk}",
                "typeclass": self.obj1.db_typeclass_path,
                "key": self.obj1.db_key,
            },
        )

    @covers_requirement("gm-runtime-state::universal-evennia-raw-inspection")
    def test_unsupported_values_carry_a_bounded_repr(self):
        marker = json_value(complex(1, 2))
        self.assertEqual(set(marker), {"$unserializable", "repr"})
        self.assertEqual(marker["$unserializable"], "complex")
        # A long repr is clipped to the documented bound.
        clipped = json_value(bytearray(b"x" * 400))
        self.assertEqual(clipped["$unserializable"], "bytearray")
        self.assertEqual(len(clipped["repr"]), MAX_REPR_CHARS)

    def test_a_cycle_becomes_one_bounded_marker(self):
        cyclic: list = []
        cyclic.append(cyclic)
        self.assertEqual(json_value(cyclic), [{"$unserializable": "list", "repr": "[[...]]"}])

    def test_scalars_collections_and_datetimes_convert(self):
        self.assertEqual(json_value({"a": [1, "b", None, True]}), {"a": [1, "b", None, True]})
        self.assertEqual(json_value(datetime(2026, 10, 7, 1, 2, 3)), "2026-10-07T01:02:03")
        self.assertEqual(json_value({1, 2}), [1, 2])
        self.assertEqual(json_value("x" * 400), "x" * 400)
        self.assertEqual(json_value(float("inf"))["$unserializable"], "float")


class RawInventoryTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.plain = create.create_object(
            DefaultObject, key="t_reader_plain", location=self.room1
        )
        self.plain.attributes.add("t_count", value=7)
        self.plain.attributes.add("t_plain_note", value="備註", category="t_notes")
        self.plain.attributes.add("t_link", value=self.room1)
        self.plain.attributes.add("t_slot::field", value="合成欄位")
        self.plain.attributes.add("component_names", value=["t_slot"])
        self.plain.tags.add("t_tagged", category="t_category")

    @covers_requirement("gm-runtime-state::universal-evennia-raw-inspection")
    def test_raw_object_lists_every_attribute_with_its_category(self):
        inventory = raw.raw_object(self.plain)
        keys = {(row["key"], row["category"]) for row in inventory["attributes"]}
        self.assertIn(("t_count", ""), keys)
        self.assertIn(("t_plain_note", "t_notes"), keys)
        # Sorted by (category, key): the categorized row is not lost among them.
        self.assertEqual(
            inventory["attributes"],
            sorted(inventory["attributes"], key=lambda row: (row["category"], row["key"])),
        )
        values = {row["key"]: row["value"] for row in inventory["attributes"]}
        self.assertEqual(values["t_count"], 7)

    def test_attribute_values_are_converted_references(self):
        inventory = raw.raw_object(self.plain)
        values = {row["key"]: row["value"] for row in inventory["attributes"]}
        self.assertEqual(values["t_link"]["$ref"], f"#{self.room1.pk}")

    @covers_requirement("gm-runtime-state::universal-evennia-raw-inspection")
    def test_categorized_tags_and_existing_components_are_reported(self):
        inventory = raw.raw_object(self.plain)
        self.assertIn({"key": "t_tagged", "category": "t_category"}, inventory["tags"])
        components = {entry["name"]: entry["fields"] for entry in inventory["components"]}
        self.assertEqual(components, {"t_slot": {"field": "合成欄位"}})

    def test_identity_location_and_creation_date_are_reported(self):
        inventory = raw.raw_object(self.plain)
        self.assertEqual(inventory["dbref"], self.plain.pk)
        self.assertEqual(inventory["location"]["$ref"], f"#{self.room1.pk}")
        self.assertEqual(inventory["typeclass"], self.plain.db_typeclass_path)
        self.assertIsInstance(inventory["date_created"], str)
        identity = raw.raw_identity(self.plain)
        self.assertEqual(identity["kind"], "object")
        self.assertEqual(identity["id"], str(self.plain.pk))

    @covers_requirement("gm-runtime-state::universal-evennia-raw-inspection")
    def test_an_account_reports_no_object_only_location(self):
        inventory = raw.raw_object(self.account)
        self.assertIsNone(inventory["location"])
        self.assertIsInstance(inventory["attributes"], list)

    def test_component_fields_are_read_from_the_attribute_inventory_alone(self):
        # ``component_names`` is the only registry read; no handler is built.
        inventory = raw.raw_object(self.plain)
        self.assertEqual([entry["name"] for entry in inventory["components"]], ["t_slot"])

    def test_an_object_reference_keeps_its_shape_and_others_carry_their_model(self):
        self.plain.attributes.add("t_account", value=self.account)
        values = {
            row["key"]: row["value"] for row in raw.raw_object(self.plain)["attributes"]
        }
        # An ObjectDB reference is exactly the specified marker: the raw-object
        # route is the one that can resolve it.
        self.assertEqual(set(values["t_link"]), {"$ref", "typeclass", "key"})
        # An account reference lives in another table, so it says so and is
        # never routed to the ObjectDB namespace.
        self.assertEqual(values["t_account"]["model"], "account")
        self.assertEqual(values["t_account"]["$ref"], f"#{self.account.pk}")
