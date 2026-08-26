"""Pure version-1 envelope and bound validation tests (foundation section 1.1)."""

import json
import unittest

from tools.spec_traceability import covers_requirement

from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_FIELDS,
    MAX_LIST_ITEMS,
    MAX_SAFE_INTEGER,
    MAX_STRING_CODE_POINTS,
    OUTCOMES,
    PROTOCOL_ERROR_CODES,
    PROTOCOL_VERSION,
    UI_ACTION,
    UI_ACTION_RESULT,
    UI_PROTOCOL_ERROR,
    UI_SNAPSHOT,
    UI_SYNC,
    UI_UPDATE,
    ProtocolValidationError,
    JSONSafetyError,
    check_envelope,
    check_json_safety,
    json_byte_size,
    new_presentation_epoch,
    unavailable_payload,
    validate_server_time,
    validate_ui_action,
    validate_ui_action_result,
    validate_ui_protocol_error,
    validate_ui_snapshot,
    validate_ui_sync,
    validate_ui_update,
)

VALID_EPOCH = new_presentation_epoch()


def _server_time(**overrides):
    value = {
        "year": 1204,
        "season_index": 2,
        "season_label": "仲夏",
        "day_in_season": 17,
        "hour": 14,
        "minute": 30,
        "second": 5,
    }
    value.update(overrides)
    return value


def _snapshot(**overrides):
    value = {
        "protocol_version": 1,
        "presentation_epoch": VALID_EPOCH,
        "revision": 3,
        "mode": "exploration",
        "panels": {"status": {"schema_version": 1, "available": True}},
        "layout_version": 1,
        "server_time": _server_time(),
    }
    value.update(overrides)
    return value


def _update(**overrides):
    value = _snapshot(revision=4, mode="combat")
    value.update(overrides)
    return value


def _result(**overrides):
    value = {
        "protocol_version": 1,
        "presentation_epoch": VALID_EPOCH,
        "request_id": "client:42",
        "outcome": "success",
        "code": "ok",
        "message": "已送出",
        "presentation_revision": 12,
    }
    value.update(overrides)
    return value


def _protocol_error(**overrides):
    value = {
        "protocol_version": 1,
        "code": "unsupported_version",
        "message": "不支援的協定版本",
        "reload_required": True,
    }
    value.update(overrides)
    return value


class JSONSafetyTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    def test_global_bounds_reject_oversized_input(self):
        check_json_safety({"nested": [1, 2, 3]})
        value = {}
        node = value
        # Depth 12 is the raised bound (nested context_actions v3 shape); the
        # deepest legitimate leaf sits at depth 11, so 13 levels must fail.
        for _ in range(13):
            node["child"] = {}
            node = node["child"]
        with self.assertRaises(JSONSafetyError):
            check_json_safety(value)
        with self.assertRaises(JSONSafetyError):
            check_json_safety({"fields": {str(i): i for i in range(65)}})
        with self.assertRaises(JSONSafetyError):
            check_json_safety({"items": list(range(MAX_LIST_ITEMS + 1))})
        # The raised ceiling clears the largest legitimate flat panel list
        # (the context_actions exploration form's 320-entry affordance array).
        self.assertIsNone(
            check_json_safety({"items": list(range(MAX_LIST_ITEMS))})
        )
        with self.assertRaises(JSONSafetyError):
            check_json_safety({"s": "x" * (MAX_STRING_CODE_POINTS + 1)})
        with self.assertRaises(JSONSafetyError):
            check_json_safety({"n": MAX_SAFE_INTEGER + 1})
        # The global integer range is the full JavaScript-safe range
        # (-2^53+1 .. 2^53-1): negative safe integers (the signed values in
        # the deterministic combat_modifiers.yaml, e.g. defense -15) pass,
        # while values below -2^53 still fail.
        self.assertIsNone(check_json_safety({"defense": -15}))
        self.assertIsNone(check_json_safety({"n": -MAX_SAFE_INTEGER}))
        with self.assertRaises(JSONSafetyError):
            check_json_safety({"n": -MAX_SAFE_INTEGER - 1})
        with self.assertRaises(JSONSafetyError):
            check_json_safety({"n": float("inf")})
        with self.assertRaises(JSONSafetyError):
            check_json_safety({"n": float("nan")})

    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    def test_canonical_byte_size_is_enforced(self):
        large = {"status": "x" * (MAX_CANONICAL_JSON_BYTES)}
        self.assertGreater(json_byte_size(large), MAX_CANONICAL_JSON_BYTES)
        with self.assertRaises(JSONSafetyError):
            check_envelope(large)
        small = {"protocol_version": 1}
        check_envelope(small)

    def test_booleans_are_not_integers(self):
        # The JSON-safety walker allows booleans as JSON scalars; the
        # integer/bool separation is enforced by every integer field validator.
        check_json_safety({"b": True})


class ServerTimeTests(unittest.TestCase):
    def test_valid_server_time_normalizes(self):
        result = validate_server_time(_server_time())
        self.assertEqual(result["season_label"], "仲夏")
        self.assertEqual(result["day_in_season"], 17)

    def test_rejects_bad_fields(self):
        for override, in (
            ({"year": -1},),
            ({"season_index": 4},),
            ({"season_label": ""},),
            ({"season_label": "x" * 33},),
            ({"day_in_season": 0},),
            ({"day_in_season": 91},),
            ({"hour": 24},),
            ({"minute": 60},),
            ({"second": 60},),
            ({"extra": 1},),
        ):
            with self.subTest(override=override):
                with self.assertRaises(ProtocolValidationError):
                    validate_server_time(_server_time(**override))

    def test_booleans_rejected_for_integers(self):
        with self.assertRaises(ProtocolValidationError):
            validate_server_time(_server_time(year=True))
        with self.assertRaises(ProtocolValidationError):
            validate_server_time(_server_time(day_in_season=True))


class SnapshotUpdateTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    def test_valid_snapshot_and_update_pass(self):
        snapshot = validate_ui_snapshot(_snapshot())
        self.assertEqual(snapshot["protocol_version"], 1)
        update = validate_ui_update(_update())
        self.assertEqual(update["mode"], "combat")

    def test_unknown_fields_rejected(self):
        for builder in (validate_ui_snapshot, validate_ui_update):
            with self.assertRaises(ProtocolValidationError):
                builder(_snapshot(extra=1))
            with self.assertRaises(ProtocolValidationError):
                builder(_snapshot(missing="drop", **{"unrelated": 1}))

    def test_missing_required_fields_rejected(self):
        for builder in (validate_ui_snapshot, validate_ui_update):
            for field in ("revision", "mode", "panels", "server_time"):
                payload = _snapshot()
                del payload[field]
                with self.subTest(field=field):
                    with self.assertRaises(ProtocolValidationError):
                        builder(payload)

    def test_bad_metadata_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(protocol_version=2))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(presentation_epoch="short"))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(presentation_epoch="x/y*" * 6))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(revision=0))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(revision=True))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(mode="travel"))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(layout_version=0))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(layout_version=MAX_SAFE_INTEGER))

    def test_empty_and_unknown_panels_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(panels={}))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_update(_update(panels={}))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(
                _snapshot(panels={"unknown_panel": {}}), known_panels={"status"}
            )
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(
                _snapshot(panels={f"p{i}": {} for i in range(33)})
            )
        with self.assertRaises(ProtocolValidationError):
            validate_ui_snapshot(_snapshot(panels={"BAD!": {}}))

    def test_known_panel_allowlist_enforced_when_provided(self):
        # Unknown panels are rejected only when the coordinator supplies the
        # registered allowlist; without one, panel names are still shape-checked.
        validate_ui_snapshot(_snapshot(panels={"anything": {}}))
        result = validate_ui_snapshot(_snapshot(), known_panels={"status"})
        self.assertEqual(list(result["panels"]), ["status"])


class ResultEnvelopeTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping"
    )
    def test_valid_outcomes_pass(self):
        for outcome in OUTCOMES:
            payload = _result(outcome=outcome)
            if outcome == "error":
                payload["correlation_id"] = "a" * 32
            result = validate_ui_action_result(payload)
            self.assertEqual(result["outcome"], outcome)

    def test_error_requires_correlation_and_others_forbid_it(self):
        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(_result(outcome="error"))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(
                _result(outcome="success", correlation_id="a" * 32)
            )
        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(
                _result(outcome="error", correlation_id="not-hex")
            )

    def test_request_id_and_message_bounds(self):
        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(_result(request_id="x" * 65))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(_result(request_id="has space"))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(_result(message=""))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(_result(message="x" * 513))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(_result(code="UPPER"))


class ProtocolErrorTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping"
    )
    def test_valid_codes_pass(self):
        for code in PROTOCOL_ERROR_CODES:
            payload = _protocol_error(code=code)
            if code == "internal_error":
                payload["correlation_id"] = "b" * 32
            result = validate_ui_protocol_error(payload)
            self.assertEqual(result["code"], code)

    def test_conditional_correlation_exact(self):
        with self.assertRaises(ProtocolValidationError):
            validate_ui_protocol_error(_protocol_error(code="internal_error"))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_protocol_error(
                _protocol_error(code="unsupported_version", correlation_id="b" * 32)
            )
        with self.assertRaises(ProtocolValidationError):
            validate_ui_protocol_error(_protocol_error(code="mystery"))

    def test_forbidden_payload_fields(self):
        with self.assertRaises(ProtocolValidationError):
            validate_ui_protocol_error(_protocol_error(panels={}))
        with self.assertRaises(ProtocolValidationError):
            validate_ui_protocol_error(_protocol_error(actor="id"))


class SyncEnvelopeTests(unittest.TestCase):
    def test_sync_exact(self):
        self.assertEqual(
            validate_ui_sync({"protocol_version": 1}),
            {"protocol_version": 1},
        )
        with self.assertRaises(ProtocolValidationError):
            validate_ui_sync({"protocol_version": 2})
        with self.assertRaises(ProtocolValidationError):
            validate_ui_sync({"protocol_version": 1, "actor": "id"})
        with self.assertRaises(ProtocolValidationError):
            validate_ui_sync({"protocol_version": 1, "presentation_epoch": VALID_EPOCH})


class ActionEnvelopeTests(unittest.TestCase):
    @covers_requirement(
        "webclient-action-dispatch::ui-actions-use-an-exact-bounded-request-envelope"
    )
    def test_valid_action_envelope_passes(self):
        payload = {
            "protocol_version": 1,
            "presentation_epoch": VALID_EPOCH,
            "request_id": "session:7",
            "base_revision": 42,
            "action_id": "proof.noop",
            "payload": {"op": 1},
        }
        result = validate_ui_action(payload)
        self.assertEqual(result["action_id"], "proof.noop")
        self.assertEqual(result["base_revision"], 42)

    def test_global_bounds_reject_before_lookup(self):
        for override in (
            {"protocol_version": 2},
            {"presentation_epoch": "bad"},
            {"request_id": "x" * 65},
            {"base_revision": -1},
            {"base_revision": True},
            {"action_id": "BAD"},
            {"action_id": ""},
            {"payload": []},
            {"actor": "id"},
            {"extra": 1},
        ):
            with self.subTest(override=override):
                payload = {
                    "protocol_version": 1,
                    "presentation_epoch": VALID_EPOCH,
                    "request_id": "session:7",
                    "base_revision": 42,
                    "action_id": "proof.noop",
                    "payload": {"op": 1},
                }
                payload.update(override)
                with self.assertRaises(ProtocolValidationError):
                    validate_ui_action(payload)


class EpochTests(unittest.TestCase):
    def test_epoch_shape(self):
        epoch = new_presentation_epoch()
        self.assertEqual(len(epoch), 22)
        self.assertTrue(
            all(char.isascii() and (char.isalnum() or char in "-_") for char in epoch)
        )

    def test_epochs_differ(self):
        self.assertNotEqual(new_presentation_epoch(), new_presentation_epoch())


class UnavailablePayloadTests(unittest.TestCase):
    def test_exact_common_unavailable_shape(self):
        payload = unavailable_payload(1, "missing_data", "無法讀取角色資料")
        self.assertEqual(
            payload,
            {"schema_version": 1, "available": False, "reason": {"code": "missing_data", "message": "無法讀取角色資料"}},
        )
        correlated = unavailable_payload(1, "internal_presenter_error", "暫時無法使用", correlation_id="c" * 32)
        self.assertEqual(correlated["reason"]["correlation_id"], "c" * 32)
        with self.assertRaises(ProtocolValidationError):
            unavailable_payload(1, "missing_data", "x", correlation_id="short")


if __name__ == "__main__":
    unittest.main()
