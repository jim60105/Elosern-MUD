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


class RulesGuildTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    @covers_requirement(
        "test-data-independence::"
        "guild-shop-and-service-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in BEHAVIOR_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    @covers_requirement(
        "test-data-independence::"
        "guild-shop-and-service-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        universe = test_data_lint.derive_universe(test_data_lint.REPO_ROOT)
        for path in BEHAVIOR_FILES:
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
        mine = set(BEHAVIOR_FILES)
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
