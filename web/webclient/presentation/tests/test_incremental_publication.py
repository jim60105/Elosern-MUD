"""Content-aware publication baseline: comparison, receipts and the one owner.

These are the focused behavior tests for the incremental publication slice:
JSON value comparison, isolated per-session baselines, difference-only
transmission, unchanged publications consuming no revision, preflight before
the first send, partial-send invalidation, receipts, retirement and the
serialized batch boundary.
"""

from collections import deque
from types import SimpleNamespace
import unittest

from tools.spec_traceability import covers_requirement

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import (
    MAX_PENDING_PUBLICATIONS,
    PresentationCoordinator,
    PresentationQueueFull,
    ResultDeliveryError,
)
from web.webclient.presentation.publication import (
    PublicationCompletion,
    PublicationReceipt,
    copy_json_value,
    json_value_equal,
)
from web.webclient.presentation.registry import PresenterSpec, PresentationRegistry
from web.webclient.presentation.tests._support import (
    publication_failure,
    publication_receipt,
    publication_result,
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

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.ndb = SimpleNamespace()
        self.puppet = None
        self.sessid = 7
        #: Optional ``(message_name, envelope, call_index)`` hook run before
        #: the frame is recorded; it may raise to inject a send fault.
        self.on_send = None
        self._sends = 0

    def msg(self, **kwargs) -> None:
        (name, payload) = next(iter(kwargs.items()))
        envelope = payload[0][0]
        self._sends += 1
        if self.on_send is not None:
            self.on_send(name, envelope, self._sends)
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


def _coordinator(session, registry, *, mode="exploration", calendar=_calendar):
    return PresentationCoordinator(
        session,
        registry,
        calendar_provider=calendar,
        mode_provider=lambda context: mode,
    )


def _completion(request_id="r1", **result):
    payload = {"outcome": "success", "code": "ok", "message": "完成"}
    payload.update(result)
    owned = copy_json_value(payload)

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


class JsonValueSemanticsTests(unittest.TestCase):
    """The comparator and the owned-copy contract."""

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_object_key_order_is_irrelevant(self):
        self.assertTrue(
            json_value_equal({"a": 1, "b": {"c": 2, "d": 3}}, {"b": {"d": 3, "c": 2}, "a": 1})
        )

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_array_order_is_significant(self):
        self.assertFalse(json_value_equal([1, 2], [2, 1]))
        self.assertFalse(json_value_equal([1, 2], [1, 2, 3]))
        self.assertTrue(json_value_equal([1, {"a": 2}], [1, {"a": 2}]))

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_boolean_and_number_are_distinct(self):
        self.assertFalse(json_value_equal(True, 1))
        self.assertFalse(json_value_equal(1, True))
        self.assertTrue(json_value_equal(True, True))

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_numbers_share_one_type(self):
        self.assertTrue(json_value_equal(1, 1.0))
        self.assertFalse(json_value_equal(1, 2))
        self.assertFalse(json_value_equal("1", 1))
        self.assertFalse(json_value_equal(None, False))

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_object_key_sets_must_match(self):
        self.assertFalse(json_value_equal({"a": 1}, {"a": 1, "b": 2}))
        self.assertFalse(json_value_equal({"a": 1}, {"b": 1}))

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_copy_owns_nested_containers(self):
        shared = [{"rows": [1, 2]}]
        owned = copy_json_value(shared)
        shared[0]["rows"].append(3)
        shared.append({"extra": True})
        self.assertEqual(owned, [{"rows": [1, 2]}])
        self.assertEqual(copy_json_value((1, 2)), [1, 2])
        with self.assertRaises(TypeError):
            copy_json_value(object())


class CandidateComparisonTests(unittest.TestCase):
    """Only real JSON differences reach the wire."""

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_reordered_dictionary_keys_are_suppressed(self):
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True, "a": 1, "b": 2}))
        )
        self.assertTrue(publication_receipt(coordinator.full_snapshot(_context())).published)
        session.sent.clear()
        receipt = publication_receipt(
            coordinator.panel_update(
                _context(), {"status": {"available": True, "b": 2, "a": 1}}
            )
        )
        self.assertEqual(receipt.kind, "unchanged")
        self.assertFalse(receipt.published)
        self.assertEqual(session.sent, [])
        self.assertEqual(coordinator.revision, 1)

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_list_order_and_boolean_changes_are_published(self):
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True, "rows": [1, 2]}))
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        publication_receipt(
            coordinator.panel_update(_context(), {"status": {"available": True, "rows": [2, 1]}})
        )
        self.assertEqual(session.frames("ui_update")[-1]["panels"]["status"]["rows"], [2, 1])

        publication_receipt(
            coordinator.panel_update(_context(), {"status": {"available": True, "flag": True}})
        )
        publication_receipt(
            coordinator.panel_update(_context(), {"status": {"available": True, "flag": 1}})
        )
        frames = session.frames("ui_update")
        self.assertIs(frames[-2]["panels"]["status"]["flag"], True)
        self.assertEqual(frames[-1]["panels"]["status"]["flag"], 1)

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_integral_float_candidate_matches_the_integer_baseline(self):
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True, "value": 1}))
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        receipt = publication_receipt(
            coordinator.panel_update(_context(), {"status": {"available": True, "value": 1.0}})
        )
        self.assertFalse(receipt.published)

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_presenter_alias_mutation_cannot_corrupt_the_baseline(self):
        rows = [1, 2]
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True, "rows": rows}))
        )
        coordinator.full_snapshot(_context())
        # The presenter keeps handing back the same mutable list; the baseline
        # owns its own copy, so a later mutation is a real difference.
        rows.append(3)
        session.sent.clear()
        receipt = publication_receipt(coordinator.enqueue_publication(_context))
        self.assertTrue(receipt.published)
        self.assertEqual(
            session.frames("ui_update")[-1]["panels"]["status"]["rows"], [1, 2, 3]
        )
        # And the committed value is not the presenter's object either.
        rows.append(4)
        self.assertEqual(coordinator.committed_panels["status"]["rows"], [1, 2, 3])
        # The diagnostic read is a copy too: mutating it never moves the
        # baseline, so the next comparison still sees the published content.
        snapshot = coordinator.committed_panels
        snapshot["status"]["rows"].append(5)
        receipt = publication_receipt(coordinator.enqueue_publication(_context))
        self.assertTrue(receipt.published)
        self.assertEqual(
            session.frames("ui_update")[-1]["panels"]["status"]["rows"],
            [1, 2, 3, 4],
            "the mutated diagnostic copy never entered the baseline",
        )

    def test_unavailable_replacement_is_not_a_removal(self):
        from web.webclient.presentation.registry import PanelUnavailableError

        state = {"available": True}

        def status(context):
            if not state["available"]:
                raise PanelUnavailableError("gone")
            return {"available": True, "value": 1}

        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", status))
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        state["available"] = False
        publication_receipt(
            coordinator.enqueue_publication(_context, affected_panels={"status"})
        )
        delta = session.frames("ui_update")[-1]
        # A registered presenter returning unavailable is a replacement: the
        # panel stays committed with its unavailable form and is never removed.
        self.assertEqual(delta["removed_panels"], [])
        replacement = delta["panels"]["status"]
        self.assertIs(replacement["available"], False)
        self.assertEqual(
            coordinator.committed_panels["status"], replacement
        )

    @covers_requirement(
        "webclient-incremental-publication::candidate-equality-follows-json-value-semantics"
    )
    def test_unchanged_candidates_are_omitted_and_untouched_panels_preserved(self):
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec("status", lambda context: {"available": True, "value": 1}),
                _spec("party", lambda context: {"available": True, "slots": []}),
            ),
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        publication_receipt(
            coordinator.panel_update(
                _context(),
                {
                    "status": {"available": True, "value": 1},
                    "party": {"available": True, "slots": [7]},
                },
            )
        )
        delta = session.frames("ui_update")[-1]
        self.assertEqual(set(delta["panels"]), {"party"})
        self.assertEqual(coordinator.committed_panels["status"], {"available": True, "value": 1})


class UnknownScopeTests(unittest.TestCase):
    """An absent declaration re-renders every eager panel, never maps."""

    @covers_requirement(
        "webclient-incremental-publication::unknown-scope-recomputes-all-eager-panels-without-full-retransmission"
    )
    def test_unknown_scope_renders_each_eager_panel_and_sends_only_differences(self):
        renders: dict[str, int] = {"status": 0, "party": 0, "area_map": 0}
        changed = {"value": 1}

        def status(context):
            renders["status"] += 1
            return {"available": True, "value": changed["value"]}

        def party(context):
            renders["party"] += 1
            return {"available": True, "slots": []}

        def area_map(context):
            renders["area_map"] += 1
            return {"available": True}

        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec("status", status),
                _spec("party", party),
                _spec("area_map", area_map, on_demand=True),
            ),
        )
        coordinator.full_snapshot(_context())
        self.assertEqual(renders, {"status": 1, "party": 1, "area_map": 0})
        renders.update({"status": 0, "party": 0})
        session.sent.clear()
        changed["value"] = 2
        receipt = publication_receipt(coordinator.enqueue_publication(_context))
        self.assertEqual(renders, {"status": 1, "party": 1, "area_map": 0})
        delta = session.frames("ui_update")[-1]
        self.assertEqual(set(delta["panels"]), {"status"})
        self.assertEqual(delta["base_revision"], 1)
        self.assertEqual(receipt.revision, 2)

    @covers_requirement(
        "webclient-incremental-publication::unknown-scope-recomputes-all-eager-panels-without-full-retransmission"
    )
    def test_unchanged_dialogue_companion_stays_consistent(self):
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec("status", lambda context: {"available": True, "value": 1}),
                _spec("dialogue", lambda context: {"available": True, "line": "hi"}),
            ),
            mode="dialogue",
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        publication_receipt(
            coordinator.panel_update(_context(), {"status": {"available": True, "value": 2}})
        )
        delta = session.frames("ui_update")[-1]
        # The dialogue panel was a candidate (mode dialogue) but renders equal,
        # so it is omitted while the staged mode/dialogue pair stays consistent.
        self.assertEqual(set(delta["panels"]), {"status"})
        self.assertEqual(delta["mode"], "dialogue")
        self.assertEqual(
            coordinator.committed_panels["dialogue"], {"available": True, "line": "hi"}
        )


class BaselineOwnershipTests(unittest.TestCase):
    """One isolated baseline per live sequence; no reuse after failure."""

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_two_viewers_keep_isolated_baselines(self):
        calls = {"value": 1}

        def status(context):
            return {"available": True, "value": calls["value"]}

        registry = _registry(_spec("status", status))
        first, second = FakeSession(), FakeSession()
        one = _coordinator(first, registry)
        two = _coordinator(second, registry)
        one.full_snapshot(_context())
        calls["value"] = 2
        two.full_snapshot(_context())
        calls["value"] = 3
        first.sent.clear()
        second.sent.clear()

        publication_receipt(one.enqueue_publication(_context))
        self.assertEqual(first.frames("ui_update")[-1]["base_revision"], 1)
        self.assertEqual(second.sent, [])

        calls["value"] = 4
        publication_receipt(two.enqueue_publication(_context))
        self.assertEqual(second.frames("ui_update")[-1]["base_revision"], 1)
        self.assertEqual(one.revision, 2)
        self.assertEqual(two.revision, 2)

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_preflight_failure_sends_nothing_and_consumes_no_revision(self):
        # Over-budget aggregates now travel as bounded parts; a structurally
        # invalid candidate (a 2,100-code-point string) still fails preflight.
        oversized = {
            "available": True,
            **{f"pad_{index}": "x" * 1500 for index in range(50)},
            "overflow": "x" * 2100,
        }
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True}))
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        before = coordinator.revision
        publication_failure(
            coordinator.panel_update(_context(), {"status": oversized})
        ).trap(Exception)
        self.assertEqual(session.sent, [])
        self.assertEqual(coordinator.revision, before)
        self.assertEqual(coordinator.published_revision, before)

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_partial_send_invalidates_the_baseline_and_never_reuses_the_target(self):
        def dense(context):
            body = {
                "available": True,
                "nodes": [{"id": index} for index in range(400)],
            }
            return body

        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec("status", lambda context: {"available": True, "value": 1}),
                _spec("area_map", dense, on_demand=True),
            ),
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()

        def fail_second_send(name, envelope, index):
            if index == 2:
                raise RuntimeError("socket gone")

        session.on_send = fail_second_send
        publication_failure(
            coordinator.enqueue_publication(_context, affected_panels={"area_map"})
        ).trap(RuntimeError)
        escaped = coordinator.revision
        self.assertGreater(escaped, 1)
        # The issued target escaped the transport, so it can never be reused
        # and the incomplete publication can never be a delta base.
        self.assertEqual(coordinator.published_revision, escaped)
        self.assertEqual(coordinator.committed_panels, {})

        session.on_send = None
        session.sent.clear()
        receipt = publication_receipt(coordinator.enqueue_publication(_context))
        self.assertEqual(receipt.kind, "snapshot")
        self.assertEqual(receipt.revision, escaped + 1)
        self.assertGreater(receipt.revision, escaped)

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_unchanged_completion_consumes_no_revision_and_orders_the_result(self):
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True}))
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        receipt = publication_receipt(
            coordinator.enqueue_publication(
                _context,
                affected_panels={"status"},
                completion=_completion(),
            )
        )
        self.assertEqual(receipt.kind, "unchanged")
        self.assertFalse(receipt.published)
        self.assertEqual(session.names(), ["ui_action_result"])
        self.assertEqual(session.frames("ui_action_result")[-1]["presentation_revision"], 1)
        self.assertEqual(coordinator.revision, 1)

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_metadata_only_change_advances_the_revision(self):
        clock = SimpleNamespace(**{
            key: getattr(_Calendar, key)
            for key in ("year", "season_index", "season_name", "day_in_season", "hour", "minute", "second")
        })
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(_spec("status", lambda context: {"available": True})),
            calendar=lambda: clock,
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        clock.minute = 31
        receipt = publication_receipt(coordinator.enqueue_publication(_context))
        self.assertEqual(receipt.kind, "delta")
        delta = session.frames("ui_update")[-1]
        self.assertEqual(delta["panels"], {})
        self.assertEqual(delta["removed_panels"], [])
        self.assertEqual(delta["server_time"]["minute"], 31)
        self.assertEqual(delta["revision"], 2)

    def test_explicit_removal_is_transmitted_and_absent_removal_is_suppressed(self):
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec("status", lambda context: {"available": True}),
                _spec("party", lambda context: {"available": True}),
            ),
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        receipt = publication_receipt(
            coordinator.enqueue_publication(
                _context, affected_panels={"status"}, removed_panels=("party",)
            )
        )
        self.assertTrue(receipt.published)
        delta = session.frames("ui_update")[-1]
        self.assertEqual(delta["removed_panels"], ["party"])
        self.assertEqual(delta["panels"], {})
        self.assertNotIn("party", coordinator.committed_panels)

        # Removing an already absent name is idempotent: no change, no revision.
        receipt = publication_receipt(
            coordinator.enqueue_publication(
                _context, affected_panels={"status"}, removed_panels=("party",)
            )
        )
        self.assertFalse(receipt.published)
        self.assertEqual(coordinator.revision, 2)

    def test_unknown_scope_never_re_renders_an_explicit_removal(self):
        state = {"value": 1}
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec(
                    "status",
                    lambda context: {"available": True, "value": state["value"]},
                ),
                _spec("party", lambda context: {"available": True, "value": 1}),
            ),
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        # The removed panel's presenter now returns different content: the
        # removal still wins, so the delta never both replaces and removes it.
        state["value"] = 2
        receipt = publication_receipt(
            coordinator.enqueue_publication(_context, removed_panels=("party",))
        )
        self.assertTrue(receipt.published)
        delta = session.frames("ui_update")[-1]
        self.assertEqual(delta["removed_panels"], ["party"])
        self.assertEqual(set(delta["panels"]), {"status"})
        self.assertNotIn("party", coordinator.committed_panels)

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_partial_send_of_a_multi_frame_publication_invalidates_the_baseline(self):
        # A schema-valid synthetic area body whose 400 edges exceed one frame's
        # list ceiling, so one logical map publication really spans many frames.
        from web.webclient.presentation.tests.test_map_panel_protocol import (
            _dense_grid,
        )

        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec("status", lambda context: {"available": True, "value": 1}),
                _spec("area_map", _dense_grid, on_demand=True),
            ),
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        sent_before = session._sends

        def fail_middle(name, envelope, index):
            # Let the eager companion delta and the first map part escape, then
            # break the next part of the same logical map publication.
            if index == sent_before + 3:
                raise RuntimeError("socket gone")

        session.on_send = fail_middle
        publication_failure(
            coordinator.enqueue_publication(
                _context,
                candidate_panels={
                    "status": {"available": True, "value": 2},
                    "area_map": _dense_grid(),
                },
            )
        ).trap(RuntimeError)
        escaped = coordinator.revision
        self.assertGreater(len(session.frames()), 1, "more than one frame escaped")
        # The issued target escaped, the incomplete publication is no baseline,
        # and the next publication repairs with a snapshot past that target.
        self.assertEqual(coordinator.committed_panels, {})
        session.on_send = None
        session.sent.clear()
        receipt = publication_receipt(coordinator.enqueue_publication(_context))
        self.assertEqual(receipt.kind, "snapshot")
        self.assertGreater(receipt.revision, escaped)

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_invalid_action_result_aborts_before_any_frame(self):
        from web.webclient.presentation.publication import PublicationCompletion

        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True, "value": 1}))
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        before = coordinator.revision
        invalid = PublicationCompletion(
            request_id="r1", result={}, envelope=lambda epoch, revision: {"bogus": True}
        )
        publication_failure(
            coordinator.enqueue_publication(
                _context,
                affected_panels={"status"},
                completion=invalid,
            )
        ).trap(Exception)
        self.assertEqual(session.sent, [])
        self.assertEqual(coordinator.revision, before)

    def test_queue_overflow_errbacks_and_invalidates_the_baseline(self):
        state = {"value": 1}
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec(
                    "status",
                    lambda context: {"available": True, "value": state["value"]},
                )
            ),
        )
        coordinator.full_snapshot(_context())
        state["value"] = 2
        session.sent.clear()
        queued: list = []

        def flood(name, envelope, index):
            if queued:
                return
            for _ in range(MAX_PENDING_PUBLICATIONS + 1):
                queued.append(
                    coordinator.enqueue_publication(
                        _context, affected_panels={"status"}
                    )
                )

        session.on_send = flood
        publication_receipt(coordinator.enqueue_publication(_context))
        failures = [
            failure
            for failure in (publication_failure_of(deferred) for deferred in queued)
            if failure is not None
        ]
        self.assertEqual(len(failures), 1, "exactly the overflowing intent is reported")
        self.assertTrue(failures[0].check(PresentationQueueFull))
        # An overflow invalidates the baseline, so the very next publication in
        # the queue repairs it with a complete snapshot instead of a delta.
        session.on_send = None
        resolved: list = []
        for deferred in queued:
            deferred.addBoth(resolved.append)
        receipts = [
            item for item in resolved if isinstance(item, PublicationReceipt)
        ]
        self.assertEqual(len(receipts), MAX_PENDING_PUBLICATIONS)
        self.assertEqual(receipts[0].kind, "snapshot")
        self.assertTrue(
            all(receipt.kind == "unchanged" for receipt in receipts[1:]),
            "the repair snapshot re-commits the unchanged publications",
        )

    def test_retired_intent_resolves_none(self):
        state = {"value": 1}
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec(
                    "status",
                    lambda context: {"available": True, "value": state["value"]},
                )
            ),
        )
        coordinator.full_snapshot(_context())
        state["value"] = 2
        session.sent.clear()
        resolutions: list = []

        def retire(name, envelope, index):
            if resolutions:
                return
            deferred = coordinator.enqueue_publication(_context)
            deferred.addBoth(resolutions.append)
            coordinator.reset()

        session.on_send = retire
        coordinator.enqueue_publication(_context)
        self.assertEqual(resolutions, [None])

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_complete_batch_cannot_interleave(self):
        state = {"value": 1}
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _spec(
                    "status",
                    lambda context: {"available": True, "value": state["value"]},
                )
            ),
        )
        coordinator.full_snapshot(_context())
        state["value"] = 2
        session.sent.clear()
        reentrant: list = []

        def interpose(name, envelope, index):
            if name != "ui_update" or reentrant:
                return
            reentrant.append(coordinator.enqueue_publication(_context, force_snapshot=True))

        session.on_send = interpose
        publication_receipt(
            coordinator.enqueue_publication(
                _context, affected_panels={"status"}, completion=_completion()
            )
        )
        names = session.names()
        # The action's presentation and its result are adjacent; the reentrant
        # snapshot follows both.
        self.assertEqual(names, ["ui_update", "ui_action_result", "ui_snapshot"])

    @covers_requirement(
        "webclient-incremental-publication::publication-baseline-belongs-to-one-live-session-sequence"
    )
    def test_result_delivery_failure_keeps_the_published_baseline(self):
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True, "value": 1}))
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()

        def fail_result(name, envelope, index):
            if name == "ui_action_result":
                raise RuntimeError("result socket gone")

        session.on_send = fail_result
        publication_failure(
            coordinator.enqueue_publication(
                _context,
                candidate_panels={"status": {"available": True, "value": 2}},
                completion=_completion(),
            )
        ).trap(ResultDeliveryError)
        # The presentation had already published completely, so the baseline is
        # valid at that revision and the next publication is a delta from it.
        self.assertEqual(coordinator.published_revision, 2)
        session.on_send = None
        receipt = publication_receipt(
            coordinator.enqueue_publication(
                _context, candidate_panels={"status": {"available": True, "value": 3}}
            )
        )
        self.assertEqual(receipt.kind, "delta")
        self.assertEqual(session.frames("ui_update")[-1]["base_revision"], 2)


def publication_failure_of(deferred):
    """The ``Failure`` a resolved publication carries, or ``None``."""
    from twisted.python.failure import Failure

    result = getattr(deferred, "result", None)
    if not isinstance(result, Failure):
        return None
    deferred.addErrback(lambda _failure: None)
    return result


class ReceiptContractTests(unittest.TestCase):
    """Receipts report what actually happened, including retirement."""

    def test_retired_epoch_publication_resolves_none(self):
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True}))
        )
        epoch = coordinator.epoch
        coordinator.reset()
        deferred = coordinator.enqueue_publication(_context, expected_epoch=epoch)
        self.assertIsNone(publication_result(deferred))
        self.assertEqual(session.sent, [])


    def test_receipt_is_frozen_and_reports_the_published_revision(self):
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True}))
        )
        receipt = publication_receipt(coordinator.full_snapshot(_context()))
        self.assertIsInstance(receipt, PublicationReceipt)
        self.assertEqual(receipt.kind, "snapshot")
        self.assertTrue(receipt.published)
        self.assertEqual(receipt.revision, 1)
        self.assertEqual(receipt.epoch, coordinator.epoch)
        with self.assertRaises(Exception):
            receipt.revision = 5  # frozen receipt: no parser, no writer

    def test_unknown_candidate_and_removal_declarations_fail_before_queueing(self):
        session = FakeSession()
        coordinator = _coordinator(
            session, _registry(_spec("status", lambda context: {"available": True}))
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        publication_failure(
            coordinator.panel_update(_context(), {"ghost": {"available": True}})
        ).trap(ValueError)
        publication_failure(
            coordinator.enqueue_publication(_context, removed_panels=("ghost",))
        ).trap(ValueError)
        publication_failure(
            coordinator.enqueue_publication(
                _context,
                candidate_panels={"status": {"available": True}},
                affected_panels={"status"},
            )
        ).trap(ValueError)
        self.assertEqual(session.sent, [])


class DispatcherCompletionTests(unittest.TestCase):
    """The dispatcher's completion path keeps its answer under overflow."""

    def test_presentation_queue_overflow_still_answers_the_admitted_action(self):
        from web.webclient.actions import dispatcher

        state = {"value": 1}
        session = FakeSession()
        registry = _registry(
            _spec("status", lambda context: {"available": True, "value": state["value"]})
        )
        coordinator = _coordinator(session, registry)
        session.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(_context())
        state["value"] = 2
        sequence = dispatcher._sequence_state(session)
        sequence.in_flight = True
        sequence.epoch = coordinator.epoch
        session.sent.clear()
        flooded: list = []

        def flood(name, envelope, index):
            if flooded:
                return
            flooded.append(True)
            for _ in range(MAX_PENDING_PUBLICATIONS):
                coordinator.enqueue_publication(_context, affected_panels={"status"})
            # An admitted completion arriving now hits the full queue.
            dispatcher._publish_completion(
                session,
                session.puppet or _context().actor,
                {
                    "outcome": "success",
                    "code": "ok",
                    "message": "完成",
                    "affected_panels": ["status"],
                },
                registry,
                "r1",
                coordinator.epoch,
            )

        session.on_send = flood
        publication_receipt(
            coordinator.enqueue_publication(
                _context, candidate_panels={"status": {"available": True, "value": 2}}
            )
        )
        session.on_send = None
        results = session.frames("ui_action_result")
        # The overflowing presentation was reported, and the admitted request
        # still received exactly one safe answer through the same owner.
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["outcome"], "error")
        self.assertFalse(dispatcher._sequence_state(session).in_flight)


if __name__ == "__main__":
    unittest.main()
