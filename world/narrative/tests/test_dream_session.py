"""Synthetic behavior tests for durable six-exchange dream session accounting.

Everything here is deterministic and offline: synthetic actors, a fixed clock,
no model or image service. Substantive tests are annotated against the
canonical main requirement ids they establish, including the
``dream-session-lifecycle`` ids published when the delta spec synced.
"""

from __future__ import annotations

import json
import types
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.ai.profiles import LAYER_NAMES, default_profiles
from world.narrative.authoring import (
    REASON_MESSAGES,
    DirectionValidationError,
    draft_is_confirmed,
    get_draft,
)
from world.narrative.dream_session import (
    MAX_EXCHANGES,
    MAX_RENDERED_INPUT_CHARS,
    DreamExchangeConflictError,
    DreamInputRejected,
    DreamOutstandingTurnError,
    DreamSessionAccessError,
    DreamSessionClosedError,
    DreamSessionNotDraftedError,
    abandon_turn,
    awaken_session,
    begin_turn,
    choices,
    confirm_session,
    get_session,
    list_exchanges,
    list_open_sessions,
    open_session,
    open_session_for,
    preserve_draft,
    progress,
    remaining_exchanges,
    settle_exchange,
)
from world.narrative.models import (
    CreativeRequest,
    DreamExchange,
    DreamSession,
    MemoryRecord,
    NarrativeEvent,
    ProjectionProgress,
)
from world.rules.clock import get_world_clock


def new_story_direction(**overrides):
    """A complete, valid new-story direction; overrides replace whole fields."""
    direction = {
        "summary": "合成夢境方向：在無名港尋找失落的鐘聲。",
        "themes": ["合成主題"],
        "atmosphere": ["合成氛圍"],
        "participants": [],
        "emphasis": ["合成重點"],
        "exclusions": ["合成排除"],
        "kind": "new_story",
        "thread_id": None,
        "effects": [],
        "revisions": [],
    }
    direction.update(overrides)
    return direction


class DreamSessionTestCase(EvenniaTest):
    """Shared synthetic actors, a fixed clock, and exchange helpers."""

    def setUp(self):
        super().setUp()
        self.owner = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="Synthetic dream owner",
            location=self.room1,
        )
        self.other = create_object(
            "typeclasses.characters.PlayerCharacter", key="Synthetic other dream owner"
        )
        self.clock = get_world_clock()
        self.clock._persist(100)
        self.clock.tick = 100

    @property
    def owner_id(self) -> str:
        return str(self.owner.pk)

    @property
    def other_id(self) -> str:
        return str(self.other.pk)

    def open(self, **kwargs) -> DreamSession:
        return open_session(self.owner_id, tick=100, **kwargs)

    def complete_exchanges(self, session: DreamSession, count: int) -> list[DreamExchange]:
        """Deliver ``count`` validated exchanges through the public operations."""
        exchanges = []
        for index in range(count):
            turn = begin_turn(
                session.session_id,
                self.owner_id,
                f"合成訊息 {index}",
                submission_id=f"submission_{index}",
                tick=100 + index,
            )
            exchanges.append(
                settle_exchange(
                    session.session_id,
                    self.owner_id,
                    turn.submission_id,
                    f"delivery_{index}",
                    response_ref=f"response:{index}",
                    tick=100 + index,
                )
            )
        return exchanges

    def character_attribute_snapshot(self):
        return sorted(
            (attribute.db_key, repr(attribute.value))
            for attribute in self.owner.attributes.all()
        )


class DreamSessionBudgetTests(DreamSessionTestCase):
    """Only a successfully delivered validated response consumes an exchange."""

    @covers_requirement("dream-session-lifecycle::only-completed-exchanges-consume-the-six-exchange-budget")
    def test_retry_and_duplicate_do_not_consume_twice(self):
        session = self.open()
        first = begin_turn(
            session.session_id,
            self.owner_id,
            "合成重試訊息",
            submission_id="submission_retry",
            tick=100,
        )
        # A transport retry re-submits the same identity and its saved input.
        again = begin_turn(
            session.session_id,
            self.owner_id,
            "合成重試訊息",
            submission_id="submission_retry",
            tick=101,
        )
        self.assertEqual(first.submission_id, again.submission_id)
        self.assertEqual(again.progress.completed, 0)

        delivered = settle_exchange(
            session.session_id,
            self.owner_id,
            "submission_retry",
            "delivery_retry",
            response_ref="response:retry",
            tick=102,
        )
        self.assertEqual(delivered.exchange_number, 1)

        # Replaying the same delivery identity after a restart is a no-op.
        replayed = settle_exchange(
            session.session_id,
            self.owner_id,
            "submission_retry",
            "delivery_retry",
            response_ref="response:retry",
            tick=103,
        )
        self.assertEqual(replayed.pk, delivered.pk)
        # A duplicate submission under a fresh delivery identity still consumes
        # nothing: the first delivered response stands.
        duplicate = settle_exchange(
            session.session_id,
            self.owner_id,
            "submission_retry",
            "delivery_retry_second",
            response_ref="response:retry_second",
            tick=104,
        )
        self.assertEqual(duplicate.pk, delivered.pk)
        self.assertEqual(DreamExchange.objects.filter(session=session).count(), 1)
        self.assertEqual(
            get_session(session.session_id, self.owner_id).completed_exchanges, 1
        )

    @covers_requirement("dream-session-lifecycle::only-completed-exchanges-consume-the-six-exchange-budget")
    def test_reconnect_after_five_keeps_the_count_and_remaining(self):
        session = self.open(session_id="dream_session_reconnect")
        self.complete_exchanges(session, 5)
        resumed = open_session_for(self.owner_id)
        self.assertEqual(resumed.pk, session.pk)
        self.assertEqual(resumed.completed_exchanges, 5)
        self.assertEqual(remaining_exchanges(resumed), 1)
        view = progress(resumed)
        self.assertTrue(view.converging)
        self.assertFalse(view.at_cap)
        self.assertTrue(view.free_text_allowed)

    @covers_requirement("dream-session-lifecycle::only-completed-exchanges-consume-the-six-exchange-budget")
    def test_oversized_message_rejects_without_generation_or_consumption(self):
        session = self.open()
        with self.assertRaises(DreamInputRejected) as caught:
            begin_turn(
                session.session_id,
                self.owner_id,
                "字" * (MAX_RENDERED_INPUT_CHARS + 1),
                submission_id="submission_oversized",
                tick=100,
            )
        self.assertEqual(caught.exception.code, "oversized_input")
        stored = get_session(session.session_id, self.owner_id)
        self.assertEqual(stored.completed_exchanges, 0)
        self.assertEqual(stored.pending_submission_id, "")
        self.assertEqual(stored.saved_input, "")
        self.assertEqual(stored.revision, 1)
        self.assertEqual(DreamExchange.objects.count(), 0)

    def test_blank_message_rejects_without_consumption(self):
        session = self.open()
        with self.assertRaises(DreamInputRejected) as caught:
            begin_turn(
                session.session_id,
                self.owner_id,
                "   ",
                submission_id="submission_blank",
                tick=100,
            )
        self.assertEqual(caught.exception.code, "empty_input")
        stored = get_session(session.session_id, self.owner_id)
        self.assertEqual(stored.completed_exchanges, 0)
        self.assertEqual(stored.pending_submission_id, "")

    def test_input_bound_is_independent_and_exact(self):
        session = self.open()
        turn = begin_turn(
            session.session_id,
            self.owner_id,
            "字" * MAX_RENDERED_INPUT_CHARS,
            submission_id="submission_bound",
            tick=100,
        )
        self.assertEqual(turn.message_length, MAX_RENDERED_INPUT_CHARS)
        self.assertEqual(
            get_session(session.session_id, self.owner_id).saved_input,
            "字" * MAX_RENDERED_INPUT_CHARS,
        )

    @covers_requirement("dream-session-lifecycle::convergence-and-exit-require-explicit-choices")
    def test_sixth_completes_and_free_text_stops(self):
        session = self.open()
        self.complete_exchanges(session, MAX_EXCHANGES)
        final = get_session(session.session_id, self.owner_id)
        view = progress(final)
        self.assertEqual(view.completed, MAX_EXCHANGES)
        self.assertEqual(view.remaining, 0)
        self.assertTrue(view.at_cap)
        self.assertTrue(view.converging)
        self.assertFalse(view.free_text_allowed)
        offered = choices(final)
        self.assertFalse(offered.can_input)
        self.assertTrue(offered.can_confirm)
        self.assertTrue(offered.can_preserve_draft)
        self.assertTrue(offered.can_awaken)
        with self.assertRaises(DreamSessionClosedError):
            begin_turn(
                session.session_id,
                self.owner_id,
                "第七次交流",
                submission_id="submission_seven",
                tick=200,
            )
        self.assertEqual(DreamExchange.objects.filter(session=session).count(), 6)
        self.assertEqual(
            get_session(session.session_id, self.owner_id).completed_exchanges, 6
        )

    @covers_requirement("dream-session-lifecycle::convergence-and-exit-require-explicit-choices")
    def test_exit_before_cap_offers_same_choices_and_schedules_nothing(self):
        session = self.open()
        self.complete_exchanges(session, 2)
        offered = choices(get_session(session.session_id, self.owner_id))
        self.assertTrue(offered.can_input)
        self.assertTrue(offered.can_confirm)
        self.assertTrue(offered.can_preserve_draft)
        self.assertTrue(offered.can_awaken)
        draft = preserve_draft(
            session.session_id, self.owner_id, new_story_direction(), tick=200
        )
        self.assertEqual(CreativeRequest.objects.count(), 0)
        self.assertFalse(draft_is_confirmed(get_draft(draft.draft_id, self.owner_id)))

    def test_a_second_different_turn_is_refused_while_one_is_outstanding(self):
        session = self.open()
        begin_turn(
            session.session_id,
            self.owner_id,
            "合成第一則訊息",
            submission_id="submission_first",
            tick=100,
        )
        with self.assertRaises(DreamOutstandingTurnError):
            begin_turn(
                session.session_id,
                self.owner_id,
                "合成第二則訊息",
                submission_id="submission_second",
                tick=101,
            )
        with self.assertRaises(DreamOutstandingTurnError):
            begin_turn(
                session.session_id,
                self.owner_id,
                "合成不同內容",
                submission_id="submission_first",
                tick=102,
            )
        self.assertEqual(DreamExchange.objects.count(), 0)


class DreamSessionFailureTests(DreamSessionTestCase):
    """Failure and restart preserve progress and never settle twice."""

    @covers_requirement("dream-session-lifecycle::failures-preserve-progress-and-permit-offline-awakening")
    def test_failure_after_five_preserves_count_and_allows_offline_end(self):
        session = self.open()
        self.complete_exchanges(session, 5)
        begin_turn(
            session.session_id,
            self.owner_id,
            "合成未完成的訊息",
            submission_id="submission_failing",
            tick=200,
        )
        # The generation/transport fails: the turn is abandoned, never settled.
        view = abandon_turn(
            session.session_id,
            self.owner_id,
            "submission_failing",
            reason="transport_failure",
            tick=201,
        )
        self.assertEqual(view.completed, 5)
        stored = get_session(session.session_id, self.owner_id)
        self.assertEqual(stored.pending_submission_id, "")
        # The player's unfinished message stays recoverable for resume.
        self.assertEqual(stored.saved_input, "合成未完成的訊息")

        disabled = default_profiles()
        for layer in LAYER_NAMES:
            disabled[layer]["enabled"] = False
        with (
            override_settings(LLM_PROFILES=disabled),
            patch("socket.socket", side_effect=AssertionError("no transport")),
        ):
            draft = preserve_draft(
                session.session_id, self.owner_id, new_story_direction(), tick=202
            )
            ending = awaken_session(session.session_id, self.owner_id, tick=203)
        self.assertEqual(ending.completed, 5)
        self.assertEqual(CreativeRequest.objects.count(), 0)
        self.assertFalse(draft_is_confirmed(get_draft(draft.draft_id, self.owner_id)))
        self.assertEqual(
            get_session(session.session_id, self.owner_id).state, "ended"
        )

    @covers_requirement("dream-session-lifecycle::failures-preserve-progress-and-permit-offline-awakening")
    def test_restart_during_delivery_replays_without_a_second_exchange(self):
        session = self.open()
        begin_turn(
            session.session_id,
            self.owner_id,
            "合成重播訊息",
            submission_id="submission_restart",
            tick=100,
        )
        first = settle_exchange(
            session.session_id,
            self.owner_id,
            "submission_restart",
            "delivery_restart",
            response_ref="response:restart",
            tick=101,
        )
        # After a restart the same committed delivery identity is replayed.
        replayed = settle_exchange(
            session.session_id,
            self.owner_id,
            "submission_restart",
            "delivery_restart",
            response_ref="response:restart",
            tick=999,
        )
        self.assertEqual(replayed.pk, first.pk)
        self.assertEqual(replayed.exchange_number, 1)
        self.assertEqual(DreamExchange.objects.filter(session=session).count(), 1)
        self.assertEqual(
            get_session(session.session_id, self.owner_id).completed_exchanges, 1
        )

    def test_settle_requires_the_outstanding_turn(self):
        session = self.open()
        with self.assertRaises(DreamExchangeConflictError):
            settle_exchange(
                session.session_id,
                self.owner_id,
                "submission_missing",
                "delivery_missing",
                tick=100,
            )
        begin_turn(
            session.session_id,
            self.owner_id,
            "合成進行中的訊息",
            submission_id="submission_active",
            tick=100,
        )
        with self.assertRaises(DreamExchangeConflictError):
            settle_exchange(
                session.session_id,
                self.owner_id,
                "submission_other",
                "delivery_other",
                tick=101,
            )
        self.assertEqual(DreamExchange.objects.count(), 0)

    def test_delivery_identity_cannot_attach_to_a_different_exchange(self):
        session = self.open()
        self.complete_exchanges(session, 1)
        other_session = open_session(self.other_id, session_id="dream_other_owner", tick=100)
        begin_turn(
            other_session.session_id,
            self.other_id,
            "合成其他擁有者訊息",
            submission_id="submission_other_owner",
            tick=100,
        )
        with self.assertRaises(DreamExchangeConflictError):
            settle_exchange(
                other_session.session_id,
                self.other_id,
                "submission_other_owner",
                "delivery_0",
                tick=101,
            )

    @covers_requirement("dream-session-lifecycle::failures-preserve-progress-and-permit-offline-awakening")
    def test_awaken_is_idempotent_and_ends_without_a_model(self):
        session = self.open()
        self.complete_exchanges(session, 2)
        first = awaken_session(session.session_id, self.owner_id, tick=200)
        revision = get_session(session.session_id, self.owner_id).revision
        second = awaken_session(session.session_id, self.owner_id, tick=300)
        self.assertEqual(first, second)
        self.assertEqual(second.completed, 2)
        self.assertEqual(
            get_session(session.session_id, self.owner_id).revision, revision
        )

    def test_owner_scoped_reads_and_writes(self):
        session = self.open()
        with self.assertRaises(DreamSessionAccessError):
            get_session(session.session_id, self.other_id)
        with self.assertRaises(DreamSessionAccessError):
            begin_turn(
                session.session_id,
                self.other_id,
                "合成他人訊息",
                submission_id="submission_intruder",
                tick=100,
            )
        with self.assertRaises(DreamSessionAccessError):
            awaken_session(session.session_id, self.other_id, tick=100)
        self.assertIsNone(open_session_for(self.other_id))
        self.assertEqual(list_open_sessions(self.other_id), [])
        with self.assertRaises(DreamSessionAccessError):
            list_exchanges(session.session_id, self.other_id)

    def test_multiple_open_sessions_are_all_visible_and_resume_picks_newest(self):
        older = self.open(session_id="dream_session_older")
        newer = self.open(session_id="dream_session_newer")
        self.assertEqual(
            [row.pk for row in list_open_sessions(self.owner_id)], [older.pk, newer.pk]
        )
        self.assertEqual(open_session_for(self.owner_id).pk, newer.pk)


class DreamSessionConfirmationTests(DreamSessionTestCase):
    """Confirm/draft choices are deterministic, offline and submit once."""

    @covers_requirement("dream-authoring::explicit-version-confirmation-submits-once")
    def test_confirmation_submits_once_across_reconnect(self):
        session = self.open(session_id="dream_session_confirm")
        self.complete_exchanges(session, MAX_EXCHANGES)
        draft = preserve_draft(
            session.session_id, self.owner_id, new_story_direction(), tick=200
        )
        first = confirm_session(session.session_id, self.owner_id, tick=201)
        self.assertEqual(first.draft_id, draft.pk)
        # A reconnect re-confirms the same session and returns the same request.
        again = confirm_session(session.session_id, self.owner_id, tick=900)
        self.assertEqual(again.pk, first.pk)
        self.assertEqual(CreativeRequest.objects.count(), 1)
        stored = get_session(session.session_id, self.owner_id)
        self.assertEqual(stored.state, "ended")
        self.assertEqual(stored.outcome, "confirmed")
        self.assertEqual(stored.request_key, first.submission_key)
        self.assertEqual(stored.pending_submission_id, "")

    @covers_requirement("dream-authoring::explicit-version-confirmation-submits-once")
    def test_confirm_with_direction_saves_and_confirms_in_one_step(self):
        session = self.open()
        self.complete_exchanges(session, 2)
        request = confirm_session(
            session.session_id,
            self.owner_id,
            direction=new_story_direction(summary="合成確認方向。"),
            tick=200,
        )
        self.assertEqual(request.version, 1)
        self.assertEqual(CreativeRequest.objects.count(), 1)
        self.assertEqual(
            get_session(session.session_id, self.owner_id).outcome, "confirmed"
        )

    def test_invalid_direction_keeps_the_session_open_and_unconfirmed(self):
        session = self.open()
        with self.assertRaises(DirectionValidationError):
            confirm_session(
                session.session_id,
                self.owner_id,
                direction=new_story_direction(effects=["clue"]),
                tick=200,
            )
        stored = get_session(session.session_id, self.owner_id)
        self.assertEqual(stored.state, "open")
        self.assertEqual(stored.outcome, "")
        self.assertEqual(stored.request_key, "")
        self.assertEqual(CreativeRequest.objects.count(), 0)
        # The refused direction remains an unconfirmed private draft.
        draft = get_draft(stored.draft_id, self.owner_id)
        self.assertFalse(draft_is_confirmed(draft))

    def test_confirm_without_a_draft_is_refused(self):
        session = self.open()
        with self.assertRaises(DreamSessionNotDraftedError):
            confirm_session(session.session_id, self.owner_id, tick=100)
        self.assertEqual(CreativeRequest.objects.count(), 0)
        self.assertEqual(
            get_session(session.session_id, self.owner_id).state, "open"
        )

    def test_confirmation_is_offline_and_opens_no_transport(self):
        import world.narrative.dream_session as session_module

        disabled = default_profiles()
        for layer in LAYER_NAMES:
            disabled[layer]["enabled"] = False
        session = self.open()
        with (
            override_settings(LLM_PROFILES=disabled),
            patch("socket.socket", side_effect=AssertionError("no transport")),
        ):
            preserve_draft(
                session.session_id, self.owner_id, new_story_direction(), tick=100
            )
            request = confirm_session(session.session_id, self.owner_id, tick=101)
        self.assertEqual(request.validation_status, "valid")

        # The session boundary is generation-free by construction.
        bound_modules = {
            value.__name__
            for value in vars(session_module).values()
            if isinstance(value, types.ModuleType)
        }
        self.assertEqual(
            sorted(name for name in bound_modules if name.startswith("world.ai")), []
        )

    @covers_requirement("dream-authoring::creative-discussion-remains-private-authoring-data")
    def test_session_data_never_becomes_cognition_or_a_character_effect(self):
        session = self.open()
        self.complete_exchanges(session, 3)
        before = self.character_attribute_snapshot()
        preserve_draft(session.session_id, self.owner_id, new_story_direction(), tick=200)
        after = self.character_attribute_snapshot()
        self.assertEqual(before, after)
        self.assertEqual(MemoryRecord.objects.count(), 0)
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        self.assertEqual(ProjectionProgress.objects.count(), 0)

    def test_settle_clears_saved_input_after_the_exchange_is_evidence(self):
        session = self.open()
        begin_turn(
            session.session_id,
            self.owner_id,
            "合成訊息內容",
            submission_id="submission_clear",
            tick=100,
        )
        settle_exchange(
            session.session_id,
            self.owner_id,
            "submission_clear",
            "delivery_clear",
            tick=101,
        )
        stored = get_session(session.session_id, self.owner_id)
        self.assertEqual(stored.saved_input, "")
        self.assertEqual(stored.pending_submission_id, "")


class DreamSessionImmutabilityTests(DreamSessionTestCase):
    """Counted evidence and session identity are durable, never rewritten."""

    def test_session_identity_is_immutable_and_rows_cannot_be_bulk_rewritten(self):
        session = self.open()
        session.session_id = "changed"
        with self.assertRaises(ValueError):
            session.save()
        with self.assertRaises(ValueError):
            DreamSession.objects.filter(pk=session.pk).update(completed_exchanges=5)
        with self.assertRaises(ValueError):
            DreamSession.objects.filter(pk=session.pk).delete()
        with self.assertRaises(ValueError):
            session.delete()

    def test_exchange_rows_are_append_only(self):
        session = self.open()
        self.complete_exchanges(session, 1)
        exchange = DreamExchange.objects.get(session=session)
        with self.assertRaises(ValueError):
            DreamExchange.objects.filter(pk=exchange.pk).update(response_ref="changed")
        with self.assertRaises(ValueError):
            DreamExchange.objects.filter(pk=exchange.pk).delete()
        with self.assertRaises(ValueError):
            exchange.save()
        exchange.tick = 999
        with self.assertRaises(ValueError):
            exchange.save()
        with self.assertRaises(ValueError):
            exchange.delete()

    def test_unique_constraints_backstop_a_second_exchange(self):
        session = self.open()
        self.complete_exchanges(session, 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            DreamExchange.objects.bulk_create(
                [
                    DreamExchange(
                        delivery_id="delivery_duplicate_number",
                        session=session,
                        owner_id=self.owner_id,
                        exchange_number=1,
                        submission_id="submission_duplicate_number",
                        tick=100,
                    )
                ]
            )
        self.assertEqual(DreamExchange.objects.filter(session=session).count(), 1)


class DreamSessionObservabilityTests(DreamSessionTestCase):
    """Boundary events carry identifiers, counts and codes only."""

    @covers_requirement("observability-logging::facade-is-the-sole-game-code-log-entry-point")
    def test_boundary_events_never_carry_player_prose(self):
        import world.narrative.dream_session as session_module

        info_calls: list[tuple[str, dict]] = []
        warn_calls: list[tuple[str, dict]] = []

        def capture_info(event, *, context=None, exc=None):
            info_calls.append((event, dict(context or {})))

        def capture_warn(event, *, context=None, exc=None):
            warn_calls.append((event, dict(context or {})))

        message = "不應寫入日誌的合成夢境訊息。"
        direction = new_story_direction(summary=message)
        with (
            patch.object(session_module, "log_info", side_effect=capture_info),
            patch.object(session_module, "log_warn", side_effect=capture_warn),
            self.captureOnCommitCallbacks(execute=True),
        ):
            session = open_session(
                self.owner_id, session_id="dream_session_logging", tick=100
            )
            begin_turn(
                session.session_id,
                self.owner_id,
                message,
                submission_id="submission_logging",
                tick=100,
            )
            settle_exchange(
                session.session_id,
                self.owner_id,
                "submission_logging",
                "delivery_logging",
                response_ref="response:logging",
                tick=101,
            )
            with self.assertRaises(DreamInputRejected):
                begin_turn(
                    session.session_id,
                    self.owner_id,
                    "字" * (MAX_RENDERED_INPUT_CHARS + 1),
                    submission_id="submission_oversized_logging",
                    tick=102,
                )
            preserve_draft(session.session_id, self.owner_id, direction, tick=103)
            confirm_session(session.session_id, self.owner_id, tick=104)

        events = [event for event, _context in info_calls]
        self.assertIn("dream_session_opened", events)
        self.assertIn("dream_session_submission_accepted", events)
        self.assertIn("dream_session_exchange_completed", events)
        self.assertIn("dream_session_draft_preserved", events)
        self.assertIn("dream_session_confirmed", events)
        self.assertEqual(warn_calls[0][0], "dream_session_input_rejected")
        self.assertEqual(warn_calls[0][1]["reason"], "oversized_input")
        for _event, context in (*info_calls, *warn_calls):
            serialized = json.dumps(context, ensure_ascii=False)
            self.assertNotIn(message, serialized)
            self.assertNotIn(REASON_MESSAGES["unauthorized_effects"], serialized)
