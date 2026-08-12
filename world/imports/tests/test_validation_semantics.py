from tools.spec_traceability import covers_requirement

from unittest import TestCase
from unittest.mock import patch

from world.imports.tests.helpers import example_record
from world.imports.validate import (
    _check_disguised_stats_subset,
    _check_race_subrace,
    _check_skills,
    _check_stats_band,
    collect_degraded_checks,
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

    def test_internal_registry_import_failure_is_not_misreported_as_absent(self):
        error = ModuleNotFoundError("broken dependency")
        error.name = "broken_dependency"
        with patch("world.imports.validate.importlib.import_module", side_effect=error):
            with self.assertRaises(ModuleNotFoundError):
                from world.imports.validate import _resolve_skill_registry

                _resolve_skill_registry()
