"""Resolver integration tests for the narration pass (task 3.1-3.3).

Every case resolves a real synthetic skill through the action pipeline; the
assertions establish that narration changes only the entry's text template.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from typeclasses.rooms import Room

from world.rules.action import ActionRequest, ActionResolver
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_beats import RoundRecord, build_combat_beats
from world.rules.event_log import render_entry_text
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.tests.synthetic_data import make_skill
from world.skills.narration import FAMILY_ROWS
from world.skills.registry import TargetSpec


class NarrationPipelineTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.traits.magic_power.base = 30
        self.room = create_object(Room, key="narration arena")
        self.player.move_to(self.room)
        self.damage_skill = make_skill(
            "t_narr_strike",
            target_spec=TargetSpec.SINGLE,
            effects=["damage:none:physical"],
            cost={"mp": 5},
            usable_out_of_combat=False,
        )
        self.empty_skill = make_skill(
            "t_narr_empty",
            target_spec=TargetSpec.SINGLE,
            effects=[],
            cost={},
            usable_out_of_combat=True,
        )
        open_synthetic_scope(
            self,
            "skills",
            extra={
                "skills": {
                    self.damage_skill.key: self.damage_skill,
                    self.empty_skill.key: self.empty_skill,
                }
            },
        )
        grant_lineage(
            self.player,
            [self.damage_skill.key, self.empty_skill.key],
        )

    def _monster(self, key: str = "narr goblin", hp: int = 10000) -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = hp
        monster.traits.hp.current = hp
        monster.location = self.room
        return monster

    def _request(self, skill, monster):
        field = Battlefield(
            {
                "party": frozenset({self.player.key}),
                "foes": frozenset({monster.key}),
            },
            {self.player.key: self.player, monster.key: monster},
        )
        return (
            ActionRequest(
                self.player,
                skill.key,
                [monster],
                BattlefieldActionContext(field),
            ),
            field,
        )

    def _resolve(self, skill, monster, *, narration_scope=""):
        request, field = self._request(skill, monster)
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                request, narration_scope=narration_scope
            )
        return result, field

    def test_narration_keeps_kinds_order_and_exact_data(self):
        monster = self._monster()
        result, _ = self._resolve(self.damage_skill, monster)
        self.assertEqual(result.outcome, "success")
        entries = result.event_log.entries
        self.assertEqual(
            [entry.kind for entry in entries],
            ["roll", "damage", "resource_spend", "trait_delta", "skill_practice"],
        )
        roll = entries[0]
        damage = entries[1]
        self.assertEqual(roll.data["raw_roll"], 100)
        self.assertIsInstance(damage.data["amount"], int)
        self.assertGreater(damage.data["amount"], 0)
        for entry in entries:
            rendered = render_entry_text(entry)
            self.assertFalse(
                any(character.isdigit() for character in rendered),
                rendered,
            )

    def test_the_first_entry_carries_the_skill_action_clause(self):
        monster = self._monster()
        result, _ = self._resolve(self.damage_skill, monster)
        first = result.event_log.entries[0]
        family_actions = FAMILY_ROWS["martial_arts"].action
        self.assertTrue(
            any(first.text_template.startswith(action) for action in family_actions),
            first.text_template,
        )
        self.assertIn("{target}", first.text_template)

    def test_narration_consumes_no_gameplay_randomness(self):
        monster = self._monster()
        request, _ = self._request(self.damage_skill, monster)
        draws: list[int] = []

        def _counting_roll():
            draws.append(1)
            return 100

        with patch(
            "world.rules.combat.damage.roll_d100", side_effect=_counting_roll
        ):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(len(draws), 1)

    def test_an_effect_less_success_emits_one_action_line(self):
        from world.rules.action.event_log import _step7_build_event_log

        monster = self._monster()
        request, _ = self._request(self.empty_skill, monster)
        # Step 7 is the pipeline seam: an empty pending list is the successful
        # action whose effects staged nothing.
        log = _step7_build_event_log(request, self.empty_skill, [])
        entries = log.entries
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].kind, "action_narration")
        rendered = render_entry_text(entries[0])
        self.assertTrue(rendered)
        self.assertFalse(any(character.isdigit() for character in rendered))

    def test_a_different_narration_scope_can_vary_the_prose(self):
        templates = set()
        for index in range(10):
            monster = self._monster(key=f"narr goblin {index}")
            result, _ = self._resolve(
                self.damage_skill,
                monster,
                narration_scope=f"scope-{index}",
            )
            templates.add(
                tuple(entry.text_template for entry in result.event_log.entries)
            )
        self.assertGreater(len(templates), 1)

    def test_round_beats_keep_one_beat_per_entry(self):
        monster = self._monster()
        hp_before = int(monster.traits.hp.value)
        result, field = self._resolve(self.damage_skill, monster)
        hp_after = int(monster.traits.hp.value)
        record = RoundRecord(
            session_id="narration:1:0",
            number=1,
            logs=(result.event_log,),
            identities={
                self.player.key: self.player.pk,
                monster.key: monster.pk,
            },
            hp_before={monster.pk: hp_before},
            hp_after={monster.pk: hp_after},
        )
        view = build_combat_beats(record)
        self.assertEqual(len(view.beats), len(result.event_log.entries))
        for beat in view.beats:
            self.assertLessEqual(len(beat.text), 256)

    def test_a_terminal_upkeep_log_hides_its_amount(self):
        from world.rules.upkeep import settle_upkeep

        monster = self._monster(hp=500)
        _, field = self._request(self.damage_skill, monster)
        record = type(
            "Tick",
            (),
            {"source_pk": self.player.pk, "delta": -12.0, "hp_before": 500.0},
        )()
        logs = settle_upkeep(
            field,
            {monster.key: (record,)},
            narration_scope="field|3|upkeep",
        )
        self.assertEqual(len(logs), 1)
        damage = next(
            entry for entry in logs[0].entries if entry.kind == "damage"
        )
        self.assertEqual(damage.data["amount"], 12)
        self.assertFalse(
            any(character.isdigit() for character in render_entry_text(damage))
        )

    def test_an_upkeep_narration_fault_degrades_instead_of_aborting(self):
        from world.rules.upkeep import settle_upkeep

        monster = self._monster(hp=500)
        _, field = self._request(self.damage_skill, monster)
        record = type(
            "Tick",
            (),
            {"source_pk": self.player.pk, "delta": -12.0, "hp_before": 500.0},
        )()
        with patch(
            "world.rules.upkeep.entry_line",
            side_effect=RuntimeError("narration fault"),
        ):
            logs = settle_upkeep(
                field,
                {monster.key: (record,)},
                narration_scope="field|3|upkeep",
            )
        self.assertEqual(len(logs), 1)
        damage = next(
            entry for entry in logs[0].entries if entry.kind == "damage"
        )
        self.assertEqual(damage.data["amount"], 12)
        self.assertFalse(
            any(character.isdigit() for character in render_entry_text(damage))
        )


if __name__ == "__main__":
    unittest.main()
