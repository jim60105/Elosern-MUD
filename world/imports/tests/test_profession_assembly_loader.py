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
COURIER_PROBE = Profession(
    key="courier",
    components=(ProfessionComponent("scripted_dialogue", "person"),),
    schedule_template=None,
    default_tier=None,
)
PROBE_TABLE = MappingProxyType(
    {
        probe.key: probe
        for probe in (MERCHANT_PROBE, STAFF_PROBE, TIERED_PROBE, COURIER_PROBE)
    }
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
        # The probe professions are place-bound (mirroring the shipped
        # rulebook), so every assembled record must name an anchor room the
        # loader can resolve by tag (service-anchoring D8).
        from evennia.utils.create import create_object
        from typeclasses.rooms import Room

        self.anchor_room = create_object(
            Room, key="assembly anchor", tags=["assembly_anchor"]
        )

    def write(self, name, record):
        # Every place-bound probe needs its anchor tag to pass the
        # binding-consistency validator; the injection spares every other
        # test. Anchor-focused tests use raw_write to author records verbatim.
        if record.get("profession") and "anchor_room" not in record:
            record["anchor_room"] = "assembly_anchor"
        return self.raw_write(name, record)

    def raw_write(self, name, record):
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

    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_later_record_failure_emits_no_assembly_event_for_earlier_success(self):
        # The assembly event is commit-bound: a second record failing during
        # construction rolls the whole batch back, and a success event must
        # never describe an NPC that was never persisted.
        first = example_record()
        first["key"] = "rollback_first"
        first["profession"] = "merchant"
        first["components"] = [{"type": "merchant", "kwargs": merchant_kwargs()}]
        second = example_record()
        second["key"] = "rollback_second"
        first_path = self.write("first.json", first)
        second_path = self.write("second.json", second)
        from world.imports import loader

        real = loader._instantiate_validated_character
        calls = 0

        def fail_second(record, typeclass, profession_row=None):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected construction failure")
            return real(record, typeclass, profession_row)

        with (
            patch.object(loader, "_instantiate_validated_character", fail_second),
            patch("world.imports.loader.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(RuntimeError):
                load_batch([first_path, second_path])
        events = [call.args[0] for call in info.call_args_list]
        self.assertNotIn("import_profession_assembled", events)
        self.assertFalse(
            NPC.objects.filter(db_key__in=["rollback_first", "rollback_second"]).exists()
        )

    @covers_requirement("import-loader::a-profession-bearing-npc-record-assembles-blueprint-components-with-explicit-precedence")
    def test_construction_never_reconsults_the_registry_after_validation(self):
        # The loader assembles from the validator's resolved row snapshot: any
        # registry read after the validation lookup would let a rulebook
        # reload mix two rows inside one constructed NPC.
        record = example_record()
        record["key"] = "snapshot_import"
        record["profession"] = "tiered_merchant"
        record["components"] = [{"type": "merchant", "kwargs": merchant_kwargs()}]
        path = self.write("snap.json", record)
        seen: list[str] = []
        real = profession_config.get_profession

        def counted(key):
            seen.append(key)
            if len(seen) > 1:
                raise AssertionError(
                    "registry re-consulted after the validation lookup"
                )
            return real(key)

        with patch.object(profession_config, "get_profession", counted):
            npc = load_batch([path])[0]
        self.assertEqual(seen, ["tiered_merchant"])
        # The constructed state came from the validated row itself.
        self.assertEqual(npc.db.schedule, {"schema_version": 1, "template": "guard"})
        self.assertTrue(npc.components.has("merchant"))


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
            "affinity_elements": ["fire", "wind"],
            "skill_proficiency": {},
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
        self.assertEqual(npc.npc_title, "參考範例")
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
        with patch("world.imports.loader.log_info") as info, (
            self.captureOnCommitCallbacks(execute=True)
        ):
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

class AnchorRoomTests(ProfessionAssemblyHarness):
    """Authored anchor matrix for import records (service-anchoring D8)."""

    def _merchant_record(self, key):
        record = example_record()
        record["key"] = key
        record["profession"] = "merchant"
        record["components"] = [{"type": "merchant", "kwargs": merchant_kwargs()}]
        return record

    def _courier_record(self, key):
        record = example_record()
        record["key"] = key
        record["profession"] = "courier"
        record["components"] = [
            {"type": "scripted_dialogue", "kwargs": {"dialogue_key": "dock"}}
        ]
        return record

    def _rejection_blob(self, record, name):
        path = self.raw_write(name, record)
        with self.assertRaises(ImportRejected) as ctx:
            load_batch([path])
        return " ".join(
            f"{issue.field} {issue.message}"
            for report in ctx.exception.report.records
            for issue in report.rejections
        )

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_place_bound_import_persists_the_resolved_anchor(self):
        record = self._merchant_record("anchored_merchant")
        npc = self.assembled(record)
        component = npc.components.get("merchant")
        self.assertEqual(component.service_binding, "place")
        self.assertEqual(component.anchor_room_id, self.anchor_room.pk)

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_person_bound_import_needs_no_anchor(self):
        # The courier plan is person-bound: the harness never injects an
        # anchor for it, and assembly writes binding with no anchor value.
        record = self._courier_record("plain_courier")
        path = self.raw_write("plain.json", record)
        npc = load_batch([path])[0]
        component = npc.components.get("scripted_dialogue")
        self.assertEqual(component.service_binding, "person")
        self.assertIsNone(component.anchor_room_id)

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_person_plan_carrying_an_anchor_is_rejected_before_construction(self):
        # The "person carrying an anchor" invalid combination: rejected at
        # validation (DB-free), before any construction.
        record = self._courier_record("anchored_courier")
        record["anchor_room"] = "assembly_anchor"
        blob = self._rejection_blob(record, "anchored.json")
        self.assertIn("anchor_room", blob)
        self.assertFalse(NPC.objects.filter(db_key="anchored_courier").exists())

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_place_plan_without_an_anchor_is_rejected(self):
        record = self._merchant_record("unanchored_merchant")
        blob = self._rejection_blob(record, "unanchored.json")
        self.assertIn("anchor_room", blob)
        self.assertFalse(NPC.objects.filter(db_key="unanchored_merchant").exists())

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_unresolvable_anchor_tag_aborts_the_batch_naming_the_record(self):
        # Tag EXISTENCE is a load-time fact (validation is DB-free): the tag
        # passes validation and the in-transaction resolution failure aborts
        # the all-or-nothing batch naming the record and the tag.
        record = self._merchant_record("ghost_anchor_merchant")
        record["anchor_room"] = "no_such_room_tag"
        path = self.raw_write("ghost.json", record)
        with self.assertRaises(ValueError) as ctx:
            load_batch([path])
        self.assertIn("ghost_anchor_merchant", str(ctx.exception))
        self.assertIn("no_such_room_tag", str(ctx.exception))
        self.assertFalse(
            NPC.objects.filter(db_key="ghost_anchor_merchant").exists()
        )
