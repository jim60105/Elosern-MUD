"""Scenario-director occupant card contract: proposal type, schema, budget, prompt.

Covers npc-persona-generated-quest-cards tasks 1.1-1.3: the frozen
``BlueprintPersona`` carrier and its payload round trip, the ``npc_req``
output-schema card object, the whole-blueprint occupant cap, the worked
token-budget sizing heuristic, and the system prompt's card instructions.
Every fixture is synthetic; identifier rows resolve through the shared
director helpers' live-registry probes.
"""

from dataclasses import FrozenInstanceError
import copy
import json
import unittest

from jsonschema import Draft7Validator

from tools.spec_traceability import covers_requirement
from world.ai.profiles import SCENARIO_DIRECTOR_MAX_TOKENS, build_profiles, default_profiles
from world.ai.scenario_director import (
    MAX_BLUEPRINT_OCCUPANTS,
    SCENARIO_DIRECTOR_OUTPUT_SCHEMA,
    BlueprintPersona,
    QuestBlueprint,
    _VALIDATORS,
    build_scenario_prompt,
)
from world.ai.tests._director_helpers import _context, _instance_payload
from world.lore.npc_card import (
    CARD_BLOCK_LIMIT,
    IDENTITY_SECTION_LIMIT,
    LEAF_LIMIT,
    NPC_CARD_FIELDS,
    normalize_card,
    render_card_block,
)
from world.quests.tests._card_fixtures import occupant_card_record


def _schema_errors(payload):
    validator = Draft7Validator(SCENARIO_DIRECTOR_OUTPUT_SCHEMA)
    return [error.message for error in validator.iter_errors(payload)]


def _semantic_errors(payload):
    errors = []
    for validate in _VALIDATORS.values():
        errors.extend(validate(payload))
    return errors


def _occupant(position):
    entry = copy.deepcopy(_instance_payload()["stages"][0]["npc_req"][0])
    entry["display_name"] = f"測試住民{'甲乙丙丁戊'[position]}"
    entry["persona"] = occupant_card_record(str(position))
    return entry


def _sized_card(target: int, tag: str) -> dict:
    """A synthetic card whose rendered block is close to ``target`` code points."""
    record = {
        "identity": {"public": f"住民{tag}" + "公" * 90, "hidden": "隱" * 40},
        "appearance": "貌" * 110,
        "personality": "性" * 90,
        "speech_style": "語" * 90,
        "life_story": "生" * 180,
        "habit": "習" * 60,
        "social_connection": "人" * 40,
    }
    rendered = len(render_card_block(normalize_card(record)))
    record["life_story"] += "生" * max(0, target - rendered)
    return record


class BlueprintPersonaTypeTests(unittest.TestCase):
    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_persona_carrier_is_frozen_and_round_trips_through_the_payload(self):
        payload = _instance_payload()
        blueprint = QuestBlueprint.from_payload(payload)
        persona = blueprint.stages[0].npc_reqs[0].persona
        self.assertIsInstance(persona, BlueprintPersona)
        with self.assertRaises(FrozenInstanceError):
            persona.speech_style = "改寫"
        self.assertEqual(
            blueprint.stages[0].npc_reqs[0].persona.to_record(),
            payload["stages"][0]["npc_req"][0]["persona"],
        )
        self.assertEqual(QuestBlueprint.from_payload(blueprint.to_payload()), blueprint)
        self.assertNotIn("background", blueprint.to_payload()["stages"][0]["npc_req"][0])


class OccupantCardSchemaTests(unittest.TestCase):
    @covers_requirement("scenario-director::the-director-prompt-asks-for-a-complete-card-per-occupant")
    def test_schema_requires_exactly_the_card_keys_and_rejects_background(self):
        self.assertEqual(_schema_errors(_instance_payload()), [])

        def mutate(change):
            payload = _instance_payload()
            change(payload["stages"][0]["npc_req"][0])
            return payload

        cases = {
            "missing_speech_style": lambda e: e["persona"].pop("speech_style"),
            "persona_background": lambda e: e["persona"].update(background="舊欄位"),
            "identity_extra_key": lambda e: e["persona"]["identity"].update(alias="別名"),
            "identity_missing_hidden": lambda e: e["persona"]["identity"].pop("hidden"),
            "non_string_leaf": lambda e: e["persona"].update(habit=42),
            "missing_persona": lambda e: e.pop("persona"),
            "null_persona": lambda e: e.update(persona=None),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                self.assertTrue(_schema_errors(mutate(change)))
        npc_req = SCENARIO_DIRECTOR_OUTPUT_SCHEMA["properties"]["stages"]["items"][
            "properties"
        ]["npc_req"]["items"]
        self.assertIn("persona", npc_req["required"])
        self.assertNotIn("background", npc_req["properties"])
        self.assertEqual(
            set(npc_req["properties"]["persona"]["required"]), set(NPC_CARD_FIELDS)
        )

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_semantic_validation_rejects_a_card_over_its_total_bound(self):
        payload = _instance_payload()
        card = payload["stages"][0]["npc_req"][0]["persona"]
        for field in ("appearance", "personality", "life_story", "habit"):
            card[field] = "長" * LEAF_LIMIT
        self.assertEqual(_schema_errors(payload), [])
        self.assertIn("stage 0 persona: card_too_long", _semantic_errors(payload))


class OccupantTotalCapTests(unittest.TestCase):
    def _blueprint_with(self, per_stage):
        payload = _instance_payload()
        template = payload["stages"][0]
        stages = []
        position = 0
        for index, count in enumerate(per_stage):
            stage = copy.deepcopy(template)
            stage["index"] = index
            stage["location_req"]["scene_sentence"] = f"第{index}段霧氣低垂的小徑。"
            stage["npc_req"] = []
            for _ in range(count):
                stage["npc_req"].append(_occupant(position))
                position += 1
            stages.append(stage)
        payload["stages"] = stages
        return payload

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_four_occupants_across_stages_are_rejected_naming_the_total(self):
        validate = _VALIDATORS["npc_occupant_total"]
        self.assertEqual(MAX_BLUEPRINT_OCCUPANTS, 3)
        self.assertEqual(validate(self._blueprint_with((2, 1))), [])
        errors = validate(self._blueprint_with((2, 2)))
        self.assertEqual(len(errors), 1)
        self.assertIn("4 npc_req occupants in total", errors[0])
        self.assertIn("at most 3", errors[0])

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    @covers_requirement("llm-profiles::per-layer-profile-registry")
    def test_three_compact_cards_fit_the_scenario_director_output_budget(self):
        """Worked-budget heuristic (design D6), not a tokenizer measurement.

        Three occupants with ~800-code-point rendered cards are costed at a
        conservative 2 tokens per card code point (measured on the JSON form,
        so key names and escaping are included) plus one token per UTF-8 byte
        of the non-card remainder of the blueprint.
        """
        payload = self._blueprint_with((3,))
        for position, entry in enumerate(payload["stages"][0]["npc_req"]):
            entry["persona"] = _sized_card(800, str(position))
            rendered = len(render_card_block(normalize_card(entry["persona"])))
            self.assertGreaterEqual(rendered, 790)
            self.assertLessEqual(rendered, 820)
        self.assertEqual(_schema_errors(payload), [])
        card_code_points = sum(
            len(json.dumps(entry["persona"], ensure_ascii=False))
            for entry in payload["stages"][0]["npc_req"]
        )
        remainder = copy.deepcopy(payload)
        for entry in remainder["stages"][0]["npc_req"]:
            entry["persona"] = {}
        remainder_bytes = len(json.dumps(remainder, ensure_ascii=False).encode("utf-8"))
        estimate = 2 * card_code_points + remainder_bytes
        self.assertLess(estimate, SCENARIO_DIRECTOR_MAX_TOKENS)
        self.assertEqual(
            build_profiles(default_profiles())["scenario_director"].max_tokens,
            SCENARIO_DIRECTOR_MAX_TOKENS,
        )


class OccupantCardPromptTests(unittest.TestCase):
    @covers_requirement("scenario-director::the-director-prompt-asks-for-a-complete-card-per-occupant")
    def test_system_prompt_names_the_card_fields_optional_leaves_and_bounds(self):
        system, _user = build_scenario_prompt(_context())
        text = system["content"]
        for field in sorted(NPC_CARD_FIELDS):
            with self.subTest(field=field):
                self.assertIn(field, text)
        for leaf in ("public", "hidden"):
            self.assertIn(leaf, text)
        self.assertIn("identity.hidden 與 social_connection 可為空字串", text)
        self.assertIn("speech_style（說話風格，描述此人如何說話", text)
        self.assertIn(f"每個欄位上限 {LEAF_LIMIT} 個字元", text)
        self.assertIn(f"身分段落上限 {IDENTITY_SECTION_LIMIT} 個字元", text)
        self.assertIn(f"上限 {CARD_BLOCK_LIMIT} 個字元", text)
        self.assertIn("約 800 個字元", text)
        self.assertIn(f"合計最多 {MAX_BLUEPRINT_OCCUPANTS} 個", text)
        self.assertNotIn("background", text)
        # The example blueprint embedded in the prompt carries the card shape.
        self.assertIn('"persona": {"identity": {"public": "…", "hidden": ""}', text)


if __name__ == "__main__":
    unittest.main()
