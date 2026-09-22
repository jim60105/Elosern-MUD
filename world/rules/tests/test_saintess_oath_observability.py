"""Boundary-event assertions for the 聖女容器 oath flip (saintess-vessel D4).

The irreversible first flip of the ``virgin`` flag by the
``first_vaginal_penetration`` event is a Saintess oath event ONLY for a
``saintess_vessel`` holder: ``saintess_oath_broken`` fires exactly once,
through the transaction-commit seam, with a plain-data context and zero
title reads or writes (design D5 — this capability owns no title state).

All shipped-content key references are derived from the loaded rule table
(the same source the ownership-gated branch reads) — never echoed as
literals — so this module stays outside the test-data debt ledger.
"""

from pathlib import Path
from unittest.mock import patch

from django.db import transaction

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTest

from world.lore.titles import FIXED_TITLE_REGISTRY as FixedTitleRegistry
from world.lore.titles import TitlePredicateFamily
from world.rules.rulebook.schema import load_rules
from world.rules.sexual_transitions import apply_event

RULES = {
    rule.id: rule
    for rule in load_rules(
        Path(__file__).parents[1] / "rulebook" / "combat_modifiers.yaml"
    )
}
VESSEL_KEY = next(
    rule.when["skill_owned"]
    for rule in RULES.values()
    if "blessing_arousal_scale" in rule.then
)
OATH_EVENT = "saintess_oath_broken"
FLIP_EVENT = "first_vaginal_penetration"


class SaintessOathObservabilityTests(EvenniaTest):
    """The oath flip is commit-bound, vessel-gated, and title-free."""

    def _holder(self):
        entity = self.char1
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": [VESSEL_KEY]}
        return entity

    def _title_snapshot(self, entity):
        return (
            entity.attributes.get("title_collection"),
            entity.attributes.get("title_equipped"),
        )

    def _events(self, info_mock):
        return [call.args[0] for call in info_mock.call_args_list if call.args]

    @covers_requirement(
        "saintess-vessel::the-oath-flip-stays-observable-through-the-facade-and-the-office-name-title-ban-holds"
    )
    def test_holder_flip_emits_exactly_one_oath_event_at_commit(self):
        holder = self._holder()
        self.assertTrue(holder.sexual.virgin)
        titles_before = self._title_snapshot(holder)
        with (
            patch("world.rules.sexual_transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True) as callbacks,
        ):
            with transaction.atomic():
                changes = apply_event(holder, FLIP_EVENT)
        self.assertEqual(len(callbacks), 1, "exactly one on_commit callback queued")
        self.assertEqual(changes.get("virgin"), "down")
        self.assertFalse(holder.sexual.virgin)
        self.assertEqual(self._events(info), [OATH_EVENT])
        (event,), kwargs = info.call_args
        self.assertEqual(event, OATH_EVENT)
        self.assertEqual(kwargs["context"]["entity"], str(holder))
        self.assertEqual(kwargs["context"]["event"], FLIP_EVENT)
        self.assertEqual(self._title_snapshot(holder), titles_before)

    def test_repeat_flip_after_commit_reemits_nothing(self):
        holder = self._holder()
        with (
            patch("world.rules.sexual_transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                apply_event(holder, FLIP_EVENT)
        self.assertEqual(self._events(info), [OATH_EVENT])

        with (
            patch("world.rules.sexual_transitions.log_info") as info2,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                changes = apply_event(holder, FLIP_EVENT)
        self.assertNotIn("virgin", changes)
        self.assertNotIn(OATH_EVENT, self._events(info2))

    @covers_requirement(
        "saintess-vessel::the-oath-flip-stays-observable-through-the-facade-and-the-office-name-title-ban-holds"
    )
    def test_rolled_back_flip_emits_no_oath_event(self):
        holder = self._holder()
        with (
            patch("world.rules.sexual_transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                apply_event(holder, FLIP_EVENT)
                transaction.set_rollback(True)
        self.assertNotIn(OATH_EVENT, self._events(info))

    def test_non_holder_flip_emits_no_oath_event(self):
        plain = self.char2
        plain.race = "human"
        plain.apply_race_baseline()
        plain.db.skills = {"active": [], "passive": []}
        self.assertTrue(plain.sexual.virgin)
        with (
            patch("world.rules.sexual_transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                changes = apply_event(plain, FLIP_EVENT)
        self.assertEqual(changes.get("virgin"), "down")
        self.assertNotIn(OATH_EVENT, self._events(info))

    @covers_requirement(
        "saintess-vessel::the-oath-flip-stays-observable-through-the-facade-and-the-office-name-title-ban-holds"
    )
    def test_title_system_is_untouched_by_the_capability(self):
        families_before = frozenset(TitlePredicateFamily)
        rows_before = frozenset(FixedTitleRegistry)
        holder = self._holder()
        with self.captureOnCommitCallbacks(execute=True):
            apply_event(holder, FLIP_EVENT)
        self.assertEqual(frozenset(TitlePredicateFamily), families_before)
        self.assertEqual(frozenset(FixedTitleRegistry), rows_before)
        # The §9.2 sanction allows at most ONE extension — the church
        # redeemed-count family — and it lands with the sibling
        # order-catalogue change: at THIS landing the family set stays
        # unchanged, so the sanctioned family is asserted ABSENT here.
        self.assertNotIn("church_skills_redeemed", {f.value for f in TitlePredicateFamily})
        self.assertFalse(
            any(
                "聖女" in str(getattr(row, "display_name_zh", ""))
                for row in FixedTitleRegistry.values()
            )
        )