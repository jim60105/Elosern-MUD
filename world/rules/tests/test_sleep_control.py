"""Synthetic owner sleep-control view, decision and continuation behavior."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from world.narrative.dream_surface import DreamEntryError, associated_session
from world.rules.clock import (
    ScheduledEvent,
    _EVENT_SOURCES,
    get_world_clock,
    register_event_source,
)
from world.rules.fatigue import SleepPosture, read_fatigue_state, write_fatigue_state
from world.rules.party import join_party
from world.rules.possession import (
    PossessionWriteError,
    current_possession,
    enter_possession,
    release_possession,
)
from world.rules.sleep_control import (
    ALL_PARTY_SLEEP_LABEL,
    begin_all_party_sleep,
    build_sleep_control_view,
)
from world.rules.sleep_receipt import (
    KIND_FORCED,
    read_sleep_receipt,
    read_sleep_view_generation,
)
from world.rules.time_skip import (
    advance_wait,
    continue_owner_sleep,
    decline_owner_sleep_dream,
    enter_sleep,
    owner_sleep_view_state,
)


def _catalog():
    from world.quests.catalog import register_catalog

    register_catalog()


class SleepControlViewTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        _catalog()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.save()
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)

    def _companion(self, key, *, reserve=180000, location=None):
        npc = create_object(NPC, key=key, location=location or self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        write_fatigue_state(npc, reserve, SleepPosture.AWAKE)
        return npc

    def _view(self, actor=None):
        return build_sleep_control_view(
            actor or self.player, account=self.account, session=self.session
        )

    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_view_lists_every_companion_with_a_reason_and_the_party_last(self):
        awake = self._companion("清醒同伴")
        asleep = self._companion("沉睡同伴")
        enter_sleep(asleep, mode="duration", seconds=100)
        remote = self._companion("遠方同伴")
        remote.location = self.room2
        entry = enter_sleep(self.player, mode="duration", seconds=600)
        # The awake companion is a lawful handoff choice; the owner question is
        # independent of that list.
        self.assertTrue(entry.handoff_offered)

        view = self._view()
        self.assertIsNotNone(view)
        self.assertEqual(
            [row.identity for row in view.rows],
            [int(awake.pk), int(asleep.pk), int(remote.pk)],
        )
        self.assertTrue(view.rows[0].enabled)
        self.assertEqual(view.rows[1].reason, "沉睡中，無法行動")
        self.assertEqual(view.rows[2].reason, "不在同一地點")
        self.assertEqual(ALL_PARTY_SLEEP_LABEL, "全員一起睡眠")
        self.assertTrue(view.party_enabled)
        self.assertIsNotNone(view.owner_sleep)
        self.assertTrue(view.owner_sleep.dream_pending)
        self.assertEqual(view.owner_sleep.sleep_id, entry.sleep_id)

    @covers_requirement(
        "companion-possession-transition::released-control-preserves-owner-physiology-and-rederives-the-view"
    )
    def test_explicit_release_reopens_the_owner_question_at_the_same_revision(self):
        sleeper = self._companion("沉睡者")
        shield = self._companion("見證者")
        enter_sleep(self.player, mode="duration", seconds=600)
        enter_possession(self.player, sleeper)
        enter_sleep(sleeper, mode="duration", seconds=100)
        before_revision = read_sleep_receipt(self.player).revision
        release_possession(self.player, npc=sleeper, reason="handback")
        view = self._view()
        self.assertIsNotNone(view)
        self.assertTrue(view.owner_sleep.dream_pending)
        self.assertGreater(read_sleep_view_generation(self.player), 0)
        self.assertEqual(read_sleep_receipt(self.player).revision, before_revision)
        # The awake companion's presence does not suppress the owner question.
        self.assertIn(int(shield.pk), [row.identity for row in view.rows])

    @covers_requirement(
        "dream-sleep-surface::dream-collaboration-consumes-the-committed-elapsed-result"
    )
    def test_npc_companion_never_owns_the_player_dream(self):
        sleeper = self._companion("沉睡者")
        enter_possession(self.player, sleeper)
        entry = enter_sleep(sleeper, mode="duration", seconds=100)
        self.assertIsNone(associated_session(sleeper))
        with self.assertRaises(DreamEntryError):
            from world.narrative.dream_surface import enter_for_owner

            enter_for_owner(
                sleeper,
                sleep_id=entry.sleep_id,
                revision=0,
                generation=0,
            )

    @covers_requirement(
        "dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result"
    )
    def test_owner_dream_entry_at_zero_elapsed(self):
        before = int(get_world_clock().tick)
        entry = enter_sleep(self.player, mode="duration", seconds=600)
        view = owner_sleep_view_state(self.player)
        result = answer_sleep_dream_for(self.player, view, "enter")
        self.assertEqual(result["outcome"], "success")
        state = associated_session(self.player)
        self.assertIsNotNone(state)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertEqual(read_sleep_receipt(self.player).sleep_id, entry.sleep_id)
        self.actor_cleanup()

    @covers_requirement(
        "dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result"
    )
    def test_forced_owner_sleep_requires_explicit_opt_in(self):
        # Forced sleep creates its own accepted threshold receipt and still
        # requires an explicit opt-in; it never opens automatically.
        write_fatigue_state(self.player, 1200, SleepPosture.AWAKE)
        advance_wait(self.player, 600)
        receipt = read_sleep_receipt(self.player)
        self.assertEqual(receipt.kind, KIND_FORCED)
        forced_state = owner_sleep_view_state(self.player)
        self.assertTrue(forced_state["pending"])
        result = answer_sleep_dream_for(self.player, forced_state, "enter")
        self.assertEqual(result["outcome"], "success")

    def actor_cleanup(self):
        self.player.db.dream_surface = None

    @covers_requirement(
        "time-skip-commands::owner-targeted-sleep-continuation-preserves-skip-safety"
    )
    def test_owner_continuation_crosses_an_earlier_companion_wake(self):
        companion = self._companion("早醒同伴")
        enter_sleep(companion, mode="duration", seconds=100)
        enter_sleep(self.player, mode="duration", seconds=7200)
        before = int(get_world_clock().tick)
        view = owner_sleep_view_state(self.player)
        _value, auto = decline_owner_sleep_dream(
            self.player,
            sleep_id=view["sleep_id"],
            revision=view["revision"],
            generation=view["generation"],
        )
        self.assertTrue(auto)
        result = continue_owner_sleep(
            self.player,
            sleep_id=view["sleep_id"],
            expected_generation=view["generation"],
        )
        self.assertEqual(int(get_world_clock().tick) - before, 7200)
        self.assertEqual(result.elapsed_seconds, 7200)
        self.assertIs(read_fatigue_state(companion).posture, SleepPosture.AWAKE)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        # The early companion consumed awake reserve after its own wake.
        self.assertLess(
            read_fatigue_state(companion).reserve_units, 180000
        )

    @covers_requirement(
        "time-skip-commands::owner-targeted-sleep-continuation-preserves-skip-safety"
    )
    def test_retained_continuation_is_idempotent(self):
        enter_sleep(self.player, mode="duration", seconds=600)
        view = owner_sleep_view_state(self.player)
        decline_owner_sleep_dream(
            self.player,
            sleep_id=view["sleep_id"],
            revision=view["revision"],
            generation=view["generation"],
        )
        before = int(get_world_clock().tick)
        result = continue_owner_sleep(
            self.player,
            sleep_id=view["sleep_id"],
            expected_generation=view["generation"],
            operation_id="synthetic-owner-continuation",
        )
        after = int(get_world_clock().tick)
        replay = continue_owner_sleep(
            self.player,
            sleep_id=view["sleep_id"],
            expected_generation=view["generation"],
            operation_id="synthetic-owner-continuation",
        )
        self.assertEqual(int(get_world_clock().tick), after)
        self.assertEqual(replay.elapsed_seconds, result.elapsed_seconds)
        self.assertEqual(after - before, 600)

    @covers_requirement(
        "time-skip-commands::interruptible-skips-stop-at-the-earliest-relevant-boundary"
    )
    def test_interactive_registered_event_pauses_then_resumes_the_same_target(self):
        original = _EVENT_SOURCES.get("shop_hours")
        register_event_source(
            "shop_hours",
            lambda start, end: [ScheduledEvent("synthetic_interactive", end, {}, interactive=True)],
            next_boundary=lambda start, end: start + 37,
        )
        try:
            enter_sleep(self.player, mode="duration", seconds=7200)
            view = owner_sleep_view_state(self.player)
            decline_owner_sleep_dream(
                self.player,
                sleep_id=view["sleep_id"],
                revision=view["revision"],
                generation=view["generation"],
            )
            before = int(get_world_clock().tick)
            paused = continue_owner_sleep(
                self.player,
                sleep_id=view["sleep_id"],
                expected_generation=view["generation"],
            )
            self.assertTrue(paused.interrupted)
            self.assertEqual(int(get_world_clock().tick) - before, 37)
            after_pause = int(get_world_clock().tick)
            # Once the interaction is resolved, one resume action finishes the
            # remaining owner target without another wait click.
            register_event_source(
                "shop_hours", lambda start, end: [], next_boundary=None
            )
            resumed = continue_owner_sleep(
                self.player,
                sleep_id=view["sleep_id"],
                expected_generation=view["generation"],
            )
            self.assertEqual(resumed.continuation, "complete")
            self.assertEqual(int(get_world_clock().tick) - after_pause, 7200 - 37)
        finally:
            if original is not None:
                _EVENT_SOURCES["shop_hours"] = original

    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_party_choice_releases_control_and_enters_every_present_member(self):
        sleeper = self._companion("沉睡者")
        awake = self._companion("清醒同伴")
        enter_possession(self.player, sleeper)
        enter_sleep(sleeper, mode="duration", seconds=600)
        before = int(get_world_clock().tick)
        begin_all_party_sleep(sleeper, session=self.session)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertIsNone(current_possession(self.player))
        for member in (self.player, sleeper, awake):
            self.assertIs(
                read_fatigue_state(member).posture, SleepPosture.VOLUNTARY
            )
            self.assertIsNotNone(read_sleep_receipt(member))

    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_party_release_fault_restores_every_sleep_and_control_surface(self):
        sleeper = self._companion("沉睡者")
        enter_possession(self.player, sleeper)
        enter_sleep(sleeper, mode="duration", seconds=600)
        before_tick = int(get_world_clock().tick)
        with patch(
            "world.rules.sleep_control.release_possession",
            side_effect=PossessionWriteError("write_failed", "synthetic"),
        ):
            with self.assertRaises(PossessionWriteError):
                begin_all_party_sleep(sleeper, session=self.session)
        self.assertEqual(int(get_world_clock().tick), before_tick)
        self.assertEqual(current_possession(self.player)["npc_dbid"], int(sleeper.pk))
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertIs(
            read_fatigue_state(sleeper).posture, SleepPosture.VOLUNTARY
        )


def answer_sleep_dream_for(actor, view, decision):
    from server.dream_service import answer_sleep_dream

    return answer_sleep_dream(
        actor,
        decision=decision,
        sleep_id=view["sleep_id"],
        revision=view["revision"],
        generation=view["generation"],
    )
