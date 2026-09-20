"""Shared module-level helpers for the ``test_dispatcher`` test package."""


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
    validate_ui_action_result,
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


def _sequence_state_for_test(session):
    from web.webclient.actions.dispatcher import _sequence_state

    return _sequence_state(session)
