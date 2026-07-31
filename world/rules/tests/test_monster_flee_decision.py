"""Rulebook-backed monster flee-policy tests."""

from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import (
    BEHAVIOUR_PROFILES,
    MONSTER_BEHAVIOUR_YAML,
    MonsterBehaviourConfigError,
    _load_rulebook,
    _load_behaviour_profiles,
    monster_behaviour_policy,
    resolve_behaviour_profile,
)

from .combat_fixtures import FakeEntity, FakeGauge
from .test_monster_behaviour_policy import FakeMonster, _field


class MonsterFleeProfileTests(unittest.TestCase):
    def test_shipped_thresholds_and_tier_defaults_are_valid(self):
        self.assertEqual(
            {
                key: profile.flee_hp_fraction
                for key, profile in BEHAVIOUR_PROFILES.items()
            },
            {
                "instinctive": 0.35,
                "pack_hunter": 0.20,
                "brute": 0.10,
                "tactical_caster": 0.25,
                "apex_predator": None,
            },
        )
        for tier, key in MONSTER_BEHAVIOUR_YAML[
            "tier_default_archetype"
        ].items():
            monster = type(
                "MonsterFixture",
                (),
                {"threat_tier": tier, "behaviour_tree": None},
            )()
            self.assertIs(
                resolve_behaviour_profile(monster),
                BEHAVIOUR_PROFILES[key],
            )

    def test_invalid_profile_data_fails_before_profiles_are_constructed(self):
        invalid_cases = {
            "boolean_fraction": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].update(flee_hp_fraction=True),
            "string_fraction": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].update(flee_hp_fraction="0.35"),
            "below_range": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].update(flee_hp_fraction=-0.01),
            "above_range": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].update(flee_hp_fraction=1.01),
            "missing_field": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].pop("flee_hp_fraction"),
            "extra_field": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].update(extra=True),
            "unknown_default": lambda rulebook: rulebook[
                "tier_default_archetype"
            ].update(low="missing"),
            "unknown_strategy": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].update(target_strategy="missing"),
            "non_string_strategy": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].update(target_strategy=[]),
            "non_boolean_area": lambda rulebook: rulebook["archetypes"][
                "instinctive"
            ].update(prefer_area_when_multiple_enemies=1),
        }
        for name, mutate in invalid_cases.items():
            with self.subTest(name=name):
                rulebook = deepcopy(MONSTER_BEHAVIOUR_YAML)
                mutate(rulebook)
                with self.assertRaisesRegex(
                    MonsterBehaviourConfigError,
                    r"^invalid monster behaviour rulebook:",
                ):
                    _load_behaviour_profiles(rulebook)
        with self.assertRaisesRegex(
            MonsterBehaviourConfigError,
            r"^invalid monster behaviour rulebook:",
        ):
            _load_behaviour_profiles(
                {
                    "tier_default_archetype": {"low": "instinctive"},
                    "archetypes": [],
                }
            )

    def test_malformed_yaml_uses_the_stable_configuration_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "monster_behaviour.yaml"
            path.write_text("archetypes: [", encoding="utf-8")
            with self.assertRaisesRegex(
                MonsterBehaviourConfigError,
                r"^invalid monster behaviour rulebook:",
            ):
                _load_rulebook(path)

    def test_override_changes_threshold_without_mutating_monster_state(self):
        default = FakeMonster(
            "default",
            hp=30,
            max_hp=100,
            owned=["fire_ball"],
        )
        override = FakeMonster(
            "override",
            hp=30,
            max_hp=100,
            owned=["fire_ball"],
            behaviour_tree="brute",
        )
        enemy = FakeEntity("enemy")
        default_snapshot = (
            deepcopy(default.traits.hp._data),
            deepcopy(default.skills.values),
            default.behaviour_tree,
            default.threat_tier,
        )
        override_snapshot = (
            deepcopy(override.traits.hp._data),
            deepcopy(override.skills.values),
            override.behaviour_tree,
            override.threat_tier,
        )
        self.assertEqual(
            monster_behaviour_policy(default, _field(default, [enemy])).skill_key,
            FLEE_SKILL_KEY,
        )
        self.assertEqual(
            monster_behaviour_policy(override, _field(override, [enemy])).skill_key,
            "fire_ball",
        )
        self.assertEqual(
            (
                default.traits.hp._data,
                default.skills.values,
                default.behaviour_tree,
                default.threat_tier,
            ),
            default_snapshot,
        )
        self.assertEqual(
            (
                override.traits.hp._data,
                override.skills.values,
                override.behaviour_tree,
                override.threat_tier,
            ),
            override_snapshot,
        )


class MonsterFleePolicyTests(unittest.TestCase):
    @staticmethod
    def _request(
        *,
        hp=35,
        max_hp=100,
        threat_tier="low",
        behaviour_tree=None,
        owned=None,
    ):
        monster = FakeMonster(
            "monster",
            hp=hp,
            max_hp=max_hp,
            threat_tier=threat_tier,
            behaviour_tree=behaviour_tree,
            owned=["fire_ball"] if owned is None else owned,
        )
        enemy = FakeEntity("enemy")
        battlefield = _field(monster, [enemy])
        return monster, enemy, battlefield, monster_behaviour_policy(
            monster,
            battlefield,
        )

    def test_threshold_boundary_above_boundary_and_null_profile(self):
        _, _, _, boundary = self._request(hp=35)
        self.assertEqual(boundary.skill_key, FLEE_SKILL_KEY)
        _, _, _, above = self._request(hp=36)
        self.assertEqual(above.skill_key, "fire_ball")
        _, _, _, below = self._request(hp=34)
        self.assertEqual(below.skill_key, FLEE_SKILL_KEY)
        _, _, _, apex = self._request(hp=1, threat_tier="calamity")
        self.assertEqual(apex.skill_key, "fire_ball")

    def test_non_positive_maximum_does_not_divide_or_choose_flee(self):
        monster, _, _, _ = self._request(hp=1)
        monster.traits.hp = FakeGauge(0, 1)
        monster.traits.hp._data["base"] = 0
        enemy = FakeEntity("enemy")
        request = monster_behaviour_policy(monster, _field(monster, [enemy]))
        self.assertEqual(request.skill_key, "fire_ball")

    def test_flee_precedes_skill_selection_and_consumes_no_policy_roll(self):
        monster = FakeMonster("monster", hp=20, max_hp=100, owned=["flight"])
        enemies = [FakeEntity("first"), FakeEntity("second")]
        battlefield = _field(monster, enemies)
        with patch("world.rules.monster_behaviour.dice.roll_d100") as roller:
            request = monster_behaviour_policy(monster, battlefield)
        self.assertEqual(request.skill_key, FLEE_SKILL_KEY)
        roller.assert_not_called()

    def test_no_living_enemy_returns_none_before_flee(self):
        monster = FakeMonster("monster", hp=20, max_hp=100, owned=[])
        enemy = FakeEntity("enemy")
        battlefield = _field(monster, [enemy])
        battlefield.fled.add(enemy.key)
        self.assertIsNone(monster_behaviour_policy(monster, battlefield))

    def test_request_shape_and_policy_purity(self):
        monster, _, battlefield, request = self._request(hp=35)
        monster.traits.hp._data["last_regen_at"] = 123
        monster.sexual_state = {"arousal": "平靜"}
        monster.buffs_state = {"poison": {"stacks": 1}}
        monster.skill_grants = ["grant"]
        monster.inventory = ["potion"]
        monster.currency = 12
        snapshot = (
            deepcopy(monster.traits.hp._data),
            deepcopy(monster.skills.values),
            list(monster.skills.owned_keys()),
            deepcopy(battlefield.fled),
            deepcopy(monster.sexual_state),
            deepcopy(monster.buffs_state),
            list(monster.skill_grants),
            list(monster.inventory),
            monster.currency,
        )
        request = monster_behaviour_policy(monster, battlefield)
        self.assertEqual(request.actor, monster)
        self.assertEqual(request.skill_key, FLEE_SKILL_KEY)
        self.assertEqual(request.targets, [monster])
        self.assertIs(request.context.battlefield, battlefield)
        self.assertIs(request.context.event_context["battlefield"], battlefield)
        self.assertEqual(
            (
                monster.traits.hp._data,
                monster.skills.values,
                monster.skills.owned_keys(),
                battlefield.fled,
                monster.sexual_state,
                monster.buffs_state,
                monster.skill_grants,
                monster.inventory,
                monster.currency,
            ),
            snapshot,
        )

    def test_all_tier_defaults_and_override_have_reproducible_decisions(self):
        cases = {
            "low": (35, FLEE_SKILL_KEY),
            "mid": (20, FLEE_SKILL_KEY),
            "high": (10, FLEE_SKILL_KEY),
            "calamity": (1, "fire_ball"),
        }
        for tier, (hp, expected_skill) in cases.items():
            with self.subTest(tier=tier):
                first = self._request(hp=hp, threat_tier=tier)[3]
                second = self._request(hp=hp, threat_tier=tier)[3]
                self.assertEqual(first.skill_key, expected_skill)
                self.assertEqual(first.skill_key, second.skill_key)
        override = self._request(
            hp=20,
            threat_tier="high",
            behaviour_tree="tactical_caster",
        )[3]
        self.assertEqual(override.skill_key, FLEE_SKILL_KEY)

    def test_source_preserves_deterministic_single_writer_boundary(self):
        source = (
            Path(__file__).parents[1] / "monster_behaviour.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "world.ai",
            "import random",
            "from random",
            "requests.",
            "httpx.",
            "urllib.",
            "ActionResolver.resolve(",
            ".fled.add(",
            "0.35",
            "0.20",
            "0.10",
            "0.25",
        ):
            self.assertNotIn(forbidden, source)

    def test_fresh_import_loads_flee_registration(self):
        script = "\n".join(
            (
                "import django",
                "django.setup()",
                "import evennia",
                "evennia._init()",
                "import world.rules.monster_behaviour",
                "from world.rules.action import _EFFECT_HANDLERS",
                "from world.rules.action import _step1_ownership",
                "from world.rules.disengage import FLEE_SKILL_KEY",
                "from world.rules.monster_behaviour import monster_behaviour_policy",
                "from world.rules.tests.combat_fixtures import FakeEntity",
                "from world.rules.tests.test_monster_behaviour_policy import FakeMonster, _field",
                "from world.skills.registry import SKILL_REGISTRY",
                "assert FLEE_SKILL_KEY in SKILL_REGISTRY",
                "assert 'disengage' in _EFFECT_HANDLERS",
                "monster = FakeMonster('monster', hp=20, max_hp=100, owned=[FLEE_SKILL_KEY])",
                "request = monster_behaviour_policy(monster, _field(monster, [FakeEntity('enemy')]))",
                "assert _step1_ownership(request).key == FLEE_SKILL_KEY",
            )
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            cwd=Path(__file__).parents[3],
            env={
                **os.environ,
                "DJANGO_SETTINGS_MODULE": "server.conf.settings",
            },
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
