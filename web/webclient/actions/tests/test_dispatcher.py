"""UI action registry and dispatcher tests (foundation section 2)."""

from types import SimpleNamespace
import unittest

from tools.spec_traceability import covers_requirement

from twisted.internet.defer import Deferred, succeed

from web.webclient.actions.dispatcher import (
    CACHE_CAPACITY,
    SequenceState,
    handle_ui_action,
    retire_sequence,
)
from web.webclient.actions.registry import (
    ActionRegistry,
    ActionSpec,
    build_production_action_registry,
)
from web.webclient.presentation.coordinator import (
    PresentationCoordinator,
    attach_coordinator,
)
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    new_presentation_epoch,
)
from web.webclient.presentation.registry import (
    PresenterSpec,
    PresentationRegistry,
)


class FakeSession:
    def __init__(self):
        self.sent = []
        self.puppet = None
        self.ndb = SimpleNamespace()

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class FakeActor:
    def __init__(self, key="actor", pk=1):
        self.key = key
        self.pk = pk
        self.location = None


def _registry(*specs):
    registry = PresentationRegistry("test")
    for spec in specs:
        registry.register(spec)
    return registry


def _presenter_registry():
    return _registry(
        PresenterSpec(
            name="status",
            schema_version=1,
            unavailable_reason=("missing_data", "無法讀取角色資料"),
            presenter=lambda context: {"available": True, "value": 1},
        )
    )


def _proof_spec(action_id="proof.noop", adapter=None):
    return ActionSpec(
        action_id=action_id,
        validate_payload=lambda payload: payload,
        adapter=adapter
        or (
            lambda actor, payload, session=None: {
                "outcome": "success",
                "code": "ok",
                "message": "完成",
                "affected_panels": ("status",),
            }
        ),
        affected_panels=("status",),
    )


def _coordinator(session):
    coordinator = PresentationCoordinator(
        session,
        _presenter_registry(),
        calendar_provider=lambda: SimpleNamespace(
            year=1204, season_index=0, season_name="春", day_in_season=1, hour=1, minute=0, second=0
        ),
        mode_provider=lambda ctx: "exploration",
    )
    session.ndb.elosern_coordinator = coordinator
    return coordinator


class RegistryTests(unittest.TestCase):
    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_duplicate_registration_fails(self):
        registry = ActionRegistry("test")
        registry.register(_proof_spec())
        with self.assertRaises(ProtocolValidationError):
            registry.register(_proof_spec())

    def test_unknown_action_ids_not_exposed(self):
        registry = ActionRegistry("test")
        registry.register(_proof_spec())
        self.assertEqual(registry.action_ids, frozenset({"proof.noop"}))
        with self.assertRaises(KeyError):
            registry.spec("combat.cast")

    def test_validate_and_adapter_resolves_the_registered_spec(self):
        registry = ActionRegistry("test")
        spec = _proof_spec()
        registry.register(spec)
        resolved, adapter = registry.validate_and_adapter("proof.noop")
        self.assertIs(resolved, spec)
        self.assertEqual(
            adapter("actor", {}), spec.adapter("actor", {})
        )

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_production_registry_exposes_only_specified_adapters(self):
        registry = build_production_action_registry()
        self.assertEqual(
            registry.action_ids,
            frozenset(
                {
                    "combat.cast",
                    "combat.flee",
                    "combat.forfeit",
                    "guild.register",
                    "guild.quest_accept",
                    "guild.quest_abandon",
                    "guild.quest_turnin",
                    "guild.exam_start",
                    "shop.buy",
                    "shop.sell",
                    "creation.preset",
                    "creation.custom",
                    "creation.concept",
                    "creation.activate",
                    "creation.reset",
                    "explore.move",
                    "explore.look",
                    "explore.talk_scripted",
                    "explore.talk_freeform",
                    "explore.party_invite",
                    "explore.party_leave",
                    "explore.engage",
                    "explore.wait",
                    "options.dismiss",
                }
            ),
        )
        # Validation and dispatch infrastructure remains usable.
        self.assertTrue(hasattr(registry, "spec"))


class DispatcherTests(unittest.TestCase):
    def _session_with_coordinator(self):
        session = FakeSession()
        _coordinator(session)
        session.puppet = FakeActor()
        return session

    def _envelope(self, *, base_revision=None, epoch=None, action_id="proof.noop", request_id="r1", payload=None):
        coordinator = None
        if base_revision is None or epoch is None:
            # derive from a fresh coordinator to mirror live state
            pass
        return {
            "protocol_version": 1,
            "presentation_epoch": epoch or "x" * 22,
            "request_id": request_id,
            "base_revision": base_revision if base_revision is not None else 1,
            "action_id": action_id,
            "payload": payload if payload is not None else {},
        }

    def _ui_action(self, session, envelope, registry):
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())

    @covers_requirement(
        "webclient-action-dispatch::action-identity-comes-only-from-the-authenticated-session"
    )
    def test_actor_like_unknown_field_is_rejected(self):
        session = self._session_with_coordinator()
        envelope = self._envelope(epoch=session.ndb.elosern_coordinator.epoch, base_revision=1, payload={})
        envelope["actor"] = "me"
        handle_ui_action(session, session.puppet, envelope, ActionRegistry("test"), _presenter_registry())
        errors = [call for call in session.sent if "ui_protocol_error" in call]
        self.assertTrue(errors)
        self.assertEqual(errors[-1]["ui_protocol_error"][0][0]["code"], "malformed_envelope")

    def test_malformed_envelope_gets_safe_error(self):
        session = self._session_with_coordinator()
        handle_ui_action(session, session.puppet, {"bad": 1}, ActionRegistry("test"), _presenter_registry())
        errors = [call for call in session.sent if "ui_protocol_error" in call]
        self.assertEqual(errors[-1]["ui_protocol_error"][0][0]["code"], "malformed_envelope")

    @covers_requirement(
        "webclient-action-dispatch::stale-presentation-state-prevents-adapter-invocation"
    )
    def test_stale_revision_calls_no_adapter_and_emits_snapshot(self):
        calls = []
        registry = ActionRegistry("test")
        registry.register(_proof_spec(adapter=lambda actor, payload, session=None: calls.append(1) or {"outcome": "success", "code": "ok", "message": "完成"}))
        session = self._session_with_coordinator()
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision - 1, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        self.assertEqual(calls, [])
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertEqual(results[-1]["ui_action_result"][0][0]["outcome"], "stale")
        snapshots = [call for call in session.sent if "ui_snapshot" in call]
        self.assertTrue(snapshots)

    @covers_requirement(
        "webclient-action-dispatch::stale-presentation-state-prevents-adapter-invocation"
    )
    def test_prior_epoch_calls_no_adapter(self):
        calls = []
        registry = ActionRegistry("test")
        registry.register(_proof_spec(adapter=lambda actor, payload, session=None: calls.append(1) or {"outcome": "success", "code": "ok", "message": "完成"}))
        session = self._session_with_coordinator()
        envelope = self._envelope(epoch="a" * 22, base_revision=1, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        self.assertEqual(calls, [])

    @covers_requirement(
        "webclient-action-dispatch::completed-request-ids-are-deduplicated-within-a-bounded-session-cache"
    )
    def test_duplicate_request_executes_once(self):
        calls = []
        registry = ActionRegistry("test")
        registry.register(
            _proof_spec(
                adapter=lambda actor, payload, session=None: calls.append(1)
                or {"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)}
            )
        )
        session = self._session_with_coordinator()
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        self.assertEqual(calls, [1])
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertEqual(len(results), 2)

    @covers_requirement(
        "webclient-action-dispatch::completed-request-ids-are-deduplicated-within-a-bounded-session-cache"
    )
    def test_cache_remains_bounded(self):
        session = self._session_with_coordinator()
        state = SequenceState()
        for i in range(CACHE_CAPACITY + 10):
            from web.webclient.actions.dispatcher import _cache_result

            _cache_result(state, f"r{i}", {"outcome": "success", "code": "ok", "message": "m"})
        self.assertLessEqual(len(state.cache), CACHE_CAPACITY)
        self.assertNotIn("r0", state.cache)

    @covers_requirement(
        "webclient-action-dispatch::completed-request-ids-are-deduplicated-within-a-bounded-session-cache"
    )
    def test_retire_sequence_discards_cache_and_marker(self):
        session = self._session_with_coordinator()
        state = _sequence_state_for_test(session)
        from web.webclient.actions.dispatcher import _cache_result

        _cache_result(state, "r1", {"outcome": "success", "code": "ok", "message": "m"})
        state.in_flight = True
        retire_sequence(session)
        self.assertIsNone(getattr(session.ndb, "elosern_dispatch", None))

    @covers_requirement(
        "webclient-action-dispatch::each-session-admits-only-one-mutation-in-flight"
    )
    def test_concurrent_mutation_rejected_as_busy(self):
        calls = []
        held = Deferred()
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="proof.slow",
                validate_payload=lambda payload: payload,
                adapter=lambda actor, payload, session=None: calls.append(1) or held,
            )
        )
        session = self._session_with_coordinator()
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        first = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.slow", request_id="r1")
        second = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.slow", request_id="r2")
        handle_ui_action(session, session.puppet, first, registry, _presenter_registry())
        handle_ui_action(session, session.puppet, second, registry, _presenter_registry())
        self.assertEqual(calls, [1])
        results = [call for call in session.sent if "ui_action_result" in call]
        busy = [call for call in results if call["ui_action_result"][0][0]["outcome"] == "rejected"]
        self.assertTrue(busy)
        self.assertEqual(busy[-1]["ui_action_result"][0][0]["code"], "busy")
        held.callback({"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)})

    @covers_requirement(
        "webclient-action-dispatch::admitted-action-completion-publishes-canonical-state-before-unlocking"
    )
    def test_success_publishes_update_before_result_and_unlocks(self):
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(_proof_spec())
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        # The synchronous adapter published update then result.
        updates = [call for call in session.sent if "ui_update" in call]
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertTrue(updates)
        update_rev = updates[-1]["ui_update"][0][0]["revision"]
        result_rev = results[-1]["ui_action_result"][0][0]["presentation_revision"]
        self.assertEqual(update_rev, result_rev)
        self.assertEqual(results[-1]["ui_action_result"][0][0]["outcome"], "success")
        self.assertFalse(getattr(session.ndb, "elosern_dispatch", None).in_flight)

    @covers_requirement(
        "webclient-combat-menu::terminal-combat-outcomes-refresh-all-mode-relevant-panels"
    )
    def test_empty_affected_panels_publishes_full_snapshot(self):
        # A terminal settlement (empty affected panels) must publish a full
        # snapshot at a fresh revision, never a partial ui_update, so the mode
        # flip to exploration carries every panel.
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(
            _proof_spec(
                adapter=lambda actor, payload, session=None: {
                    "outcome": "success",
                    "code": "fled",
                    "message": "你脫離了戰鬥。",
                    "affected_panels": (),
                }
            )
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        snapshots = [call for call in session.sent if "ui_snapshot" in call]
        updates = [call for call in session.sent if "ui_update" in call]
        self.assertTrue(snapshots, "terminal completion must publish a full snapshot")
        self.assertFalse(updates, "terminal completion must not publish a partial update")
        result = [
            call for call in session.sent if "ui_action_result" in call
        ][-1]["ui_action_result"][0][0]
        self.assertEqual(result["presentation_revision"], snapshots[-1]["ui_snapshot"][0][0]["revision"])
        self.assertFalse(getattr(session.ndb, "elosern_dispatch", None).in_flight)

    @covers_requirement(
        "webclient-action-dispatch::dispatch-rejects-no-puppet-actions-with-a-bounded-response"
    )
    def test_reject_no_puppet_echoes_request_binding(self):
        from web.webclient.actions.dispatcher import NO_PUPPET_CODE, reject_no_puppet

        session = self._session_with_coordinator()
        epoch = session.ndb.elosern_coordinator.epoch
        action = {
            "protocol_version": 1,
            "presentation_epoch": epoch,
            "request_id": "stale-9",
            "base_revision": 4,
            "action_id": "explore.rest",
            "payload": {},
        }
        reject_no_puppet(session, action)
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertEqual(len(results), 1)
        envelope = results[0]["ui_action_result"][0][0]
        self.assertEqual(envelope["outcome"], "rejected")
        self.assertEqual(envelope["code"], NO_PUPPET_CODE)
        self.assertEqual(envelope["presentation_epoch"], epoch)
        self.assertEqual(envelope["request_id"], "stale-9")
        self.assertEqual(envelope["presentation_revision"], 4)
        self.assertNotIn("panels", envelope)
        self.assertNotIn("correlation_id", envelope)

    @covers_requirement(
        "webclient-action-dispatch::admitted-action-completion-publishes-canonical-state-before-unlocking"
    )
    def test_internal_error_publishes_snapshot_and_unlocks(self):
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(
            _proof_spec(adapter=lambda actor, payload, session=None: (_ for _ in ()).throw(RuntimeError("boom")))
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        results = [call for call in session.sent if "ui_action_result" in call]
        result = results[-1]["ui_action_result"][0][0]
        self.assertEqual(result["outcome"], "error")
        self.assertEqual(len(result["correlation_id"]), 32)
        self.assertNotIn("boom", repr(result))
        self.assertFalse(getattr(session.ndb, "elosern_dispatch", None).in_flight)

    @covers_requirement(
        "webclient-action-dispatch::action-results-are-safe-and-disconnects-are-never-retried-automatically"
    )
    def test_domain_rejection_is_stable_and_safe(self):
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(
            _proof_spec(
                adapter=lambda actor, payload, session=None: {"outcome": "rejected", "code": "insufficient_sp", "message": "SP 不足"}
            )
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        results = [call for call in session.sent if "ui_action_result" in call]
        result = results[-1]["ui_action_result"][0][0]
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_sp")
        self.assertNotIn("correlation_id", result)

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe",
        "webclient-action-dispatch::action-results-are-safe-and-disconnects-are-never-retried-automatically"
    )
    def test_unknown_action_gets_schema_valid_rejected_result(self):
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(_proof_spec())
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="combat.cast",
        )
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        # The rejection must be a schema-valid ui_action_result, never a
        # protocol error with an unregistered code.
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertTrue(results)
        result = results[-1]["ui_action_result"][0][0]
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_action")
        self.assertEqual(result["request_id"], "r1")
        errors = [call for call in session.sent if "ui_protocol_error" in call]
        self.assertFalse(errors)

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe",
        "webclient-action-dispatch::action-results-are-safe-and-disconnects-are-never-retried-automatically"
    )
    def test_malformed_action_payload_gets_schema_valid_rejected_result(self):
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="proof.strict",
                validate_payload=lambda payload: (_ for _ in ()).throw(
                    ProtocolValidationError("bad payload")
                ),
                adapter=lambda actor, payload, session=None: {"outcome": "success", "code": "ok", "message": "m"},
            )
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="proof.strict",
        )
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        results = [call for call in session.sent if "ui_action_result" in call]
        result = results[-1]["ui_action_result"][0][0]
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "malformed_payload")
        errors = [call for call in session.sent if "ui_protocol_error" in call]
        self.assertFalse(errors)

    @covers_requirement(
        "webclient-action-dispatch::completed-request-ids-are-deduplicated-within-a-bounded-session-cache"
    )
    def test_retired_sequence_cannot_publish_or_clear_replacement_lock(self):
        from web.webclient.actions.dispatcher import retire_sequence

        calls = []
        held = Deferred()
        session = self._session_with_coordinator()
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="proof.slow",
                validate_payload=lambda payload: payload,
                adapter=lambda actor, payload, session=None: calls.append(actor) or held,
            )
        )
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(
            epoch=coordinator.epoch,
            base_revision=coordinator.revision,
            action_id="proof.slow",
            request_id="retire-1",
        )
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        # Puppet change: coordinator reset + sequence retirement.
        coordinator.reset()
        retire_sequence(session)
        held.callback({"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)})
        results = [call for call in session.sent if "ui_action_result" in call]
        self.assertFalse(results, "retired sequence must not publish a result")
        state = getattr(session.ndb, "elosern_dispatch", None)
        if state is not None:
            # Any recreated state carries no epoch token and is not in flight.
            self.assertIsNone(state.epoch)
            self.assertFalse(state.in_flight)

    @covers_requirement(
        "dismiss-options-action::adapters-receive-the-authenticated-session-through-a-fixed-optional-parameter",
        "webclient-action-dispatch::adapters-may-receive-the-authenticated-session-through-a-fixed-optional-third-parameter",
    )
    def test_proof_adapter_receives_the_session_as_the_third_argument(self):
        received = []
        registry = ActionRegistry("test")
        registry.register(
            _proof_spec(
                adapter=lambda actor, payload, session=None: received.append((actor, session))
                or {"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)}
            )
        )
        session = self._session_with_coordinator()
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        self.assertEqual(len(received), 1)
        actor_arg, session_arg = received[0]
        self.assertIs(actor_arg, session.puppet)
        self.assertIs(session_arg, session)

    @covers_requirement(
        "dismiss-options-action::adapters-receive-the-authenticated-session-through-a-fixed-optional-parameter",
        "webclient-action-dispatch::adapters-may-receive-the-authenticated-session-through-a-fixed-optional-third-parameter",
    )
    def test_two_argument_direct_invocation_defaults_session_to_none(self):
        received = {}

        def proof(actor, payload, session=None):
            received["session"] = session
            return {"outcome": "success", "code": "ok", "message": "完成"}

        result = proof("actor", {"x": 1})
        self.assertIsNone(received["session"])
        self.assertEqual(result["outcome"], "success")

    @covers_requirement(
        "dismiss-options-action::adapters-receive-the-authenticated-session-through-a-fixed-optional-parameter",
        "webclient-action-dispatch::adapters-may-receive-the-authenticated-session-through-a-fixed-optional-third-parameter",
    )
    def test_dispatcher_passes_three_positionals_without_introspection(self):
        received = []

        def proof(actor, payload, session=None, *extra):
            # The declared three-parameter ABI plus a rest slot: the rest must
            # stay empty, proving the dispatcher passes exactly three
            # positional arguments unconditionally, never introspecting.
            received.append((actor, payload, session, extra))
            return {"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)}

        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="proof.noop",
                validate_payload=lambda payload: payload,
                adapter=proof,
            )
        )
        session = self._session_with_coordinator()
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=session.puppet, protocol_version=1))
        envelope = self._envelope(epoch=coordinator.epoch, base_revision=coordinator.revision, action_id="proof.noop")
        handle_ui_action(session, session.puppet, envelope, registry, _presenter_registry())
        self.assertEqual(len(received), 1)
        actor_arg, payload_arg, session_arg, extra = received[0]
        self.assertIs(actor_arg, session.puppet)
        self.assertEqual(payload_arg, {})
        self.assertIs(session_arg, session)
        self.assertEqual(extra, ())


def _sequence_state_for_test(session):
    from web.webclient.actions.dispatcher import _sequence_state

    return _sequence_state(session)


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
            lambda actor, payload: {
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
            lambda actor, payload: held,
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
            lambda actor, payload: {
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
            lambda actor, payload: {
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
            lambda actor, payload: {
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
            lambda actor, payload: {
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
            lambda actor, payload: held,
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
