"""Pure-logic tests for the onboarding data package (D1/D2).

These are read-only unit tests: ``guide.py`` and the data modules must import
nothing from ``world.rules``, ``typeclasses``, or Evennia. One test per beat and
per keyword group, plus the import-graph cycle guard.
"""

from tools.spec_traceability import covers_requirement

import ast
from pathlib import Path
import unittest

from world.onboarding.guide import (
    GuideProgress,
    OnboardingSnapshot,
    arrival_scene,
    dialogue_response,
    guide_should_prompt,
    next_beat_output,
    room_entry_decision,
)
from world.onboarding.guide_dialogue import (
    DIALOGUE_TABLE,
    GUARD_DIALOGUE_KEY,
    GUILD_STAFF_DIALOGUE_KEY,
    DialogueDefinition,
    NO_UNDERSTANDING_LINE,
)
from world.onboarding.scenes import (
    BEAT_REGISTRY,
    GUIDANCE_BEAT_ID,
    GUIDED_CORRIDOR,
    GUILD_EXTERIOR_ROOM_KEY,
    LOOK_BEAT_ID,
    SOUTH_GATE_ROOM_KEY,
    TriggerKind,
)

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN = ("world.rules", "typeclasses", "evennia")


def _snapshot(**overrides) -> OnboardingSnapshot:
    values = {
        "onboarded": False,
        "onboarding_beat": None,
        "guide_progress": None,
        "first_arrival_seen": False,
        "location_key": SOUTH_GATE_ROOM_KEY,
    }
    values.update(overrides)
    return OnboardingSnapshot(**values)


class SceneBeatTests(unittest.TestCase):
    def test_every_beat_has_a_registry_entry(self):
        for beat in BEAT_REGISTRY.values():
            self.assertIsInstance(beat.beat_id, str)
            self.assertTrue(beat.prose)
            self.assertIn(beat.trigger, TriggerKind)

    def test_look_beat_advances_to_guidance(self):
        self.assertEqual(BEAT_REGISTRY[LOOK_BEAT_ID].trigger, TriggerKind.COMMAND_LOOK)
        self.assertEqual(BEAT_REGISTRY[LOOK_BEAT_ID].next_beat_id, GUIDANCE_BEAT_ID)

    def test_look_beat_prompts_the_localized_look_command(self):
        prose = BEAT_REGISTRY[LOOK_BEAT_ID].prose
        self.assertIn("先用「看」看看四周", prose)
        self.assertNotIn("look 看看", prose)

    def test_guidance_beat_prompts_two_step_route_to_guild(self):
        prose = BEAT_REGISTRY[GUIDANCE_BEAT_ID].prose
        self.assertIn("先向北走到南大道", prose)
        self.assertIn("再向東到冒險者公會外", prose)
        self.assertNotIn("中央廣場", prose)
        self.assertIsNone(BEAT_REGISTRY[GUIDANCE_BEAT_ID].next_beat_id)

    def test_guided_corridor_contains_the_four_documented_rooms(self):
        self.assertEqual(
            GUIDED_CORRIDOR,
            frozenset({"南門", "南大道", "中央廣場", "冒險者公會外"}),
        )
        self.assertIn(GUILD_EXTERIOR_ROOM_KEY, GUIDED_CORRIDOR)


class MapRouteTests(unittest.TestCase):
    def test_guild_route_matches_the_capital_grid(self):
        from world.maps.altoria_capital import PROTOTYPES

        def key_at(xy):
            return PROTOTYPES[xy]["key"]

        self.assertEqual(key_at((2, 0)), "南門")
        self.assertEqual(key_at((2, 1)), "南大道")
        self.assertEqual(key_at((3, 1)), "冒險者公會外")

    def test_guidance_never_directs_through_the_plaza(self):
        prose = BEAT_REGISTRY[GUIDANCE_BEAT_ID].prose
        self.assertNotIn("中央廣場", prose)
        from world.maps.altoria_capital import PROTOTYPES

        self.assertEqual(PROTOTYPES[(2, 2)]["key"], "中央廣場")


class ArrivalSceneTests(unittest.TestCase):
    def test_first_arrival_returns_arrival_and_look_beats(self):
        beats = arrival_scene(_snapshot())
        self.assertIsNotNone(beats)
        self.assertEqual(
            [beat.beat_id for beat in beats], ["arrival", LOOK_BEAT_ID]
        )

    def test_onboarded_player_never_sees_the_scene(self):
        self.assertIsNone(arrival_scene(_snapshot(onboarded=True)))

    def test_scene_only_plays_at_the_south_gate(self):
        self.assertIsNone(arrival_scene(_snapshot(location_key="中央廣場")))

    def test_completed_arrival_never_replays(self):
        self.assertIsNone(arrival_scene(_snapshot(first_arrival_seen=True)))


class BeatAdvanceTests(unittest.TestCase):
    def test_look_beat_advances_to_guidance(self):
        output = next_beat_output(_snapshot(onboarding_beat=LOOK_BEAT_ID))
        self.assertIsNotNone(output)
        self.assertEqual(output.beat.beat_id, GUIDANCE_BEAT_ID)
        self.assertIsNone(output.next_beat_id)

    def test_unknown_beat_has_no_output(self):
        self.assertIsNone(next_beat_output(_snapshot(onboarding_beat="nope")))

    def test_guidance_beat_has_no_further_continuation(self):
        self.assertIsNone(next_beat_output(_snapshot(onboarding_beat=GUIDANCE_BEAT_ID)))


class GuideProgressTests(unittest.TestCase):
    def test_schema_round_trips_through_storage(self):
        progress = GuideProgress.active().with_keyword("公會")
        self.assertEqual(
            GuideProgress.from_storage(progress.to_storage()), progress
        )

    def test_active_and_terminal_states_are_accepted(self):
        for state in ("active", "completed", "skipped"):
            progress = GuideProgress(state=state, seen_keywords=("再見",))
            self.assertEqual(GuideProgress.from_storage(progress.to_storage()), progress)

    def test_invalid_state_is_rejected(self):
        with self.assertRaises(ValueError):
            GuideProgress.from_storage({"state": "bogus", "seen_keywords": []})

    def test_keyword_is_recorded_once(self):
        progress = GuideProgress.active().with_keyword("公會").with_keyword("公會")
        self.assertEqual(progress.seen_keywords, ("公會",))


class RoomEntryTests(unittest.TestCase):
    def test_guild_exterior_completes_guidance(self):
        self.assertEqual(
            room_entry_decision(_snapshot(), GUILD_EXTERIOR_ROOM_KEY), "completed"
        )

    def test_room_outside_corridor_skips_guidance(self):
        self.assertEqual(room_entry_decision(_snapshot(), "神殿街"), "skipped")

    def test_corridor_room_keeps_guidance_active(self):
        self.assertIsNone(room_entry_decision(_snapshot(), "中央廣場"))

    def test_onboarded_player_gets_no_decision(self):
        self.assertIsNone(
            room_entry_decision(_snapshot(onboarded=True), "神殿街")
        )

    def test_ended_guide_never_transitions_again(self):
        for state in ("completed", "skipped"):
            with self.subTest(state=state):
                self.assertIsNone(
                    room_entry_decision(
                        _snapshot(guide_progress=GuideProgress(state=state)),
                        "神殿街",
                    )
                )
                self.assertIsNone(
                    room_entry_decision(
                        _snapshot(guide_progress=GuideProgress(state=state)),
                        GUILD_EXTERIOR_ROOM_KEY,
                    )
                )


class DialogueTableTests(unittest.TestCase):
    def test_known_keywords_return_authored_responses(self):
        definition = DIALOGUE_TABLE[GUARD_DIALOGUE_KEY]
        self.assertIsNone(definition.greeting)
        for keyword in ("公會", "冒險", "危險", "再見"):
            with self.subTest(keyword=keyword):
                self.assertEqual(
                    dialogue_response(GUARD_DIALOGUE_KEY, keyword),
                    next(
                        entry.response
                        for entry in definition.responses
                        if entry.keyword == keyword
                    ),
                )

    def test_guild_keyword_points_east_of_south_street(self):
        response = dialogue_response(GUARD_DIALOGUE_KEY, "公會")
        self.assertIn("先向北走到南大道", response)
        self.assertIn("再向東", response)
        self.assertNotIn("中央廣場", response)

    def test_unknown_keyword_returns_no_understanding(self):
        self.assertEqual(
            dialogue_response(GUARD_DIALOGUE_KEY, "謎語"), NO_UNDERSTANDING_LINE
        )

    def test_unknown_dialogue_key_returns_no_understanding(self):
        self.assertEqual(dialogue_response("nope", "公會"), NO_UNDERSTANDING_LINE)


class GuildStaffDialogueTests(unittest.TestCase):
    def test_dialogue_table_is_read_only_at_runtime(self):
        from types import MappingProxyType

        self.assertIsInstance(DIALOGUE_TABLE, MappingProxyType)
        with self.assertRaises(TypeError):
            DIALOGUE_TABLE["bogus"] = DialogueDefinition("x", ())
        with self.assertRaises((TypeError, AttributeError)):
            DIALOGUE_TABLE.pop(GUILD_STAFF_DIALOGUE_KEY)

    def test_guild_staff_table_is_registered_and_frozen(self):
        definition = DIALOGUE_TABLE[GUILD_STAFF_DIALOGUE_KEY]
        self.assertIsInstance(definition.greeting, str)
        self.assertTrue(definition.greeting)
        self.assertIn("guild register", definition.greeting)

    def test_guild_staff_greeting_teaches_the_guild_commands(self):
        definition = DIALOGUE_TABLE[GUILD_STAFF_DIALOGUE_KEY]
        for command in (
            "guild register",
            "guild list",
            "guild accept",
            "guild log",
            "guild show",
            "guild turnin",
            "guild abandon",
            "guild merit",
        ):
            with self.subTest(command=command):
                self.assertTrue(
                    command in definition.greeting
                    or any(command in entry.response for entry in definition.responses)
                )

    def test_guild_staff_answers_known_keywords(self):
        definition = DIALOGUE_TABLE[GUILD_STAFF_DIALOGUE_KEY]
        for keyword in ("公會", "任務", "註冊", "回報", "再見"):
            with self.subTest(keyword=keyword):
                response = dialogue_response(GUILD_STAFF_DIALOGUE_KEY, keyword)
                self.assertNotEqual(response, NO_UNDERSTANDING_LINE)

    def test_guild_staff_teaches_the_dialogue_turnin_path(self):
        definition = DIALOGUE_TABLE[GUILD_STAFF_DIALOGUE_KEY]
        combined = definition.greeting + "".join(
            entry.response for entry in definition.responses
        )
        self.assertIn("回報", combined)
        self.assertIn("任務編號", combined)

    def test_turnin_keyword_response_teaches_register_first(self):
        response = dialogue_response(GUILD_STAFF_DIALOGUE_KEY, "回報")
        self.assertIn("guild register", response)


class GuidePromptTests(unittest.TestCase):
    def test_active_guide_prompts(self):
        self.assertTrue(guide_should_prompt(_snapshot(guide_progress=GuideProgress.active())))

    def test_completed_guide_does_not_prompt(self):
        self.assertFalse(
            guide_should_prompt(
                _snapshot(guide_progress=GuideProgress(state="completed"))
            )
        )

    def test_skipped_guide_does_not_prompt(self):
        self.assertFalse(
            guide_should_prompt(
                _snapshot(guide_progress=GuideProgress(state="skipped"))
            )
        )

    def test_onboarded_player_does_not_prompt(self):
        self.assertFalse(guide_should_prompt(_snapshot(onboarded=True)))


class ImportGraphGuardTests(unittest.TestCase):
    def test_onboarding_modules_import_no_rules_typeclasses_or_evennia(self):
        for relative in (
            "__init__.py",
            "scenes.py",
            "guide_dialogue.py",
            "guide.py",
        ):
            with self.subTest(module=relative):
                tree = ast.parse(
                    (_PACKAGE_ROOT / relative).read_text(encoding="utf-8"),
                    filename=relative,
                )
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for forbidden in _FORBIDDEN:
                            self.assertNotIn(
                                module,
                                forbidden,
                                f"{relative} imports forbidden module {module!r}",
                            )


if __name__ == "__main__":
    unittest.main()
