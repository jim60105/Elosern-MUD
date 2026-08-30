"""Offline director end-to-end compile tests (OfflineDirectorEndToEndTests).

Covers the full deterministic quest lifecycle with no LLM and no generative
state mutation: template draw, compile, register, accept, bind, fight, and
turn-in. Shared isolation and payload helpers come from ``_compile_helpers``.
"""

from unittest.mock import patch
import unittest

from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.ai.fake_client import FakeLLMClient
from world.ai.scenario_director import (
    QuestBlueprint,
    generate_quest_blueprint,
    register_scenario_director,
)
from world.quests.compile import (
    compile_quest_blueprint,
    register_generated_quest,
    scene_requirements_for,
)
from world.quests.runtime import QuestState, accept_quest, read_records
from world.quests.tests._compile_helpers import (
    CompileRegistryIsolation,
    _raw,
    await_result,
)
from world.rules.action import ActionRequest, ActionResolver
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.guild import register_adventurer, turn_in_quest
from world.rules.surfaces import read_counter_trait

from tools.spec_traceability import covers_requirement

class OfflineDirectorEndToEndTests(CompileRegistryIsolation, EvenniaTestCase):
    """Offline loop through the template draw, compile, register, accept,
    fight, and turn-in with no LLM call and no generative state mutation."""

    def setUp(self):
        super().setUp()
        from world.quests.bootstrap import sync_quest_runtime

        sync_quest_runtime()
        register_scenario_director()
        self.hall = create_object(Room, key="offline-hall")
        self.staff = create_object(NPC, key="offline staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(
                self.staff,
                service_id="staff",
                branch_key="guild_branch_altoria",
            )
        )
        self.player = create_object(PlayerCharacter, key="offline-director-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        # Human static magic_power at 術師 tier so fire_ball casts pass.
        self.player.traits.magic_power.base = 30
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)

    def _monster(self, key: str, hp: int = 1) -> Monster:
        monster = create_object(Monster, key=key, location=self.player.location)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _resolve_lethal(self, monster: Monster):
        field = Battlefield(
            {"party": frozenset({self.player.key}), "foes": frozenset({monster.key})},
            {self.player.key: self.player, monster.key: monster},
        )
        request = ActionRequest(
            self.player,
            "fire_ball",
            [monster],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    @covers_requirement("quest-progress-tracking::change-15-exposes-a-deterministic-no-ai-completion-seam-for-phase-4")
    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation")
    def test_offline_loop_completes_with_no_llm_and_no_generative_mutation(self):
        disabled = {layer: {"enabled": False} for layer in ("narrator", "npc_dialogue", "scenario_director", "scene_builder")}
        client = FakeLLMClient()
        context = {
            "requested_type": "討伐",
            "allowed_rank": "F",
            "issuer_branch": "guild_branch_altoria",
            "anchor": "capital_altoria",
        }
        with override_settings(LLM_PROFILES=_raw(**disabled)):
            d = generate_quest_blueprint(client, context=context)
            blueprint = await_result(d)
        self.assertIsInstance(blueprint, QuestBlueprint)
        self.assertEqual(len(client.calls), 0)

        compiled = compile_quest_blueprint(blueprint.to_payload())
        register_generated_quest(compiled)
        self.assertTrue(scene_requirements_for(compiled.definition.key))

        record = accept_quest(self.player, compiled.definition.key)
        self.assertIs(record.state, QuestState.IN_PROGRESS)
        from world.quests.binding import bind_stage_runtime

        from typeclasses.rooms import InstanceRoom

        room = create_object(InstanceRoom, key="offline-director-instance")
        monster = self._monster("offline-director-goblin")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            objective_targets=(monster,),
        )
        result = self._resolve_lethal(monster)
        self.assertEqual(result.outcome, "success")

        completed = [
            r
            for r in read_records(self.player)
            if r.definition_key == compiled.definition.key
            and r.state is QuestState.COMPLETED
        ]
        self.assertTrue(completed, "quest did not auto-complete offline")

        turn_in = turn_in_quest(self.player, self.staff, completed[0].quest_id)
        self.assertEqual(turn_in["copper"], compiled.reward.copper)
        self.assertEqual(turn_in["merit"], compiled.reward.merit)
        self.assertEqual(self.player.db.wallet, compiled.reward.copper)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), compiled.reward.merit)
        for item in compiled.reward.items:
            self.assertIn(item.item_key, self.player.db.inventory)
if __name__ == "__main__":
    unittest.main()
