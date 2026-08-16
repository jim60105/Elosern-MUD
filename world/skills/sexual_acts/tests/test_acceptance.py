"""End-to-end acceptance proof for the act ownership/unlock/ActionResolver seam.

The synthetic act is built inside this test module via ``_act_family()`` and
installed into both registries for the duration of the test only; the shipped
catalogue rows (the seed acts and, later, the full catalog) live in the line
modules and are never edited here.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts._builder import _act_family


class AcceptanceProofTests(EvenniaTest):
    """One synthetic act proves the ownership/unlock/cast round trip."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="act tester")
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        self.context = RoomActionContext(self.actor.location, {})
        (self.skill, self.act), = _act_family(
            "獨處線",
            (
                "test_seed_act",
                "測試行為",
                "僅存在於測試中的合成行為。",
                TargetSpec.SELF,
                {"restraint_count": 1},
                10,
                "私處",
                None,
                0.5,
                ("restraint_count",),
                (),
                (),
                True,
            ),
        )

    def _install(self):
        return (
            patch.dict(SEXUAL_ACT_REGISTRY, {self.act.key: self.act}),
            patch.dict(SKILL_REGISTRY, {self.skill.key: self.skill}),
        )

    def _resolve(self):
        return ActionResolver.resolve(
            ActionRequest(self.actor, self.act.key, [], self.context)
        )

    def test_act_stays_locked_below_threshold_and_cannot_be_cast(self):
        with self._install()[0], self._install()[1]:
            self.assertNotIn(self.act.key, self.actor.skills.owned_keys())
            result = self._resolve()
            self.assertIs(result.reason, RejectReason.UNKNOWN_SKILL)

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_act_unlocks_at_threshold_and_resolves_through_the_full_pipeline(self):
        with self._install()[0], self._install()[1]:
            self.actor.sexual.record_restraint()
            self.assertIn(self.act.key, self.actor.skills.owned_keys())
            result = self._resolve()
            self.assertEqual(result.outcome, "success")
            self.assertEqual(result.event_log.skill_key, self.act.key)
            self.assertEqual(
                [entry.kind for entry in result.event_log.entries],
                ["pleasure_gain", "sexual_counter", "skill_practice"],
            )
            self.assertEqual(self.actor.sexual.restraint_count, 2)
