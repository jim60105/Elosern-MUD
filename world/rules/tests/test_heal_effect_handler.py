"""Heal and self-heal handler staging, event, and resolution tests."""

from tools.spec_traceability import covers_requirement

import unittest
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_SURFACES,
    _entries_from_effect,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    COMBAT_YAML,
    _handle_heal,
    _handle_self_heal,
    _heal_magnitude,
    _parse_heal_effect,
)
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec

from .combat_fixtures import FakeEntity


class HealEffectHandlerTests(unittest.TestCase):
    @covers_requirement("heal-effect-handler::heal-effect-prefix-restores-hp-capped-at-max")
    def test_registration_declares_exactly_the_traits_surface(self):
        self.assertEqual(
            _EFFECT_HANDLER_SURFACES["heal"],
            frozenset({"traits"}),
        )
        self.assertEqual(
            _EFFECT_HANDLER_SURFACES["self_heal"],
            frozenset({"traits"}),
        )

    def test_heal_magnitude_is_caster_stat_derived(self):
        actor = FakeEntity("actor", magic_level=40)
        self.assertEqual(
            _heal_magnitude(actor),
            round(40 * COMBAT_YAML["heal"]["multiplier"]),
        )

    def test_heal_shape_is_validated_during_staging(self):
        actor = FakeEntity("actor")
        target = FakeEntity("target")
        with self.assertRaises(ValueError):
            _parse_heal_effect("heal:everyone")
        with self.assertRaises(ValueError):
            _handle_heal(actor, [target], "heal:everyone", {}, 1.0)

    @covers_requirement("heal-effect-handler::heal-effect-prefix-restores-hp-capped-at-max")
    def test_heal_is_staged_before_apply_and_restores_hp(self):
        actor = FakeEntity("actor", magic_level=20)
        target = FakeEntity("target", hp=40, max_hp=100)
        pending = _handle_heal(actor, [target], "heal:single", {}, 1.0)[0]
        self.assertEqual(target.traits.hp.value, 40)
        self.assertTrue(pending.description.startswith("heal|"))
        pending.apply()
        self.assertEqual(target.traits.hp.value, 60)

    @covers_requirement("heal-effect-handler::heal-effect-prefix-restores-hp-capped-at-max")
    def test_healing_a_target_already_at_max_hp_is_a_noop(self):
        actor = FakeEntity("actor", magic_level=20)
        target = FakeEntity("target", hp=100, max_hp=100)
        _handle_heal(actor, [target], "heal:single", {}, 1.0)[0].apply()
        self.assertEqual(target.traits.hp.value, 100)

    @covers_requirement("heal-effect-handler::heal-effect-prefix-restores-hp-capped-at-max")
    def test_healing_a_near_death_target_is_capped_at_max_hp(self):
        actor = FakeEntity("actor", magic_level=200)
        target = FakeEntity("target", hp=1, max_hp=100)
        _handle_heal(actor, [target], "heal:single", {}, 1.0)[0].apply()
        self.assertEqual(target.traits.hp.value, 100)

    @covers_requirement("heal-effect-handler::heal-area-targets-every-valid-target-in-the-action-s-target-set")
    def test_area_heal_restores_each_target_independently(self):
        actor = FakeEntity("actor", magic_level=30)
        low = FakeEntity("low", hp=10, max_hp=100)
        mid = FakeEntity("mid", hp=60, max_hp=100)
        high = FakeEntity("high", hp=90, max_hp=100)
        for effect in _handle_heal(actor, [low, mid, high], "heal:area", {}, 1.0):
            effect.apply()
        self.assertEqual(low.traits.hp.value, 40)
        self.assertEqual(mid.traits.hp.value, 90)
        self.assertEqual(high.traits.hp.value, 100)

    @covers_requirement("heal-effect-handler::self-heal-restores-the-acting-entity-s-hp-regardless-of-the-skill-s-resolved-targets")
    def test_self_heal_binds_the_actor_and_ignores_the_target_list(self):
        actor = FakeEntity("actor", hp=30, max_hp=100, magic_level=20)
        target = FakeEntity("target", hp=100, max_hp=100)
        with self.assertRaises(ValueError):
            _handle_self_heal(actor, [target], "self_heal:single", {}, 1.0)
        pending = _handle_self_heal(actor, [target], "self_heal", {}, 1.0)[0]
        self.assertTrue(pending.description.startswith("self_heal|actor|"))
        pending.apply()
        self.assertEqual(actor.traits.hp.value, 50)
        self.assertEqual(target.traits.hp.value, 100)

    def test_heal_entries_emit_a_heal_event_with_amount(self):
        actor = FakeEntity("actor")
        target = FakeEntity("target", hp=50, max_hp=100)
        pending = _handle_heal(actor, [target], "heal:single", {}, 1.0)[0]
        entries = _entries_from_effect("actor", pending)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].kind, "heal")
        self.assertEqual(entries[0].data["amount"], _heal_magnitude(actor))

    def test_self_heal_entries_emit_a_self_heal_event_with_amount(self):
        actor = FakeEntity("actor", hp=50, max_hp=100, magic_level=20)
        pending = _handle_self_heal(actor, [], "self_heal", {}, 1.0)[0]
        entries = _entries_from_effect("actor", pending)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].kind, "self_heal")
        self.assertEqual(entries[0].target, "actor")
        self.assertEqual(entries[0].data["amount"], 20)

    def test_malformed_heal_description_is_rejected(self):
        actor = FakeEntity("actor")
        pending = _handle_heal(
            actor, [FakeEntity("target")], "heal:single", {}, 1.0
        )[0]
        malformed = PendingEffect(
            entity=pending.entity,
            description="heal|target|5|extra",
            surfaces=frozenset(),
            apply=pending.apply,
        )
        with self.assertRaises(ValueError):
            _entries_from_effect("actor", malformed)

    def test_heal_magnitude_never_drops_below_the_floor(self):
        actor = FakeEntity("actor", magic_level=0)
        self.assertEqual(
            _heal_magnitude(actor),
            COMBAT_YAML["heal"]["floor"],
        )


class HealResolverIntegrationTests(EvenniaTest):
    """End-to-end heal resolution through the eight-step action pipeline."""

    _TEST_SKILL_KEY = "heal_effect_handler_test"

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="healer")
        self.target = create_object(PlayerCharacter, key="patient")
        self.ally = create_object(PlayerCharacter, key="ally")
        enemy = create_object(PlayerCharacter, key="enemy")
        for entity in (self.actor, self.target, self.ally, enemy):
            entity.race = "human"
            entity.apply_race_baseline()
            entity.db.skills = {"active": [], "passive": []}
        self.actor.traits.hp.current = 30
        self.target.traits.hp.current = 40
        self.ally.traits.hp.current = 80
        enemy.traits.hp.current = 60
        self.actor.traits.magic_level.base = 20
        self.actor.traits.magic_level.current = 20
        self.battlefield = Battlefield(
            {
                "party": frozenset({"healer", "patient", "ally"}),
                "foes": frozenset({"enemy"}),
            },
            {
                "healer": self.actor,
                "patient": self.target,
                "ally": self.ally,
                "enemy": enemy,
            },
        )

    def _grant(self, effects: list[str], target_spec: TargetSpec) -> SkillDef:
        skill = SkillDef(
            key=self._TEST_SKILL_KEY,
            label="測試治療",
            description="測試用的治療技能。",
            kind=SkillKind.ACTIVE,
            target_spec=target_spec,
            cost={"mp": 5},
            usable_out_of_combat=True,
            element=None,
            effects=effects,
        )
        previous = SKILL_REGISTRY.get(self._TEST_SKILL_KEY)

        def _restore():
            if previous is None:
                SKILL_REGISTRY.pop(self._TEST_SKILL_KEY, None)
            else:
                SKILL_REGISTRY[self._TEST_SKILL_KEY] = previous

        self.addCleanup(_restore)
        SKILL_REGISTRY[self._TEST_SKILL_KEY] = skill
        self.actor.db.skills = {
            "active": [self._TEST_SKILL_KEY],
            "passive": [],
        }
        return skill

    def _request(self, skill: SkillDef, targets: list[Any]):
        return ActionRequest(
            self.actor,
            skill.key,
            targets,
            BattlefieldActionContext(self.battlefield),
        )

    @covers_requirement("heal-effect-handler::heal-effect-prefix-restores-hp-capped-at-max")
    def test_single_heal_restores_a_damaged_target_up_to_max(self):
        skill = self._grant(["heal:single"], TargetSpec.SINGLE)
        expected = _heal_magnitude(self.actor)
        result = ActionResolver.resolve(self._request(skill, [self.target]))
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.target.traits.hp.current,
            min(100, 40 + expected),
        )
        entry_kinds = [entry.kind for entry in result.event_log.entries]
        self.assertIn("heal", entry_kinds)

    @covers_requirement("heal-effect-handler::heal-effect-prefix-restores-hp-capped-at-max")
    def test_healing_a_full_hp_target_resolves_without_error(self):
        skill = self._grant(["heal:single"], TargetSpec.SINGLE)
        self.target.traits.hp.current = 100
        result = ActionResolver.resolve(self._request(skill, [self.target]))
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.traits.hp.current, 100)

    @covers_requirement("heal-effect-handler::heal-area-targets-every-valid-target-in-the-action-s-target-set")
    def test_area_heal_restores_each_target_independently_through_the_resolver(self):
        skill = self._grant(["heal:area"], TargetSpec.AREA)
        expected = _heal_magnitude(self.actor)
        result = ActionResolver.resolve(
            self._request(skill, [self.target, self.ally])
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.traits.hp.current, min(100, 40 + expected))
        self.assertEqual(self.ally.traits.hp.current, min(100, 80 + expected))

    @covers_requirement("heal-effect-handler::self-heal-restores-the-acting-entity-s-hp-regardless-of-the-skill-s-resolved-targets")
    def test_self_heal_restores_the_caster_while_damage_hits_the_enemy(self):
        skill = self._grant(
            ["damage:fire:magic", "self_heal"],
            TargetSpec.SINGLE,
        )
        enemy = self.battlefield.roster["enemy"]
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
        ):
            result = ActionResolver.resolve(self._request(skill, [enemy]))
        self.assertEqual(result.outcome, "success")
        self.assertLess(enemy.traits.hp.current, 60)
        self.assertEqual(
            self.actor.traits.hp.current,
            min(100, 30 + _heal_magnitude(self.actor)),
        )

    @covers_requirement("heal-effect-handler::neither-heal-nor-self-heal-can-revive-a-knocked-out-target")
    def test_heal_targeting_a_knocked_out_ally_is_rejected_before_the_handler(self):
        skill = self._grant(["heal:single"], TargetSpec.SINGLE)
        self.target.traits.hp.current = 0
        handler = unittest.mock.MagicMock()
        with patch.dict(_EFFECT_HANDLERS, {"heal": handler}):
            result = ActionResolver.resolve(self._request(skill, [self.target]))
        self.assertEqual(result.reason, RejectReason.TARGET_DEAD)
        handler.assert_not_called()
        self.assertEqual(self.target.traits.hp.current, 0)

    @covers_requirement("heal-effect-handler::neither-heal-nor-self-heal-can-revive-a-knocked-out-target")
    def test_mid_action_damage_cannot_be_reversed_by_a_later_heal(self):
        skill = self._grant(
            ["damage:fire:magic", "heal:single"],
            TargetSpec.SINGLE,
        )
        enemy = self.battlefield.roster["enemy"]
        enemy.traits.hp.current = 10
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
        ):
            result = ActionResolver.resolve(self._request(skill, [enemy]))
        self.assertEqual(result.outcome, "success")
        self.assertEqual(enemy.traits.hp.current, 0)

    @covers_requirement("heal-effect-handler::neither-heal-nor-self-heal-can-revive-a-knocked-out-target")
    def test_dead_caster_self_heal_does_not_revive(self):
        skill = self._grant(["self_heal"], TargetSpec.NONE)
        self.actor.traits.hp.current = 0
        result = ActionResolver.resolve(self._request(skill, []))
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.hp.current, 0)
