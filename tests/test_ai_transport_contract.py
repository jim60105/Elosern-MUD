"""Repository-wide contract for the generative transport boundary.

The live transport (``OpenAICompatClient``, Evennia's ``LLMClient``, Twisted's
``Agent``) is owned by exactly one module, ``world/ai/client.py``. Every other
generative module consumes transport only through an injected client protocol,
tests never construct the real client (except the client's own unit tests), the
deterministic paths (``world/rules``, ``world/maps``, ``world/quests``,
``commands``) stay free of any LLM/client import, and no module under
``world/ai`` may import a state writer.
"""

import ast
from pathlib import Path
import unittest

from tools.spec_traceability import covers_requirement

LIVE_TRANSPORT_MODULES = (
    "evennia.contrib.rpg.llm",
    "twisted.web",
    "twisted.internet.reactor",
)
LIVE_TRANSPORT_NAMES = ("OpenAICompatClient", "LLMClient", "Agent", "reactor")
STATE_WRITER_MODULES = (
    "world.rules",
    "world.maps",
    "world.quests",
    "world.art",
    "typeclasses",
    "evennia.prototypes.spawner",
    "evennia.utils.create",
)
FORBIDDEN_FRAGMENTS = ("ollama", "llm_client", "world.ai")

# Pure read-only rule modules that carry no state writes and no typeclasses:
# ``world.quests.characterization`` is the shared blueprint-characterization
# bound helper (blueprint-portrait-policy D3). ``world/ai`` imports it read-only
# exactly as it already imports the ``world.lore`` registries, and it never
# mutates state, so it is exempt from the state-writer ban.
READ_ONLY_RULE_MODULES = ("world.quests.characterization",)

DETERMINISTIC_PACKAGES = ("world/rules", "world/maps", "world/quests", "world/art", "commands")

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = REPO_ROOT / "world" / "ai"
AI_TESTS_ROOT = AI_ROOT / "tests"


def _module_paths(root: Path) -> list[Path]:
    paths = []
    for path in sorted(root.rglob("*.py")):
        parts = path.relative_to(root).parts
        if "__init__.py" in parts or "__pycache__" in parts:
            continue
        paths.append(path)
    return paths


def _production_module_paths(root: Path) -> list[Path]:
    return [
        path
        for path in _module_paths(root)
        if "tests" not in path.relative_to(root).parts
    ]


def _imported_module_names(tree: ast.Module) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
    return names


def _imported_alias_names(tree: ast.Module) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.extend(alias.name for alias in node.names)
    return names


def _imports_state_writer(tree: ast.Module) -> list[str]:
    banned = []
    for module in _imported_module_names(tree):
        if any(
            module == rule or module.startswith(rule + ".")
            for rule in READ_ONLY_RULE_MODULES
        ):
            continue
        for prefix in STATE_WRITER_MODULES:
            if module == prefix or module.startswith(prefix + "."):
                banned.append(module)
    return banned


class AiTransportBoundaryTests(unittest.TestCase):
    @covers_requirement("scenario-director::the-scenario-director-layer-preserves-the-single-writer-and-transport-boundaries")
    @covers_requirement("action-options-layer::the-layer-is-strictly-proposal-only")
    def test_only_client_py_imports_a_live_transport(self):
        for module_path in _production_module_paths(AI_ROOT):
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            imported = _imported_module_names(tree)
            imported_aliases = _imported_alias_names(tree)
            with self.subTest(module=module_path.as_posix()):
                for module in imported:
                    for prefix in LIVE_TRANSPORT_MODULES:
                        if module == prefix or module.startswith(prefix + "."):
                            self.assertEqual(
                                module_path.name,
                                "client.py",
                                f"{module_path} must not import live transport {module}",
                            )
                for name in LIVE_TRANSPORT_NAMES:
                    if name in imported_aliases:
                        self.assertEqual(
                            module_path.name,
                            "client.py",
                            f"{module_path} must not import live transport symbol {name}",
                        )

    def test_schemas_fake_and_errors_never_import_the_live_transport(self):
        for module_path in [
            *_production_module_paths(AI_ROOT / "schemas"),
            AI_ROOT / "errors.py",
        ]:
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            with self.subTest(module=module_path.as_posix()):
                for module in _imported_module_names(tree):
                    for prefix in LIVE_TRANSPORT_MODULES:
                        self.assertFalse(
                            module == prefix or module.startswith(prefix + "."),
                            f"{module_path} must not import {module}",
                        )

    @covers_requirement("scenario-director::the-scenario-director-layer-preserves-the-single-writer-and-transport-boundaries")
    @covers_requirement("persona-dialogue-injection::persona-wiring-is-read-only-and-value-passing")
    @covers_requirement("action-options-layer::the-layer-is-strictly-proposal-only")
    def test_no_ai_module_imports_a_state_writer(self):
        for module_path in _production_module_paths(AI_ROOT):
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            banned = _imports_state_writer(tree)
            with self.subTest(module=module_path.as_posix()):
                self.assertEqual(banned, [])

    @covers_requirement("fake-llm-client::generative-layer-tests-never-contact-a-live-endpoint")
    @covers_requirement("scenario-director::the-scenario-director-layer-preserves-the-single-writer-and-transport-boundaries")
    def test_tests_never_construct_openai_compat_client(self):
        for module_path in _module_paths(AI_TESTS_ROOT):
            if module_path.name == "test_client.py":
                continue  # the client's own unit tests must construct it
            source = module_path.read_text(encoding="utf-8")
            with self.subTest(module=module_path.as_posix()):
                self.assertNotIn("OpenAICompatClient(", source)

    @covers_requirement("fake-llm-client::generative-layer-tests-never-contact-a-live-endpoint")
    @covers_requirement("scenario-director::the-scenario-director-layer-preserves-the-single-writer-and-transport-boundaries")
    @covers_requirement("action-options-layer::the-layer-is-strictly-proposal-only")
    def test_generative_module_source_has_no_socket_imports(self):
        for module_path in [
            *_production_module_paths(AI_ROOT),
            *_production_module_paths(AI_ROOT / "schemas"),
        ]:
            source = module_path.read_text(encoding="utf-8").lower()
            with self.subTest(module=module_path.as_posix()):
                self.assertNotIn("import socket", source)
                self.assertNotIn("from socket", source)


class DeterministicPathBanTests(unittest.TestCase):
    @covers_requirement("scenario-director::the-scenario-director-layer-preserves-the-single-writer-and-transport-boundaries")
    def test_deterministic_paths_stay_free_of_llm_imports(self):
        for package in DETERMINISTIC_PACKAGES:
            package_root = REPO_ROOT / package
            for module_path in sorted(package_root.rglob("*.py")):
                if "/tests/" in module_path.as_posix():
                    continue
                source = module_path.read_text(encoding="utf-8").lower()
                with self.subTest(module=module_path.as_posix()):
                    for fragment in FORBIDDEN_FRAGMENTS:
                        self.assertNotIn(
                            fragment,
                            source,
                            f"{module_path} must not reference {fragment}",
                        )
