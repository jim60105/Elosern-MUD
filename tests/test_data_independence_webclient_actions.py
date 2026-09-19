"""Repository contract: the webclient actions test migration stays closed.

The migrate-webclient-actions-tests-off-real-data change removed every ledger
DEBT exemption for the twelve modules it migrated (ten
``web/webclient/actions/tests`` modules plus ``test_webclient_contract`` and
``test_art_media`` under ``web/webclient/tests``). This contract
re-derives the gate over exactly those files: none may carry a ledger DEBT or
CONTRACT exemption, and all must hold zero lint findings — so a future edit
that reintroduces a shipped identifier cannot silently re-register debt.
Every manifest file resolves game data through the synthetic kit (scoped
catalogs, kit rows, runtime vocabulary probes) or file-local synthetic
fixtures, so the whole manifest stays debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "web/webclient/actions/tests/test_character_actions.py",
    "web/webclient/actions/tests/test_combat_actions.py",
    "web/webclient/actions/tests/test_combat_dispatcher.py",
    "web/webclient/actions/tests/test_creation_actions.py",
    "web/webclient/actions/tests/test_exploration_actions.py",
    "web/webclient/actions/tests/test_inventory_actions.py",
    "web/webclient/actions/tests/test_node_ids.py",
    "web/webclient/actions/tests/test_service_actions.py",
    "web/webclient/actions/tests/test_service_validators.py",
    "web/webclient/actions/tests/test_title_actions.py",
    "web/webclient/tests/test_webclient_contract.py",
    "web/webclient/tests/test_art_media.py",
)


class WebclientActionsTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "webclient-action-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::"
        "webclient-action-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(MIGRATED_FILES)

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(MIGRATED_FILES)

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
