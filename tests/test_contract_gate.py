"""The repository contract gate bundles the cheap contracts and CI reuses it."""

from pathlib import Path
import unittest
from unittest.mock import patch

import yaml

from tools import contract_gate


REPO_ROOT = Path(__file__).resolve().parents[1]


class ContractGateTests(unittest.TestCase):
    def test_manifest_structure_errors_are_reported(self):
        self.assertEqual(contract_gate.manifest_errors("evennia-shards", {"shards": []}), ["evennia-shards: manifest declares no shards"])
        self.assertEqual(
            contract_gate.manifest_errors("evennia-shards", {"shards": [{"index": 1, "labels": ["a"]}, {"index": 0, "labels": ["b"]}]}),
            ["evennia-shards: shard indices must be unique and sorted"],
        )
        self.assertEqual(
            contract_gate.manifest_errors("browser-shards", {"shards": [{"index": 0, "files_a": ["x"], "files_b": []}]}),
            ["browser-shards: shard 0 must declare non-empty files_a and files_b"],
        )
        self.assertEqual(
            contract_gate.manifest_errors("browser-shards", {"shards": [{"index": 0, "files_a": ["x"], "files_b": ["y"]}]}),
            [],
        )

    def test_unknown_gate_is_rejected_before_anything_runs(self):
        self.assertEqual(contract_gate.main(["no-such-gate"]), 2)

    def test_change_is_forwarded_only_to_the_traceability_check(self):
        for argv in (["--change", "retire-old", "traceability"], ["traceability", "--change=retire-old"]):
            with self.subTest(argv=argv), patch.object(contract_gate.subprocess, "run") as run:
                run.return_value.returncode = 0
                self.assertEqual(contract_gate.main(argv), 0)
                self.assertEqual(
                    run.call_args.args[0][1:],
                    ["-m", "tools.spec_traceability", "check", "--change", "retire-old"],
                )

    def test_traceability_without_change_stays_strict(self):
        with patch.object(contract_gate.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertEqual(contract_gate.main(["traceability"]), 0)
            self.assertEqual(run.call_args.args[0][1:], ["-m", "tools.spec_traceability", "check"])

    def test_malformed_change_is_rejected_before_anything_runs(self):
        for argv in (["--change"], ["--change="], ["--change", "--x"], ["--change", "a", "--change", "b"]):
            with self.subTest(argv=argv), patch.object(contract_gate.subprocess, "run") as run:
                self.assertEqual(contract_gate.main(argv), 2)
                run.assert_not_called()

    def test_every_bundled_gate_is_selectable_and_the_contracts_are_named(self):
        self.assertEqual(list(contract_gate.GATES), ["reference-context", "traceability", "observability", "test-data", "manifests", "contracts"])
        self.assertIn("tests.test_evennia_test_optimization_contract", contract_gate.CONTRACT_MODULES)
        self.assertIn("tests.test_webclient_frozen_contract", contract_gate.CONTRACT_MODULES)

    def test_ci_preflight_reuses_the_gate(self):
        workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8"))
        steps = {step["name"]: step for step in workflow["jobs"]["preflight"]["steps"]}
        self.assertEqual(
            steps["Validate execution shard manifests"]["run"],
            "uv run --locked python -m tools.contract_gate manifests contracts",
        )

    def test_agents_md_names_the_gate(self):
        self.assertIn("python -m tools.contract_gate", (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"))
