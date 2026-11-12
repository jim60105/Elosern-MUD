"""Fixed-input golden decisions across monster tiers."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from world.rules import monster_behaviour as behaviour
from world.rules.combat import Battlefield
from world.rules.monster_behaviour import monster_behaviour_policy
from world.skills.registry import TargetSpec

from ._combat_session_helpers import open_synthetic_scope, synth_damage_skill
from .combat_fixtures import FakeEntity
from .test_monster_behaviour_policy import FakeMonster, _field

# File-local synthetic damage rows: one single-target strike and one area
# strike, so every authored strategy is observable without naming a shipped
# skill.
_T_SINGLE = synth_damage_skill("t_golden_single", "合成單擊")
_T_AREA = synth_damage_skill(
    "t_golden_sweep", "合成範圍擊", target_spec=TargetSpec.AREA
)
_SCOPE_EXTRA = {"skills": {_T_SINGLE.key: _T_SINGLE, _T_AREA.key: _T_AREA}}

#: Two synthetic archetypes differed only by their authored target metric, and
#: two synthetic tiers bind them: the shipped tier-to-archetype mapping is never
#: the thing under test.
_WEAKEST = "t_golden_weakest"
_STRONGEST = "t_golden_strongest"
_LOW_TIER = "t_golden_low"
_HIGH_TIER = "t_golden_high"


def _profile(*, target_strategy: str, skill_choice: str = "first_owned"):
    return {
        "target_strategy": target_strategy,
        "skill_choice": skill_choice,
        "prefer_area_when_multiple_enemies": False,
        "flee_hp_fraction": None,
        "decision_mode": "reflex",
        "utility_weights": {
            name: 1.0 for name in behaviour.UTILITY_WEIGHT_NAMES
        },
        **(
            {"reflex_temperature": 10.0}
            if skill_choice == "highest_expected_damage"
            else {}
        ),
    }


def _rulebook() -> dict:
    return {
        "tier_default_archetype": {
            _LOW_TIER: _WEAKEST,
            _HIGH_TIER: _STRONGEST,
        },
        "archetypes": {
            _WEAKEST: _profile(target_strategy="lowest_hp"),
            _STRONGEST: _profile(target_strategy="highest_effective_power"),
        },
        "variant_intelligence": {},
        "variant_decision_mode": {},
        "candidate_budget": 64,
    }


def _install(book: dict):
    """Load one synthetic rulebook's profiles and tuning exactly as startup does."""
    profiles = behaviour._load_behaviour_profiles(
        book, tiers={_LOW_TIER, _HIGH_TIER}
    )
    tuning = behaviour._load_ai_tuning(
        book, profiles=profiles, species={}, variants={}
    )
    patcher = patch.multiple(
        behaviour,
        MONSTER_BEHAVIOUR_YAML=book,
        BEHAVIOUR_PROFILES=profiles,
        MONSTER_AI_TUNING=tuning,
    )
    return profiles, tuning, patcher


class _FixedDraw:
    """The injectable selection generator: one exact uniform draw."""

    def __init__(self, draw: float):
        self.draw = draw

    def random(self) -> float:
        return self.draw


class MonsterBehaviourGoldenTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(
            self, "skills", "elements", extra=_SCOPE_EXTRA
        )
        self.profiles, self.tuning, patcher = _install(_rulebook())
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _monster(tier: str, *owned: str) -> FakeMonster:
        return FakeMonster(
            f"{tier}-monster",
            threat_tier=tier,
            combat_identity=f"{tier}-monster",
            owned=list(owned),
        )

    @staticmethod
    def _field_for(monster):
        weak = FakeEntity(
            "weak", combat_identity='weak', hp=10, max_hp=100, atk_phys=2,
            agility=2, defense=2, magic_power=2,
        )
        strong = FakeEntity(
            "strong", combat_identity='strong', hp=90, max_hp=200, atk_phys=40,
            agility=40, defense=40, magic_power=40,
        )
        return _field(monster, [weak, strong])

    def _decision(self, tier, *, rng=None):
        monster = self._monster(tier, _T_SINGLE.key, _T_AREA.key)
        request = monster_behaviour_policy(
            monster, self._field_for(monster), rng=rng
        )
        targets = request.targets
        if targets == "all-enemies":
            return request.skill_key, ("all-enemies",)
        return request.skill_key, tuple(target.key for target in targets)

    @covers_requirement("monster-action-policy::golden-fixed-seed-tests-demonstrate-distinct-reproducible-behaviour-across-monstertiers")
    def test_distinct_authored_metrics_choose_distinct_targets(self):
        # Each tier-default profile owns exactly one usable SINGLE kit, so the
        # authored target metric is the only thing that can move the decision.
        self.assertEqual(
            self._decision(_LOW_TIER), (_T_SINGLE.key, ("weak",))
        )
        self.assertEqual(
            self._decision(_HIGH_TIER), (_T_SINGLE.key, ("strong",))
        )

    @covers_requirement("monster-action-policy::golden-fixed-seed-tests-demonstrate-distinct-reproducible-behaviour-across-monstertiers")
    def test_identical_inputs_reproduce_every_decision(self):
        first = [self._decision(tier) for tier in (_LOW_TIER, _HIGH_TIER)]
        second = [self._decision(tier) for tier in (_LOW_TIER, _HIGH_TIER)]
        self.assertEqual(first, second)

    @covers_requirement("monster-action-policy::highest-expected-damage-comparison-uses-effective-value-and-one-tie-breaking-roll")
    def test_a_sampled_shape_replays_under_the_same_injected_draw(self):
        # The evaluating profile competes the SINGLE and AREA kits: the same
        # injected draw over identical state, tuning and owned order returns
        # the same skill and target shape, never a fresh random pick.
        book = _rulebook()
        book["archetypes"][_WEAKEST] = _profile(
            target_strategy="lowest_hp", skill_choice="highest_expected_damage"
        )
        _profiles, _tuning, nested = _install(book)
        nested.start()
        self.addCleanup(nested.stop)
        first = self._decision(_LOW_TIER, rng=_FixedDraw(0.5))
        replay = self._decision(_LOW_TIER, rng=_FixedDraw(0.5))
        self.assertEqual(first, replay)
        self.assertEqual(first, (_T_AREA.key, ("all-enemies",)))
