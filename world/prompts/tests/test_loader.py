"""Loader and render tests for the prompt library (prompt-library).

Covers valid loading, every validation failure mode (unknown key, duplicate
key, missing file, missing key, empty/over-length text, unknown placeholder),
deterministic rendering with allowlist and literal-brace rules, auto-load on
first use, reset/reload, and the named errors surfaced to consumers.
"""

from __future__ import annotations

import unittest

from world.prompts.loader import (
    PromptLibraryError,
    PromptUnavailableError,
    UnexpectedPromptValueError,
    UnknownPromptKeyError,
    load_prompt_library,
    render_prompt,
    reset_prompt_library,
)
from world.prompts.registry import PROMPT_SPECS

from tools.spec_traceability import covers_requirement

from world.prompts.tests.fixtures import REPO_PROMPTS, PromptFixture



class ValidLoadTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_prompt_library()

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt", "prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_repo_prompts_load_fully_and_render_deterministically(self):
        library = load_prompt_library(str(REPO_PROMPTS))
        self.assertEqual(library.unavailable, frozenset())
        self.assertEqual(set(library.texts), set(PROMPT_SPECS))
        first = render_prompt("narrator.system")
        second = render_prompt("narrator.system")
        self.assertEqual(first, second)
        self.assertIn("伊洛瑟恩大陸", first)

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt")
    def test_every_generative_layer_has_a_registered_prompt_file(self):
        library = load_prompt_library(str(REPO_PROMPTS))
        for spec in PROMPT_SPECS.values():
            self.assertIn(spec.key, library.texts)
        self.assertEqual(
            {spec.file for spec in PROMPT_SPECS.values()},
            {
                "narrator.yaml",
                "npc_dialogue.yaml",
                "scenario_director.yaml",
                "npc.yaml",
                "art.yaml",
                "character_creation.yaml",
            },
        )

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt")
    def test_character_creation_key_is_registered_but_unused(self):
        library = load_prompt_library(str(REPO_PROMPTS))
        self.assertIn("character_creation.system", library.texts)
        self.assertIn("character_creation.system", PROMPT_SPECS)
        world_modules = [
            path
            for path in (REPO_PROMPTS.parent / "world").rglob("*.py")
            if "prompts" not in path.parts and "tests" not in path.parts
        ]
        self.assertFalse(
            [
                str(path)
                for path in world_modules
                if "character_creation.system" in path.read_text(encoding="utf-8")
            ],
            "no runtime consumer may call the forward-declared character_creation key",
        )

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_allowlisted_placeholders_are_substituted_exactly_once(self):
        load_prompt_library(str(REPO_PROMPTS))
        text = render_prompt(
            "npc_dialogue.system",
            name="艾洛西亞",
            desc="南門的守衛",
            location="王都",
        )
        self.assertEqual(text.count("艾洛西亞"), 1)
        self.assertEqual(text.count("南門的守衛"), 1)
        self.assertEqual(text.count("王都"), 1)
        self.assertNotIn("{name}", text)
        self.assertNotIn("{desc}", text)
        self.assertNotIn("{location}", text)

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_double_braced_tokens_and_json_braces_pass_through(self):
        load_prompt_library(str(REPO_PROMPTS))
        scenario = render_prompt("scenario_director.system")
        self.assertIn('{"name": "…"', scenario)
        self.assertIn('"item_key": "healing_potion"', scenario)
        dialogue = render_prompt("npc_dialogue.system", name="甲", desc="乙", location="丙")
        self.assertIn('{"speech": "你要說的話", "intent": {"kind": "..."}}', dialogue)
        thinking = render_prompt("npc.thinking", name="甲")
        self.assertEqual(thinking, "（甲 沉思片刻……）")


class ValidationFailureTests(PromptFixture):
    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_unknown_key_is_recorded_with_a_named_error(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: 旁白。\n  narrator.extra: 多餘。\n",
        )
        library = self.load()
        error = library.errors["narrator.extra"]
        self.assertIn("unknown prompt key", error.problem)
        self.assertEqual(error.file, "narrator.yaml")
        self.assertIn("narrator.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_duplicate_top_level_key_rejects_the_file(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nschema_version: 1\nprompts:\n  narrator.system: 旁白。\n",
        )
        library = self.load()
        error = library.errors["narrator.system"]
        self.assertIn("duplicate mapping key", error.problem)
        self.assertNotIn("narrator.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_duplicate_prompts_key_rejects_the_file(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: 旁白。\n  narrator.system: 覆寫。\n",
        )
        library = self.load()
        error = library.errors["narrator.system"]
        self.assertIn("duplicate mapping key", error.problem)
        self.assertNotIn("narrator.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_missing_key_file_marks_the_key_unavailable(self):
        (self.root / "npc_dialogue.yaml").unlink()
        library = self.load()
        error = library.errors["npc_dialogue.system"]
        self.assertIn("not found", error.problem)
        self.assertIn("narrator.system", library.texts)
        self.assertIn("scenario_director.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_missing_key_in_prompts_mapping_is_recorded(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: 旁白。\n",
        )
        self.write_file(
            "scenario_director.yaml",
            "schema_version: 1\nprompts: {}\n",
        )
        library = self.load()
        self.assertNotIn("scenario_director.system", library.texts)
        error = library.errors["scenario_director.system"]
        self.assertIn("missing prompt key", error.problem)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_empty_text_is_rejected(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: \"  \"\n",
        )
        library = self.load()
        self.assertIn("empty", library.errors["narrator.system"].problem)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_overlength_text_is_rejected(self):
        spec = PROMPT_SPECS["narrator.system"]
        self.write_file(
            "narrator.yaml",
            f"schema_version: 1\nprompts:\n  narrator.system: \"{'字' * (spec.max_length + 1)}\"\n",
        )
        library = self.load()
        self.assertIn("exceeds max", library.errors["narrator.system"].problem)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_unknown_placeholder_token_is_a_load_time_error(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: 旁白 {nmme}。\n",
        )
        library = self.load()
        error = library.errors["narrator.system"]
        self.assertIn("unknown placeholder", error.problem)
        self.assertIn("nmme", error.problem)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_a_malformed_file_fails_only_its_own_key(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: 旁白 {nmme}。\n",
        )
        library = self.load()
        self.assertIn("narrator.system", library.errors)
        self.assertIn("npc_dialogue.system", library.texts)
        self.assertIn("scenario_director.system", library.texts)
        self.assertIn("art.style", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_unreadable_file_marks_its_keys_unavailable(self):
        (self.root / "narrator.yaml").unlink()
        (self.root / "narrator.yaml").mkdir()
        library = self.load()
        self.assertIn("narrator.system", library.errors)
        self.assertNotIn("narrator.system", library.texts)
        self.assertIn("npc_dialogue.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_invalid_utf8_file_marks_its_keys_unavailable(self):
        (self.root / "narrator.yaml").write_bytes(b"\xff\xfe\x00\x80")
        library = self.load()
        self.assertIn("narrator.system", library.errors)
        self.assertNotIn("narrator.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_unlistable_root_marks_every_key_unavailable_without_raising(self):
        from unittest.mock import patch

        with patch("world.prompts.loader.os.listdir", side_effect=OSError("denied")):
            library = self.load()
        self.assertEqual(set(library.errors), set(PROMPT_SPECS))
        self.assertEqual(library.texts, {})

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_mixed_type_unknown_top_level_key_is_recorded_not_a_crash(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\n123: 數字鍵\nprompts:\n  narrator.system: 旁白。\n",
        )
        library = self.load()
        self.assertIn("narrator.system", library.errors)
        self.assertNotIn("narrator.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_python_object_tags_are_rejected_not_constructed(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: !!python/object/apply:os.getcwd []\n",
        )
        library = self.load()
        self.assertIn("narrator.system", library.errors)
        self.assertNotIn("narrator.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_character_creation_failure_is_a_warning_never_a_blocker(self):
        self.write_file(
            "character_creation.yaml",
            "schema_version: 1\nprompts:\n  character_creation.system: {bad}\n",
        )
        library = self.load()
        self.assertIn("character_creation.system", library.errors)
        self.assertIn("narrator.system", library.texts)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_unavailable_key_rendering_raises_a_named_error(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: 旁白 {nmme}。\n",
        )
        self.load()
        with self.assertRaises(PromptUnavailableError) as ctx:
            render_prompt("narrator.system")
        message = str(ctx.exception)
        self.assertIn("narrator.yaml", message)
        self.assertIn("narrator.system", message)
        self.assertIn("prompt key unavailable", message)


class RenderContractTests(PromptFixture):
    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_render_of_unavailable_key_raises_named_error(self):
        self.write_file(
            "npc.yaml",
            "schema_version: 1\nprompts:\n  npc.thinking: （{name} {oops}）\n",
        )
        self.load()
        with self.assertRaises(PromptUnavailableError):
            render_prompt("npc.thinking", name="甲")

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_consumer_typo_in_supplied_values_is_rejected(self):
        self.load()
        with self.assertRaises(UnexpectedPromptValueError) as ctx:
            render_prompt("npc.thinking", name="甲", namme="乙")
        message = str(ctx.exception)
        self.assertIn("namme", message)
        self.assertIn("npc.thinking", message)

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_unknown_key_rendering_raises_named_error(self):
        self.load()
        with self.assertRaises(UnknownPromptKeyError):
            render_prompt("no.such.key")

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_render_is_byte_identical_for_identical_input(self):
        self.load()
        first = render_prompt("art.character_description", race="貓人族", name="艾琳", age="24", style="approved visual style")
        second = render_prompt("art.character_description", race="貓人族", name="艾琳", age="24", style="approved visual style")
        self.assertEqual(first, second)
        self.assertEqual(first, "A 貓人族 adult named 艾琳 (24) in the approved visual style.")


class LoadLifecycleTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_prompt_library()

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_concurrent_auto_load_and_explicit_load_never_leaves_none(self):
        import threading

        reset_prompt_library()
        results: list[str] = []
        barrier = threading.Barrier(3)

        def renderer():
            barrier.wait()
            results.append(render_prompt("narrator.system"))

        def loader():
            barrier.wait()
            load_prompt_library(str(REPO_PROMPTS))

        threads = [threading.Thread(target=renderer) for _ in range(2)]
        threads.append(threading.Thread(target=loader))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertEqual(len(results), 2)
        for text in results:
            self.assertIn("伊洛瑟恩大陸", text)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_first_use_auto_loads_from_the_default_root(self):
        reset_prompt_library()
        text = render_prompt("narrator.system")
        self.assertIn("伊洛瑟恩大陸", text)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_reset_then_explicit_root_reload_without_state_leak(self):
        import shutil
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(REPO_PROMPTS, root, dirs_exist_ok=True)
            (root / "narrator.yaml").write_text(
                "schema_version: 1\nprompts:\n  narrator.system: 測試旁白。\n",
                encoding="utf-8",
            )
            load_prompt_library(str(root))
            self.assertEqual(render_prompt("narrator.system"), "測試旁白。")
            reset_prompt_library()
            self.assertIn("伊洛瑟恩大陸", render_prompt("narrator.system"))


if __name__ == "__main__":
    unittest.main()
