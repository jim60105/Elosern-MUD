"""Behaviour of the per-pass world-maintenance counting scope."""

import unittest

from world.observability.tally import (
    MAINTENANCE_EVENTS,
    maintenance_tally,
    note_maintenance,
    suspended_maintenance_tally,
)


class MaintenanceTallyTests(unittest.TestCase):
    def test_no_scope_counts_nothing_and_reports_false(self) -> None:
        self.assertFalse(note_maintenance("monster_arrived"))
        with maintenance_tally() as counts:
            self.assertEqual(counts, {})

    def test_open_scope_counts_each_name(self) -> None:
        with maintenance_tally() as counts:
            self.assertTrue(note_maintenance("monster_departed"))
            self.assertTrue(note_maintenance("monster_departed"))
            self.assertTrue(note_maintenance("fatigue_transition"))
            self.assertEqual(
                counts, {"monster_departed": 2, "fatigue_transition": 1}
            )

    def test_nested_open_reuses_the_same_scope(self) -> None:
        with maintenance_tally() as outer:
            with maintenance_tally() as inner:
                self.assertIs(inner, outer)
                self.assertTrue(note_maintenance("monster_activity_decided"))
            self.assertEqual(outer, {"monster_activity_decided": 1})
            self.assertTrue(note_maintenance("monster_activity_decided"))
            self.assertEqual(outer, {"monster_activity_decided": 2})

    def test_suspension_stops_counting_then_resumes_the_scope(self) -> None:
        with maintenance_tally() as counts:
            with suspended_maintenance_tally():
                self.assertFalse(note_maintenance("monster_arrived"))
                self.assertEqual(counts, {})
            self.assertTrue(note_maintenance("monster_arrived"))
            self.assertEqual(counts, {"monster_arrived": 1})
        self.assertFalse(note_maintenance("monster_arrived"))

    def test_a_scope_that_raises_is_closed(self) -> None:
        with self.assertRaises(RuntimeError):
            with maintenance_tally() as counts:
                self.assertTrue(note_maintenance("monster_arrived"))
                raise RuntimeError("late settlement fault")
        self.assertFalse(note_maintenance("monster_arrived"))

    def test_every_declared_name_is_accepted_and_unknown_names_raise(self) -> None:
        with maintenance_tally() as counts:
            for event in MAINTENANCE_EVENTS:
                self.assertTrue(note_maintenance(event))
            self.assertEqual(set(counts), set(MAINTENANCE_EVENTS))
        with self.assertRaises(ValueError):
            note_maintenance("clock_advance")
        with maintenance_tally() as counts:
            with self.assertRaises(ValueError):
                note_maintenance("monster_site_cleared")
            self.assertEqual(counts, {})
