"""Freeform casting (element-mastery-freeform-casting) tests.

Covers the closed scale table, deterministic scaling helpers, eligibility
predicate, mastery entitlement query, the resolver's step-1 freeform gate,
scaled resource deduction and magnitudes, preview scaling, the combat-session
facade threading, and the text ``cast`` command scale token.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest.mock import patch
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.action_preview import preview_skill, revalidate_submission
from world.rules.clock import WorldClock
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
)
from world.rules.combat_session import engage, submit_player_action
from world.rules.player_messages import rejection_message
from world.rules.progression import (
    FREEFORM_CAST_SCALES,
    FREEFORM_SCALE_VALUES,
    _load_freeform_cast_scales,
    freeform_scales_for,
    scale_for_label,
    scale_label_for,
    scaled_magnitude,
    scaled_mp_cost,
)
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SKILL_REGISTRY
from .combat_fixtures import BattlefieldIsolation


def _player(key="freeform caster"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.traits.magic_level.current = 30
    return player


def _granted_mastery_only(player: PlayerCharacter) -> None:
    player.db.skill_grants = [
        ConferredSkillGrant("source", "wind_mastery", 1.0)
    ]


class FreeformScaleTableTests(unittest.TestCase):
    """The closed scale table is fixed and load-validated (freeform-casting)."""

    @covers_requirement("freeform-casting::the-freeform-scale-table-is-a-fixed-load-validated-closed-set")
    def test_canonical_table_loads_ascending_with_labels(self):
        self.assertEqual(
            FREEFORM_CAST_SCALES,
            (
                (0.25, "1/4"),
                (0.5, "1/2"),
                (1.0, "1"),
                (2.0, "2"),
                (4.0, "4"),
            ),
        )
        self.assertEqual(FREEFORM_SCALE_VALUES, (0.25, 0.5, 1.0, 2.0, 4.0))
        self.assertEqual(scale_label_for(2.0), "2")
        self.assertEqual(scale_label_for(3.0), None)
        self.assertEqual(scale_for_label("1/2"), 0.5)
        self.assertEqual(scale_for_label("3"), None)

    @covers_requirement("freeform-casting::the-freeform-scale-table-is-a-fixed-load-validated-closed-set")
    def test_deviant_tables_are_rejected_at_load(self):
        base = [
            {"scale": 0.25, "label": "1/4"},
            {"scale": 0.5, "label": "1/2"},
            {"scale": 1.0, "label": "1"},
            {"scale": 2.0, "label": "2"},
            {"scale": 4.0, "label": "4"},
        ]
        cases = {
            "missing 1.0": base[:2] + base[3:],
            "duplicate scale": base[:2] + [{"scale": 0.5, "label": "x"}] + base[2:],
            "unsorted": [base[1], base[0], *base[2:]],
            "non-finite scale": [{"scale": float("nan"), "label": "nan"}, *base[1:]],
            "non-positive scale": [{"scale": -1.0, "label": "-1"}, *base[1:]],
            "empty label": [{"scale": 0.25, "label": "  "}, *base[1:]],
            "duplicate label": base[:2] + [{"scale": 0.75, "label": "1/2"}] + base[2:],
            "count other than five": base[:4],
            "non-object entry": [0.25, *base[1:]],
            "extra key": [{"scale": 0.25, "label": "1/4", "extra": 1}, *base[1:]],
            "non-canonical scale value": [
                {"scale": 0.75, "label": "3/4"},
                *base[1:],
            ],
            "swapped label pairing": [
                {"scale": 0.25, "label": "4"},
                {"scale": 0.5, "label": "1/2"},
                {"scale": 1.0, "label": "1"},
                {"scale": 2.0, "label": "2"},
                {"scale": 4.0, "label": "1/4"},
            ],
        }
        for name, table in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    _load_freeform_cast_scales({"freeform_cast_scales": table})
        with self.assertRaises(ValueError):
            _load_freeform_cast_scales({})


class ScaledCostAndMagnitudeTests(unittest.TestCase):
    """Deterministic round-half-away-from-zero helpers (freeform-casting)."""

    @covers_requirement("freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero")
    def test_half_scale_of_an_even_cost_is_exact(self):
        self.assertEqual(scaled_mp_cost(14, 0.5), 7)
        self.assertEqual(scaled_magnitude(10, 0.5), 5)

    @covers_requirement("freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero")
    def test_fractional_results_round_half_away_from_zero(self):
        self.assertEqual(scaled_mp_cost(11, 0.5), 6)
        self.assertEqual(scaled_magnitude(5, 0.5), 3)
        self.assertEqual(scaled_mp_cost(150, 0.25), 38)
        self.assertEqual(scaled_mp_cost(11, 0.5), scaled_mp_cost(11, 0.5))

    @covers_requirement("freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero")
    def test_scaled_mp_cost_never_falls_below_one(self):
        self.assertEqual(scaled_mp_cost(1, 0.25), 1)
        self.assertEqual(scaled_mp_cost(2, 0.25), 1)
        self.assertEqual(scaled_mp_cost(1, 0.5), 1)

    @covers_requirement("freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero")
    def test_whole_scales_are_exact_and_invalid_inputs_raise(self):
        self.assertEqual(scaled_mp_cost(26, 2.0), 52)
        for base, scale in (
            (0, 1.0),
            (-1, 1.0),
            (1, 0.0),
            (1, -2.0),
            (1, float("nan")),
            (1, float("inf")),
            (True, 1.0),
            (1, True),
        ):
            with self.subTest(base=base, scale=scale):
                with self.assertRaises(ValueError):
                    scaled_mp_cost(base, scale)
                with self.assertRaises(ValueError):
                    scaled_magnitude(base, scale)


class FreeformEligibilityTests(unittest.TestCase):
    """is_freeform_eligible is a pure skill-shape predicate."""

    @covers_requirement("freeform-casting::is-freeform-eligible-is-a-pure-skill-shape-predicate")
    def test_pure_damage_and_heal_spells_are_eligible(self):
        for key in (
            "wind_blade",
            "tornado_blade",
            "sea_of_life",
            "phoenix_eternal_flame",
        ):
            with self.subTest(skill=key):
                self.assertTrue(is_freeform_eligible(SKILL_REGISTRY[key]))

    @covers_requirement("freeform-casting::is-freeform-eligible-is-a-pure-skill-shape-predicate")
    def test_buff_status_mixed_and_non_spell_skills_are_ineligible(self):
        for key in (
            "gale_step",
            "haste_domain",
            "scorching_wave",
            "purify",
            "basic_attack",
            "flight",
            "dual_blade_mastery",
            "concentration",
        ):
            with self.subTest(skill=key):
                self.assertFalse(is_freeform_eligible(SKILL_REGISTRY[key]))

    @covers_requirement("freeform-casting::is-freeform-eligible-is-a-pure-skill-shape-predicate")
    def test_effect_less_elemental_skill_is_ineligible(self):
        from dataclasses import replace

        skill = replace(SKILL_REGISTRY["wind_blade"], effects=[])
        self.assertFalse(is_freeform_eligible(skill))


class FreeformScalesForTests(EvenniaTestCase):
    """Mastery ownership entitles scaling of the element's spells."""

    def setUp(self):
        super().setUp()
        self.entity = _player()
        self.entity.db.skills = {"active": [], "passive": []}

    @covers_requirement("element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells")
    def test_mastery_holder_receives_the_full_scale_set(self):
        self.entity.db.skills = {"active": [], "passive": ["wind_mastery"]}
        self.assertEqual(
            freeform_scales_for(self.entity, "wind"),
            (0.25, 0.5, 1.0, 2.0, 4.0),
        )

    @covers_requirement("element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells")
    def test_entity_without_mastery_receives_an_empty_set(self):
        self.entity.traits.magic_level.current = 100
        self.assertEqual(freeform_scales_for(self.entity, "wind"), ())
        _granted_mastery_only(self.entity)
        self.assertEqual(freeform_scales_for(self.entity, "wind"), ())

    @covers_requirement("element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells")
    def test_unknown_element_fails_closed(self):
        self.entity.db.skills = {"active": [], "passive": ["not_an_element_mastery"]}
        with self.assertRaises(ValueError):
            freeform_scales_for(self.entity, "not_an_element")


class FreeformResolverGateTests(EvenniaTestCase):
    """The resolver gates scaled casts at the ownership step."""

    def setUp(self):
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="freeform target")
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.actor.traits.mp.base = 500
        self.actor.traits.mp.current = 500
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"freeform target"}),
            },
            {"freeform caster": self.actor, "freeform target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    def _request(self, skill_key, scale):
        return ActionRequest(
            self.actor,
            skill_key,
            [self.target],
            self.context,
            scale=scale,
        )

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_mastery_holder_can_scale_an_eligible_spell(self):
        self.actor.db.skills = {
            "active": ["wind_blade"],
            "passive": ["wind_mastery"],
        }
        result = ActionResolver.preflight(self._request("wind_blade", 2.0))
        self.assertEqual(result.outcome, "success")
        self.assertNotEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scaling_without_mastery_is_rejected(self):
        self.actor.db.skills = {"active": ["wind_blade"], "passive": []}
        result = ActionResolver.preflight(self._request("wind_blade", 2.0))
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_mastery_entitles_scaling_of_that_element_only(self):
        self.actor.db.skills = {
            "active": ["wind_blade", "light_arrow"],
            "passive": ["wind_mastery"],
        }
        light = ActionResolver.preflight(self._request("light_arrow", 2.0))
        self.assertEqual(light.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        wind = ActionResolver.preflight(self._request("wind_blade", 2.0))
        self.assertEqual(wind.outcome, "success")

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scaling_an_ineligible_spell_is_rejected_even_with_mastery(self):
        self.actor.db.skills = {
            "active": ["gale_step"],
            "passive": ["wind_mastery"],
        }
        result = ActionResolver.preflight(self._request("gale_step", 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_non_elemental_mp_skill_never_crashes_the_gate(self):
        self.actor.db.skills = {"active": ["concentration"], "passive": []}
        result = ActionResolver.preflight(self._request("concentration", 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_sp_only_elemental_skill_is_not_scalable(self):
        self.actor.db.skills = {
            "active": ["dual_blade_mastery"],
            "passive": ["dark_mastery"],
        }
        self.actor.traits.sp.current = 500
        result = ActionResolver.preflight(self._request("dual_blade_mastery", 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        sp_before = self.actor.traits.sp.value
        ActionResolver.resolve(self._request("dual_blade_mastery", 2.0))
        self.assertEqual(self.actor.traits.sp.value, sp_before)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_non_member_scale_is_rejected(self):
        self.actor.db.skills = {
            "active": ["wind_blade"],
            "passive": ["wind_mastery"],
        }
        result = ActionResolver.preflight(self._request("wind_blade", 3.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scale_one_is_always_permitted(self):
        self.actor.db.skills = {
            "active": ["concentration", "scorching_wave", "gale_step"],
            "passive": ["wind_mastery", "fire_mastery"],
        }
        for key in ("concentration", "scorching_wave", "gale_step"):
            with self.subTest(skill=key):
                result = ActionResolver.preflight(self._request(key, 1.0))
                self.assertNotEqual(
                    result.reason,
                    RejectReason.SCALED_CAST_FORBIDDEN,
                )


class ActionRequestScaleContractTests(EvenniaTestCase):
    """ActionRequest carries an optional scale modifier and a new rejection category."""

    def setUp(self):
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="scale contract target")
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.actor.db.skills = {
            "active": ["wind_blade"],
            "passive": ["wind_mastery"],
        }
        self.actor.traits.mp.base = 500
        self.actor.traits.mp.current = 500
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"scale contract target"}),
            },
            {"freeform caster": self.actor, "scale contract target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_existing_requests_default_to_scale_one(self):
        request = ActionRequest(
            self.actor,
            "wind_blade",
            [self.target],
            self.context,
        )
        self.assertEqual(request.scale, 1.0)
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        spend = next(
            entry
            for entry in result.event_log.entries
            if entry.kind == "resource_spend"
        )
        self.assertEqual(spend.data["amount"], 14)

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_scale_reaches_the_resource_steps_and_the_handlers(self):
        self.target.traits.defense.base = 0
        self.target.traits.hp.base = 200
        self.target.traits.hp.current = 200
        self.actor.traits.magic_level.current = 6
        request = ActionRequest(
            self.actor,
            "wind_blade",
            [self.target],
            self.context,
            scale=0.5,
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        spend = next(
            entry
            for entry in result.event_log.entries
            if entry.kind == "resource_spend"
        )
        # Step 2 and step 6 compare and deduct the same scaled amount.
        self.assertEqual(spend.data["amount"], 7)
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        self.assertEqual(damage_entry.data["amount"], 6)

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_the_rejection_category_is_available(self):
        self.actor.db.skills = {"active": ["wind_blade"], "passive": []}
        request = ActionRequest(
            self.actor,
            "wind_blade",
            [self.target],
            self.context,
            scale=2.0,
        )
        result = ActionResolver.preflight(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        self.assertIsNone(result.event_log)
        self.assertIsNone(result.time_cost_seconds)


class FreeformScaledResolutionTests(EvenniaTestCase, BattlefieldIsolation):
    """A scaled cast deducts scaled MP and applies scaled magnitudes."""

    def setUp(self):
        super().setUp()
        self.actor = _player()
        self.monster = create_object(Monster, key="freeform wolf")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")
        self.actor.traits.mp.base = 1000
        self.actor.traits.mp.current = 1000
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"freeform wolf"}),
            },
            {"freeform caster": self.actor, "freeform wolf": self.monster},
        )
        self.context = BattlefieldActionContext(self.field)
        self.actor.db.skills = {
            "active": ["wind_blade", "tornado_blade", "phoenix_eternal_flame"],
            "passive": ["wind_mastery", "fire_mastery", "water_mastery"],
        }

    def _request(self, skill_key, targets, scale):
        return ActionRequest(
            self.actor,
            skill_key,
            targets,
            self.context,
            scale=scale,
        )

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_half_scale_wind_blade_deducts_half_mp_and_deals_half_damage(self):
        # magic_level 6 gives an unscaled critical of round(6 * 2.0) = 12
        # against zero defense; half scale stages 6.
        self.actor.traits.magic_level.current = 6
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        mp_before = self.actor.traits.mp.value
        hp_before = self.monster.traits.hp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request("wind_blade", [self.monster], 0.5)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.mp.value, mp_before - 7)
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        self.assertEqual(damage_entry.data["amount"], 6)
        self.assertEqual(self.monster.traits.hp.value, hp_before - 6)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_double_scale_cast_deducts_double_mp(self):
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request("tornado_blade", [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.mp.value, mp_before - 52)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_unaffordable_scaled_cost_rejects_without_any_effect(self):
        self.actor.db.skills = {
            "active": ["world_ending_blaze"],
            "passive": ["fire_mastery"],
        }
        self.actor.traits.mp.base = 200
        self.actor.traits.mp.current = 200
        hp_before = self.monster.traits.hp.value
        result = ActionResolver.resolve(
            self._request("world_ending_blaze", [self.monster], 4.0)
        )
        self.assertEqual(result.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(self.actor.traits.mp.value, 200)
        self.assertEqual(self.monster.traits.hp.value, hp_before)
        self.assertIsNone(result.event_log)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_damage_obeys_the_floor(self):
        # magic_level 2 → base critical 4 → quarter scale 1 (the floor), never 0.
        self.actor.traits.magic_level.current = 2
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request("wind_blade", [self.monster], 0.25)
            )
        self.assertEqual(result.outcome, "success")
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        self.assertEqual(damage_entry.data["amount"], 1)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_lethal_hit_emits_exactly_one_defeat(self):
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 5
        self.monster.traits.hp.current = 5
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request("wind_blade", [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        defeated = [
            entry
            for entry in result.event_log.entries
            if entry.kind == "target_defeated"
        ]
        self.assertEqual(len(defeated), 1)
        self.assertLessEqual(self.monster.traits.hp.value, 0)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_healing_respects_the_maximum_and_knockout_rules(self):
        self.actor.db.skills = {
            "active": ["sea_of_life"],
            "passive": ["water_mastery"],
        }
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 150
        # magic_level 30 → base heal 30 → double scale 60, capped by the gap 50.
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request("sea_of_life", [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        heal_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "heal"
        )
        self.assertEqual(heal_entry.data["amount"], 50)
        self.assertEqual(self.monster.traits.hp.value, 200)
        # A zero-HP entity is never revived: targeting drops the dead
        # candidate, so the scaled heal applies no restoration.
        self.monster.traits.hp.current = 0
        self.actor.traits.mp.current = 1000
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request("sea_of_life", [self.monster], 2.0)
            )
        self.assertEqual(result.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)
        self.assertEqual(self.monster.traits.hp.value, 0)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_phoenix_eternal_flame_scales_damage_self_heal_and_mp_together(self):
        self.actor.traits.hp.current = 40
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request("phoenix_eternal_flame", [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.mp.value, mp_before - 300)
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        # magic_level 30 → base critical 60 → double scale 120.
        self.assertEqual(damage_entry.data["amount"], 120)
        self.assertEqual(self.monster.traits.hp.value, 80)
        heal_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "self_heal"
        )
        # base heal 30 → double scale 60, capped by the gap to maximum.
        self.assertEqual(heal_entry.data["amount"], 60)
        self.assertEqual(self.actor.traits.hp.value, 100)


class FreeformPreviewTests(EvenniaTestCase):
    """Preview and the combat facade accept and revalidate scale."""

    def setUp(self):
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="preview target")
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.actor.db.skills = {
            "active": ["wind_blade"],
            "passive": ["wind_mastery"],
        }
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"preview target"}),
            },
            {"freeform caster": self.actor, "preview target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_preview_reports_scaled_resource_availability(self):
        self.actor.traits.mp.current = 56
        preview = preview_skill(
            self.actor,
            "wind_blade",
            self.context,
            [self.target],
            scale=4.0,
        )
        self.assertTrue(preview.enabled)
        self.actor.traits.mp.current = 40
        preview = preview_skill(
            self.actor,
            "wind_blade",
            self.context,
            [self.target],
            scale=4.0,
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(preview.detail, "mp")

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_preview_applies_the_freeform_gate(self):
        self.actor.db.skills = {"active": ["wind_blade"], "passive": []}
        preview = preview_skill(
            self.actor,
            "wind_blade",
            self.context,
            [self.target],
            scale=2.0,
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        preview = revalidate_submission(
            self.actor,
            "wind_blade",
            self.context,
            [self.target],
            scale=2.0,
        )
        self.assertEqual(preview.reason, RejectReason.SCALED_CAST_FORBIDDEN)


class FreeformSessionFacadeTests(EvenniaTest, BattlefieldIsolation):
    """The facade resolves a scaled combat cast and rejects tampered scales."""

    def setUp(self):
        super().setUp()
        self.actor = _player("freeform session")
        self.actor.db.skills = {
            "active": ["wind_blade"],
            "passive": ["wind_mastery"],
        }
        self.actor.traits.mp.base = 1000
        self.actor.traits.mp.current = 1000
        self.monster = create_object(Monster, key="session wolf")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        self.actor.move_to(self.room1)
        self.monster.move_to(self.room1)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_facade_resolves_a_scaled_combat_cast(self):
        engage(self.actor, self.monster)
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(
                self.actor, "wind_blade", [self.monster], scale=2.0
            )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(self.actor.traits.mp.value, mp_before - 28)
        self.assertLess(self.monster.traits.hp.value, 200)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_facade_rejects_a_tampered_scale_before_initiative(self):
        engage(self.actor, self.monster)
        mp_before = self.actor.traits.mp.value
        hp_before = self.monster.traits.hp.value
        record_before = self.actor.db.active_combat
        result = submit_player_action(
            self.actor, "wind_blade", [self.monster], scale=3.0
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.SCALED_CAST_FORBIDDEN)
        self.assertEqual(self.actor.traits.mp.value, mp_before)
        self.assertEqual(self.monster.traits.hp.value, hp_before)
        self.assertEqual(self.actor.db.active_combat, record_before)


class FreeformTextCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """The text cast command accepts a scale token."""

    def _setup_caster(self, *, mastery: bool) -> None:
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.traits.magic_level.current = 30
        self.char1.db.skills = {
            "active": ["wind_blade", "gale_step"],
            "passive": ["wind_mastery"] if mastery else [],
        }
        self.char1.traits.mp.base = 500
        self.char1.traits.mp.current = 500
        self.char1.move_to(self.room1)

    def _setup_target(self) -> None:
        target = create_object(PlayerCharacter, key="wind target")
        target.race = "human"
        target.apply_race_baseline()
        target.move_to(self.room1)

    def _clock(self):
        clock = WorldClock()
        return patch(
            "world.rules.cast_settlement.read_world_clock", return_value=clock
        ), patch(
            "world.rules.cast_settlement.get_world_clock", return_value=clock
        ), clock

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scaled_out_of_combat_cast_deducts_scaled_mp_and_advances_time(self):
        from commands.action import CmdCast

        # No catalog spell usable out of combat is magnitude-scalable today;
        # the fixture supplies the flag deterministically (freeform-casting
        # spec scenario) without changing the shipped registry.
        original = SKILL_REGISTRY["wind_blade"]
        SKILL_REGISTRY["wind_blade"] = replace(
            original, usable_out_of_combat=True
        )
        try:
            self._setup_caster(mastery=True)
            self._setup_target()
            read_patch, get_patch, clock = self._clock()
            with read_patch, get_patch:
                self.call(
                    CmdCast(),
                    "wind_blade@1/2=wind target",
                    f"{self.char1.key} 對 wind target 的攻擊擲出了",
                )
            half_end = self.char1.traits.mp.value
            # The ordinary command-time charge applies per cast.
            self.assertEqual(clock.tick, 6)
            # Reset the gauge (and its regen remainder) so the second cast
            # accrues the same regen; the exact scaled deduction is then the
            # differential between the two command casts.
            self.char1.traits.mp.current = 500
            self.char1.traits.mp.regen_remainder = 0.0
            with read_patch, get_patch:
                self.call(
                    CmdCast(),
                    "wind_blade@1=wind target",
                    f"{self.char1.key} 對 wind target 的攻擊擲出了",
                )
            one_end = self.char1.traits.mp.value
            self.assertEqual(clock.tick, 12)
            # 1/2 scale deducts exactly 7 less than full scale.
            self.assertEqual(half_end - one_end, 7)
        finally:
            SKILL_REGISTRY["wind_blade"] = original

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_invalid_scale_token_rejects_without_effect(self):
        from commands.action import CmdCast

        original = SKILL_REGISTRY["wind_blade"]
        SKILL_REGISTRY["wind_blade"] = replace(
            original, usable_out_of_combat=True
        )
        try:
            self._setup_caster(mastery=True)
            read_patch, get_patch, clock = self._clock()
            mp_before = self.char1.traits.mp.value
            with read_patch, get_patch:
                self.call(
                    CmdCast(),
                    "wind_blade@3",
                    rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
                )
            self.assertEqual(self.char1.traits.mp.value, mp_before)
            self.assertEqual(clock.tick, 0)
        finally:
            SKILL_REGISTRY["wind_blade"] = original

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_unauthorized_scale_rejects_without_effect(self):
        from commands.action import CmdCast

        original = SKILL_REGISTRY["wind_blade"]
        SKILL_REGISTRY["wind_blade"] = replace(
            original, usable_out_of_combat=True
        )
        try:
            self._setup_caster(mastery=False)
            read_patch, get_patch, clock = self._clock()
            mp_before = self.char1.traits.mp.value
            with read_patch, get_patch:
                self.call(
                    CmdCast(),
                    "wind_blade@2",
                    rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
                )
            self.assertEqual(self.char1.traits.mp.value, mp_before)
            self.assertEqual(clock.tick, 0)
        finally:
            SKILL_REGISTRY["wind_blade"] = original

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scale_on_an_ineligible_spell_rejects_with_the_stable_message(self):
        from commands.action import CmdCast

        original = SKILL_REGISTRY["gale_step"]
        SKILL_REGISTRY["gale_step"] = replace(
            original, usable_out_of_combat=True
        )
        try:
            self._setup_caster(mastery=True)
            read_patch, get_patch, clock = self._clock()
            with read_patch, get_patch:
                self.call(
                    CmdCast(),
                    "gale_step@2",
                    rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
                )
            self.assertEqual(clock.tick, 0)
        finally:
            SKILL_REGISTRY["gale_step"] = original

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scale_one_stays_the_ordinary_command_path(self):
        from commands.action import CmdCast

        original = SKILL_REGISTRY["wind_blade"]
        SKILL_REGISTRY["wind_blade"] = replace(
            original, usable_out_of_combat=True
        )
        try:
            self._setup_caster(mastery=True)
            self._setup_target()
            read_patch, get_patch, clock = self._clock()
            with read_patch, get_patch:
                self.call(
                    CmdCast(),
                    "wind_blade@1=wind target",
                    f"{self.char1.key} 對 wind target 的攻擊擲出了",
                )
            one_end = self.char1.traits.mp.value
            # Reset the gauge (and its regen remainder) so the second cast
            # accrues the same regen; the exact deduction is the differential.
            self.char1.traits.mp.current = 500
            self.char1.traits.mp.regen_remainder = 0.0
            with read_patch, get_patch:
                self.call(
                    CmdCast(),
                    "wind_blade@2=wind target",
                    f"{self.char1.key} 對 wind target 的攻擊擲出了",
                )
            two_end = self.char1.traits.mp.value
            self.assertEqual(clock.tick, 12)
            # 2× scale deducts exactly 14 more than full scale.
            self.assertEqual(one_end - two_end, 14)
        finally:
            SKILL_REGISTRY["wind_blade"] = original
