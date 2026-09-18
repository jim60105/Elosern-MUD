"""Repository contract: the rules equipment/item test migration stays closed.

The migrate-rules-equipment-item-tests-off-real-data change removed every
ledger exemption for the seventeen ``world/rules/tests`` modules it migrated.
This contract re-derives the gate over exactly those files: none may carry a
ledger DEBT or CONTRACT exemption, and all must hold zero lint findings — so
a future edit that reintroduces a shipped identifier cannot silently
re-register debt. One manifest file's claims are pure shipped-content
bindings: ``test_buffs.py`` is the buffs.yaml one-test-per-key correspondence
owner, so it was converted atomically to a registered Data-contract file; it
must stay registered and must never re-enter debt. (The combat migration's
``test_combat_modifiers.py`` was first registered the same way and has since
been converted to a pure behavior suite deriving its expectations from the
loaded rule table.) The other suites compute their expectations from runtime
rule probes instead of pinned data.

``_equipment_rulebook_probes.py`` is the shared runtime-probe helper created
by this migration (never seeded as debt); it joins the zero-findings set.

Annotated with the canonical requirement id added when this change's delta
was archived/synced into ``openspec/specs``.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "world/rules/tests/test_buffs.py",
    "world/rules/tests/test_cast_settlement.py",
    "world/rules/tests/test_climax_settlement.py",
    "world/rules/tests/test_damage_effect_handler.py",
    "world/rules/tests/test_effect_handlers.py",
    "world/rules/tests/test_equipment_attached_buffs.py",
    "world/rules/tests/test_equipment_combat_wiring.py",
    "world/rules/tests/test_equipment_gauge_sync.py",
    "world/rules/tests/test_equipment_immunity.py",
    "world/rules/tests/test_equipment_prose.py",
    "world/rules/tests/test_equipment_toggle.py",
    "world/rules/tests/test_equipment_worn_grace_rules.py",
    "world/rules/tests/test_heal_effect_handler.py",
    "world/rules/tests/test_holy_water_cleanse.py",
    "world/rules/tests/test_inventory_helpers.py",
    "world/rules/tests/test_item_combat_turn.py",
    "world/rules/tests/test_item_use.py",
)

#: The manifest file whose shipped-content claims (buffs.yaml per-key field
#: bindings and catalogue scans) stayed tested in a registered Data-contract
#: file instead of synthetic fixtures.
CONTRACT_FILE = "world/rules/tests/test_buffs.py"
#: New helper files created by this migration (never seeded as debt).
NEW_HELPER_FILES = (
    "world/rules/tests/_equipment_rulebook_probes.py",
)

#: Everything that must stay at zero lint findings.
BEHAVIOR_FILES = tuple(p for p in MIGRATED_FILES if p != CONTRACT_FILE) + NEW_HELPER_FILES


class RulesEquipmentTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "equipment-and-item-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_contract_file_stays_registered_and_never_debt(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        self.assertNotIn(
            CONTRACT_FILE, debt, f"{CONTRACT_FILE} reintroduced into debt"
        )
        self.assertIn(
            CONTRACT_FILE,
            contract,
            f"{CONTRACT_FILE} lost its contract registration",
        )

    @covers_requirement(
        "test-data-independence::"
        "equipment-and-item-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(BEHAVIOR_FILES)

    @covers_requirement(
        "test-data-independence::"
        "equipment-and-item-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(BEHAVIOR_FILES)

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest({CONTRACT_FILE, *MIGRATED_FILES, *NEW_HELPER_FILES})

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES, exact_order=False)


if __name__ == "__main__":
    unittest.main()
