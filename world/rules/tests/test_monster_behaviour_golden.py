"""Fixed-input golden decisions across monster tiers."""

from tools.spec_traceability import covers_requirement

import random
import unittest

from world.rules.monster_behaviour import monster_behaviour_policy

from .combat_fixtures import FakeEntity
from .test_monster_behaviour_policy import FakeMonster, _field


class MonsterBehaviourGoldenTests(unittest.TestCase):
    @staticmethod
    def _decision(tier):
        monster = FakeMonster(
            f"{tier}-monster",
            threat_tier=tier,
            owned=["shadow_slash"],
        )
        weak = FakeEntity("weak", hp=10, max_hp=100, atk_phys=2)
        strong = FakeEntity("strong", hp=90, atk_phys=40)
        request = monster_behaviour_policy(
            monster,
            _field(monster, [weak, strong]),
        )
        return request.skill_key, tuple(target.key for target in request.targets)

    @covers_requirement("monster-action-policy::golden-fixed-seed-tests-demonstrate-distinct-reproducible-behaviour-across-monstertiers")
    def test_low_and_calamity_choose_distinct_reproducible_targets(self):
        random.seed(730)
        tiers = ("low", "mid", "high", "calamity")
        first = [self._decision(tier) for tier in tiers]
        random.seed(730)
        second = [self._decision(tier) for tier in tiers]
        self.assertEqual(first, second)
        self.assertEqual(first, [
            ("shadow_slash", ("weak",)),
            ("shadow_slash", ("weak",)),
            ("shadow_slash", ("strong",)),
            ("shadow_slash", ("strong",)),
        ])
