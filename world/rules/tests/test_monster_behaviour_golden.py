"""Fixed-input golden decisions across monster tiers."""

from tools.spec_traceability import covers_requirement

import random
import unittest

from world.rules.combat import Battlefield
from world.rules.monster_behaviour import (
    BEHAVIOUR_PROFILES,
    MONSTER_BEHAVIOUR_YAML,
    monster_behaviour_policy,
)
from world.skills.registry import TargetSpec

from ._combat_session_helpers import open_synthetic_scope, synth_damage_skill
from .combat_fixtures import FakeEntity
from .test_monster_behaviour_policy import FakeMonster, _field

# File-local synthetic damage rows: one single-target strike and one area
# strike, so every archetype branch (target strategy + area preference) is
# observable without naming a shipped skill.
_T_SINGLE = synth_damage_skill("t_golden_single", "合成單擊")
_T_AREA = synth_damage_skill(
    "t_golden_sweep", "合成範圍擊", target_spec=TargetSpec.AREA
)
_SCOPE_EXTRA = {"skills": {_T_SINGLE.key: _T_SINGLE, _T_AREA.key: _T_AREA}}


class MonsterBehaviourGoldenTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_SCOPE_EXTRA)

    @staticmethod
    def _monster(tier):
        return FakeMonster(
            f"{tier}-monster",
            threat_tier=tier,
            owned=[_T_SINGLE.key, _T_AREA.key],
        )

    @staticmethod
    def _field_for(monster):
        weak = FakeEntity("weak", hp=10, max_hp=100, atk_phys=2)
        strong = FakeEntity("strong", hp=90, atk_phys=40)
        return _field(monster, [weak, strong])

    def _decision(self, tier):
        monster = self._monster(tier)
        request = monster_behaviour_policy(monster, self._field_for(monster))
        targets = request.targets
        if targets == "all-enemies":
            return request.skill_key, ("all-enemies",)
        return request.skill_key, tuple(target.key for target in targets)

    @staticmethod
    def _expected(tier):
        """The archetype mechanics the shipped tier-default table names."""
        profile = BEHAVIOUR_PROFILES[
            MONSTER_BEHAVIOUR_YAML["tier_default_archetype"][tier]
        ]
        if profile.prefer_area_when_multiple_enemies:
            return _T_AREA.key, ("all-enemies",)
        weakest, strongest = "weak", "strong"
        target = weakest if profile.target_strategy == "lowest_hp" else strongest
        return _T_SINGLE.key, (target,)

    @covers_requirement("monster-action-policy::golden-fixed-seed-tests-demonstrate-distinct-reproducible-behaviour-across-monstertiers")
    def test_tier_default_decisions_replay_and_follow_archetype_mechanics(self):
        tiers = sorted(MONSTER_BEHAVIOUR_YAML["tier_default_archetype"])
        self.assertTrue(tiers)
        random.seed(730)
        first = [self._decision(tier) for tier in tiers]
        random.seed(730)
        second = [self._decision(tier) for tier in tiers]
        self.assertEqual(first, second)
        for tier, decision in zip(tiers, first):
            with self.subTest(tier=tier):
                self.assertEqual(decision, self._expected(tier))
