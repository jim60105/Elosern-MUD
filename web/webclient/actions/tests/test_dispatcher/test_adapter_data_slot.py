"""The success-only adapter ``data`` slot through the full emit path."""
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
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    new_presentation_epoch,
    validate_ui_action_result,
)
from ._support import (
    FakeActor,
    FakeSession,
    _coordinator,
    _presenter_registry,
)


class AdapterDataSlotTests(unittest.TestCase):
    """The success-only adapter ``data`` slot through the full emit path."""

    def _dispatch(self, adapter, *, request_id="r1"):
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="proof.data",
                validate_payload=lambda payload: payload,
                adapter=adapter,
                affected_panels=("status",),
            )
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="proof.data",
            request_id=request_id,
        )
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        return session

    def _results(self, session):
        return [
            call["ui_action_result"][0][0]
            for call in session.sent
            if "ui_action_result" in call
        ]

    def _session_with_coordinator(self):
        session = FakeSession()
        _coordinator(session)
        session.puppet = FakeActor()
        return session

    def _envelope(self, *, base_revision, epoch, action_id, request_id, payload=None):
        return {
            "protocol_version": 1,
            "presentation_epoch": epoch,
            "request_id": request_id,
            "base_revision": base_revision,
            "action_id": action_id,
            "payload": payload if payload is not None else {},
        }

    @covers_requirement(
        "webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping"
    )
    def test_success_data_slot_emits_and_validates(self):
        slot = {"display_name": "加斯帕・斯諾"}
        session = self._dispatch(
            lambda actor, payload, session=None: {
                "outcome": "success",
                "code": "ok",
                "message": "完成",
                "affected_panels": ("status",),
                "data": dict(slot),
            }
        )
        envelope = self._results(session)[-1]
        self.assertEqual(envelope["data"], slot)
        validated = validate_ui_action_result(envelope)
        self.assertEqual(validated["data"], slot)

    @covers_requirement(
        "webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping"
    )
    def test_non_success_or_malformed_data_normalizes_to_internal_error(self):
        nine = {f"key_{index}": index for index in range(9)}
        cases = {
            "rejected+data": {"outcome": "rejected", "code": "denied", "message": "拒絕", "data": {"k": 1}},
            "stale+data": {"outcome": "stale", "code": "stale", "message": "过時", "data": {"k": 1}},
            "error+data": {"outcome": "error", "code": "internal_error", "message": "錯誤", "correlation_id": "a" * 32, "data": {"k": 1}},
            "success+non_object": {"outcome": "success", "code": "ok", "message": "完成", "data": [{"k": 1}]},
            "success+nine_fields": {"outcome": "success", "code": "ok", "message": "完成", "data": nine},
        }
        for index, (label, adapter_value) in enumerate(cases.items()):
            with self.subTest(case=label):
                session = self._dispatch(
                    lambda actor, payload, session=None, _v=adapter_value: dict(_v),
                    request_id=f"r{index}",
                )
                envelope = self._results(session)[-1]
                self.assertEqual(envelope["outcome"], "error")
                self.assertEqual(envelope["code"], "internal_error")
                self.assertNotIn("data", envelope)

    @covers_requirement(
        "webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping"
    )
    def test_no_data_adapters_keep_exact_seven_field_envelopes(self):
        session = self._dispatch(
            lambda actor, payload, session=None: {
                "outcome": "success",
                "code": "ok",
                "message": "完成",
                "affected_panels": ("status",),
            }
        )
        envelope = self._results(session)[-1]
        self.assertEqual(
            set(envelope),
            {
                "protocol_version",
                "presentation_epoch",
                "request_id",
                "outcome",
                "code",
                "message",
                "presentation_revision",
            },
        )

    @covers_requirement(
        "webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping"
    )
    def test_deferred_data_slot_replays_an_immutable_snapshot(self):
        held: Deferred = Deferred()
        adapter_data = {"display_name": "加斯帕", "nested": {"tags": ["甲"]}}
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="proof.data",
                validate_payload=lambda payload: payload,
                adapter=lambda actor, payload, session=None: held,
                affected_panels=("status",),
            )
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="proof.data",
            request_id="r1",
        )
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        held.callback(
            {
                "outcome": "success",
                "code": "ok",
                "message": "完成",
                "affected_panels": ("status",),
                "data": adapter_data,
            }
        )
        first = self._results(session)[-1]
        # The adapter mutates its own object after completion; the cached
        # replay must be the private snapshot, not the mutated live object.
        adapter_data["display_name"] = "被改寫"
        adapter_data["nested"]["tags"].append("乙")
        replay = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="proof.data",
            request_id="r1",
        )
        handle_ui_action(session, session.puppet, replay, registry, _presenter_registry())
        second = self._results(session)[-1]
        self.assertEqual(second["data"], first["data"])
        self.assertEqual(second["data"]["display_name"], "加斯帕")
        self.assertEqual(second["data"]["nested"]["tags"], ["甲"])

if __name__ == "__main__":
    unittest.main()
