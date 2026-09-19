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
from ._data_independence_base import DataIndependenceContractMixin

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


class QuestsMapsTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::quests-and-maps-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::quests-and-maps-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::quests-and-maps-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_gate_is_green_and_reports_no_violation_for_migrated_files(self):
        self.assert_gate_green_for_manifest()

    @covers_requirement(
        "test-data-independence::quests-and-maps-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES, exact_order=False)


if __name__ == "__main__":
    unittest.main()
