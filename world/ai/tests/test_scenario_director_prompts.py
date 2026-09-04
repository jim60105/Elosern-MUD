"""Tests for the deterministic bounded scenario-director prompt construction."""


import json
import zlib
from random import Random
import unittest

from world.ai.scenario_director import (
    MAX_CONTEXT_FIELD_LENGTH,
    MAX_TOTAL_SIZE,
    SCENARIO_DIRECTOR_OUTPUT_SCHEMA,
    _VALIDATORS,
    build_scenario_prompt,
)
from world.ai.tests._director_helpers import _context
from world.lore.names import NAME_PACK_REGISTRY
from world.rules.namegen import roll_name_for_race

from tools.spec_traceability import covers_requirement


# Independent recomputation of the namegen-npc-flow D1 bank: pinned seed
# source, pinned count, pinned separator — a production drift in any of the
# three fails these tests, not just a change in the names themselves.
_BANK_COUNT = 6


def _expected_bank(bounded_user_text: str) -> str:
    rng = Random(zlib.crc32(bounded_user_text.encode("utf-8")))
    return "、".join(
        roll_name_for_race(None, "", rng) for _ in range(_BANK_COUNT)
    )



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

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_system_carries_the_full_context_seeded_bank_with_guidance(self):
        system, user = build_scenario_prompt(_context())
        bank = _expected_bank(user["content"])
        self.assertEqual(len(bank.split("、")), _BANK_COUNT)
        self.assertIn(bank, system["content"])
        self.assertEqual(system["content"].count(bank), 1)
        self.assertIn("僅供靈感", system["content"])
        # Required-identity guidance ships in the prompt library only.
        self.assertIn("必須附帶 display_name 與 title", system["content"])
        self.assertNotIn("仍為選填", system["content"])

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_contexts_normalizing_to_one_bounded_text_share_one_bank(self):
        # The seed is the FINAL bounded text: raw contexts that differ only
        # past the cap boundary must render byte-identical prompts, pinning
        # the seed source to the serialized (not raw) context.
        over = _context(note="字" * (MAX_CONTEXT_FIELD_LENGTH + 50))
        exact = _context(note="字" * MAX_CONTEXT_FIELD_LENGTH)
        first = build_scenario_prompt(over)
        second = build_scenario_prompt(exact)
        self.assertEqual(first[1]["content"], second[1]["content"])
        self.assertEqual(first[0]["content"], second[0]["content"])

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_output_contract_carries_the_required_identity_fields(self):
        npc_req = (
            SCENARIO_DIRECTOR_OUTPUT_SCHEMA["properties"]["stages"]["items"]
            ["properties"]["npc_req"]["items"]
        )
        self.assertIn("display_name", npc_req["required"])
        self.assertIn("title", npc_req["required"])
        self.assertEqual(
            npc_req["properties"]["display_name"]["type"], ["string", "null"]
        )
        self.assertEqual(npc_req["properties"]["title"]["type"], ["string", "null"])
        system, user = build_scenario_prompt(_context())
        for name in _expected_bank(user["content"]).split("、"):
            self.assertNotIn(name, json.dumps(SCENARIO_DIRECTOR_OUTPUT_SCHEMA, ensure_ascii=False))

    @covers_requirement("prompt-library::the-scenario-director-key-is-registered-with-the-name-inspiration-placeholder-and-carries-the-naming-guidance")
    def test_validators_require_identity_and_accept_bank_external_names(self):
        def _payload(npc_req: dict) -> dict:
            base_npc = {"role": "向導", "tier": "bandit"}
            return {
                "stages": [
                    {
                        "index": 0,
                        "objective": {"kind": "defeat", "quantity": 1},
                        "npc_req": [dict(base_npc, **npc_req)],
                    }
                ]
            }

        validate = _VALIDATORS["npc_characterization"]
        # Missing identity fields are named guardrail failures now.
        self.assertTrue(validate(_payload({})))
        self.assertTrue(validate(_payload({"display_name": "非庫名・自取"})))
        # A bank-external authored pair (rolled name adapted freely) validates.
        self.assertEqual(
            validate(
                _payload(
                    {"display_name": "非庫名・自取", "title": "邊境嚮導"}
                )
            ),
            [],
        )

    @covers_requirement("scenario-director::the-scenario-director-name-inspiration-reads-the-namegen-rule-layer-without-crossing-the-single-writer-boundary")
    def test_prompt_construction_leaves_no_state_behind(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        before = repr(NAME_PACK_REGISTRY)
        with CaptureQueriesContext(connection) as queries:
            system, user = build_scenario_prompt(_context())
        self.assertEqual(repr(NAME_PACK_REGISTRY), before)
        self.assertEqual(
            [
                query["sql"]
                for query in queries.captured_queries
                if query["sql"].lstrip().upper().startswith(
                    ("INSERT", "UPDATE", "DELETE")
                )
            ],
            [],
        )
        # The rolled names exist only inside the returned message strings.
        self.assertIn(_expected_bank(user["content"]), system["content"])
        self.assertNotIn("・", user["content"])
