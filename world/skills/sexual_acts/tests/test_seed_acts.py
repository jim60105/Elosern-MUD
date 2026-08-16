"""Behaviour tests for the seven unconditionally-owned seed acts.

The seeds are real catalogue rows registered in ``solo.py``/``shame.py``/
``partner.py``/``combat.py``; this module casts them through the ordinary
``ActionResolver`` pipeline and asserts ownership, resistibility, and counter
credit per the sexual-act-seeds delta spec.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts.interspecies import INTERSPECIES_ACTS
from world.skills.sexual_acts.divine import DIVINE_ACTS


_SELF_SEEDS = ("solo_self_touch", "solo_fondle_breasts", "solo_thigh_rub", "shame_hem_lift")
_SINGLE_SEEDS = ("partner_caress", "partner_hand_hold", "combat_tease")


class SeedActOwnershipTests(EvenniaTest):
    """The seven seeds are owned from zero counters; 異種/神之秘法 gain none."""

    def _entity(self, key="seed owner"):
        entity = create_object(PlayerCharacter, key=key, location=self.room1)
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement("sexual-act-seeds::seven-seed-acts-are-registered-with-an-empty-unlock-mapping-and-are-unconditionally-owned")
    def test_fresh_character_owns_every_seed_act(self):
        entity = self._entity()
        owned = set(entity.skills.owned_keys())
        self.assertTrue(
            {"solo_self_touch", "solo_fondle_breasts", "solo_thigh_rub",
             "shame_hem_lift", "partner_caress", "partner_hand_hold", "combat_tease"}
            <= owned
        )

    @covers_requirement("sexual-act-seeds::seven-seed-acts-are-registered-with-an-empty-unlock-mapping-and-are-unconditionally-owned")
    def test_interspecies_and_divine_gain_no_seed(self):
        self.assertEqual(INTERSPECIES_ACTS, ())
        self.assertEqual(DIVINE_ACTS, ())

    def test_seed_rows_are_registered_under_the_same_key_in_both_registries(self):
        for key in (*_SELF_SEEDS, *_SINGLE_SEEDS):
            with self.subTest(key=key):
                self.assertIn(key, SEXUAL_ACT_REGISTRY)
                self.assertIs(
                    SKILL_REGISTRY[key].category.value,
                    "sexual_act",
                )

    @covers_requirement("sexual-act-seeds::the-four-self-target-seeds-are-unresistable-the-three-single-target-seeds-are-resistible")
    def test_self_target_seeds_are_unresistable(self):
        for key in _SELF_SEEDS:
            with self.subTest(key=key):
                self.assertFalse(SEXUAL_ACT_REGISTRY[key].resistible)

    @covers_requirement("sexual-act-seeds::the-four-self-target-seeds-are-unresistable-the-three-single-target-seeds-are-resistible")
    def test_single_target_seeds_are_resistible(self):
        for key in _SINGLE_SEEDS:
            with self.subTest(key=key):
                self.assertTrue(SEXUAL_ACT_REGISTRY[key].resistible)


class SeedActCastingTests(EvenniaTest):
    """Casting the seeds through ActionResolver credits the declared counters."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(
            PlayerCharacter, key="seed caster", location=self.room1
        )
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        self.target = create_object(
            PlayerCharacter, key="seed target", location=self.room1
        )
        self.target.race = "human"
        self.target.apply_race_baseline()

    def _cast(self, act_key, targets):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                targets,
                RoomActionContext(self.actor.location, {}),
            )
        )

    @covers_requirement("sexual-act-seeds::solo-seeds-credit-masturbation-count-on-the-actor-only-only-solo-self-touch-also-emits-the-masturbation-experience-type-event")
    def test_every_solo_seed_increments_actor_masturbation_count_only(self):
        for key in ("solo_self_touch", "solo_fondle_breasts", "solo_thigh_rub"):
            with self.subTest(key=key):
                before = self.actor.sexual.masturbation_count
                result = self._cast(key, [])
                self.assertEqual(result.outcome, "success", key)
                self.assertEqual(
                    self.actor.sexual.masturbation_count, before + 1, key
                )
                self.assertEqual(self.target.sexual.masturbation_count, 0, key)

    @covers_requirement("sexual-act-seeds::solo-seeds-credit-masturbation-count-on-the-actor-only-only-solo-self-touch-also-emits-the-masturbation-experience-type-event")
    def test_only_solo_self_touch_adds_the_masturbation_experience_type(self):
        self._cast("solo_fondle_breasts", [])
        self._cast("solo_thigh_rub", [])
        self.assertNotIn("自慰", self.actor.sexual.experience_types)

    @covers_requirement("sexual-act-seeds::solo-seeds-credit-masturbation-count-on-the-actor-only-only-solo-self-touch-also-emits-the-masturbation-experience-type-event")
    def test_solo_self_touch_adds_the_masturbation_experience_type(self):
        self._cast("solo_self_touch", [])
        self.assertIn("自慰", self.actor.sexual.experience_types)

    @covers_requirement("sexual-act-seeds::partner-seeds-credit-duo-act-count-on-both-participants")
    def test_partner_seed_increments_duo_act_count_on_both_participants(self):
        result = self._cast("partner_caress", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.duo_act_count, 1)
        self.assertEqual(self.target.sexual.duo_act_count, 1)

    @covers_requirement("sexual-act-seeds::the-combat-seed-credits-hostile-act-count-on-the-actor-only")
    def test_combat_tease_increments_hostile_act_count_on_actor_only(self):
        result = self._cast("combat_tease", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.hostile_act_count, 1)
        self.assertEqual(self.target.sexual.hostile_act_count, 0)

    def test_single_target_seed_cannot_be_self_cast(self):
        # A SINGLE-target sex act is a two-participant act by construction;
        # self-casting would credit its lifetime counters with no partner.
        for key in ("partner_caress", "partner_hand_hold", "combat_tease"):
            with self.subTest(key=key):
                result = self._cast(key, [self.actor])
                self.assertEqual(result.outcome, "rejected", key)
                self.assertEqual(
                    self.actor.sexual.duo_act_count, 0, key
                )
                self.assertEqual(
                    self.actor.sexual.hostile_act_count, 0, key
                )

    @covers_requirement("sexual-act-seeds::a-single-target-sexual-act-cannot-be-self-cast")
    def test_self_cast_rejection_credits_no_counters_on_either_seed(self):
        for key in ("partner_caress", "partner_hand_hold", "combat_tease"):
            with self.subTest(key=key):
                self._cast(key, [self.actor])
                self.assertEqual(self.actor.sexual.duo_act_count, 0, key)
                self.assertEqual(self.actor.sexual.hostile_act_count, 0, key)
                self.assertEqual(self.target.sexual.duo_act_count, 0, key)
                self.assertEqual(self.target.sexual.hostile_act_count, 0, key)


class ShameSeedExposureTests(EvenniaTest):
    """shame_hem_lift raises the actor's exposure and cascades into shame."""

    def _entity(self):
        entity = create_object(PlayerCharacter, key="shame seed caster")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement("sexual-act-seeds::a-new-sexual-yaml-rule-lets-an-act-raise-its-own-actor-s-exposure-cascading-to-shame-within-the-same-apply-event-call")
    def test_shame_hem_lift_raises_exposure_by_one(self):
        entity = self._entity()
        result = ActionResolver.resolve(
            ActionRequest(
                entity,
                "shame_hem_lift",
                [],
                RoomActionContext(entity.location, {}),
            )
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity.sexual.exposure.value, 1)

    @covers_requirement("sexual-act-seeds::a-new-sexual-yaml-rule-lets-an-act-raise-its-own-actor-s-exposure-cascading-to-shame-within-the-same-apply-event-call")
    def test_shame_hem_lift_cascades_exposure_into_shame_in_the_same_call(self):
        entity = self._entity()
        self.assertEqual(entity.sexual.shame.value, 0)
        result = ActionResolver.resolve(
            ActionRequest(
                entity,
                "shame_hem_lift",
                [],
                RoomActionContext(entity.location, {}),
            )
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity.sexual.exposure.value, 1)
        self.assertEqual(entity.sexual.shame.value, 1)
