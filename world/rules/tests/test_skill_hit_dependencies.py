"""Synthetic test suite for hit-dependent skill effects (OpenSpec change skill-hit-dependent-effects)."""

from unittest.mock import patch
from dataclasses import replace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from tools.spec_traceability import covers_requirement
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    DamageHitEvidence,
    PendingEffect,
    RejectReason,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.tests.combat_fixtures import FakeEntity, grant_lineage
from world.tests.synthetic_data import (
    make_skill,
    make_monster_species,
    make_monster_variant,
    synthetic_registries,
)
from world.lore.monster_species import MonsterCombatProfile
from world.rules.monster_individual import construct_species_individual
from world.skills.effects import (
    DamageEffect,
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    GaugeTransferPolicy,
)
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillEligibility,
    SkillKind,
    TargetSpec,
)


class SkillHitDependenciesTests(EvenniaTestCase):
    """Test hit-dependent effect resolution, routing, isolation, and reuse."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="hit_actor")
        self.target_a = create_object(PlayerCharacter, key="hit_target_a")
        self.target_b = create_object(PlayerCharacter, key="hit_target_b")
        for char in (self.actor, self.target_a, self.target_b):
            char.race = "human"
            char.apply_race_baseline()
            char.traits.hp.current = 100
            char.traits.mp.current = 100
        self.actor.traits.atk_phys.base = 50
        self.actor.traits.agility.base = 20
        self.target_a.traits.agility.base = 10
        self.target_b.traits.agility.base = 10
        self.target_a.traits.defense.base = 10
        self.target_b.traits.defense.base = 10
        self.battlefield = Battlefield(
            roster={
                "hit_actor": self.actor,
                "hit_target_a": self.target_a,
                "hit_target_b": self.target_b,
            },
            teams={"team_a": {"hit_actor"}, "team_b": {"hit_target_a", "hit_target_b"}},
        )
        self.context = BattlefieldActionContext(self.battlefield)

    def _make_skill(
        self,
        key: str,
        effects: list[str],
        policies: tuple[EffectPolicy, ...],
        target_spec: TargetSpec = TargetSpec.AREA,
    ) -> SkillDef:
        synth_key = key if key.startswith("t_") else f"t_{key}"
        skill = make_skill(
            synth_key,
            target_spec=target_spec,
            effects=effects,
            effect_policies=policies,
        )
        grant_lineage(self.actor, [skill.key])
        return skill

    @covers_requirement(
        "skill-effect-model::damage-provides-trusted-invocation-local-typed-hit-outcomes"
    )
    def test_per_target_isolation_with_duplicate_display_names(self):
        """Scenario: Identity is not display text; targets with same key/label isolate hit qualifications."""
        foe1 = create_object(PlayerCharacter, key="goblin_1")
        foe2 = create_object(PlayerCharacter, key="goblin_2")
        for f in (foe1, foe2):
            f.race = "human"
            f.apply_race_baseline()
            f.traits.hp.current = 100
            f.traits.mp.current = 100
            f.traits.defense.base = 0
            f.traits.agility.base = 10
            f.db.display_name = "哥布林"
        bf = Battlefield(
            roster={"goblin_1": foe1, "goblin_2": foe2, "hit_actor": self.actor},
            teams={"team_a": {"hit_actor"}, "team_b": {"goblin_1", "goblin_2"}},
        )
        ctx = BattlefieldActionContext(bf)

        # Skill: 0: damage, 1: dependent drain rider
        skill = self._make_skill(
            "dup_name_test",
            effects=["damage:fire:physical", "gauge_transfer:mp:drain:fixed:5"],
            policies=(
                EffectPolicy(),
                EffectPolicy(requires_hit_from=0),
            ),
        )
        req = ActionRequest(self.actor, skill.key, [foe1, foe2], ctx)

        # Roll returns hit for foe1 (roll 50 -> hit), miss for foe2 (roll 1 -> miss)
        # damage._to_hit calls roll_d100 twice: first for foe1, second for foe2
        with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 1]):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        # Check event log entries or pending effects: foe1 got damage + drain, foe2 got miss and NO drain
        drain_entries = [
            e for e in res.event_log.entries if e.kind == "gauge_transfer"
        ]
        self.assertEqual(len(drain_entries), 1)
        # Verify drain target was foe1, not foe2
        self.assertEqual(drain_entries[0].target, str(foe1.key))

    @covers_requirement(
        "skill-effect-model::damage-provides-trusted-invocation-local-typed-hit-outcomes"
    )
    def test_single_strike_hit_and_miss_vectors_no_extra_roll(self):
        """Scenario: Exactly source hit roll occurs; hit delivers rider, miss skips it, no extra roll."""
        skill = self._make_skill(
            "single_strike_vec",
            effects=["damage:fire:physical", "gauge_transfer:mp:drain:fixed:5"],
            policies=(
                EffectPolicy(),
                EffectPolicy(requires_hit_from=0),
            ),
            target_spec=TargetSpec.SINGLE,
        )
        req = ActionRequest(self.actor, skill.key, [self.target_a], self.context)

        # 1. Hit vector
        with patch("world.rules.combat.damage.roll_d100", return_value=80) as mock_roll:
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res_hit = ActionResolver.resolve(req)
        self.assertEqual(mock_roll.call_count, 1)
        self.assertEqual(res_hit.outcome, "success")
        self.assertTrue(any(e.kind == "gauge_transfer" for e in res_hit.event_log.entries))

        # 2. Miss vector
        with patch("world.rules.combat.damage.roll_d100", return_value=1) as mock_roll_miss:
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res_miss = ActionResolver.resolve(req)
        self.assertEqual(mock_roll_miss.call_count, 1)
        self.assertEqual(res_miss.outcome, "success")
        self.assertFalse(any(e.kind == "gauge_transfer" for e in res_miss.event_log.entries))

    @covers_requirement(
        "skill-effect-model::dependent-recipients-intersect-ordinary-audiences-with-source-hits"
    )
    def test_multi_strike_all_hit_miss_vectors_any_hit_once_per_target(self):
        """Scenario: Multi-strike any-hit: 2 strikes -> (hit, hit), (hit, miss), (miss, hit), (miss, miss). Rider executes once per target on any hit."""
        # 2-strike damage policy
        policy_dmg = DamagePolicy(extra_strikes=1)
        skill = self._make_skill(
            "multistrike_vec",
            effects=["damage:fire:physical", "gauge_transfer:mp:drain:fixed:5"],
            policies=(
                EffectPolicy(damage=policy_dmg),
                EffectPolicy(requires_hit_from=0),
            ),
            target_spec=TargetSpec.SINGLE,
        )
        req = ActionRequest(self.actor, skill.key, [self.target_a], self.context)

        vectors = [
            ([80, 80], 1, "both hit"),
            ([80, 1], 1, "first hit second miss"),
            ([1, 80], 1, "first miss second hit"),
            ([1, 1], 0, "both miss"),
        ]

        for rolls, expected_drains, desc in vectors:
            with self.subTest(desc=desc):
                self.target_a.traits.hp.current = 100
                with patch("world.rules.combat.damage.roll_d100", side_effect=rolls):
                    with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                        res = ActionResolver.resolve(req)
                if res.outcome != "success":
                    print(f"FAILED {desc}: {res.reason} {res.detail}")
                self.assertEqual(res.outcome, "success")
                drains = [e for e in res.event_log.entries if e.kind == "gauge_transfer"]
                self.assertEqual(len(drains), expected_drains)

    @covers_requirement(
        "skill-effect-model::effect-hit-dependencies-reference-earlier-damage-occurrences"
    )
    def test_source_occurrence_independence_repeated_damage_ids(self):
        """Scenario: Two identical damage occurrences; rider referring to second occurrence only checks second."""
        skill = self._make_skill(
            "repeated_occ_indep",
            effects=[
                "damage:fire:physical",
                "damage:fire:physical",
                "gauge_transfer:mp:drain:fixed:5",
            ],
            policies=(
                EffectPolicy(),
                EffectPolicy(),
                EffectPolicy(requires_hit_from=1),  # depends on second damage occurrence (index 1)
            ),
            target_spec=TargetSpec.SINGLE,
        )
        req = ActionRequest(self.actor, skill.key, [self.target_a], self.context)

        # Case A: occurrence 0 hits, occurrence 1 misses -> rider (dep on 1) must be skipped!
        self.target_a.traits.hp.current = 100
        with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 1]):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res_a = ActionResolver.resolve(req)
        self.assertEqual(res_a.outcome, "success")
        self.assertFalse(any(e.kind == "gauge_transfer" for e in res_a.event_log.entries))

        # Case B: occurrence 0 misses, occurrence 1 hits -> rider (dep on 1) must execute!
        self.target_a.traits.hp.current = 100
        with patch("world.rules.combat.damage.roll_d100", side_effect=[1, 80]):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res_b = ActionResolver.resolve(req)
        self.assertEqual(res_b.outcome, "success")
        self.assertTrue(any(e.kind == "gauge_transfer" for e in res_b.event_log.entries))

    @covers_requirement(
        "skill-effect-model::dependent-recipients-intersect-ordinary-audiences-with-source-hits"
    )
    def test_reuse_by_already_supported_target_status_effect(self):
        """Scenario: A target buff/status effect depends on damage hit; reuses contract without species branch."""
        self.target_a.traits.hp.current = 100
        skill = self._make_skill(
            "status_dep_reuse",
            effects=["damage:fire:physical", "buff_apply:paralysis"],
            policies=(
                EffectPolicy(),
                EffectPolicy(requires_hit_from=0),
            ),
            target_spec=TargetSpec.SINGLE,
        )
        req = ActionRequest(self.actor, skill.key, [self.target_a], self.context)

        # On hit: buff is applied
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res_hit = ActionResolver.resolve(req)
        self.assertEqual(res_hit.outcome, "success")
        self.assertTrue(any(e.kind == "buff_applied" and e.data.get("buff_key") == "paralysis" for e in res_hit.event_log.entries))

        # On miss: buff is skipped
        self.target_a.traits.hp.current = 100
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res_miss = ActionResolver.resolve(req)
        self.assertEqual(res_miss.outcome, "success")
        self.assertFalse(any(e.kind == "buff_applied" and e.data.get("buff_key") == "paralysis" for e in res_miss.event_log.entries))

    @covers_requirement(
        "skill-effect-model::dependent-recipients-intersect-ordinary-audiences-with-source-hits"
    )
    def test_audience_never_expands_self_or_allies_absent_from_hit_set(self):
        """Scenario: Rider audience cannot add entities absent from damage hit set (e.g. self/allies)."""
        # Skill damages ENEMIES, rider declares ALLIES audience but requires hit from 0
        skill = self._make_skill(
            "audience_no_expand",
            effects=["damage:fire:physical", "buff_apply:focus"],
            policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(audience=EffectAudience.ALLIES, requires_hit_from=0),
            ),
            target_spec=TargetSpec.AREA,
        )
        req = ActionRequest(self.actor, skill.key, [self.target_a], self.context)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        # Ally/self never received buff because damage only hit enemy (target_a)
        self.assertFalse(any(e.kind == "buff_applied" and e.data.get("buff_key") == "focus" for e in res.event_log.entries))

    @covers_requirement(
        "skill-effect-model::dependent-effects-retain-normal-settlement-and-rollback",
        "monster-resource-abilities::successful-bite-drains-mp-and-recovers-only-actual-removal",
        "monster-resource-abilities::affordability-precedes-effects-and-recovery-precedes-costs",
    )
    def test_synthetic_transfer_partial_zero_mp_and_caster_cap(self):
        """Scenario: Target partial/zero MP and caster full/partial cap."""
        skill = self._make_skill(
            "synth_bite_mechanics",
            effects=["damage:water:physical", "gauge_transfer:mp:drain:fixed:10"],
            policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    requires_hit_from=0,
                    transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
                ),
            ),
            target_spec=TargetSpec.SINGLE,
        )
        skill = replace(skill, cost={"mp": 10, "sp": 5})
        req = ActionRequest(self.actor, skill.key, [self.target_a], self.context)

        # 1. Target with 3 MP: removal is at most 3, actor recovers at most 3
        self.target_a.traits.mp.current = 3
        self.actor.traits.mp.current = 20
        self.actor.traits.sp.current = 20
        self.actor.traits.sp.base = 100
        self.actor.traits.mp.base = 100
        self.target_a.traits.mp.base = 100
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertEqual(self.target_a.traits.mp.current, 0)
        # Actor recovers 3 -> 23, pays 10 -> ends at 13 MP, SP: 20 -> 15
        self.assertEqual(self.actor.traits.mp.current, 13)
        self.assertEqual(self.actor.traits.sp.current, 15)

        # 2. Target with 0 MP: deals damage, 0 drain, actor recovers 0, pays costs
        self.target_a.traits.mp.current = 0
        self.actor.traits.mp.current = 20
        self.actor.traits.sp.current = 20
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertEqual(self.target_a.traits.mp.current, 0)
        # Actor recovers 0 -> pays 10 MP -> 10 MP, SP: 20 -> 15
        self.assertEqual(self.actor.traits.mp.current, 10)
        self.assertEqual(self.actor.traits.sp.current, 15)

        # 3. Full cap: starting at max 100 MP, removes 10 MP -> recovery clamps to 100, pays 10 -> 90 MP
        self.target_a.traits.mp.current = 20
        self.actor.traits.mp.current = 100
        self.actor.traits.sp.current = 20
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertEqual(self.actor.traits.mp.current, 90)
        self.assertEqual(self.actor.traits.sp.current, 15)

        # 4. Starting at 20 MP, removes 10 -> recovers to 30 -> pays 10 -> ends at 20 MP
        self.target_a.traits.hp.current = 100
        self.target_a.traits.mp.current = 20
        self.actor.traits.mp.current = 20
        self.actor.traits.sp.current = 20
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual((res.outcome, getattr(res, "reason", None), getattr(res, "detail", None)), ("success", None, None))
        self.assertEqual(self.actor.traits.mp.current, 20)
        self.assertEqual(self.actor.traits.sp.current, 15)

        # 5. Miss: pays both costs, transfers nothing
        self.target_a.traits.hp.current = 100
        self.target_a.traits.mp.current = 20
        self.actor.traits.mp.current = 20
        self.actor.traits.sp.current = 20
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertEqual(self.target_a.traits.mp.current, 20)
        self.assertEqual(self.actor.traits.mp.current, 10)
        self.assertEqual(self.actor.traits.sp.current, 15)

        # 6. Insufficient MP or SP: rejected before rolls or effects
        self.actor.traits.mp.current = 9
        self.actor.traits.sp.current = 20
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
            res_fail_mp = ActionResolver.resolve(req)
        self.assertEqual(res_fail_mp.outcome, "rejected")

        self.actor.traits.mp.current = 20
        self.actor.traits.sp.current = 4
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
            res_fail_sp = ActionResolver.resolve(req)
        self.assertEqual(res_fail_sp.outcome, "rejected")

    @covers_requirement(
        "skill-effect-model::dependent-recipients-intersect-ordinary-audiences-with-source-hits",
        "monster-resource-abilities::successful-bite-drains-mp-and-recovers-only-actual-removal",
    )
    def test_critical_defeat_crossing(self):
        """Critical hit does not multiply drain; defeat crossing still transfers."""
        skill = self._make_skill(
            "synth_second_species_skill",
            effects=["damage:water:physical", "gauge_transfer:mp:drain:fixed:10"],
            policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    requires_hit_from=0,
                    transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
                ),
            ),
            target_spec=TargetSpec.SINGLE,
        )
        skill = replace(skill, cost={"mp": 10, "sp": 5})
        req = ActionRequest(self.actor, skill.key, [self.target_a], self.context)

        # Critical hit: drain remains fixed at 10 (not multiplied)
        self.target_a.traits.hp.current = 100
        self.target_a.traits.mp.current = 50
        self.actor.traits.mp.current = 20
        self.actor.traits.sp.current = 20
        # roll 100 -> critical hit
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        # target lost exactly 10 MP
        self.assertEqual(self.target_a.traits.mp.current, 40)
        drain_entry = next(e for e in res.event_log.entries if e.kind == "gauge_transfer")
        self.assertEqual(drain_entry.data.get("amount"), 10)

        # Defeat-crossing hit: target has 1 HP, damage reduces to 0, transfer still executes
        self.target_a.traits.hp.current = 1
        self.target_a.traits.mp.current = 20
        self.actor.traits.mp.current = 20
        self.actor.traits.sp.current = 20
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertLessEqual(self.target_a.traits.hp.current, 0)
        self.assertEqual(self.target_a.traits.mp.current, 10)
        self.assertEqual(self.actor.traits.mp.current, 20)

    @covers_requirement(
        "skill-effect-model::dependent-recipients-intersect-ordinary-audiences-with-source-hits",
        "monster-resource-abilities::successful-bite-drains-mp-and-recovers-only-actual-removal",
        "test-data-independence::shared-synthetic-mechanism-coverage-owns-independently-known-outcomes",
    )
    def test_two_species_execute_shared_drain_with_isolated_hit_state(self):
        """Detect species-specific execution and hit evidence leaking by DB identity."""
        species_keys = ("t_drain_species_a", "t_drain_species_b")
        skill = make_skill(
            "t_shared_species_drain",
            target_spec=TargetSpec.AREA,
            cost={"mp": 10, "sp": 5},
            eligibility=SkillEligibility(
                allowed_actor_kinds=("monster",), allowed_species=species_keys,
            ),
            effects=["damage:water:physical", "gauge_transfer:mp:drain:fixed:10"],
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    requires_hit_from=0,
                    transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
                ),
            ),
        )
        species = {}
        variants = {}
        for index, species_key in enumerate(species_keys):
            variant_key = f"t_drain_variant_{index}"
            species[species_key] = make_monster_species(
                species_key, default_variant_key=variant_key,
            )
            variants[variant_key] = make_monster_variant(
                variant_key,
                species_key=species_key,
                combat_profile=MonsterCombatProfile(
                    hp=100, mp=100, sp=100, atk_phys=10,
                    agility=20, defense=0, magic_power=0,
                ),
                active_skill_keys=(skill.key,),
            )
        with synthetic_registries(
            "monster_species", "monster_variants", "monster_tiers",
            extra={"monster_species": species, "monster_variants": variants},
        ), patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
            actors = [
                construct_species_individual(key, species[key].default_variant_key)
                for key in species_keys
            ]
            self.assertNotEqual(actors[0].pk, actors[1].pk)
            self.assertNotEqual(self.target_a.pk, self.target_b.pk)
            for index, actor in enumerate(actors):
                actor.traits.mp.current = 20
                actor.traits.sp.current = 20
                self.target_a.traits.mp.current = 3
                self.target_b.traits.mp.current = 3
                context = BattlefieldActionContext(Battlefield(
                    roster={
                        str(actor.key): actor,
                        "hit_target_a": self.target_a,
                        "hit_target_b": self.target_b,
                    },
                    teams={
                        "actors": {str(actor.key)},
                        "foes": {"hit_target_a", "hit_target_b"},
                    },
                ))
                # Swap hit/miss in the next invocation, so stale evidence fails.
                rolls = [80, 1] if index == 0 else [1, 80]
                with patch("world.rules.combat.damage.roll_d100", side_effect=rolls):
                    result = ActionResolver.resolve(ActionRequest(
                        actor, skill.key, [self.target_a, self.target_b], context,
                    ))
                self.assertEqual(result.outcome, "success")
                self.assertEqual(actor.traits.mp.current, 13)
                self.assertEqual(actor.traits.sp.current, 15)
                self.assertEqual(
                    (self.target_a.traits.mp.current, self.target_b.traits.mp.current),
                    (0, 3) if index == 0 else (3, 0),
                )
