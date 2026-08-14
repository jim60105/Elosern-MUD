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
        for banned in ("world.rules", "typeclasses", "evennia.utils.create"):
            self.assertFalse(
                any(module == banned or module.startswith(banned + ".") for module in imported),
                f"characterization.py must not import {banned}",
            )

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_the_persona_field_bound_mirrors_the_rules_bound(self):
        # The characterization helper cannot import ``world.rules`` (purity
        # contract above), so the authored persona bound is mirrored locally
        # and pinned here to the authoritative persona field cap.
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
