"""Damage handler staging and event conversion tests."""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    SKILL_TIME_OVERRIDES,
    _EFFECT_HANDLER_SURFACES,
    _entries_from_effect,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _handle_damage,
    _stored_hp,
)

from .combat_fixtures import FakeEntity


class DamageEffectHandlerTests(unittest.TestCase):
    @covers_requirement("damage-effect-handlers::damage-is-registered-into-change-8-s-effect-handler-registry-declaring-the-traits")
    @covers_requirement("action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its")
    def test_registration_declares_exactly_the_traits_surface(self):
        self.assertEqual(
            _EFFECT_HANDLER_SURFACES["damage"],
            frozenset({"traits"}),
        )

    @covers_requirement("action-resolution-pipeline::nonlethal-policy-transforms-lethal-projection-before-eventlog-planners")
    def test_physical_damage_is_staged_before_apply(self):
        actor = FakeEntity("actor", atk_phys=20, agility=10)
        target = FakeEntity("target", hp=100, agility=10, defense=5)
        with (
            patch("world.rules.combat.roll_d100", return_value=75),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
        ):
            pending = _handle_damage(
                actor, [target], "damage:dark:physical", {}, 1.0
            )[0]
        self.assertEqual(target.traits.hp.value, 100)
        entries = _entries_from_effect("actor", pending)
        self.assertEqual([entry.kind for entry in entries], ["roll", "damage"])
        pending.apply()
        self.assertLess(target.traits.hp.value, 100)

    def test_apply_closure_consumes_no_randomness(self):
        actor = FakeEntity("actor")
        target = FakeEntity("target")
        with (
            patch("world.rules.combat.roll_d100", return_value=90) as roller,
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
        ):
            pending = _handle_damage(
                actor, [target], "damage:fire:magic", {}, 1.0
            )[0]
            self.assertEqual(roller.call_count, 1)
            pending.apply()
            self.assertEqual(roller.call_count, 1)

    @covers_requirement("damage-effect-handlers::damage-element-school-is-the-defined-convention-for-this-prefix")
    def test_invalid_school_and_element_reject_during_staging(self):
        actor = FakeEntity("actor")
        target = FakeEntity("target")
        with self.assertRaises(ValueError):
            _handle_damage(actor, [target], "damage:nope:magic", {}, 1.0)
        with self.assertRaises(ValueError):
            _handle_damage(actor, [target], "damage:fire:nope", {}, 1.0)

    @covers_requirement("damage-effect-handlers::combat-modifiers-apply-uniformly-regardless-of-origin")
    def test_modifier_bundle_changes_hit_math_without_origin_branch(self):
        actor = FakeEntity("actor", agility=10)
        target = FakeEntity("target", agility=10)

        def modifiers(entity):
            return {"accuracy": -10} if entity is actor else {}

        with (
            patch("world.rules.combat.roll_d100", return_value=51),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                side_effect=modifiers,
            ),
        ):
            pending = _handle_damage(
                actor, [target], "damage:fire:magic", {}, 1.0
            )[0]
        self.assertTrue(pending.description.endswith("|0|0"))


def _staged_amount(actor, target, effect_id, modifiers):
    """Resolve one hit and return the staged damage amount."""
    with (
        patch("world.rules.combat.roll_d100", return_value=100),
        patch(
            "world.rules.combat.evaluate_combat_modifiers",
            side_effect=modifiers,
        ),
    ):
        pending = _handle_damage(actor, [target], effect_id, {}, 1.0)[0]
    return int(pending.description.rsplit("|", 1)[1])


class AdjustedStatDamageTests(unittest.TestCase):
    """Flat atk_phys/defense bundle values enter the damage magnitude."""

    @covers_requirement(
        "combat-modifier-table::flat-defense-and-atk-phys-bundle-values-adjust-deterministic-damage-magnitude"
    )
    def test_physical_attack_gains_the_flat_atk_phys_bonus(self):
        actor = FakeEntity("actor", atk_phys=20, agility=10)
        target = FakeEntity("target", defense=5, agility=10)
        self.assertEqual(
            _staged_amount(
                actor,
                target,
                "damage:dark:physical",
                lambda entity: {"atk_phys": 5} if entity is actor else {},
            ),
            round((20 + 5) * 2.0) - 5,
        )

    def test_physical_attack_without_the_bonus_is_unchanged(self):
        actor = FakeEntity("actor", atk_phys=20, agility=10)
        target = FakeEntity("target", defense=5, agility=10)
        self.assertEqual(
            _staged_amount(
                actor,
                target,
                "damage:dark:physical",
                lambda entity: {},
            ),
            round(20 * 2.0) - 5,
        )

    @covers_requirement(
        "combat-modifier-table::flat-defense-and-atk-phys-bundle-values-adjust-deterministic-damage-magnitude"
    )
    def test_magic_school_damage_ignores_the_atk_phys_bonus(self):
        actor = FakeEntity("actor", magic_level=20, agility=10)
        target = FakeEntity("target", defense=5, agility=10)
        self.assertEqual(
            _staged_amount(
                actor,
                target,
                "damage:fire:magic",
                lambda entity: {"atk_phys": 5} if entity is actor else {},
            ),
            round(20 * 2.0) - 5,
        )

    @covers_requirement(
        "combat-modifier-table::flat-defense-and-atk-phys-bundle-values-adjust-deterministic-damage-magnitude"
    )
    def test_defense_bonus_mitigates_physical_and_magic_damage(self):
        actor = FakeEntity("actor", atk_phys=20, magic_level=20, agility=10)
        target = FakeEntity("target", defense=5, agility=10)
        for effect_id in ("damage:dark:physical", "damage:fire:magic"):
            with self.subTest(effect_id=effect_id):
                self.assertEqual(
                    _staged_amount(
                        actor,
                        target,
                        effect_id,
                        lambda entity: {"defense": 5} if entity is target else {},
                    ),
                    round(20 * 2.0) - 10,
                )

    def test_damage_floor_still_clamps_after_adjustments(self):
        actor = FakeEntity("actor", atk_phys=1, agility=10)
        target = FakeEntity("target", defense=999, agility=10)
        self.assertEqual(
            _staged_amount(
                actor,
                target,
                "damage:dark:physical",
                lambda entity: {"atk_phys": 5, "defense": 5},
            ),
            1,
        )

    def test_fractional_grant_bonus_stays_integer_in_the_staged_amount(self):
        actor = FakeEntity("actor", atk_phys=20, agility=10)
        target = FakeEntity("target", defense=5, agility=10)
        self.assertEqual(
            _staged_amount(
                actor,
                target,
                "damage:dark:physical",
                lambda entity: {"defense": 2.5} if entity is target else {},
            ),
            int(round(20 * 2.0) - (5 + 2.5)),
        )


class DamageResolverIntegrationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="actor")
        self.target = create_object(PlayerCharacter, key="target")
        for entity in (self.actor, self.target):
            entity.race = "human"
            entity.apply_race_baseline()
        # Human starting magic level (術師 tier) so the fire_ball cast passes
        # the element-mastery cast gate.
        self.actor.traits.magic_level.base = 30
        self.actor.db.skills = {"active": ["fire_ball"], "passive": []}
        self.target.db.skills = {"active": [], "passive": []}
        battlefield = Battlefield(
            {
                "party": frozenset({"actor"}),
                "foes": frozenset({"target"}),
            },
            {"actor": self.actor, "target": self.target},
        )
        self.request = ActionRequest(
            self.actor,
            "fire_ball",
            [self.target],
            BattlefieldActionContext(battlefield),
        )

    def test_damage_skill_resolves_and_emits_structured_entries(self):
        before = self.target.traits.hp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(self.request)
        self.assertEqual(result.outcome, "success")
        self.assertLess(self.target.traits.hp.value, before)
        self.assertEqual(
            [entry.kind for entry in result.event_log.entries[:2]],
            ["roll", "damage"],
        )

    @covers_requirement("damage-effect-handlers::the-to-hit-roll-and-damage-number-are-computed-during-effect-resolution-never-inside")
    @covers_requirement("action-resolution-pipeline::the-pipeline-executes-design-doc-6-1-s-eight-steps-in-order-each-rejecting-with-a")
    def test_late_rejection_leaves_hp_untouched_after_roll(self):
        before = self.target.traits.hp.value
        SKILL_TIME_OVERRIDES["fire_ball"] = -1
        try:
            with patch("world.rules.combat.roll_d100", return_value=100) as roller:
                result = ActionResolver.resolve(self.request)
        finally:
            SKILL_TIME_OVERRIDES.pop("fire_ball", None)
        self.assertEqual(result.reason, RejectReason.TIME_COST_LOOKUP_FAILED)
        self.assertEqual(roller.call_count, 1)
        self.assertEqual(self.target.traits.hp.value, before)

    def test_fled_target_reaches_named_range_rejection(self):
        self.request.context.battlefield.fled.add("target")
        result = ActionResolver.resolve(self.request)
        self.assertEqual(result.reason, RejectReason.TARGET_OUT_OF_RANGE)

    def test_miss_leaves_complete_hp_gauge_backing_data_unchanged(self):
        before = deepcopy(self.target.traits.hp._data)
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(self.request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.traits.hp._data, before)

    def test_combat_hp_read_does_not_advance_regeneration_timer(self):
        hp_data = self.target.traits.hp._data
        hp_data["current"] = max(hp_data["base"] - 5, 1)
        hp_data["last_update"] = 1
        before = deepcopy(hp_data)
        self.assertEqual(_stored_hp(self.target), before["current"])
        self.assertEqual(hp_data, before)

    def test_conferred_granted_defense_reduces_live_damage(self):
        from world.skills.handler import ConferredSkillGrant

        self.target.traits.hp.current = 100
        with patch("world.rules.combat.roll_d100", return_value=100):
            ActionResolver.resolve(self.request)
        base_damage = 100 - self.target.traits.hp.value
        self.target.traits.hp.current = 100
        self.target.db.skill_grants = [
            ConferredSkillGrant("elosia", "guardian_instinct", 0.5)
        ]
        with patch("world.rules.combat.roll_d100", return_value=100):
            ActionResolver.resolve(self.request)
        granted_damage = 100 - self.target.traits.hp.value
        self.assertGreater(base_damage, 0)
        # scale 0.5 of the flat +5 defense adds 2.5 to the subtracted term;
        # the truncated magnitude costs exactly 3 more HP.
        self.assertEqual(granted_damage, base_damage - 3)

    def test_imported_npc_with_a_valid_key_takes_damage_normally(self):
        from world.imports.loader import instantiate_character
        from world.imports.tests.helpers import example_record

        record = example_record()
        record["key"] = "orc alpha"
        npc = instantiate_character(record)
        self.assertEqual(npc.key, "orc alpha")
        npc.db.skills = {"active": [], "passive": []}
        npc.traits.agility.base = 5
        npc.traits.agility.current = 5
        battlefield = Battlefield(
            {
                "party": frozenset({"actor"}),
                "foes": frozenset({"orc alpha"}),
            },
            {"actor": self.actor, "orc alpha": npc},
        )
        request = ActionRequest(
            self.actor,
            "fire_ball",
            [npc],
            BattlefieldActionContext(battlefield),
        )
        before = npc.traits.hp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertNotEqual(result.reason, RejectReason.EVENT_LOG_CONSTRUCTION_FAILED)
        self.assertEqual(
            [entry.kind for entry in result.event_log.entries[:2]],
            ["roll", "damage"],
        )
        self.assertLess(npc.traits.hp.value, before)
