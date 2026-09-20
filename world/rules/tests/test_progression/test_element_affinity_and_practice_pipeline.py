"""Slice of ``test_progression``: ElementAffinityProgressionTests, PracticePipelineIntegrationTests.
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
    _MAGIC_CASTER,
    _scoped_setup,
)


class ElementAffinityProgressionTests(EvenniaTestCase):
    """element-affinity: multiplicative per-element multiplier (pure read)."""

    def setUp(self):
        _scoped_setup(self)
        super().setUp()

    def _caster(
        self,
        key: str,
        magic_power: int,
        race: str | None = None,
        affinity: tuple[str, ...] | None = None,
    ) -> PlayerCharacter:
        entity = create_object(PlayerCharacter, key=key)
        entity.race = _race_key() if race is None else race
        entity.apply_race_baseline()
        entity.traits.magic_power.base = magic_power
        entity.db.skills = {"active": [], "passive": []}
        if affinity is not None:
            entity.db.affinity_elements = list(affinity)
        return entity

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_neutral_default_returns_exactly_one_point_zero(self):
        entity = self._caster("neutral", 50)
        # Runtime-probed element keys: the multiplier is closed over the
        # element vocabulary, which rows are exercised is a data choice.
        element_keys = list(_live_registry("world.lore.elements", "ELEMENT_REGISTRY"))
        self.assertEqual(element_affinity_multiplier(entity, element_keys[0]), 1.0)
        self.assertEqual(
            AFFINITY_ELEMENT_MULTIPLIER, 1.1
        )
        self.assertEqual(
            NON_AFFINITY_ELEMENT_MULTIPLIER, 0.9
        )

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_favored_and_non_favored_elements_return_the_yaml_constants(self):
        element_keys = list(_live_registry("world.lore.elements", "ELEMENT_REGISTRY"))
        # Scoped element vocabulary: the kit carries the invented row plus
        # the borrowed row -- favoured is one, non-favoured the other.
        self.assertGreaterEqual(len(element_keys), 2)
        entity = self._caster("violet", 50, affinity=(element_keys[0],))
        self.assertEqual(
            element_affinity_multiplier(entity, element_keys[0]),
            AFFINITY_ELEMENT_MULTIPLIER,
        )
        self.assertEqual(
            element_affinity_multiplier(entity, element_keys[1]),
            NON_AFFINITY_ELEMENT_MULTIPLIER,
        )

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_unknown_element_key_fails_closed_and_writes_nothing(self):
        entity = self._caster("unknown-element", 50)
        with self.assertRaises(ValueError):
            element_affinity_multiplier(entity, "t_not_an_element")
        self.assertIsNone(entity.db.affinity_elements)


class PracticePipelineIntegrationTests(EvenniaTestCase):
    """End-to-end resolve(): accrual, simulated marker, AOE per-target, release."""

    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        progression.reset_practice_dedupe()
        # One fixed tick for the whole test: dedupe behaviour must come from
        # claims, never from the clock silently rolling.
        tick = patch.object(progression, "_current_tick", lambda: 5)
        tick.start()
        self.addCleanup(tick.stop)
        self.actor = create_object(PlayerCharacter, key="pipeline caster")
        self.actor.race = _race_key()
        self.actor.apply_race_baseline()
        self.actor.traits.magic_power.base = 30
        grant_lineage(
            self.actor,
            ["t_tree_root", _MAGIC_CASTER, SYNTH_SEAM_AREA_SKILL.key],
        )

    def _monsters(self, count):
        monsters = []
        for index in range(count):
            monster = create_object(Monster, key=f"pipeline wolf {index}")
            monster.threat_tier = _monster_tier_key()
            monster.behaviour_tree = _behaviour_archetype_key()
            monster.apply_monster_tier("floor")
            monster.traits.hp.base = 200
            monster.traits.hp.current = 200
            monsters.append(monster)
        return monsters

    def _request(self, skill, targets, context):
        return ActionRequest(self.actor, skill, targets, context)

    def _field(self, monsters, **event_context):
        field = Battlefield(
            {
                "party": frozenset({"pipeline caster"}),
                "foes": frozenset(monster.key for monster in monsters),
            },
            {"pipeline caster": self.actor}
            | {monster.key: monster for monster in monsters},
        )
        return BattlefieldActionContext(field, event_context=dict(event_context))

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_simulated_marker_suppresses_every_accrual(self):
        monster = self._monsters(1)[0]
        context = self._field([monster], simulated=True)
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_MAGIC_CASTER, [monster], context)
            )
        self.assertEqual(result.outcome, "success")
        self.assertLess(monster.traits.hp.current, 200)
        # A real, committed cast that grants nothing.
        self.assertNotIn(
            _MAGIC_CASTER, dict(self.actor.db.skill_proficiency or {})
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_area_hit_accrues_once_per_distinct_target(self):
        monsters = self._monsters(3)
        context = self._field(monsters)
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request("t_glitter_cascade", "all-enemies", context)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency["t_glitter_cascade"],
            3 * SKILL_PRACTICE_XP_PER_USE,
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_rolled_back_commit_releases_claims_so_retry_accrues(self):
        monster = self._monsters(1)[0]
        context = self._field([monster])
        request = self._request(_MAGIC_CASTER, [monster], context)
        before = dict(self.actor.db.skill_proficiency)
        real = dict(_EVENT_EFFECT_PLANNERS)

        def poison(_request, _log):
            # Runs after the staged practice batch; its failure forces the
            # snapshot/restore rollback the release path must undo.
            return [
                PendingEffect(
                    self.actor,
                    "poisoned commit",
                    frozenset({"progression"}),
                    lambda: (_ for _ in ()).throw(RuntimeError("injected")),
                )
            ]

        _EVENT_EFFECT_PLANNERS["test-poison"] = poison
        try:
            with patch("world.rules.combat.damage.roll_d100", return_value=100):
                first = ActionResolver.resolve(request)
        finally:
            _EVENT_EFFECT_PLANNERS.clear()
            _EVENT_EFFECT_PLANNERS.update(real)
        self.assertNotEqual(first.outcome, "success")
        self.assertEqual(dict(self.actor.db.skill_proficiency), before)
        self.assertEqual(
            progression.practice_claims_for(self.actor, _MAGIC_CASTER), set()
        )
        # The legitimate same-tick retry accrues normally.
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            retry = ActionResolver.resolve(request)
        self.assertEqual(retry.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency[_MAGIC_CASTER],
            SKILL_PRACTICE_XP_PER_USE,
        )
        # And the same (actor, skill, target) is then deduped for the tick.
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            again = ActionResolver.resolve(request)
        self.assertEqual(again.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency[_MAGIC_CASTER],
            SKILL_PRACTICE_XP_PER_USE,
        )
