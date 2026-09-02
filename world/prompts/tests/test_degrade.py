"""Bounded per-key failure tests for the prompt library (prompt-library).

A broken prompt key must never take the deterministic game offline: loading
records the named error and marks only that key unavailable, and the consuming
generative layer resolves to its existing deterministic degrade path. Mirrors
design D3's mapping: narrator → template renderer, npc-dialogue → the
``None``/greeting marker, scenario-director → template pool, thinking → no
echo, art → deterministic registry-driven fallback.
"""

from __future__ import annotations

import types
import unittest

from django.test import override_settings

from world.ai import guardrail
from world.ai.fake_client import FakeLLMClient
from world.ai.narrator import narrate_event_logs, register_narrator
from world.ai.npc_dialogue import generate_npc_reply, register_npc_dialogue
from world.ai.profiles import default_profiles
from world.ai.scenario_director import generate_quest_blueprint, register_scenario_director
from world.prompts.loader import (
    PromptUnavailableError,
    load_prompt_library,
    render_prompt,
)
from world.rules.event_log import EventEntry, EventLog, render_plain_text

from tools.spec_traceability import covers_requirement

from world.prompts.tests.fixtures import PromptFixture



def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _semantic_reset():
    guardrail._semantic_validators.clear()


def _fallback_reset():
    guardrail._degrade_fallbacks.clear()


def _schema_reset():
    from world.ai.schemas.registry import _OUTPUT_SCHEMAS

    _OUTPUT_SCHEMAS.clear()


def _reset_all():
    _semantic_reset()
    _fallback_reset()
    _schema_reset()


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _log():
    return EventLog(
        actor="elosia",
        skill_key="basic_attack",
        targets=("violet",),
        entries=(
            EventEntry(
                kind="damage",
                actor="elosia",
                target="violet",
                data={"amount": 12},
                text_template="{actor} 對 {target} 造成 {data[amount]} 點傷害。",
            ),
        ),
        time_cost_seconds=5,
    )


def _join_renderer(logs):
    return "\n".join(render_plain_text(log) for log in logs)


class BoundedFailureDegradeTests(PromptFixture):
    def tearDown(self) -> None:
        _reset_all()
        super().tearDown()

    def _break_narrator(self):
        self.write_file(
            "narrator.yaml",
            "schema_version: 1\nprompts:\n  narrator.system: 旁白 {nmme}。\n",
        )

    def _break_npc_dialogue(self):
        self.write_file(
            "npc_dialogue.yaml",
            "schema_version: 1\nprompts:\n  npc_dialogue.system: 對話 {oops}。\n",
        )

    def _break_scenario_director(self):
        self.write_file(
            "scenario_director.yaml",
            "schema_version: 1\nprompts:\n  scenario_director.system: 任務 {oops}。\n",
        )

    def _break_npc_thinking(self):
        self.write_file(
            "npc.yaml",
            "schema_version: 1\nprompts:\n  npc.thinking: （{name} {oops}）\n",
        )

    def _break_character_creation(self):
        self.write_file(
            "character_creation.yaml",
            "schema_version: 1\nprompts:\n  character_creation.system: 創角 {oops}。\n",
        )

    def _break_art(self):
        self.write_file(
            "art.yaml",
            "schema_version: 1\nprompts:\n  art.style: approved visual style\n"
            "  art.character_description: A {race} adult named {name} ({age}) in the {style}.\n"
            "  art.character_description: A {race} adult named {name} ({age}) in the {style}.\n"
            "  art.monster_description: \"{description} ({display_name}；例如：{examples})\"\n",
        )

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_broken_key_marks_only_its_key_unavailable_at_startup(self):
        self._break_narrator()
        library = self.load()
        self.assertIn("narrator.system", library.errors)
        self.assertEqual(library.unavailable, frozenset({"narrator.system"}))

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer", "narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_broken_narrator_key_degrades_to_template_rendering(self):
        self._break_narrator()
        self.load()
        _reset_all()
        register_narrator(_join_renderer)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, _join_renderer((_log(),)))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer", "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_broken_npc_dialogue_key_resolves_to_none_greeting_marker(self):
        self._break_npc_dialogue()
        self.load()
        _reset_all()
        register_npc_dialogue()
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context={"name": "甲", "desc": "乙", "location": "丙"},
                player_context={"name": "薇歐蕾", "disguised_stats": {}},
                memory=[],
            )
            result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer", "scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_broken_scenario_director_key_draws_from_the_template_pool(self):
        self._break_scenario_director()
        self.load()
        _reset_all()
        register_scenario_director()
        client = FakeLLMClient()
        context = {
            "requested_type": "討伐",
            "allowed_rank": "F",
            "issuer_branch": "guild_branch_altoria",
            "anchor": "capital_altoria",
        }
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=context)
            blueprint = await_result(d)
        self.assertIsNotNone(blueprint)
        self.assertEqual(blueprint.quest_type, "討伐")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_broken_thinking_key_degrades_to_no_echo(self):
        self._break_npc_thinking()
        self.load()
        from typeclasses.npcs import LLMNPC

        npc = types.SimpleNamespace(
            key="甲",
            db=types.SimpleNamespace(thinking_messages=None),
        )
        self.assertEqual(LLMNPC._thinking_text(npc), "")

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer", "art-subject-model::subject-descriptions-are-deterministic-adult-safe-and-exclude-non-physical-truth")
    def test_broken_art_file_degrades_to_deterministic_fallback_descriptions(self):
        from unittest.mock import Mock

        from world.art.subjects import (
            character_description,
            description_for,
            monster_description,
            monster_subject_for,
            scene_subject_for,
        )

        self._break_art()
        library = self.load()
        self.assertIn("art.character_description", library.errors)
        self.assertIn("art.style", library.errors)

        scene = scene_subject_for("forest_path")
        self.assertEqual(
            description_for(scene),
            "陽光穿過層疊的枝葉，灑在一條蜿蜒的林間小徑上，四周寂靜得只剩下風聲。",
        )

        character = Mock()
        character.db.display_name = "艾琳"
        character.db.race = "beastfolk"
        character.db.subrace = "catkin"
        character.key = "艾琳"
        text = character_description(character, 24)
        self.assertIn("艾琳", text)
        self.assertIn("貓人族", text)
        self.assertIn("24", text)

        monster = monster_subject_for("low")
        self.assertEqual(
            monster_description(monster),
            "Threats a beginning adventurer can handle alone.",
        )

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_broken_character_creation_key_degrades_to_the_unavailable_marker(self):
        from world.ai.character_creation import (
            generate_character_proposal,
            register_character_creation,
        )

        self._break_character_creation()
        self.load()
        _reset_all()
        register_character_creation()
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_character_proposal(client, concept="流浪的精靈劍士")
            result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_render_of_broken_key_raises_named_error_for_loud_consumers(self):
        self._break_narrator()
        self.load()
        with self.assertRaises(PromptUnavailableError):
            render_prompt("narrator.system")

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_every_other_layer_keeps_working_while_one_key_is_down(self):
        self._break_narrator()
        library = self.load()
        self.assertEqual(library.unavailable, frozenset({"narrator.system"}))
        thinking = render_prompt("npc.thinking", name="甲")
        self.assertEqual(thinking, "（甲 沉思片刻……）")

    @covers_requirement("prompt-library::the-loader-validates-every-prompt-key-and-bounds-failures-to-the-affected-layer")
    def test_startup_seam_never_aborts_even_if_the_loader_itself_throws(self):
        from unittest.mock import patch

        from server.conf import at_server_startstop as hooks

        with patch("world.lore.sync.sync_all"), patch(
            "world.maps.bootstrap.sync_grid"
        ), patch("world.maps.bootstrap.sync_wilderness"), patch(
            "world.maps.bootstrap.sync_service_interiors"
        ), patch("world.quests.bootstrap.sync_quest_runtime"), patch(
            "world.rules.guild_economy.sync_guild_economy"
        ), patch("world.rules.onboarding.sync_guard_npc"), patch(
            "world.rules.clock.get_world_clock"
        ), patch("world.art.service.art_sync_all"), patch(
            "web.webclient.presentation.art_push.connect_art_push"
        ), patch(
            "world.prompts.loader.load_prompt_library",
            side_effect=RuntimeError("unexpected loader bug"),
        ), patch(
            "server.conf.at_server_startstop._register_narrator_layer"
        ) as register_narrator, patch(
            "server.conf.at_server_startstop._register_npc_dialogue_layer"
        ), patch(
            "server.conf.at_server_startstop._register_scenario_director_layer"
        ), patch(
            "server.conf.at_server_startstop._register_character_creation_layer"
        ):
            hooks.at_server_start()
        register_narrator.assert_called_once()


class LoaderExceptionChainTests(PromptFixture):
    """Swallowed OS/YAML failures stay reachable through ``__cause__``."""

    def test_parse_failure_keeps_the_underlying_cause(self):
        # The duplicate-key loader error names the real failure; the recorded
        # PromptLibraryError must chain to it so the facade renders the
        # causal type/traceback, not just the flattened message string.
        self.write_file(
            "art.yaml",
            "schema_version: 1\nprompts:\n"
            "  art.style: approved visual style\n"
            "  art.style: approved visual style\n",
        )
        library = self.load()
        error = library.errors["art.style"]
        self.assertIsNotNone(error.__cause__)
        self.assertIsInstance(error.__cause__, Exception)

    def test_root_listing_failure_keeps_the_os_error_cause(self):
        # A prompt root that cannot be listed records per-key errors chained
        # to the underlying OSError (rubber-duck P3 MAJOR: loader swallowed
        # the exception chain).
        import unittest.mock

        with unittest.mock.patch(
            "world.prompts.loader.os.listdir",
            side_effect=OSError("permission denied"),
        ):
            library = self.load()
        self.assertTrue(library.errors)
        for error in library.errors.values():
            self.assertIsInstance(error.__cause__, OSError)


if __name__ == "__main__":
    unittest.main()
