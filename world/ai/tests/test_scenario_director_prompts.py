"""Tests for the deterministic bounded scenario-director prompt construction."""


import json
import unittest

from world.ai.scenario_director import (
    MAX_CONTEXT_FIELD_LENGTH,
    MAX_TOTAL_SIZE,
    build_scenario_prompt,
)
from world.ai.tests._director_helpers import _context

from tools.spec_traceability import covers_requirement



class ScenarioDirectorPromptTests(unittest.TestCase):
    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_identical_contexts_produce_byte_identical_prompts(self):
        first = build_scenario_prompt(_context())
        second = build_scenario_prompt(_context())
        self.assertEqual(first, second)
        self.assertEqual(first[0]["role"], "system")
        self.assertEqual(first[1]["role"], "user")
        self.assertEqual(first[0]["content"], second[0]["content"])
        self.assertEqual(first[1]["content"], second[1]["content"])

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_oversized_context_is_bounded_and_valid(self):
        context = _context(note="字" * (MAX_CONTEXT_FIELD_LENGTH * 4))
        system, user = build_scenario_prompt(context)
        self.assertLessEqual(len(user["content"]), MAX_TOTAL_SIZE)
        parsed = json.loads(user["content"])
        self.assertLessEqual(len(parsed["note"]), MAX_CONTEXT_FIELD_LENGTH)
        self.assertEqual(parsed["issuer_branch"], "guild_branch_altoria")

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_system_message_names_the_blueprint_contract_and_fidelity(self):
        system, _ = build_scenario_prompt(_context())
        self.assertIn("QuestBlueprint", system["content"])
        self.assertIn("不得編造", system["content"])
        self.assertIn("正體中文", system["content"])
        self.assertIn("伊洛瑟恩大陸", system["content"])

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_user_message_carries_keys_and_no_live_objects(self):
        _, user = build_scenario_prompt(
            _context(issuer_branch="guild_branch_altoria", anchor="capital_altoria")
        )
        self.assertIn("guild_branch_altoria", user["content"])
        self.assertIn("capital_altoria", user["content"])
        self.assertNotIn("<", user["content"])
        self.assertNotIn("object at", user["content"])
