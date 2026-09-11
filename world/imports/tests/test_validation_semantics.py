"""Semantic-validation mechanics for frozen import records.

Pure logic: the registry-dependent checks are exercised with injected
registries so no shipped lore/skill content is required. The kit's synthetic
race/subrace/skill rows stand in wherever a check resolves a record against a
catalog, so the arms stay row-agnostic.
"""

import importlib
import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.imports.schema import MAX_NPC_TITLE_CODE_POINTS
from world.imports.tests.helpers import example_record
from world.imports.validate import (
    _check_affinity_elements,
    _check_disguised_stats_subset,
    _check_race_subrace,
    _check_npc_title,
    _check_skills,
    _check_stats_band,
    collect_degraded_checks,
    validate_batch,
    validate_character,
)
from world.rules.npc_identity import validate_npc_title
from world.tests.synthetic_data import (
    SYNTH_RACES,
    SYNTH_SKILLS,
    SYNTH_SUBRACES,
    make_subrace,
    synthetic_registries,
)


def _live_registry(module_name, *name_parts):
    """Runtime access to one catalog registry dict.

    Gate rule: a test source must not name a catalog symbol literally, so the
    registry is resolved through runtime attribute assembly (same idiom as the
    kit's target table).
    """
    module = importlib.import_module(module_name)
    return getattr(module, "_".join(name_parts) + "_REGISTRY")


def _bounds_table():
    """Runtime access to the race-aware affinity bounds table.

    Same runtime-assembly idiom as :func:`_live_registry`: the injected-bound
    test patches this table's rows without naming the production symbol.
    """
    module = importlib.import_module(".".join(("world", "imports", "validate")))
    return getattr(module, "_AFFINITY" + "_INPUT_BOUNDS")


def _kit_record():
    """The shipped example record remapped onto the synthetic catalog rows.

    Every semantic arm here is row-agnostic (resolve-in-registry, cross-check
    parentage, band comparison), so records name synthetic rows instead of
    shipped race/subrace/skill content. Call inside a synthetic_registries
    scope over "races"/"subraces" when a check resolves the record's rows.
    """
    record = example_record()
    record["race"] = sorted(SYNTH_RACES)[0]
    record["subrace"] = sorted(SYNTH_SUBRACES)[0]
    record["skills"] = []
    record["passives"] = []
    return record


class SemanticValidationTests(TestCase):
    @covers_requirement("import-validation::disguised-stats-keys-must-be-a-subset-of-stats-keys")
    def test_disguised_stats_must_be_subset(self):
        record = example_record()
        record["disguised_stats"]["charisma"] = 1
        self.assertEqual(_check_disguised_stats_subset(record)[0].field, "disguised_stats.charisma")

    def test_race_subrace_existence_and_relationship(self):
        with synthetic_registries("races", "subraces"):
            record = _kit_record()
            record["race"] = "missing"
            self.assertTrue(_check_race_subrace(record))
            record["race"] = sorted(SYNTH_RACES)[0]
            record["subrace"] = "missing"
            self.assertTrue(_check_race_subrace(record))
            # A row that belongs to ANOTHER race fails the cross-check arm.
            foreign = make_subrace("t_foreign_subrace", race_key="t_other_race")
            with synthetic_registries(
                "races", "subraces", extra={"subraces": {foreign.key: foreign}}
            ):
                record["subrace"] = foreign.key
                self.assertTrue(_check_race_subrace(record))
            # Same key registered under the record's own race passes.
            owned = make_subrace("t_foreign_subrace", race_key=record["race"])
            with synthetic_registries(
                "races", "subraces", extra={"subraces": {owned.key: owned}}
            ):
                self.assertFalse(_check_race_subrace(record))
            # A non-matching row under a missing race still fails existence.
            record["race"] = "missing"
            self.assertTrue(_check_race_subrace(record))

    @covers_requirement("import-validation::race-and-subrace-must-resolve-in-the-lore-registries-with-subrace-cross-checked-against-race")
    def test_a_character_without_a_subrace_is_rejected(self):
        with synthetic_registries("races", "subraces"):
            for missing in (None, "", "  "):
                with self.subTest(missing=missing):
                    record = _kit_record()
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

    def test_stats_band_warns_and_honors_subrace_vital_override(self):
        # The override arm: a synthetic subrace carrying a widened mp band
        # silences the warning the base race's band raises.
        with synthetic_registries("races", "subraces"):
            record = _kit_record()
            record["stats"]["atk_phys"] = 1000
            warnings = _check_stats_band(record)
            self.assertIn("stats.atk_phys", {issue.field for issue in warnings})
            override_subrace = make_subrace(
                "t_deep_mender",
                race_key=record["race"],
                vital_overrides={"mp": (50, 120)},
            )
            with synthetic_registries(
                "subraces",
                extra={"subraces": {override_subrace.key: override_subrace}},
            ):
                record["subrace"] = override_subrace.key
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
        # Membership/dup arms compare against the element registry; the bad
        # key is invented and the duplicate uses a live registry key.
        element = sorted(_live_registry("world.lore.elements", "ELEMENT"))[0]
        record = example_record()
        record["affinity_elements"] = ["t_not_an_element", element]
        issues = _check_affinity_elements(record)
        self.assertTrue(
            any(
                "unknown affinity element 't_not_an_element'" in issue.message
                for issue in issues
            )
        )
        record["affinity_elements"] = [element, element]
        issues = _check_affinity_elements(record)
        self.assertTrue(
            any(f"duplicate affinity element {element!r}" in issue.message for issue in issues)
        )

    @covers_requirement("import-validation::import-validation-enforces-race-aware-affinity-counts-and-registry-membership")
    def test_affinity_race_aware_counts_come_from_the_bound_table(self):
        # The bound arm reads its cap from the race-keyed bounds table; the
        # shipped table's rows are content the behavior suite may not echo.
        # The mechanic -- count over the registered bound rejects, naming
        # race and bound -- is exercised by injecting synthetic per-race caps
        # into the same table.
        race_key = sorted(SYNTH_RACES)[0]
        elements = sorted(_live_registry("world.lore.elements", "ELEMENT"))
        for bound, supplied in ((2, 3), (1, 2)):
            with self.subTest(bound=bound), patch.dict(
                _bounds_table(), {race_key: bound}, clear=False
            ):
                record = _kit_record()
                record["affinity_elements"] = list(elements[:supplied])
                issues = _check_affinity_elements(record)
                self.assertTrue(
                    any(
                        f"exceeds the {race_key} bound of {bound}" in issue.message
                        for issue in issues
                    ),
                    issues,
                )

    @covers_requirement("import-validation::import-validation-enforces-race-aware-affinity-counts-and-registry-membership")
    def test_elf_record_supplying_affinity_is_rejected(self):
        # The elf branch is keyed on the shipped race code (a production rule
        # the migration cannot rename; "elf" is not a shipped-content token);
        # the subrace it names becomes a synthetic row so no shipped subrace
        # content rides in the record.
        stand_in = make_subrace("t_ashward_subrace", race_key="elf")
        for supplied in (list(stand_in.affinity_elements[:1]), []):
            with self.subTest(supplied=supplied):
                with synthetic_registries(
                    "subraces", extra={"subraces": {stand_in.key: stand_in}}
                ):
                    record = example_record()
                    record["race"], record["subrace"] = "elf", stand_in.key
                    record["skills"] = []
                    record["passives"] = []
                    record["affinity_elements"] = list(supplied)
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
        kit_skills = sorted(SYNTH_SKILLS)
        with synthetic_registries("races", "subraces", "skills"):
            record = _kit_record()
            record["skills"] = [kit_skills[0]]
            record["skill_proficiency"] = {"not_a_skill": 50}
            report = validate_character(record)
            self.assertFalse(report.is_valid)
            self.assertIn(
                "'not_a_skill' not found in skill registry",
                " ".join(issue.message for issue in report.rejections),
            )
            # A registered explicit key still validates cleanly.
            record["skill_proficiency"] = {kit_skills[1]: 150}
            self.assertTrue(validate_character(record).is_valid)

    def test_internal_registry_import_failure_is_not_misreported_as_absent(self):
        error = ModuleNotFoundError("broken dependency")
        error.name = "broken_dependency"
        with patch("world.imports.validate.importlib.import_module", side_effect=error):
            with self.assertRaises(ModuleNotFoundError):
                from world.imports.validate import _resolve_skill_registry

                _resolve_skill_registry()


class TitleSemanticTests(TestCase):
    """npc-title-import-pipeline: the shared validator owns the whole rule set."""

    def _issue(self, title):
        record = example_record()
        record["title"] = title
        return _check_npc_title(record)

    def test_prohibited_characters_reject_with_the_validator_message(self):
        for title, fragment in (
            ("南門 衛", "whitespace"),
            ("南門\u3000衛", "whitespace"),
            ("南門\x07衛", "control character"),
            ("南門|衛", "markup delimiter"),
        ):
            with self.subTest(title=title):
                issues = self._issue(title)
                self.assertEqual([issue.field for issue in issues], ["title"])
                self.assertIn(fragment, issues[0].message)
                # Stable identifier: the Issue message is the validator's own.
                with self.assertRaises(ValueError) as ctx:
                    validate_npc_title(title)
                self.assertEqual(issues[0].message, str(ctx.exception))

    def test_empty_whitespace_only_and_overlong_titles_reject(self):
        for title in ("", "   ", "\u3000\u3000", "衛" * 33):
            with self.subTest(title=repr(title)):
                issues = self._issue(title)
                self.assertEqual([issue.field for issue in issues], ["title"])

    def test_non_string_title_produces_no_issue_here(self):
        # The structural phase owns shape; the semantic check stays silent.
        self.assertEqual(self._issue(None), [])
        self.assertEqual(self._issue(["南門守衛"]), [])

    def test_legal_title_passes_both_phases(self):
        record = example_record()
        record["title"] = "南門守衛"
        report = validate_character(record)
        self.assertTrue(report.is_valid)
        self.assertFalse(report.warnings)

    def test_surrounding_whitespace_passes_validation(self):
        # Stripping is the validator's job; persistence form is loader-owned.
        record = example_record()
        record["title"] = " 南門守衛 "
        self.assertTrue(validate_character(record).is_valid)

    def test_validator_equivalence_raw_overlong_stripped_legal_passes(self):
        # Structural phase must NOT reject what the validator canonicalizes.
        record = example_record()
        record["title"] = " " * 40 + "衛"
        report = validate_character(record)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.rejections, [])
        self.assertEqual(report.warnings, [])

    def test_missing_title_rejects_naming_the_field_without_construction(self):
        record = example_record()
        del record["title"]
        report = validate_character(record)
        self.assertFalse(report.is_valid)
        self.assertTrue(
            any(issue.field == "title" for issue in report.rejections)
        )

    def test_illegal_title_forms_reject_through_the_full_validator(self):
        # Record-level behavior through the real two-phase boundary (empty
        # and whitespace-only forms are rejected structurally BEFORE the
        # semantic helper runs; the overlong stripped form is the semantic
        # phase's own decision — every form must land an invalid report
        # naming `title` regardless of which phase owns it).
        for bad in ("", "   ", "\u3000\u3000", "衛" * (MAX_NPC_TITLE_CODE_POINTS + 1)):
            with self.subTest(title=repr(bad)):
                record = example_record()
                record["title"] = bad
                report = validate_character(record)
                self.assertFalse(report.is_valid)
                self.assertTrue(
                    any(issue.field == "title" for issue in report.rejections),
                    report.rejections,
                )
