"""Data-contract test: offline quest template occupant card contract

The hand-written ``QUEST_TEMPLATE_POOL`` is shipped production content and the
offline degradation path materializes its occupants directly, so every
NPC-bearing template occupant must carry a fully authored compact card that
passes the shared characterization helper (npc-persona-generated-quest-cards
task 4.1), every template must respect the guardrail's whole-blueprint
occupant cap, and the director prompt must not embed any shipped card prose.
"""

import unittest

from tools.spec_traceability import covers_requirement
from world.ai.director_templates import QUEST_TEMPLATE_POOL
from world.ai.scenario_director import MAX_BLUEPRINT_OCCUPANTS, build_scenario_prompt
from world.lore.npc_card import normalize_card
from world.quests.characterization import characterize_errors, race_lifespan_upper_bound


def _occupants():
    for template in QUEST_TEMPLATE_POOL:
        for stage in template.stages:
            for position, requirement in enumerate(stage.npc_reqs):
                yield template, stage, position, requirement


class TemplateOccupantCardContractTests(unittest.TestCase):
    @covers_requirement("scenario-director::offline-template-occupants-carry-fully-authored-cards")
    def test_every_template_occupant_carries_a_valid_card(self):
        occupants = list(_occupants())
        self.assertTrue(occupants, "the pool lost its NPC-bearing template")
        for template, stage, position, requirement in occupants:
            with self.subTest(template=template.name, stage=stage.index, occupant=position):
                self.assertIsNotNone(requirement.persona)
                entry = template.to_payload()["stages"][stage.index]["npc_req"][position]
                self.assertEqual(
                    characterize_errors(
                        entry,
                        lifespan_upper_bound=race_lifespan_upper_bound(requirement.tier),
                    ),
                    [],
                )
                card = normalize_card(requirement.persona.to_record())
                # Authored content is already normalized: storage is verbatim.
                self.assertEqual(card.to_record(), requirement.persona.to_record())

    @covers_requirement("scenario-director::offline-template-occupants-carry-fully-authored-cards")
    def test_every_template_respects_the_occupant_total_cap(self):
        for template in QUEST_TEMPLATE_POOL:
            with self.subTest(template=template.name):
                total = sum(len(stage.npc_reqs) for stage in template.stages)
                self.assertLessEqual(total, MAX_BLUEPRINT_OCCUPANTS)

    @covers_requirement("scenario-director::the-director-prompt-asks-for-a-complete-card-per-occupant")
    def test_the_director_prompt_embeds_no_shipped_card_prose(self):
        system, _user = build_scenario_prompt({"requested_type": "討伐"})
        text = system["content"]
        for template, stage, position, requirement in _occupants():
            for leaf, value in requirement.persona.to_record().items():
                values = value.values() if isinstance(value, dict) else (value,)
                for prose in values:
                    if prose:
                        with self.subTest(template=template.name, leaf=leaf):
                            self.assertNotIn(prose, text)


if __name__ == "__main__":
    unittest.main()
