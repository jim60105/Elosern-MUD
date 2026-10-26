"""Causal publication groups: coalescing, independent ingress and outcomes.

These are the focused behavior tests for the settlement slice:

- the synchronous publication-group API (nested reuse, scoped binding, commit
  capture and rebinding, and no revival across a copied asynchronous context);
- one final checkpoint publication per committed group for every watcher, in
  either callback order, including a completion with no initiating command;
- overlapping text and graphical ingress without a session-wide token, and
  explicit synchronization staying an independent queue entry;
- the always-Deferred queue outcome (receipt after send, retirement, preflight,
  send and bounded-overflow failures) for merged group entries;
- the dispatcher's group capture, private result slot and result-only flush.

The coordinator is always the production one; sessions, presenters and the
reactor scheduler are synthetic so the ordering is deterministic.
"""

from types import SimpleNamespace
from unittest import mock
import unittest

from django.db import transaction
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet.task import Clock
from twisted.python.failure import Failure

from evennia.utils.test_resources import EvenniaTest

from world.rules.presentation_events import (
    AlignmentIdentity,
    PresentationAlignmentFact,
    PublicationGroup,
    clear_alignment_observers,
    current_publication_group,
    emit_alignment_fact,
    new_publication_group,
    on_publication_commit,
    publication_group,
    register_alignment_observer,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import (
    MAX_PENDING_PUBLICATIONS,
    PresentationCoordinator,
    PresentationQueueFull,
)
from web.webclient.presentation.ingress import observe_command_settlement
from web.webclient.presentation.publication import (
    PublicationCompletion,
    PublicationReceipt,
    copy_json_value,
)
from web.webclient.presentation.registry import PresenterSpec, PresentationRegistry
from web.webclient.presentation.tests._support import (
    publication_failure,
    publication_receipt,
)


class _Calendar:
    year = 1204
    season_index = 2
    season_name = "仲夏"
    day_in_season = 17
    hour = 14
    minute = 30
    second = 5


def _calendar():
    return _Calendar()


class FakeSession:
    """A transport that records frames and can inject send faults."""

    def __init__(self, sessid=7):
        self.sent: list[dict] = []
        self.ndb = SimpleNamespace()
        self.puppet = None
        self.sessid = sessid
        self.protocol_key = "websocket"
        self.on_send = None

    def msg(self, **kwargs) -> None:
        (name, payload) = next(iter(kwargs.items()))
        envelope = payload[0][0]
        if self.on_send is not None:
            self.on_send(name, envelope)
        self.sent.append(kwargs)

    def frames(self, message: str | None = None) -> list[dict]:
        recorded = []
        for call in self.sent:
            for name, payload in call.items():
                if message is None or name == message:
                    recorded.append(payload[0][0])
        return recorded

    def names(self) -> list[str]:
        return [name for call in self.sent for name in call]


class QueuedScheduler:
    """An injected reactor-next-turn seam a test runs explicitly."""

    def __init__(self) -> None:
        self.callbacks: list = []

    def __call__(self, callback) -> None:
        self.callbacks.append(callback)

    def run(self) -> None:
        while self.callbacks:
            self.callbacks.pop(0)()


def _spec(name, presenter, *, on_demand=False):
    return PresenterSpec(
        name=name,
        schema_version=1,
        unavailable_reason=("missing_data", "無法讀取"),
        presenter=presenter,
        on_demand=on_demand,
    )


def _registry(*specs):
    registry = PresentationRegistry("test")
    for spec in specs:
        registry.register(spec)
    return registry


def _context(actor=None):
    return PresentationContext(actor=actor or SimpleNamespace(), protocol_version=1)


def _coordinator(session, registry, scheduler=None):
    coordinator = PresentationCoordinator(
        session,
        registry,
        calendar_provider=_calendar,
        mode_provider=lambda context: "exploration",
        scheduler=scheduler,
    )
    session.ndb.elosern_coordinator = coordinator
    return coordinator


def _state_registry(state, name="status"):
    return _registry(
        _spec(name, lambda context: {"available": True, "value": state["value"]})
    )


def _completion(request_id="r1"):
    owned = copy_json_value({"outcome": "success", "code": "ok", "message": "完成"})

    def envelope(epoch, revision):
        return {
            "protocol_version": 1,
            "presentation_epoch": epoch,
            "request_id": request_id,
            "outcome": owned["outcome"],
            "code": owned["code"],
            "message": owned["message"],
            "presentation_revision": revision,
        }

    return PublicationCompletion(request_id=request_id, result=owned, envelope=envelope)


class PublicationGroupApiTests(unittest.TestCase):
    """The synchronous causal-group helper and its lifetime rules."""

    def test_nested_scopes_reuse_the_group_and_reset_before_a_deferred(self):
        seen = {}
        deferred = Deferred()
        with publication_group() as outer:
            with publication_group() as inner:
                seen["inner"] = inner
            deferred.addCallback(lambda _value: current_publication_group())
        self.assertIs(seen["inner"], outer)
        self.assertIsNone(current_publication_group(), "the scope must reset")
        deferred.callback(None)
        self.assertIsNone(deferred.result, "a returned Deferred never carries the group")

    def test_group_ids_are_unique_hex_and_validated(self):
        first = new_publication_group()
        second = new_publication_group()
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(len(first.id), 32)
        int(first.id, 16)
        with self.assertRaises(ValueError):
            PublicationGroup("not-a-group-id")

    def test_a_closed_binding_is_not_revived_by_a_copied_async_context(self):
        held = Deferred()
        seen: list = []
        resumed: list = []

        @inlineCallbacks
        def worker():
            yield held
            seen.append(current_publication_group())
            with publication_group() as fresh:
                resumed.append(fresh)

        with publication_group() as captured:
            deferred = worker()
        self.assertIsNone(current_publication_group())
        held.callback(None)
        self.assertTrue(deferred.called)
        self.assertEqual(seen, [None])
        self.assertNotEqual(resumed[0].id, captured.id)

    def test_a_callback_returning_a_pending_deferred_does_not_leak_its_group(self):
        def operation():
            with publication_group() as group:
                return group, Deferred()

        group, pending = operation()
        self.assertIsNone(current_publication_group())
        later: list = []
        pending.addCallback(lambda value: later.append(current_publication_group()))
        pending.callback(None)
        self.assertEqual(later, [None])
        self.assertIsNotNone(group.id)

    def test_on_publication_commit_captures_and_rebinds_the_group(self):
        registered: list = []
        observed: list = []
        with publication_group() as captured:
            with mock.patch(
                "django.db.transaction.on_commit",
                side_effect=lambda callback, using=None: registered.append(callback),
            ):
                on_publication_commit(
                    lambda: observed.append(current_publication_group())
                )
        self.assertIsNone(current_publication_group())
        self.assertEqual(len(registered), 1)
        registered[0]()
        self.assertIs(observed[0], captured)
        self.assertIsNone(current_publication_group())

    def test_fact_values_are_validated(self):
        group = new_publication_group()
        fact = PresentationAlignmentFact(
            group_id=group.id, actor_id=4, cause="movement_boundary"
        )
        self.assertIsNone(fact.source)
        with self.assertRaises(ValueError):
            PresentationAlignmentFact(
                group_id="short", actor_id=4, cause="movement_boundary"
            )
        with self.assertRaises(ValueError):
            PresentationAlignmentFact(
                group_id=group.id, actor_id=4, cause="unsupported"
            )
        with self.assertRaises(ValueError):
            PresentationAlignmentFact(
                group_id=group.id, actor_id=True, cause="movement_boundary"
            )
        with self.assertRaises(ValueError):
            AlignmentIdentity(layer="area", area_key="a", instance_key=(0, ""))
        identity = AlignmentIdentity(layer="area", area_key="a", instance_key=(2, "t"))
        with self.assertRaises(ValueError):
            PresentationAlignmentFact(
                group_id=group.id,
                actor_id=4,
                cause="movement_boundary",
                source="area",
            )
        self.assertEqual(identity.instance_key, (2, "t"))

    def test_one_failing_observer_cannot_stop_the_others(self):
        self.addCleanup(clear_alignment_observers)
        clear_alignment_observers()
        delivered: list = []
        fact = PresentationAlignmentFact(
            group_id=new_publication_group().id, actor_id=1, cause="skip_completed"
        )

        def broken(_fact):
            raise RuntimeError("observer failed")

        register_alignment_observer(broken)
        register_alignment_observer(delivered.append)
        with mock.patch("world.rules.presentation_events.log_warn") as log_warn:
            emit_alignment_fact(fact)
        self.assertEqual(delivered, [fact])
        self.assertEqual(log_warn.call_args.args[0], "alignment_fact_delivery_failed")
        self.assertEqual(log_warn.call_args.kwargs["context"]["cause"], "skip_completed")


class DialogueReadingGroupTests(unittest.TestCase):
    """A reading push submits a name inside a group and stays independent with a batch."""

    def _run(self, *, unlock_batch, grouped):
        from web.webclient.presentation import dialogue_push

        published: list = []
        rendered: list = []
        watcher = FakeSession()
        puppet = SimpleNamespace(pk=1)

        def _forbidden(reason):
            def _fail(*_args, **_kwargs):
                raise AssertionError(reason)

            return _fail

        deps = dialogue_push.PanelPushDeps(
            watchers_for=lambda actor: ((watcher, "epoch-1"),),
            build_registry=(
                _forbidden("a grouped plain push must not build the registry")
                if grouped and unlock_batch is None
                else (
                    lambda: SimpleNamespace(
                        render=lambda name, context: rendered.append(name)
                        or {"available": True}
                    )
                )
            ),
            build_context=(
                _forbidden("a grouped plain push must not render eagerly")
                if grouped and unlock_batch is None
                else (
                    lambda session, actor: PresentationContext(
                        actor=actor, protocol_version=1
                    )
                )
            ),
            publish=lambda session, actor, panels, **kwargs: published.append(
                (panels, kwargs)
            ),
            log_warn=lambda *args, **kwargs: None,
        )
        with (
            mock.patch.object(dialogue_push, "_deps", return_value=deps),
            mock.patch.object(dialogue_push, "_owner_puppets", return_value=(puppet,)),
        ):
            if grouped:
                with publication_group():
                    dialogue_push.push_dialogue_reading(
                        SimpleNamespace(pk=5), unlock_batch=unlock_batch
                    )
            else:
                dialogue_push.push_dialogue_reading(
                    SimpleNamespace(pk=5), unlock_batch=unlock_batch
                )
        return published, rendered

    def test_a_plain_reading_push_inside_a_group_submits_the_panel_name(self):
        published, rendered = self._run(unlock_batch=None, grouped=True)
        self.assertEqual(rendered, [])
        self.assertEqual(len(published), 1)
        panels, kwargs = published[0]
        self.assertEqual(panels, {})
        self.assertEqual(
            kwargs, {"expected_epoch": "epoch-1", "affected_panels": ("dialogue",)}
        )

    def test_a_plain_reading_push_outside_a_group_still_renders_its_payload(self):
        published, rendered = self._run(unlock_batch=None, grouped=False)
        self.assertEqual(rendered, ["dialogue"])
        self.assertEqual(published[0][0], {"dialogue": {"available": True}})
        self.assertNotIn("independent", published[0][1])

    def test_a_claimed_batch_publishes_its_decorated_payload_independently(self):
        published, rendered = self._run(unlock_batch=object(), grouped=True)
        self.assertEqual(rendered, ["dialogue"])
        panels, kwargs = published[0]
        self.assertIn("dialogue", panels)
        self.assertTrue(kwargs["independent"])


class CoordinatorGroupingTests(unittest.TestCase):
    """One pending entry per group, merged declarations and real outcomes."""

    def _two_watchers(self):
        scheduled = QueuedScheduler()
        sessions = [FakeSession(sessid=11), FakeSession(sessid=12)]
        state = {"value": 1}
        coordinators = [
            _coordinator(session, _state_registry(state), scheduler=scheduled)
            for session in sessions
        ]
        for coordinator in coordinators:
            coordinator.full_snapshot(_context())
        scheduled.run()
        for coordinator in coordinators:
            coordinator.session.sent.clear()
        return state, sessions, coordinators, scheduled

    def test_every_watcher_receives_one_snapshot_in_either_callback_order(self):
        for push_first in (True, False):
            with self.subTest(push_first=push_first):
                state, sessions, coordinators, scheduled = self._two_watchers()
                group = new_publication_group()
                state["value"] = 2
                for coordinator in coordinators:
                    payload = {"available": True, "value": 2}
                    if push_first:
                        coordinator.enqueue_publication(
                            _context,
                            candidate_panels={"status": payload},
                            group_id=group.id,
                        )
                        coordinator.enqueue_publication(
                            _context, force_snapshot=True, group_id=group.id
                        )
                    else:
                        coordinator.enqueue_publication(
                            _context, force_snapshot=True, group_id=group.id
                        )
                        coordinator.enqueue_publication(
                            _context,
                            candidate_panels={"status": payload},
                            group_id=group.id,
                        )
                for session in sessions:
                    self.assertEqual(session.sent, [], "grouped frames wait for the boundary")
                scheduled.run()
                for session in sessions:
                    self.assertEqual(session.names(), ["ui_snapshot"])
                    snapshot = session.frames("ui_snapshot")[0]
                    self.assertEqual(snapshot["revision"], 2)
                    self.assertEqual(snapshot["panels"]["status"]["value"], 2)

    def test_every_waiter_resolves_with_the_same_actual_receipt(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        state["value"] = 3
        group = new_publication_group()
        first = coordinator.enqueue_publication(
            _context, affected_panels={"status"}, group_id=group.id
        )
        second = coordinator.enqueue_publication(
            _context, affected_panels={"status"}, group_id=group.id
        )
        scheduled.run()
        first_receipt = publication_receipt(first)
        second_receipt = publication_receipt(second)
        self.assertEqual(first_receipt, second_receipt)
        self.assertEqual(first_receipt.kind, "delta")
        self.assertTrue(first_receipt.published)
        self.assertEqual(sessions[0].frames("ui_update")[0]["base_revision"], 1)

    def test_retirement_resolves_every_group_waiter_with_no_publication(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        group = new_publication_group()
        waiters = [
            coordinator.enqueue_publication(
                _context, affected_panels={"status"}, group_id=group.id
            )
            for _ in range(3)
        ]
        coordinator.reset()
        scheduled.run()
        self.assertEqual([waiter.result for waiter in waiters], [None, None, None])
        self.assertEqual(sessions[0].sent, [])

    def test_queue_order_is_publication_order_for_grouped_and_standalone_work(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        group = new_publication_group()
        state["value"] = 2
        grouped = coordinator.enqueue_publication(
            _context, affected_panels={"status"}, group_id=group.id
        )
        standalone = coordinator.enqueue_publication(_context, force_snapshot=True)
        self.assertEqual(sessions[0].sent, [], "every entry waits for the boundary")
        state["value"] = 3
        scheduled.run()
        self.assertTrue(grouped.called)
        self.assertTrue(standalone.called)
        published = [
            (next(iter(call)), call[next(iter(call))][0][0]["revision"])
            for call in sessions[0].sent
        ]
        self.assertEqual(
            published,
            [("ui_update", 2), ("ui_snapshot", 3)],
            "the earlier committed entry published first",
        )
        self.assertEqual(
            sessions[0].frames()[0]["base_revision"], 1
        )

    def test_preflight_failure_errbacks_every_group_waiter_and_sends_nothing(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        group = new_publication_group()
        waiters = [
            coordinator.enqueue_publication(
                _context,
                candidate_panels={"status": object()},
                group_id=group.id,
            )
            for _ in range(2)
        ]
        publication_failure(waiters[0]).trap(TypeError)
        publication_failure(waiters[1]).trap(TypeError)
        scheduled.run()
        self.assertEqual(sessions[0].sent, [])
        self.assertEqual(coordinator.revision, 1)

    def test_send_failure_errbacks_every_waiter_and_reports_the_real_error(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        state["value"] = 2
        group = new_publication_group()
        waiters = [
            coordinator.enqueue_publication(
                _context, affected_panels={"status"}, group_id=group.id
            )
            for _ in range(2)
        ]

        def fail(name, envelope):
            raise RuntimeError("transport is gone")

        sessions[0].on_send = fail
        scheduled.run()
        for waiter in waiters:
            publication_failure(waiter).trap(RuntimeError)
        self.assertGreater(coordinator.revision, 1)
        sessions[0].on_send = None
        recovery = coordinator.enqueue_publication(_context)
        scheduled.run()
        receipt = publication_receipt(recovery)
        self.assertEqual(receipt.kind, "snapshot", "an escaped frame forbids deltas")

    def test_the_pending_bound_overflow_explicitly_in_one_group_or_many(self):
        for spread in (False, True):
            with self.subTest(spread=spread):
                state, sessions, coordinators, scheduled = self._two_watchers()
                coordinator = coordinators[0]
                ids = [
                    new_publication_group().id
                    for _ in range(MAX_PENDING_PUBLICATIONS + 1)
                ]
                if not spread:
                    ids = [ids[0]] * len(ids)
                waiters = [
                    coordinator.enqueue_publication(
                        _context, affected_panels={"status"}, group_id=group_id
                    )
                    for group_id in ids
                ]
                self.assertTrue(
                    publication_failure(waiters[-1]).check(PresentationQueueFull)
                )
                self.assertEqual(
                    len(coordinator._pending_groups),
                    1 if not spread else MAX_PENDING_PUBLICATIONS,
                )
                scheduled.run()
                receipts = [publication_receipt(waiter) for waiter in waiters[:-1]]
                self.assertEqual(len(receipts), MAX_PENDING_PUBLICATIONS)
                self.assertTrue(
                    all(isinstance(receipt, PublicationReceipt) for receipt in receipts)
                )
                self.assertEqual(sessions[0].names()[0], "ui_snapshot")

    def test_explicit_synchronization_never_joins_the_active_group(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        with publication_group() as group:
            deferred = coordinator.synchronize(_context())
            self.assertNotIn(group.id, coordinator._pending_groups)
        self.assertEqual(len(coordinator._pending_groups), 1, "the sync made its own entry")
        scheduled.run()
        self.assertEqual(publication_receipt(deferred).kind, "snapshot")
        self.assertEqual(sessions[0].names(), ["ui_snapshot"])

    def test_later_asynchronous_work_is_a_distinct_ordered_publication(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        group = new_publication_group()
        state["value"] = 2
        coordinator.enqueue_publication(
            _context, affected_panels={"status"}, group_id=group.id
        )
        scheduled.run()
        self.assertEqual(sessions[0].frames("ui_update")[-1]["revision"], 2)
        state["value"] = 3
        later = coordinator.enqueue_publication(
            _context,
            candidate_panels={"status": {"available": True, "value": 3}},
        )
        scheduled.run()
        receipt = publication_receipt(later)
        self.assertEqual(receipt.kind, "delta")
        self.assertEqual(receipt.revision, 3)
        self.assertEqual(sessions[0].frames("ui_update")[-1]["base_revision"], 2)

    def test_a_result_only_group_is_flushed_before_a_scheduled_retirement(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        retire = Clock()
        retire.callLater(0, coordinator.reset)
        group = new_publication_group()
        deferred = coordinator.enqueue_publication(
            _context,
            result_only=True,
            completion=_completion("r1"),
            group_id=group.id,
        )
        coordinator.flush_publication_group(group.id)
        self.assertEqual(sessions[0].names(), ["ui_action_result"])
        self.assertIsNotNone(publication_receipt(deferred))
        retire.advance(0)
        self.assertEqual(sessions[0].names(), ["ui_action_result"])

    def test_reentrant_sync_during_a_send_receives_its_own_later_receipt(self):
        state, sessions, coordinators, scheduled = self._two_watchers()
        coordinator = coordinators[0]
        state["value"] = 2
        inner: list = []

        def interpose(name, envelope):
            if inner:
                return
            state["value"] = 3
            inner.append(coordinator.enqueue_publication(_context, independent=True))

        sessions[0].on_send = interpose
        outer = coordinator.enqueue_publication(_context, affected_panels={"status"})
        scheduled.run()
        sessions[0].on_send = None
        outer_receipt = publication_receipt(outer)
        inner_receipt = publication_receipt(inner[0])
        self.assertEqual(outer_receipt.kind, "delta")
        self.assertGreater(inner_receipt.revision, outer_receipt.revision)
        self.assertEqual(
            [frame["revision"] for frame in sessions[0].frames()],
            [outer_receipt.revision, inner_receipt.revision],
        )


class TextIngressIndependenceTests(unittest.TestCase):
    """Overlapping text Deferreds settle independently, in completion order."""

    def setUp(self):
        self.state = {"value": 1}
        self.session = FakeSession()
        self.actor = SimpleNamespace(pk=1, key="actor")
        self.session.puppet = self.actor
        self.session.ndb.elosern_actor_id = "1"
        self.scheduler = QueuedScheduler()
        self.coordinator = _coordinator(
            self.session, _state_registry(self.state), scheduler=self.scheduler
        )
        self.coordinator.full_snapshot(_context(self.actor))
        self.scheduler.run()
        self.session.sent.clear()

    def test_two_text_commands_settle_in_reverse_order(self):
        first = Deferred()
        second = Deferred()
        observe_command_settlement(first, self.session)
        observe_command_settlement(second, self.session)
        self.state["value"] = 2
        second.callback("second")
        self.state["value"] = 3
        first.callback("first")
        self.assertEqual(second.result, "second")
        self.assertEqual(first.result, "first")
        self.assertEqual(self.session.sent, [], "the refreshes wait for the boundary")
        self.assertEqual(len(self.coordinator._pending_groups), 2, "one entry per command")
        self.scheduler.run()
        updates = self.session.frames("ui_update")
        self.assertEqual(len(updates), 1, "both refreshes compare the same current state")
        self.assertEqual(updates[0]["panels"]["status"]["value"], 3)

    def test_a_failed_command_preserves_its_failure_and_still_refreshes(self):
        pending = Deferred()
        observe_command_settlement(pending, self.session)
        self.state["value"] = 2
        pending.errback(RuntimeError("command failed"))
        self.scheduler.run()
        self.assertIsInstance(pending.result, Failure)
        self.assertTrue(pending.result.check(RuntimeError))
        self.assertEqual(self.session.names(), ["ui_update"])
        # The command's own Deferred still carries its Failure; the observer is
        # non-consuming, so a real caller owns that error exactly as before.
        pending.addErrback(lambda failure: None)

    def test_text_during_a_pending_graphical_adapter_stays_available(self):
        graphical_group = new_publication_group()
        with publication_group(graphical_group):
            self.coordinator.enqueue_publication(
                lambda: _context(self.actor),
                affected_panels={"status"},
                group_id=graphical_group.id,
            )
        text = Deferred()
        observe_command_settlement(text, self.session)
        self.state["value"] = 5
        text.callback("text")
        self.assertEqual(text.result, "text", "text is never blocked or rejected")
        self.assertEqual(self.session.sent, [], "nothing publishes before the boundary")
        self.assertEqual(
            len(self.coordinator._pending_groups),
            2,
            "the command group and the text refresh are separate entries",
        )
        self.scheduler.run()
        self.assertEqual(self.session.names(), ["ui_update"])
        self.coordinator.enqueue_publication(
            lambda: _context(self.actor), force_snapshot=True, independent=True
        )
        self.assertTrue(
            self.coordinator._pending_groups,
            "the sync is its own entry, not merged into a completed one",
        )
        self.scheduler.run()
        self.assertEqual(self.session.names(), ["ui_update", "ui_snapshot"])


class DispatcherGroupTests(unittest.TestCase):
    """Graphical completion capture, private slot stripping and result order."""

    def setUp(self):
        from web.webclient.actions.tests.test_dispatcher._support import (
            FakeSession as ActionSession,
            FakeActor,
            _coordinator as action_coordinator,
            _presenter_registry,
        )

        self.actor = FakeActor()
        self.registry = _presenter_registry()
        self.session = ActionSession()
        self.session.sessid = 3
        self.session.puppet = self.actor
        self.coordinator = action_coordinator(self.session, self.registry)

    def _run(self, adapter):
        from web.webclient.actions.dispatcher import handle_ui_action
        from web.webclient.actions.registry import ActionRegistry
        from web.webclient.actions.tests.test_dispatcher._support import _proof_spec

        registry = ActionRegistry("test")
        registry.register(_proof_spec(adapter=adapter))
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": self.coordinator.epoch,
            "request_id": "req-1",
            "base_revision": self.coordinator.revision,
            "action_id": "proof.noop",
            "payload": {},
        }
        handle_ui_action(
            self.session, self.actor, envelope, registry, self.registry
        )

    def test_result_frames_follow_the_presentation_frames(self):
        def adapter(actor, payload, session=None):
            return {
                "outcome": "success",
                "code": "ok",
                "message": "done",
                "affected_panels": ("status",),
            }

        self._run(adapter)
        self.assertEqual(list(self.session.sent[0]), ["ui_snapshot"])
        self.assertEqual(list(self.session.sent[-1]), ["ui_action_result"])
        self.assertFalse(_in_flight(self.session))

    def test_the_private_group_slot_never_reaches_the_wire(self):
        def adapter(actor, payload, session=None):
            group = new_publication_group()
            return {
                "outcome": "success",
                "code": "ok",
                "message": "done",
                "affected_panels": ("status",),
                "publication_group_id": group.id,
            }

        self._run(adapter)
        result = self.session.sent[-1]["ui_action_result"][0][0]
        self.assertNotIn("publication_group_id", result)
        self.assertEqual(
            set(result),
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

    def test_a_result_only_completion_leaves_before_its_retirement(self):
        retire = Clock()
        retire.callLater(0, self.coordinator.reset)

        def adapter(actor, payload, session=None):
            return {
                "outcome": "success",
                "code": "ok",
                "message": "done",
                "no_presentation": True,
            }

        self._run(adapter)
        self.assertEqual(list(self.session.sent[-1]), ["ui_action_result"])
        sent_before = list(self.session.sent)
        retire.advance(0)
        self.assertEqual(self.session.sent, sent_before)

    def test_a_pending_adapter_does_not_inherit_the_invocation_group(self):
        held = Deferred()
        seen: list = []

        def adapter(actor, payload, session=None):
            return held

        self._run(adapter)
        self.assertIsNone(current_publication_group())
        held.addCallback(lambda value: seen.append(current_publication_group()))
        held.callback(
            {
                "outcome": "success",
                "code": "ok",
                "message": "done",
                "affected_panels": ("status",),
            }
        )
        self.assertEqual(seen, [None])
        self.assertEqual(list(self.session.sent[-1]), ["ui_action_result"])


def _in_flight(session):
    from web.webclient.actions.dispatcher import _sequence_state

    return _sequence_state(session).in_flight


class AlignmentDeliveryTests(EvenniaTest):
    """Committed facts reach every lawful watcher through the production API."""

    def setUp(self):
        super().setUp()
        import evennia

        from web.webclient.presentation import alignment
        from web.webclient.presentation.ingress import (
            build_presentation_context,
            build_production_registry,
        )
        from web.webclient.presentation.watchers import clear_watchers, register_watcher
        from world.rules.clock import get_world_clock

        self.build_presentation_context = build_presentation_context
        self.register_watcher = register_watcher
        clear_alignment_observers()
        clear_watchers()
        alignment.connect_alignment_observer()
        self.addCleanup(clear_alignment_observers)
        self.addCleanup(clear_watchers)
        get_world_clock()
        self.char1.location = self.room1
        self.sessions = []
        for index in (0, 1):
            session = FakeSession(sessid=40 + index)
            session.puppet = self.char1
            self.sessions.append(session)
        self.sessionhandler = mock.patch.object(
            evennia.SESSION_HANDLER, "get_sessions", return_value=list(self.sessions)
        )
        self.sessionhandler.start()
        self.addCleanup(self.sessionhandler.stop)
        self.schedulers = []
        for session in self.sessions:
            scheduler = QueuedScheduler()
            self.schedulers.append(scheduler)
            _coordinator(
                session, build_production_registry(), scheduler=scheduler
            )

    def _prime(self):
        for session, scheduler in zip(self.sessions, self.schedulers):
            coordinator = session.ndb.elosern_coordinator
            coordinator.full_snapshot(
                self.build_presentation_context(session, self.char1)
            )
            self.register_watcher(session)
            scheduler.run()
            session.sent.clear()

    def _commit(self, *, push_first):
        from web.webclient.presentation.party_push import push_party_update

        def push():
            push_party_update(self.char1)

        with self.captureOnCommitCallbacks(execute=True):
            with publication_group() as group:
                def fact():
                    emit_alignment_fact(
                        PresentationAlignmentFact(
                            group_id=group.id,
                            actor_id=int(self.char1.pk),
                            cause="movement_boundary",
                        )
                    )

                if push_first:
                    on_publication_commit(push)
                    on_publication_commit(fact)
                else:
                    on_publication_commit(fact)
                    on_publication_commit(push)
        return group

    def _drain(self):
        for scheduler in self.schedulers:
            scheduler.run()

    def test_push_and_fact_coalesce_into_one_snapshot_per_watcher(self):
        for push_first in (True, False):
            with self.subTest(push_first=push_first):
                self._prime()
                before = [
                    session.ndb.elosern_coordinator.revision
                    for session in self.sessions
                ]
                self._commit(push_first=push_first)
                for session in self.sessions:
                    coordinator = session.ndb.elosern_coordinator
                    self.assertTrue(
                        coordinator._pending_groups,
                        "the commit queued one group entry per watcher",
                    )
                    self.assertEqual(session.sent, [], "frames wait for the boundary")
                self._drain()
                for session, previous in zip(self.sessions, before):
                    self.assertEqual(session.names(), ["ui_snapshot"])
                    self.assertEqual(session.frames("ui_update"), [])
                    self.assertEqual(
                        session.frames("ui_snapshot")[0]["revision"], previous + 1
                    )

    def test_a_fact_only_group_still_publishes_one_snapshot(self):
        self._prime()
        with self.captureOnCommitCallbacks(execute=True):
            with publication_group() as group:
                on_publication_commit(
                    lambda: emit_alignment_fact(
                        PresentationAlignmentFact(
                            group_id=group.id,
                            actor_id=int(self.char1.pk),
                            cause="combat_terminal",
                        )
                    )
                )
        self._drain()
        for session in self.sessions:
            self.assertEqual(session.names(), ["ui_snapshot"])

    def test_a_rolled_back_commit_publishes_nothing(self):
        self._prime()
        from web.webclient.presentation.party_push import push_party_update

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            with transaction.atomic():
                with publication_group() as group:
                    on_publication_commit(lambda: push_party_update(self.char1))
                    on_publication_commit(
                        lambda: emit_alignment_fact(
                            PresentationAlignmentFact(
                                group_id=group.id,
                                actor_id=int(self.char1.pk),
                                cause="skip_completed",
                            )
                        )
                    )
                transaction.set_rollback(True)
        self.assertEqual(callbacks, [])
        self._drain()
        for session in self.sessions:
            self.assertEqual(session.sent, [])


class RollbackSilenceTests(EvenniaTest):
    """A rolled-back transaction commits no presentation intent at all."""

    def test_rollback_discards_the_registered_callback(self):
        recorded: list = []
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            with transaction.atomic():
                on_publication_commit(lambda: recorded.append(1))
                transaction.set_rollback(True)
        self.assertEqual(callbacks, [])
        self.assertEqual(recorded, [])

    def test_commit_runs_the_callback_inside_its_captured_group(self):
        observed: list = []
        with self.captureOnCommitCallbacks(execute=True):
            with publication_group() as group:
                on_publication_commit(
                    lambda: observed.append(current_publication_group())
                )
        self.assertEqual(len(observed), 1)
        self.assertIs(observed[0], group)
        self.assertIsNone(current_publication_group())

    def test_a_commit_callback_keeps_its_captured_group_under_another_ambient_one(self):
        observed: list = []
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            with publication_group() as captured:
                on_publication_commit(
                    lambda: observed.append(current_publication_group())
                )
        self.assertEqual(len(callbacks), 1)
        with publication_group() as ambient:
            for callback in callbacks:
                callback()
        self.assertEqual(len(observed), 1)
        self.assertIs(observed[0], captured)
        self.assertIsNot(observed[0], ambient)
        self.assertIsNone(current_publication_group())


if __name__ == "__main__":
    unittest.main()
