from tools.spec_traceability import covers_requirement

import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from world.imports.tests.helpers import example_record
from world.imports.validate import (
    _check_affinity_elements,
    _check_disguised_stats_subset,
    _check_race_subrace,
    _check_skills,
    _check_stats_band,
    collect_degraded_checks,
    validate_batch,
    validate_character,
)


class SemanticValidationTests(TestCase):
    @covers_requirement("import-validation::disguised-stats-keys-must-be-a-subset-of-stats-keys")
    def test_disguised_stats_must_be_subset(self):
        record = example_record()
        record["disguised_stats"]["charisma"] = 1
        self.assertEqual(_check_disguised_stats_subset(record)[0].field, "disguised_stats.charisma")

    def test_race_subrace_existence_and_relationship(self):
        record = example_record()
        record["race"] = "missing"
        self.assertTrue(_check_race_subrace(record))
        record["race"], record["subrace"] = "elf", "missing"
        self.assertTrue(_check_race_subrace(record))
        record["subrace"] = "foxkin"
        self.assertTrue(_check_race_subrace(record))

    @covers_requirement("import-validation::race-and-subrace-must-resolve-in-the-lore-registries-with-subrace-cross-checked-against-race")
    def test_a_character_without_a_subrace_is_rejected(self):
        for missing in (None, "", "  "):
            with self.subTest(missing=missing):
                record = example_record()
                record["subrace"] = missing
                errors = _check_race_subrace(record)
                self.assertEqual(len(errors), 1)
                self.assertEqual(errors[0].field, "subrace")
                report = validate_character(record)
                self.assertFalse(report.is_valid)
                self.assertTrue(
                    any(issue.field == "subrace" for issue in report.rejections),
                    report.rejections,
                )

    def test_stats_band_warns_and_honors_foxkin_override(self):
        record = example_record()
        record["stats"]["atk_phys"] = 1000
        warnings = _check_stats_band(record)
        self.assertIn("stats.atk_phys", {issue.field for issue in warnings})
        record["race"], record["subrace"] = "beastfolk", "foxkin"
        record["stats"] = {"mp": 60}
        self.assertFalse(_check_stats_band(record))

    def test_bad_sexual_vocabulary_rejects(self):
        record = example_record()
        record["sexual_baseline"]["arousal"] = "invalid"
        report = validate_character(record)
        self.assertTrue(report.rejections)
        self.assertFalse(report.warnings)

    @covers_requirement("import-validation::key-charset-is-checked-at-import-validation")
    def test_separator_and_overlong_keys_are_structural_rejections(self):
        for bad in ("orc|alpha", "x" * 65):
            with self.subTest(key=bad[:8]):
                record = example_record()
                record["key"] = bad
                report = validate_character(record)
                self.assertFalse(report.is_valid)
                self.assertIn("key", {issue.field for issue in report.rejections})

    @covers_requirement("import-validation::key-charset-is-checked-at-import-validation")
    def test_digit_only_keys_are_structural_rejections_naming_the_reserved_region(self):
        for bad in ("42", "7", "0"):
            with self.subTest(key=bad):
                record = example_record()
                record["key"] = bad
                report = validate_character(record)
                self.assertFalse(report.is_valid)
                self.assertIn("key", {issue.field for issue in report.rejections})
                self.assertIn(
                    "reserved for player characters",
                    " ".join(issue.message for issue in report.rejections),
                )

    @covers_requirement("import-validation::key-charset-is-checked-at-import-validation")
    def test_digit_only_keys_in_a_batch_are_rejected_and_never_instantiated(self):
        bad_character = example_record()
        bad_character["key"] = "42"
        bad_world = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": "7",
            "content": "Numeric world key.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good_path = root / "good.json"
            good_path.write_text(
                json.dumps(example_record(), ensure_ascii=False), encoding="utf-8"
            )
            bad_character_path = root / "bad_character.json"
            bad_character_path.write_text(
                json.dumps(bad_character, ensure_ascii=False), encoding="utf-8"
            )
            bad_world_path = root / "bad_world.json"
            bad_world_path.write_text(
                json.dumps(bad_world, ensure_ascii=False), encoding="utf-8"
            )
            report = validate_batch([good_path, bad_character_path, bad_world_path])
        self.assertFalse(report.all_valid)
        rejected = {item.key for item in report.records if item.rejections}
        self.assertEqual(rejected, {"42", "7"})
        self.assertEqual(
            [record["key"] for record in report.character_records],
            ["human_reference"],
        )

    @covers_requirement("art-stable-key-contract::stable-keys-share-one-producer-contract")
    def test_every_reserved_separator_and_overlong_key_rejects_without_an_entity(self):
        from world.art.subjects import (
            FORBIDDEN_SUBJECT_KEY_CHARACTERS,
            MAX_SUBJECT_KEY_BYTES,
            MAX_SUBJECT_KEY_LENGTH,
        )

        for bad in (
            *(f"a{char}b" for char in sorted(FORBIDDEN_SUBJECT_KEY_CHARACTERS)),
            "x" * (MAX_SUBJECT_KEY_LENGTH + 1),
            # 64 four-byte characters pass the code-point bound but exceed the
            # UTF-8 byte bound that keeps worker filenames within NAME_MAX.
            "😀" * (MAX_SUBJECT_KEY_BYTES // 4 + 1),
        ):
            with self.subTest(key=bad[:8]):
                record = example_record()
                record["key"] = bad
                report = validate_character(record)
                self.assertFalse(report.is_valid)
                self.assertIn("key", {issue.field for issue in report.rejections})

    @covers_requirement("import-validation::key-charset-is-checked-at-import-validation")
    def test_format_and_private_use_characters_in_keys_reject_like_creation(self):
        for bad in ("a\u200b", "a\ue000", "a\ud800"):
            with self.subTest(key=bad[:2]):
                record = example_record()
                record["key"] = bad
                report = validate_character(record)
                self.assertFalse(report.is_valid)
                self.assertIn(
                    "non-printable or control",
                    " ".join(issue.message for issue in report.rejections),
                )

    @covers_requirement("import-validation::the-cli-prints-a-prominent-banner-whenever-any-check-is-running-in-degraded-mode")
    def test_skill_check_degrades_once_at_batch_level(self):
        with patch("world.imports.validate._resolve_skill_registry", return_value=None):
            self.assertFalse(_check_skills({"skills": ["unknown"], "passives": []}))
            self.assertEqual(collect_degraded_checks()[0].name, "skill-registry")

    @covers_requirement("import-validation::race-and-subrace-must-resolve-in-the-lore-registries-with-subrace-cross-checked-against-race", "import-validation::skills-and-passives-use-a-pluggable-registry-with-explicit-degraded-state-reporting")
    def test_skill_check_rejects_unknown_once_registry_exists(self):
        record = {"skills": ["known", "unknown"], "passives": ["passive"]}
        with patch(
            "world.imports.validate._resolve_skill_registry",
            return_value={"known": object(), "passive": object()},
        ):
            issues = _check_skills(record)
        self.assertEqual([issue.message for issue in issues], ["'unknown' not found in skill registry"])

    @covers_requirement("import-validation::import-validation-enforces-race-aware-affinity-counts-and-registry-membership")
    def test_affinity_unknown_and_duplicate_rejected(self):
        record = example_record()
        record["affinity_elements"] = ["luck", "wind"]
        issues = _check_affinity_elements(record)
        self.assertTrue(
            any("unknown affinity element 'luck'" in issue.message for issue in issues)
        )
        record = example_record()
        record["affinity_elements"] = ["fire", "fire"]
        issues = _check_affinity_elements(record)
        self.assertTrue(
            any("duplicate affinity element 'fire'" in issue.message for issue in issues)
        )

    @covers_requirement("import-validation::import-validation-enforces-race-aware-affinity-counts-and-registry-membership")
    def test_affinity_race_aware_counts(self):
        human = example_record()
        human["affinity_elements"] = ["fire", "wind", "water"]
        issues = _check_affinity_elements(human)
        self.assertTrue(
            any("exceeds the human bound of 2" in issue.message for issue in issues)
        )
        beast = example_record()
        beast["race"], beast["subrace"] = "beastfolk", "foxkin"
        beast["affinity_elements"] = ["fire", "wind"]
        issues = _check_affinity_elements(beast)
        self.assertTrue(
            any("exceeds the beastfolk bound of 1" in issue.message for issue in issues)
        )

    @covers_requirement("import-validation::import-validation-enforces-race-aware-affinity-counts-and-registry-membership")
    def test_elf_record_supplying_affinity_is_rejected(self):
        for supplied in (["light"], []):
            with self.subTest(supplied=supplied):
                record = example_record()
                record["race"], record["subrace"] = "elf", "fionnen"
                record["affinity_elements"] = supplied
                issues = _check_affinity_elements(record)
                self.assertTrue(
                    any("subrace-derived" in issue.message for issue in issues)
                )
                report = validate_character(record)
                self.assertFalse(report.is_valid)

    @covers_requirement("import-validation::import-validation-enforces-race-aware-affinity-counts-and-registry-membership")
    def test_record_without_affinity_produces_no_rejection(self):
        record = example_record()
        record.pop("affinity_elements", None)
        self.assertEqual(_check_affinity_elements(record), [])
        report = validate_character(record)
        self.assertTrue(report.is_valid)

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_unregistered_skill_proficiency_key_rejects_the_record(self):
        # Fail-closed: the auto-seed understands registry keys only, so an
        # explicit practice-XP typo must name itself and reject the whole
        # record instead of being dropped or persisted unchecked.
        record = example_record()
        record["skills"] = ["fire_ball"]
        record["skill_proficiency"] = {"not_a_skill": 50}
        report = validate_character(record)
        self.assertFalse(report.is_valid)
        self.assertIn(
            "'not_a_skill' not found in skill registry",
            " ".join(issue.message for issue in report.rejections),
        )
        # A registered explicit key still validates cleanly.
        record["skill_proficiency"] = {"fire_arrow": 150}
        self.assertTrue(validate_character(record).is_valid)

    def test_internal_registry_import_failure_is_not_misreported_as_absent(self):
        error = ModuleNotFoundError("broken dependency")
        error.name = "broken_dependency"
        with patch("world.imports.validate.importlib.import_module", side_effect=error):
            with self.assertRaises(ModuleNotFoundError):
                from world.imports.validate import _resolve_skill_registry

                _resolve_skill_registry()
