"""Repository contract: the AI-server test migration stays closed.

The migrate-ai-server-integration-tests-off-real-data change removed every
ledger DEBT exemption for the seventeen ``server/conf/tests``, ``tests/`` and
``world/ai/tests`` modules it migrated. This contract re-derives the gate over
exactly those files: none may carry a ledger DEBT or CONTRACT exemption, and
all must hold zero lint findings — so a future edit that reintroduces a shipped
identifier cannot silently re-register debt. Every manifest file resolves game
data through the synthetic kit (scoped catalogs, kit rows, runtime vocabulary
probes) or file-local synthetic fixtures, so the whole manifest stays
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
    "server/conf/tests/test_ai_director_service.py",
    "server/conf/tests/test_option_proposal_service.py",
    "server/conf/tests/test_scene_flavor_service.py",
    "server/conf/tests/test_ui_action_integration.py",
    "tests/test_creation_parity_contract.py",
    "tests/test_quality_gate_contract.py",
    "world/ai/tests/_director_helpers.py",
    "world/ai/tests/test_action_options_layer.py",
    "world/ai/tests/test_action_options_schema.py",
    "world/ai/tests/test_character_creation.py",
    "world/ai/tests/test_narrator.py",
    "world/ai/tests/test_npc_dialogue_retry.py",
    "world/ai/tests/test_scenario_director_prompts.py",
    "world/ai/tests/test_scenario_director_proposals.py",
    "world/ai/tests/test_scenario_director_registration.py",
    "world/ai/tests/test_scenario_director_validation.py",
    "world/ai/tests/test_title_nomination.py",
)


#: Oversized modules later split into same-named packages (server.conf test
#: split). The ledger/seed checks stay pinned on the original flat paths; the
#: zero-findings scan below expands each split path onto its package slices so
#: the guarantee covers every slice verbatim.
_SPLIT_PACKAGES = (
    "test_option_proposal_service",
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


class AiServerTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "ai-server-and-integration-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::"
        "ai-server-and-integration-behavior-tests-resolve-game-data-through-"
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
