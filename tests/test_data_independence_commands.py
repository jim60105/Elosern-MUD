"""Repository contract: the commands/typeclasses test migration stays closed.

The migrate-commands-tests-off-real-data change removed every ledger DEBT
exemption for the twenty-seven ``commands/tests`` and ``typeclasses/tests``
modules it migrated. This contract re-derives the gate over exactly those
files: none may carry a ledger DEBT or CONTRACT exemption, and all must hold
zero lint findings — so a future edit that reintroduces a shipped identifier
cannot silently re-register debt. Every manifest file resolves game data
through the synthetic kit (scoped catalogs, kit rows/factories, and runtime
vocabulary probes over the loaded registries), so the whole manifest stays
debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "commands/tests/test_art.py",
    "commands/tests/test_background.py",
    "commands/tests/test_character_creation.py",
    "commands/tests/test_combat_actions.py",
    "commands/tests/test_command_branch_behaviour.py",
    "commands/tests/test_guild_economy_commands.py",
    "commands/tests/test_inventory_breakdown.py",
    "commands/tests/test_items.py",
    "commands/tests/test_lineage_command.py",
    "commands/tests/test_localized.py",
    "commands/tests/test_lore_command.py",
    "commands/tests/test_party_commands.py",
    "commands/tests/test_persona_commands.py",
    "commands/tests/test_talk_turnin_branch.py",
    "commands/tests/test_talk_turnin_commands.py",
    "commands/tests/test_title_command.py",
    "typeclasses/tests/test_account_capacity.py",
    "typeclasses/tests/test_account_login.py",
    "typeclasses/tests/test_appearance.py",
    "typeclasses/tests/test_art_room_entry.py",
    "typeclasses/tests/test_components.py",
    "typeclasses/tests/test_entities.py",
    "typeclasses/tests/test_exit_movement_cost.py",
    "typeclasses/tests/test_exits.py",
    "typeclasses/tests/test_npc_dialogue.py",
    "typeclasses/tests/test_npcs.py",
    "typeclasses/tests/test_rooms.py",
)


class CommandsTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    @covers_requirement(
        "test-data-independence::"
        "command-and-typeclass-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in MIGRATED_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    @covers_requirement(
        "test-data-independence::"
        "command-and-typeclass-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
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
