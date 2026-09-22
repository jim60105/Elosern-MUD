"""Slice of ``test_env_overrides``: InventoryTests, ShardOwnershipGuardTests.
"""
import ast
import os
import re
import subprocess
import sys
import unittest
from server.conf.llm_knobs import llm_env_names, llm_global_env_names
from tools.spec_traceability import covers_requirement

from ._support import (
    ENV_BACKED,
    EXTERNAL_READERS,
    EXTERNAL_READERS_PREFIXES,
    GUIDE_PATH,
    PROMPTS_DOC_PATH,
    REPO_ROOT,
    SETTINGS_PATH,
    SIDEBAR_PATH,
    _active_env_example_keys,
    _env_example_lines,
    _env_read_names,
    _guide_rows,
    _test_settings_popped_names,
)


class InventoryTests(unittest.TestCase):
    """Pure filesystem + AST checks; no subprocess."""

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_settings_ast_reads_exactly_the_env_backed_inventory(self):
        read = _env_read_names(SETTINGS_PATH)
        self.assertEqual(
            read, set(ENV_BACKED.values()) | {"PROMPT_ROOT", "ART_SEED_ROOT"}
        )
        # The LLM knob reads are loop-generated (invisible to this extractor)
        # and the retired OLLAMA_BASE_URL name must not reappear anywhere in
        # the settings module.
        self.assertNotIn("OLLAMA_BASE_URL", read)
        # Belt-and-braces for the security seam: the forbidden names never
        # appear as an argument to ANY call in settings.py, so an aliased or
        # dynamic environment read (env = os.environ; env.get(...)) cannot
        # reintroduce an env path for them outside the shapes above.
        tree = ast.parse(open(SETTINGS_PATH, encoding="utf-8").read())
        call_string_args = {
            node.value
            for call in ast.walk(tree)
            if isinstance(call, ast.Call)
            for arg in [*call.args, *(kw.value for kw in call.keywords)]
            for node in ast.walk(arg)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertNotIn("ART_SD_CLIENT", call_string_args)
        self.assertNotIn("ART_STORE_ROOT", call_string_args)
        self.assertNotIn("ART_SD_USERNAME", call_string_args)
        self.assertNotIn("ART_SD_PASSWORD", call_string_args)
        self.assertNotIn("ART_REMBG_BACKEND", call_string_args)
        self.assertNotIn("ART_REMBG_MODEL_DIR", call_string_args)
        self.assertNotIn("ART_TRANSLATE_BACKEND", call_string_args)

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_env_example_advertises_no_dead_variables(self):
        live = set(ENV_BACKED.values()) | {"PROMPT_ROOT", "ART_SEED_ROOT"}
        generated = llm_env_names()
        for key in _active_env_example_keys():
            with self.subTest(key=key):
                self.assertTrue(
                    key in live
                    or key in generated
                    or key in EXTERNAL_READERS
                    or any(
                        key.startswith(prefix)
                        for prefix in EXTERNAL_READERS_PREFIXES
                    ),
                    msg=f"{key} has no reader (settings AST or allow-list)",
                )

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_llm_knob_entries_match_the_inert_definition_exactly(self):
        # Comment style is irrelevant (typed knobs ship commented by
        # convention): parse every NAME= assignment starting with LLM_ and
        # compare as an EXACT SET against the knob module's generated globals
        # (column-0 assignments only, matching the file's entry convention —
        # indented example lines inside doc comments are prose, not entries).
        parsed = {
            match.group(1)
            for line in _env_example_lines()
            if (
                match := re.match(
                    r"^#?([A-Za-z_][A-Za-z0-9_]*)=", line
                )
            )
            and match.group(1).startswith("LLM_")
        }
        self.assertEqual(parsed, set(llm_global_env_names()))
        self.assertNotIn("OLLAMA_BASE_URL", parsed)
        # Per-layer names are documented through the grammar, not enumerated.
        for name in llm_env_names() - llm_global_env_names():
            self.assertNotIn(name, parsed)

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_settings_publishes_the_generated_name_set(self):
        # Derived-export contract: settings.LLM_ENV_NAMES equals the inert
        # function exactly. Read as source here (the module-level assignment)
        # and asserted against the function; the subprocess boot case lives
        # in server/conf/tests/test_llm_env_overrides.py.
        source = open(SETTINGS_PATH, encoding="utf-8").read()
        self.assertIn("LLM_ENV_NAMES = frozenset(llm_env_names())", source)
        self.assertEqual(len(llm_env_names()), 184)

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_env_example_documents_every_env_backed_override(self):
        # The typed override examples ship commented (never an uncommented
        # empty typed entry), so completeness must be checked against the
        # COMMENTED assignments too — deleting or renaming one example entry
        # would otherwise silently desync the template from the live AST.
        commented = {
            match.group(1)
            for line in _env_example_lines()
            if (match := re.match(r"^#([A-Za-z_][A-Za-z0-9_]*)=", line))
        }
        missing = set(ENV_BACKED.values()) - commented
        self.assertFalse(missing, msg=f"missing .env.example entries: {missing}")

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_test_settings_override_names_match_the_settings_ast(self):
        # The literal ART tuple stays exact, plus the <LLM_KNOB_SWEEP> marker
        # proving the second sanitize loop over the inert knob module exists
        # (an AST pass cannot enumerate that loop's generated names; the
        # knob-module set-equality tests pin them instead).
        self.assertEqual(
            _test_settings_popped_names(),
            set(ENV_BACKED.values()) | {"<LLM_KNOB_SWEEP>"},
        )

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_guide_documents_every_env_backed_setting_and_is_linked(self):
        self.assertTrue(os.path.isfile(GUIDE_PATH))
        with open(SIDEBAR_PATH, encoding="utf-8") as handle:
            self.assertIn("/development/settings-and-environment", handle.read())
        rows = _guide_rows()
        for setting, variable in ENV_BACKED.items():
            matching = [
                row
                for row in rows
                if f"`{setting}`" in row and f"`{variable}`" in row
            ]
            self.assertTrue(
                matching,
                msg=f"guide has no table row naming {setting} and {variable}",
            )
            cells = [
                cell.strip()
                for cell in matching[0].strip().strip("|").split("|")
            ]
            self.assertGreaterEqual(
                len(cells),
                5,
                msg=f"guide row for {setting} lacks type/default/rule cells",
            )
            self.assertTrue(
                all(cells), msg=f"guide row for {setting} has an empty cell"
            )
        timeout_rows = [row for row in rows if "`ART_SD_TIMEOUT_SECONDS`" in row]
        self.assertTrue(
            any("600" in row for row in timeout_rows),
            msg="timeout guide row omits its default",
        )
        prepin_rows = [row for row in rows if "`ART_SD_PREPIN_SAMPLES_FORMAT`" in row]
        self.assertTrue(
            any("1/true/yes/on" in row for row in prepin_rows),
            msg="boolean guide row omits the accepted word list",
        )
        for dimension in (
            "ART_SD_SCENE_WIDTH",
            "ART_SD_SCENE_HEIGHT",
            "ART_SD_PORTRAIT_WIDTH",
            "ART_SD_PORTRAIT_HEIGHT",
        ):
            dimension_rows = [row for row in rows if f"`{dimension}`" in row]
            self.assertTrue(
                any("8 倍數" in row or "multiple of 8" in row for row in dimension_rows),
                msg=f"dimension guide row for {dimension} omits the multiple-of-8 rule",
            )
        with open(PROMPTS_DOC_PATH, encoding="utf-8") as handle:
            self.assertIn("settings-and-environment", handle.read())


class ShardOwnershipGuardTests(unittest.TestCase):
    """server/conf/tests/ is owned by the manifest's package-level `server`
    label, which resolves by walking test*.py under the directory; adding an
    entry for this module to .github/evennia-shards.json would BREAK the
    ownership contract (tests.test_evennia_test_optimization_contract)."""

    def test_new_module_path_is_not_listed_in_the_shard_manifest(self):
        manifest_path = os.path.join(REPO_ROOT, ".github", "evennia-shards.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest_text = handle.read()
        for module in ("test_env_overrides", "test_llm_env_overrides"):
            self.assertNotIn(module, manifest_text)
