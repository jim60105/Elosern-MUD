"""The dispatcher's action-options dialogue trigger firing rules."""
from web.webclient.actions.registry import (
    ActionRegistry,
    ActionSpec,
    build_production_action_registry,
)
from twisted.internet.defer import Deferred, succeed
from types import SimpleNamespace
from tools.spec_traceability import covers_requirement
from web.webclient.actions.dispatcher import (
    CACHE_CAPACITY,
    SequenceState,
    handle_ui_action,
    retire_sequence,
)
import unittest
from ._support import (
    FakeActor,
    FakeSession,
    _coordinator,
    _presenter_registry,
)


class DialogueTriggerTests(unittest.TestCase):
    """The dispatcher fires the action-options dialogue trigger only for a
    successful talk completion, after both sends (action-options-trigger-hooks
    D3); rejected and non-talk completions stay silent."""

    def _session_with_coordinator(self):
        session = FakeSession()
        _coordinator(session)
        session.puppet = FakeActor()
        return session

    def _envelope(self, *, base_revision=None, epoch=None, action_id="proof.noop", request_id="r1", payload=None):
        return {
            "protocol_version": 1,
            "presentation_epoch": epoch or "x" * 22,
            "request_id": request_id,
            "base_revision": base_revision if base_revision is not None else 1,
            "action_id": action_id,
            "payload": payload if payload is not None else {},
        }

    def _talk_registry(self, action_id, adapter):
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id=action_id,
                validate_payload=lambda payload: payload,
                adapter=adapter,
                affected_panels=("status",),
            )
        )
        return registry

    def _traced_session(self):
        session = self._session_with_coordinator()
        order = []
        original_msg = session.msg

        def _msg(**kwargs):
            order.append(tuple(kwargs))
            return original_msg(**kwargs)

        session.msg = _msg
        return session, order

    @covers_requirement(
        "action-options-trigger-hooks::conversation-completion-triggers-a-proposal-after-publication"
    )
    def test_successful_scripted_talk_schedules_once_after_both_sends(self):
        from unittest.mock import patch

        from server import option_proposal_service as service

        session, order = self._traced_session()
        registry = self._talk_registry(
            "explore.talk_scripted",
            lambda actor, payload, session=None: {
                "outcome": "success",
                "code": "talked",
                "message": "店員說：你好。",
                "affected_panels": ("status",),
            },
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        order.clear()  # the snapshot priming send is not part of the trigger sequence
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="explore.talk_scripted",
        )
        calls = []

        def _spy(actor, *, watchers, client=None):
            calls.append((actor, watchers, client))
            order.append(("schedule",))
            return None

        with patch.object(service, "schedule_action_options", side_effect=_spy):
            handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], session.puppet)
        self.assertEqual(len(calls[0][1]), 1)
        self.assertIs(calls[0][1][0][0], session)
        self.assertEqual(calls[0][1][0][1], coordinator.epoch)
        self.assertIsNone(calls[0][2])
        # The scheduling call lands after the update and the result are on the wire.
        self.assertEqual(
            [name for name, in order],
            ["ui_update", "ui_action_result", "schedule"],
            "exactly two sends then the trigger",
        )

    @covers_requirement(
        "action-options-trigger-hooks::conversation-completion-triggers-a-proposal-after-publication"
    )
    def test_successful_freeform_talk_schedules_once_after_both_sends(self):
        from unittest.mock import patch

        from server import option_proposal_service as service

        session, order = self._traced_session()
        held = Deferred()
        registry = self._talk_registry(
            "explore.talk_freeform",
            lambda actor, payload, session=None: held,
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        order.clear()  # the snapshot priming send is not part of the trigger sequence
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="explore.talk_freeform",
            payload={"npc_id": 3, "speech": "你好"},
        )
        calls = []

        def _spy(actor, *, watchers, client=None):
            calls.append((actor, watchers, client))
            order.append(("schedule",))
            return None

        with patch.object(service, "schedule_action_options", side_effect=_spy):
            handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
            self.assertEqual(calls, [], "nothing schedules before the Deferred settles")
            held.callback(
                {"outcome": "success", "code": "talked", "message": "對方回應了你的話。", "affected_panels": ("status",)}
            )

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], session.puppet)
        self.assertEqual(len(calls[0][1]), 1)
        self.assertIs(calls[0][1][0][0], session)
        self.assertEqual(calls[0][1][0][1], coordinator.epoch)
        self.assertEqual(
            [name for name, in order],
            ["ui_update", "ui_action_result", "schedule"],
            "exactly two sends then the trigger",
        )

    def test_rejected_talk_schedules_nothing(self):
        from unittest.mock import patch

        from server import option_proposal_service as service

        session = self._session_with_coordinator()
        registry = self._talk_registry(
            "explore.talk_scripted",
            lambda actor, payload, session=None: {
                "outcome": "rejected",
                "code": "schedule_blocked",
                "message": "對方現在沒空理你。",
            },
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="explore.talk_scripted",
        )
        with patch.object(service, "schedule_action_options") as schedule:
            handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
            schedule.assert_not_called()
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertEqual(results[-1]["ui_action_result"][0][0]["outcome"], "rejected")

    def test_successful_look_schedules_nothing(self):
        from unittest.mock import patch

        from server import option_proposal_service as service

        session = self._session_with_coordinator()
        registry = self._talk_registry(
            "explore.look",
            lambda actor, payload, session=None: {
                "outcome": "success",
                "code": "looked",
                "message": "你仔細打量了一番。",
                "affected_panels": ("status",),
            },
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="explore.look",
        )
        with patch.object(service, "schedule_action_options") as schedule:
            handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
            schedule.assert_not_called()

    def test_scheduling_failure_never_breaks_publication(self):
        from unittest.mock import patch

        from server import option_proposal_service as service

        session, order = self._traced_session()
        registry = self._talk_registry(
            "explore.talk_scripted",
            lambda actor, payload, session=None: {
                "outcome": "success",
                "code": "talked",
                "message": "店員說：你好。",
                "affected_panels": ("status",),
            },
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="explore.talk_scripted",
        )

        def _failing_schedule(*args, **kwargs):
            raise RuntimeError("transport unavailable")

        with patch.object(service, "schedule_action_options", side_effect=_failing_schedule):
            handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())

        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertEqual(results[-1]["ui_action_result"][0][0]["outcome"], "success")
        self.assertFalse(getattr(session.ndb, "elosern_dispatch", None).in_flight)

    def test_raw_success_that_normalizes_to_internal_error_schedules_nothing(self):
        """The trigger gate reads the *normalized* result actually sent to the
        client: a talk completion whose raw outcome is ``success`` but whose
        code/message violates the envelope schema resolves to an internal
        error and must never schedule a proposal."""
        from unittest.mock import patch

        from server import option_proposal_service as service

        session = self._session_with_coordinator()
        registry = self._talk_registry(
            "explore.talk_scripted",
            lambda actor, payload, session=None: {
                "outcome": "success",
                "code": "bad code with spaces",
                "message": "店員說：你好。",
                "affected_panels": ("status",),
            },
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="explore.talk_scripted",
        )
        with patch.object(service, "schedule_action_options") as schedule:
            handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
            schedule.assert_not_called()
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertEqual(results[-1]["ui_action_result"][0][0]["outcome"], "error")

    def test_retired_talk_completion_never_schedules(self):
        from unittest.mock import patch

        from server import option_proposal_service as service

        session = self._session_with_coordinator()
        held = Deferred()
        registry = self._talk_registry(
            "explore.talk_freeform",
            lambda actor, payload, session=None: held,
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="explore.talk_freeform",
            payload={"npc_id": 3, "speech": "你好"},
        )
        with patch.object(service, "schedule_action_options") as schedule:
            handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
            # Puppet change: the sequence is retired before the talk settles.
            from web.webclient.actions.dispatcher import retire_sequence

            coordinator.reset()
            retire_sequence(session)
            held.callback(
                {"outcome": "success", "code": "talked", "message": "對方回應了你的話。", "affected_panels": ("status",)}
            )
            schedule.assert_not_called()
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertFalse(results, "a retired sequence publishes nothing")

if __name__ == "__main__":
    unittest.main()
