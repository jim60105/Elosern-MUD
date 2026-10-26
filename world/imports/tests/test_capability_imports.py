"""Direct capability declarations through the import schema, validator and loader.

Replaces the profession-blueprint suites: the same behavioral contracts are
proven on explicit declarations — shape and vocabulary rejection before
construction, the complete plan assembled inside the all-or-nothing batch, the
two fail-closed gates, and the literal-stats construction that no longer
consults a tier.

The probe dialogue key is registered in the live dialogue table for the test
scope only; no shipped table, place or record is touched.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from typeclasses.components import (
    GuildStaff,
    Merchant,
    QuestIssuer,
    ScriptedDialogue,
)
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.imports.loader import ImportRejected, load_batch
from world.imports.tests.helpers import example_record
from world.imports.validate import validate_character
from world.lore.races import RACE_REGISTRY
from world.rules.quest_issuance import npc_issuer_key, resolve_issuer_key
from world.rules.traits import race_floor

_DIALOGUE_KEY = "capability_probe_dialogue"
_ANCHOR_TAG = "capability_probe_anchor"

_SCHEMA_REQUIREMENT = (
    "import-schema::the-character-record-schema-defines-an-optional-profession-field-and-an-optional-components-field"
)
_ASSEMBLY_REQUIREMENT = (
    "import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence"
)
_ISSUER_REQUIREMENT = (
    "quest-issuer-authorization::commissioner-authority-is-authorable-through-the-import-pipeline"
)


def _patch_dialogue_table():
    from world.rules import dialogue

    table = dict(dialogue.DIALOGUE_TABLE)
    table[_DIALOGUE_KEY] = next(iter(dialogue.DIALOGUE_TABLE.values()))
    return patch.object(dialogue, "DIALOGUE_TABLE", MappingProxyType(table))


def merchant_entry(service_id="probe_service", shop_key="probe_shop", **extra):
    kwargs = {"service_id": service_id, "shop_key": shop_key, **extra}
    return {
        "type": Merchant.name,
        "kwargs": kwargs,
        "binding": {"kind": "place", "anchor_room": _ANCHOR_TAG},
    }


def dialogue_entry(**extra):
    return {
        "type": ScriptedDialogue.name,
        "kwargs": {"dialogue_key": _DIALOGUE_KEY, **extra},
        "binding": {"kind": "place", "anchor_room": _ANCHOR_TAG},
    }


def issuer_entry(service_id="probe_service", issuer_key="probe_commission"):
    return {
        "type": QuestIssuer.name,
        "kwargs": {"service_id": service_id, "issuer_key": issuer_key},
        "binding": {"kind": "person"},
    }


class CapabilitySchemaTests(unittest.TestCase):
    def setUp(self):
        self._dialogue = _patch_dialogue_table()
        self._dialogue.start()
        self.addCleanup(self._dialogue.stop)

    def _record(self, **overrides):
        record = example_record()
        record["key"] = "capability_probe_record"
        record.update(overrides)
        return record

    @covers_requirement(_SCHEMA_REQUIREMENT)
    def test_absent_components_declare_no_capabilities(self):
        report = validate_character(self._record())
        self.assertTrue(report.is_valid, report.rejections)

    def test_empty_components_list_is_a_valid_declaration(self):
        report = validate_character(self._record(components=[]))
        self.assertTrue(report.is_valid, report.rejections)

    @covers_requirement(_SCHEMA_REQUIREMENT)
    def test_a_removed_profession_field_is_structurally_rejected(self):
        report = validate_character(self._record(profession="merchant"))
        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("profession" in issue.message for issue in report.rejections)
        )

    @covers_requirement(_SCHEMA_REQUIREMENT)
    def test_unknown_type_and_duplicate_type_are_named(self):
        unknown = validate_character(
            self._record(components=[{"type": "blacksmith", "kwargs": {}}])
        )
        self.assertFalse(unknown.is_valid)
        self.assertTrue(
            any("blacksmith" in issue.message for issue in unknown.rejections)
        )
        duplicate = validate_character(
            self._record(components=[merchant_entry(), merchant_entry()])
        )
        self.assertFalse(duplicate.is_valid)
        self.assertTrue(
            any("more than once" in issue.message for issue in duplicate.rejections)
        )

    @covers_requirement(_SCHEMA_REQUIREMENT)
    def test_unknown_kwarg_runtime_field_and_missing_required_kwarg_are_named(self):
        unknown = validate_character(
            self._record(components=[merchant_entry(branch_key="not_a_merchant_field")])
        )
        self.assertTrue(
            any("branch_key" in issue.message for issue in unknown.rejections)
        )
        runtime = validate_character(
            self._record(components=[merchant_entry(merchant_stock={"probe_item": 1})])
        )
        self.assertTrue(
            any("runtime-owned field" in issue.message for issue in runtime.rejections)
        )
        missing = validate_character(
            self._record(
                components=[
                    {
                        "type": Merchant.name,
                        "kwargs": {"service_id": "probe_service"},
                        "binding": {"kind": "person"},
                    }
                ]
            )
        )
        self.assertTrue(
            any("shop_key" in issue.message for issue in missing.rejections)
        )

    @covers_requirement(_SCHEMA_REQUIREMENT)
    def test_malformed_binding_shape_is_a_structural_rejection(self):
        report = validate_character(
            self._record(
                components=[
                    {
                        "type": QuestIssuer.name,
                        "kwargs": {"service_id": "probe_service"},
                        "binding": {"kind": "portable"},
                    }
                ]
            )
        )
        self.assertFalse(report.is_valid)
        self.assertTrue(any("binding" in issue.field for issue in report.rejections))

    @covers_requirement(_SCHEMA_REQUIREMENT)
    def test_a_player_target_cannot_declare_capabilities(self):
        report = validate_character(
            self._record(components=[issuer_entry()]), PlayerCharacter
        )
        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("capabilities" in issue.message for issue in report.rejections)
        )

    @covers_requirement(_ISSUER_REQUIREMENT)
    def test_issuer_key_stays_optional_and_duplicates_reject_the_batch(self):
        optional = validate_character(
            self._record(
                components=[
                    {
                        "type": QuestIssuer.name,
                        "kwargs": {"service_id": "probe_service"},
                        "binding": {"kind": "person"},
                    }
                ]
            )
        )
        self.assertTrue(optional.is_valid, optional.rejections)


class CapabilityBatchHarness(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        dialogue_patcher = _patch_dialogue_table()
        dialogue_patcher.start()
        self.addCleanup(dialogue_patcher.stop)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.anchor_room = create_object(Room, key="probe anchor room", tags=[_ANCHOR_TAG])

    def write(self, name, record):
        path = self.root / name
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return path

    def record(self, key, components):
        record = example_record()
        record["key"] = key
        record["components"] = components
        return record


class CapabilityLoaderTests(CapabilityBatchHarness):
    @covers_requirement(_ASSEMBLY_REQUIREMENT)
    def test_each_declaration_attaches_once_with_its_own_kwargs(self):
        npc = load_batch(
            [
                self.write(
                    "assembled.json",
                    self.record(
                        "capability_probe_host",
                        [merchant_entry(), dialogue_entry()],
                    ),
                )
            ]
        )[0]
        self.assertTrue(npc.components.has(Merchant.name))
        self.assertTrue(npc.components.has(ScriptedDialogue.name))
        merchant = npc.components.get(Merchant.get_component_slot())
        self.assertEqual(merchant.service_id, "probe_service")
        self.assertEqual(merchant.shop_key, "probe_shop")
        self.assertEqual(merchant.service_binding, "place")
        self.assertEqual(merchant.anchor_room_id, self.anchor_room.pk)
        dialogue = npc.components.get(ScriptedDialogue.get_component_slot())
        self.assertEqual(dialogue.dialogue_key, _DIALOGUE_KEY)

    @covers_requirement(_ISSUER_REQUIREMENT)
    def test_a_merchant_can_also_be_a_person_bound_commissioner(self):
        npc = load_batch(
            [
                self.write(
                    "commissioner.json",
                    self.record(
                        "capability_probe_commissioner",
                        [
                            {
                                "type": Merchant.name,
                                "kwargs": {
                                    "service_id": "probe_service",
                                    "shop_key": "probe_shop",
                                },
                                "binding": {"kind": "person"},
                            },
                            issuer_entry(),
                        ],
                    ),
                )
            ]
        )[0]
        issuer = npc.components.get(QuestIssuer.get_component_slot())
        self.assertEqual(issuer.issuer_key, "probe_commission")
        self.assertEqual(issuer.service_binding, "person")
        self.assertIsNone(issuer.anchor_room_id)
        self.assertEqual(resolve_issuer_key(npc), npc_issuer_key("probe_commission"))

    @covers_requirement(_ISSUER_REQUIREMENT)
    def test_the_loader_never_invents_an_issuer_key(self):
        npc = load_batch(
            [
                self.write(
                    "identity_issuer.json",
                    self.record(
                        "capability_probe_identity_issuer",
                        [
                            {
                                "type": QuestIssuer.name,
                                "kwargs": {"service_id": "probe_service"},
                                "binding": {"kind": "person"},
                            }
                        ],
                    ),
                )
            ]
        )[0]
        issuer = npc.components.get(QuestIssuer.get_component_slot())
        self.assertIsNone(issuer.issuer_key)
        self.assertEqual(resolve_issuer_key(npc), npc_issuer_key(pk=npc.pk))

    @covers_requirement(_ASSEMBLY_REQUIREMENT)
    def test_unresolved_ambiguous_and_non_room_anchors_abort_the_batch(self):
        create_object(Room, key="ambiguity first", tags=["ambiguous_probe"])
        create_object(Room, key="ambiguity second", tags=["ambiguous_probe"])
        create_object(NPC, key="probe squatter", tags=["squatter_probe"])
        for tag, fragment in (
            ("absent_probe", "resolves to no room"),
            ("ambiguous_probe", "the anchor must be unique"),
            ("squatter_probe", "non-Room object"),
        ):
            with self.subTest(tag=tag):
                record = self.record(
                    f"capability_probe_{tag}",
                    [
                        {
                            "type": Merchant.name,
                            "kwargs": {
                                "service_id": "probe_service",
                                "shop_key": "probe_shop",
                            },
                            "binding": {"kind": "place", "anchor_room": tag},
                        }
                    ],
                )
                with self.assertRaises(ValueError) as caught:
                    load_batch([self.write(f"{tag}.json", record)])
                self.assertIn(fragment, str(caught.exception))
                self.assertFalse(NPC.objects.filter(db_key=record["key"]).exists())

    @covers_requirement(_ASSEMBLY_REQUIREMENT)
    def test_a_validation_failure_persists_nothing_for_the_whole_batch(self):
        good = self.record("capability_probe_good", [merchant_entry()])
        broken = self.record(
            "capability_probe_broken",
            [
                {
                    "type": Merchant.name,
                    "kwargs": {"service_id": "probe_service"},
                    "binding": {"kind": "place", "anchor_room": _ANCHOR_TAG},
                }
            ],
        )
        paths = [self.write("good.json", good), self.write("broken.json", broken)]
        with self.assertRaises(ImportRejected):
            load_batch(paths)
        self.assertFalse(
            NPC.objects.filter(
                db_key__in=["capability_probe_good", "capability_probe_broken"]
            ).exists()
        )

    @covers_requirement(_ASSEMBLY_REQUIREMENT)
    def test_injected_assembly_failure_rolls_the_batch_and_its_handler_caches_back(self):
        from world.imports import loader
        from world.rules import npc_capabilities

        first = self.record("capability_probe_first", [merchant_entry()])
        second = self.record("capability_probe_second", [merchant_entry()])
        paths = [self.write("first.json", first), self.write("second.json", second)]
        real = npc_capabilities.assemble_capabilities
        calls: list[str] = []

        def fail_second(entity, plan, **kwargs):
            calls.append(entity.key)
            if len(calls) == 2:
                raise RuntimeError("injected assembly failure")
            return real(entity, plan, **kwargs)

        with patch.object(loader, "assemble_capabilities", fail_second):
            with self.assertRaises(RuntimeError):
                load_batch(paths)
        self.assertEqual(calls, ["capability_probe_first", "capability_probe_second"])
        self.assertFalse(
            NPC.objects.filter(
                db_key__in=["capability_probe_first", "capability_probe_second"]
            ).exists()
        )

    def test_one_assembly_event_is_emitted_per_assembled_npc(self):
        from world.imports import loader

        with patch.object(loader, "log_info") as logged, (
            self.captureOnCommitCallbacks(execute=True)
        ):
            load_batch(
                [
                    self.write(
                        "event.json",
                        self.record(
                            "capability_probe_event", [merchant_entry(), dialogue_entry()]
                        ),
                    )
                ]
            )
        events = [
            (call.args[0], call.kwargs["context"])
            for call in logged.call_args_list
            if call.args and call.args[0] == "import_capabilities_assembled"
        ]
        self.assertEqual(len(events), 1)
        _, context = events[0]
        self.assertEqual(context["char"], "capability_probe_event")
        self.assertEqual(sorted(context["components"]), ["merchant", "scripted_dialogue"])
        self.assertNotIn("profession", context)

    @covers_requirement(_ASSEMBLY_REQUIREMENT)
    def test_a_record_without_components_constructs_no_capability_slot(self):
        npc = load_batch(
            [self.write("plain.json", self.record("capability_probe_plain", []))]
        )[0]
        for component_class in (
            Merchant,
            GuildStaff,
            ScriptedDialogue,
            QuestIssuer,
        ):
            self.assertFalse(npc.components.has(component_class.name))


if __name__ == "__main__":
    unittest.main()
