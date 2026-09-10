"""Integration tests for skill ownership and effective trait values."""

from tools.spec_traceability import covers_requirement

import ast
import inspect

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.rules.traits import STATIC_KEYS
from world.skills import handler
from world.skills.effects import StatMultiplyEffect
from world.skills.handler import _matching_multiplier
from world.tests.synthetic_data import SYNTH_ACTS, make_skill, synthetic_registries

# Synthetic multiplier fixtures: the handler's arithmetic reads the skill's
# own parsed effects, so invented rows exercise the identical resolution.
_T_STOIC = make_skill("t_stoic_guard", effects=["stat_multiply:atk_phys:100"])
_T_TITAN = make_skill("t_titan_ward", effects=["stat_multiply:atk_phys:1000"])
_T_ASH_WARD = make_skill("t_ash_ward", effects=["stat_multiply:defense:2"])

# A fresh entity owns only the unconditionally-unlocked synthetic acts;
# counter-gated catalogue rows stay absent until their thresholds are met.
# The innate pair is read from the handler's own ordering constant so the
# expectation tracks the production contract without naming its rows.
def _fresh_entity_owned_keys():
    seed_acts = sorted(key for key, act in SYNTH_ACTS.items() if not act.unlock)
    return [*handler.INNATE_SKILL_ORDER, *seed_acts]


@synthetic_registries(
    "skills",
    "races",
    "subraces",
    "static_tiers",
    "elements",
    "items",
    "sexual_acts",
    extra={
        "skills": {
            skill.key: skill for skill in (_T_STOIC, _T_TITAN, _T_ASH_WARD)
        }
    },
)
class SkillHandlerTests(EvenniaTestCase):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="skill tester")
        entity.race = "t_duskmari"
        entity.subrace = "t_duskmari_evensong"
        entity.apply_race_baseline()
        return entity

    @covers_requirement("skill-handler::skillhandler-is-mounted-directly-as-entity-skills")
    def test_handler_reads_private_storage_and_has_no_bare_assignment(self):
        entity = self._entity()
        entity.db.skills = None
        self.assertEqual(
            entity.skills.owned_keys(),
            _fresh_entity_owned_keys(),
        )
        with self.assertRaises(AttributeError):
            entity.skills = {"active": [], "passive": []}

        entity.db.skills = {
            "active": [_T_TITAN.key],
            "passive": [_T_ASH_WARD.key],
        }
        self.assertEqual(
            entity.skills.owned_keys(),
            [_T_TITAN.key, _T_ASH_WARD.key, *_fresh_entity_owned_keys()],
        )

    @covers_requirement("universal-action-ownership::innate-ownership-is-unconditional-and-not-combat-gated")
    def test_flee_is_innate_for_bare_monster_and_not_combat_gated(self):
        monster = create_object(Monster, key="bare monster")
        monster.db.skills = None
        before = monster.skills.owned_keys()
        monster.db.current_battlefield = object()
        after = monster.skills.owned_keys()
        self.assertEqual(before, _fresh_entity_owned_keys())
        self.assertEqual(after, before)

    @covers_requirement("universal-action-ownership::world-skills-does-not-depend-on-world-rules-to-define-innate-ownership")
    def test_skill_handler_has_no_rules_dependency(self):
        source = inspect.getsource(handler)
        self.assertNotIn("world.rules", source)

    @covers_requirement("skill-handler::effective-value-is-the-sole-resolution-time-multiplier-application-point-and-never-writes-to-entity-traits")
    def test_effective_value_multiplies_without_mutating_base(self):
        entity = self._entity()
        entity.db.skills = {
            "active": [_T_TITAN.key],
            "passive": [],
        }
        before = entity.traits.atk_phys.value
        self.assertEqual(
            entity.skills.effective_value("atk_phys"),
            before * _T_TITAN.parsed_effects[0].multiplier,
        )
        self.assertEqual(entity.traits.atk_phys.value, before)

        entity.db.skills = {"active": [_T_ASH_WARD.key], "passive": []}
        self.assertEqual(entity.skills.effective_value("atk_phys"), before)

    @covers_requirement("skill-registry::body-enhancement-family-is-passive-not-active")
    def test_passive_ownership_still_applies_the_multiplier(self):
        entity = self._entity()
        entity.db.skills = {
            "active": [],
            "passive": [_T_TITAN.key],
        }
        before = entity.traits.atk_phys.value
        self.assertEqual(
            entity.skills.effective_value("atk_phys"),
            before * _T_TITAN.parsed_effects[0].multiplier,
        )

    def test_duplicate_owned_key_is_resolution_idempotent(self):
        entity = self._entity()
        entity.db.skills = {
            "active": [_T_STOIC.key, _T_STOIC.key],
            "passive": [],
        }
        base = entity.traits.atk_phys.value
        self.assertEqual(
            entity.skills.effective_value("atk_phys"),
            base * _T_STOIC.parsed_effects[0].multiplier,
        )

    def test_effective_value_never_moves_static_bases_out_of_race_bands(self):
        entity = self._entity()
        entity.db.skills = {
            "active": [_T_STOIC.key, _T_TITAN.key, _T_ASH_WARD.key],
            "passive": [],
        }
        for _ in range(3):
            for key in STATIC_KEYS:
                entity.skills.effective_value(key)
        from world.tests import synthetic_data

        synthetic_races = synthetic_data.SYNTH_RACES
        race = synthetic_races["t_duskmari"]
        for key in STATIC_KEYS:
            lower, upper = getattr(race.static_baseline, key)
            self.assertLessEqual(lower, getattr(entity.traits, key).base)
            self.assertLessEqual(getattr(entity.traits, key).base, upper)

    def test_matching_multiplier_reads_typed_effects(self):
        skill = _T_STOIC
        self.assertEqual(
            _matching_multiplier(skill.parsed_effects, "atk_phys"),
            100.0,
        )
        self.assertIsNone(_matching_multiplier(skill.parsed_effects, "magic_power"))
        self.assertIsNone(_matching_multiplier((), "atk_phys"))
        duplicate = (
            StatMultiplyEffect(trait="atk_phys", multiplier=2.0),
            StatMultiplyEffect(trait="atk_phys", multiplier=3.0),
        )
        with self.assertRaises(ValueError):
            _matching_multiplier(duplicate, "atk_phys")

    def test_handler_source_never_assigns_to_traits(self):
        tree = ast.parse(inspect.getsource(handler))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                self.assertNotIn(".traits", ast.unparse(target))
