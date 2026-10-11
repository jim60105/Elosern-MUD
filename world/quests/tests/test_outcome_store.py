"""Durable exclusive-group and consumed-transition store tests (task 1.2)."""

import unittest

from django.db import IntegrityError, transaction
from evennia.utils.test_resources import EvenniaTest

from world.quests.models import EscortEventTransition, ExclusiveOutcomeGroup
from world.quests.outcome_store import (
    allocate_acceptance_sequence,
    consume_transition,
    get_or_create_group,
    list_owner_groups,
    mark_group_resolved,
    read_group,
    transition_consumed,
)

_OWNER = 4101
_PACKAGE = "pkg_predicate_group"
_GROUP = "reunion"


class OutcomeStoreTests(EvenniaTest):
    """The two database-unique outcome records and their write seams."""

    def test_group_identity_is_database_unique(self):
        first = get_or_create_group(
            owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP
        )
        second = get_or_create_group(
            owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ExclusiveOutcomeGroup.objects.count(), 1)
        # The constraint, not a prior read, is what forbids a second row.
        with self.assertRaises(IntegrityError):
            # The savepoint contains the violation so the test's own
            # transaction (and the surrounding Evennia teardown) stays usable.
            with transaction.atomic():
                ExclusiveOutcomeGroup.objects.create(
                    owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP
                )
        # A repeated creation never multiplies the row (no list scan involved).
        for _ in range(5):
            get_or_create_group(owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP)
        self.assertEqual(ExclusiveOutcomeGroup.objects.count(), 1)

    def test_distinct_owner_package_and_group_are_distinct_rows(self):
        first = get_or_create_group(
            owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP
        )
        other_owner = get_or_create_group(
            owner_id=_OWNER + 1, package_id=_PACKAGE, group_id=_GROUP
        )
        other_package = get_or_create_group(
            owner_id=_OWNER, package_id=_PACKAGE + "_b", group_id=_GROUP
        )
        other_group = get_or_create_group(
            owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP + "_b"
        )
        self.assertEqual(len({first.pk, other_owner.pk, other_package.pk, other_group.pk}), 4)
        # The owner holds the base group plus the other-package and
        # other-group variants; the foreign owner's group is not theirs.
        self.assertEqual(len(list_owner_groups(_OWNER)), 3)
        self.assertEqual(len(list_owner_groups(_OWNER + 1)), 1)

    def test_acceptance_sequences_are_monotonic_and_persist(self):
        first = allocate_acceptance_sequence(
            owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP, tick=7
        )
        second = allocate_acceptance_sequence(
            owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP, tick=7
        )
        third = allocate_acceptance_sequence(
            owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP, tick=8
        )
        # Same-tick acceptances are still ordered, which world tick cannot do.
        self.assertEqual((first, second, third), (1, 2, 3))
        reloaded = read_group(owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP)
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.next_sequence, 4)
        self.assertEqual(reloaded.updated_tick, 8)
        self.assertEqual(
            allocate_acceptance_sequence(
                owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP
            ),
            4,
        )

    def test_the_sequence_allocation_creates_the_group_once(self):
        allocate_acceptance_sequence(
            owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP
        )
        self.assertEqual(ExclusiveOutcomeGroup.objects.count(), 1)
        self.assertEqual(
            read_group(owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP).resolved,
            False,
        )

    def test_a_transition_is_consumed_once_per_stable_source(self):
        self.assertTrue(
            consume_transition(
                owner_id=_OWNER, record_id="escort:1", source_key="move:41:room:9", tick=3
            )
        )
        # The same stable source — pre-follow receive or post-follow recheck,
        # or a replay after a committed reload — consumes nothing more.
        self.assertFalse(
            consume_transition(
                owner_id=_OWNER, record_id="escort:1", source_key="move:41:room:9", tick=3
            )
        )
        self.assertTrue(
            transition_consumed(
                owner_id=_OWNER, record_id="escort:1", source_key="move:41:room:9"
            )
        )
        # A different source, record, or owner is a different identity.
        self.assertTrue(
            consume_transition(
                owner_id=_OWNER, record_id="escort:1", source_key="move:42:room:9"
            )
        )
        self.assertTrue(
            consume_transition(
                owner_id=_OWNER, record_id="escort:2", source_key="move:41:room:9"
            )
        )
        self.assertTrue(
            consume_transition(
                owner_id=_OWNER + 1, record_id="escort:1", source_key="move:41:room:9"
            )
        )
        self.assertEqual(EscortEventTransition.objects.count(), 4)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EscortEventTransition.objects.create(
                    owner_id=_OWNER, record_id="escort:1", source_key="move:41:room:9"
                )

    def test_resolution_state_is_persisted_and_exclusive(self):
        get_or_create_group(owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP)
        resolved = mark_group_resolved(
            owner_id=_OWNER,
            package_id=_PACKAGE,
            group_id=_GROUP,
            resolution_source="move:41:room:9",
            winner_quest_id="escort:1",
            tick=11,
        )
        self.assertTrue(resolved.resolved)
        self.assertFalse(resolved.unresolved)
        reloaded = read_group(owner_id=_OWNER, package_id=_PACKAGE, group_id=_GROUP)
        self.assertEqual(reloaded.resolution_source, "move:41:room:9")
        self.assertEqual(reloaded.winner_quest_id, "escort:1")
        self.assertFalse(reloaded.no_commission)
        self.assertEqual(reloaded.updated_tick, 11)
        # An unaccepted physical result names no winning record.
        unaccepted = mark_group_resolved(
            owner_id=_OWNER + 1,
            package_id=_PACKAGE,
            group_id=_GROUP,
            resolution_source="meet:41:42",
            no_commission=True,
        )
        self.assertTrue(unaccepted.no_commission)
        self.assertEqual(unaccepted.winner_quest_id, "")

    def test_a_resolution_never_names_both_a_winner_and_no_commission(self):
        with self.assertRaises(ValueError):
            mark_group_resolved(
                owner_id=_OWNER,
                package_id=_PACKAGE,
                group_id=_GROUP,
                resolution_source="move:41:room:9",
                winner_quest_id="escort:1",
                no_commission=True,
            )
        with self.assertRaises(ValueError):
            mark_group_resolved(
                owner_id=_OWNER,
                package_id=_PACKAGE,
                group_id=_GROUP,
                resolution_source="",
            )
        self.assertEqual(ExclusiveOutcomeGroup.objects.count(), 0)


if __name__ == "__main__":
    unittest.main()