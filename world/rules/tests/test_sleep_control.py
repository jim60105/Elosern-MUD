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
    authorize_owner_sleep_continuation,
    continue_owner_sleep,
    decline_owner_sleep_dream,
    enter_sleep,
    owner_sleep_view_state,
    resume_pending_owner_continuation,
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
    def test_a_new_control_generation_invalidates_the_old_open_dream(self):
        companion = self._companion("同伴")
        enter_sleep(self.player, mode="duration", seconds=600)
        view = owner_sleep_view_state(self.player)
        result = answer_sleep_dream_for(self.player, view, "enter")
        self.assertEqual(result["outcome"], "success")
        self.assertIsNotNone(associated_session(self.player))
        enter_possession(self.player, companion)
        release_possession(self.player, npc=companion, reason="handback")
        self.assertIsNone(associated_session(self.player))
        fresh = owner_sleep_view_state(self.player)
        self.assertTrue(fresh["pending"])

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
        "dream-sleep-surface::dream-departure-never-settles-sleep-again"
    )
    def test_departure_intent_commits_without_time_then_resumes_once(self):
        entry = enter_sleep(self.player, mode="duration", seconds=600)
        before = int(get_world_clock().tick)
        authorized = authorize_owner_sleep_continuation(
            self.player,
            sleep_id=entry.sleep_id,
            revision=0,
            generation=read_sleep_view_generation(self.player),
        )
        self.assertIsNotNone(authorized)
        self.assertEqual(int(get_world_clock().tick), before)
        resumed = resume_pending_owner_continuation(self.player)
        self.assertIsNotNone(resumed)
        self.assertEqual(int(get_world_clock().tick) - before, 600)
        self.assertEqual(resumed.continuation, "complete")
        self.assertIsNone(resume_pending_owner_continuation(self.player))

    @covers_requirement(
        "time-skip-commands::owner-targeted-sleep-continuation-preserves-skip-safety"
    )
    def test_completed_owner_operation_replays_durably_after_restart(self):
        from world.rules import time_skip as time_skip_module

        enter_sleep(self.player, mode="duration", seconds=600)
        result = continue_owner_sleep(
            self.player,
            operation_id="restart-complete",
            expected_generation=read_sleep_view_generation(self.player),
        )
        self.assertEqual(result.continuation, "complete")
        after = int(get_world_clock().tick)
        time_skip_module._RESULT_LEDGER.clear()
        replay = continue_owner_sleep(
            self.player,
            operation_id="restart-complete",
            expected_generation=read_sleep_view_generation(self.player),
        )
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.elapsed_seconds, result.elapsed_seconds)
        self.assertEqual(int(get_world_clock().tick), after)

    @covers_requirement(
        "time-skip-commands::owner-targeted-sleep-continuation-preserves-skip-safety"
    )
    def test_paused_owner_operation_replays_durably_after_restart(self):
        from world.rules import time_skip as time_skip_module

        original = _EVENT_SOURCES.get("shop_hours")
        register_event_source(
            "shop_hours",
            lambda start, end: [
                ScheduledEvent("synthetic_interactive", end, {}, interactive=True)
            ],
            next_boundary=lambda start, end: start + 37,
        )
        try:
            enter_sleep(self.player, mode="duration", seconds=600)
            paused = continue_owner_sleep(
                self.player,
                operation_id="restart-paused",
                expected_generation=read_sleep_view_generation(self.player),
            )
            self.assertEqual(paused.continuation, "paused")
            after = int(get_world_clock().tick)
            time_skip_module._RESULT_LEDGER.clear()
            replay = continue_owner_sleep(
                self.player,
                operation_id="restart-paused",
                expected_generation=read_sleep_view_generation(self.player),
            )
            self.assertTrue(replay.replayed)
            self.assertTrue(replay.interrupted)
            self.assertEqual(int(get_world_clock().tick), after)
        finally:
            if original is not None:
                _EVENT_SOURCES["shop_hours"] = original
            else:
                _EVENT_SOURCES.pop("shop_hours", None)

    @covers_requirement(
        "time-skip-commands::interruptible-skips-stop-at-the-earliest-relevant-boundary"
    )
    def test_sleep_continue_does_not_resume_past_its_own_interactive_pause(self):
        from commands.skip import CmdSleep

        original = _EVENT_SOURCES.get("shop_hours")
        register_event_source(
            "shop_hours",
            lambda start, end: [
                ScheduledEvent("synthetic_interactive", end, {}, interactive=True)
            ],
            next_boundary=lambda start, end: start + 37,
        )
        try:
            enter_sleep(self.player, mode="duration", seconds=600)
            before = int(get_world_clock().tick)
            command = CmdSleep()
            command.caller = self.player
            command.session = self.session
            command.args = "continue"
            command.func()
            self.assertEqual(int(get_world_clock().tick) - before, 37)
            view = owner_sleep_view_state(self.player)
            self.assertFalse(view["pending"])
            self.assertEqual(view["continuation"], "paused")
        finally:
            if original is not None:
                _EVENT_SOURCES["shop_hours"] = original
            else:
                _EVENT_SOURCES.pop("shop_hours", None)

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
            else:
                _EVENT_SOURCES.pop("shop_hours", None)

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
        before_receipt = read_sleep_receipt(sleeper)
        before_tick = int(get_world_clock().tick)
        real_release = release_possession

        def release_then_fail(*args, **kwargs):
            real_release(*args, **kwargs)
            raise PossessionWriteError("write_failed", "synthetic after release")

        with patch(
            "world.rules.sleep_control.release_possession",
            side_effect=release_then_fail,
        ):
            with self.assertRaises(PossessionWriteError):
                begin_all_party_sleep(sleeper, session=self.session)
        self.assertEqual(int(get_world_clock().tick), before_tick)
        self.assertEqual(current_possession(self.player)["npc_dbid"], int(sleeper.pk))
        self.assertIs(self.session.puppet, sleeper)
        self.assertEqual(getattr(sleeper.db, "possessed_by", None), int(self.player.pk))
        self.assertIs(sleeper.location, self.room1)
        self.assertIn("puppet:", sleeper.locks.get("puppet") or "")
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertIs(
            read_fatigue_state(sleeper).posture, SleepPosture.VOLUNTARY
        )
        self.assertEqual(read_sleep_receipt(sleeper).sleep_id, before_receipt.sleep_id)

    @covers_requirement(
        "time-skip-commands::explicit-party-sleep-selects-present-effective-bodies-atomically"
    )
    def test_party_duration_is_admissible_at_full_recovery(self):
        companion = self._companion("同伴")
        for member in (self.player, companion):
            write_fatigue_state(member, 360000, SleepPosture.AWAKE)
        before = int(get_world_clock().tick)
        begin_all_party_sleep(
            self.player, mode="duration", seconds=7200, session=self.session
        )
        self.assertEqual(int(get_world_clock().tick), before)
        for member in (self.player, companion):
            receipt = read_sleep_receipt(member)
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt.target_tick, before + 7200)
            self.assertIs(
                read_fatigue_state(member).posture, SleepPosture.VOLUNTARY
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


class CampingConsentTests(EvenniaTest):
    """Entry-time dream consent commits with the entry or not at all."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self._body(self.player)
        self.player.location = self.room1
        self.player.save()
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        self._sources = dict(_EVENT_SOURCES)
        _EVENT_SOURCES.clear()
        self.addCleanup(_EVENT_SOURCES.update, self._sources)
        self.addCleanup(_EVENT_SOURCES.clear)

    @staticmethod
    def _body(body):
        body.race = "human"
        body.apply_race_baseline()
        for key in ("hp", "mp", "sp"):
            gauge = getattr(body.traits, key)
            gauge.current = gauge.max
            gauge.rate = 0.0

    def _companion(self, key, reserve=180000):
        npc = create_object(NPC, key=key, location=self.room1)
        self._body(npc)
        join_party(npc, self.player)
        write_fatigue_state(npc, reserve, SleepPosture.AWAKE)
        return npc

    @staticmethod
    def _state(*bodies):
        return {
            int(body.pk): sorted(
                (attr.db_key, attr.db_category or "", repr(attr.value))
                for attr in body.attributes.all()
            )
            for body in bodies
        }

    def _commit(self, actor, **kwargs):
        from world.rules.camping import commit_sleep_entry

        values = {"scope": "party", "mode": "duration", "seconds": 3600, "operation_id": "op-consent"}
        values.update(kwargs)
        return commit_sleep_entry(actor, **values)

    def test_entry_consent_and_rollback(self):
        from world.rules.sleep_receipt import (
            CONTINUATION_NONE,
            DECISION_DECLINED,
            DECISION_ENTERED,
            read_sleep_view_decision,
        )
        from world.rules.time_skip import SleepRefused

        companion = self._companion("同伴")
        tick = int(get_world_clock().tick)

        # Self-only duration opt-in: the owner enters and the dream opens at
        # zero time without a question; the awake companion is untouched.
        before_companion = self._state(companion)
        result = self._commit(self.player, scope="self", answer="enter", operation_id="op-self")
        self.assertTrue(result["dream_entered"])
        self.assertEqual(int(get_world_clock().tick), tick)
        receipt = read_sleep_receipt(self.player)
        self.assertEqual(receipt.target_tick, tick + 3600)
        self.assertEqual(read_sleep_view_decision(self.player)["decision"], DECISION_ENTERED)
        self.assertFalse(owner_sleep_view_state(self.player)["pending"])
        self.assertIsNotNone(associated_session(self.player))
        self.assertEqual(self._state(companion), before_companion)

    def test_party_answers_and_question_policy(self):
        from world.rules.sleep_receipt import (
            CONTINUATION_NONE,
            DECISION_DECLINED,
            read_sleep_view_decision,
        )

        companion = self._companion("同伴")
        tick = int(get_world_clock().tick)
        # Ordinary absent/false: no answer, the question remains.
        result = self._commit(self.player, answer=None, operation_id="op-plain")
        self.assertFalse(result["dream_entered"])
        self.assertIsNone(read_sleep_view_decision(self.player))
        self.assertTrue(owner_sleep_view_state(self.player)["pending"])
        # Party/duration parity: both bodies share the explicit deadline.
        for body in (self.player, companion):
            self.assertEqual(read_sleep_receipt(body).target_tick, tick + 3600)
            self.assertEqual(read_sleep_receipt(body).entry_operation_id, "op-plain")

    def test_camp_decline_and_full_owner(self):
        from world.rules.sleep_receipt import (
            CONTINUATION_NONE,
            DECISION_DECLINED,
            read_sleep_view_decision,
        )

        companion = self._companion("同伴")
        # Camp false declines explicitly: no later question, no continuation
        # authorization is written.
        self._commit(self.player, answer="decline", operation_id="op-decline")
        decision = read_sleep_view_decision(self.player)
        self.assertEqual(decision["decision"], DECISION_DECLINED)
        self.assertEqual(decision["continuation"], CONTINUATION_NONE)
        self.assertFalse(owner_sleep_view_state(self.player)["pending"])
        self.assertIs(read_fatigue_state(companion).posture, SleepPosture.VOLUNTARY)

    def test_full_owner_camp_fabricates_no_answer(self):
        from world.rules.sleep_receipt import read_sleep_view_decision

        companion = self._companion("同伴")
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)
        self._commit(self.player, mode="recovery", seconds=None, answer="decline", operation_id="op-full")
        self.assertIsNone(read_sleep_receipt(self.player))
        self.assertIsNone(read_sleep_view_decision(self.player))
        self.assertIsNone(owner_sleep_view_state(self.player))
        self.assertIs(read_fatigue_state(companion).posture, SleepPosture.VOLUNTARY)

    def test_ineligible_or_failed_consent_writes_nothing(self):
        from server import dream_service
        from world.narrative import dream_surface
        from world.rules.time_skip import SleepRefused

        companion = self._companion("同伴")
        tick = int(get_world_clock().tick)
        generation = read_sleep_view_generation(self.player)

        def unchanged(before):
            self.assertEqual(self._state(self.player, companion), before)
            self.assertEqual(int(get_world_clock().tick), tick)
            self.assertIsNone(associated_session(self.player))

        # Forced owner: never enters a dream.
        write_fatigue_state(self.player, 0, SleepPosture.FORCED)
        before = self._state(self.player, companion)
        with self.assertRaises(SleepRefused) as caught:
            self._commit(self.player, answer="enter")
        self.assertEqual(caught.exception.code, "dream_not_offerable")
        unchanged(before)
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)

        # Excluded (already recovered) owner under recovery: nothing to enter.
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)
        before = self._state(self.player, companion)
        with self.assertRaises(SleepRefused):
            self._commit(self.player, mode="recovery", seconds=None, answer="enter")
        unchanged(before)
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)

        # Companion possession: the request comes from the possessed body.
        enter_possession(self.player, companion)
        before = self._state(self.player, companion)
        with self.assertRaises(SleepRefused):
            self._commit(companion, answer="enter")
        self.assertIsNotNone(current_possession(self.player))
        unchanged(before)
        release_possession(self.player, npc=companion, reason="handback")

        # An injected answer failure after the entry wrote rolls back the
        # whole entry, including the cached physiology and the view identity.
        before = self._state(self.player, companion)
        generation = read_sleep_view_generation(self.player)
        with patch.object(
            dream_surface,
            "enter_for_owner",
            side_effect=DreamEntryError("dream_stale_sleep", "stale"),
        ):
            with self.assertRaises(SleepRefused):
                self._commit(self.player, answer="enter", operation_id="op-fail")
        unchanged(before)
        self.assertEqual(read_sleep_view_generation(self.player), generation)
        self.assertIs(read_fatigue_state(companion).posture, SleepPosture.AWAKE)

        # A stale decline during revalidation rolls back the camp entry too.
        before = self._state(self.player, companion)
        with patch(
            "world.rules.time_skip.record_owner_sleep_decision",
            side_effect=SleepRefused("stale_sleep", "stale"),
        ):
            with self.assertRaises(SleepRefused):
                self._commit(self.player, answer="decline", operation_id="op-stale")
        unchanged(before)
        self.assertIsNotNone(dream_service)
