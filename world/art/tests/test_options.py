"""Tests for the bounded sd-webui option enumeration (``@art options`` seam).

Every case stubs ``http.client`` connections (no socket) and asserts the
enforced bounds: the fixed 10-s per-call timeout, the 100-item list cap, the
existing response-size cap, verbatim names, and the named failure codes.
"""

from __future__ import annotations

import base64
import json
import unittest
from unittest.mock import patch

from django.test import override_settings

from world.art.sd_worker import (
    SDError,
    list_models,
    list_modules,
    list_samplers,
    list_schedulers,
    list_styles,
)

from tools.spec_traceability import covers_requirement

# A payload item valid for every wrapper's fallback keys.
_UNIVERSAL_ITEM = {"name": "a", "title": "a", "label": "a", "model_name": "a"}


class FakeResponse:
    def __init__(self, status=200, body=b"[]", reason="OK"):
        self.status = status
        self.reason = reason
        self._body = body

    def close(self):
        pass

    def read(self, size=-1):
        if not self._body:
            return b""
        if size < 0:
            chunk, self._body = self._body, b""
            return chunk
        chunk, self._body = self._body[:size], self._body[size:]
        return chunk


class FakeConnection:
    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.calls = []
        self._outcome = None
        self.sock = None

    def script(self, outcome):
        self._outcome = outcome

    def request(self, method, path, body=None, headers=None):
        self.calls.append(
            {"method": method, "path": path, "body": body, "headers": headers}
        )

    def getresponse(self):
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome

    def close(self):
        pass


class _EnumerationTests(unittest.TestCase):
    """Shared harness: one scripted GET response per call.

    ``HTTPConnection`` is patched with a factory so each call's connect timeout
    is recorded on a fresh connection object (``self.connection`` is the last
    connection created).
    """

    def setUp(self):
        self.created = []
        self._scripted = None
        patcher = patch(
            "world.art.sd_worker.http.client.HTTPConnection",
            side_effect=self._make_connection,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        settings_patcher = override_settings(
            ART_SD_BASE_URL="http://sd.example:7860",
            ART_SD_MAX_RESPONSE_BYTES=1_000_000,
        )
        settings_patcher.enable()
        self.addCleanup(settings_patcher.disable)

    def _make_connection(self, host, port, timeout=None):
        connection = FakeConnection(host, port, timeout=timeout)
        if self._scripted is not None:
            connection.script(self._scripted)
        self.created.append(connection)
        return connection

    @property
    def connection(self):
        return self.created[-1]

    def _serve(self, payload, status=200):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self._scripted = FakeResponse(status, body)

    def _assert_bad(self, code, call):
        with self.assertRaises(SDError) as ctx:
            call()
        self.assertEqual(ctx.exception.code, code)

    def _assert_ten_second_connect_budget(self):
        # The connect timeout derives from the fixed 10-s cap (minus the
        # real-clock elapsed since the deadline was computed), never from
        # ART_SD_TIMEOUT_SECONDS (600 in these tests' environment).
        timeout = self.connection.timeout
        self.assertIsNotNone(timeout)
        self.assertLessEqual(timeout, 10.0)
        self.assertGreater(timeout, 9.0)


class MappingTests(_EnumerationTests):
    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_each_wrapper_maps_its_endpoint_and_fallback_keys(self):
        cases = [
            (
                list_models,
                "/sdapi/v1/sd-models",
                [{"title": "Anima A [hash]", "model_name": "unused"}],
                ["Anima A [hash]"],
            ),
            (list_samplers, "/sdapi/v1/samplers", [{"name": "Euler a"}], ["Euler a"]),
            (
                list_schedulers,
                "/sdapi/v1/schedulers",
                [{"label": "Karras", "name": "karras"}],
                ["Karras"],
            ),
            (
                list_styles,
                "/sdapi/v1/prompt-styles",
                [{"name": "cinematic"}],
                ["cinematic"],
            ),
            (
                list_modules,
                "/sdapi/v1/sd-modules",
                [{"model_name": "te.safetensors"}],
                ["te.safetensors"],
            ),
        ]
        for wrapper, path, payload, expected in cases:
            with self.subTest(path=path):
                self._serve(payload)
                self.assertEqual(wrapper(), expected)
                call = self.connection.calls[-1]
                self.assertEqual(call["method"], "GET")
                self.assertEqual(call["path"], path)
                self.assertIsNone(call["body"])

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_names_are_verbatim_with_only_whitespace_empty_dropped(self):
        self._serve(
            [
                {"name": "  padded  "},
                {"name": "   "},
                {"name": "Euler a"},
            ]
        )
        names = list_samplers()
        # Verbatim: padding preserved so staff can copy exactly; whitespace-only dropped.
        self.assertEqual(names, ["  padded  ", "Euler a"])

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_model_title_falls_back_to_model_name(self):
        self._serve([{"model_name": "fallback.safetensors"}])
        self.assertEqual(list_models(), ["fallback.safetensors"])

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_scheduler_label_falls_back_to_name(self):
        self._serve([{"name": "karras"}])
        self.assertEqual(list_schedulers(), ["karras"])


class BoundTests(_EnumerationTests):
    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_every_call_uses_the_fixed_ten_second_budget(self):
        for wrapper in (list_models, list_samplers, list_schedulers, list_styles, list_modules):
            with self.subTest(wrapper=wrapper.__name__):
                self._serve([_UNIVERSAL_ITEM])
                wrapper()
                self._assert_ten_second_connect_budget()

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_the_budget_override_survives_a_different_generation_timeout(self):
        with override_settings(ART_SD_TIMEOUT_SECONDS=600):
            self._serve([{"name": "a"}])
            list_samplers()
        self._assert_ten_second_connect_budget()

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_lists_over_one_hundred_items_are_rejected(self):
        self._serve([{"name": f"s{i}"} for i in range(101)])
        self._assert_bad("sd_malformed_response", list_samplers)

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_a_hundred_items_are_accepted(self):
        self._serve([{"name": f"s{i}"} for i in range(100)])
        self.assertEqual(len(list_samplers()), 100)

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_an_oversized_body_hits_the_existing_size_cap(self):
        with override_settings(ART_SD_MAX_RESPONSE_BYTES=20):
            self._serve([{"name": "x" * 64}])
            self._assert_bad("sd_response_too_large", list_samplers)


class MalformedTests(_EnumerationTests):
    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_non_list_body_is_malformed(self):
        self._serve({"models": []})
        self._assert_bad("sd_malformed_response", list_models)

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_non_object_item_is_malformed(self):
        self._serve(["Euler a"])
        self._assert_bad("sd_malformed_response", list_samplers)

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_item_without_a_string_name_field_is_malformed(self):
        self._serve([{"name": 42}])
        self._assert_bad("sd_malformed_response", list_samplers)

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_non_200_is_http_error(self):
        self._serve(b"nope", status=401)
        self._assert_bad("sd_http_error", list_styles)

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_unreachable_server_is_connection_error(self):
        # A transport-level failure surfaces as the named connection error.
        self._serve([])
        self._scripted = ConnectionRefusedError("refused")
        self._assert_bad("sd_connection_error", list_models)


class AuthEnumerationTests(_EnumerationTests):
    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-sends-basic-auth-only-from-secret-file-credentials"
    )
    def test_enumeration_carries_basic_auth_when_configured(self):
        self._serve([{"name": "a"}])
        with override_settings(ART_SD_USERNAME="admin", ART_SD_PASSWORD="hunter2"):
            list_samplers()
        expected = "Basic " + base64.b64encode(b"admin:hunter2").decode("ascii")
        self.assertEqual(self.connection.calls[-1]["headers"]["Authorization"], expected)


if __name__ == "__main__":
    unittest.main()
