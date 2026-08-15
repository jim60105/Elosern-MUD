"""Tests for the action resolver's sexual-transition bridge."""

from dataclasses import replace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY


class _FixedRng:
    @staticmethod
    def randint(lower, upper):
        return lower


class SexualEventSelfArmingTests(EvenniaTest):
    def test_landed_transition_module_resolves_and_mutates(self):
        actor = create_object(PlayerCharacter, key="sexual-caster")
        actor.race = "human"
        actor.apply_race_baseline()
        actor.db.skills = {"active": ["status_disguise"], "passive": []}
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(
            original,
            effects=["sexual_event:stimulus_applied"],
        )
        try:
            before = actor.sexual.pleasure.value
            result = ActionResolver.resolve(
                ActionRequest(
                    actor,
                    "status_disguise",
                    [],
                    RoomActionContext(
                        actor.location,
                        {"sexual": {"rng": _FixedRng()}},
                    ),
                )
            )
        finally:
            SKILL_REGISTRY["status_disguise"] = original
        self.assertEqual(result.outcome, "success")
        self.assertGreater(actor.sexual.pleasure.value, before)
