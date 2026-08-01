"""Resolver-level scenario tests that fill spec gaps (step-4 buff, vocabulary)."""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import _add_buff
from world.rules.targeting import RoomActionContext


class ActionForbiddenStepTests(EvenniaTest):
    def test_buff_that_blocks_action_rejects_at_step_4(self):
        actor = create_object(PlayerCharacter, key="blocked-caster")
        actor.race = "human"
        actor.apply_race_baseline()
        actor.db.skills = {"active": ["status_disguise"], "passive": []}
        _add_buff(actor, "paralysis")
        request = ActionRequest(
            actor,
            "status_disguise",
            [],
            RoomActionContext(actor.location),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.reason, RejectReason.ACTION_FORBIDDEN)
        self.assertIsNone(result.event_log)
        self.assertIsNone(actor.db.disguised_stats)


if __name__ == "__main__":
    unittest.main()