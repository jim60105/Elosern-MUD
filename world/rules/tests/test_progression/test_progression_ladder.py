"""Slice of ``test_progression``: ProgressionTests.
"""
import inspect
import unittest
from dataclasses import replace
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _EVENT_EFFECT_PLANNERS,
    _commit,
)
from world.rules.action_preview import preview_skill
from world.rules.buffs import grant_conferred_growth_rate
from world.rules.combat import Battlefield, BattlefieldActionContext, run_round
from world.rules.progression import (
    AFFINITY_ELEMENT_MULTIPLIER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    PRACTICE_XP_PER_STUDY_HOUR,
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    element_affinity_multiplier,
    grant_skill_practice_xp,
    skill_proficiency_level,
)
from world.rules.targeting import RoomActionContext
import world.rules.progression as progression
from world.tests.synthetic_data import (
    SYNTH_GLOWMIRE_ELEMENT,
    SYNTH_RACES,
    SYNTH_SKILLS,
    make_race,
    make_skill,
)
from ..combat_fixtures import grant_lineage
from .._combat_session_helpers import (
    _behaviour_archetype_key,
    _monster_tier_key,
    _race_key,
    SYNTH_GLOW_ELEMENT,
    live_skill_registry,
    SYNTH_SEAM_AREA_SKILL,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
    synth_lineage_tree,
    synth_lineage_tree_magic,
    _live_registry,
)
from world.skills.registry import (
    SkillCategory,
    SkillKind,
    validate_prerequisite_graph,
)
# Cross-lineage wiring: importing the rulebook module at collection time also
# forces its shipped-table load against the LIVE registry, before any
# synthetic scope clears it (the shared helpers' eager import is the same
# guarantee for sibling modules in other shard processes).
import world.rules.cross_lineage_unlock as cross_lineage


from ._support import (
    SWIFT_LEARNER,
    _T_DRILL,
    _T_FIRE_SPELL,
    _T_GALE,
    _T_GLOW_SPELL,
    _T_GROWTH_DUP,
    _T_GROWTH_FIRE,
    _T_GROWTH_FIRE2,
    _T_PLAIN_DRILL,
    _character,
    _monster,
    _scoped_setup,
)


class ProgressionTests(EvenniaTestCase):
    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        # The dedupe triple is keyed by pk; EvenniaTestCase rollbacks reuse
        # pks across tests, so a claim from a previous test (or a rolled-back
        # commit) must not suppress this test's accrual.
        progression.reset_practice_dedupe()

    def _character(self, key: str, race: str | None = None) -> PlayerCharacter:
        return _character(self, key, race)

    def _monster(self, key: str) -> Monster:
        return _monster(self, key)

    def test_growth_rate_conferral_rejects_invalid_scales(self):
        entity = self._character("invalid-scale")
        for scale in (-1, float("nan"), float("inf"), True):
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    grant_conferred_growth_rate(entity, "source", scale)
        self.assertFalse(entity.buffs.all)

    @covers_requirement(
        "skill-lineage::successful-active-resolution-accruses-lineage-practice-xp",
        "skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick",
    )
    def test_skill_practice_is_scaled_by_race_and_growth(self):
        # Use-driven lineage: one grant per call, race learning AND the
        # conferred growth buff both participate; magic_power never moves.
        # The race factor is read from the synthetic race row this file
        # authored, never from a shipped race identifier.
        entity = self._character("practitioner", SWIFT_LEARNER.key)
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        before = entity.traits.magic_power.value
        self.assertTrue(grant_skill_practice_xp(entity, _T_DRILL.key))
        self.assertEqual(
            entity.db.skill_proficiency[_T_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE
            * SWIFT_LEARNER.learning_multiplier
            * 0.5,
        )
        # The magic-XP engine is retired: practice is the only growth writer
        # and the static magic_power trait never moves (delta scenario
        # "Granting skill practice XP does not affect magic_power").
        self.assertEqual(entity.traits.magic_power.value, before)
        self.assertEqual(skill_proficiency_level(entity, _T_DRILL.key), 0)
        # Same (actor, skill, target) in one tick dedupes to a single accrual.
        self.assertFalse(grant_skill_practice_xp(entity, _T_DRILL.key))
        self.assertEqual(
            entity.db.skill_proficiency[_T_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE
            * SWIFT_LEARNER.learning_multiplier
            * 0.5,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_owned_scoped_growth_accelerates_only_its_own_tree(self):
        # The owned growth passive accelerates the spell of its scoped element
        # and leaves a spell of another element at the neutral factor (the
        # delta's "accelerates only its own tree" scenario). Both spells are
        # cast by the same entity in one tick; the dedupe triple differs by
        # skill key, so both accruals land.
        entity = self._character("growth-scope", SWIFT_LEARNER.key)
        entity.db.skills = {"active": [], "passive": [_T_GROWTH_FIRE.key]}
        self.assertTrue(grant_skill_practice_xp(entity, _T_FIRE_SPELL.key))
        self.assertTrue(grant_skill_practice_xp(entity, _T_GLOW_SPELL.key))
        base = SKILL_PRACTICE_XP_PER_USE * SWIFT_LEARNER.learning_multiplier
        self.assertEqual(
            entity.db.skill_proficiency[_T_FIRE_SPELL.key],
            base
            * element_affinity_multiplier(entity, _T_FIRE_SPELL.element.key)
            * 5.0,
        )
        self.assertEqual(
            entity.db.skill_proficiency[_T_GLOW_SPELL.key],
            base
            * element_affinity_multiplier(entity, _T_GLOW_SPELL.element.key),
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_owned_scoped_growth_leaves_non_elemental_practice_alone(self):
        # A skill declaring no element takes the neutral owned-skill factor
        # even when the actor owns a scoped growth passive (delta scenario).
        entity = self._character("growth-plain", SWIFT_LEARNER.key)
        entity.db.skills = {"active": [], "passive": [_T_GROWTH_FIRE.key]}
        self.assertTrue(grant_skill_practice_xp(entity, _T_PLAIN_DRILL.key))
        self.assertEqual(
            entity.db.skill_proficiency[_T_PLAIN_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE * SWIFT_LEARNER.learning_multiplier,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_owned_and_conferred_growth_compose_multiplicatively(self):
        # The owned-skill factor and the conferred-buff factor are independent
        # and multiply (delta scenario).
        entity = self._character("growth-compose", SWIFT_LEARNER.key)
        entity.db.skills = {"active": [], "passive": [_T_GROWTH_FIRE.key]}
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        self.assertTrue(grant_skill_practice_xp(entity, _T_FIRE_SPELL.key))
        self.assertEqual(
            entity.db.skill_proficiency[_T_FIRE_SPELL.key],
            SKILL_PRACTICE_XP_PER_USE
            * SWIFT_LEARNER.learning_multiplier
            * element_affinity_multiplier(entity, _T_FIRE_SPELL.element.key)
            * 0.5
            * 5.0,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_duplicate_scoped_growth_raises_only_for_the_queried_scope(self):
        # One skill declaring two growth_rate effects for the same scope
        # raises when that scope is practised (mirroring _matching_multiplier);
        # a spell of another element is unaffected by the duplicate pair.
        entity = self._character("growth-dup", SWIFT_LEARNER.key)
        entity.db.skills = {"active": [], "passive": [_T_GROWTH_DUP.key]}
        with self.assertRaises(ValueError):
            grant_skill_practice_xp(entity, _T_FIRE_SPELL.key)
        self.assertTrue(grant_skill_practice_xp(entity, _T_GLOW_SPELL.key))
        self.assertEqual(
            entity.db.skill_proficiency[_T_GLOW_SPELL.key],
            SKILL_PRACTICE_XP_PER_USE
            * SWIFT_LEARNER.learning_multiplier
            * element_affinity_multiplier(entity, _T_GLOW_SPELL.element.key),
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_separate_owned_growth_skills_multiply(self):
        # The duplicate guard is per skill: two distinct owned growth passives
        # of the same scope multiply across skills (5 x 7).
        entity = self._character("growth-multi", SWIFT_LEARNER.key)
        entity.db.skills = {
            "active": [],
            "passive": [_T_GROWTH_FIRE.key, _T_GROWTH_FIRE2.key],
        }
        self.assertTrue(grant_skill_practice_xp(entity, _T_FIRE_SPELL.key))
        self.assertEqual(
            entity.db.skill_proficiency[_T_FIRE_SPELL.key],
            SKILL_PRACTICE_XP_PER_USE
            * SWIFT_LEARNER.learning_multiplier
            * element_affinity_multiplier(entity, _T_FIRE_SPELL.element.key)
            * 5.0
            * 7.0,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_booked_study_inherits_the_owned_scoped_growth_factor(self):
        # The booked-hourly settlement scales by the same composite as the
        # per-use grant (one formula, two entry points).
        entity = self._character("growth-study", SWIFT_LEARNER.key)
        entity.db.skills = {"active": [], "passive": [_T_GROWTH_FIRE.key]}
        self.assertTrue(
            progression.grant_study_practice_xp(entity, _T_FIRE_SPELL.key, hours=1)
        )
        self.assertEqual(
            entity.db.skill_proficiency[_T_FIRE_SPELL.key],
            PRACTICE_XP_PER_STUDY_HOUR
            * SWIFT_LEARNER.learning_multiplier
            * 5.0,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_proficiency_query_is_pure(self):
        entity = self._character("query")
        entity.db.skill_proficiency = {
            _T_DRILL.key: 3 * SKILL_PROFICIENCY_XP_PER_LEVEL + 1
        }
        before = dict(entity.db.skill_proficiency)
        self.assertEqual(skill_proficiency_level(entity, _T_DRILL.key), 3)
        self.assertEqual(skill_proficiency_level(entity, "never_practiced"), 0)
        self.assertEqual(entity.db.skill_proficiency, before)

    def test_action_commit_restores_progression_attributes_on_failure(self):
        entity = self._character("atomic")
        effects = [
            PendingEffect(
                entity,
                "practice",
                frozenset({"progression"}),
                lambda: grant_skill_practice_xp(entity, _T_DRILL.key),
            ),
            PendingEffect(
                entity,
                "failure",
                frozenset({"progression"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects, char="tester", action="test_skill")
        self.assertIsNone(entity.db.skill_proficiency)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_successful_combat_action_awards_practice_once(self):
        actor = self._character("fighter")
        actor.db.skills = {"active": [_T_DRILL.key], "passive": []}
        monster = self._monster("goblin")
        monster.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"fighter"}), "foes": frozenset({"goblin"})},
            {"fighter": actor, "goblin": monster},
        )
        request = ActionRequest(
            actor,
            _T_DRILL.key,
            [monster],
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            logs = run_round(
                battlefield,
                lambda entity, _: request if entity is actor else None,
            )
        self.assertTrue(logs)
        self.assertEqual(
            actor.db.skill_proficiency[_T_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE,
        )

    def test_area_shorthand_defeats_each_newly_living_monster_once(self):
        actor = self._character("area-fighter")
        actor.db.skills = {"active": [_T_GALE.key], "passive": []}
        first, second, corpse = (
            self._monster("first"),
            self._monster("second"),
            self._monster("corpse"),
        )
        first.traits.hp.current = second.traits.hp.current = 1
        corpse.traits.hp.current = 0
        battlefield = Battlefield(
            {
                "party": frozenset({"area-fighter"}),
                "foes": frozenset({"first", "second", "corpse"}),
            },
            {
                "area-fighter": actor,
                "first": first,
                "second": second,
                "corpse": corpse,
            },
        )
        request = ActionRequest(
            actor,
            _T_GALE.key,
            "all-enemies",
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            logs = run_round(
                battlefield,
                lambda entity, _: request if entity is actor else None,
            )
        kinds = [
            entry.kind for log in logs for entry in log.entries
        ]
        self.assertEqual(kinds.count("target_defeated"), 2)
        self.assertIsNone(actor.db.magic_xp)
        # Use-driven accrual is per distinct hit target: the two newly
        # living monsters each claim one grant; the dead corpse claims none.
        self.assertEqual(
            actor.db.skill_proficiency[_T_GALE.key],
            2 * SKILL_PRACTICE_XP_PER_USE,
        )

    def test_duplicate_area_targets_reject_before_resolution(self):
        actor = self._character("duplicate-fighter")
        actor.db.skills = {"active": [_T_GALE.key], "passive": []}
        monster = self._monster("duplicate-goblin")
        monster.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"duplicate-fighter"}), "foes": frozenset({"duplicate-goblin"})},
            {"duplicate-fighter": actor, "duplicate-goblin": monster},
        )
        request = ActionRequest(
            actor,
            _T_GALE.key,
            [monster, monster],
            BattlefieldActionContext(battlefield),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.TARGET_SPEC_MISMATCH)
        self.assertIsNone(actor.db.skill_proficiency)
        self.assertEqual(monster.traits.hp.current, 1)

    def test_non_monster_defeat_awards_practice_only(self):
        actor = self._character("player-fighter")
        actor.db.skills = {"active": [_T_DRILL.key], "passive": []}
        target = self._character("tiered-player")
        target.threat_tier = _monster_tier_key()
        target.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"player-fighter"}), "foes": frozenset({"tiered-player"})},
            {"player-fighter": actor, "tiered-player": target},
        )
        request = ActionRequest(
            actor,
            _T_DRILL.key,
            [target],
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            run_round(
                battlefield,
                lambda entity, _: request if entity is actor else None,
            )
        # Defeat carries no progression award any more; the single growth
        # writer is the practice grant for the resolved skill itself.
        self.assertEqual(
            actor.db.skill_proficiency[_T_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE,
        )
        self.assertIsNone(actor.db.magic_xp)


    def test_divine_arts_remain_outside_progression_scope(self):
        self.assertFalse(
            any("divine" in name for name in vars(progression))
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_magic_xp_engine_is_absent_from_progression_source(self):
        """skill-proficiency delta: no magic-XP writer may remain."""
        source = inspect.getsource(progression)
        for token in (
            "magic_xp",
            "accrue_magic_study",
            "grant_combat_kill_xp",
            "effective_growth_multiplier",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)
