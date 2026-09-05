"""Schema + semantic contract for the profession/components record fields.

Pure logic: no database. The profession registry cache is swapped through the
``profession_config`` module attribute so rejections are exercised without the
shipped rulebook, and the shipped example pins the absent-fields baseline.
"""

from types import MappingProxyType
from unittest import TestCase
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.imports import assembly
from world.imports.tests.helpers import example_record
from world.imports.validate import validate_character
from world.rules import profession_assembly
from world.rules import profession_config
from world.rules.profession_config import Profession, ProfessionComponent



def _table(**rows: Profession) -> MappingProxyType:
    return MappingProxyType({row.key: row for row in rows.values()})


PROBE = Profession(
    key="merchant",
    components=(ProfessionComponent(type_key="merchant", default_binding="place"),),
    schedule_template=None,
    default_tier=None,
)


class ProfessionSchemaHarness(TestCase):
    def setUp(self):
        super().setUp()
        self.addPatch(
            patch.object(profession_config, "TABLE", _table(merchant=PROBE))
        )

    def addPatch(self, patcher):
        patcher.start()
        self.addCleanup(patcher.stop)

    def rejections(self, record):
        return validate_character(record).rejections

    def fields(self, record):
        return [issue.field for issue in self.rejections(record)]

    def assert_rejected(self, record, *needles):
        issues = self.rejections(record)
        self.assertTrue(issues, "expected at least one named rejection")
        blob = " ".join(f"{issue.field} {issue.message}" for issue in issues)
        for needle in needles:
            self.assertIn(needle, blob)


class ProfessionSemanticTests(ProfessionSchemaHarness):
    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_absent_fields_leave_the_record_structurally_unchanged(self):
        record = example_record()
        self.assertEqual(self.rejections(record), [])
        record["profession"] = None
        self.assertEqual(self.rejections(record), [])

    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_unknown_profession_key_is_a_named_issue(self):
        record = example_record()
        record["profession"] = "paladin"
        self.assert_rejected(record, "profession", "paladin")

    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_component_type_outside_the_vocabulary_is_a_named_issue(self):
        record = example_record()
        record["profession"] = "merchant"
        record["components"] = [{"type": "tinker", "kwargs": {}}]
        self.assert_rejected(record, "components.0.type", "tinker", "vocabulary")

    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_components_without_a_profession_is_a_named_issue(self):
        record = example_record()
        record["components"] = [
            {"type": "merchant", "kwargs": {"service_id": "s", "shop_key": "b"}}
        ]
        self.assert_rejected(
            record, "components", "profession", "blueprint"
        )

    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_an_empty_components_declaration_without_a_profession_is_rejected(self):
        # Presence, not emptiness, is the declaration: an explicit [] is still
        # a components row riding alongside no blueprint.
        record = example_record()
        record["components"] = []
        self.assert_rejected(record, "components", "profession")
        # An explicit null profession does not make it a legal pair either.
        record["profession"] = None
        self.assert_rejected(record, "components", "profession")

    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_kwarg_outside_the_component_fields_is_a_named_issue(self):
        record = example_record()
        record["profession"] = "merchant"
        record["components"] = [
            {"type": "merchant", "kwargs": {"bogus_key": "x"}}
        ]
        self.assert_rejected(
            record, "components.0.kwargs", "bogus_key", "shop_key"
        )

    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_duplicate_component_types_are_rejected(self):
        record = example_record()
        record["profession"] = "merchant"
        entry = {"type": "merchant", "kwargs": {"service_id": "s", "shop_key": "b"}}
        record["components"] = [dict(entry), dict(entry)]
        self.assert_rejected(
            record, "components.1.type", "duplicate", "merchant"
        )

    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_missing_identity_kwargs_are_rejected_on_the_resolved_plan(self):
        record = example_record()
        record["profession"] = "merchant"
        record["components"] = [{"type": "merchant", "kwargs": {"shop_key": "b"}}]
        self.assert_rejected(
            record, "components", "merchant", "identity", "service_id"
        )
        # A blank string counts as missing identity, never as authored.
        record["components"][0]["kwargs"]["service_id"] = ""
        self.assert_rejected(record, "service_id")

    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_a_fully_authored_plan_validates_clean(self):
        record = example_record()
        record["profession"] = "merchant"
        record["components"] = [
            {
                "type": "merchant",
                "kwargs": {"service_id": "silver_scales", "shop_key": "plaza"},
            }
        ]
        self.assertEqual(self.rejections(record), [])

    def test_player_character_target_rejects_a_profession(self):
        from typeclasses.characters import PlayerCharacter

        record = example_record()
        record["profession"] = "merchant"
        record["components"] = [
            {
                "type": "merchant",
                "kwargs": {"service_id": "s", "shop_key": "b"},
            }
        ]
        issues = validate_character(record, PlayerCharacter).rejections
        blob = " ".join(f"{issue.field} {issue.message}" for issue in issues)
        self.assertIn("PlayerCharacter", blob)
        self.assertIn("profession", blob)
        # The same record is clean against the NPC-default target.
        self.assertEqual(validate_character(record).rejections, [])


class ProfessionSchemaShapeTests(ProfessionSchemaHarness):
    @covers_requirement("import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field")
    def test_shape_violations_are_structural_rejections(self):
        cases = [
            ("non-list components", lambda r: r.update(components="merchant")),
            ("non-dict entry", lambda r: r.update(components=["merchant"])),
            ("missing kwargs key", lambda r: r.update(components=[{"type": "merchant"}])),
            ("extra entry property", lambda r: r.update(
                components=[{"type": "merchant", "kwargs": {}, "extra": 1}]
            )),
            ("non-string type", lambda r: r.update(components=[{"type": 7, "kwargs": {}}])),
            ("non-object kwargs", lambda r: r.update(components=[{"type": "merchant", "kwargs": "x"}])),
        ]
        for label, mutate in cases:
            with self.subTest(label):
                record = example_record()
                record["profession"] = "merchant"
                mutate(record)
                self.assertTrue(
                    self.rejections(record),
                    "shape violation must be rejected",
                )


class AssemblyPlanTests(TestCase):
    """The one resolution algorithm shared by validator and loader."""

    def setUp(self):
        self.profession = Profession(
            key="guild_staff",
            components=(
                ProfessionComponent("guild_staff", "place"),
                ProfessionComponent("guild_examiner", "place"),
                ProfessionComponent("scripted_dialogue", "place"),
            ),
            schedule_template=None,
            default_tier=None,
        )

    def test_explicit_entry_replaces_the_blueprint_entry(self):
        record = {
            "components": [
                {"type": "guild_staff", "kwargs": {"service_id": "s", "branch_key": "b"}}
            ]
        }
        plan = assembly.resolve_plan(self.profession, record)
        self.assertEqual(
            plan,
            [
                ("guild_staff", {"service_id": "s", "branch_key": "b"}),
                ("guild_examiner", {}),
                ("scripted_dialogue", {}),
            ],
        )

    def test_extra_vocabulary_entries_append_in_record_order(self):
        record = {
            "components": [
                {"type": "merchant", "kwargs": {"service_id": "s", "shop_key": "k"}},
                {
                    "type": "scripted_dialogue",
                    "kwargs": {"dialogue_key": "dock"},
                },
            ]
        }
        plan = assembly.resolve_plan(self.profession, record)
        self.assertEqual([type_key for type_key, _ in plan][-1], "merchant")
        self.assertIn(
            ("scripted_dialogue", {"dialogue_key": "dock"}), plan
        )
        self.assertEqual(
            sum(1 for type_key, _ in plan if type_key == "scripted_dialogue"), 1
        )

    def test_identity_fields_are_the_class_intersection(self):
        self.assertEqual(
            profession_assembly.identity_fields("merchant"),
            frozenset({"service_id", "shop_key"}),
        )
        self.assertEqual(
            profession_assembly.identity_fields("scripted_dialogue"),
            frozenset({"dialogue_key"}),
        )
        self.assertEqual(
            profession_assembly.missing_identity_kwargs(
                "merchant", {"service_id": "s", "shop_key": "b"}
            ),
            [],
        )
        self.assertEqual(
            profession_assembly.missing_identity_kwargs("merchant", {}),
            ["service_id", "shop_key"],
        )

    def test_component_field_names_are_the_class_db_fields(self):
        self.assertEqual(
            profession_assembly.component_field_names("merchant"),
            frozenset({"service_id", "shop_key", "merchant_stock", "last_restock_day"}),
        )
