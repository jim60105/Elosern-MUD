"""Snapshot coordinator and presenter isolation tests (foundation 1.3/1.4)."""

from types import SimpleNamespace
import unittest

from tools.spec_traceability import covers_requirement

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import (
    ClockUnavailable,
    PresentationCoordinator,
)
from web.webclient.presentation.protocol import (
    PROTOCOL_VERSION,
    new_presentation_epoch,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    PresenterSpec,
    PresentationRegistry,
)

LAYOUT_VERSION = 1


class FakeSession:
    def __init__(self):
        self.sent = []

    def msg(self, **kwargs):
        self.sent.append(kwargs)

    @property
    def sessid(self):
        return 7


class FakeActor:
    def __init__(self, *, creation_pending=False, in_combat=False, key="a", pk=1):
        self.creation_pending = creation_pending
        self._in_combat = in_combat
        self.key = key
        self.pk = pk
        self.location = None

    def is_in_active_session(self):
        return self._in_combat


class FakeClockCalendar:
    year = 1204
    season_index = 2
    season_name = "仲夏"
    day_in_season = 17
    hour = 14
    minute = 30
    second = 5


def _context(actor=None):
    return PresentationContext(actor=actor or FakeActor(), protocol_version=1)


def _coordinator(session, registry, **kwargs):
    defaults = {
        "calendar_provider": lambda: FakeClockCalendar(),
        "mode_provider": lambda ctx: "exploration",
    }
    defaults.update(kwargs)
    return PresentationCoordinator(session, registry, **defaults)


def _available_payload(**fields):
    value = {"available": True}
    value.update(fields)
    return value


def _registry(*specs):
    registry = PresentationRegistry("test")
    for spec in specs:
        registry.register(spec)
    return registry


def _status_spec(presenter=None):
    return PresenterSpec(
        name="status",
        schema_version=1,
        unavailable_reason=("missing_data", "無法讀取角色資料"),
        presenter=presenter or (lambda context: _available_payload(value=1)),
    )


class CoordinatorBasicsTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::presentation-ordering-is-scoped-by-transport-and-puppet-epoch"
    )
    def test_coordinator_creates_epoch_and_monotonic_revisions(self):
        session = FakeSession()
        coordinator = _coordinator(session, _registry(_status_spec()))
        self.assertEqual(len(coordinator.epoch), 22)
        coordinator.full_snapshot(_context())
        coordinator.full_snapshot(_context())
        self.assertEqual(coordinator.revision, 2)
        messages = session.sent
        self.assertEqual(messages[0]["ui_snapshot"][0][0]["revision"], 1)
        self.assertEqual(messages[1]["ui_snapshot"][0][0]["revision"], 2)
        self.assertEqual(
            messages[1]["ui_snapshot"][0][0]["presentation_epoch"],
            coordinator.epoch,
        )

    @covers_requirement(
        "webclient-oob-protocol::presentation-ordering-is-scoped-by-transport-and-puppet-epoch"
    )
    def test_reset_starts_a_new_epoch_and_revision_sequence(self):
        session = FakeSession()
        coordinator = _coordinator(session, _registry(_status_spec()))
        old_epoch = coordinator.epoch
        coordinator.full_snapshot(_context())
        coordinator.reset()
        self.assertNotEqual(coordinator.epoch, old_epoch)
        self.assertEqual(coordinator.revision, 0)
        coordinator.full_snapshot(_context())
        envelope = session.sent[-1]["ui_snapshot"][0][0]
        self.assertEqual(envelope["revision"], 1)
        self.assertEqual(envelope["presentation_epoch"], coordinator.epoch)

    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    def test_snapshot_contains_exact_metadata_and_all_panels(self):
        session = FakeSession()
        coordinator = _coordinator(session, _registry(_status_spec()))
        coordinator.full_snapshot(_context())
        envelope = session.sent[0]["ui_snapshot"][0][0]
        self.assertEqual(envelope["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(envelope["mode"], "exploration")
        self.assertEqual(envelope["layout_version"], LAYOUT_VERSION)
        self.assertEqual(set(envelope["panels"]), {"status"})
        self.assertEqual(
            envelope["server_time"]["season_label"], "仲夏"
        )
        self.assertEqual(envelope["server_time"]["day_in_season"], 17)

    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    def test_over_budget_envelope_rejects_before_revision_consumption_or_send(self):
        from web.webclient.presentation.protocol import JSONSafetyError

        from web.webclient.presentation.tests._support import publication_failure

        session = FakeSession()
        over_spec = PresenterSpec(
            name="status",
            schema_version=1,
            unavailable_reason=("missing_data", "無法讀取角色資料"),
            presenter=lambda context: {"available": True, **{f"pad_{i}": "x" * 1500 for i in range(50)}},
        )
        coordinator = _coordinator(session, _registry(over_spec))
        self.assertEqual(coordinator.revision, 0)
        publication_failure(coordinator.full_snapshot(_context())).trap(JSONSafetyError)
        self.assertEqual(coordinator.revision, 0)
        self.assertEqual(len(session.sent), 0)

        publication_failure(
            coordinator.panel_update(
                _context(), {"status": {f"pad_{i}": "x" * 1500 for i in range(50)}}
            )
        ).trap(JSONSafetyError)
        self.assertEqual(coordinator.revision, 0)
        self.assertEqual(len(session.sent), 0)

    def test_mode_derivation_uses_injected_provider(self):
        context = _context()
        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(_status_spec()),
            mode_provider=lambda ctx: "combat",
        )
        coordinator.full_snapshot(context)
        envelope = session.sent[0]["ui_snapshot"][0][0]
        self.assertEqual(envelope["mode"], "combat")

    def test_panel_update_completely_replaces_named_panels(self):
        session = FakeSession()
        coordinator = _coordinator(session, _registry(_status_spec()))
        # A delta requires the exact committed baseline: establish it first
        # and record only the publication under assertion.
        coordinator.full_snapshot(_context())
        session.sent.clear()
        coordinator.panel_update(_context(), {"status": _available_payload(value=9)})
        envelope = session.sent[0]["ui_update"][0][0]
        self.assertEqual(envelope["mode"], "exploration")
        self.assertEqual(envelope["panels"]["status"]["value"], 9)
        self.assertEqual(envelope["revision"], 2)
        self.assertEqual(envelope["base_revision"], 1)
        self.assertEqual(envelope["removed_panels"], [])

    def test_panel_update_removals_are_explicit_and_disjoint(self):
        from web.webclient.presentation.tests._support import (
            last_frame,
            publication_failure,
            publication_receipt,
        )

        session = FakeSession()
        coordinator = _coordinator(
            session,
            _registry(
                _status_spec(),
                PresenterSpec(
                    name="other",
                    schema_version=1,
                    unavailable_reason=("missing_data", "無法讀取角色資料"),
                    presenter=lambda context: _available_payload(),
                ),
            ),
        )
        coordinator.full_snapshot(_context())
        session.sent.clear()
        receipt = publication_receipt(
            coordinator.panel_update(_context(), {}, removed_panels=("other",))
        )
        envelope = last_frame(session, "ui_update")
        self.assertEqual(receipt.kind, "delta")
        self.assertTrue(receipt.published)
        self.assertEqual(receipt.revision, envelope["revision"])
        self.assertEqual(envelope["removed_panels"], ["other"])
        self.assertEqual(envelope["panels"], {})
        self.assertEqual(envelope["base_revision"], 1)
        self.assertEqual(envelope["revision"], 2)
        publication_failure(
            coordinator.panel_update(
                _context(),
                {"status": _available_payload(value=1)},
                removed_panels=("status",),
            )
        ).trap(ValueError)
        publication_failure(
            coordinator.panel_update(_context(), {}, removed_panels=("unknown",))
        ).trap(ValueError)
        publication_failure(
            coordinator.panel_update(_context(), {}, removed_panels=("area_map",))
        ).trap(ValueError)
        self.assertEqual(coordinator.revision, 2)

    def test_panel_update_rejects_empty_and_unknown(self):
        from web.webclient.presentation.tests._support import publication_failure

        session = FakeSession()
        coordinator = _coordinator(session, _registry(_status_spec()))
        publication_failure(coordinator.panel_update(_context(), {})).trap(ValueError)
        publication_failure(
            coordinator.panel_update(_context(), {"unknown": {}})
        ).trap(ValueError)

    def test_missing_clock_raises(self):
        from web.webclient.presentation.tests._support import publication_failure

        session = FakeSession()
        coordinator = _coordinator(session, _registry(_status_spec()), calendar_provider=lambda: None)
        publication_failure(coordinator.full_snapshot(_context())).trap(ClockUnavailable)


class IsolationTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only"
    )
    def test_one_broken_presenter_does_not_suppress_others(self):
        def broken(context):
            raise RuntimeError("boom")

        registry = _registry(
            _status_spec(presenter=broken),
            PresenterSpec(
                name="other",
                schema_version=1,
                unavailable_reason=("missing_data", "無法讀取角色資料"),
                presenter=lambda context: _available_payload(ok=True),
            ),
        )
        session = FakeSession()
        coordinator = _coordinator(session, registry)
        coordinator.full_snapshot(_context())
        panels = session.sent[0]["ui_snapshot"][0][0]["panels"]
        self.assertEqual(panels["other"], {"available": True, "ok": True})
        self.assertFalse(panels["status"]["available"])
        self.assertEqual(
            panels["status"]["reason"]["code"], "internal_presenter_error"
        )
        self.assertEqual(
            len(panels["status"]["reason"]["correlation_id"]), 32
        )
        self.assertNotIn("boom", repr(panels))

    def test_panel_unavailable_uses_non_internal_reason(self):
        def unavailable(context):
            raise PanelUnavailableError

        registry = _registry(_status_spec(presenter=unavailable))
        session = FakeSession()
        coordinator = _coordinator(session, registry)
        coordinator.full_snapshot(_context())
        panel = session.sent[0]["ui_snapshot"][0][0]["panels"]["status"]
        self.assertFalse(panel["available"])
        self.assertEqual(panel["reason"]["code"], "missing_data")
        self.assertNotIn("correlation_id", panel["reason"])

    @covers_requirement(
        "webclient-oob-protocol::every-panel-payload-has-an-exact-availability-discriminator"
    )
    def test_narrative_output_is_not_suppressed_by_panel_failure(self):
        # A presenter failure must not raise out of snapshot building; the
        # coordinator returns a complete envelope regardless.
        registry = _registry(
            _status_spec(presenter=lambda context: (_ for _ in ()).throw(RuntimeError("x")))
        )
        session = FakeSession()
        coordinator = _coordinator(session, registry)
        coordinator.full_snapshot(_context())
        self.assertEqual(len(session.sent), 1)


if __name__ == "__main__":
    unittest.main()
