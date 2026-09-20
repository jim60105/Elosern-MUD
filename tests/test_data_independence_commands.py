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
from ._data_independence_base import DataIndependenceContractMixin

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


#: Oversized modules later split into same-named packages (commands test
#: split). The ledger/seed checks stay pinned on the original flat paths; the
#: zero-findings scan below expands each split path onto its package slices so
#: the guarantee covers every slice verbatim.
_SPLIT_PACKAGES = (
    "test_character_creation",
    "test_localized",
)


def _finding_scan_files() -> tuple[str, ...]:
    """Every manifest file to scan, following split modules into slices."""
    files: list[str] = []
    for rel in MIGRATED_FILES:
        name = rel.rsplit("/", 1)[-1][: -len(".py")]
        if name in _SPLIT_PACKAGES:
            package = (REPO_ROOT / rel).with_suffix("")
            files.extend(
                str(path.relative_to(REPO_ROOT))
                for path in sorted(package.rglob("*.py"))
                if "__pycache__" not in path.parts
            )
        else:
            files.append(rel)
    return tuple(files)


class CommandsTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "command-and-typeclass-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::"
        "command-and-typeclass-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(_finding_scan_files())

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(MIGRATED_FILES)

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
