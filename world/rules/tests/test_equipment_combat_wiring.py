"""Worn-equipment combat wiring tests (P2).

Covers the single accessor's additive fold and purity, the merged bundle's
arrival in live combat math (damage staging, required-roll estimation, cost
preview/preflight parity), the shared floored adjusted-agility path across
the consumers, the ``heal_gain`` heal funnel, and the structural
single-source guard that no other gameplay module reads the equipment-effect
rulebook data directly.
"""

from tools.spec_traceability import covers_requirement

import ast
import unittest
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules import combat
from world.rules.action import ActionRequest, ActionResolver
from world.rules.action_preview import preview_skill
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _heal_magnitude,
    _to_hit,
)
from world.rules.combat_modifiers import (
    adjusted_agility,
    evaluate_combat_modifiers,
    evaluate_combat_modifiers_no_create,
)
from world.rules.combat_session import engage, read_session, reconstruct_battlefield
from world.rules.disengage import _adjusted_agility as flee_agility
from world.rules.equipment import toggle_equipment
from world.rules.equipment_effects import (
    equipment_adjustments,
    equipment_gauge_caps,
)
from world.rules.items import ItemUseRequest, preflight_item_use
from world.rules.overwhelm import _required_roll
from world.rules.sexual_resist import _blended_score
from world.rules.tests.combat_fixtures import (
    BattlefieldIsolation,
    FakeEntity,
    grant_lineage,
)
from world.quests.catalog import register_catalog
from world.skills.registry import SKILL_REGISTRY

_ROOT = Path(__file__).resolve().parents[3]

# The loader module is the only production surface allowed to reference the
# loaded rulebook data; its accessors are the capability surface, and every
# other consumer goes through the accessor functions.
_RULEBOOK_ALLOWLIST = frozenset({Path("world/rules/equipment_effects.py")})


def _worn(entity, *, weapon=None, off=None, armor=None, accessories=()) -> None:
    """Write raw equipment storage directly onto a fixture entity."""
    entity.db.equipment = {
        "weapon_main": weapon,
        "weapon_off": off,
        "armor": armor,
        "accessories": list(accessories),
    }


def _player(key: str):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.traits.hp.rate = 0
    player.traits.magic_power.base = 30
    player.db.equipment = None
    player.db.inventory = []
    return player


def _monster(key: str, location):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = 500
    monster.traits.hp.current = 500
    monster.location = location
    return monster


class _WearerCase(EvenniaTestCase):
    """Evennia-backed base with a wear helper."""

    def wear(self, entity, *item_keys: str):
        entity.db.inventory = list(item_keys)
        for item_key in item_keys:
            result = toggle_equipment(entity, item_key)
            assert result.outcome == "success", (item_key, result.reason)
        return entity


class AccessorFoldTests(_WearerCase):
    @covers_requirement(
        "equipment-effects::equipment-adjustments-reach-every-consumer-through-one-accessor"
    )
    def test_worn_items_stack_additively(self):
        entity = self.wear(
            _player("fold stacker"),
            "gilded_saber",
            "knight_platemail",
            "protective_ring",
        )
        self.assertEqual(
            dict(equipment_adjustments(entity)),
            # +5 saber and -2 platemail; +8 platemail and +6 ring; the
            # platemail percent keeps its signed string shape.
            {"atk_phys": 3, "defense": 14, "agility": "-10%"},
        )
        self.assertEqual(dict(equipment_gauge_caps(entity)), {"hp": 25})

    def test_flat_and_percent_agility_split_across_keys(self):
        entity = self.wear(_player("fold splitter"), "shadow_blade", "chainmail")
        bundle = dict(equipment_adjustments(entity))
        self.assertEqual(bundle["atk_phys"], 12)
        self.assertEqual(bundle["agility_flat"], 3)
        self.assertEqual(bundle["agility"], "-5%")

    def test_percent_fields_sum_and_rerender_as_signed_strings(self):
        entity = self.wear(_player("fold percent"), "mage_robe", "royal_signet_ring")
        bundle = dict(equipment_adjustments(entity))
        self.assertEqual(bundle["mp_cost"], "-8%")
        self.assertEqual(bundle["sp_cost"], "-5%")
        self.assertEqual(bundle["magic_power"], 3)

    def test_accessor_is_a_pure_read(self):
        entity = self.wear(_player("fold purity"), "gilded_saber")

        def storage():
            return (
                repr(entity.db.equipment),
                repr(entity.db.inventory),
                repr(dict(entity.traits.trait_data)),
            )

        before = storage()
        dict(equipment_adjustments(entity))
        dict(equipment_gauge_caps(entity))
        evaluate_combat_modifiers_no_create(entity)
        self.assertEqual(storage(), before)

    @covers_requirement(
        "equipment-effects::equipment-adjustments-reach-every-consumer-through-one-accessor"
    )
    def test_malformed_storage_reads_as_empty_bundle(self):
        entity = _player("fold malformed")
        entity.db.equipment = "not-a-mapping"
        self.assertEqual(dict(equipment_adjustments(entity)), {})
        self.assertEqual(dict(equipment_gauge_caps(entity)), {})

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_both_evaluation_paths_merge_the_equipment_layer(self):
        entity = self.wear(_player("merge both paths"), "gilded_saber")
        with patch(
            "world.rules.combat_modifiers.matched_combat_modifiers",
            return_value=(("rule", {"atk_phys": 2}),),
        ):
            self.assertEqual(evaluate_combat_modifiers(entity)["atk_phys"], 7)
            self.assertEqual(
                evaluate_combat_modifiers_no_create(entity)["atk_phys"], 7
            )

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_malformed_storage_keeps_the_rule_bundle_intact(self):
        entity = self.wear(_player("merge malformed"), "gilded_saber")
        entity.db.equipment = "corrupted"
        with patch(
            "world.rules.combat_modifiers.matched_combat_modifiers",
            return_value=(("rule", {"atk_phys": 2}),),
        ):
            self.assertEqual(evaluate_combat_modifiers(entity), {"atk_phys": 2})
            self.assertEqual(
                evaluate_combat_modifiers_no_create(entity), {"atk_phys": 2}
            )


class SingleSourceStructureTests(unittest.TestCase):
    @covers_requirement(
        "equipment-effects::equipment-adjustments-reach-every-consumer-through-one-accessor"
    )
    def test_no_other_production_module_reads_the_rulebook_data(self):
        """Structural single-source guard (delta scenario).

        Production modules outside the loader itself must not reference the
        loaded rulebook symbol or its entry fields; consumers go through the
        accessor functions only.
        """
        offenders: list[str] = []
        for root in ("commands", "server", "typeclasses", "web", "world"):
            for path in (_ROOT / root).rglob("*.py"):
                relative = path.relative_to(_ROOT)
                if "tests" in relative.parts or relative in _RULEBOOK_ALLOWLIST:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Attribute)
                        and node.attr
                        in {"EQUIPMENT_EFFECT_RULES", "adjustments", "gauge_caps"}
                    ) or (
                        isinstance(node, ast.Name)
                        and node.id == "EQUIPMENT_EFFECT_RULES"
                    ):
                        offenders.append(f"{relative}:{node.lineno}")
        self.assertEqual(offenders, [])


class CostParityTests(BattlefieldIsolation, _WearerCase):
    def _context(self, player, monster):
        engage(player, monster)
        return BattlefieldActionContext(
            reconstruct_battlefield(player, read_session(player))
        )

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_preview_and_resolve_agree_on_equipment_adjusted_mp_cost(self):
        player = self.wear(_player("mp parity"), "mage_robe")
        grant_lineage(player, ["fire_ball"])
        room = create_object(Room, key="mp parity arena")
        player.location = room
        monster = _monster("mp parity goblin", room)
        context = self._context(player, monster)

        # The robe's -8% lands on the declared 14 MP: floor(14 * 0.92) == 12.
        self.assertEqual(
            evaluate_combat_modifiers_no_create(player)["mp_cost"], "-8%"
        )
        player.traits.mp.base = 12
        player.traits.mp.current = 12
        preview = preview_skill(player, "fire_ball", context, [monster])
        self.assertTrue(preview.enabled)
        preflight = ActionResolver.preflight(
            ActionRequest(player, "fire_ball", [monster], context)
        )
        self.assertEqual(preflight.outcome, "success")

        player.traits.mp.current = 11
        preview = preview_skill(player, "fire_ball", context, [monster])
        self.assertFalse(preview.enabled)
        preflight = ActionResolver.preflight(
            ActionRequest(player, "fire_ball", [monster], context)
        )
        self.assertEqual(preflight.outcome, "rejected")

        # A successful cast spends exactly the equipment-adjusted cost.
        player.traits.mp.current = 12
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = ActionResolver.resolve(
                ActionRequest(player, "fire_ball", [monster], context)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(player.traits.mp.current, 0)

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_preview_gates_on_equipment_adjusted_sp_cost(self):
        player = self.wear(_player("sp parity"), "royal_signet_ring")
        player.db.skills = {"active": ["light_sword_style"], "passive": []}
        room = create_object(Room, key="sp parity arena")
        player.location = room
        monster = _monster("sp parity goblin", room)
        context = self._context(player, monster)

        # Declared 6 SP, ring -5%: floor(6 * 0.95) == 5.
        player.traits.sp.current = 5
        self.assertTrue(
            preview_skill(player, "light_sword_style", context, [monster]).enabled
        )
        player.traits.sp.current = 4
        self.assertFalse(
            preview_skill(player, "light_sword_style", context, [monster]).enabled
        )

        # Without the ring the same 5 SP cannot afford the 6 SP skill.
        self.assertEqual(
            toggle_equipment(player, "royal_signet_ring").outcome, "success"
        )
        player.traits.sp.current = 5
        self.assertFalse(
            preview_skill(player, "light_sword_style", context, [monster]).enabled
        )
        player.traits.sp.current = 6
        self.assertTrue(
            preview_skill(player, "light_sword_style", context, [monster]).enabled
        )


class _FixtureFieldCase(BattlefieldIsolation, EvenniaTestCase):
    def _staged_damage(self, actor, target):
        with patch("world.rules.combat.roll_d100", return_value=100):
            pending = combat._handle_damage(
                actor, [target], "damage:dark:physical", {}, 1.0
            )[0]
        return int(pending.description.rsplit("|", 1)[1])


class DamageWiringTests(_FixtureFieldCase):
    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_worn_weapon_raises_staged_physical_damage(self):
        attacker = FakeEntity("wiring attacker", atk_phys=20, agility=10)
        defender = FakeEntity("wiring defender", hp=1000, agility=10, defense=5)
        baseline = self._staged_damage(attacker, defender)
        _worn(attacker, weapon="gilded_saber")
        worn = self._staged_damage(attacker, defender)
        # Crit roll 100 doubles the +5 flat attack before defense.
        self.assertEqual(worn - baseline, 10)

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_worn_armor_moves_the_defender_required_roll(self):
        attacker = FakeEntity("roll attacker", agility=10)
        defender = FakeEntity("roll defender", agility=30, defense=5)
        self.assertEqual(_required_roll(attacker, defender), 51 + 30 - 10)
        _worn(defender, armor="chainmail")
        # chainmail agility "-5%" scales the effective agility: 30 -> 28.5.
        self.assertAlmostEqual(_required_roll(attacker, defender), 69.5)
        hit, margin = _to_hit(attacker, defender, 70)
        self.assertTrue(hit)
        self.assertAlmostEqual(margin, 0.5)
        missed, _ = _to_hit(attacker, defender, 69)
        self.assertFalse(missed)


class AdjustedAgilityTests(_FixtureFieldCase):
    @covers_requirement(
        "combat-modifier-table::adjusted-agility-never-resolves-negative"
    )
    def test_flat_penalty_floors_agility_at_zero_everywhere(self):
        floored = FakeEntity("floored agility", agility=2)
        zero = FakeEntity("zero agility", agility=0)
        attacker = FakeEntity("steady attacker", agility=10)
        # shadow_blade_echo grants -3 flat agility: 2 - 3 floors to 0.
        _worn(floored, off="shadow_blade_echo")

        self.assertEqual(adjusted_agility(floored, {"agility_flat": -3}), 0.0)
        self.assertEqual(flee_agility(floored), flee_agility(zero))
        self.assertEqual(
            _required_roll(attacker, floored), _required_roll(attacker, zero)
        )
        # The floored defender behaves exactly like the zero-agility one in
        # live to-hit math.
        hit_a, margin_a = _to_hit(attacker, floored, 51)
        hit_b, margin_b = _to_hit(attacker, zero, 51)
        self.assertEqual(hit_a, hit_b)
        self.assertAlmostEqual(margin_a, margin_b)

    @covers_requirement(
        "combat-modifier-table::adjusted-agility-never-resolves-negative"
    )
    def test_resist_blend_shares_the_shared_floor(self):
        register_catalog()
        entity = _player("floored resist blend")
        entity.db.inventory = ["shadow_blade_echo"]
        self.assertEqual(
            toggle_equipment(entity, "shadow_blade_echo").outcome, "success"
        )
        entity.traits.agility.base = 2
        entity.traits.agility.current = 2
        blended = _blended_score(entity)
        # agility 2 - 3 floors to 0; the echo's +10 atk_phys is the flat
        # addend the blend's atk component reads.
        expected = 0.6 * 0.0 + 0.4 * (
            float(entity.skills.effective_value("atk_phys")) + 10
        )
        self.assertAlmostEqual(blended, expected)

    @covers_requirement(
        "combat-modifier-table::adjusted-agility-never-resolves-negative"
    )
    def test_percent_scales_then_flat_adds_then_floor(self):
        entity = FakeEntity("composed agility", agility=10)
        # -50% scales to 5, +3 lands on top of the scaled value.
        self.assertEqual(
            adjusted_agility(entity, {"agility": "-50%", "agility_flat": 3}),
            8.0,
        )
        # The floor lands after both components: a beyond--100% percent
        # still cannot leave the flat addend as a negative escape hatch.
        self.assertEqual(
            adjusted_agility(entity, {"agility": "-200%", "agility_flat": 3}),
            0.0,
        )
        self.assertEqual(adjusted_agility(entity, {"agility": "-200%"}), 0.0)

    @covers_requirement(
        "combat-modifier-table::adjusted-agility-never-resolves-negative"
    )
    def test_initiative_keeps_its_raw_agility_exception(self):
        boosted = FakeEntity("cloak carrier", agility=10)
        plain = FakeEntity("plain runner", agility=12)
        # shadow_blade grants +3 flat agility: adjusted 13 would beat 12,
        # so an initiative that consulted the bundle would invert the order.
        _worn(boosted, weapon="shadow_blade")
        field = Battlefield(
            {
                "first": frozenset({"cloak carrier"}),
                "second": frozenset({"plain runner"}),
            },
            {"cloak carrier": boosted, "plain runner": plain},
        )
        with patch("world.rules.combat.roll_d100", side_effect=[1, 1]):
            order = combat.roll_initiative(field)
        # Raw effective agility decides: 12 outranks 10 despite the gear.
        self.assertEqual(order, ["plain runner", "cloak carrier"])


class HealWiringTests(_WearerCase):
    def setUp(self):
        super().setUp()
        self.caster = _player("wiring caster")
        self.caster.traits.magic_power.base = 40

    @covers_requirement(
        "combat-resolution::skill-heal-magnitude-scales-by-the-merged-heal-gain-percent"
    )
    def test_holy_gear_amplifies_skill_heal_magnitude(self):
        self.assertEqual(_heal_magnitude(self.caster), 40)
        self.wear(self.caster, "radiant_holy_emblem")
        # emblem heal_gain "+20%": floor(40 * 1.2) == 48.
        self.assertEqual(_heal_magnitude(self.caster), 48)

    @covers_requirement(
        "combat-resolution::skill-heal-magnitude-scales-by-the-merged-heal-gain-percent"
    )
    def test_gear_scaling_floors_instead_of_banker_rounding(self):
        self.caster.traits.magic_power.base = 3
        self.wear(self.caster, "radiant_holy_emblem")
        self.assertEqual(_heal_magnitude(self.caster), 3)  # floor(3 * 1.2)

    @covers_requirement(
        "combat-resolution::skill-heal-magnitude-scales-by-the-merged-heal-gain-percent"
    )
    def test_magic_gear_lifts_the_heal_base(self):
        self.wear(self.caster, "mage_robe")
        # mage_robe magic_power +3 raises the caster-stat base.
        self.assertEqual(_heal_magnitude(self.caster), 43)

    @covers_requirement(
        "combat-resolution::skill-heal-magnitude-scales-by-the-merged-heal-gain-percent"
    )
    def test_potion_heal_stays_flat_under_heal_gear(self):
        self.wear(self.caster, "radiant_holy_emblem")
        self.caster.db.inventory = ["healing_potion"]
        self.caster.traits.hp.base = 100
        self.caster.traits.hp.current = 10
        preflight = preflight_item_use(
            ItemUseRequest(actor=self.caster, item_key="healing_potion"),
            in_combat=False,
        )
        self.assertTrue(preflight.allowed)
        self.assertEqual(preflight.plan.amount, 40)
        self.assertEqual(preflight.plan.gauge_restored, 50)

    def test_fractional_heal_gain_percent_is_tolerated(self):
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={"heal_gain": "+2.5%"},
        ):
            self.assertEqual(_heal_magnitude(self.caster), 41)  # floor(40*1.025)


class PreviewShapeTests(unittest.TestCase):
    def test_declared_costs_under_test(self):
        self.assertEqual(SKILL_REGISTRY["fire_ball"].cost, {"mp": 14})
        self.assertEqual(SKILL_REGISTRY["light_sword_style"].cost, {"sp": 6})
