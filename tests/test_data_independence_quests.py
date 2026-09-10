"""Repository contract: the quests/maps test migration off shipped data stays closed.

The migrate-quests-maps-tests-off-real-data change removed every ledger
exemption for the twenty-eight ``world/quests/tests`` and ``world/maps/tests``
modules it migrated. This contract re-derives the gate over exactly those
files: they must carry no ledger exemption (debt or contract) AND zero lint
findings, so a future edit that reintroduces a shipped identifier cannot
silently re-register debt.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "world/maps/tests/test_city_wilderness_roundtrip.py",
    "world/maps/tests/test_instance_reclamation.py",
    "world/maps/tests/test_instance_spawn.py",
    "world/maps/tests/test_limbo_room.py",
    "world/maps/tests/test_movement_roundtrip.py",
    "world/maps/tests/test_service_interiors.py",
    "world/maps/tests/test_wilderness_clock.py",
    "world/maps/tests/test_wilderness_destination.py",
    "world/maps/tests/test_wilderness_population.py",
    "world/maps/tests/test_wilderness_provider.py",
    "world/quests/tests/_compile_helpers.py",
    "world/quests/tests/_fixtures.py",
    "world/quests/tests/test_acquire.py",
    "world/quests/tests/test_action_events.py",
    "world/quests/tests/test_binding.py",
    "world/quests/tests/test_characterization.py",
    "world/quests/tests/test_deliver.py",
    "world/quests/tests/test_describe.py",
    "world/quests/tests/test_generated_quest_store.py",
    "world/quests/tests/test_integration.py",
    "world/quests/tests/test_pipeline_scenarios.py",
    "world/quests/tests/test_planner.py",
    "world/quests/tests/test_room_observation.py",
    "world/quests/tests/test_runtime.py",
    "world/quests/tests/test_scene_builder.py",
    "world/quests/tests/test_scene_builder_flavor.py",
    "world/quests/tests/test_scene_builder_offline.py",
    "world/quests/tests/test_settlement.py",
)


class QuestsMapsTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    @covers_requirement(
        "test-data-independence::quests-and-maps-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in MIGRATED_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    @covers_requirement(
        "test-data-independence::quests-and-maps-behavior-tests-resolve-game-data-through-synthetic-fixtures"
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

    @covers_requirement(
        "test-data-independence::quests-and-maps-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_gate_is_green_and_reports_no_violation_for_migrated_files(self):
        report = test_data_lint.check_repo(test_data_lint.REPO_ROOT)
        self.assertTrue(
            report.ok,
            "\n".join(
                f"{v.path}: {v.rule}: {v.detail}" for v in report.violations
            ),
        )

    @covers_requirement(
        "test-data-independence::quests-and-maps-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        # The migration removed debt entries only; the carried classification
        # still lists every seeded debt path (shrink-only ratchet design).
        seed = test_data_lint.load_seed(test_data_lint.REPO_ROOT)
        seed_debt = set(seed["seedDebtPaths"])
        for path in MIGRATED_FILES:
            self.assertIn(path, seed_debt)
        self.assertEqual(
            sorted(self.ledger["seedDebtPaths"]), sorted(seed["seedDebtPaths"])
        )


if __name__ == "__main__":
    unittest.main()
