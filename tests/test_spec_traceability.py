"""Tests for the OpenSpec requirement traceability verifier."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.spec_traceability import (
    EVIDENCE_ENV,
    covers_requirement,
    parse_requirements,
    verify,
)


@contextmanager
def fixture_repository(spec: str, test: str):
    with TemporaryDirectory() as directory:
        root = Path(directory)
        spec_path = root / "openspec" / "specs" / "sample" / "spec.md"
        test_path = root / "sample" / "tests" / "test_sample.py"
        spec_path.parent.mkdir(parents=True)
        test_path.parent.mkdir(parents=True)
        spec_path.write_text(spec, encoding="utf-8")
        test_path.write_text(test, encoding="utf-8")
        yield root


SPEC = """## Requirements

### Requirement: Useful behavior
The system SHALL work.
"""

ANNOTATED_TEST = """from unittest import TestCase
from tools.spec_traceability import covers_requirement

class SampleTests(TestCase):
    @covers_requirement("sample::useful-behavior")
    def test_behavior(self):
        self.assertTrue(True)
"""


class RequirementParsingTests(unittest.TestCase):
    @covers_requirement(
        "spec-test-traceability::main-spec-requirements-have-deterministic-identities"
    )
    def test_main_specs_are_indexed_and_change_specs_are_excluded(self):
        with fixture_repository(SPEC, "") as root:
            change_spec = root / "openspec" / "changes" / "x" / "specs" / "ignored" / "spec.md"
            change_spec.parent.mkdir(parents=True)
            change_spec.write_text("### Requirement: Ignored\n", encoding="utf-8")
            requirements, errors = parse_requirements(root)
        self.assertFalse(errors)
        self.assertEqual([item.identifier for item in requirements], ["sample::useful-behavior"])

    def test_normalized_collision_reports_both_locations(self):
        spec = "### Requirement: Same name\n### Requirement: Same-name\n"
        with fixture_repository(spec, "") as root:
            requirements, errors = parse_requirements(root)
        self.assertEqual(len(requirements), 1)
        self.assertEqual(errors[0].code, "requirement-id-collision")
        self.assertIn(":1", errors[0].message)


class StaticAnnotationTests(unittest.TestCase):
    @covers_requirement(
        "spec-test-traceability::existing-tests-declare-requirement-coverage-locally"
    )
    def test_valid_literal_annotation_covers_requirement(self):
        with fixture_repository(SPEC, ANNOTATED_TEST) as root:
            report = verify(root)
        self.assertTrue(report.ok)
        self.assertEqual(report.covered, ("sample::useful-behavior",))

    def test_stale_id_is_rejected_and_requirement_is_uncovered(self):
        source = ANNOTATED_TEST.replace("sample::useful-behavior", "sample::old-name")
        with fixture_repository(SPEC, source) as root:
            report = verify(root)
        self.assertEqual(report.errors[0].code, "unknown-requirement-id")
        self.assertEqual(report.uncovered, ("sample::useful-behavior",))

    def test_dynamic_argument_is_rejected(self):
        source = ANNOTATED_TEST.replace(
            '@covers_requirement("sample::useful-behavior")',
            "@covers_requirement(REQUIREMENT_ID)",
        ).replace("class SampleTests", 'REQUIREMENT_ID = "sample::useful-behavior"\n\nclass SampleTests')
        with fixture_repository(SPEC, source) as root:
            report = verify(root)
        self.assertEqual(report.errors[0].code, "dynamic-requirement-id")

    def test_non_test_placement_is_rejected(self):
        source = ANNOTATED_TEST.replace("def test_behavior", "def helper")
        with fixture_repository(SPEC, source) as root:
            report = verify(root)
        self.assertEqual(report.errors[0].code, "invalid-annotation-placement")

    def test_wrong_decorator_import_is_rejected(self):
        source = ANNOTATED_TEST.replace("tools.spec_traceability", "other.module")
        with fixture_repository(SPEC, source) as root:
            report = verify(root)
        self.assertEqual(report.errors[0].code, "invalid-decorator-import")


class RuntimeEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "spec-test-traceability::associated-tests-provide-successful-execution-evidence"
    )
    def test_decorator_preserves_identity_behavior_and_success_evidence(self):
        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.jsonl"

            @covers_requirement("sample::useful-behavior")
            def test_example(value):
                """Original documentation."""
                return value + 1

            with patch.dict(os.environ, {EVIDENCE_ENV: str(evidence)}):
                self.assertEqual(test_example(2), 3)
            record = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(test_example.__name__, "test_example")
        self.assertEqual(test_example.__doc__, "Original documentation.")
        self.assertEqual(record["requirements"], ["sample::useful-behavior"])
        self.assertTrue(record["test"].endswith("RuntimeEvidenceTests.test_decorator_preserves_identity_behavior_and_success_evidence.<locals>.test_example"))

    def test_failing_test_emits_no_evidence(self):
        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.jsonl"

            @covers_requirement("sample::useful-behavior")
            def test_failure():
                raise AssertionError("failure")

            with patch.dict(os.environ, {EVIDENCE_ENV: str(evidence)}):
                with self.assertRaises(AssertionError):
                    test_failure()
            self.assertFalse(evidence.exists())

    def test_skipped_test_emits_no_evidence(self):
        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.jsonl"

            @covers_requirement("sample::useful-behavior")
            @unittest.skip("fixture")
            def test_skip():
                pass

            with patch.dict(os.environ, {EVIDENCE_ENV: str(evidence)}):
                with self.assertRaises(unittest.SkipTest):
                    test_skip()
            self.assertFalse(evidence.exists())

    def test_uncollected_annotation_has_no_matching_evidence(self):
        with fixture_repository(SPEC, ANNOTATED_TEST) as root:
            evidence = root / "evidence.jsonl"
            evidence.write_text("", encoding="utf-8")
            report = verify(root, evidence)
        self.assertEqual(report.uncovered, ("sample::useful-behavior",))

    @covers_requirement(
        "spec-test-traceability::every-current-requirement-is-associated-with-a-test"
    )
    def test_matching_successful_evidence_counts(self):
        with fixture_repository(SPEC, ANNOTATED_TEST) as root:
            evidence = root / "evidence.jsonl"
            evidence.write_text(
                json.dumps(
                    {
                        "test": "sample.tests.test_sample.SampleTests.test_behavior",
                        "requirements": ["sample::useful-behavior"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            report = verify(root, evidence)
        self.assertTrue(report.ok)


if __name__ == "__main__":
    unittest.main()
