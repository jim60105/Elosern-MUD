"""End-to-end test for the existing conferral write seam."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver
from world.rules.targeting import RoomActionContext


class ConferralActionTests(EvenniaTest):
    def test_conferral_commits_through_action_resolver(self):
        actor = create_object(PlayerCharacter, key="source")
        actor.race = "human"
        actor.apply_race_baseline()
        actor.db.skills = {"active": ["dominion_art"], "passive": []}
        result = ActionResolver.resolve(
            ActionRequest(
                actor,
                "dominion_art",
                [actor],
                RoomActionContext(
                    actor.location,
                    {
                        "confer_skill_key": "body_enhancement",
                        "confer_scale": 0.1,
                        "confer_trait_keys": ("atk_phys",),
                    },
                ),
            )
        )
        self.assertEqual(result.outcome, "success")
        grant = actor.db.skill_grants[0]
        self.assertEqual(grant.source_key, "source")
        self.assertEqual(grant.skill_key, "body_enhancement")
