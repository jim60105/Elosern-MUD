"""Repository contract: the guild/shop/service test migration stays closed.

The migrate-rules-guild-economy-tests-off-real-data change removed every
ledger exemption for the sixteen ``world/rules/tests`` modules it migrated.
This contract re-derives the gate over exactly those files: none may carry a
ledger DEBT or CONTRACT exemption, and all must hold zero lint findings — so
a future edit that reintroduces a shipped identifier cannot silently
re-register debt. Every manifest file is a pure behavior suite: no shipped-
content claim was pinned in a Data-contract file for this area, so the whole
manifest must stay debt-free and finding-free.

``_guild_service_probes.py`` is the shared synthetic-catalog probe helper
created by this migration (never seeded as debt); it joins the zero-findings
set. The pre-existing ``_combat_session_helpers.py`` helper belongs to an
earlier migration's manifest and is not restated here.

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
    "world/rules/tests/test_cap_break_turnin.py",
    "world/rules/tests/test_dialogue.py",
    "world/rules/tests/test_dialogue_session.py",
    "world/rules/tests/test_guild_dialogue_turnin.py",
    "world/rules/tests/test_guild_economy_sync.py",
    "world/rules/tests/test_guild_exams.py",
    "world/rules/tests/test_guild_registration.py",
    "world/rules/tests/test_guild_rewards.py",
    "world/rules/tests/test_npc_intents.py",
    "world/rules/tests/test_npc_schedule_runtime.py",
    "world/rules/tests/test_service_binding_persistence.py",
    "world/rules/tests/test_service_messages.py",
    "world/rules/tests/test_service_view.py",
    "world/rules/tests/test_service_view_side_effects.py",
    "world/rules/tests/test_shop_clock_sources.py",
    "world/rules/tests/test_shop_economy.py",
)

#: New helper files created by this migration (never seeded as debt).
NEW_HELPER_FILES = (
    "world/rules/tests/_guild_service_probes.py",
)

#: Everything that must stay at zero lint findings.
BEHAVIOR_FILES = (*MIGRATED_FILES, *NEW_HELPER_FILES)

#: Oversized modules later split into same-named packages (rules test split).
#: The ledger/seed checks stay pinned on the original flat paths; the
#: file-level checks below expand each split path onto its package slices so
#: the zero-findings guarantee covers every slice verbatim.
_SPLIT_PACKAGES = (
    "test_npc_intents",
    "test_service_view",
)


def _finding_scan_files(paths) -> tuple[str, ...]:
    """Every manifest file to scan, following split modules into slices."""
    files: list[str] = []
    for rel in paths:
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


class RulesGuildTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "guild-shop-and-service-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(BEHAVIOR_FILES)

    @covers_requirement(
        "test-data-independence::"
        "guild-shop-and-service-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(_finding_scan_files(BEHAVIOR_FILES))

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(_finding_scan_files(BEHAVIOR_FILES))

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
