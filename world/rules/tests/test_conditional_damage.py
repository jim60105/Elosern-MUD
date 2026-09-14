"""Synthetic behavior tests for conditional damage policies and combat traits (light-judgment-traits)."""

import math
from collections.abc import Mapping
from copy import deepcopy
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.imports.loader import load_batch
from world.imports.schema import CHARACTER_SCHEMA_V1
from world.imports.tests.helpers import example_record
from world.imports.validate import _check_combat_traits, validate_character
from world.maps.wilderness_population import MonsterPopulation, _matches_expected, _spawn
from world.quests.compile import (
    QuestCompileError,
    _characterization_from_payload,
    _compile_characterization,
    _npc_req_canonical,
)
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _handle_damage,
    _max_hp,
    _stored_hp,
)
from world.rules.target_facts import (
    get_affinity_elements,
    get_combat_traits,
    get_target_facts,
    matches_target_predicate,
)
from world.rules.traits import (
    COMBAT_TRAITS_VOCABULARY,
    restore_gauges_to_full,
    set_combat_traits,
    validate_combat_traits,
)
from world.skills.effects import (
    DamageEffect,
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    HealEffect,
    ResolvedEffect,
)
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill, synthetic_registries

from .combat_fixtures import grant_lineage


# Synthetic skills for behavior tests
# Base synthetic fire damage spell (potency 1.0)
_T_BASE_DAMAGE = SYNTH_SKILLS["t_ember_burst"]

# Synthetic anti-dark / anti-undead damage skill with +50% multiplier
_T_JUDGMENT_BURST = make_skill(
    "t_judgment_burst",
    element=_T_BASE_DAMAGE.element,
    effects=("damage:fire:magic",),
    effect_policies=(
        EffectPolicy(
            coefficient=1.0,
            damage=DamagePolicy(
                predicate=("dark", "undead"),
                attack_multiplier=1.5,
                bypass_defense=False,
                max_hp_fraction=0.0,
            ),
        ),
    ),
)

# Synthetic defense bypass skill (no attack bonus)
_T_EXECUTION_BURST = make_skill(
    "t_execution_burst",
    element=_T_BASE_DAMAGE.element,
    effects=("damage:fire:magic",),
    effect_policies=(
        EffectPolicy(
            coefficient=1.0,
            damage=DamagePolicy(
                predicate=("dark", "undead"),
                attack_multiplier=1.0,
                bypass_defense=True,
                max_hp_fraction=0.0,
            ),
        ),
    ),
)

# Synthetic devastation skill with 10% max HP rider (unconditional on hit)
_T_DEVASTATION_BURST = make_skill(
    "t_devastation_burst",
    element=_T_BASE_DAMAGE.element,
    effects=("damage:fire:magic",),
    effect_policies=(
        EffectPolicy(
            coefficient=1.0,
            damage=DamagePolicy(
                predicate=(),
                attack_multiplier=1.0,
                bypass_defense=False,
                max_hp_fraction=0.10,
            ),
        ),
    ),
)

# Synthetic conditional skill with both bypass and 10% max HP rider
_T_BYPASS_DEVASTATION = make_skill(
    "t_bypass_devastation",
    element=_T_BASE_DAMAGE.element,
    effects=("damage:fire:magic",),
    effect_policies=(
        EffectPolicy(
            coefficient=1.0,
            damage=DamagePolicy(
                predicate=("dark", "undead"),
                attack_multiplier=1.0,
                bypass_defense=True,
                max_hp_fraction=0.10,
            ),
        ),
    ),
)

# Second synthetic non-light configuration: water-predicated skill with bypass
_T_WATER_HUNTER = make_skill(
    "t_water_hunter",
    element=_T_BASE_DAMAGE.element,
    effects=("damage:fire:magic",),
    effect_policies=(
        EffectPolicy(
            coefficient=1.0,
            damage=DamagePolicy(
                predicate=("water",),
                attack_multiplier=1.5,
                bypass_defense=True,
                max_hp_fraction=0.0,
            ),
        ),
    ),
)

_EXTRA_SKILLS = {
    _T_BASE_DAMAGE.key: _T_BASE_DAMAGE,
    _T_JUDGMENT_BURST.key: _T_JUDGMENT_BURST,
    _T_EXECUTION_BURST.key: _T_EXECUTION_BURST,
    _T_DEVASTATION_BURST.key: _T_DEVASTATION_BURST,
    _T_BYPASS_DEVASTATION.key: _T_BYPASS_DEVASTATION,
    _T_WATER_HUNTER.key: _T_WATER_HUNTER,
}
_SCOPE = synthetic_registries("skills", extra={"skills": _EXTRA_SKILLS})


class DamagePolicyValidationTests(unittest.TestCase):
    """Validation and invariant tests for DamagePolicy."""

    def test_empty_predicate_with_attack_multiplier_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(predicate=(), attack_multiplier=1.5)
        self.assertIn("empty predicate", str(ctx.exception))

    def test_empty_predicate_with_bypass_defense_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(predicate=(), bypass_defense=True)
        self.assertIn("empty predicate", str(ctx.exception))

    def test_pure_unconditional_rider_with_empty_predicate_is_valid(self):
        policy = DamagePolicy(predicate=(), max_hp_fraction=0.10)
        self.assertEqual(policy.predicate, ())
        self.assertEqual(policy.attack_multiplier, 1.0)
        self.assertFalse(policy.bypass_defense)
        self.assertEqual(policy.max_hp_fraction, 0.10)

    def test_namespaced_predicate_entries_raise(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(predicate=("affinity:dark",), attack_multiplier=1.5)
        self.assertIn("bare registry keys, not namespaced", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(predicate=("combat_trait:undead",), attack_multiplier=1.5)
        self.assertIn("bare registry keys, not namespaced", str(ctx.exception))

    def test_unknown_predicate_fact_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(predicate=("dragon",), attack_multiplier=1.5)
        self.assertIn("unknown DamagePolicy predicate fact", str(ctx.exception))

    def test_duplicate_predicate_entries_raise(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(predicate=("dark", "dark"), attack_multiplier=1.5)
        self.assertIn("duplicate DamagePolicy predicate entry", str(ctx.exception))

    def test_non_string_predicate_entry_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(predicate=("dark", 123), attack_multiplier=1.5)
        self.assertIn("must be a string", str(ctx.exception))

    def test_non_sequence_predicate_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(predicate="dark", attack_multiplier=1.5)
        self.assertIn("sequence of strings", str(ctx.exception))

    def test_invalid_attack_multiplier_raises(self):
        for bad in (0, -1.0, float("nan"), float("inf"), True, False):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    DamagePolicy(predicate=("dark",), attack_multiplier=bad)

    def test_invalid_bypass_defense_raises(self):
        for bad in ("yes", 1, 0, None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    DamagePolicy(predicate=("dark",), bypass_defense=bad)

    def test_invalid_max_hp_fraction_raises(self):
        for bad in (-0.01, 1.01, float("nan"), float("inf"), True, False, "0.1"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    DamagePolicy(max_hp_fraction=bad)

    def test_skill_def_rejects_damage_policy_on_non_damage_effect(self):
        with self.assertRaises(ValueError) as ctx:
            make_skill(
                "t_invalid_heal_policy",
                effects=("heal:single",),
                effect_policies=(
                    EffectPolicy(
                        damage=DamagePolicy(predicate=(), max_hp_fraction=0.1)
                    ),
                ),
            )
        self.assertIn("not a DamageEffect", str(ctx.exception))

    def test_alias_parameters_are_supported(self):
        policy = DamagePolicy(
            target_facts=("dark",),
            conditional_multiplier=1.5,
            conditional_defense_bypass=True,
        )
        self.assertEqual(policy.predicate, ("dark",))
        self.assertEqual(policy.target_facts, ("dark",))
        self.assertEqual(policy.attack_multiplier, 1.5)
        self.assertEqual(policy.conditional_multiplier, 1.5)
        self.assertTrue(policy.bypass_defense)


class TargetFactsPurityTests(EvenniaTestCase):
    """Purity and correctness tests for target fact readers."""

    def test_uninitialized_entity_does_not_materialize_storage(self):
        char = create_object(PlayerCharacter, key="uninit_char")
        # Ensure combat_traits attribute has not been written to DB
        self.assertIsNone(char.attributes.get("combat_traits"))

        traits = get_combat_traits(char)
        self.assertEqual(traits, frozenset())
        # Inspecting did not write storage
        self.assertIsNone(char.attributes.get("combat_traits"))

        affinities = get_affinity_elements(char)
        self.assertEqual(affinities, frozenset())
        self.assertIsNone(char.attributes.get("affinity_elements"))

    @covers_requirement(
        "combat-target-traits::combat-target-facts-are-explicit-and-persist-through-construction"
    )
    def test_names_and_labels_do_not_imply_facts(self):
        char = create_object(PlayerCharacter, key="Dark Undead Necromancer")
        char.db.desc = "A dark undead creature of darkness."
        self.assertEqual(get_combat_traits(char), frozenset())
        self.assertEqual(get_affinity_elements(char), frozenset())
        self.assertEqual(get_target_facts(char), frozenset())
        self.assertFalse(matches_target_predicate(char, ("dark", "undead")))

    def test_explicit_facts_are_returned_accurately(self):
        char = create_object(PlayerCharacter, key="test_facts_char")
        char.db.affinity_elements = ["dark", "fire"]
        set_combat_traits(char, ["undead"])

        self.assertEqual(get_affinity_elements(char), frozenset({"dark", "fire"}))
        self.assertEqual(get_combat_traits(char), frozenset({"undead"}))
        self.assertEqual(
            get_target_facts(char), frozenset({"dark", "fire", "undead"})
        )

        self.assertTrue(matches_target_predicate(char, ("dark",)))
        self.assertTrue(matches_target_predicate(char, ("undead",)))
        self.assertTrue(matches_target_predicate(char, ("water", "undead")))
        self.assertFalse(matches_target_predicate(char, ("water", "earth")))
        self.assertFalse(matches_target_predicate(char, ()))


@_SCOPE
class ConditionalDamageMechanicsTests(EvenniaTestCase):
    """Behavior tests for conditional damage computation, banding, and riders."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="cond_actor")
        self.target = create_object(PlayerCharacter, key="cond_target")
        for entity in (self.actor, self.target):
            entity.race = "human"
            entity.apply_race_baseline()
        self.actor.traits.magic_power.base = 40
        self.target.traits.defense.base = 20
        restore_gauges_to_full(self.actor)
        restore_gauges_to_full(self.target)
        self.target.db.skills = {"active": [], "passive": []}
        grant_lineage(
            self.actor,
            list(_EXTRA_SKILLS.keys()),
        )

    def _resolve_cast(self, skill_key: str, roll: int = 60, scale: float = 1.0):
        restore_gauges_to_full(self.actor)
        battlefield = Battlefield(
            {"party": frozenset({"cond_actor"}), "foes": frozenset({"cond_target"})},
            {"cond_actor": self.actor, "cond_target": self.target},
        )
        request = ActionRequest(
            self.actor,
            skill_key,
            [self.target],
            BattlefieldActionContext(battlefield),
            scale=scale,
        )
        with patch("world.rules.combat.roll_d100", return_value=roll):
            result = ActionResolver.resolve(request)
            return result

    @covers_requirement(
        "skill-effect-model::conditional-damage-policies-compose-without-double-matching",
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_two_facts_match_once_not_squared(self):
        """WHEN target has both dark affinity AND undead trait, 1.5x applies ONCE."""
        # Setup target with both facts
        self.target.db.affinity_elements = ["dark"]
        set_combat_traits(self.target, ["undead"])
        restore_gauges_to_full(self.target)

        before_hp = _stored_hp(self.target)
        result = self._resolve_cast(_T_JUDGMENT_BURST.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_both = before_hp - _stored_hp(self.target)

        # Reset target to ONLY undead
        self.target.db.affinity_elements = []
        restore_gauges_to_full(self.target)
        result = self._resolve_cast(_T_JUDGMENT_BURST.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_undead_only = before_hp - _stored_hp(self.target)

        # Reset target to NEUTRAL (neither fact)
        set_combat_traits(self.target, [])
        restore_gauges_to_full(self.target)
        result = self._resolve_cast(_T_JUDGMENT_BURST.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_neutral = before_hp - _stored_hp(self.target)

        # Damage against (dark + undead) MUST equal damage against (undead only): 40
        self.assertEqual(damage_both, damage_undead_only)
        self.assertEqual(damage_both, 40)
        # And must be strictly greater than neutral damage: 20 (40 * 1.5 - 20 vs 40 - 20)
        self.assertEqual(damage_neutral, 20)
        self.assertGreater(damage_both, damage_neutral)

    @covers_requirement(
        "skill-effect-model::conditional-damage-policies-compose-without-double-matching",
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_bypass_and_bonus_are_independent(self):
        """Bypass ignores defense without adding undeclared attack bonus."""
        self.target.db.affinity_elements = ["dark"]
        self.target.traits.defense.base = 20
        restore_gauges_to_full(self.target)

        # Cast execution burst (bypass defense, no bonus multiplier): 40 - 0 = 40
        before_hp = _stored_hp(self.target)
        result = self._resolve_cast(_T_EXECUTION_BURST.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_bypassed = before_hp - _stored_hp(self.target)
        self.assertEqual(damage_bypassed, 40)

        # Now test neutral target where defense is NOT bypassed: 40 - 20 = 20
        self.target.db.affinity_elements = []
        restore_gauges_to_full(self.target)
        result = self._resolve_cast(_T_EXECUTION_BURST.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_not_bypassed = before_hp - _stored_hp(self.target)
        self.assertEqual(damage_not_bypassed, 20)

        # Defense was 20; bypassed damage is exactly 20 higher than non-bypassed
        self.assertEqual(damage_bypassed - damage_not_bypassed, 20)

    @covers_requirement(
        "skill-effect-model::conditional-damage-policies-compose-without-double-matching",
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_percent_rider_requires_a_hit(self):
        """On a miss, zero damage is dealt and percentage rider does not apply."""
        restore_gauges_to_full(self.target)
        before_hp = _stored_hp(self.target)
        before_data = deepcopy(self.target.traits.hp._data)
        # Roll 1 is guaranteed miss
        result = self._resolve_cast(_T_DEVASTATION_BURST.key, roll=1)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.traits.hp._data, before_data)
        self.assertEqual(_stored_hp(self.target), before_hp)

        # On hit (roll 60): 10% of max HP is added to base damage
        rider = math.floor(_max_hp(self.target) * 0.10)
        result = self._resolve_cast(_T_DEVASTATION_BURST.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_with_rider = before_hp - _stored_hp(self.target)

        # Compare with base damage without rider
        restore_gauges_to_full(self.target)
        result = self._resolve_cast(_T_BASE_DAMAGE.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_base = before_hp - _stored_hp(self.target)

        # Exactly rider difference
        self.assertEqual(damage_with_rider - damage_base, rider)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_unconditional_rider_applies_even_when_predicate_does_not_match(self):
        """A policy with a predicate and max_hp_fraction applies rider on hit even when target does not match."""
        # Target is neutral (neither dark nor undead)
        self.target.db.affinity_elements = []
        set_combat_traits(self.target, [])
        restore_gauges_to_full(self.target)
        before_hp = _stored_hp(self.target)

        # Cast bypass + devastation (predicate is dark/undead, max_hp_fraction is 0.10)
        result = self._resolve_cast(_T_BYPASS_DEVASTATION.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage = before_hp - _stored_hp(self.target)

        # Base damage without rider against same defense
        restore_gauges_to_full(self.target)
        result = self._resolve_cast(_T_BASE_DAMAGE.key, roll=60)
        self.assertEqual(result.outcome, "success")
        base_damage = before_hp - _stored_hp(self.target)

        # Defense was NOT bypassed (still subtracted), but rider WAS added!
        rider = math.floor(_max_hp(self.target) * 0.10)
        self.assertEqual(damage - base_damage, rider)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_freeform_scaling_scales_all_components_including_rider(self):
        """Freeform scaling applies after the max-HP rider is added."""
        restore_gauges_to_full(self.target)
        event_context = {
            "resolved_effect": ResolvedEffect(
                policy=EffectPolicy(damage=DamagePolicy(max_hp_fraction=0.10))
            )
        }
        with patch("world.rules.combat.roll_d100", return_value=60):
            unscaled = _handle_damage(
                self.actor, [self.target], "damage:fire:magic", event_context, scale=1.0
            )
            scaled = _handle_damage(
                self.actor, [self.target], "damage:fire:magic", event_context, scale=0.5
            )

        unscaled_amount = int(unscaled[0].description.rsplit("|", 1)[1])
        scaled_amount = int(scaled[0].description.rsplit("|", 1)[1])
        self.assertEqual(scaled_amount, unscaled_amount // 2)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_conditional_damage_preserves_nonlethal_outcome(self):
        """Protected entity hit with lethal conditional damage floors at 1 HP."""
        self.target.db.affinity_elements = ["dark"]
        self.target.traits.hp._data["current"] = 10
        # High magic power to ensure lethal crossing
        self.actor.traits.magic_power.base = 100

        battlefield = Battlefield(
            {"party": frozenset({"cond_actor"}), "foes": frozenset({"cond_target"})},
            {"cond_actor": self.actor, "cond_target": self.target},
        )
        request = ActionRequest(
            self.actor,
            _T_BYPASS_DEVASTATION.key,
            [self.target],
            BattlefieldActionContext(battlefield, nonlethal=True),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(_stored_hp(self.target), 1)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_high_defense_clamped_to_floor_without_bypass_and_full_with_bypass(self):
        """High defense clamps damage to floor(1); bypass ignores defense completely."""
        self.target.traits.defense.base = 500  # Absorbs all attack
        self.target.db.affinity_elements = []  # Neutral -> no bypass
        set_combat_traits(self.target, [])
        restore_gauges_to_full(self.target)
        before_hp = _stored_hp(self.target)

        result = self._resolve_cast(_T_EXECUTION_BURST.key, roll=60)
        self.assertEqual(result.outcome, "success")
        # Clamped to damage floor (1)
        self.assertEqual(before_hp - _stored_hp(self.target), 1)

        # Now grant dark affinity -> bypass activates
        self.target.db.affinity_elements = ["dark"]
        restore_gauges_to_full(self.target)
        result = self._resolve_cast(_T_EXECUTION_BURST.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage = before_hp - _stored_hp(self.target)
        # Full un-mitigated attack damage: 40
        self.assertEqual(damage, 40)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_second_synthetic_non_light_configuration(self):
        """Reusable mechanics work for a non-light elemental predicate (fire vs water)."""
        self.target.db.affinity_elements = ["water"]
        self.target.traits.defense.base = 25
        restore_gauges_to_full(self.target)
        before_hp = _stored_hp(self.target)

        # Water hunter has predicate ("water",), attack_multiplier=1.5, bypass_defense=True
        result = self._resolve_cast(_T_WATER_HUNTER.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_water = before_hp - _stored_hp(self.target)
        # Attack = 40 * 1.5 = 60, defense = 0 -> damage = 60
        self.assertEqual(damage_water, 60)

        # Neutral target without water affinity
        self.target.db.affinity_elements = ["earth"]
        restore_gauges_to_full(self.target)
        result = self._resolve_cast(_T_WATER_HUNTER.key, roll=60)
        self.assertEqual(result.outcome, "success")
        damage_earth = before_hp - _stored_hp(self.target)
        # Attack = 40, defense = 25 -> damage = 15
        self.assertEqual(damage_earth, 15)

        # Water target has defense bypassed AND 1.5x attack, so takes much higher damage
        self.assertGreater(damage_water, damage_earth + 25)

    def test_transaction_rollback_restores_hp_on_late_failure(self):
        """A multi-effect commit failure cleanly rolls back the damage effect."""
        restore_gauges_to_full(self.target)
        before_hp = _stored_hp(self.target)
        battlefield = Battlefield(
            {"party": frozenset({"cond_actor"}), "foes": frozenset({"cond_target"})},
            {"cond_actor": self.actor, "cond_target": self.target},
        )
        request = ActionRequest(
            self.actor,
            _T_JUDGMENT_BURST.key,
            [self.target],
            BattlefieldActionContext(battlefield),
        )

        with patch("world.rules.action._commit", side_effect=RuntimeError("simulated commit crash")):
            with self.assertRaises(RuntimeError):
                ActionResolver.resolve(request)

        # Target HP must remain unchanged
        self.assertEqual(_stored_hp(self.target), before_hp)


class CombatTraitsPersistenceAndConstructionTests(EvenniaTestCase):
    """Tests for combat traits validation, import, spawn, and persistence."""

    def test_validate_combat_traits_rules(self):
        # Valid cases
        self.assertEqual(validate_combat_traits(None), [])
        self.assertEqual(validate_combat_traits([]), [])
        self.assertEqual(validate_combat_traits(["undead"]), ["undead"])
        self.assertEqual(validate_combat_traits(("undead",)), ["undead"])

        # Invalid cases
        with self.assertRaises(ValueError):
            validate_combat_traits("undead")  # Str is not sequence of traits
        with self.assertRaises(ValueError):
            validate_combat_traits(b"undead")  # Bytes rejected
        with self.assertRaises(ValueError):
            validate_combat_traits(["undead", "undead"])  # Duplicate rejected
        with self.assertRaises(ValueError):
            validate_combat_traits(["goblin"])  # Unknown trait rejected
        with self.assertRaises(ValueError):
            validate_combat_traits([123])  # Non-string rejected

    @covers_requirement(
        "combat-target-traits::combat-target-facts-are-explicit-and-persist-through-construction"
    )
    def test_set_combat_traits_persists_and_survives_refetch(self):
        npc = create_object(NPC, key="undead_guard")
        set_combat_traits(npc, ["undead"])
        self.assertEqual(get_combat_traits(npc), frozenset({"undead"}))

        # Refetch from DB
        pk = npc.pk
        refetched = NPC.objects.get(id=pk)
        self.assertEqual(get_combat_traits(refetched), frozenset({"undead"}))

    @covers_requirement(
        "combat-target-traits::combat-target-facts-are-explicit-and-persist-through-construction"
    )
    def test_character_schema_and_validator_accept_combat_traits(self):
        record = example_record()
        record["combat_traits"] = ["undead"]
        report = validate_character(record)
        self.assertEqual(report.rejections, [])

        # Schema validation rejects unknown trait
        bad_record = deepcopy(record)
        bad_record["combat_traits"] = ["alien"]
        bad_report = validate_character(bad_record)
        self.assertFalse(bad_report.is_valid)
        self.assertTrue(len(bad_report.rejections) > 0)

        # Semantic validator directly catches unknown combat trait
        semantic_issues = _check_combat_traits({"combat_traits": ["alien"]})
        self.assertTrue(any("unknown combat trait" in str(rej) for rej in semantic_issues))

        # Semantic validator directly catches duplicate trait
        dup_issues = _check_combat_traits({"combat_traits": ["undead", "undead"]})
        self.assertTrue(any("duplicate combat trait" in str(rej) for rej in dup_issues))

    def test_quest_compilation_and_scene_builder_carry_combat_traits(self):
        char_req = {
            "display_name": "亡靈祭司",
            "title": "無光者",
            "age": 40,
            "apparent_age": 40,
            "combat_traits": ["undead"],
        }
        compiled = _compile_characterization(char_req)
        self.assertIsNotNone(compiled)
        self.assertEqual(compiled.combat_traits, ("undead",))

        # Canonical dictionary serialization
        canonical = _npc_req_canonical(("caster", "low", "hostile"), compiled)
        self.assertEqual(canonical["combat_traits"], ["undead"])

        # Deserialization from payload
        payload = {
            "display_name": "亡靈祭司",
            "title": "無光者",
            "age": 40,
            "apparent_age": 40,
            "portrait_stable_key": None,
            "combat_traits": ["undead"],
        }
        deserialized = _characterization_from_payload(payload)
        self.assertEqual(deserialized.combat_traits, ("undead",))

        # Invalid trait raises QuestCompileError
        with self.assertRaises(QuestCompileError):
            _compile_characterization(dict(char_req, combat_traits=["invalid_trait"]))

    def test_wilderness_population_supports_combat_traits(self):
        pop = MonsterPopulation(tier="low", name_zh="腐爛行屍", combat_traits=("undead",))
        self.assertEqual(pop.combat_traits, ("undead",))

        # Test spawn helper assigns trait
        wilderness = create_object(NPC, key="wild_anchor")  # Mock wilderness script
        wilderness.db.itemcoordinates = {}
        wilderness.db.rooms = {}

        _spawn(wilderness, (10, 20), pop)
        spawned = list(wilderness.db.itemcoordinates.keys())[0]
        self.assertEqual(get_combat_traits(spawned), frozenset({"undead"}))

        # Test _matches_expected verifies combat_traits
        self.assertTrue(_matches_expected(spawned, pop))

        # Mismatched trait fails matching
        diff_pop = MonsterPopulation(tier="low", name_zh="腐爛行屍", combat_traits=())
        self.assertFalse(_matches_expected(spawned, diff_pop))
