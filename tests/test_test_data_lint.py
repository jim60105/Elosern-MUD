"""Gate tests for ``tools.test_data_lint`` (test-data independence).

Pure unittest over temp trees + synthetic universes; the only production-touching
tests are the universe derivation (no DB) and the deny-list regressions.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import tools.test_data_lint as lint

REPO = Path(__file__).resolve().parent.parent
UNIVERSE = lint.derive_universe(REPO)

#: one real shipped identifier, selected at runtime (never written as a literal so
#: this file itself stays gate-clean)
SHIPPED = next(t for t in sorted(UNIVERSE.tokens) if "_" in t and t.isascii() and t.islower())


def _catalog_symbol() -> str:
    import world.skills.registry as skill_registry

    return next(s for s in sorted(UNIVERSE.symbols) if hasattr(skill_registry, s))


CATALOG_SYMBOL = _catalog_symbol()
SYNTH = "t_ember_spray_zzz"
FAKE_KEY = "abc_shipped_key_zzz"


def _tree(files: dict[str, str]) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp


def _ledger(seed_debt: list[str], contract: list[dict], debt: list[str]) -> dict:
    return {"seedDebtPaths": sorted(seed_debt), "contract": contract, "debt": sorted(debt)}


MINI = lint.Universe(tokens=frozenset({FAKE_KEY}), symbols=frozenset(), denied=frozenset())


class ScannerTests(unittest.TestCase):
    """Spec: the-test-data-lint-gate-blocks-shipped-content-references."""

    def _scan(self, source: str, rel: str = "world/rules/tests/test_probe.py", universe: lint.Universe = MINI):
        tmp = _tree({rel: source})
        try:
            return lint.scan_file(Path(tmp.name), rel, universe)
        finally:
            tmp.cleanup()

    def test_shipped_literal_flagged(self):
        findings = self._scan(f'"""x"""\nITEM = "{SHIPPED}"\n', universe=UNIVERSE)
        self.assertEqual([f.kind for f in findings], ["token"])
        self.assertEqual(findings[0].detail, SHIPPED)

    def test_synthetic_fixture_not_flagged(self):
        findings = self._scan(f'"""x"""\nITEM = "{SYNTH}"\nLABEL = "synthetic potion of nothing"\n')
        self.assertEqual(findings, [])

    def test_literal_concatenation_flagged(self):
        half_a, half_b = SHIPPED[: len(SHIPPED) // 2], SHIPPED[len(SHIPPED) // 2:]
        findings = self._scan(f'"""x"""\nITEM = "{half_a}" + "{half_b}"\n', universe=UNIVERSE)
        self.assertIn("token", {f.kind for f in findings})
        self.assertIn(SHIPPED, {f.detail for f in findings})

    def test_all_literal_fstring_flagged(self):
        findings = self._scan(f'"""x"""\nITEM = f"{SHIPPED}"\n', universe=UNIVERSE)
        self.assertIn(SHIPPED, {f.detail for f in findings})

    def test_dynamic_concatenation_not_resolvable(self):
        findings = self._scan(f'"""x"""\nITEM = "a" + input()\n', universe=UNIVERSE)
        self.assertEqual([f for f in findings if f.kind == "token"], [])

    def test_js_literal_flagged(self):
        findings = self._scan(f"const x = '{FAKE_KEY}';\n", rel="web/webclient-app/tests/a.test.js")
        self.assertEqual([f.kind for f in findings], ["token"])

    def test_js_template_literal_flagged(self):
        findings = self._scan(f"const x = `{FAKE_KEY}`;\n", rel="web/webclient-app/tests/a.test.js")
        self.assertEqual([f.kind for f in findings], ["token"])

    def test_js_literal_concatenation_flagged(self):
        half_a, half_b = FAKE_KEY[: 6], FAKE_KEY[6:]
        findings = self._scan(f"const x = '{half_a}' + \"{half_b}\";\n", rel="web/webclient-app/tests/a.test.js")
        self.assertIn(FAKE_KEY, {f.detail for f in findings})

    def test_symbol_reference_flagged(self):
        universe = lint.Universe(tokens=frozenset(), symbols=frozenset({CATALOG_SYMBOL}), denied=frozenset())
        findings = self._scan(f'"""x"""\nimport world.skills.registry as r\nN = r.{CATALOG_SYMBOL}\n', universe=universe)
        self.assertEqual([f.kind for f in findings], ["symbol-ref"])

    def test_quantity_pin_reported_as_pin_class(self):
        universe = lint.Universe(tokens=frozenset(), symbols=frozenset({CATALOG_SYMBOL}), denied=frozenset())
        source = f'"""x"""\nimport unittest\nclass T(unittest.TestCase):\n    def t(self):\n        self.assertEqual(len({CATALOG_SYMBOL}), 58)\n'
        findings = self._scan(source, universe=universe)
        kinds = {f.kind for f in findings}
        self.assertIn("quantity-pin", kinds)
        self.assertNotIn("token", kinds)

    def test_bare_len_compare_is_pin(self):
        universe = lint.Universe(tokens=frozenset(), symbols=frozenset({CATALOG_SYMBOL}), denied=frozenset())
        findings = self._scan(f'"""x"""\nassert len({CATALOG_SYMBOL}) == 58\n', universe=universe)
        self.assertIn("quantity-pin", {f.kind for f in findings})

    def test_len_compared_to_variable_is_not_pin(self):
        universe = lint.Universe(tokens=frozenset(), symbols=frozenset({CATALOG_SYMBOL}), denied=frozenset())
        source = f'"""x"""\nimport unittest\nclass T(unittest.TestCase):\n    def t(self):\n        n = 1\n        self.assertEqual(len({CATALOG_SYMBOL}), n)\n'
        findings = self._scan(source, universe=universe)
        self.assertNotIn("quantity-pin", {f.kind for f in findings})

    def test_universe_tracks_catalogs(self):
        """The universe is derived from the catalogs, not a hand list (no DB access)."""
        import importlib

        registry = importlib.import_module("world.skills.registry")
        sample = getattr(registry, CATALOG_SYMBOL)
        keys = {k for k in sample if isinstance(k, str)}
        self.assertTrue(keys & UNIVERSE.tokens, "catalog keys must appear in the universe")
        self.assertGreater(len(UNIVERSE.tokens), 500)
        self.assertIn(CATALOG_SYMBOL, UNIVERSE.symbols)

    def test_rulebook_keys_follow_yaml(self):
        tmp = _tree({"world/rules/rulebook/buffs.yaml": "buffs:\n  zzz_synthetic_buff: {}\n"})
        try:
            keys = lint._rulebook_keys(Path(tmp.name))
            self.assertIn("zzz_synthetic_buff", keys)
        finally:
            tmp.cleanup()

    def test_deny_list_regressions(self):
        """Every deny entry: rule-bound admission is mechanically checkable, and
        shipped-key references stay caught while the denied token alone is clean."""
        entries = json.loads((REPO / lint.DENY_PATH).read_text(encoding="utf-8"))["entries"]
        self.assertGreater(len(entries), 0)
        caught = self._scan(f'"""x"""\nV = "{SHIPPED}"\n', universe=UNIVERSE)
        self.assertEqual([f.kind for f in caught], ["token"])
        for entry in entries:
            with self.subTest(token=entry["token"]):
                self.assertTrue(entry["reason"].strip() and entry["evidence"].strip())
                self.assertIn(entry["rule"], ("schema-structural", "production-independent"))
                if entry["rule"] == "production-independent":
                    # Evidence is a non-test production path that contains the token,
                    # and the token collides with the pre-deny derived universe.
                    evidence_path = entry["evidence"].split(":")[0]
                    self.assertFalse(lint._is_test_path(evidence_path))
                    text = (REPO / evidence_path).read_text(encoding="utf-8")
                    self.assertIn(entry["token"], text)
                    self.assertIn(entry["token"], UNIVERSE.raw_tokens | UNIVERSE.denied)
                else:
                    # schema-structural: the token is a rulebook YAML / catalog payload
                    # field name — present in the pre-deny universe or as a literal key
                    # in the locked rulebook payloads.
                    in_catalog = entry["token"] in UNIVERSE.raw_tokens or any(
                        f"{entry['token']}:" in p.read_text(encoding="utf-8")
                        for p in (REPO / "world/rules/rulebook").rglob("*.yaml")
                    )
                    self.assertTrue(in_catalog)
                clean = self._scan(f'"""x"""\nV = "{entry["token"]}"\n', universe=UNIVERSE)
                self.assertEqual(clean, [])


class CorpusTests(unittest.TestCase):
    """Spec: scan every versioned test source, nothing else (design D4)."""

    FILES = [
        "world/rules/tests/test_a.py",
        "tests/_fixture.py",
        "tests/test_b.py",
        "web/webclient-app/tests/x/y.test.js",
        "web/webclient-app/tests/z.spec.ts",
        "commands/test_cmd.py",
        "tools/tests/test_tool.py",
        "world/rules/plain_module.py",
        "web/static/js/dist/bundle.test.js",
        "web/node_modules/pkg/a.test.js",
        "scripts/test_outside.py",
        "docs/notes.md",
    ]

    def test_corpus_selection(self):
        picked = set(lint.test_corpus(Path("."), files=self.FILES))
        self.assertEqual(
            picked,
            {
                "world/rules/tests/test_a.py",
                "tests/_fixture.py",
                "tests/test_b.py",
                "web/webclient-app/tests/x/y.test.js",
                "web/webclient-app/tests/z.spec.ts",
                "commands/test_cmd.py",
                "tools/tests/test_tool.py",
            },
        )

    def test_corpus_uses_git_ls_files(self):
        corpus = lint.test_corpus(REPO)
        self.assertGreater(len(corpus), 500)
        self.assertTrue(all(not p.startswith("dist/") for p in corpus))


class LedgerTests(unittest.TestCase):
    """Spec: the-exemption-ledger-is-provably-shrink-only + tag/ledger agreement."""

    def _run(self, files: dict[str, str], seed: dict, ledger: dict, universe: lint.Universe = MINI):
        tmp = _tree(files)
        try:
            root = Path(tmp.name)
            (root / lint.SEED_PATH).parent.mkdir(parents=True, exist_ok=True)
            (root / lint.SEED_PATH).write_text(json.dumps(seed), encoding="utf-8")
            corpus = [rel for rel in files if lint._is_test_path(rel)]
            return lint.check_ledger(root, ledger, universe, files=corpus)
        finally:
            tmp.cleanup()

    @staticmethod
    def _flagged(rel: str) -> str:
        return f'"""x"""\nV = "{FAKE_KEY}"\n'

    def test_green_tree(self):
        files = {"tests/test_clean.py": '"""x"""\nV = "zzz_nothing"\n'}
        report = self._run(files, _ledger([], [], []), _ledger([], [], []))
        self.assertEqual(report.violations, ())
        self.assertEqual(report.flagged_files, 0)

    def test_unexempted(self):
        files = {"tests/test_dirty.py": self._flagged("tests/test_dirty.py")}
        report = self._run(files, _ledger([], [], []), _ledger([], [], []))
        self.assertIn("unexempted", [v.rule for v in report.violations])

    def test_debt_exempt(self):
        files = {"tests/test_dirty.py": self._flagged("tests/test_dirty.py")}
        ledger = _ledger(["tests/test_dirty.py"], [], ["tests/test_dirty.py"])
        report = self._run(files, ledger, ledger)
        self.assertEqual(report.violations, ())

    def test_new_debt_rejected(self):
        files = {"tests/test_dirty.py": self._flagged("tests/test_dirty.py")}
        report = self._run(files, _ledger([], [], []), _ledger([], [], ["tests/test_dirty.py"]))
        self.assertIn("new-debt", [v.rule for v in report.violations])

    def test_stale_path(self):
        ledger = _ledger(["tests/test_gone.py"], [], ["tests/test_gone.py"])
        report = self._run({}, ledger, ledger)
        self.assertIn("stale-path", [v.rule for v in report.violations])

    def test_duplicate_same_kind(self):
        files = {"tests/test_dirty.py": self._flagged("tests/test_dirty.py")}
        ledger = _ledger(["tests/test_dirty.py"], [], ["tests/test_dirty.py"])
        ledger["debt"] = ["tests/test_dirty.py", "tests/test_dirty.py"]
        report = self._run(files, _ledger(["tests/test_dirty.py"], [], ["tests/test_dirty.py"]), ledger)
        self.assertIn("duplicate", [v.rule for v in report.violations])

    def test_duplicate_cross_kind(self):
        files = {
            "tests/test_c.py": '"""Data-contract test: reason"""\n' + self._flagged("tests/test_c.py"),
        }
        contract = [{"path": "tests/test_c.py", "reason": "reason"}]
        seed = _ledger(["tests/test_c.py"], [], [])
        ledger = _ledger(["tests/test_c.py"], contract, ["tests/test_c.py"])
        report = self._run(files, seed, ledger)
        self.assertIn("duplicate", [v.rule for v in report.violations])

    def test_untagged_contract(self):
        files = {"tests/test_c.py": '"""No tag here."""\n' + self._flagged("tests/test_c.py")}
        contract = [{"path": "tests/test_c.py", "reason": "reason"}]
        seed = _ledger(["tests/test_c.py"], contract, [])
        ledger = _ledger(["tests/test_c.py"], contract, [])
        report = self._run(files, seed, ledger)
        self.assertIn("untagged-contract", [v.rule for v in report.violations])

    def test_tagged_contract_passes(self):
        files = {"tests/test_c.py": '"""Data-contract test: reason"""\n' + self._flagged("tests/test_c.py")}
        contract = [{"path": "tests/test_c.py", "reason": "reason"}]
        seed = _ledger(["tests/test_c.py"], contract, [])
        report = self._run(files, seed, _ledger(["tests/test_c.py"], contract, []))
        self.assertEqual(report.violations, ())

    def test_tag_rationale_must_match_ledger_reason(self):
        files = {"tests/test_c.py": '"""Data-contract test: something else"""\n' + self._flagged("tests/test_c.py")}
        contract = [{"path": "tests/test_c.py", "reason": "reason"}]
        seed = _ledger(["tests/test_c.py"], contract, [])
        report = self._run(files, seed, _ledger(["tests/test_c.py"], contract, []))
        self.assertIn("untagged-contract", [v.rule for v in report.violations])

    def test_tag_needs_rationale(self):
        files = {"tests/test_c.py": '"""Data-contract test:"""\n' + self._flagged("tests/test_c.py")}
        contract = [{"path": "tests/test_c.py", "reason": "reason"}]
        seed = _ledger(["tests/test_c.py"], contract, [])
        report = self._run(files, seed, _ledger(["tests/test_c.py"], contract, []))
        self.assertIn("untagged-contract", [v.rule for v in report.violations])

    def test_js_tag(self):
        files = {"web/webclient-app/tests/c.test.js": "// Data-contract test: reason\nconst x = '" + FAKE_KEY + "';\n"}
        contract = [{"path": "web/webclient-app/tests/c.test.js", "reason": "reason"}]
        seed = _ledger(["web/webclient-app/tests/c.test.js"], contract, [])
        report = self._run(files, seed, _ledger(["web/webclient-app/tests/c.test.js"], contract, []))
        self.assertEqual(report.violations, ())

    def test_atomic_debt_to_contract_conversion(self):
        """Seeded debt file reclassified: removed from debt, added once to contract+tag."""
        body = self._flagged("tests/test_c.py")
        contract = [{"path": "tests/test_c.py", "reason": "reason"}]
        seed = _ledger(["tests/test_c.py"], [], [])
        files = {"tests/test_c.py": '"""Data-contract test: reason"""\n' + body}
        converted = _ledger(["tests/test_c.py"], contract, [])
        report = self._run(files, seed, converted)
        self.assertEqual(report.violations, ())

    def test_conversion_outside_seed_rejected(self):
        files = {"tests/test_new.py": '"""Data-contract test: reason"""\n' + self._flagged("tests/test_new.py")}
        contract = [{"path": "tests/test_new.py", "reason": "reason"}]
        seed = _ledger([], [], [])
        report = self._run(files, seed, _ledger([], contract, []))
        self.assertIn("new-debt", [v.rule for v in report.violations])

    def test_seed_debt_paths_frozen(self):
        files = {"tests/test_dirty.py": self._flagged("tests/test_dirty.py")}
        seed = _ledger(["tests/test_dirty.py"], [], ["tests/test_dirty.py"])
        weakened = _ledger([], [], ["tests/test_dirty.py"])  # seed list edited away
        report = self._run(files, seed, weakened)
        self.assertIn("seed-mismatch", [v.rule for v in report.violations])

    def test_contract_reason_drift(self):
        files = {"tests/test_c.py": '"""Data-contract test: new wording"""\n' + self._flagged("tests/test_c.py")}
        seed = _ledger(["tests/test_c.py"], [{"path": "tests/test_c.py", "reason": "old reason"}], [])
        ledger = _ledger(["tests/test_c.py"], [{"path": "tests/test_c.py", "reason": "new wording"}], [])
        report = self._run(files, seed, ledger)
        self.assertIn("seed-mismatch", [v.rule for v in report.violations])


class RepoLedgerTests(unittest.TestCase):
    """The committed ledger/seed/tag state of this repository is coherent."""

    def test_check_green(self):
        report = lint.check_repo(REPO)
        self.assertEqual([v.rule for v in report.violations], [])
        self.assertGreater(report.flagged_files, 300)
        self.assertGreater(report.scanned_files, 500)

    def test_seed_subcommand_matches_committed_ledger(self):
        committed = json.loads((REPO / lint.LEDGER_PATH).read_text(encoding="utf-8"))
        seed = json.loads((REPO / lint.SEED_PATH).read_text(encoding="utf-8"))
        # the ledger's frozen fields must equal the seed classification it was seeded from
        self.assertEqual(sorted(committed["contract"], key=lambda c: c["path"]), sorted(seed["contract"], key=lambda c: c["path"]))
        self.assertEqual(committed["seedDebtPaths"], sorted(seed["seedDebtPaths"]))
        self.assertTrue(set(committed["debt"]) <= set(committed["seedDebtPaths"]))


class WiringTests(unittest.TestCase):
    """Spec: the-gate-is-wired-into-ci-and-the-authoring-rules-are-documented."""

    def test_workflow_runs_the_gate(self):
        text = (REPO / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        self.assertIn("python -m tools.test_data_lint check", text)
        self.assertIn("tools.observability_lint", text)
        self.assertIn("tools.spec_traceability", text)

    def test_agents_md_authoring_rule(self):
        text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("tools.test_data_lint check", text)
        self.assertIn("Data-contract test:", text)

    def test_testing_guide_rules(self):
        text = (REPO / "docs/development/evennia-testing-guide.md").read_text(encoding="utf-8")
        for phrase in (
            "tools.test_data_lint check",
            "Data-contract test:",
            "world/tests/synthetic_data.py",
        ):
            self.assertIn(phrase, text)


class ArtifactIntegrityTests(unittest.TestCase):
    """Ledger/seed/deny files are valid JSON artifacts with the required shape."""

    def test_ledger_shape(self):
        for rel in (lint.LEDGER_PATH, lint.SEED_PATH, lint.DENY_PATH):
            with self.subTest(path=rel):
                payload = json.loads((REPO / rel).read_text(encoding="utf-8"))
                self.assertIsInstance(payload, dict)
                self.assertTrue(json.dumps(payload, ensure_ascii=False))
        deny = json.loads((REPO / lint.DENY_PATH).read_text(encoding="utf-8"))["entries"]
        self.assertEqual(sorted(e["token"] for e in deny), sorted({e["token"] for e in deny}))


if __name__ == "__main__":
    unittest.main()
