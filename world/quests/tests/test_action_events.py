"""Tests for stable action events and the event-effect planner seam (5.1-5.4)."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import InstanceRoom
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    register_event_effect_planner,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)
from world.quests.planner import quest_event_effect_planner

from ._fixtures import QuestRegistryIsolation, defeat, quest, register


def fire_field(actor, target) -> Battlefield:
    return Battlefield(
        {
            "party": frozenset({actor.key}),
            "foes": frozenset({target.key}),
        },
        {actor.key: actor, target.key: target},
    )


class TargetDefeatedEventTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="actor")
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        # Direct mastery keeps the cast gate open at magic level 0, preserving
        # this class's small-damage profile for the defeat-event scenarios.
        self.actor.db.skills = {
            "active": ["fire_ball"],
            "passive": ["fire_mastery"],
        }

    def _monster(self, key: str, hp: int) -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _resolve(self, targets, skill_key: str = "fire_ball"):
        field = fire_field(self.actor, targets[0])
        request = ActionRequest(
            self.actor,
            skill_key,
            targets,
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    def test_lethal_damage_emits_single_target_defeated_with_identity(self):
        monster = self._monster("goblin", hp=1)
        result = self._resolve([monster])
        self.assertEqual(result.outcome, "success")
        defeated = [entry for entry in result.event_log.entries if entry.kind == "target_defeated"]
        self.assertEqual(len(defeated), 1)
        self.assertEqual(defeated[0].data["target_id"], monster.pk)
        self.assertEqual(defeated[0].data["monster_tier"], "low")

    def test_miss_emits_no_target_defeated(self):
        monster = self._monster("goblin-miss", hp=1)
        field = fire_field(self.actor, monster)
        request = ActionRequest(
            self.actor,
            "fire_ball",
            [monster],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            [entry.kind for entry in result.event_log.entries if entry.kind == "target_defeated"],
            [],
        )
        self.assertGreater(monster.traits.hp.current, 0)

    def test_nonlethal_damage_emits_no_target_defeated(self):
        monster = self._monster("goblin-nonlethal", hp=50)
        result = self._resolve([monster])
        self.assertEqual(
            [entry.kind for entry in result.event_log.entries if entry.kind == "target_defeated"],
            [],
        )
        self.assertLess(monster.traits.hp.current, 50)

    def test_two_damage_effects_emit_one_defeat(self):
        skill_key = "test_double_fire"
        SKILL_REGISTRY[skill_key] = SkillDef(
            key=skill_key,
            label="雙重火焰",
            description="測試用：對單一敵人造成兩次火焰傷害。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=False,
            element=None,
            effects=["damage:fire:magic", "damage:fire:magic"],
            category=SkillCategory.UTILITY,
        )
        self.actor.db.skills = {"active": [skill_key], "passive": []}
        monster = self._monster("goblin-double", hp=1)
        try:
            result = self._resolve([monster], skill_key)
        finally:
            SKILL_REGISTRY.pop(skill_key, None)
        defeated = [entry for entry in result.event_log.entries if entry.kind == "target_defeated"]
        self.assertEqual(result.outcome, "success")
        self.assertEqual(len(defeated), 1)
        self.assertEqual(monster.traits.hp.current, 0)

    def test_same_key_different_dbref_targets_use_dbref_identity(self):
        monster_a = self._monster("lookalike", hp=1)
        monster_b = self._monster("lookalike", hp=1)
        self.assertNotEqual(monster_a.pk, monster_b.pk)
        result = self._resolve([monster_b])
        defeated = [entry for entry in result.event_log.entries if entry.kind == "target_defeated"]
        self.assertEqual(len(defeated), 1)
        self.assertEqual(defeated[0].data["target_id"], monster_b.pk)


class EventEffectPlannerSeamTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="planner-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        # Human starting magic level (術師 tier) so fire_ball casts pass.
        self.player.traits.magic_level.current = 30
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        register_event_effect_planner("quest", quest_event_effect_planner)
        self.low_hunt = register(quest("planner_hunt"))

    def tearDown(self):
        super().tearDown()
        from world.rules.action import _EVENT_EFFECT_PLANNERS

        _EVENT_EFFECT_PLANNERS.pop("quest", None)

    def _monster(self, key: str, hp: int = 1) -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _resolve_lethal(self, monster: Monster):
        from world.quests.runtime import accept_quest

        record = accept_quest(self.player, self.low_hunt.key)
        field = fire_field(self.player, monster)
        request = ActionRequest(
            self.player,
            "fire_ball",
            [monster],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        return record, result

    @covers_requirement("action-resolution-pipeline::event-effect-planners-are-registered-deterministic-and-idempotent-by-name")
    def test_repeated_quest_planner_registration_does_not_duplicate_progress(self):
        register_event_effect_planner("quest", quest_event_effect_planner)
        record, result = self._resolve_lethal(self._monster("double"))
        self.assertEqual(result.outcome, "success")
        from world.quests.runtime import read_records, to_storage

        stored = [to_storage(r) for r in read_records(self.player)]
        self.assertEqual(stored[0]["stage_progress"], 1)
        self.assertEqual(stored[0]["quest_id"], record.quest_id)

    def test_planner_stages_without_mutating_when_step8_rejects(self):
        from world.quests.runtime import accept_quest

        accept_quest(self.player, self.low_hunt.key)
        monster = self._monster("late-reject")
        field = fire_field(self.player, monster)
        request = ActionRequest(
            self.player,
            "fire_ball",
            [monster],
            BattlefieldActionContext(field),
        )
        from world.rules.action import SKILL_TIME_OVERRIDES

        SKILL_TIME_OVERRIDES["fire_ball"] = -1
        try:
            with patch("world.rules.combat.roll_d100", return_value=100):
                result = ActionResolver.resolve(request)
        finally:
            SKILL_TIME_OVERRIDES.pop("fire_ball", None)
        self.assertEqual(result.reason, RejectReason.TIME_COST_LOOKUP_FAILED)
        self.assertEqual(self.player.db.quest_log[0]["stage_progress"], 0)
        self.assertEqual(monster.traits.hp.current, 1)

    def test_malformed_planner_output_rejects_the_complete_action(self):
        def bad_planner(request, event_log):
            return [object()]

        register_event_effect_planner("bad", bad_planner)
        try:
            monster = self._monster("bad")
            record, result = self._resolve_lethal(monster)
        finally:
            from world.rules.action import _EVENT_EFFECT_PLANNERS

            _EVENT_EFFECT_PLANNERS.pop("bad", None)
        self.assertEqual(result.reason, RejectReason.EVENT_LOG_CONSTRUCTION_FAILED)
        self.assertEqual(monster.traits.hp.current, 1)
        stored = self.player.db.quest_log
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["stage_progress"], 0)
        self.assertEqual(stored[0]["quest_id"], record.quest_id)

    def test_unsupported_planner_surface_rejects_before_mutation(self):
        def inventory_planner(request, event_log):
            return [
                PendingEffect(
                    self.player,
                    "inventory",
                    frozenset({"inventory"}),
                    lambda: None,
                )
            ]

        register_event_effect_planner("inventory", inventory_planner)
        try:
            monster = self._monster("inv")
            record, result = self._resolve_lethal(monster)
        finally:
            from world.rules.action import _EVENT_EFFECT_PLANNERS

            _EVENT_EFFECT_PLANNERS.pop("inventory", None)
        self.assertEqual(result.reason, RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE)
        self.assertEqual(monster.traits.hp.current, 1)
        stored = self.player.db.quest_log
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["stage_progress"], 0)
        self.assertEqual(stored[0]["quest_id"], record.quest_id)


class CrossRequestSurfaceRestoreTests(EvenniaTest):
    def test_commit_restores_out_of_request_player_and_room_surfaces(self):
        from world.rules.action import _commit

        owner_one = create_object(PlayerCharacter, key="owner-one")
        owner_two = create_object(PlayerCharacter, key="owner-two")
        room_one = create_object(InstanceRoom, key="room-one")
        room_two = create_object(InstanceRoom, key="room-two")
        victim = create_object(PlayerCharacter, key="victim")
        victim.race = "human"
        victim.apply_race_baseline()

        for owner in (owner_one, owner_two):
            owner.race = "human"
            owner.apply_race_baseline()
            owner.db.quest_log = [{"quest_id": f"{owner.key}:1"}]
        room_one.db.pin_reasons = ["pin:1"]
        room_two.db.pin_reasons = ["pin:2"]
        hp_before = victim.traits.hp.current

        def boom():
            raise RuntimeError("injected second-owner write failure")

        effects = [
            PendingEffect(
                owner_one,
                "quest_log_one",
                frozenset({"quest_log"}),
                lambda: setattr(owner_one.db, "quest_log", [{"quest_id": "one:2"}]),
            ),
            PendingEffect(
                room_one,
                "pin_one",
                frozenset({"instance_pin"}),
                lambda: setattr(room_one.db, "pin_reasons", ["pin:1", "new:1"]),
            ),
            PendingEffect(
                victim,
                "damage",
                frozenset({"traits"}),
                lambda: setattr(victim.traits.hp, "current", hp_before - 5),
            ),
            PendingEffect(owner_two, "quest_log_two", frozenset({"quest_log"}), boom),
            PendingEffect(
                room_two,
                "pin_two",
                frozenset({"instance_pin"}),
                lambda: setattr(room_two.db, "pin_reasons", ["pin:2", "new:2"]),
            ),
        ]
        with self.assertRaises(Exception) as caught:
            _commit(effects)
        self.assertEqual(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(owner_one.db.quest_log, [{"quest_id": "owner-one:1"}])
        self.assertEqual(owner_two.db.quest_log, [{"quest_id": "owner-two:1"}])
        self.assertEqual(room_one.db.pin_reasons, ["pin:1"])
        self.assertEqual(room_two.db.pin_reasons, ["pin:2"])
        self.assertEqual(victim.traits.hp.current, hp_before)


if __name__ == "__main__":
    unittest.main()
