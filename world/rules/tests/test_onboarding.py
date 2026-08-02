"""Onboarding state-service tests (tasks 5.3).

These tests exercise ``world.rules.onboarding`` — the sole writer of onboarding
state — plus the arrival/guard integration paths.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import OnboardingGuide
from typeclasses.npcs import NPC
from world.maps.bootstrap import (
    GUILD_HALL_EXTERIOR_XYZ,
    SOUTH_GATE_XYZ,
    sync_grid,
    sync_service_interiors,
)
from world.onboarding.guide import GuideProgress
from world.onboarding.guide_dialogue import GUARD_DIALOGUE_KEY
from world.rules.onboarding import (
    advance_beat,
    guard_adult_identity,
    mark_guide_skipped,
    maybe_play_arrival,
    observe_room_entry,
    relocate_to_starting_location,
    set_onboarded,
    snapshot_for,
    sync_guard_npc,
    talk_response,
)


def _grid(xyz):
    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom

    return XYZRoom.objects.filter_xyz(xyz=xyz).first()


def _south_gate():
    return _grid(SOUTH_GATE_XYZ)


def _guild_exterior():
    return _grid(GUILD_HALL_EXTERIOR_XYZ)


class OnboardingGridMixin:
    def setUp(self):
        super().setUp()
        create_object(__import__("typeclasses.rooms", fromlist=["Room"]).Room, key="Limbo", location=None)
        sync_grid()
        sync_service_interiors()
        self.player = create_object(PlayerCharacter, key="onboard-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = _south_gate()

    def _corridor_room(self):
        room = _grid((2, 1, "capital_altoria"))  # 南大道
        return room


class OnboardingStateServiceTests(OnboardingGridMixin, EvenniaTest):
    def test_relocation_moves_shell_to_south_gate_without_clock_advance(self):
        clock_tick = __import__("world.rules.clock", fromlist=["get_world_clock"]).get_world_clock().tick
        self.player.location = self.room1
        relocate_to_starting_location(self.player)
        self.assertIs(self.player.location, _south_gate())
        self.assertEqual(
            __import__("world.rules.clock", fromlist=["get_world_clock"]).get_world_clock().tick,
            clock_tick,
        )

    def test_relocation_without_south_gate_leaves_shell_in_place(self):
        self.player.location = self.room1
        with patch("world.rules.onboarding._south_gate", return_value=None):
            messages = []
            self.player.msg = lambda text, **kwargs: messages.append(str(text))
            relocate_to_starting_location(self.player)
        self.assertIs(self.player.location, self.room1)
        self.assertTrue(any("南門" in message for message in messages))

    def test_relocation_failed_move_sends_degradation_and_keeps_activation(self):
        self.player.location = self.room1
        self.player.creation_pending = False

        class FakeGate:
            key = "南門"

        with patch(
            "world.rules.onboarding._south_gate", return_value=FakeGate()
        ), patch.object(
            self.player, "move_to", return_value=False
        ):
            messages = []
            self.player.msg = lambda text, **kwargs: messages.append(str(text))
            relocate_to_starting_location(self.player)
        self.assertIs(self.player.location, self.room1)
        self.assertTrue(any("南門" in message for message in messages))
        self.assertFalse(self.player.creation_pending)

    def test_relocation_exception_degrades_without_rollback(self):
        self.player.location = self.room1
        self.player.creation_pending = False
        with patch(
            "world.rules.onboarding._south_gate", side_effect=RuntimeError("boom")
        ):
            messages = []
            self.player.msg = lambda text, **kwargs: messages.append(str(text))
            relocate_to_starting_location(self.player)
        self.assertIs(self.player.location, self.room1)
        self.assertTrue(any("南門" in message for message in messages))
        self.assertFalse(self.player.creation_pending)

    def test_maybe_play_arrival_plays_at_gate_and_sets_look_beat(self):
        messages = []
        self.player.msg = lambda text, **kwargs: messages.append(str(text))
        self.assertTrue(maybe_play_arrival(self.player))
        self.assertEqual(self.player.onboarding_beat, "look")
        self.assertTrue(any("南門" in message for message in messages))

    def test_arrival_does_not_replay_once_onboarded(self):
        self.player.onboarded = True
        self.assertFalse(maybe_play_arrival(self.player))

    def test_advance_beat_returns_guidance_and_sets_first_arrival_seen(self):
        self.player.onboarding_beat = "look"
        guidance = advance_beat(self.player)
        self.assertIsNotNone(guidance)
        self.assertIn("北", guidance)
        self.assertTrue(self.player.first_arrival_seen)
        self.assertEqual(self.player.onboarding_beat, "guidance")

    def test_advance_beat_nowhere_else_never_advances(self):
        self.player.location = self._corridor_room()
        self.player.onboarding_beat = "look"
        self.assertIsNone(advance_beat(self.player))
        self.assertEqual(self.player.onboarding_beat, "look")
        self.assertFalse(self.player.first_arrival_seen)

    def test_room_outside_corridor_marks_guide_skipped(self):
        self.player.guide_progress = GuideProgress.active().to_storage()
        self.player.location = self.room1  # non-corridor room
        observe_room_entry(self.player)
        self.assertEqual(snapshot_for(self.player).guide_progress.state, "skipped")
        self.assertFalse(self.player.onboarded)

    def test_guild_exterior_completes_guidance(self):
        self.player.guide_progress = GuideProgress.active().to_storage()
        self.player.onboarding_beat = "guidance"
        self.player.location = _guild_exterior()
        observe_room_entry(self.player)
        self.assertEqual(snapshot_for(self.player).guide_progress.state, "completed")
        self.assertFalse(self.player.onboarded)

    def test_guide_progress_round_trips_through_storage(self):
        self.player.guide_progress = GuideProgress.active().with_keyword("公會").to_storage()
        self.assertEqual(
            snapshot_for(self.player).guide_progress,
            GuideProgress.active().with_keyword("公會"),
        )

    def test_mark_guide_skipped_preserves_seen_keywords(self):
        self.player.guide_progress = GuideProgress.active().with_keyword("公會").to_storage()
        mark_guide_skipped(self.player)
        progress = snapshot_for(self.player).guide_progress
        self.assertEqual(progress.state, "skipped")
        self.assertEqual(progress.seen_keywords, ("公會",))

    def test_set_onboarded_blocks_further_guidance(self):
        set_onboarded(self.player)
        self.assertTrue(self.player.onboarded)

    def test_talk_response_requires_component_and_updates_progress(self):
        npc = create_object(NPC, key="plain-npc")
        self.player.guide_progress = GuideProgress.active().to_storage()
        self.assertIsNone(talk_response(npc, self.player, "公會"))

    def test_talk_response_known_and_unknown_keywords(self):
        guard = create_object(NPC, key="guard")
        guard.components.add(OnboardingGuide.create(guard, dialogue_key=GUARD_DIALOGUE_KEY))
        self.player.guide_progress = GuideProgress.active().to_storage()
        response = talk_response(guard, self.player, "公會")
        self.assertIn("冒險者公會", response)
        self.assertEqual(
            snapshot_for(self.player).guide_progress.seen_keywords, ("公會",)
        )
        unknown = talk_response(guard, self.player, "謎語")
        self.assertIn("明白", unknown)
        self.assertEqual(
            snapshot_for(self.player).guide_progress.seen_keywords, ("公會",)
        )


class GuardSyncTests(OnboardingGridMixin, EvenniaTest):
    @covers_requirement("onboarding-guide::the-south-gate-guard-offers-scripted-guidance")
    def test_sync_creates_exactly_one_adult_guard(self):
        sync_guard_npc()
        sync_guard_npc()
        from evennia.utils.search import search_object_by_tag

        guards = search_object_by_tag("onboarding_guard")
        self.assertEqual(len(guards), 1)
        self.assertIs(guards[0].location, _south_gate())
        self.assertIsInstance(guards[0], NPC)
        age, apparent_age = guard_adult_identity(guards[0])
        self.assertGreaterEqual(age, 18)
        self.assertGreaterEqual(apparent_age, 18)

    def test_sync_repairs_an_existing_tagged_guard(self):
        from evennia.utils.create import create_object as _co

        stale = _co(NPC, key="stale-guard", location=self.room1, tags=["onboarding_guard"])
        sync_guard_npc()
        from evennia.utils.search import search_object_by_tag

        guards = search_object_by_tag("onboarding_guard")
        self.assertEqual(len(guards), 1)
        self.assertIs(guards[0], stale)
        age, apparent_age = guard_adult_identity(guards[0])
        self.assertGreaterEqual(age, 18)
        self.assertGreaterEqual(apparent_age, 18)
        self.assertTrue(guards[0].components.has(OnboardingGuide.name))

    def test_sync_skips_without_south_gate(self):
        with patch("world.rules.onboarding._south_gate", return_value=None):
            sync_guard_npc()
        from evennia.utils.search import search_object_by_tag

        self.assertEqual(list(search_object_by_tag("onboarding_guard")), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
