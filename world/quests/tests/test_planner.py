"""Tests for action-driven quest progress and protected-entity failure (6.1-6.4)."""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage, QuestType
from world.quests.planner import quest_event_effect_planner
from world.quests.runtime import (
    QuestState,
    accept_quest,
    read_records,
    to_storage,
)
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    register_event_effect_planner,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec

from ._fixtures import (
    QuestRegistryIsolation,
    anchor_locator,
    defeat,
    escort,
    quest,
    register,
)


CLAW_SKILL = SkillDef(
    key="claw",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=False,
    element=None,
    effects=["damage:dark:physical"],
)


class QuestPlannerTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)
        SKILL_REGISTRY["claw"] = CLAW_SKILL
        self.player = create_object(PlayerCharacter, key="quest-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.tier_hunt = register(quest("tier_hunt_three", stages=(QuestStage(0, defeat(quantity=3)),)))
        self.bound_hunt = register(
            quest("bound_hunt", stages=(QuestStage(0, defeat(bound=True)),))
        )
        self.two_stage = register(
            quest(
                "two_stage",
                stages=(
                    QuestStage(0, defeat(quantity=1)),
                    QuestStage(1, defeat(quantity=1)),
                ),
            )
        )
        self.escort_quest = register(
            quest(
                "escort_anchor",
                quest_type=QuestType.ESCORT,
                stages=(QuestStage(0, escort(anchor_locator())),),
            )
        )

    def tearDown(self):
        from world.rules.action import _EVENT_EFFECT_PLANNERS

        _EVENT_EFFECT_PLANNERS.pop("quest", None)
        SKILL_REGISTRY.pop("claw", None)
        super().tearDown()

    def _monster(self, key: str, hp: int = 1, tier: str = "low") -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = tier
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _npc(self, key: str, hp: int = 1) -> NPC:
        npc = create_object(NPC, key=key)
        npc.race = "human"
        npc.apply_race_baseline()
        npc.traits.hp._data["current"] = hp
        return npc

    def _field(self, actor, targets, key_override: str | None = None):
        actor_key = key_override or actor.key
        return Battlefield(
            {"party": frozenset({actor_key}), "foes": frozenset(t.key for t in targets)},
            {actor_key: actor, **{t.key: t for t in targets}},
        )

    def _resolve(self, actor, skill_key, targets):
        field = self._field(actor, targets)
        request = ActionRequest(actor, skill_key, targets, BattlefieldActionContext(field))
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    def _records(self):
        return [to_storage(record) for record in read_records(self.player)]

    def test_player_defeat_advances_matching_tier_objective(self):
        accept_quest(self.player, self.tier_hunt.key)
        first = self._monster("a")
        self.assertEqual(self._resolve(self.player, "fire_ball", [first]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 1)
        second = self._monster("b")
        self.assertEqual(self._resolve(self.player, "fire_ball", [second]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 2)
        self.assertEqual(self._records()[0]["state"], "in_progress")

    def test_wrong_tier_kill_grants_no_progress(self):
        accept_quest(self.player, self.tier_hunt.key)
        mid = self._monster("mid", tier="mid")
        self.assertEqual(self._resolve(self.player, "fire_ball", [mid]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    def test_bound_objective_matches_exact_dbref_not_display_key(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        unbound = self._monster("decoy")
        bound = self._monster("real")
        bind_stage_runtime(self.player, record.quest_id, objective_targets=(bound,))
        self.assertEqual(self._resolve(self.player, "fire_ball", [unbound]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 0)
        self.assertEqual(self._resolve(self.player, "fire_ball", [bound]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 1)

    def test_non_player_actor_grants_no_ordinary_kill_credit(self):
        accept_quest(self.player, self.tier_hunt.key)
        hunter = self._monster("hunter", hp=200, tier="mid")
        hunter.db.skills = {"active": ["claw"], "passive": []}
        prey = self._monster("prey")
        result = self._resolve(hunter, "claw", [prey])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(prey.traits.hp.current, 0)
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    def test_area_defeat_aggregates_without_skipping_stages(self):
        accept_quest(self.player, self.two_stage.key)
        monsters = [self._monster(f"m{i}") for i in range(3)]
        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        result = self._resolve(self.player, "wind_blade", monsters)
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["stage_index"], 1)
        self.assertEqual(stored["stage_progress"], 0)

    def test_final_objective_completes_and_clears_bindings(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        room = create_object(InstanceRoom, key="hunt-room")
        bound = self._monster("final")
        bind_stage_runtime(self.player, record.quest_id, room=room, objective_targets=(bound,))
        result = self._resolve(self.player, "fire_ball", [bound])
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["stage_progress"], 1)
        self.assertEqual(stored["stage_room_id"], None)
        self.assertEqual(stored["objective_target_ids"], [])
        self.assertEqual(room.db.pin_reasons, [])

    def test_terminal_records_ignore_later_matching_events(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        bound = self._monster("done")
        bind_stage_runtime(self.player, record.quest_id, objective_targets=(bound,))
        self._resolve(self.player, "fire_ball", [bound])
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        extra = self._monster("extra")
        self._resolve(self.player, "fire_ball", [extra])
        after = self._records()[0]
        self.assertEqual(after, stored)
        self.assertEqual(after["state"], "completed")

    def test_protected_npc_death_fails_escort_quest(self):
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("guard")
        room = create_object(InstanceRoom, key="escort-room")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            protected_entities=(guard,),
        )
        killer = self._monster("killer", hp=200, tier="mid")
        killer.db.skills = {"active": ["claw"], "passive": []}
        result = self._resolve(killer, "claw", [guard])
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["failure_reason"], "protected_entity_defeated")
        self.assertEqual(stored["protected_entity_ids"], [])
        self.assertEqual(stored["stage_room_id"], None)
        self.assertEqual(room.db.pin_reasons, [])

    def test_same_display_key_creates_no_false_failure(self):
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("guard-identical")
        impostor = self._npc("guard-identical")
        guard.db.key = "guard"
        impostor.db.key = "guard"
        bind_stage_runtime(self.player, record.quest_id, protected_entities=(guard,))
        killer = self._monster("killer", hp=200, tier="mid")
        killer.db.skills = {"active": ["claw"], "passive": []}
        self._resolve(killer, "claw", [impostor])
        self.assertEqual(self._records()[0]["state"], "in_progress")
        self._resolve(killer, "claw", [guard])
        self.assertEqual(self._records()[0]["state"], "failed")

    def test_objective_target_death_cannot_trigger_protected_failure(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        target = self._monster("objective-target")
        bind_stage_runtime(self.player, record.quest_id, objective_targets=(target,))
        self._resolve(self.player, "fire_ball", [target])
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["failure_reason"], None)

    def test_same_event_protected_failure_wins_over_defeat_progress(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        target = self._monster("dual-target")
        npc_guard = self._npc("dual-guard")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            objective_targets=(target,),
            protected_entities=(npc_guard,),
        )
        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        result = self._resolve(self.player, "wind_blade", [target, npc_guard])
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["failure_reason"], "protected_entity_defeated")
        self.assertEqual(stored["objective_target_ids"], [])
        self.assertEqual(stored["protected_entity_ids"], [])

    def test_commit_fault_rolls_back_death_and_quest_failure_together(self):
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("guard-rollback")
        room = create_object(InstanceRoom, key="escort-rollback")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            protected_entities=(guard,),
        )
        killer = self._monster("killer-rollback", hp=200, tier="mid")
        killer.db.skills = {"active": ["claw"], "passive": []}
        guard_hp_before = guard.traits.hp.current
        room_pins_before = list(room.db.pin_reasons)
        with patch(
            "world.quests.transitions._apply_pin_operations",
            side_effect=RuntimeError("injected pin failure"),
        ):
            result = self._resolve(killer, "claw", [guard])
        from world.rules.action import RejectReason

        self.assertEqual(result.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(guard.traits.hp.current, guard_hp_before)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "in_progress")
        self.assertEqual(room.db.pin_reasons, room_pins_before)


if __name__ == "__main__":
    unittest.main()