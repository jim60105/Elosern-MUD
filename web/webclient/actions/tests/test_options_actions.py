"""Tests for the ``options.dismiss`` action and the unified adapter ABI.

Covers the exact-empty payload validator, the thin eviction adapter (mock the
service boundary — never re-implement the service), the single-publication
rule through the dispatcher completion path, and the per-session isolation of
a dismissal across two windows on one puppet.
"""

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.options import (
    OptionsActionError,
    _dismiss_adapter,
    validate_options_dismiss_payload,
)
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry
from world.rules.clock import get_world_clock


def _unavailable_state(actor, token=1):
    """The exact options state the mocked eviction contract writes."""
    return {
        "owner_actor_id": str(getattr(actor, "pk", "")),
        "fingerprint": None,
        "status": "unavailable",
        "generation_token": token,
        "displayed": None,
    }


class DismissPayloadValidationTests(unittest.TestCase):
    @covers_requirement(
        "dismiss-options-action::the-dismiss-action-accepts-exactly-an-empty-payload"
    )
    def test_empty_payload_validates(self):
        self.assertEqual(validate_options_dismiss_payload({}), {})

    @covers_requirement(
        "dismiss-options-action::the-dismiss-action-accepts-exactly-an-empty-payload"
    )
    def test_non_empty_payloads_are_rejected(self):
        for value in (
            {"npc_id": 1},
            {"field": "x"},
            {"displayed": []},
            ["x"],
            "dismiss",
            1,
            None,
        ):
            with self.subTest(value=value):
                with self.assertRaises(OptionsActionError):
                    validate_options_dismiss_payload(value)


class DismissAdapterTests(unittest.TestCase):
    def _actor(self):
        return SimpleNamespace(pk=7, key="actor")

    @covers_requirement(
        "dismiss-options-action::dismiss-clears-the-displayed-proposal-state-through-per-session-eviction"
    )
    def test_adapter_calls_evict_with_the_dispatcher_held_session(self):
        session = SimpleNamespace()
        actor = self._actor()
        with patch(
            "server.option_proposal_service.evict",
            return_value=True,
        ) as evict_mock:
            result = _dismiss_adapter(actor, {}, session)
        evict_mock.assert_called_once_with(session, actor)
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "dismissed")
        self.assertEqual(result["affected_panels"], ("context_actions",))

    @covers_requirement(
        "webclient-action-dispatch::adapters-may-receive-the-authenticated-session-through-a-fixed-optional-third-parameter"
    )
    def test_two_argument_direct_call_defaults_session_to_none(self):
        actor = self._actor()
        with patch(
            "server.option_proposal_service.evict",
            return_value=True,
        ) as evict_mock:
            result = _dismiss_adapter(actor, {})
        # A direct two-argument invocation stays valid through the default.
        evict_mock.assert_called_once_with(None, actor)
        self.assertEqual(result["outcome"], "success")

    @covers_requirement(
        "dismiss-options-action::dismiss-clears-the-displayed-proposal-state-through-per-session-eviction"
    )
    def test_failed_eviction_rejects_without_reporting_success(self):
        session = SimpleNamespace()
        actor = self._actor()
        with patch(
            "server.option_proposal_service.evict",
            return_value=False,
        ) as evict_mock:
            result = _dismiss_adapter(actor, {}, session)
        evict_mock.assert_called_once_with(session, actor)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dismiss_failed")

    @covers_requirement(
        "dismiss-options-action::the-dismiss-action-accepts-exactly-an-empty-payload"
    )
    def test_adapter_failure_maps_to_a_rejection_and_never_raises(self):
        session = SimpleNamespace()
        actor = self._actor()
        with patch(
            "server.option_proposal_service.evict",
            side_effect=RuntimeError("boom"),
        ) as evict_mock:
            result = _dismiss_adapter(actor, {}, session)
        evict_mock.assert_called_once_with(session, actor)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dismiss_failed")


class _FakeSession:
    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = 1

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class DismissDispatchIntegrationTests(EvenniaTest):
    """Dispatcher-level dismissal tests over the production registries.

    The service boundary is mocked: the test double replays the eviction
    contract's state write for the exact session it receives (per-session
    targeting) and records nothing else, so "exactly one publication per
    dismissal" is asserted against the real dispatcher completion path while
    cross-session token/cache semantics stay owned by the trigger-service
    suite.
    """

    def setUp(self):
        super().setUp()
        get_world_clock()
        self.room = create_object(Room, key="建議廣場")
        self.player = create_object(PlayerCharacter, key="建議玩家")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()

    def _window(self):
        session = _FakeSession(self.player)
        session.ndb.options_state = None
        attach_coordinator(session, self.registry)
        return session

    def _coordinator(self, session):
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=self.player, protocol_version=1))
        return coordinator

    def _envelope(self, coordinator, action_id, payload, request_id="r1"):
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision,
            "action_id": action_id,
            "payload": payload,
        }

    def _result(self, session):
        results = [call for call in session.sent if "ui_action_result" in call]
        return results[-1]["ui_action_result"][0][0]

    def _updates(self, session):
        return [call for call in session.sent if "ui_update" in call]

    @covers_requirement(
        "dismiss-options-action::dismissal-publishes-exactly-one-state-backed-unavailable-update"
    )
    def test_dismiss_emits_one_state_backed_update_then_one_result(self):
        session = self._window()
        coordinator = self._coordinator(session)

        def _mock_evict(session_arg, actor):
            session_arg.ndb.options_state = _unavailable_state(actor)
            return True

        with patch("server.option_proposal_service.evict", side_effect=_mock_evict) as evict_mock:
            handle_ui_action(
                session,
                self.player,
                self._envelope(coordinator, "options.dismiss", {}),
                self.action_registry,
                self.registry,
            )
            evict_mock.assert_called_once_with(session, self.player)
        updates = self._updates(session)
        self.assertEqual(len(updates), 1)
        update = updates[0]["ui_update"][0][0]
        self.assertEqual(
            update["panels"]["context_actions"]["suggestions"]["status"],
            "unavailable",
        )
        result = self._result(session)
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "dismissed")
        self.assertEqual(result["presentation_revision"], update["revision"])

    @covers_requirement(
        "dismiss-options-action::dismissal-publishes-exactly-one-state-backed-unavailable-update"
    )
    def test_dismiss_with_the_real_evict_publishes_unavailable(self):
        """End-to-end against the real state-only ``evict`` (no mock).

        Seeds a ready session options state, dismisses through the production
        registry, and asserts the real eviction's state write renders exactly
        one unavailable update — pinning the adapter-to-service contract so the
        test doubles and the service cannot drift apart.
        """
        from server import option_proposal_service

        session = self._window()
        coordinator = self._coordinator(session)
        session.ndb.options_state = {
            "owner_actor_id": str(self.player.pk),
            "fingerprint": "situation-fp",
            "status": "ready",
            "generation_token": 4,
            "displayed": [],
        }
        handle_ui_action(
            session,
            self.player,
            self._envelope(coordinator, "options.dismiss", {}),
            self.action_registry,
            self.registry,
        )
        self.assertEqual(session.ndb.options_state["status"], "unavailable")
        self.assertIsNone(session.ndb.options_state["fingerprint"])
        self.assertEqual(session.ndb.options_state["generation_token"], 5)
        updates = self._updates(session)
        self.assertEqual(len(updates), 1)
        self.assertEqual(
            updates[0]["ui_update"][0][0]["panels"]["context_actions"]["suggestions"]["status"],
            "unavailable",
        )
        result = self._result(session)
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            result["presentation_revision"],
            updates[0]["ui_update"][0][0]["revision"],
        )
        # The global cache entry for the dismissed situation is gone.
        self.assertNotIn("situation-fp", option_proposal_service._cache)

    @covers_requirement(
        "dismiss-options-action::dismiss-clears-the-displayed-proposal-state-through-per-session-eviction"
    )
    def test_dismiss_in_window_a_leaves_window_b_untouched(self):
        first = self._window()
        second = self._window()
        second.ndb.options_state = {
            "owner_actor_id": str(self.player.pk),
            "fingerprint": "situation-fp",
            "status": "ready",
            "generation_token": 9,
            "displayed": [],
        }
        first_coordinator = self._coordinator(first)
        self._coordinator(second)
        second_sent_before = list(second.sent)
        second_state_before = dict(second.ndb.options_state)

        def _mock_evict(session_arg, actor):
            session_arg.ndb.options_state = _unavailable_state(actor)
            return True

        with patch("server.option_proposal_service.evict", side_effect=_mock_evict) as evict_mock:
            handle_ui_action(
                first,
                self.player,
                self._envelope(first_coordinator, "options.dismiss", {}, request_id="a-1"),
                self.action_registry,
                self.registry,
            )
            # The eviction is targeted at the dismissing session only.
            evict_mock.assert_called_once_with(first, self.player)
        self.assertEqual(len(self._updates(first)), 1)
        self.assertEqual(first.ndb.options_state["status"], "unavailable")
        self.assertEqual(second.ndb.options_state, second_state_before)
        self.assertEqual(second.sent, second_sent_before)

    @covers_requirement(
        "dismiss-options-action::the-dismiss-action-accepts-exactly-an-empty-payload"
    )
    def test_non_empty_payload_rejects_without_adapter_invocation(self):
        session = self._window()
        coordinator = self._coordinator(session)
        with patch("server.option_proposal_service.evict") as evict_mock:
            handle_ui_action(
                session,
                self.player,
                self._envelope(coordinator, "options.dismiss", {"extra": 1}),
                self.action_registry,
                self.registry,
            )
            evict_mock.assert_not_called()
        result = self._result(session)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "malformed_payload")
        self.assertEqual(self._updates(session), [])


if __name__ == "__main__":
    unittest.main()
