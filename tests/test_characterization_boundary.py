"""Repository-wide guard for the shared blueprint-characterization rule source.

The scenario-director guardrail (``world/ai``) and the deterministic compile
boundary (``world/quests``) must both validate the optional per-occupant
characterization fields through the one shared helper in
``world.quests.characterization`` -- never through inline copies of the
age/name/key rules. This contract locks the two call sites and forbids an
inline duplicate of the rules from reappearing in either layer.
"""

import ast
from pathlib import Path
import re
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_HELPER = "world.quests.characterization"
SHARED_VALIDATOR_MODULE = "world.rules.npc_identity"
# The synced blueprint-portrait-policy spec allows exactly one immutable bound
# constant at module scope; the validators must stay deferred. Adding another
# bound constant is a contract change and must amend this tuple deliberately.
MODULE_BOUND_SYMBOLS = ("MAX_NPC_NAME_CODE_POINTS",)
DEFERRED_VALIDATOR_SYMBOLS = (
    "NPCNameError",
    "NPCTitleError",
    "validate_npc_name",
    "validate_npc_title",
)
RULE_SYMBOLS = (
    "characterize_errors",
    "duplicate_stable_key_errors",
    "race_lifespan_upper_bound",
)
RULE_MARKERS = (
    "age and apparent_age must be declared together",
    "portrait.stable_key must be non-empty text",
)


def _production_source(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _imported_module_names(tree: ast.Module) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
    return names


def _classify_world_rules_imports(
    tree: ast.Module,
) -> tuple[set[str], set[str], set[str]]:
    """Split world.rules usage into (module-scope, function-scope, plain-imports).

    Scope is lexical: any import under a module-level compound statement
    (``if``/``try``/``with``...) counts as module scope; only imports inside a
    (async) function count as deferred. Plain ``import world.rules...`` forms
    are reported separately because they hide the shared surface behind a
    namespace alias and cannot be symbol-classified.
    """
    module_scope: set[str] = set()
    function_scope: set[str] = set()
    plain: set[str] = set()

    def _visit(node: ast.AST, in_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Import):
                for alias in child.names:
                    if _is_world_rules(alias.name):
                        plain.add(alias.name)
            elif isinstance(child, ast.ImportFrom) and _is_world_rules(child.module or ""):
                bucket = function_scope if in_function else module_scope
                bucket.update(f"{child.module}.{alias.name}" for alias in child.names)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _visit(child, True)
            elif isinstance(child, ast.AST):
                _visit(child, in_function)

    _visit(tree, False)
    return module_scope, function_scope, plain


def _is_world_rules(module: str) -> bool:
    return module == "world.rules" or module.startswith("world.rules.")


class SharedCharacterizationHelperGuardTests(unittest.TestCase):
    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_both_layers_import_the_shared_helper(self):
        for relative in (
            "world/ai/scenario_director.py",
            "world/quests/compile.py",
        ):
            with self.subTest(module=relative):
                tree = ast.parse(_production_source(relative))
                imported = _imported_module_names(tree)
                self.assertIn(SHARED_HELPER, imported)
                for symbol in RULE_SYMBOLS:
                    source = _production_source(relative)
                    self.assertIn(symbol, source, f"{relative} must call {symbol}")

    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_no_inline_duplicate_of_the_rules_exists_in_either_layer(self):
        for relative in (
            "world/ai/scenario_director.py",
            "world/quests/compile.py",
        ):
            with self.subTest(module=relative):
                source = _production_source(relative)
                for marker in RULE_MARKERS:
                    self.assertNotIn(marker, source)

    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_the_helper_is_pure_and_read_only(self):
        source = _production_source("world/quests/characterization.py")
        for fragment in ("world.ai", "ollama", "llm_client"):
            self.assertNotIn(fragment, source)
        tree = ast.parse(source)
        imported = _imported_module_names(tree)
        # The synced spec mandates delegating the name/title rules to exactly
        # one world.rules module; every other rules import stays banned and
        # the delegation itself is required, so this exception can never be
        # silently widened or dropped.
        rules_imports = {module for module in imported if _is_world_rules(module)}
        self.assertEqual(
            rules_imports,
            {SHARED_VALIDATOR_MODULE},
            "characterization.py may depend on world.rules only through the "
            "single shared validator module " + SHARED_VALIDATOR_MODULE,
        )
        # The delegation is pinned to a function-local deferred import; only
        # the immutable bound alias may be imported at module scope, and the
        # namespace-import form is banned outright because it evades the
        # symbol classification below.
        module_scope, function_scope, plain = _classify_world_rules_imports(tree)
        self.assertEqual(
            plain,
            set(),
            "characterization.py must not use plain 'import world.rules...' "
            "namespace imports",
        )
        allowed_module_symbols = {
            f"{SHARED_VALIDATOR_MODULE}.{name}" for name in MODULE_BOUND_SYMBOLS
        }
        self.assertTrue(
            module_scope <= allowed_module_symbols,
            f"module-scope world.rules imports {sorted(module_scope - allowed_module_symbols)} "
            "violate the deferred-delegation contract",
        )
        required_deferred = {
            f"{SHARED_VALIDATOR_MODULE}.{name}" for name in DEFERRED_VALIDATOR_SYMBOLS
        }
        self.assertTrue(
            required_deferred <= function_scope,
            "the shared name/title validators must be deferred-imported inside "
            f"{SHARED_VALIDATOR_MODULE.rsplit('.', 1)[-1]} functions",
        )
        for banned in ("typeclasses", "evennia.utils.create"):
            self.assertFalse(
                any(module == banned or module.startswith(banned + ".") for module in imported),
                f"characterization.py must not import {banned}",
            )

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_the_persona_field_bound_mirrors_the_rules_bound(self):
        # The characterization helper may import only
        # ``world.rules.npc_identity`` (purity contract above), never
        # ``world.rules.character_creation``, so the authored persona bound is
        # mirrored locally and pinned here to the authoritative persona cap.
        char_source = _production_source("world/quests/characterization.py")
        rules_source = _production_source("world/rules/character_creation.py")
        char_match = re.search(r"^MAX_PERSONA_FIELD_LENGTH\s*=\s*([0-9]+)", char_source, re.MULTILINE)
        rules_match = re.search(r"^MAX_PERSONA_FIELD_LENGTH\s*=\s*([0-9]+)", rules_source, re.MULTILINE)
        self.assertIsNotNone(char_match, "characterization MAX_PERSONA_FIELD_LENGTH missing")
        self.assertIsNotNone(rules_match, "rules MAX_PERSONA_FIELD_LENGTH missing")
        self.assertEqual(char_match.group(1), rules_match.group(1))
        self.assertEqual(rules_match.group(1), "600")


if __name__ == "__main__":
    unittest.main()
