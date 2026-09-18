"""Shared implementation behind the repository-wide test-data-independence contracts.

The seventeen ``tests/test_data_independence_*.py`` modules each pin one
migration's manifest (module-level ``MIGRATED_FILES`` / ``BEHAVIOR_FILES`` /
``CONTRACT_FILE`` constants). Their ``test_*`` methods are thin shells that
delegate the formerly-verbatim bodies to :class:`DataIndependenceContractMixin`;
each shell keeps its literal ``@covers_requirement`` IDs and its own manifest
constants, so traceability and ``git grep`` still land on the owning module.

The mixin loads the ledger once per test (``setUp``) and exposes one
``assert_*`` helper per contract check. The bodies are the union of the copies
this file replaced; where the family carried two orderings of the same
assertion, the variant is a keyword parameter (``check_exists``,
``exact_order``) that the shell that had it passes explicitly.
"""

from tools import test_data_lint


class DataIndependenceContractMixin:
    """unittest mixin; subclasses pin their manifests as module constants."""

    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    def assert_no_ledger_exemption(self, paths):
        """No manifest path may carry a ledger DEBT or CONTRACT exemption."""
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in paths:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    def assert_zero_findings(self, paths, *, check_exists=True):
        """Every manifest path must exist and scan with zero lint findings."""
        universe = test_data_lint.derive_universe(test_data_lint.REPO_ROOT)
        for path in paths:
            with self.subTest(path=path):
                if check_exists:
                    self.assertTrue((test_data_lint.REPO_ROOT / path).is_file())
                self.assertEqual(
                    test_data_lint.scan_file(test_data_lint.REPO_ROOT, path, universe),
                    [],
                )

    def assert_no_violation_naming_manifest(self, paths):
        # Whole-repo greenness is owned by the ``tools.test_data_lint check``
        # gate itself; inside the Evennia test runner a process-wide universe
        # can pick up lazily-registered vocabulary and name unrelated files.
        # What must never regress is a violation whose path belongs to this
        # migration's manifest.
        report = test_data_lint.check_repo(test_data_lint.REPO_ROOT)
        mine = set(paths)
        self.assertEqual(
            [
                f"{v.path}: {v.rule}: {v.detail}"
                for v in report.violations
                if v.path in mine
            ],
            [],
        )

    def assert_freeze_seed_untouched(self, paths, *, exact_order=True):
        # The migration removed debt entries only; the carried classification
        # still lists every seeded debt path (shrink-only ratchet design).
        # Migrations that pinned the exact committed order also pass
        # ``exact_order=True``: a reorder of the carried array is a regression
        # too, so the ledger array must equal the seed file element-for-element.
        seed = test_data_lint.load_seed(test_data_lint.REPO_ROOT)
        seed_debt = set(seed["seedDebtPaths"])
        for path in paths:
            self.assertIn(path, seed_debt)
        if exact_order:
            self.assertEqual(self.ledger["seedDebtPaths"], seed["seedDebtPaths"])
        else:
            self.assertEqual(
                sorted(self.ledger["seedDebtPaths"]), sorted(seed["seedDebtPaths"])
            )

    def assert_gate_green_for_manifest(self):
        """The whole-repo data gate must be green for every migrated file."""
        report = test_data_lint.check_repo(test_data_lint.REPO_ROOT)
        self.assertTrue(
            report.ok,
            "\n".join(
                f"{v.path}: {v.rule}: {v.detail}" for v in report.violations
            ),
        )