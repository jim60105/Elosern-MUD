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
                "scene_builder.yaml",
                "npc.yaml",
                "art.yaml",
                "character_creation.yaml",
                "action_options.yaml",
                "title_nomination.yaml",
            },
        )

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt")
    def test_scene_flavor_key_is_registered_with_four_scene_placeholders(self):
        library = load_prompt_library(str(REPO_PROMPTS))
        self.assertIn("scene_builder.system", library.texts)
        self.assertIn("scene_builder.system", PROMPT_SPECS)
        spec = PROMPT_SPECS["scene_builder.system"]
        self.assertEqual(
            set(spec.allowed_placeholders),
            {"scene_sentence", "quest_context", "room_name", "region"},
        )
        text = render_prompt(
            "scene_builder.system",
            scene_sentence="古老森林深處的祭壇",
            quest_context="採集任務：採集靈藥草",
            room_name="林間祭壇",
            region="遺忘森林",
        )
        self.assertIn("古老森林深處的祭壇", text)
        self.assertIn("採集任務：採集靈藥草", text)
        self.assertIn("林間祭壇", text)
        self.assertIn("遺忘森林", text)
        self.assertNotIn("{scene_sentence}", text)
        self.assertNotIn("{quest_context}", text)
        self.assertNotIn("{room_name}", text)
        self.assertNotIn("{region}", text)

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt")
    def test_character_creation_key_is_registered_with_concept_placeholders(self):
        library = load_prompt_library(str(REPO_PROMPTS))
        self.assertIn("character_creation.system", library.texts)
        self.assertIn("character_creation.system", PROMPT_SPECS)
        spec = PROMPT_SPECS["character_creation.system"]
        self.assertEqual(
            set(spec.allowed_placeholders), {"concept", "race_catalog"}
        )
        text = render_prompt(
            "character_creation.system",
            concept="流浪的精靈劍士",
            race_catalog="種族：human（…）",
        )
        self.assertIn("流浪的精靈劍士", text)
        self.assertIn("種族：human（…）", text)
        self.assertNotIn("{concept}", text)
        self.assertNotIn("{race_catalog}", text)

    @covers_requirement("ai-action-options-prompts::prompts-action-options-yaml-ships-the-system-and-user-prompt-keys", "ai-action-options-prompts::the-registry-declares-the-action-options-entries-with-an-exact-placeholder-allowlist")
    def test_action_options_keys_are_registered_with_split_allowlists(self):
        library = load_prompt_library(str(REPO_PROMPTS))
        for key in ("action_options.system", "action_options.user"):
            self.assertIn(key, library.texts)
            self.assertIn(key, PROMPT_SPECS)
        system = PROMPT_SPECS["action_options.system"]
        user = PROMPT_SPECS["action_options.user"]
        self.assertEqual(system.allowed_placeholders, ())
        self.assertEqual(
            set(user.allowed_placeholders),
            {
                "room_name",
                "room_summary",
                "npc_entries",
                "monster_entries",
                "objective",
                "narrative_tail",
                "affordances",
            },
        )
        self.assertEqual(system.file, "action_options.yaml")
        self.assertEqual(user.file, "action_options.yaml")

    @covers_requirement("ai-action-options-prompts::prompts-action-options-yaml-ships-the-system-and-user-prompt-keys")
    def test_action_options_system_prompt_forbids_hidden_values(self):
        load_prompt_library(str(REPO_PROMPTS))
        text = render_prompt("action_options.system")
        self.assertIn("不得出現任何數字", text)
        self.assertIn("不得洩漏隱藏數值", text)
        self.assertIn("不得虛構目標", text)
        self.assertIn("正體中文", text)
        self.assertIn("npc_index、params", text)

    @covers_requirement("ai-action-options-prompts::prompts-action-options-yaml-ships-the-system-and-user-prompt-keys", "ai-action-options-prompts::the-registry-declares-the-action-options-entries-with-an-exact-placeholder-allowlist")
    def test_action_options_user_renders_the_seven_context_fields_exactly_once(self):
        load_prompt_library(str(REPO_PROMPTS))
        text = render_prompt(
            "action_options.user",
            room_name="林間祭壇",
            room_summary="古老森林深處的祭壇",
            npc_entries="1. 艾洛西亞（npc_index=0）",
            monster_entries="無",
            objective="採集靈藥草",
            narrative_tail="你沿著小徑走進森林。",
            affordances="explore.look",
        )
        for value in (
            "林間祭壇",
            "古老森林深處的祭壇",
            "1. 艾洛西亞（npc_index=0）",
            "採集靈藥草",
            "你沿著小徑走進森林。",
            "explore.look",
        ):
            self.assertEqual(text.count(value), 1)
        for token in (
            "{room_name}",
            "{room_summary}",
            "{npc_entries}",
            "{monster_entries}",
            "{objective}",
            "{narrative_tail}",
            "{affordances}",
        ):
            self.assertNotIn(token, text)

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_allowlisted_placeholders_are_substituted_exactly_once(self):
        load_prompt_library(str(REPO_PROMPTS))
        text = render_prompt(
            "npc_dialogue.system",
            name="艾洛西亞",
            desc="南門的守衛",
            location="王都",
            persona="",
        )
        self.assertEqual(text.count("艾洛西亞"), 1)
        self.assertEqual(text.count("南門的守衛"), 1)
        self.assertEqual(text.count("王都"), 1)
        self.assertNotIn("{name}", text)
        self.assertNotIn("{desc}", text)
        self.assertNotIn("{location}", text)

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_persona_placeholder_is_allowlisted_and_substituted_exactly_once(self):
        load_prompt_library(str(REPO_PROMPTS))
        block = "性格：沉穩\n人生經歷：曾在邊境服役\n習慣：清晨練劍"
        text = render_prompt(
            "npc_dialogue.system",
            name="艾洛西亞",
            desc="南門的守衛",
            location="王都",
            persona=block,
        )
        self.assertEqual(text.count(block), 1)
        self.assertNotIn("{persona}", text)

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_empty_persona_value_substitutes_without_error_or_literal_token(self):
        load_prompt_library(str(REPO_PROMPTS))
        text = render_prompt(
            "npc_dialogue.system",
            name="艾洛西亞",
            desc="南門的守衛",
            location="王都",
            persona="",
        )
        self.assertNotIn("{persona}", text)
        self.assertNotIn("性格：", text)
        self.assertTrue(text.startswith("你是《伊洛瑟恩大陸》中的 艾洛西亞。"))

    @covers_requirement("prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically")
    def test_double_braced_tokens_and_json_braces_pass_through(self):
        load_prompt_library(str(REPO_PROMPTS))
        scenario = render_prompt(
            "scenario_director.system", name_inspiration="加斯帕・斯諾"
        )
        self.assertIn('{"name": "…"', scenario)
        self.assertIn('"item_key": "healing_potion"', scenario)
        dialogue = render_prompt(
            "npc_dialogue.system", name="甲", desc="乙", location="丙", persona=""
        )
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
    def test_scene_builder_unknown_placeholder_is_a_load_time_error(self):
        self.write_file(
            "scene_builder.yaml",
            "schema_version: 1\nprompts:\n  scene_builder.system: 場景 {nmme}。\n",
        )
        library = self.load()
        error = library.errors["scene_builder.system"]
        self.assertIn("unknown placeholder", error.problem)
        self.assertIn("nmme", error.problem)
        self.assertNotIn("scene_builder.system", library.texts)

    @covers_requirement("ai-action-options-prompts::the-registry-declares-the-action-options-entries-with-an-exact-placeholder-allowlist")
    def test_action_options_hostile_fixture_records_unknown_placeholder_errors(self):
        import shutil

        shutil.copyfile(
            REPO_PROMPTS / "tests" / "action_options.yaml",
            self.root / "action_options.yaml",
        )
        library = self.load()
        for key in ("action_options.system", "action_options.user"):
            error = library.errors[key]
            self.assertIn("unknown placeholder", error.problem)
            self.assertIn("nmme", error.problem)
            self.assertNotIn(key, library.texts)
        self.assertIn("narrator.system", library.texts)

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


class ArtGenerationPromptTests(PromptFixture):
    """The three art generation prompt keys that feed the sd-webui client."""

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt")
    def test_art_generation_keys_load_and_render_deterministically(self):
        library = self.load()
        for key in ("art.scene_prompt", "art.portrait_prompt", "art.negative_prompt"):
            self.assertIn(key, library.texts)
        scene = render_prompt("art.scene_prompt", description="desc")
        portrait = render_prompt("art.portrait_prompt", description="desc")
        negative = render_prompt("art.negative_prompt")
        self.assertIn("desc", scene)
        self.assertIn("desc", portrait)
        self.assertNotIn("{description}", scene)
        self.assertNotIn("{description}", portrait)
        self.assertNotIn("{", negative)
        self.assertEqual(scene, render_prompt("art.scene_prompt", description="desc"))
        self.assertEqual(portrait, render_prompt("art.portrait_prompt", description="desc"))

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_art_generation_keys_reject_unknown_placeholders(self):
        self.write_file(
            "art.yaml",
            "schema_version: 1\n"
            "prompts:\n"
            "  art.style: approved visual style\n"
            "  art.scene_prompt: 場景 {nmme}。\n",
        )
        library = self.load()
        error = library.errors["art.scene_prompt"]
        self.assertIn("unknown placeholder", error.problem)
        self.assertIn("nmme", error.problem)
        self.assertNotIn("art.scene_prompt", library.texts)

    def test_editing_an_art_template_changes_the_rendered_prompt_text(self):
        library = self.load()
        before = render_prompt("art.scene_prompt", description="desc")
        self.write_file(
            "art.yaml",
            "schema_version: 1\n"
            "prompts:\n"
            "  art.style: approved visual style\n"
            "  art.character_description: |-\n"
            "    A {race} adult named {name} ({age}) in the {style}.\n"
            "  art.monster_description: '{description} ({display_name}；例如：{examples})'\n"
            "  art.negative_prompt: lowres, text\n"
            "  art.portrait_prompt: |-\n"
            "    A portrait — {description} — painted.\n"
            "  art.scene_prompt: |-\n"
            "    A wide scene — {description} — painted.\n",
        )
        self.load()
        after = render_prompt("art.scene_prompt", description="desc")
        self.assertNotEqual(before, after)
        self.assertEqual(library.unavailable, frozenset())


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


class ScenarioDirectorNameInspirationTests(PromptFixture):
    """The namegen-npc-flow placeholder contract for scenario_director.system."""

    @covers_requirement("prompt-library::the-scenario-director-key-is-registered-with-the-name-inspiration-placeholder-and-carries-the-naming-guidance")
    def test_key_allowlist_is_exactly_name_inspiration(self):
        spec = PROMPT_SPECS["scenario_director.system"]
        self.assertEqual(spec.allowed_placeholders, ("name_inspiration",))

    @covers_requirement("prompt-library::the-scenario-director-key-is-registered-with-the-name-inspiration-placeholder-and-carries-the-naming-guidance")
    def test_shipped_text_carries_token_and_inspiration_guidance(self):
        library = self.load()
        text = library.texts["scenario_director.system"]
        self.assertIn("{name_inspiration}", text)
        self.assertIn("僅供靈感", text)
        self.assertIn("建議填寫 display_name", text)
        self.assertIn("仍為選填", text)

    @covers_requirement("prompt-library::the-scenario-director-key-is-registered-with-the-name-inspiration-placeholder-and-carries-the-naming-guidance")
    def test_typo_placeholder_outside_allowlist_is_rejected(self):
        self.write_file(
            "scenario_director.yaml",
            "schema_version: 1\nprompts:\n  scenario_director.system: 任務 {name_inspiraton}。\n",
        )
        library = self.load()
        error = library.errors["scenario_director.system"]
        self.assertIn("unknown placeholder", error.problem)
        self.assertIn("name_inspiraton", error.problem)
        self.assertNotIn("scenario_director.system", library.texts)

    @covers_requirement("prompt-library::the-scenario-director-key-is-registered-with-the-name-inspiration-placeholder-and-carries-the-naming-guidance")
    def test_text_without_the_token_still_loads_and_renders(self):
        # A key renders with the tokens it declares: an admin rewrite that
        # drops the placeholder is valid, and passing the value anyway is the
        # consumer's business, not a load failure.
        self.write_file(
            "scenario_director.yaml",
            "schema_version: 1\nprompts:\n  scenario_director.system: 任務企劃。\n",
        )
        library = self.load()
        self.assertEqual(library.texts["scenario_director.system"], "任務企劃。")
        self.assertEqual(render_prompt("scenario_director.system"), "任務企劃。")


if __name__ == "__main__":
    unittest.main()
