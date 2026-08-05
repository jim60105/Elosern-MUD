"""Presenter registry contract tests (foundation section 1.2)."""

import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.registry import (
    PresenterSpec,
    PresentationRegistry,
)


def _context(actor=None):
    return PresentationContext(actor=actor, protocol_version=1)


def _spec(name="status", presenter=None, schema_version=1):
    return PresenterSpec(
        name=name,
        schema_version=schema_version,
        unavailable_reason=("missing_data", "無法讀取角色資料"),
        presenter=presenter or (lambda context: {"available": True, "value": 1}),
    )


class RegistryTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only"
    )
    def test_duplicate_registration_fails(self):
        registry = PresentationRegistry("test")
        registry.register(_spec())
        with self.assertRaises(ProtocolValidationError):
            registry.register(_spec())

    def test_unknown_panel_names_are_not_exposed(self):
        registry = PresentationRegistry("test")
        registry.register(_spec())
        self.assertEqual(registry.panel_names, frozenset({"status"}))
        with self.assertRaises(KeyError):
            registry.spec("nonexistent")
        with self.assertRaises(KeyError):
            registry.build_unavailable("nonexistent")

    def test_isolated_test_registries_do_not_leak(self):
        one = PresentationRegistry("one")
        two = PresentationRegistry("two")
        one.register(_spec("alpha"))
        two.register(_spec("beta"))
        self.assertEqual(one.panel_names, frozenset({"alpha"}))
        self.assertEqual(two.panel_names, frozenset({"beta"}))

    def test_invalid_panel_names_rejected_at_registration(self):
        registry = PresentationRegistry("test")
        with self.assertRaises(ProtocolValidationError):
            registry.register(_spec("BAD NAME"))
        with self.assertRaises(ProtocolValidationError):
            registry.register(_spec(""))

    def test_unavailable_builder_uses_registry_owned_reason(self):
        registry = PresentationRegistry("test")
        registry.register(_spec())
        payload = registry.build_unavailable("status")
        self.assertEqual(
            payload,
            {
                "schema_version": 1,
                "available": False,
                "reason": {"code": "missing_data", "message": "無法讀取角色資料"},
            },
        )

    @covers_requirement(
        "webclient-oob-protocol::every-panel-payload-has-an-exact-availability-discriminator"
    )
    def test_internal_failure_uses_correlated_unavailable(self):
        registry = PresentationRegistry("test")
        registry.register(_spec())
        payload = registry.build_unavailable("status", internal=True, correlation_id="d" * 32)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "internal_presenter_error")
        self.assertEqual(payload["reason"]["correlation_id"], "d" * 32)
        self.assertNotIn("traceback", json_repr(payload))
        self.assertNotIn("exception", json_repr(payload))

    def test_registration_rejects_invalid_schema_version(self):
        registry = PresentationRegistry("test")
        with self.assertRaises(ProtocolValidationError):
            registry.register(_spec(schema_version=0))

    def test_presenter_non_available_payload_is_rejected(self):
        registry = PresentationRegistry("test")
        registry.register(_spec(presenter=lambda context: {"available": False}))
        with self.assertRaises(ProtocolValidationError):
            registry.render("status", _context())
        registry = PresentationRegistry("test")
        registry.register(_spec(presenter=lambda context: [1, 2]))
        with self.assertRaises(ProtocolValidationError):
            registry.render("status", _context())

    def test_logger_failure_still_isolates_presenter_errors(self):
        registry = PresentationRegistry("test")
        registry.register(_spec(presenter=lambda context: 1 / 0))
        with patch(
            "evennia.utils.logger.log_trace",
            side_effect=RuntimeError("log down"),
        ):
            payload = registry.render("status", _context())
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "internal_presenter_error")


def json_repr(payload):
    import json

    return json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
