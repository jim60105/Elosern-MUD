"""Typeclass-aware compact NPC card validation and loading for imports.

NPC-target imports carry a complete compact card validated semantically and
persisted through the shared NPC persona initializer; PlayerCharacter imports
keep the opaque persona contract (npc-persona-import-cards D1-D3). Card prose
is file-local synthetic text.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from evennia.typeclasses.attributes import Attribute
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import LLMNPC, NPC
from world.imports.loader import ImportRejected, instantiate_character, load_batch
from world.imports.tests.helpers import example_record
from world.imports.validate import main, validate_batch, validate_character
from world.lore.npc_card import NpcCardError
from world.rules.npc_persona import NpcPersonaSnapshot, read_npc_persona


def synthetic_card(**overrides):
    """A complete, already-normalized synthetic compact card."""
    card = {
        "identity": {"public": "合成測試用的旅人。", "hidden": ""},
        "appearance": "合成外觀描述。",
        "personality": "合成性格描述。",
        "speech_style": "合成說話風格。",
        "life_story": "合成人生經歷。",
        "habit": "合成習慣。",
        "social_connection": "",
    }
    card.update(overrides)
    return card


def npc_record(key="synthetic_card_npc", **card_overrides):
    record = example_record()
    record["key"] = key
    record["persona"] = synthetic_card(**card_overrides)
    return record


def persona_issues(report):
    return [
        issue
        for issue in report.rejections
        if issue.field == "persona" or issue.field.startswith("persona.")
    ]


class BatchFiles:
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


class NpcCardValidationTests(BatchFiles, EvenniaTestCase):
    @covers_requirement("import-validation::npc-target-imports-validate-a-complete-compact-card")
    def test_partial_persona_is_rejected_by_leaf_and_batch_loads_nothing(self):
        record = npc_record()
        del record["persona"]["speech_style"]
        report = validate_character(record)
        issues = persona_issues(report)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].field, "persona.speech_style")
        self.assertTrue(issues[0].message.startswith("missing_field"))

        good = self.write("good.json", npc_record(key="synthetic_good_npc"))
        bad = self.write("bad.json", record)
        batch = validate_batch([good, bad])
        self.assertFalse(batch.all_valid)
        with self.assertRaises(ImportRejected):
            load_batch([good, bad])
        self.assertFalse(
            NPC.objects.filter_family(
                db_key__in=["synthetic_good_npc", "synthetic_card_npc"]
            ).exists()
        )

    @covers_requirement("import-validation::npc-target-imports-validate-a-complete-compact-card")
    def test_background_key_is_an_unknown_field(self):
        record = npc_record()
        record["persona"]["background"] = "合成背景。"
        issues = persona_issues(validate_character(record, NPC))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].field, "persona.background")
        self.assertTrue(issues[0].message.startswith("unknown_field"))

    def test_card_wide_and_identity_reasons_name_their_paths(self):
        too_long = npc_record(
            **{
                key: "長" * 400
                for key in ("appearance", "personality", "speech_style", "life_story", "habit")
            }
        )
        issues = persona_issues(validate_character(too_long))
        self.assertEqual([issue.field for issue in issues], ["persona"])
        self.assertTrue(issues[0].message.startswith("card_too_long"))

        blank_public = npc_record(identity={"public": "  ", "hidden": ""})
        issues = persona_issues(validate_character(blank_public))
        self.assertEqual([issue.field for issue in issues], ["persona.identity.public"])
        self.assertTrue(issues[0].message.startswith("required_empty"))

    @covers_requirement("import-validation::npc-target-imports-validate-a-complete-compact-card")
    def test_player_target_keeps_an_opaque_persona(self):
        record = example_record()
        record["persona"] = {
            "background": "合成背景。",
            "anything": [1, {"nested": None}],
        }
        report = validate_character(record, PlayerCharacter)
        self.assertEqual(persona_issues(report), [])
        self.assertEqual(report.record["persona"], record["persona"])

    @covers_requirement("import-validation::npc-target-imports-validate-a-complete-compact-card")
    def test_validated_record_carries_the_normalized_card(self):
        record = npc_record(
            appearance="  合成外觀\r\n第二行  ",
            habit="合成習慣\r第二行",
            identity={"public": " 合成身分 ", "hidden": "\r\n"},
        )
        raw_persona = json.loads(json.dumps(record["persona"]))
        report = validate_character(record)
        self.assertTrue(report.is_valid, report.rejections)
        persona = report.record["persona"]
        self.assertEqual(persona["appearance"], "合成外觀\n第二行")
        self.assertEqual(persona["habit"], "合成習慣\n第二行")
        self.assertEqual(persona["identity"], {"public": "合成身分", "hidden": ""})
        # The caller's raw record is never mutated by normalization.
        self.assertEqual(record["persona"], raw_persona)

    @covers_requirement("import-validation::npc-target-imports-validate-a-complete-compact-card")
    def test_npc_subclass_target_applies_the_card_contract(self):
        record = npc_record()
        del record["persona"]["habit"]
        issues = persona_issues(validate_character(record, LLMNPC))
        self.assertEqual([issue.field for issue in issues], ["persona.habit"])

    def test_failed_card_leaves_the_lineage_normalized_record(self):
        record = npc_record()
        record["persona"]["habit"] = 7
        report = validate_character(record)
        self.assertFalse(report.is_valid)
        self.assertEqual(report.record["persona"], record["persona"])

    def test_cli_default_target_reports_the_leaf(self):
        record = npc_record()
        del record["persona"]["speech_style"]
        path = self.write("partial.json", record)
        with patch("builtins.print") as printed:
            self.assertEqual(main([str(path)]), 1)
        output = printed.call_args.args[0]
        self.assertIn("REJECT persona.speech_style: missing_field", output)


class NpcCardLoaderTests(BatchFiles, EvenniaTestCase):
    @covers_requirement("import-loader::non-trait-record-fields-are-stored-verbatim-into-the-seam-attributes-without-interpretation")
    def test_npc_import_persists_the_validated_card_with_metadata(self):
        record = npc_record(personality="  合成性格  ")
        npc = instantiate_character(record)
        snapshot = read_npc_persona(npc)
        self.assertIsInstance(snapshot, NpcPersonaSnapshot)
        self.assertEqual(npc.db.persona, synthetic_card(personality="合成性格"))
        self.assertEqual(snapshot.card.to_record(), npc.db.persona)
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(
            snapshot.provenance, {"kind": "import", "record": "synthetic_card_npc"}
        )

    @covers_requirement("import-loader::non-trait-record-fields-are-stored-verbatim-into-the-seam-attributes-without-interpretation")
    def test_later_failure_rolls_back_the_first_card_and_metadata(self):
        first = self.write("first.json", npc_record(key="synthetic_first_npc"))
        second = self.write("second.json", npc_record(key="synthetic_second_npc"))
        from world.imports import loader

        real_construct = loader._instantiate_validated_character
        built = []

        def fail_second(record, typeclass, *args):
            if built:
                raise RuntimeError("injected construction failure")
            entity = real_construct(record, typeclass, *args)
            built.append(entity.pk)
            return entity

        with patch(
            "world.imports.loader._instantiate_validated_character",
            side_effect=fail_second,
        ), self.assertRaises(RuntimeError):
            load_batch([first, second])
        self.assertEqual(len(built), 1)
        self.assertFalse(
            NPC.objects.filter_family(
                db_key__in=["synthetic_first_npc", "synthetic_second_npc"]
            ).exists()
        )
        self.assertFalse(
            Attribute.objects.filter(
                objectdb__id=built[0],
                db_key__in=["persona", "npc_persona_meta"],
            ).exists()
        )

        # A clean reload of the same keys with different card text yields a
        # fresh version-1 card: nothing from the rolled-back batch leaks.
        retry = self.write(
            "retry.json",
            npc_record(key="synthetic_first_npc", habit="重試後的合成習慣。"),
        )
        (npc,) = load_batch([retry])
        snapshot = read_npc_persona(npc)
        self.assertIsInstance(snapshot, NpcPersonaSnapshot)
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(snapshot.card.habit, "重試後的合成習慣。")
        self.assertEqual(npc.db.persona["habit"], "重試後的合成習慣。")

    @covers_requirement("import-loader::non-trait-record-fields-are-stored-verbatim-into-the-seam-attributes-without-interpretation")
    def test_npc_subclass_import_is_initialized_with_import_provenance(self):
        npc = instantiate_character(npc_record(key="synthetic_llm_npc"), LLMNPC)
        self.assertIsInstance(npc, LLMNPC)
        snapshot = read_npc_persona(npc)
        self.assertIsInstance(snapshot, NpcPersonaSnapshot)
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(
            snapshot.provenance, {"kind": "import", "record": "synthetic_llm_npc"}
        )

    def test_single_record_entry_rejects_a_bad_card_and_creates_nothing(self):
        record = npc_record(key="synthetic_single_bad")
        record["persona"]["speech_style"] = "   "
        with self.assertRaises(ImportRejected) as ctx:
            instantiate_character(record)
        (report,) = ctx.exception.report.records
        self.assertEqual(
            [issue.field for issue in persona_issues(report)],
            ["persona.speech_style"],
        )
        self.assertFalse(
            NPC.objects.filter_family(db_key="synthetic_single_bad").exists()
        )

    @covers_requirement("import-loader::non-trait-record-fields-are-stored-verbatim-into-the-seam-attributes-without-interpretation")
    def test_player_import_stores_arbitrary_persona_verbatim_without_metadata(self):
        record = example_record()
        record["key"] = "synthetic_player_import"
        record["persona"] = {"background": "合成背景。", "anything": [1, {"nested": None}]}
        entity = instantiate_character(record, PlayerCharacter)
        self.assertIsInstance(entity, PlayerCharacter)
        self.assertEqual(entity.db.persona, record["persona"])
        self.assertFalse(entity.attributes.has("npc_persona_meta"))

    def test_internal_seam_rejects_a_non_card_before_construction(self):
        from world.imports.loader import _instantiate_validated_character

        record = npc_record(key="synthetic_seam_npc")
        record["persona"] = {"identity": "舊格式的單行身分。"}
        with self.assertRaises(NpcCardError):
            _instantiate_validated_character(record, NPC)
        self.assertFalse(
            NPC.objects.filter_family(db_key="synthetic_seam_npc").exists()
        )
