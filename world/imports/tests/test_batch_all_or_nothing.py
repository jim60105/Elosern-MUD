from tools.spec_traceability import covers_requirement

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.imports.loader import ImportRejected, instantiate_character, load_batch
from world.imports.tests.helpers import EXAMPLE_PATH, example_record
from world.imports.validate import main, validate_batch


class BatchFileHarness:
    """Temp-dir record writer shared by the batch-facing test classes."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()
        super().tearDown()

    def write(self, name, record):
        path = self.root / name
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return path


class BatchTests(BatchFileHarness, EvenniaTestCase):
    @covers_requirement("import-validation::import-validation-is-all-or-nothing-across-a-batch-of-files")
    @covers_requirement("import-validation::every-reported-issue-names-the-record-the-field-and-the-reason", "import-validation::validate-py-provides-a-cli-that-validates-one-or-more-record-files")
    def test_one_bad_record_fails_batch_but_reports_every_file(self):
        bad = example_record()
        bad["age"] = 17
        bad_path = self.write("bad.json", bad)
        report = validate_batch([EXAMPLE_PATH, bad_path])
        self.assertFalse(report.all_valid)
        self.assertEqual(len(report.records), 2)
        self.assertEqual(main([str(EXAMPLE_PATH), str(bad_path)]), 1)

    def test_rejected_batch_constructs_nothing_and_carries_report(self):
        bad = example_record()
        bad["age"] = 17
        bad_path = self.write("bad.json", bad)
        with patch("world.imports.loader._instantiate_validated_character") as instantiate:
            with self.assertRaises(ImportRejected) as ctx:
                load_batch([EXAMPLE_PATH, bad_path])
        instantiate.assert_not_called()
        self.assertEqual(len(ctx.exception.report.records), 2)

    def test_valid_mixed_batch_constructs_only_characters(self):
        world_path = self.write(
            "world.json",
            {
                "record_type": "world_entry",
                "schema_version": 1,
                "key": "tavern",
                "content": "A quiet tavern.",
            },
        )
        entities = load_batch([EXAMPLE_PATH, world_path])
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].key, "human_reference")

    def test_duplicate_world_keys_reject_every_duplicate(self):
        world = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": "duplicate",
            "content": "First.",
        }
        first = self.write("first.json", world)
        world["content"] = "Second."
        second = self.write("second.json", world)
        report = validate_batch([first, second])
        self.assertFalse(report.all_valid)
        self.assertTrue(all(item.rejections for item in report.records))

    @covers_requirement("import-loader::loader-py-instantiates-entities-only-after-batch-validation-reports-zero-rejections")
    def test_construction_failure_rolls_back_earlier_entities(self):
        second = example_record()
        second["key"] = "second_reference"
        second_path = self.write("second.json", second)
        from world.imports import loader

        real_construct = loader._instantiate_validated_character
        calls = 0

        def fail_second(record, typeclass, *args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected construction failure")
            return real_construct(record, typeclass, *args)

        with patch(
            "world.imports.loader._instantiate_validated_character",
            side_effect=fail_second,
        ), self.assertRaises(RuntimeError):
            load_batch([EXAMPLE_PATH, second_path])
        self.assertFalse(NPC.objects.filter(db_key__in=["human_reference", "second_reference"]).exists())

    def test_world_key_with_report_words_is_still_detected_as_duplicate(self):
        world = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": "x in batch",
            "content": "First.",
        }
        first = self.write("phrase-first.json", world)
        world["content"] = "Second."
        second = self.write("phrase-second.json", world)
        self.assertFalse(validate_batch([first, second]).all_valid)

    def test_unhashable_invalid_world_key_reports_schema_error_without_crashing(self):
        world = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": ["not", "hashable"],
            "content": "Invalid.",
        }
        path = self.write("unhashable.json", world)
        report = validate_batch([path])
        self.assertFalse(report.all_valid)

    @covers_requirement("import-validation::batch-import-rejects-duplicate-character-keys")
    def test_duplicate_character_keys_fail_the_whole_batch(self):
        first = example_record()
        first_path = self.write("first.json", first)
        second = example_record()
        second["key"] = first["key"]
        second_path = self.write("second.json", second)
        report = validate_batch([first_path, second_path])
        self.assertFalse(report.all_valid)
        self.assertTrue(all(item.rejections for item in report.records))
        with patch("world.imports.loader._instantiate_validated_character") as instantiate:
            with self.assertRaises(ImportRejected):
                load_batch([first_path, second_path])
        instantiate.assert_not_called()

    @covers_requirement("import-validation::batch-import-rejects-duplicate-character-keys")
    def test_unique_character_keys_pass_the_uniqueness_check(self):
        first = example_record()
        first_path = self.write("first.json", first)
        second = example_record()
        second["key"] = "second_reference"
        second_path = self.write("second.json", second)
        report = validate_batch([first_path, second_path])
        self.assertTrue(report.all_valid)
        self.assertEqual(
            [record["key"] for record in report.character_records],
            ["human_reference", "second_reference"],
        )


class ExistingNpcNameGateTests(BatchFileHarness, EvenniaTestCase):
    """npc-title-import-pipeline: the import face keeps NPC names world-unique."""

    def _existing(self, key, typeclass=NPC, **attrs):
        from evennia.utils.create import create_object

        entity = create_object(typeclass, key=key)
        for name, value in attrs.items():
            entity.attributes.add(name, value)
        return entity

    def _colliding_pair(self):
        first = self.write("first.json", example_record())
        collide = example_record()
        collide["key"] = "塞提斯門衛"
        second = self.write("second.json", collide)
        return first, second

    @covers_requirement("npc-identity-titles::the-import-face-rejects-a-name-already-used-by-an-existing-npc")
    def test_existing_npc_collision_fails_the_whole_batch(self):
        keeper = self._existing("塞提斯門衛", npc_title="南門守衛")
        first, second = self._colliding_pair()
        with patch("world.imports.loader._instantiate_validated_character") as instantiate:
            with self.assertRaises(ImportRejected) as ctx:
                load_batch([first, second])
        instantiate.assert_not_called()
        colliding = next(r for r in ctx.exception.report.records if r.key == "塞提斯門衛")
        self.assertTrue(
            any(i.field == "key" and "existing NPC" in i.message for i in colliding.rejections)
        )
        self.assertFalse(NPC.objects.filter(db_key="human_reference").exists())
        keeper.refresh_from_db()
        self.assertEqual(keeper.key, "塞提斯門衛")
        self.assertEqual(keeper.attributes.get("npc_title"), "南門守衛")

    @covers_requirement("npc-identity-titles::the-import-face-rejects-a-name-already-used-by-an-existing-npc")
    def test_existing_llmnpc_collision_is_rejected_too(self):
        from typeclasses.npcs import LLMNPC

        self._existing("塞提斯門衛", typeclass=LLMNPC)
        first, second = self._colliding_pair()
        with self.assertRaises(ImportRejected) as ctx:
            load_batch([first, second])
        self.assertTrue(
            any(
                i.field == "key"
                for r in ctx.exception.report.records
                for i in r.rejections
            )
        )
        self.assertEqual(NPC.objects.filter_family(db_key="塞提斯門衛").count(), 1)

    def test_gate_applies_to_player_character_target(self):
        self._existing("塞提斯門衛")
        first, second = self._colliding_pair()
        with self.assertRaises(ImportRejected) as ctx:
            load_batch([first, second], typeclass=PlayerCharacter)
        colliding = next(r for r in ctx.exception.report.records if r.key == "塞提斯門衛")
        self.assertTrue(
            any(i.field == "key" and "existing NPC" in i.message for i in colliding.rejections),
            colliding.rejections,
        )

    def test_non_npc_key_holder_does_not_reject(self):
        from evennia.utils.create import create_object  # noqa: I001
        from typeclasses.monsters import Monster
        from typeclasses.objects import Object
        from typeclasses.rooms import Room

        for other in (PlayerCharacter, Monster, Room, Object):
            with self.subTest(other=other.__name__):
                holder = create_object(other, key="塞提斯門衛")
                first, second = self._colliding_pair()
                entities = load_batch([first, second])
                self.assertEqual({entity.key for entity in entities}, {"human_reference", "塞提斯門衛"})
                holder.delete()
                for entity in entities:
                    entity.delete()

    def test_batch_internal_duplicates_reject_before_the_gate(self):
        first = example_record()
        first_path = self.write("first.json", first)
        second = example_record()
        second["key"] = first["key"]
        second_path = self.write("second.json", second)
        with patch("world.imports.loader._instantiate_validated_character") as instantiate:
            with self.assertRaises(ImportRejected) as ctx:
                load_batch([first_path, second_path])
        instantiate.assert_not_called()
        # They fail on the PRE-EXISTING batch-internal grounds, not the new
        # gate: the stable duplicate-key message from _flag_duplicate_keys.
        for record_report in ctx.exception.report.records:
            self.assertTrue(
                any(
                    i.field == "key" and "duplicate character key" in i.message
                    for i in record_report.rejections
                ),
                record_report.rejections,
            )

    def test_duplicate_keys_colliding_with_existing_npc_still_reject(self):
        self._existing("human_reference")
        first_path = self.write("first.json", example_record())
        second = example_record()
        second["key"] = "human_reference"
        second_path = self.write("second.json", second)
        with patch("world.imports.loader._instantiate_validated_character") as instantiate:
            with self.assertRaises(ImportRejected) as ctx:
                load_batch([first_path, second_path])
        instantiate.assert_not_called()
        # Both grounds coexist: batch-internal duplication is detected at
        # validate time, so every report fails there before the gate is ever
        # consulted (the gate never constructs anything either way).
        for record_report in ctx.exception.report.records:
            self.assertTrue(
                any(
                    i.field == "key" and "duplicate character key" in i.message
                    for i in record_report.rejections
                ),
                record_report.rejections,
            )

    @covers_requirement("npc-identity-titles::the-offline-validation-cli-stays-a-file-scope-check-with-no-database-access")
    def test_cli_validates_a_colliding_file_cleanly_but_load_rejects(self):
        self._existing("塞提斯門衛")
        collide = example_record()
        collide["key"] = "塞提斯門衛"
        path = self.write("collide.json", collide)
        report = validate_batch([path])
        self.assertTrue(report.all_valid)
        self.assertEqual(report.degraded_checks, [])
        self.assertEqual(main([str(path)]), 0)
        with self.assertRaises(ImportRejected):
            load_batch([path])

    def test_single_record_entry_rejects_a_collision(self):
        keeper = self._existing("塞提斯門衛", npc_title="南門守衛")
        record = example_record()
        record["key"] = "塞提斯門衛"
        with self.assertRaises(ImportRejected) as ctx:
            instantiate_character(record)
        self.assertTrue(
            any(i.field == "key" for r in ctx.exception.report.records for i in r.rejections)
        )
        self.assertEqual(NPC.objects.filter_family(db_key="塞提斯門衛").count(), 1)
        keeper.refresh_from_db()
        self.assertEqual(keeper.attributes.get("npc_title"), "南門守衛")

    def test_single_record_entry_builds_on_a_clear_name(self):
        entity = instantiate_character(example_record())
        self.assertEqual(entity.key, "human_reference")


class ImportBoundaryEventTests(BatchFileHarness, EvenniaTestCase):
    """npc-title-import-pipeline: the commit/reject boundary leaves a trace."""

    @covers_requirement("npc-identity-titles::the-import-boundary-emits-commit-and-rejection-events")
    def test_committed_batch_emits_exactly_one_info_with_context(self):
        # Distinct keys per subtest: both subtests share one atomic block, and
        # the first-loaded NPC would otherwise be a legitimate gate collision.
        for target, name in ((None, "NPC"), (PlayerCharacter, "PlayerCharacter")):
            with self.subTest(target=name):
                record = example_record()
                record["key"] = f"events_{name}"
                path = self.write(f"events-{name}.json", record)
                with patch("world.imports.loader.log_info") as info, patch(
                    "world.imports.loader.log_warn"
                ) as warn:
                    # The batch's atomic block never really commits inside the
                    # test transaction, so on_commit callbacks (the profession
                    # assembly event) must be captured to run.
                    with self.captureOnCommitCallbacks(execute=True):
                        kwargs = {} if target is None else {"typeclass": target}
                        load_batch([path], **kwargs)
                info.assert_called_once_with(
                    "import_batch_committed",
                    context={"records": 1, "typeclass": name},
                )
                warn.assert_not_called()

    def test_construction_failure_after_gate_emits_no_commit_event(self):
        with patch(
            "world.imports.loader._instantiate_validated_character",
            side_effect=RuntimeError("injected"),
        ), patch("world.imports.loader.log_info") as info:
            with self.assertRaises(RuntimeError):
                load_batch([EXAMPLE_PATH])
        info.assert_not_called()

    def test_validation_rejection_warns_with_reason(self):
        bad = example_record()
        bad["age"] = 17
        bad_path = self.write("bad.json", bad)
        with patch("world.imports.loader.log_info") as info, patch(
            "world.imports.loader.log_warn"
        ) as warn:
            with self.assertRaises(ImportRejected):
                load_batch([EXAMPLE_PATH, bad_path])
        warn.assert_called_once()
        event, context = warn.call_args.args[0], warn.call_args.kwargs["context"]
        self.assertEqual(event, "import_batch_rejected")
        self.assertEqual(context["reason"], "validation")
        self.assertEqual(context["typeclass"], "NPC")
        self.assertEqual(context["records"], 2)
        self.assertEqual(context["rejected"], 1)
        info.assert_not_called()

    @covers_requirement("npc-identity-titles::the-import-boundary-emits-commit-and-rejection-events")
    def test_name_collision_rejection_warns_with_reason(self):
        from evennia.utils.create import create_object

        create_object(NPC, key="塞提斯門衛")
        collide = example_record()
        collide["key"] = "塞提斯門衛"
        path = self.write("collide.json", collide)
        with patch("world.imports.loader.log_info") as info, patch(
            "world.imports.loader.log_warn"
        ) as warn:
            with self.assertRaises(ImportRejected):
                load_batch([path])
        warn.assert_called_once()
        context = warn.call_args.kwargs["context"]
        self.assertEqual(context["reason"], "existing_npc_name")
        self.assertEqual(context["typeclass"], "NPC")
        self.assertEqual(context["rejected"], 1)
        info.assert_not_called()

    def test_single_record_entries_warn_at_both_rejection_sites(self):
        bad = example_record()
        del bad["title"]
        with patch("world.imports.loader.log_warn") as warn:
            with self.assertRaises(ImportRejected):
                instantiate_character(bad)
        self.assertEqual(warn.call_args.kwargs["context"]["reason"], "validation")
        self.assertEqual(warn.call_args.kwargs["context"]["typeclass"], "NPC")
        from evennia.utils.create import create_object

        create_object(NPC, key="塞提斯門衛")
        collide = example_record()
        collide["key"] = "塞提斯門衛"
        with patch("world.imports.loader.log_warn") as warn:
            with self.assertRaises(ImportRejected):
                instantiate_character(collide)
        self.assertEqual(warn.call_args.kwargs["context"]["reason"], "existing_npc_name")

    def test_single_record_success_emits_one_info(self):
        with patch("world.imports.loader.log_info") as info, (
            self.captureOnCommitCallbacks(execute=True)
        ):
            instantiate_character(example_record())
        info.assert_called_once_with(
            "import_batch_committed",
            context={"records": 1, "typeclass": "NPC"},
        )
