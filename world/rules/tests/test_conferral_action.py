"""End-to-end tests for the conferral write seam."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.targeting import RoomActionContext


class ConferralActionTests(EvenniaTest):
    def _resolver_context(self, actor, **event_context):
        return RoomActionContext(actor.location, event_context)

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
                self._resolver_context(
                    actor,
                    confer_skill_key="body_enhancement",
                    confer_scale=0.1,
                ),
            )
        )
        self.assertEqual(result.outcome, "success")
        grant = actor.db.skill_grants[0]
        self.assertEqual(grant.source_key, "source")
        self.assertEqual(grant.skill_key, "body_enhancement")
        self.assertEqual(grant.scale, 0.1)
        self.assertEqual(
            set(type(grant).__dataclass_fields__),
            {"source_key", "skill_key", "scale"},
        )

    def test_gate_type_conferral_is_rejected_at_resolution_time(self):
        actor = create_object(PlayerCharacter, key="gate source")
        actor.race = "human"
        actor.apply_race_baseline()
        actor.db.skills = {"active": ["dominion_art"], "passive": []}
        result = ActionResolver.resolve(
            ActionRequest(
                actor,
                "dominion_art",
                [actor],
                self._resolver_context(
                    actor,
                    confer_skill_key="fire_mastery",
                    confer_scale=0.5,
                ),
            )
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertEqual(actor.db.skill_grants or [], [])

    def test_preflight_rejects_missing_confer_scale(self):
        actor = create_object(PlayerCharacter, key="preflight source")
        actor.race = "human"
        actor.apply_race_baseline()
        actor.db.skills = {"active": ["dominion_art"], "passive": []}
        result = ActionResolver.preflight(
            ActionRequest(
                actor,
                "dominion_art",
                [actor],
                self._resolver_context(actor, confer_skill_key="body_enhancement"),
            )
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.MISSING_EFFECT_CONTEXT)
