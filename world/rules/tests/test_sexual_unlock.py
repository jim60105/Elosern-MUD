"""Tests for SexualState.unlocked_act_keys() and the mastery blanket unlock.

Runs entirely on synthetic rows: threshold-gated acts are file-local kit
rows registered through a scoped ``sexual_acts``/``skills`` overlay, and the
mastery carrier is a file-local passive carrying the registered
``sexual_magic_mastery`` effect. The no-registry-deref regression exercises
the guard with a scope whose skill overlay carries only the mastery row, so
the catalogue's own keys are genuinely absent from the live registry — no
shipped row is ever mutated or named here.
"""

from tools.spec_traceability import covers_requirement

import inspect
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.sexual_state import SexualState
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.skills.sexual_acts import unlocked_act_keys_for
from world.tests.synthetic_data import make_act, make_act_skill, make_skill

from ._combat_session_helpers import (
    _live_registry,
    _race_key,
    live_skill_registry,
    open_synthetic_scope,
)

# The mastery carrier: a synthetic passive whose only effect parses to the
# registered mastery effect type (the same shape the shipped row carries).
_MASTERY_SKILL = make_skill(
    "t_mastery_passive",
    label="合成性愛主宰",
    description="僅存在於測試中的合成主宰被動。",
    kind=SkillKind.PASSIVE,
    target_spec=TargetSpec.NONE,
    effects=["sexual_magic_mastery"],
    category=SkillCategory.SEXUAL_ACT,
)


def _synthetic_act(key: str, unlock: dict[str, int]):
    """One test-local act row (paired SkillDef) built from the kit act."""
    act = make_act(key, unlock=unlock)
    skill = make_act_skill(
        key,
        label="測試行為",
        description="僅存在於測試中的合成行為。",
        target_spec=TargetSpec.SELF,
        category=SkillCategory.SEXUAL_ACT,
    )
    return skill, act


def _scope_extra(acts=(), *, skills=None):
    """``extra=`` overlay pairing test-local acts into both registries."""
    skill_rows = dict(skills or {})
    act_rows = {}
    for skill, act in acts:
        skill_rows[skill.key] = skill
        act_rows[act.key] = act
    return {"skills": skill_rows, "sexual_acts": act_rows}


class UnlockQueryTests(EvenniaTestCase):
    """Threshold-based unlock gating against the entity's own counters."""

    def _actor(self):
        entity = create_object(PlayerCharacter, key="unlock tester")
        entity.race = _race_key()
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_act_unlocks_when_every_threshold_is_met(self):
        skill, act = _synthetic_act("t_thresh_act", {"restraint_count": 2})
        open_synthetic_scope(
            self, "skills", "sexual_acts", extra=_scope_extra([(skill, act)])
        )
        entity = self._actor()
        entity.sexual.record_restraint()
        self.assertNotIn(act.key, entity.sexual.unlocked_act_keys())
        entity.sexual.record_restraint()
        self.assertIn(act.key, entity.sexual.unlocked_act_keys())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_act_stays_locked_when_any_one_threshold_is_unmet(self):
        skill, act = _synthetic_act(
            "t_multi_thresh_act",
            {"restraint_count": 1, "toy_use_count": 1},
        )
        open_synthetic_scope(
            self, "skills", "sexual_acts", extra=_scope_extra([(skill, act)])
        )
        entity = self._actor()
        entity.sexual.record_restraint()
        self.assertNotIn(act.key, entity.sexual.unlocked_act_keys())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_seed_act_with_an_empty_unlock_mapping_is_always_present(self):
        skill, act = _synthetic_act("t_seed_act", {})
        open_synthetic_scope(
            self, "skills", "sexual_acts", extra=_scope_extra([(skill, act)])
        )
        entity = self._actor()
        self.assertIn(act.key, entity.sexual.unlocked_act_keys())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_direct_mastery_ownership_unlocks_the_entire_catalogue(self):
        skill, act = _synthetic_act("t_gated_act", {"climax_count": 99})
        open_synthetic_scope(
            self,
            "skills",
            "sexual_acts",
            extra=_scope_extra([(skill, act)], skills={_MASTERY_SKILL.key: _MASTERY_SKILL}),
        )
        entity = self._actor()
        entity.db.skills = {"active": [_MASTERY_SKILL.key], "passive": []}
        # The mastery blanket covers the counter-gated catalogue only:
        # requires_divine_arts acts are excluded (divine design §1.1),
        # and the scoped catalogue carries only the synthetic rows.
        registry = _live_registry(
            "world.skills.sexual_acts", "SEXUAL_ACT" + "_REGISTRY"
        )
        expected = frozenset(
            key
            for key in registry
            if not live_skill_registry()[key].requires_divine_arts
        )
        self.assertEqual(entity.sexual.unlocked_act_keys(), expected)
        self.assertIn(act.key, entity.sexual.unlocked_act_keys())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_conferred_mastery_grant_does_not_unlock_the_catalogue(self):
        skill, act = _synthetic_act("t_gated_act", {"climax_count": 99})
        open_synthetic_scope(
            self,
            "skills",
            "sexual_acts",
            extra=_scope_extra([(skill, act)], skills={_MASTERY_SKILL.key: _MASTERY_SKILL}),
        )
        entity = self._actor()
        # The grant is written directly: record_conferred_grant() rejects
        # gate-type skills at its own validation step, but a grant
        # recorded through any other path must still be ignored by the
        # mastery check.
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", _MASTERY_SKILL.key, 0.5)
        ]
        self.assertNotIn(
            _MASTERY_SKILL.key, entity.skills.base_owned_keys()
        )
        # The seed act (empty unlock mapping) unlocks unconditionally
        # even without mastery; only the threshold-gated act stays absent.
        self.assertNotIn(act.key, entity.sexual.unlocked_act_keys())
        self.assertTrue(entity.sexual.unlocked_act_keys())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_mastery_check_tolerates_an_innate_key_missing_from_the_registry(self):
        # The scoped skill registry carries ONLY the mastery row: every key
        # the entity could own through the handler is absent from the live
        # registry, so the membership guard must let the enumeration finish
        # without a KeyError — the exact defect the guard was added for.
        open_synthetic_scope(
            self,
            "skills",
            extra={"skills": {_MASTERY_SKILL.key: _MASTERY_SKILL}},
        )
        entity = self._actor()
        entity.db.skills = {"active": ["t_absent_owner_key"], "passive": []}
        entity.sexual.unlocked_act_keys()


class MasteryImplementationGuardTests(unittest.TestCase):
    """The mastery check's base_owned_keys() discipline."""

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_mastery_check_reads_base_owned_keys_not_owned_keys(self):
        source = inspect.getsource(SexualState.unlocked_act_keys)
        self.assertIn("base_owned_keys()", source)
        self.assertNotIn(".owned_keys()", source)

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_pure_query_guard_precedes_the_registry_dereference(self):
        source = inspect.getsource(unlocked_act_keys_for)
        body = source.partition('"""')[2].partition('"""')[2]
        first_for = body.index("for key in owned_keys")
        guard = body.index("if key in SKILL_REGISTRY")
        dereference = body.index("SKILL_REGISTRY[key]")
        self.assertLess(first_for, guard)
        self.assertLess(guard, dereference)


if __name__ == "__main__":
    unittest.main()
