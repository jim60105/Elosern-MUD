"""Kit self-tests: the synthetic kit is its own first client.

Proves the four synthetic-kit requirements of test-data-independence:
catalog shape/collision/gate-clean, exact patch/restore with the discovery
pass's full binding inventory, idempotent process install, and JS-mirror
literal agreement. The file is gate-clean BY CONSTRUCTION like the kit: it
never names a shipped catalog symbol or a shipped-content string — shipped
references go through the kit's target table, split attribute strings, and
runtime lookups.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import json
import re
import sys
import types
import unittest
from pathlib import Path

import world.tests.synthetic_data as kit

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[2]

MIRROR_JS = "web/static/webclient/js/tests/support/synthetic-data.js"
MIRROR_MJS = "web/webclient-app/tests/support/synthetic-data.mjs"
KIT_REL = "world/tests/synthetic_data.py"
SELF_REL = "world/tests/test_synthetic_data.py"

_CANON_RE = re.compile("export const SYNTH_" + "CANONICAL" + r"_JSON = `([^`]*)`;")


def _catalog_maps() -> dict[str, dict]:
    """Every SYNTH_* catalog mapping (proxy views unwrapped) the kit exports."""
    out: dict[str, dict] = {}
    for name, value in vars(kit).items():
        # SYNTH_JS_PAYLOADS is a payload table keyed by payload names, not a
        # t_-keyed catalog; JsMirrorTests checks it directly.
        if not name.startswith("SYNTH_") or name == "SYNTH_JS_PAYLOADS":
            continue
        if isinstance(value, (dict, types.MappingProxyType)) and value:
            if all(isinstance(k, (str, tuple)) for k in value):
                out[name] = dict(value)
    return out


def _borrowed_seams() -> set[str]:
    """The shipped tokens the kit is allowed to carry (design D1 seams).

    Exactly the two runtime-resolved shipped references the kit documents:
    the single known grid map key (gate/placement rows must name a map the
    validator's extent scan knows) and the borrowed element key (element
    vocab is a closed shipped enum). Nothing else may collide.
    """
    return {
        kit._SYNTH_MAP_KEY,
        kit._SYNTH_ELEMENT,
        kit._SYNTH_ELEMENT_ROW.display_name_zh,
    }


def _display_strings(entry: object) -> set[str]:
    """Values of every DISPLAY_FIELDS-named field reachable from one entry."""
    from tools.test_data_lint import DISPLAY_FIELDS

    found: set[str] = set()

    def walk(node: object, depth: int) -> None:
        if depth > 4:
            return
        if isinstance(node, (str,)):
            return
        if dataclasses.is_dataclass(node) and not isinstance(node, type):
            for field in dataclasses.fields(node):
                value = getattr(node, field.name, None)
                if field.name in DISPLAY_FIELDS and isinstance(value, str):
                    found.add(value)
                walk(value, depth + 1)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value, depth + 1)
        elif isinstance(node, (list, tuple, set, frozenset)):
            for value in node:
                walk(value, depth + 1)

    walk(entry, 0)
    return found


class SyntheticCatalogShapeTests(unittest.TestCase):
    """Requirement: registry-compatible catalogs, gate-clean, collision-free."""

    @classmethod
    def setUpClass(cls) -> None:
        from tools import test_data_lint

        cls.lint = test_data_lint
        cls.universe = test_data_lint.derive_universe(REPO_ROOT)

    @covers_requirement(
        "test-data-independence::the-synthetic-test-data-kit-provides-registry-compatible-catalogs"
    )
    def test_kit_and_mirrors_are_gate_clean(self):
        for rel in (KIT_REL, SELF_REL, MIRROR_JS, MIRROR_MJS):
            with self.subTest(file=rel):
                findings = self.lint.scan_file(REPO_ROOT, rel, self.universe)
                self.assertEqual(findings, [], f"{rel} flagged: {findings}")

    @covers_requirement(
        "test-data-independence::the-synthetic-test-data-kit-provides-registry-compatible-catalogs"
    )
    def test_every_kit_key_carries_the_reserved_prefix(self):
        seams = _borrowed_seams()
        for name, catalog in _catalog_maps().items():
            for key in catalog:
                with self.subTest(catalog=name, key=str(key)):
                    parts = (key,) if isinstance(key, str) else tuple(map(str, key))
                    self.assertTrue(
                        any(
                            part.startswith(kit.SYNTH_PREFIX) or part in seams
                            for part in parts
                        ),
                        f"{name} key {key!r} is neither t_-prefixed nor a seam",
                    )

    @covers_requirement(
        "test-data-independence::the-synthetic-test-data-kit-provides-registry-compatible-catalogs"
    )
    def test_no_kit_key_or_label_collides_with_the_shipped_universe(self):
        seams = _borrowed_seams()
        universe = self.universe.tokens
        collisions: list[tuple[str, str]] = []
        for name, catalog in _catalog_maps().items():
            for key, entry in catalog.items():
                probes = {(key,) if isinstance(key, str) else tuple(map(str, key))}
                keys = {key} if isinstance(key, str) else set(map(str, key))
                collisions += [
                    (name, probe)
                    for probe in keys | _display_strings(entry)
                    if probe in universe and probe not in seams
                ]
        self.assertEqual(collisions, [], "kit/shipped token collision")

    @covers_requirement(
        "test-data-independence::the-synthetic-test-data-kit-provides-registry-compatible-catalogs"
    )
    def test_entries_are_real_definition_objects(self):
        checks = {
            "SYNTH_ITEMS": "world.lore.items",
            "SYNTH_SKILLS": "world.skills.registry",
            "SYNTH_RACES": "world.lore.races",
            "SYNTH_SUBRACES": "world.lore.races",
            "SYNTH_STARTING_KITS": "world.lore.starting_kits",
            "SYNTH_PRESETS": "world.lore.player_presets",
            "SYNTH_NPC_TIERS": "world.lore.npc_tiers",
            "SYNTH_MONSTER_TIERS": "world.lore.monsters",
            "SYNTH_REGIONS": "world.lore.wilderness_regions",
            "SYNTH_QUESTS": "world.quests.definitions",
            "SYNTH_TITLES": "world.lore.titles",
            "SYNTH_ARCHETYPES": "world.lore.scene_archetypes",
            "SYNTH_SHOPS": "world.lore.shops",
            "SYNTH_PRICES": "world.lore.economy",
            "SYNTH_BUFFS": "world.rules.buffs",
            "SYNTH_DIALOGUE": "world.rules.dialogue",
            "SYNTH_ACTS": "world.skills.sexual_acts._builder",
        }
        for catalog_name, module_name in checks.items():
            catalog = getattr(kit, catalog_name)
            module = importlib.import_module(module_name)
            for key, entry in catalog.items():
                with self.subTest(catalog=catalog_name, key=str(key)):
                    self.assertTrue(dataclasses.is_dataclass(entry))
                    self.assertIs(type(entry), getattr(module, type(entry).__name__))

    @covers_requirement(
        "test-data-independence::the-synthetic-test-data-kit-provides-registry-compatible-catalogs"
    )
    def test_factory_local_registration_is_scope_only(self):
        item = kit.make_item(key="t_local_probe", display_name_zh="地端探針")
        shared_before = dict(kit.SYNTH_ITEMS)
        with kit.synthetic_registries(
            "items", extra={"items": {"t_local_probe": item}}
        ):
            module_name, attribute = kit.REGISTRY_TARGETS["items"]
            patched = getattr(importlib.import_module(module_name), attribute)
            self.assertIn("t_local_probe", patched)
        self.assertNotIn("t_local_probe", kit.SYNTH_ITEMS)
        self.assertEqual(dict(kit.SYNTH_ITEMS), shared_before)
        with self.assertRaises(ValueError):
            kit.make_item(key="no_prefix")

    def test_every_logical_target_resolves(self):
        for logical, (module_name, attribute) in kit.REGISTRY_TARGETS.items():
            with self.subTest(target=logical):
                module = importlib.import_module(module_name)
                self.assertTrue(hasattr(module, attribute), f"{logical} unresolved")

    def test_starting_kit_scope_covers_every_synthetic_subrace(self):
        """Custom activation must find a kit for any scoped synthetic subrace."""
        self.assertEqual(
            set(kit.SYNTH_STARTING_KITS), set(kit.SYNTH_SUBRACES)
        )
        with kit.synthetic_registries("subraces", "starting_kits", "items"):
            module_name, attribute = kit.REGISTRY_TARGETS["starting_kits"]
            patched = getattr(importlib.import_module(module_name), attribute)
            for subrace_key in kit.SYNTH_SUBRACES:
                self.assertIn(subrace_key, patched)


class PatchRestoreTests(unittest.TestCase):
    """Requirement: exact scoped patch/restore over discovered bindings."""

    @staticmethod
    def _original(logical: str):
        module_name, attribute = kit.REGISTRY_TARGETS[logical]
        return getattr(importlib.import_module(module_name), attribute)

    @covers_requirement(
        "test-data-independence::the-kit-patches-and-restores-registries-exactly"
    )
    def test_context_manager_mutable_target_is_patched_in_place(self):
        original = self._original("items")
        with kit.synthetic_registries("items"):
            current = self._original("items")
            self.assertIs(current, original)  # patch.dict is in-place
            self.assertTrue(all(k.startswith("t_") for k in current))
        self.assertIs(self._original("items"), original)
        self.assertFalse(any(k.startswith("t_") for k in original))

    @covers_requirement(
        "test-data-independence::the-kit-patches-and-restores-registries-exactly"
    )
    def test_frozen_target_swaps_owner_and_every_discovered_binding(self):
        logical = "npc_tiers"
        original = self._original(logical)
        bindings = kit._consumer_bindings(logical)
        self.assertTrue(bindings, "discovery pass must find real consumers")
        exercised = 0
        with kit.synthetic_registries(logical):
            replacement = self._original(logical)
            self.assertIsInstance(replacement, types.MappingProxyType)
            self.assertTrue(all(k.startswith("t_") for k in replacement))
            for consumer_name, binding in bindings:
                consumer = importlib.import_module(consumer_name)
                exercised += 1
                self.assertIs(
                    getattr(consumer, binding),
                    replacement,
                    f"{consumer_name}.{binding} not synthetic in scope",
                )
        self.assertGreater(exercised, 0)
        self.assertIs(self._original(logical), original)
        for consumer_name, binding in bindings:
            consumer = sys.modules.get(consumer_name)
            if consumer is not None:
                self.assertIs(
                    getattr(consumer, binding),
                    original,
                    f"{consumer_name}.{binding} not restored",
                )

    @covers_requirement(
        "test-data-independence::the-kit-patches-and-restores-registries-exactly"
    )
    def test_frozen_scope_sweeps_consumer_imported_during_scope(self):
        """A consumer that bound the replacement mid-scope must be swept on exit."""
        logical = "npc_tiers"
        module_name, attribute = kit.REGISTRY_TARGETS[logical]
        original = getattr(importlib.import_module(module_name), attribute)
        bindings = dict(kit._consumer_bindings(logical))
        self.assertTrue(bindings, "discovery pass must find real consumers")
        consumer_name = sorted(bindings)[0]
        binding = bindings[consumer_name]
        saved = sys.modules.pop(consumer_name, None)
        try:
            with kit.synthetic_registries(logical):
                late = importlib.import_module(consumer_name)
                replacement = getattr(
                    importlib.import_module(module_name), attribute
                )
                self.assertIs(getattr(late, binding), replacement)
            self.assertIs(
                getattr(sys.modules[consumer_name], binding),
                original,
                "late-bound consumer kept the synthetic replacement after exit",
            )
        finally:
            if saved is not None:
                sys.modules[consumer_name] = saved

    @covers_requirement(
        "test-data-independence::the-kit-patches-and-restores-registries-exactly"
    )
    def test_decorator_and_class_decorator_get_fresh_scopes(self):
        @kit.synthetic_registries("monster_tiers")
        def decorated_check() -> bool:
            return all(
                str(k).startswith("t_") for k in self._original("monster_tiers")
            )

        self.assertTrue(decorated_check())
        self.assertFalse(
            any(str(k).startswith("t_") for k in self._original("monster_tiers"))
        )

        holder = self

        @kit.synthetic_registries("archetypes")
        class Decorated(unittest.TestCase):
            def test_a(self_inner):
                self_inner.assertTrue(
                    all(
                        str(k).startswith("t_")
                        for k in holder._original("archetypes")
                    )
                )

            def test_b(self_inner):
                self_inner.assertTrue(
                    all(
                        str(k).startswith("t_")
                        for k in holder._original("archetypes")
                    )
                )

        suite = unittest.TestLoader().loadTestsFromTestCase(Decorated)
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(result.errors + result.failures, [], "decorated class failed")
        self.assertFalse(
            any(str(k).startswith("t_") for k in self._original("archetypes"))
        )

    @covers_requirement(
        "test-data-independence::the-kit-patches-and-restores-registries-exactly"
    )
    def test_class_decorator_wraps_inherited_and_override_test_methods(self):
        holder = self

        class Base(unittest.TestCase):
            def test_inherited(self_inner):
                self_inner.fail("decorated subclass must replace inherited body")

            def test_shared(self_inner):
                holder._assert_synthetic_scope(self_inner)

        @kit.synthetic_registries("monster_tiers")
        class Sub(Base):
            def test_inherited(self_inner):
                holder._assert_synthetic_scope(self_inner)

        suite = unittest.TestLoader().loadTestsFromTestCase(Sub)
        self.assertEqual(suite.countTestCases(), 2)
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(
            result.errors + result.failures,
            [],
            "inherited/overridden tests ran without the synthetic scope",
        )

    def _assert_synthetic_scope(self, case: unittest.TestCase) -> None:
        case.assertTrue(
            all(
                str(k).startswith("t_") for k in self._original("monster_tiers")
            ),
            "synthetic scope absent in a collected test method",
        )

    @covers_requirement(
        "test-data-independence::the-kit-installs-process-wide-for-separate-test-processes"
    )
    def test_startstop_wrapper_covers_production_hook_surface(self):
        wrapper = importlib.import_module("web.tests.browser.browser_startstop")
        production = importlib.import_module("server.conf.at_server_startstop")
        production_hooks = {
            name
            for name in dir(production)
            if name.startswith("at_server_")
            and callable(getattr(production, name))
        }
        self.assertTrue(production_hooks, "no production hooks found to cover")
        missing = {
            name
            for name in production_hooks
            if not callable(getattr(wrapper, name, None))
        }
        self.assertEqual(missing, set(), "wrapper drops production hooks")

    def test_unknown_logical_and_extra_target_are_rejected(self):
        with self.assertRaises(KeyError):
            kit.synthetic_registries("not_a_registry")
        with self.assertRaises(KeyError):
            kit.synthetic_registries("items", extra={"not_a_registry": {}})

    @covers_requirement(
        "test-data-independence::the-kit-patches-and-restores-registries-exactly"
    )
    def test_discovery_inventory_matches_an_independent_ast_scan(self):
        table = kit.discover_consumer_bindings(REPO_ROOT, refresh=True)
        independent: dict[tuple[str, str], set[tuple[str, str]]] = {
            pair: set() for pair in kit.REGISTRY_TARGETS.values()
        }

        def module_level_bindings(tree: ast.Module) -> list[tuple[str, str, str]]:
            """(module, imported-attr, local-name) of MODULE-SCOPE name-imports."""
            found: list[tuple[str, str, str]] = []
            stack = list(tree.body)
            while stack:
                node = stack.pop()
                if isinstance(node, ast.ImportFrom) and node.module:
                    found.extend(
                        (node.module, alias.name, alias.asname or alias.name)
                        for alias in node.names
                    )
                elif isinstance(node, (ast.Try, ast.If)):
                    stack.extend(node.body)
                    stack.extend(node.orelse)
                    for handler in node.handlers if isinstance(node, ast.Try) else ():
                        stack.extend(handler.body)
            return found

        for package in kit._DISCOVERY_ROOTS:
            base = REPO_ROOT / package
            if not base.is_dir():
                continue
            for path in base.rglob("*.py"):
                rel = "/" + "/".join(path.relative_to(REPO_ROOT).parts)
                if any(x in rel for x in kit._DISCOVERY_EXCLUDES):
                    continue
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                except (SyntaxError, UnicodeDecodeError):
                    continue
                parts = path.relative_to(REPO_ROOT).with_suffix("").parts
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                module_name = ".".join(parts)
                for origin, attr, local in module_level_bindings(tree):
                    pair = (origin, attr)
                    if pair in independent:
                        independent[pair].add((module_name, local))
        for pair, expected in independent.items():
            self.assertEqual(
                set(table.get(pair, ())),
                expected,
                f"discovery table mismatch for {pair}",
            )

    @covers_requirement(
        "test-data-independence::the-kit-patches-and-restores-registries-exactly"
    )
    def test_sync_capture_target_patches_the_import_time_capture(self):
        seams = _borrowed_seams()
        original = self._original("lore_sync")
        categories = set(original)
        self.assertTrue(categories)
        with kit.synthetic_registries("items", include_sync_capture=True):
            capture = self._original("lore_sync")
            self.assertEqual(set(capture), categories)
            for category, content in capture.items():
                with self.subTest(category=category):
                    self.assertTrue(content, "capture category is empty")
                    for key in content:
                        probe = key if isinstance(key, str) else str(key)
                        self.assertTrue(
                            probe.startswith(kit.SYNTH_PREFIX) or probe in seams,
                            f"capture {category} key {key!r} not synthetic",
                        )
        self.assertIs(self._original("lore_sync"), original)


class ProcessInstallTests(unittest.TestCase):
    """Requirement: idempotent process-wide install bootstrap."""

    @staticmethod
    def _resolved(logical: str):
        module_name, attribute = kit.REGISTRY_TARGETS[logical]
        return getattr(importlib.import_module(module_name), attribute)

    @staticmethod
    def _synthetic_keys(container, seams: set[str]) -> list[str]:
        """Keys not carrying the prefix, checked through tuple/namespace parts."""
        bad: list[str] = []
        for key in container.keys():
            parts = (key,) if isinstance(key, str) else tuple(map(str, key))
            if not any(
                part.startswith(kit.SYNTH_PREFIX) or part in seams for part in parts
            ):
                bad.append(str(key))
        return bad

    def test_synthetic_keys_helper_rejects_midstring_prefix(self):
        # A regression key that merely CONTAINS the prefix is not synthetic.
        self.assertEqual(
            self._synthetic_keys({"old_t_entry": object()}, set()),
            ["old_t_entry"],
        )
        self.assertEqual(self._synthetic_keys({"t_ok": object()}, set()), [])

    @covers_requirement(
        "test-data-independence::the-kit-installs-process-wide-for-separate-test-processes"
    )
    def test_install_is_idempotent_and_restores_exactly(self):
        seams = _borrowed_seams()
        self.assertFalse(kit._INSTALL_STATE["installed"])
        originals = {
            logical: self._resolved(logical) for logical in kit.REGISTRY_TARGETS
        }
        self.addCleanup(kit.uninstall_synthetic_catalogs)
        self.assertTrue(kit.install_synthetic_catalogs())
        self.assertFalse(kit.install_synthetic_catalogs())  # idempotent
        for logical, original in originals.items():
            current = self._resolved(logical)
            with self.subTest(target=logical):
                if isinstance(original, types.MappingProxyType):
                    self.assertIsInstance(current, types.MappingProxyType)
                if logical == "lore_sync":
                    # Category map: the outer labels are capture categories;
                    # the synthetic invariant lives in each category's keys.
                    probes = {
                        key
                        for content in current.values()
                        for key in self._synthetic_keys(content, seams)
                    }
                else:
                    probes = set(self._synthetic_keys(current, seams))
                self.assertEqual(probes, set(), f"{logical} not synthetic after install")
        self.assertTrue(kit.uninstall_synthetic_catalogs())
        self.assertFalse(kit.uninstall_synthetic_catalogs())
        for logical, original in originals.items():
            self.assertIs(self._resolved(logical), original, logical)

    @covers_requirement(
        "test-data-independence::the-kit-installs-process-wide-for-separate-test-processes"
    )
    def test_uninstall_sweeps_consumer_imported_after_install(self):
        logical = "npc_tiers"
        module_name, attribute = kit.REGISTRY_TARGETS[logical]
        original = getattr(importlib.import_module(module_name), attribute)
        bindings = dict(kit._consumer_bindings(logical))
        consumer_name = sorted(bindings)[0]
        binding = bindings[consumer_name]
        saved = sys.modules.pop(consumer_name, None)
        try:
            self.assertTrue(kit.install_synthetic_catalogs())
            self.addCleanup(kit.uninstall_synthetic_catalogs)
            late = importlib.import_module(consumer_name)
            replacement = getattr(
                importlib.import_module(module_name), attribute
            )
            self.assertIs(getattr(late, binding), replacement)
            self.assertTrue(kit.uninstall_synthetic_catalogs())
            self.assertIs(
                getattr(sys.modules[consumer_name], binding),
                original,
                "late-bound consumer kept the installed replacement",
            )
        finally:
            if saved is not None:
                sys.modules[consumer_name] = saved


class JsMirrorTests(unittest.TestCase):
    """Requirement: JS mirrors agree with the Python kit literals."""

    @staticmethod
    def _canonical(rel: str) -> str:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        matched = _CANON_RE.search(text)
        assert matched is not None, f"{rel} must embed the canonical block"
        return matched.group(1)

    @covers_requirement(
        "test-data-independence::javascript-test-corpora-share-an-equivalent-synthetic-mirror"
    )
    def test_mirrors_are_byte_identical_and_match_the_kit(self):
        js_block = self._canonical(MIRROR_JS)
        mjs_block = self._canonical(MIRROR_MJS)
        self.assertEqual(js_block, mjs_block, "mirror copies drifted")
        self.assertEqual(json.loads(js_block), kit.SYNTH_JS_PAYLOADS)

    @covers_requirement(
        "test-data-independence::javascript-test-corpora-share-an-equivalent-synthetic-mirror"
    )
    def test_mirror_payloads_are_synthetic_and_id_backed_by_kit_catalogs(self):
        universe = self.universe_tokens()
        catalog_keys = {
            key for catalog in _catalog_maps().values() for key in catalog if isinstance(key, str)
        }
        for name, payload in kit.SYNTH_JS_PAYLOADS.items():
            with self.subTest(payload=name):
                self.assertTrue(payload["id"].startswith(kit.SYNTH_PREFIX))
                self.assertIn(payload["id"], catalog_keys, f"{name} id has no kit row")
                for value in _all_strings(payload):
                    self.assertNotIn(value, universe, f"{name} carries a shipped token")

    @staticmethod
    def universe_tokens() -> set[str]:
        from tools import test_data_lint

        return test_data_lint.derive_universe(REPO_ROOT).tokens


def _all_strings(entry: object, depth: int = 0) -> set[str]:
    if depth > 4:
        return set()
    if isinstance(entry, str):
        return {entry}
    if isinstance(entry, dict):
        return {s for v in entry.values() for s in _all_strings(v, depth + 1)}
    if isinstance(entry, (list, tuple, set, frozenset)):
        return {s for v in entry for s in _all_strings(v, depth + 1)}
    return set()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
