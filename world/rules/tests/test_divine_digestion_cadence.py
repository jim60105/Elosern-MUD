"""Synthetic behavior tests for the divine-mystery digestion cadence.

The digestion cadence (divine-mystery design §3) is the one category-scoped
brake on use-driven practice: an ACTIVE skill in
``SkillCategory.DIVINE_MYSTERY`` accrues at most once per actor per skill per
world-calendar day, with the day derived from the world clock's own calendar
(``WorldDateTime`` + the ``clock.yaml`` constants — never wall-clock time).
Every gate case here is ``unittest.TestCase``-pure: stub entities are
``SimpleNamespace`` shapes, the skills are kit-shaped synthetic rows with
shipped-content-free keys, and the persisted ``db.skill_practice_day`` claim
is exercised through the real ``grant_skill_practice_xp`` entry point. One
``EvenniaTest`` class drives the resolve-level ``_commit`` rollback, which
needs real Attribute storage. No shipped-catalog names and no data-contract
tagging anywhere in this module (test-data-independence).
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement

from world.rules import progression
from world.rules.action import CommitFailed, PendingEffect, _commit
from world.rules.clock import WorldDateTime, _DAY_SECONDS
from world.rules.progression import (
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    practice_claim_key,
    practice_day_ordinal,
    proficiency_cap,
    release_practice_claims,
    reset_practice_dedupe,
)
from world.skills.registry import SkillCategory, TargetSpec, validate_prerequisite_graph
from world.tests.synthetic_data import make_skill

from ._combat_session_helpers import live_skill_registry, open_synthetic_scope


# --- synthetic rows under test ----------------------------------------------
#
# Two distinct divine-mystery skills (the category the cadence gates) and one
# 情慾秘術-shaped row: it declares the ``requires_divine_arts`` blood marker
# while living OUTSIDE the cadence's category and must keep today's unlimited
# accrual, byte-for-byte.

_T_MYSTERY_1 = make_skill(
    "t_mystery_echo",
    label="回響神言",
    category=SkillCategory.DIVINE_MYSTERY,
    target_spec=TargetSpec.SELF,
    cost={},
    effects=[],
)
_T_MYSTERY_2 = make_skill(
    "t_mystery_veil",
    label="幔之神言",
    category=SkillCategory.DIVINE_MYSTERY,
    target_spec=TargetSpec.SELF,
    cost={},
    effects=[],
)
_T_DIVINE_LINE = make_skill(
    "t_divine_sensual_rite",
    label="性愛系統探針",
    category=SkillCategory.SEXUAL_ACT,
    requires_divine_arts=True,
    target_spec=TargetSpec.SELF,
    cost={},
    effects=[],
)
_ALL_ROWS = {
    _T_MYSTERY_1.key: _T_MYSTERY_1,
    _T_MYSTERY_2.key: _T_MYSTERY_2,
    _T_DIVINE_LINE.key: _T_DIVINE_LINE,
}


def _entity(
    owned: tuple[str, ...] = (),
    proficiency: dict[str, float] | None = None,
    race: str | None = None,
):
    """Build a pure stub entity the progression queries accept."""
    return SimpleNamespace(
        race=race,
        pk=None,
        key="stub",
        skills=SimpleNamespace(owned_keys=lambda: set(owned)),
        db=SimpleNamespace(
            skill_proficiency=dict(proficiency or {}),
            affinity_elements=[],
            skills={"active": list(owned), "passive": []},
        ),
    )


class PracticeDayOrdinalTests(unittest.TestCase):
    """The absolute day ordinal: clock.yaml ring, stable within a day."""

    @staticmethod
    def _ordinal(year: int, season: int, day: int, hour: int = 0) -> int:
        return practice_day_ordinal(
            WorldDateTime(year, season, day, hour, minute=0, second=0)
        )

    def test_stable_within_one_day(self):
        self.assertEqual(
            self._ordinal(2, 1, 7, hour=0),
            self._ordinal(2, 1, 7, hour=23),
        )

    def test_day_roll_is_exactly_one(self):
        self.assertEqual(
            self._ordinal(3, 2, 17, hour=23) + 1,
            self._ordinal(3, 2, 18),
        )

    def test_season_roll_is_exactly_one(self):
        # Day 90 of a season (90 days/season) is the ring's last day.
        self.assertEqual(
            self._ordinal(0, 0, 90, hour=23) + 1,
            self._ordinal(0, 1, 1),
        )

    def test_year_roll_is_exactly_one(self):
        # 90 days/season x 4 seasons/year: ordinal 360 is day 1 of year 1.
        self.assertEqual(
            self._ordinal(0, 3, 90, hour=23) + 1,
            self._ordinal(1, 0, 1),
        )
        self.assertEqual(self._ordinal(1, 0, 1), 90 * 4)


class CurrentPracticeDayTests(unittest.TestCase):
    """``_current_practice_day`` derives the ordinal, never the raw tick."""

    def test_no_clock_falls_back_to_day_zero(self):
        with patch("world.rules.clock.read_world_clock", return_value=None):
            self.assertEqual(progression._current_practice_day(), 0)

    def test_reads_the_ordinal_of_the_persisted_clock_calendar(self):
        # Tick 2 days + 2 hours is calendar day ordinal 2 — a bug reading
        # ``int(clock.tick)`` would yield 180000 here and fail the assertion.
        from world.rules.clock import WorldClock

        clock = WorldClock(2 * _DAY_SECONDS + 7200)
        with patch("world.rules.clock.read_world_clock", return_value=clock):
            self.assertEqual(progression._current_practice_day(), 2)


class _Scoped(unittest.TestCase):
    """Scoped base: kit rows around the whole lifecycle, caches revalidated."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "races",
            "elements",
            extra={"skills": _ALL_ROWS},
        )
        validate_prerequisite_graph(live_skill_registry())


class DigestionCadenceTests(_Scoped):
    """One accrual per (actor, skill) per world-calendar day for the category."""

    def setUp(self):
        super().setUp()
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tick = {"value": 7}
        self.day = {"value": 47}
        tick_patch = patch.object(
            progression, "_current_tick", lambda: self.tick["value"]
        )
        tick_patch.start()
        self.addCleanup(tick_patch.stop)
        day_patch = patch.object(
            progression, "_current_practice_day", lambda: self.day["value"]
        )
        day_patch.start()
        self.addCleanup(day_patch.stop)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_second_same_day_use_accrues_nothing(self):
        actor = _entity((_T_MYSTERY_1.key,), race="t_duskmari")
        first = SimpleNamespace(pk=100, key="t1")
        second = SimpleNamespace(pk=101, key="t2")
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key, first)
        )
        # A DISTINCT target: the per-tick dedupe would allow this use; only
        # the cadence can refuse it.
        self.assertFalse(
            progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key, second)
        )
        self.assertEqual(
            actor.db.skill_proficiency[_T_MYSTERY_1.key], SKILL_PRACTICE_XP_PER_USE
        )
        self.assertEqual(actor.db.skill_practice_day, {_T_MYSTERY_1.key: 47})

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_next_calendar_day_accrues_again(self):
        actor = _entity((_T_MYSTERY_1.key,), race="t_duskmari")
        self.assertTrue(progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key))
        # New day, new ticks: the same actor/skill/target is fresh on both axes.
        self.tick["value"] = 8
        self.day["value"] = 48
        self.assertTrue(progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key))
        self.assertEqual(
            actor.db.skill_proficiency[_T_MYSTERY_1.key],
            2 * SKILL_PRACTICE_XP_PER_USE,
        )
        self.assertEqual(actor.db.skill_practice_day, {_T_MYSTERY_1.key: 48})

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_each_mystery_holds_its_own_day(self):
        actor = _entity((_T_MYSTERY_1.key, _T_MYSTERY_2.key), race="t_duskmari")
        self.assertTrue(progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key))
        self.assertTrue(progression.grant_skill_practice_xp(actor, _T_MYSTERY_2.key))
        self.assertFalse(progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key))
        self.assertEqual(
            actor.db.skill_proficiency[_T_MYSTERY_1.key], SKILL_PRACTICE_XP_PER_USE
        )
        self.assertEqual(
            actor.db.skill_proficiency[_T_MYSTERY_2.key], SKILL_PRACTICE_XP_PER_USE
        )
        self.assertEqual(
            actor.db.skill_practice_day,
            {_T_MYSTERY_1.key: 47, _T_MYSTERY_2.key: 47},
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_divine_arts_skill_outside_the_category_accrues_twice_in_one_day(self):
        actor = _entity((_T_DIVINE_LINE.key,), race="t_duskmari")
        first = SimpleNamespace(pk=200, key="t1")
        second = SimpleNamespace(pk=201, key="t2")
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, _T_DIVINE_LINE.key, first)
        )
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, _T_DIVINE_LINE.key, second)
        )
        self.assertEqual(
            actor.db.skill_proficiency[_T_DIVINE_LINE.key],
            2 * SKILL_PRACTICE_XP_PER_USE,
        )
        # The cadence never materializes a claim for a skill outside the
        # category: the 情慾秘術 divine line keeps today's behavior.
        self.assertFalse(hasattr(actor.db, "skill_practice_day"))

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_day_blocked_use_takes_no_per_tick_claim(self):
        actor = _entity((_T_MYSTERY_1.key,), race="t_duskmari")
        first = SimpleNamespace(pk=300, key="t1")
        second = SimpleNamespace(pk=301, key="t2")
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key, first)
        )
        self.assertFalse(
            progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key, second)
        )
        claims = progression.practice_claims_for(actor, _T_MYSTERY_1.key)
        self.assertIn(practice_claim_key(actor, _T_MYSTERY_1.key, first), claims)
        self.assertNotIn(practice_claim_key(actor, _T_MYSTERY_1.key, second), claims)

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_a_saturated_use_still_consumes_the_day(self):
        # Accepted D5 anomaly, pinned: a use at the derived tip cap awards
        # nothing, yet the day is consumed all the same — the distinction is
        # unobservable, so the claim follows the attempted-award path.
        ceiling = proficiency_cap(_T_MYSTERY_1.key) * SKILL_PROFICIENCY_XP_PER_LEVEL
        actor = _entity(
            (_T_MYSTERY_1.key,),
            race="t_duskmari",
            proficiency={_T_MYSTERY_1.key: ceiling},
        )
        self.assertTrue(progression.grant_skill_practice_xp(actor, _T_MYSTERY_1.key))
        self.assertEqual(actor.db.skill_proficiency[_T_MYSTERY_1.key], ceiling)
        self.assertEqual(actor.db.skill_practice_day, {_T_MYSTERY_1.key: 47})


class DigestionCadenceResolveRollbackTests(EvenniaTest):
    """A failing inner commit restores the day claim byte-for-byte.

    The delta scenario's inner-failure branch: ``_commit`` snapshots the
    ``progression`` surface before applying effects, so a later pending
    effect that raises rolls the claim back with the proficiency it guards,
    and a same-day retry accrues again.
    """

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "skills",
            "races",
            "elements",
            extra={"skills": _ALL_ROWS},
        )
        reset_practice_dedupe()
        self.char1.race = "t_duskmari"
        self.char1.apply_race_baseline()
        self.char1.db.skills = {"active": [_T_MYSTERY_1.key], "passive": []}
        self.char1.db.skill_proficiency = {_T_MYSTERY_1.key: 0.0}
        self.char1.db.skill_practice_day = {_T_MYSTERY_1.key: -1}

    def _practice_effect(self) -> PendingEffect:
        return PendingEffect(
            self.char1,
            f"skill_practice|{self.char1.pk}|{_T_MYSTERY_1.key}|-",
            frozenset({"progression"}),
            lambda: progression.grant_skill_practice_xp(
                self.char1, _T_MYSTERY_1.key
            ),
        )

    def _failing_effect(self) -> PendingEffect:
        return PendingEffect(
            self.char1,
            "boom",
            frozenset({"progression"}),
            lambda: (_ for _ in ()).throw(RuntimeError("injected")),
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_failed_commit_restores_the_day_claim_and_same_day_retry_accrues(self):
        with self.assertRaises(CommitFailed):
            _commit(
                [self._practice_effect(), self._failing_effect()],
                char=str(self.char1.pk),
                action=_T_MYSTERY_1.key,
            )
        # Byte-equal restore: both attributes are back to their pre-action
        # values, so the failed commit did not burn the day.
        self.assertEqual(
            self.char1.db.skill_proficiency, {_T_MYSTERY_1.key: 0.0}
        )
        self.assertEqual(
            self.char1.db.skill_practice_day, {_T_MYSTERY_1.key: -1}
        )
        # Mirror resolve()'s CommitFailed branch (action.py): release the
        # tick claims the staged award took so the same-day retry accrues.
        release_practice_claims(
            [practice_claim_key(self.char1, _T_MYSTERY_1.key, None)]
        )
        _commit(
            [self._practice_effect()],
            char=str(self.char1.pk),
            action=_T_MYSTERY_1.key,
        )
        self.assertEqual(
            self.char1.db.skill_proficiency,
            {_T_MYSTERY_1.key: SKILL_PRACTICE_XP_PER_USE},
        )
        # No persisted world clock exists in this test, so the fallback day
        # ordinal is 0; the -1 pre-seed proves the retry genuinely re-claimed.
        self.assertEqual(self.char1.db.skill_practice_day, {_T_MYSTERY_1.key: 0})


if __name__ == "__main__":
    unittest.main()