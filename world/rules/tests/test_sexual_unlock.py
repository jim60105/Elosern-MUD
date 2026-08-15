"""Tests for SexualState.unlocked_act_keys() and the mastery blanket unlock.

This module deliberately never imports ``world.rules.disengage``: the
regression test at the bottom exists precisely because ``flee`` registers
into ``SKILL_REGISTRY`` only as that module's import side effect, and the
membership guard in ``_has_sexual_mastery()`` must hold even when it has not
run.
"""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.sexual_state import SexualState
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY, unlocked_act_keys_for
from world.skills.sexual_acts._builder import _act_family

_MISSING = object()


def _synthetic_act(key: str, unlock: dict[str, int], *, events=("stimulus_applied",)):
    """Build one test-local act row without touching any line module."""
    (skill, act), = _act_family(
        "獨處線",
        (
            key,
            "測試行為",
            "僅存在於測試中的合成行為。",
            TargetSpec.SELF,
            unlock,
            10,
            "私處",
            None,
            0.5,
            (),
            (),
            events,
            True,
        ),
    )
    return skill, act


class UnlockQueryTests(EvenniaTest):
    """Threshold-based unlock gating against the entity's own counters."""

    def _entity(self):
        entity = create_object(PlayerCharacter, key="unlock tester")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_act_unlocks_when_every_threshold_is_met(self):
        entity = self._entity()
        skill, act = _synthetic_act("thresh_act", {"restraint_count": 2})
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            entity.sexual.record_restraint()
            self.assertNotIn(act.key, entity.sexual.unlocked_act_keys())
            entity.sexual.record_restraint()
            self.assertIn(act.key, entity.sexual.unlocked_act_keys())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_act_stays_locked_when_any_one_threshold_is_unmet(self):
        entity = self._entity()
        skill, act = _synthetic_act(
            "multi_thresh_act",
            {"restraint_count": 1, "toy_use_count": 1},
        )
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            entity.sexual.record_restraint()
            self.assertNotIn(act.key, entity.sexual.unlocked_act_keys())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_seed_act_with_an_empty_unlock_mapping_is_always_present(self):
        entity = self._entity()
        skill, act = _synthetic_act("seed_act", {})
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            self.assertIn(act.key, entity.sexual.unlocked_act_keys())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_direct_mastery_ownership_unlocks_the_entire_catalogue(self):
        entity = self._entity()
        skill, act = _synthetic_act("gated_act", {"climax_count": 99})
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            entity.db.skills = {"active": ["divine_sexual_mastery"], "passive": []}
            self.assertEqual(
                entity.sexual.unlocked_act_keys(),
                frozenset(SEXUAL_ACT_REGISTRY),
            )

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_conferred_mastery_grant_does_not_unlock_the_catalogue(self):
        entity = self._entity()
        skill, act = _synthetic_act("gated_act", {"climax_count": 99})
        # The grant is written directly: record_conferred_grant() rejects
        # gate-type skills (divine_sexual_mastery) at its own validation
        # step, but a grant recorded through any other path must still be
        # ignored by the mastery check.
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "divine_sexual_mastery", 0.5)
        ]
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            self.assertNotIn(
                "divine_sexual_mastery", entity.skills.base_owned_keys()
            )
            self.assertEqual(entity.sexual.unlocked_act_keys(), frozenset())

    @covers_requirement("sexual-state-handler::sexualstate-unlocked-act-keys-gates-the-sexual-act-catalogue-by-counter-thresholds-or-unlocks-it-entirely-for-a-mastery-holder")
    def test_mastery_check_tolerates_an_innate_key_missing_from_the_registry(self):
        entity = self._entity()
        original = SKILL_REGISTRY.pop("flee", _MISSING)
        try:
            entity.sexual.unlocked_act_keys()
        finally:
            if original is not _MISSING:
                SKILL_REGISTRY["flee"] = original


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
