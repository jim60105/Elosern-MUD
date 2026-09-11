"""Repository contract: the rules sexual-status test migration stays closed.

The migrate-rules-sexual-status-tests-off-real-data change removed every
ledger exemption for the fourteen ``world/rules/tests`` modules it migrated.
This contract re-derives the gate over exactly those files: none may carry a
ledger DEBT or CONTRACT exemption, and all must hold zero lint findings — so
a future edit that reintroduces a shipped identifier cannot silently
re-register debt. Every manifest file is a pure behavior suite: the
shipped-content claims that had to survive relocation (rulebook sink-rule
bundles, condition labels, element/category vocabularies) are exercised
through runtime vocabulary probes over the loaded rulebook and live
registries plus file-local synthetic rows over the kit catalogs, so the whole
manifest stays debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "world/rules/tests/test_cast_settlement_sexual_coercion.py",
    "world/rules/tests/test_combat_session_sexual_coercion.py",
    "world/rules/tests/test_equipment_sexual_effects.py",
    "world/rules/tests/test_ordered_level_trait.py",
    "world/rules/tests/test_sexual_act_effects.py",
    "world/rules/tests/test_sexual_decay_and_reset.py",
    "world/rules/tests/test_sexual_event_self_arming.py",
    "world/rules/tests/test_sexual_resist.py",
    "world/rules/tests/test_sexual_resist_cast_wiring.py",
    "world/rules/tests/test_sexual_state.py",
    "world/rules/tests/test_sexual_transitions.py",
    "world/rules/tests/test_sexual_unlock.py",
    "world/rules/tests/test_status_query.py",
    "world/rules/tests/test_status_text.py",
)


class RulesSexualStatusTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    @covers_requirement(
        "test-data-independence::"
        "sexual-and-status-behavior-tests-resolve-game-data-through-synthetic-"
        "fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in MIGRATED_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    @covers_requirement(
        "test-data-independence::"
        "sexual-and-status-behavior-tests-resolve-game-data-through-synthetic-"
        "fixtures"
    )
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
