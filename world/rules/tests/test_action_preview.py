"""Tests for the frozen side-effect-free action preview (tasks 1.3)."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.action_preview import (
    preview_skill,
    revalidate_submission,
)
from world.rules.buffs import _add_buff
from world.rules.combat import BattlefieldActionContext
from world.rules.combat_session import engage, read_session, reconstruct_battlefield
from world.rules.sexual_state import AROUSAL_LEVELS
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY
from .combat_fixtures import BattlefieldIsolation


def _player(key="preview player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    # Human starting magic level (術師 tier) so element-gated spell casts pass.
    player.traits.magic_level.base = 30
    return player


def _monster(key="preview goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class ActionPreviewTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="preview arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.monster = _monster()
        self.monster.location = self.room

    def _context(self):
        engage(self.player, self.monster)
        battlefield = reconstruct_battlefield(self.player, read_session(self.player))
        return BattlefieldActionContext(battlefield)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_preview_reuses_named_resolver_rejection(self):
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        context = self._context()
        preview = preview_skill(self.player, "fire_ball", context, [self.monster])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(preview.detail, "mp")

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_preview_has_no_side_effects(self):
        context = self._context()
        from world.rules.clock import get_world_clock

        clock = get_world_clock()
        from world.rules.event_log import EventLog

        before_tick = clock.tick
        with patch("world.rules.combat.roll_d100") as roll:
            preview = preview_skill(
                self.player, "fire_ball", context, [self.monster]
            )
        roll.assert_not_called()
        self.assertTrue(preview.enabled)
        self.assertEqual(preview.valid_targets, (self.monster,))
        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(self.monster.traits.hp.current, 100)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_preview_parity_with_preflight(self):
        context = self._context()
        preview = preview_skill(self.player, "fire_ball", context, [self.monster])
        request = ActionRequest(
            self.player, "fire_ball", [self.monster], context
        )
        preflight = ActionResolver.preflight(request)
        self.assertEqual(preflight.outcome, "success")
        self.assertTrue(preview.enabled)

        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        preview = preview_skill(self.player, "fire_ball", context, [self.monster])
        preflight = ActionResolver.preflight(
            ActionRequest(self.player, "fire_ball", [self.monster], context)
        )
        self.assertEqual(preflight.reason, preview.reason)
        self.assertEqual(preflight.detail, preview.detail)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_zero_action_state_rejects_before_initiative(self):
        self.player.sexual.climax_phase.value = "進行中"
        context = self._context()
        preview = preview_skill(self.player, "basic_attack", context, [self.monster])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.ACTION_FORBIDDEN)

        result = revalidate_submission(
            self.player, "basic_attack", context, [self.monster]
        )
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.ACTION_FORBIDDEN)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_preview_does_not_materialize_sexual_state(self):
        self.player.db.sexual = {
            "arousal": AROUSAL_LEVELS[4],
            "wetness": "泛濫",
            "shame": "無",
            "exposure": "遮蔽",
            "climax_phase": "進行中",
            "sensitivity": {},
            "climax_today": 0,
            "virgin": True,
            "experience_types": [],
        }
        from world.rules.combat import Battlefield

        battlefield = Battlefield(
            {
                "party": frozenset({self.player.key}),
                "foes": frozenset({self.monster.key}),
            },
            {self.player.key: self.player, self.monster.key: self.monster},
        )
        context = BattlefieldActionContext(battlefield)
        preview = preview_skill(self.player, "basic_attack", context, [self.monster])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.ACTION_FORBIDDEN)
        self.assertIsNone(
            self.player.attributes.get("sexual_traits", category="traits"),
            "preview must not materialize the sexual handler",
        )

    def test_preview_targets_use_ordered_validation(self):
        context = self._context()
        preview = preview_skill(self.player, "fire_ball", context, [self.monster])
        self.assertEqual(preview.valid_targets, (self.monster,))

        self.monster.traits.hp.base = 0
        self.monster.traits.hp.current = 0
        preview = preview_skill(self.player, "fire_ball", context, [self.monster])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.TARGET_DEAD)

    def test_preview_none_skill_ignores_roster_candidates(self):
        self.player.db.skills = {"active": ["concentration"], "passive": []}
        context = self._context()
        preview = preview_skill(
            self.player, "concentration", context, [self.monster, self.player]
        )
        self.assertTrue(preview.enabled)
        self.assertEqual(preview.valid_targets, ())
        self.assertEqual(preview.shorthands, ())

    @covers_requirement("skill-registry::dual-wield-style-is-a-passive-stance-not-a-castable-active-skill")
    def test_preview_reports_owned_dual_wield_style_as_passive(self):
        self.player.db.skills = {"active": [], "passive": ["dual_wield_style"]}
        context = self._context()
        preview = preview_skill(self.player, "dual_wield_style", context, [])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.SKILL_NOT_ACTIVE)

    def test_area_shorthands_are_exposed(self):
        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        context = self._context()
        preview = preview_skill(self.player, "wind_blade", context, [self.monster])
        self.assertTrue(preview.enabled)
        self.assertEqual(preview.shorthands, ("all-enemies", "all-allies", "all"))

    def test_revalidate_rejects_stale_or_wrong_shape(self):
        context = self._context()
        result = revalidate_submission(
            self.player, "fire_ball", context, [self.monster]
        )
        self.assertTrue(result.enabled)

        # ANY skills accept every relation, so the actor itself is now a
        # valid explicit target for a damage skill (friendly-fire free
        # targeting); the wrong-shape rejection is the empty list instead.
        result = revalidate_submission(
            self.player, "fire_ball", context, [self.player]
        )
        self.assertTrue(result.enabled)

        result = revalidate_submission(self.player, "fire_ball", context, [])
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_revalidate_none_self_and_single_shapes(self):
        context = self._context()
        result = revalidate_submission(self.player, "body_enhancement", context, [])
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.UNKNOWN_SKILL)

        # SELF shape is validated with the disguise context supplied, exactly
        # as the out-of-combat cast path does (commands/action.py).
        self.player.db.skills = {"active": ["status_disguise"], "passive": []}
        disguise_context = BattlefieldActionContext(
            context.battlefield,
            event_context={"disguise": {"atk_phys": 60}},
        )
        result = revalidate_submission(
            self.player, "status_disguise", disguise_context, []
        )
        self.assertTrue(result.enabled)

        # Player-facing SELF requires an empty list: an explicit actor target
        # (even the actor itself) is a shape mismatch, matching the facade.
        result = revalidate_submission(
            self.player, "status_disguise", disguise_context, [self.player]
        )
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

        result = revalidate_submission(
            self.player, "status_disguise", disguise_context, [self.monster]
        )
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_revalidate_single_shorthand_and_area_empty(self):
        context = self._context()
        result = revalidate_submission(self.player, "fire_ball", context, "all-enemies")
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        result = revalidate_submission(self.player, "wind_blade", context, [])
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

        result = revalidate_submission(
            self.player, "wind_blade", context, "all-enemies"
        )
        self.assertTrue(result.enabled)

    def test_revalidate_area_explicit_all_filtered(self):
        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        context = self._context()
        self.monster.traits.hp.base = 0
        self.monster.traits.hp.current = 0
        result = revalidate_submission(self.player, "wind_blade", context, "all-enemies")
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

    def test_revalidate_area_duplicate_explicit_input_rejects(self):
        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        context = self._context()
        result = revalidate_submission(
            self.player, "wind_blade", context, [self.monster, self.monster]
        )
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_context_requiring_skills_are_disabled_in_combat(self):
        self.player.db.skills = {
            "active": ["status_disguise", "dominion_art"],
            "passive": [],
        }
        context = self._context()
        # SELF submits an empty list; SINGLE submits one live candidate, the
        # exact shapes the combat menu sends.
        submitted = {
            "status_disguise": [],
            "dominion_art": [self.monster],
        }
        for skill_key, targets in submitted.items():
            with self.subTest(skill_key=skill_key):
                preview = preview_skill(
                    self.player, skill_key, context, [self.monster]
                )
                self.assertFalse(preview.enabled)
                self.assertIs(
                    preview.reason, RejectReason.MISSING_EFFECT_CONTEXT
                )
                result = revalidate_submission(
                    self.player, skill_key, context, targets
                )
                self.assertFalse(result.enabled)
                self.assertIs(
                    result.reason, RejectReason.MISSING_EFFECT_CONTEXT
                )
                preflight = ActionResolver.preflight(
                    ActionRequest(
                        self.player, skill_key, targets, context
                    )
                )
                self.assertEqual(preflight.outcome, "rejected")
                self.assertIs(
                    preflight.reason, RejectReason.MISSING_EFFECT_CONTEXT
                )

    def test_context_requiring_skills_resolve_with_supplied_context(self):
        self.player.db.skills = {
            "active": ["status_disguise", "dominion_art"],
            "passive": [],
        }
        context = self._context()
        disguise_context = BattlefieldActionContext(
            context.battlefield,
            event_context={"disguise": {"atk_phys": 60}},
        )
        preview = preview_skill(
            self.player, "status_disguise", disguise_context, [self.player]
        )
        self.assertTrue(preview.enabled)
        preflight = ActionResolver.preflight(
            ActionRequest(self.player, "status_disguise", [], disguise_context)
        )
        self.assertEqual(preflight.outcome, "success")

        dominion_context = BattlefieldActionContext(
            context.battlefield,
            event_context={
                "confer_skill_key": "body_enhancement",
                "confer_scale": 0.1,
            },
        )
        preflight = ActionResolver.preflight(
            ActionRequest(
                self.player, "dominion_art", [self.monster], dominion_context
            )
        )
        self.assertEqual(preflight.outcome, "success")


class AdjustedCostPreviewTests(BattlefieldIsolation, EvenniaTest):
    """Preview/preflight/resolve parity for adjusted resource costs."""

    def setUp(self):
        super().setUp()
        self.player = _player("cost preview player")
        self.context = RoomActionContext(
            self.player.location,
            {"disguise": {"atk_phys": 1}},
        )
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(original, cost={"sp": 10})
        self.addCleanup(
            lambda: SKILL_REGISTRY.__setitem__("status_disguise", original)
        )

    def _preview(self):
        return preview_skill(self.player, "status_disguise", self.context, [])

    def _preflight(self):
        return ActionResolver.preflight(
            ActionRequest(self.player, "status_disguise", [], self.context)
        )

    def _resolve(self):
        return ActionResolver.resolve(
            ActionRequest(self.player, "status_disguise", [], self.context)
        )

    @covers_requirement(
        "combat-modifier-table::preview-preflight-and-resolve-agree-on-adjusted-resource-costs"
    )
    def test_preview_enables_exactly_the_casts_preflight_allows_under_reduction(self):
        self.player.db.skills = {
            "active": ["status_disguise"],
            "passive": ["extreme_endurance"],
        }
        self.player.traits.sp.base = 20
        self.player.traits.sp.current = 9
        self.assertTrue(self._preview().enabled)
        self.assertEqual(self._preflight().outcome, "success")
        result = self._resolve()
        self.assertEqual(result.outcome, "success")
        spend = next(
            e for e in result.event_log.entries if e.kind == "resource_spend"
        )
        self.assertEqual(spend.data, {"resource_key": "sp", "amount": 9})

    @covers_requirement(
        "combat-modifier-table::preview-preflight-and-resolve-agree-on-adjusted-resource-costs"
    )
    def test_preview_rejects_exactly_the_casts_preflight_rejects_under_reduction(self):
        self.player.db.skills = {
            "active": ["status_disguise"],
            "passive": ["extreme_endurance"],
        }
        self.player.traits.sp.base = 20
        self.player.traits.sp.current = 8
        preview = self._preview()
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(preview.detail, "sp")
        self.assertIs(self._preflight().reason, RejectReason.INSUFFICIENT_RESOURCE)
        result = self._resolve()
        self.assertIs(result.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(result.detail, "sp")
        self.assertEqual(self.player.traits.sp.value, 8)

    def test_fractional_grant_percentage_parity_across_all_three_surfaces(self):
        self.player.db.skills = {
            "active": ["status_disguise"],
            "passive": [],
        }
        self.player.traits.sp.base = 20
        self.player.traits.sp.current = 9
        bundle = {"sp_cost": "-5%"}
        with (
            patch(
                "world.rules.action_preview.evaluate_combat_modifiers_no_create",
                return_value=bundle,
            ),
            patch(
                "world.rules.action.evaluate_combat_modifiers",
                return_value=bundle,
            ),
        ):
            self.assertTrue(self._preview().enabled)
            self.assertEqual(self._preflight().outcome, "success")
            result = self._resolve()
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.player.traits.sp.value, 0)

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_conferred_grant_scale_floors_identically_across_all_surfaces(self):
        from world.skills.handler import ConferredSkillGrant

        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(original, cost={"mp": 10})
        try:
            self.player.db.skills = {"active": ["status_disguise"], "passive": []}
            self.player.db.skill_grants = [
                ConferredSkillGrant("elosia", "precise_mana_control", 0.5)
            ]
            self.player.traits.mp.base = 20
            self.player.traits.mp.current = 9
            self.assertTrue(self._preview().enabled)
            self.assertEqual(self._preflight().outcome, "success")
            result = self._resolve()
        finally:
            SKILL_REGISTRY["status_disguise"] = original
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.player.traits.mp.value, 0)
        spend = next(
            e for e in result.event_log.entries if e.kind == "resource_spend"
        )
        self.assertEqual(spend.data, {"resource_key": "mp", "amount": 9})


if __name__ == "__main__":
    import unittest

    unittest.main()
