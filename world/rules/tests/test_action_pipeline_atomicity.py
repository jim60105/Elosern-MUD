"""Integration tests for staged action commit and rollback."""

from copy import deepcopy

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _commit,
    _stored_trait_value,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.progression import practice_claims_for
from world.rules.tests.combat_fixtures import grant_lineage
from world.skills.effects import EffectPolicy
import importlib

_skills_mod = importlib.import_module("world.skills.registry")
_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")
from world.tests.synthetic_data import make_skill
from unittest.mock import patch


class ActionPipelineAtomicityTests(EvenniaTestCase):
    def test_failed_second_effect_restores_first(self):
        entity = create_object(PlayerCharacter, key="atomic")
        entity.race = "human"
        entity.apply_race_baseline()
        raw_before = deepcopy(dict(entity.traits.trait_data))
        before = entity.traits.atk_phys.value
        effects = [
            PendingEffect(
                entity,
                "first",
                frozenset({"traits"}),
                lambda: setattr(entity.traits.atk_phys, "value", before + 10),
            ),
            PendingEffect(
                entity,
                "second",
                frozenset({"traits"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(CommitFailed) as caught:
            _commit(effects, char="tester", action="test_skill")
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(entity.traits.atk_phys.value, before)
        self.assertEqual(dict(entity.traits.trait_data), raw_before)

    def test_failed_effect_restores_resource_and_attribute_absence(self):
        entity = create_object(PlayerCharacter, key="resource-atomic")
        entity.race = "human"
        entity.apply_race_baseline()
        before = _stored_trait_value(entity.traits.mp)
        self.assertFalse(entity.attributes.has("sexual_traits", category="traits"))
        effects = [
            PendingEffect(
                entity,
                "resource",
                frozenset({"traits"}),
                lambda: setattr(entity.traits.mp, "current", before - 10),
            ),
            PendingEffect(
                entity,
                "sexual failure",
                frozenset({"sexual"}),
                lambda: (
                    setattr(entity.sexual.pleasure, "base", 2),
                    (_ for _ in ()).throw(RuntimeError("injected")),
                ),
            ),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects, char="tester", action="test_skill")
        self.assertEqual(_stored_trait_value(entity.traits.mp), before)
        self.assertFalse(entity.attributes.has("sexual_traits", category="traits"))
        self.assertEqual(entity.sexual.arousal.value, 0)

    @covers_requirement(
        "skill-effect-model::dependent-effects-retain-normal-settlement-and-rollback"
    )
    def test_miss_skips_rider_pays_costs_and_claims_practice(self):
        """Scenario: A miss skips dependent transfer while paying costs and awarding practice."""
        actor = create_object(PlayerCharacter, key="atomic_actor")
        target = create_object(PlayerCharacter, key="atomic_target")
        for char in (actor, target):
            char.race = "human"
            char.apply_race_baseline()
            char.traits.hp.current = 100
            char.traits.mp.current = 100
        actor.traits.atk_phys.base = 50
        actor.traits.agility.base = 20
        target.traits.defense.base = 10
        target.traits.agility.base = 10

        skill = make_skill(
            "t_atomic_dep_skill",
            cost={"mp": 10},
            effects=["damage:fire:physical", "gauge_transfer:mp:drain:fixed:5"],
            effect_policies=(EffectPolicy(), EffectPolicy(requires_hit_from=0)),
        )
        grant_lineage(actor, [skill.key])
        bf = Battlefield(
            roster={"atomic_actor": actor, "atomic_target": target},
            teams={"team_a": {"atomic_actor"}, "team_b": {"atomic_target"}},
        )
        ctx = BattlefieldActionContext(bf)
        req = ActionRequest(actor, skill.key, [target], ctx)

        # Roll=1 -> MISS
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            with patch.dict(_SKILL_MAP, {skill.key: skill}):
                res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        # Rider was skipped
        self.assertFalse(any(e.kind == "gauge_transfer" for e in res.event_log.entries))
        # Target took no damage and lost no MP
        self.assertEqual(target.traits.hp.current, 100)
        self.assertEqual(target.traits.mp.current, 100)
        # Cost was paid: actor lost 10 MP (100 -> 90)
        self.assertEqual(actor.traits.mp.current, 90)
        # Practice was claimed
        self.assertTrue(len(practice_claims_for(actor, skill.key)) > 0)

    @covers_requirement(
        "skill-effect-model::dependent-effects-retain-normal-settlement-and-rollback"
    )
    def test_late_failure_restores_all_gauges_and_releases_same_tick_practice(self):
        """Scenario: Late failure restores actor/target gauges and releases practice claims."""
        actor = create_object(PlayerCharacter, key="fail_actor")
        target = create_object(PlayerCharacter, key="fail_target")
        for char in (actor, target):
            char.race = "human"
            char.apply_race_baseline()
            char.traits.hp.current = 100
            char.traits.mp.current = 100
        actor.traits.atk_phys.base = 50
        actor.traits.agility.base = 20
        target.traits.defense.base = 10
        target.traits.agility.base = 10

        skill = make_skill(
            "t_fail_dep_skill",
            cost={"mp": 10},
            effects=["damage:fire:physical", "gauge_transfer:mp:drain:fixed:5"],
            effect_policies=(EffectPolicy(), EffectPolicy(requires_hit_from=0)),
        )
        grant_lineage(actor, [skill.key])
        bf = Battlefield(
            roster={"fail_actor": actor, "fail_target": target},
            teams={"team_a": {"fail_actor"}, "team_b": {"fail_target"}},
        )
        ctx = BattlefieldActionContext(bf)
        req = ActionRequest(actor, skill.key, [target], ctx)

        # Simulate a crash in _commit
        with patch("world.rules.action.resolver._commit", side_effect=RuntimeError("injected late failure")):
            with patch("world.rules.combat.damage.roll_d100", return_value=80):
                with patch.dict(_SKILL_MAP, {skill.key: skill}):
                    with self.assertRaises(RuntimeError):
                        ActionResolver.resolve(req)

        # Actor & Target gauges restored to 100
        self.assertEqual(actor.traits.mp.current, 100)
        self.assertEqual(actor.traits.hp.current, 100)
        self.assertEqual(target.traits.mp.current, 100)
        self.assertEqual(target.traits.hp.current, 100)
        # Same-tick practice claim released!
        self.assertEqual(len(practice_claims_for(actor, skill.key)), 0)
