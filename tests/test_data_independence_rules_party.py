"""Repository contract: the rules-service/party test migration stays closed.

The migrate-rules-service-party-tests-off-real-data change removed every
ledger exemption for the seven ``world/rules/tests`` modules it migrated.
This contract re-derives the gate over exactly those files: none may carry a
ledger DEBT or CONTRACT exemption, and all must hold zero lint findings — so
a future edit that reintroduces a shipped identifier cannot silently
re-register debt. Every manifest file is a pure behavior suite: the
shipped-content claims that had to survive relocation (issuer resolution,
delivery prose assembly, companion activation binding) are exercised through
runtime vocabulary probes and file-local synthetic rows over the kit
catalogs, so the whole manifest stays debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "world/rules/tests/test_combat_party.py",
    "world/rules/tests/test_party.py",
    "world/rules/tests/test_party_offline_loop.py",
    "world/rules/tests/test_quest_delivery.py",
    "world/rules/tests/test_quest_issuance.py",
    "world/rules/tests/test_quest_issuer_component.py",
    "world/rules/tests/test_starting_companions.py",
)


class RulesPartyTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "party-quest-delivery-and-companion-behavior-tests-resolve-game-data-"
        "through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::"
        "party-quest-delivery-and-companion-behavior-tests-resolve-game-data-"
        "through-synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(MIGRATED_FILES)

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(MIGRATED_FILES)

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
