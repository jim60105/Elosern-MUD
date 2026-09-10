"""Resolver-level scenario tests that fill spec gaps (step-4 buff, vocabulary)."""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import _add_buff
from world.rules.targeting import RoomActionContext
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import make_skill, synthetic_registries

# The cast is an invented disguise-shaped skill: the gate under test fires on
# the ACTION_FORBIDDEN buff step, so only the skill's self-target disguise
# shape matters. No shipped skill key can substitute for the fixture.
_T_DISGUISE = make_skill(
    "t_mask_step",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    cost={},
    element=None,
    group=None,
    effects=["set_disguise"],
    category=SkillCategory.UTILITY,
)


@synthetic_registries(
    "skills",
    "races",
    "subraces",
    "static_tiers",
    "elements",
    extra={"skills": {_T_DISGUISE.key: _T_DISGUISE}},
)
class ActionForbiddenStepTests(EvenniaTest):
    def test_buff_that_blocks_action_rejects_at_step_4(self):
        actor = create_object(PlayerCharacter, key="blocked-caster")
        actor.race = "t_duskmari"
        actor.subrace = "t_duskmari_evensong"
        actor.apply_race_baseline()
        actor.db.skills = {"active": [_T_DISGUISE.key], "passive": []}
        _add_buff(actor, "paralysis")
        request = ActionRequest(
            actor,
            _T_DISGUISE.key,
            [],
            RoomActionContext(actor.location),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.reason, RejectReason.ACTION_FORBIDDEN)
        self.assertIsNone(result.event_log)
        self.assertIsNone(actor.db.disguised_stats)


if __name__ == "__main__":
    unittest.main()
