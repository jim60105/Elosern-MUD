"""Mutation-boundary tests for status reads and clock reads (3.5/3.6)."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import _add_buff
from world.rules.clock import (
    WorldClockScript,
    get_world_clock,
    read_world_clock,
)
from world.rules.status_query import build_status_read_model
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import (
    PresentationCoordinator,
    read_world_clock_calendar,
)


class ClockReadTests(EvenniaTestCase):
    @covers_requirement("world-clock::world-clock-presentation-reads-never-create-the-singleton")
    def test_read_world_clock_reports_absence_without_creating(self):
        before = len(WorldClockScript.objects.all())
        self.assertIsNone(read_world_clock())
        self.assertEqual(len(WorldClockScript.objects.all()), before)

    @covers_requirement("world-clock::world-clock-presentation-reads-never-create-the-singleton")
    def test_read_world_clock_returns_existing_singleton_without_new_script(self):
        get_world_clock()
        count = len(WorldClockScript.objects.all())
        clock = read_world_clock()
        self.assertIsNotNone(clock)
        self.assertEqual(len(WorldClockScript.objects.all()), count)

    @covers_requirement(
        "world-clock::world-clock-presentation-reads-never-create-the-singleton"
    )
    def test_calendar_provider_reads_existing_clock_only(self):
        get_world_clock()
        before = len(WorldClockScript.objects.all())
        calendar = read_world_clock_calendar()
        self.assertIsNotNone(calendar)
        self.assertEqual(len(WorldClockScript.objects.all()), before)
        self.assertIn("season_name", dir(calendar))

    @covers_requirement(
        "world-clock::world-clock-presentation-reads-never-create-the-singleton"
    )
    def test_calendar_provider_returns_none_without_clock(self):
        self.assertIsNone(read_world_clock_calendar())


class MutationBoundaryTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        get_world_clock()
        self.actor = create_object(PlayerCharacter, key="boundary actor")
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.location = self.room1
        self.actor.db.disguised_stats = {"hp": 999}
        _add_buff(self.actor, "poisoned")
        self.actor.sexual.pleasure.base = 60

    def _snapshot(self):
        from web.webclient.presentation.registry import build_production_registry

        session = MockSession()
        registry = build_production_registry()
        coordinator = PresentationCoordinator(session, registry)
        context = PresentationContext(actor=self.actor, protocol_version=1)
        coordinator.full_snapshot(context)
        return session.sent

    @covers_requirement(
        "webclient-status-presentation::status-presentation-has-no-mutation-side-effects"
    )
    def test_status_reads_preserve_every_canonical_value(self):
        def canon():
            traits = {key: getattr(self.actor.traits, key).value for key in self.actor.traits.all()}
            gauges = {key: (getattr(self.actor.traits, key).current, getattr(self.actor.traits, key).max) for key in ("hp", "mp", "sp")}
            return {
                "traits": traits,
                "gauges": gauges,
                "buffs": dict(self.actor.attributes.get("buffs") or {}),
                "sexual_traits": dict(self.actor.attributes.get("sexual_traits", category="traits") or {}),
                "active_combat": self.actor.db.active_combat,
                "location": self.actor.location,
                "disguised_stats": self.actor.db.disguised_stats,
            }

        before = canon()
        build_status_read_model(self.actor)
        self._snapshot()
        build_status_read_model(self.actor)
        after = canon()
        self.assertEqual(after, before)

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_snapshot_does_not_materialize_missing_sexual_handler(self):
        get_world_clock()
        actor = create_object(PlayerCharacter, key="no sexual")
        actor.race = "human"
        actor.apply_race_baseline()
        self.assertIsNone(actor.attributes.get("sexual_traits", category="traits"))
        from web.webclient.presentation.registry import build_production_registry

        coordinator = PresentationCoordinator(MockSession(), build_production_registry())
        context = PresentationContext(actor=actor, protocol_version=1)
        coordinator.full_snapshot(context)
        self.assertIsNone(
            actor.attributes.get("sexual_traits", category="traits"),
            "presentation must not materialize an uninitialized sexual handler",
        )

    @covers_requirement(
        "webclient-status-presentation::status-presentation-has-no-mutation-side-effects"
    )
    def test_world_tick_and_script_count_unchanged(self):
        get_world_clock()
        tick_before = get_world_clock().tick
        scripts_before = len(WorldClockScript.objects.all())
        build_status_read_model(self.actor)
        self._snapshot()
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertEqual(len(WorldClockScript.objects.all()), scripts_before)


class MockSession:
    def __init__(self):
        self.sent = []

    def msg(self, **kwargs):
        self.sent.append(kwargs)


if __name__ == "__main__":
    unittest.main()
