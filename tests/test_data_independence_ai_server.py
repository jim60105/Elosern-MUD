"""Repository contract: the AI-server test migration stays closed.

The migrate-ai-server-integration-tests-off-real-data change removed every
ledger DEBT exemption for the seventeen ``server/conf/tests``, ``tests/`` and
``world/ai/tests`` modules it migrated. This contract re-derives the gate over
exactly those files: none may carry a ledger DEBT or CONTRACT exemption, and
all must hold zero lint findings — so a future edit that reintroduces a shipped
identifier cannot silently re-register debt. Every manifest file resolves game
data through the synthetic kit (scoped catalogs, kit rows, runtime vocabulary
probes) or file-local synthetic fixtures, so the whole manifest stays
debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "server/conf/tests/test_ai_director_service.py",
    "server/conf/tests/test_option_proposal_service.py",
    "server/conf/tests/test_scene_flavor_service.py",
    "server/conf/tests/test_ui_action_integration.py",
    "tests/test_creation_parity_contract.py",
    "tests/test_quality_gate_contract.py",
    "world/ai/tests/_director_helpers.py",
    "world/ai/tests/test_action_options_layer.py",
    "world/ai/tests/test_action_options_schema.py",
    "world/ai/tests/test_character_creation.py",
    "world/ai/tests/test_narrator.py",
    "world/ai/tests/test_npc_dialogue_retry.py",
    "world/ai/tests/test_scenario_director_prompts.py",
    "world/ai/tests/test_scenario_director_proposals.py",
    "world/ai/tests/test_scenario_director_registration.py",
    "world/ai/tests/test_scenario_director_validation.py",
    "world/ai/tests/test_title_nomination.py",
)


class AiServerTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in MIGRATED_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    def test_migrated_files_carry_zero_findings(self):
        universe = test_data_lint.derive_universe(test_data_lint.REPO_ROOT)
        for path in MIGRATED_FILES:
            with self.subTest(path=path):
                self.assertTrue((test_data_lint.REPO_ROOT / path).is_file())
                self.assertEqual(
                    test_data_lint.scan_file(test_data_lint.REPO_ROOT, path, universe),
                    [],
                )

    def test_no_violation_naming_a_manifest_file(self):
        # Whole-repo greenness is owned by the ``tools.test_data_lint check``
        # gate itself; inside the Evennia test runner a process-wide universe
        # can pick up lazily-registered vocabulary and name unrelated files.
        # What must never regress is a violation whose path belongs to this
        # migration's manifest.
        report = test_data_lint.check_repo(test_data_lint.REPO_ROOT)
        mine = set(MIGRATED_FILES)
        self.assertEqual(
            [
                f"{v.path}: {v.rule}: {v.detail}"
                for v in report.violations
                if v.path in mine
            ],
            [],
        )

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        # The migration removed debt entries only; the carried classification
        # still lists every seeded debt path in its exact committed order
        # (shrink-only ratchet design; a reorder is a regression too).
        seed = test_data_lint.load_seed(test_data_lint.REPO_ROOT)
        seed_debt = set(seed["seedDebtPaths"])
        for path in MIGRATED_FILES:
            self.assertIn(path, seed_debt)
        self.assertEqual(self.ledger["seedDebtPaths"], seed["seedDebtPaths"])


if __name__ == "__main__":
    unittest.main()
