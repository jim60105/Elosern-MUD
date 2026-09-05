"""Loader-facing assembly of profession blueprints onto imported NPCs.

Uses EvenniaTestCase (no shared fixtures): every test loads records through the
public batch boundary and asserts persisted state. The profession registry cache
is swapped through the ``profession_config`` module attribute, so tiered and
scheduled rows exist without shipping rulebook churn.
"""

import json
import tempfile
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.imports.loader import ImportRejected, load_batch
from world.imports.tests.helpers import example_record
from world.rules import profession_config
from world.rules.profession_config import Profession, ProfessionComponent
from world.rules.traits import initial_trait_config


MERCHANT_PROBE = Profession(
    key="merchant",
    components=(ProfessionComponent("merchant", "place"),),
    schedule_template=None,
    default_tier=None,
)
STAFF_PROBE = Profession(
    key="guild_staff",
    components=(
        ProfessionComponent("guild_staff", "place"),
        ProfessionComponent("guild_examiner", "place"),
        ProfessionComponent("scripted_dialogue", "place"),
    ),
    schedule_template=None,
    default_tier=None,
)
TIERED_PROBE = Profession(
    key="tiered_merchant",
    components=(ProfessionComponent("merchant", "place"),),
    schedule_template="guard",
    default_tier="human_commoner",
)
PROBE_TABLE = MappingProxyType(
    {probe.key: probe for probe in (MERCHANT_PROBE, STAFF_PROBE, TIERED_PROBE)}
)


def merchant_kwargs(service_id="silver_scales", shop_key="plaza_stall"):
    return {"service_id": service_id, "shop_key": shop_key}


def staff_entry():
    return {
        "type": "guild_staff",
        "kwargs": {"service_id": "silver_scales", "branch_key": "plaza_stall"},
    }


class ProfessionAssemblyHarness(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        patcher = patch.object(profession_config, "TABLE", PROBE_TABLE)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def write(self, name, record):
        path = self.root / name
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return path

    def assembled(self, record, name="assembled.json", **kwargs):
        path = self.write(name, record)
        return load_batch([path], **kwargs)[0]


class ExplicitPrecedenceTests(ProfessionAssemblyHarness):
    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_record_entries_attach_once_with_their_own_kwargs(self):
        # Every vocabulary class carries identity fields, so a blueprint-only
        # component can never be attached (the loader never invents identity).
        # The record therefore authors all three slots; each attaches exactly
        # once with the record's kwargs, replacing the blueprint entry entirely.
        record = example_record()
        record["key"] = "assembled_staff"
        record["profession"] = "guild_staff"
        record["components"] = [
            staff_entry(),
            {
                "type": "guild_examiner",
                "kwargs": {"service_id": "silver_scales", "branch_key": "plaza_stall"},
            },
            {"type": "scripted_dialogue", "kwargs": {"dialogue_key": "dock_gossip"}},
        ]
        npc = self.assembled(record)
        self.assertTrue(npc.components.has("guild_staff"))
        self.assertTrue(npc.components.has("guild_examiner"))
        self.assertTrue(npc.components.has("scripted_dialogue"))
        staff = npc.components.get("guild_staff")
        self.assertEqual(staff.service_id, "silver_scales")
        self.assertEqual(staff.branch_key, "plaza_stall")
        dialogue = npc.components.get("scripted_dialogue")
        self.assertEqual(dialogue.dialogue_key, "dock_gossip")
        examiner = npc.components.get("guild_examiner")
        self.assertEqual(examiner.branch_key, "plaza_stall")
        # Exactly one component instance per slot.
        slots = [
            name
            for name in ("guild_staff", "guild_examiner", "scripted_dialogue")
            if npc.components.has(name)
        ]
        self.assertEqual(len(slots), 3)
        self.assertEqual(
            sum(
                1
                for n in npc.components.db_names
                if n in ("guild_staff", "guild_examiner", "scripted_dialogue")
            ),
            3,
        )

    def test_extra_vocabulary_entry_outside_the_blueprint_attaches(self):
        # ``merchant`` is outside the guild_staff blueprint: it appends after
        # the blueprint types, never duplicating a slot.
        record = example_record()
        record["key"] = "assembled_extra"
        record["profession"] = "guild_staff"
        record["components"] = [
            staff_entry(),
            {
                "type": "guild_examiner",
                "kwargs": {"service_id": "silver_scales", "branch_key": "hall"},
            },
            {"type": "scripted_dialogue", "kwargs": {"dialogue_key": "dock"}},
            {
                "type": "merchant",
                "kwargs": {"service_id": "silver_scales", "shop_key": "side_stall"},
            },
        ]
        npc = self.assembled(record)
        self.assertTrue(npc.components.has("merchant"))
        self.assertEqual(
            npc.components.get("merchant").shop_key, "side_stall"
        )
        self.assertEqual(
            sum(1 for n in npc.components.db_names if n == "merchant"), 1
        )

    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_blueprint_only_identity_gap_is_a_named_batch_rejection(self):
        # The blueprint's scripted_dialogue slot has no record entry, so its
        # dialogue_key can never be authored anywhere: named issue, not a
        # silently identity-less attach.
        record = example_record()
        record["key"] = "blueprint_gap"
        record["profession"] = "guild_staff"
        record["components"] = [
            staff_entry(),
            {
                "type": "guild_examiner",
                "kwargs": {"service_id": "silver_scales", "branch_key": "hall"},
            },
        ]
        path = self.write("gap.json", record)
        with self.assertRaises(ImportRejected) as ctx:
            load_batch([path])
        blob = " ".join(
            f"{issue.field} {issue.message}"
            for report in ctx.exception.report.records
            for issue in report.rejections
        )
        self.assertIn("scripted_dialogue", blob)
        self.assertIn("identity", blob)
        self.assertFalse(
            NPC.objects.filter(db_key="blueprint_gap").exists()
        )


class IdentityGateTests(ProfessionAssemblyHarness):
    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_incomplete_identity_rejects_the_batch_before_construction(self):
        record = example_record()
        record["key"] = "identity_gap"
        record["profession"] = "merchant"
        good = example_record()
        good["key"] = "identity_ok"
        good["profession"] = "merchant"
        good["components"] = [
            {"type": "merchant", "kwargs": merchant_kwargs()}
        ]
        bad_path = self.write("bad.json", record)
        good_path = self.write("good.json", good)
        with self.assertRaises(ImportRejected) as ctx:
            load_batch([good_path, bad_path])
        blob = " ".join(
            f"{issue.field} {issue.message}"
            for report in ctx.exception.report.records
            for issue in report.rejections
        )
        self.assertIn("identity", blob)
        self.assertIn("service_id", blob)
        self.assertFalse(
            NPC.objects.filter(db_key__in=["identity_gap", "identity_ok"]).exists()
        )

    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_player_character_target_rejects_the_batch_with_a_named_issue(self):
        record = example_record()
        record["key"] = "pc_profession"
        record["profession"] = "merchant"
        record["components"] = [
            {"type": "merchant", "kwargs": merchant_kwargs()}
        ]
        path = self.write("pc.json", record)
        with self.assertRaises(ImportRejected) as ctx:
            load_batch([path], typeclass=PlayerCharacter)
        blob = " ".join(
            f"{issue.field} {issue.message}"
            for report in ctx.exception.report.records
            for issue in report.rejections
        )
        self.assertIn("PlayerCharacter", blob)
        self.assertFalse(
            PlayerCharacter.objects.filter(db_key="pc_profession").exists()
        )

    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_attach_failure_midway_persists_nothing(self):
        record = example_record()
        record["key"] = "attach_fail"
        record["profession"] = "guild_staff"
        record["components"] = [
            staff_entry(),
            {
                "type": "guild_examiner",
                "kwargs": {"service_id": "silver_scales", "branch_key": "hall"},
            },
            {"type": "scripted_dialogue", "kwargs": {"dialogue_key": "dock"}},
        ]
        path = self.write("fail.json", record)
        from evennia.contrib.base_systems.components.holder import ComponentHandler

        real_add = ComponentHandler.add
        calls = 0

        def fail_second(self, component):
            nonlocal calls
            if component.name not in (
                "guild_staff",
                "guild_examiner",
                "scripted_dialogue",
            ):
                return real_add(self, component)
            calls += 1
            if calls == 2:
                raise RuntimeError("injected attach failure")
            return real_add(self, component)

        with patch.object(ComponentHandler, "add", fail_second):
            with self.assertRaises(RuntimeError):
                load_batch([path])
        self.assertFalse(NPC.objects.filter(db_key="attach_fail").exists())


class TierAndScheduleTests(ProfessionAssemblyHarness):
    @covers_requirement("import-loader::loaded-trait-values-are-the-literal-imported-stats-merged-onto-the-race-floor-for-omitted-keys-never-re-derived-or-multiplied")
    def test_empty_stats_with_a_tiered_row_use_the_tiered_baseline(self):
        record = example_record()
        record["key"] = "tiered_import"
        record["profession"] = "tiered_merchant"
        record["stats"] = {}
        # The disguised-stats cross-check requires every disguised key to also
        # be a literal stat; an empty-stats record carries no disguise.
        record["disguised_stats"] = {}
        record["components"] = [
            {"type": "merchant", "kwargs": merchant_kwargs()}
        ]
        npc = self.assembled(record)
        expected = initial_trait_config("human", "human_commoner", "human_commoner")
        for key, config in expected.items():
            self.assertEqual(getattr(npc.traits, key).base, config["base"], key)

    @covers_requirement("import-loader::loaded-trait-values-are-the-literal-imported-stats-merged-onto-the-race-floor-for-omitted-keys-never-re-derived-or-multiplied")
    def test_literal_stats_beat_any_profession_tier(self):
        record = example_record()
        record["key"] = "tiered_with_literals"
        record["profession"] = "tiered_merchant"
        record["components"] = [
            {"type": "merchant", "kwargs": merchant_kwargs()}
        ]
        npc = self.assembled(record)
        for key, value in record["stats"].items():
            self.assertEqual(getattr(npc.traits, key).base, value, key)

    @covers_requirement("import-loader::a-blueprint-schedule-template-is-applied-to-assembled-npcs-only")
    def test_template_row_schedules_the_assembled_npc(self):
        record = example_record()
        record["key"] = "scheduled_import"
        record["profession"] = "tiered_merchant"
        record["components"] = [
            {"type": "merchant", "kwargs": merchant_kwargs()}
        ]
        npc = self.assembled(record)
        self.assertEqual(npc.db.schedule, {"schema_version": 1, "template": "guard"})
        self.assertTrue(npc.tags.has("schedule"))

    @covers_requirement("import-loader::a-blueprint-schedule-template-is-applied-to-assembled-npcs-only")
    def test_null_template_rows_write_no_schedule(self):
        record = example_record()
        record["key"] = "unscheduled_import"
        record["profession"] = "merchant"
        record["components"] = [
            {"type": "merchant", "kwargs": merchant_kwargs()}
        ]
        npc = self.assembled(record)
        self.assertIsNone(npc.db.schedule)
        self.assertFalse(npc.tags.has("schedule"))


class ByteIdentityTests(ProfessionAssemblyHarness):
    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_absent_profession_constructs_the_frozen_pre_change_state(self):
        # The pin: a shipped-example record through the new loader matches the
        # frozen pre-change seam state (transcribed from master's observable
        # output), and never consults the profession registry at all.
        record = example_record()
        seams = {
            "sex": "female",
            "age": 22,
            "apparent_age": 22,
            "persona": record["persona"],
            "sexual": record["sexual_baseline"],
            "disguised_stats": {"atk_phys": 8, "agility": 9},
            "skills": {"active": record["skills"], "passive": record["passives"]},
            "equipment": record["equipment"],
            "inventory": record["inventory"],
            "portrait_policy": {"mode": "named", "stable_key": "human_reference"},
        }
        with patch.object(
            profession_config,
            "get_profession",
            side_effect=AssertionError("registry consulted without a profession"),
        ):
            npc = self.assembled(record)
        for attribute, expected in seams.items():
            self.assertEqual(npc.attributes.get(attribute), expected, attribute)
        self.assertEqual(npc.key, "human_reference")
        self.assertEqual(npc.race, "human")
        self.assertEqual(npc.subrace, "human_commoner")
        for key, value in record["stats"].items():
            self.assertEqual(getattr(npc.traits, key).base, value, key)
        self.assertIsNone(npc.db.schedule)
        self.assertEqual(list(npc.components.db_names), [])

    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_assembled_npc_emits_one_profession_event(self):
        record = example_record()
        record["key"] = "event_profession"
        record["profession"] = "merchant"
        record["components"] = [
            {"type": "merchant", "kwargs": merchant_kwargs()}
        ]
        path = self.write("event.json", record)
        with patch("world.imports.loader.log_info") as info:
            load_batch([path])
        events = [
            (call.args[0], call.kwargs.get("context"))
            for call in info.call_args_list
        ]
        self.assertIn(
            (
                "import_profession_assembled",
                {
                    "char": "event_profession",
                    "profession": "merchant",
                    "components": ["merchant"],
                },
            ),
            events,
        )
