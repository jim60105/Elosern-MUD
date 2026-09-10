"""Repository contract: the rules equipment/item test migration stays closed.

The migrate-rules-equipment-item-tests-off-real-data change removed every
ledger exemption for the seventeen ``world/rules/tests`` modules it migrated.
This contract re-derives the gate over exactly those files: none may carry a
ledger DEBT or CONTRACT exemption, and all must hold zero lint findings — so
a future edit that reintroduces a shipped identifier cannot silently
re-register debt. No manifest file's claims relocated to a registered
Data-contract file here: the shipped-content residue (declared skill costs,
catalogue reachability) is already owned by the existing skill-registry
contract files, and the suites compute their expectations from runtime rule
probes instead of pinned data.

``_equipment_rulebook_probes.py`` is the shared runtime-probe helper created
by this migration (never seeded as debt); it joins the zero-findings set.

Annotated with the canonical requirement id added when this change's delta
was archived/synced into ``openspec/specs``.
"""

from pathlib import Path
import unittest

from tools import test_data_lint

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

#: New helper files created by this migration (never seeded as debt).
NEW_HELPER_FILES = (
    "world/rules/tests/_equipment_rulebook_probes.py",
)

#: Everything that must stay at zero lint findings.
BEHAVIOR_FILES = MIGRATED_FILES + NEW_HELPER_FILES


class RulesEquipmentTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in BEHAVIOR_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    def test_migrated_files_carry_zero_findings(self):
        universe = test_data_lint.derive_universe(test_data_lint.REPO_ROOT)
        for path in BEHAVIOR_FILES:
            with self.subTest(path=path):
                self.assertTrue((test_data_lint.REPO_ROOT / path).is_file())
                self.assertEqual(
                    test_data_lint.scan_file(test_data_lint.REPO_ROOT, path, universe),
                    [],
                )

    def test_gate_is_green_and_reports_no_violation_for_migrated_files(self):
        report = test_data_lint.check_repo(test_data_lint.REPO_ROOT)
        self.assertTrue(
            report.ok,
            "\n".join(
                f"{v.path}: {v.rule}: {v.detail}" for v in report.violations
            ),
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
