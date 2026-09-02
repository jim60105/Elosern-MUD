"""Tests for the internal sd-webui client (request building, transport, caps).

Pure-logic tests use fixed inputs and never open a network connection: the
transport is exercised through a stubbed ``http.client`` connection, and
envelope validation through injected transports.
"""

from __future__ import annotations

import base64
import json
import socket
import struct
import unittest
from unittest.mock import patch

from django.test import override_settings

from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.sd_worker import (
    GeneratedImage,
    SDError,
    SDWebUIClient,
    _http_json,
    _http_request,
    build_txt2img_request,
    default_transport,
    maybe_prepin_samples_format,
    prompt_digest,
    render_prompt_pair,
    resolve_sd_client,
)
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement

VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

# Sentinel meaning "this key is absent" for matrix tests.
_MISSING = object()


def _scene(key="forest_path"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _monster(key="low"):
    return ArtSubject(ArtSubjectKind.MONSTER, key)


class FakeResponse:
    """A stub ``HTTPResponse`` that serves a fixed body in chunks."""

    def __init__(self, status=200, body=b"{}", reason="OK"):
        self.status = status
        self.reason = reason
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

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


class RequestBuildingTests(unittest.TestCase):
    @covers_requirement("internal-art-worker::art-generation-prompts-are-stored-in-the-prompt-library")
    def test_scene_request_renders_the_scene_prompt_with_16_9_dimensions(self):
        request = build_txt2img_request(_scene("tavern_interior"), "a description")
        self.assertIn("a description", request["prompt"])
        self.assertNotIn("{description}", request["prompt"])
        self.assertEqual(request["width"], 1344)
        self.assertEqual(request["height"], 768)
        self.assertNotEqual(request["prompt"], request["negative_prompt"])
        self.assertEqual(request["steps"], 30)
        self.assertEqual(request["cfg_scale"], 7.0)
        self.assertEqual(
            request["override_settings"], {"samples_format": "png"}
        )
        self.assertIs(request["override_settings_restore_afterwards"], True)

    @covers_requirement("internal-art-worker::art-generation-prompts-are-stored-in-the-prompt-library")
    def test_portrait_request_renders_the_portrait_prompt_with_3_4_dimensions(self):
        request = build_txt2img_request(_monster("low"), "a monster description")
        self.assertIn("a monster description", request["prompt"])
        self.assertEqual(request["width"], 768)
        self.assertEqual(request["height"], 1024)

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_request_passes_through_configured_sampler_scheduler_checkpoint(self):
        with override_settings(
            ART_SD_SAMPLER="Euler a",
            ART_SD_SCHEDULER="Beta",
            ART_SD_CHECKPOINT="anima/animaika_v36.safetensors [d50fb5b9a0]",
        ):
            request = build_txt2img_request(_scene(), "desc")
        self.assertEqual(request["sampler_name"], "Euler a")
        self.assertEqual(request["scheduler"], "Beta")
        self.assertEqual(
            request["override_settings"]["sd_model_checkpoint"],
            "anima/animaika_v36.safetensors [d50fb5b9a0]",
        )

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_request_omits_empty_sampler_scheduler_checkpoint(self):
        request = build_txt2img_request(_scene(), "desc")
        self.assertNotIn("sampler_name", request)
        self.assertNotIn("scheduler", request)
        self.assertEqual(request["override_settings"], {"samples_format": "png"})

    @covers_requirement("internal-art-worker::art-generation-prompts-are-stored-in-the-prompt-library")
    def test_prompt_pair_and_digest_are_deterministic(self):
        first = render_prompt_pair(_scene("city_street"), "desc")
        second = render_prompt_pair(_scene("city_street"), "desc")
        self.assertEqual(first, second)
        self.assertEqual(
            prompt_digest(_scene("city_street"), "desc"),
            prompt_digest(_scene("city_street"), "desc"),
        )
        self.assertNotEqual(
            prompt_digest(_scene("city_street"), "desc"),
            prompt_digest(_scene("city_street"), "other"),
        )
        self.assertNotEqual(
            prompt_digest(_scene("city_street"), "desc"),
            prompt_digest(_monster("low"), "desc"),
        )
        positive, negative = first
        self.assertNotIn("{description}", positive)
        self.assertNotIn("{", negative)


class GenerateValidationTests(unittest.TestCase):
    def _client(self, transport):
        return SDWebUIClient(transport=transport)

    def _ok_response(self, png=VALID_PNG, info=None):
        response = {"images": [base64.b64encode(png).decode("ascii")]}
        if info is not None:
            response["info"] = info
        return response

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_valid_response_returns_exactly_the_decoded_png_bytes(self):
        client = self._client(lambda request: self._ok_response())
        image = client.generate(_scene(), "desc")
        self.assertEqual(image.data, VALID_PNG)
        self.assertIsNone(image.seed)

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_empty_images_settles_sd_no_image(self):
        client = self._client(lambda request: {"images": []})
        with self.assertRaises(SDError) as ctx:
            client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_no_image")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_non_object_envelope_settles_sd_malformed_response(self):
        client = self._client(lambda request: ["not", "an", "object"])
        with self.assertRaises(SDError) as ctx:
            client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_malformed_response")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_undecodable_base64_settles_sd_decode_error(self):
        client = self._client(lambda request: {"images": ["not-base64!"]})
        with self.assertRaises(SDError) as ctx:
            client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_decode_error")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_non_png_bytes_settle_sd_not_png(self):
        client = self._client(
            lambda request: {"images": [base64.b64encode(b"jpeg-ish").decode()]}
        )
        with self.assertRaises(SDError) as ctx:
            client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_not_png")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_forged_png_without_an_ihdr_chunk_settles_sd_not_png(self):
        # PNG magic bytes followed by arbitrary data: no IHDR chunk type.
        forged = b"\x89PNG\r\n\x1a\n" + b"junk" * 8
        client = self._client(
            lambda request: {"images": [base64.b64encode(forged).decode()]}
        )
        with self.assertRaises(SDError) as ctx:
            client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_not_png")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_forged_png_with_a_bad_ihdr_length_settles_sd_not_png(self):
        png = bytearray(VALID_PNG)
        png[8:12] = struct.pack(">I", 999)
        client = self._client(
            lambda request: {"images": [base64.b64encode(bytes(png)).decode()]}
        )
        with self.assertRaises(SDError) as ctx:
            client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_not_png")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_unexpected_transport_exception_maps_to_sd_internal_error(self):
        def transport(request):
            raise RuntimeError("unexpected transport bug")

        client = self._client(transport)
        with self.assertRaises(SDError) as ctx:
            client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_internal_error")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_oversized_base64_payload_settles_sd_response_too_large(self):
        with override_settings(ART_SD_MAX_RESPONSE_BYTES=10):
            client = self._client(lambda request: self._ok_response())
            with self.assertRaises(SDError) as ctx:
                client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_response_too_large")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_oversized_png_dimensions_settle_sd_image_dimensions_too_large(self):
        # A valid PNG whose IHDR claims 4097x4097 pixels (over the caps).
        png = bytearray(VALID_PNG)
        png[16:24] = struct.pack(">II", 4097, 4097)
        with override_settings(ART_SD_MAX_IMAGE_DIMENSIONS=4096):
            client = self._client(lambda request: self._ok_response(bytes(png)))
            with self.assertRaises(SDError) as ctx:
                client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_image_dimensions_too_large")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_too_many_pixels_settle_sd_image_dimensions_too_large(self):
        png = bytearray(VALID_PNG)
        png[16:24] = struct.pack(">II", 3000, 6000)
        with override_settings(ART_SD_MAX_IMAGE_PIXELS=16_000_000):
            client = self._client(lambda request: self._ok_response(bytes(png)))
            with self.assertRaises(SDError) as ctx:
                client.generate(_scene(), "desc")
        self.assertEqual(ctx.exception.code, "sd_image_dimensions_too_large")

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_transport_receives_the_built_request(self):
        captured = {}

        def transport(request):
            captured["request"] = request
            return self._ok_response()

        client = self._client(transport)
        client.generate(_scene("tavern_interior"), "scene text")
        self.assertEqual(captured["request"]["width"], 1344)
        self.assertIn("scene text", captured["request"]["prompt"])
        self.assertIn("override_settings_restore_afterwards", captured["request"])


class FakeConnection:
    """A stub ``http.client`` connection serving a fake response or raising."""

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.calls = []
        self._outcome = None
        self.sock = FakeSocket()

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


class FakeSocket:
    """A stub socket whose timeout can be observed."""

    def __init__(self):
        self.timeouts = []

    def settimeout(self, timeout):
        self.timeouts.append(timeout)


class TransportTests(unittest.TestCase):
    def _http(self, outcome, url="http://sd.example:7860/sdapi/v1/txt2img", **settings_overrides):
        settings_overrides.setdefault("ART_SD_TIMEOUT_SECONDS", 10)
        settings_overrides.setdefault("ART_SD_MAX_RESPONSE_BYTES", 1_000_000)
        connection = FakeConnection("sd.example", 7860)
        connection.script(outcome)
        with override_settings(**settings_overrides):
            with patch(
                "world.art.sd_worker.http.client.HTTPConnection",
                return_value=connection,
            ):
                with patch(
                    "world.art.sd_worker.http.client.HTTPSConnection",
                    return_value=connection,
                ):
                    return _http_json(url, b"{}"), connection

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_ok_response_returns_the_parsed_json_object(self):
        body = json.dumps({"images": ["x"]}).encode()
        result, connection = self._http(FakeResponse(200, body))
        self.assertEqual(result, {"images": ["x"]})
        self.assertEqual(connection.calls[0]["method"], "POST")
        self.assertEqual(connection.calls[0]["path"], "/sdapi/v1/txt2img")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_http_error_maps_to_sd_http_error(self):
        with self.assertRaises(SDError) as ctx:
            self._http(FakeResponse(500, b"oops"))
        self.assertEqual(ctx.exception.code, "sd_http_error")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_redirect_status_is_a_bounded_failure_never_followed(self):
        with self.assertRaises(SDError) as ctx:
            self._http(FakeResponse(302, b"redirect"))
        self.assertEqual(ctx.exception.code, "sd_http_error")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_connection_error_maps_to_sd_connection_error(self):
        with self.assertRaises(SDError) as ctx:
            self._http(ConnectionRefusedError("refused"))
        self.assertEqual(ctx.exception.code, "sd_connection_error")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_socket_timeout_maps_to_sd_timeout(self):
        with self.assertRaises(SDError) as ctx:
            self._http(socket.timeout("stalled"))
        self.assertEqual(ctx.exception.code, "sd_timeout")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_non_json_body_maps_to_sd_malformed_response(self):
        with self.assertRaises(SDError) as ctx:
            self._http(FakeResponse(200, b"not-json"))
        self.assertEqual(ctx.exception.code, "sd_malformed_response")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_non_object_json_maps_to_sd_malformed_response(self):
        with self.assertRaises(SDError) as ctx:
            self._http(FakeResponse(200, b'["a"]'))
        self.assertEqual(ctx.exception.code, "sd_malformed_response")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_dribbling_body_is_abandoned_at_the_total_deadline(self):
        with patch(
            "world.art.sd_worker.time.monotonic",
            side_effect=[0.0, 0.0, 5.0, 601.0],
        ):
            with self.assertRaises(SDError) as ctx:
                self._http(FakeResponse(200, b"0123456789" * 10))
        self.assertEqual(ctx.exception.code, "sd_timeout")

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_each_read_is_bounded_by_the_remaining_budget(self):
        connection = FakeConnection("sd.example", 7860)
        connection.script(FakeResponse(200, b"data"))
        with override_settings(
            ART_SD_TIMEOUT_SECONDS=10, ART_SD_MAX_RESPONSE_BYTES=1_000_000
        ):
            with patch(
                "world.art.sd_worker.http.client.HTTPConnection",
                return_value=connection,
            ):
                with patch(
                    "world.art.sd_worker.http.client.HTTPSConnection",
                    return_value=connection,
                ):
                    with patch(
                        "world.art.sd_worker.time.monotonic",
                        side_effect=[0.0, 0.0, 5.0, 601.0],
                    ):
                        with self.assertRaises(SDError) as ctx:
                            _http_json("http://sd.example:7860/sdapi/v1/txt2img", b"{}")
        self.assertEqual(ctx.exception.code, "sd_timeout")
        # Before the body read the socket timeout was refreshed to the budget
        # still remaining (10s budget minus 5s elapsed), never the flat 10s.
        self.assertEqual(connection.sock.timeouts, [5.0])

    @covers_requirement("internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes")
    def test_oversized_response_body_is_rejected_before_unbounded_allocation(self):
        with self.assertRaises(SDError) as ctx:
            self._http(
                FakeResponse(200, b"x" * 64),
                ART_SD_MAX_RESPONSE_BYTES=10,
            )
        self.assertEqual(ctx.exception.code, "sd_response_too_large")

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_non_http_scheme_is_rejected_before_any_connection(self):
        with override_settings(ART_SD_TIMEOUT_SECONDS=10):
            with patch(
                "world.art.sd_worker.http.client.HTTPConnection",
                side_effect=AssertionError("must not connect"),
            ):
                with self.assertRaises(SDError) as ctx:
                    _http_json("file:///etc/passwd", b"{}")
        self.assertEqual(ctx.exception.code, "sd_connection_error")

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_default_transport_targets_the_configured_txt2img_endpoint(self):
        connection = FakeConnection("sd.example", 7860)
        connection.script(FakeResponse(200, json.dumps({"images": ["x"]}).encode()))
        with override_settings(ART_SD_BASE_URL="http://sd.example:7860"):
            with patch(
                "world.art.sd_worker.http.client.HTTPConnection",
                return_value=connection,
            ):
                result = default_transport({"prompt": "p"})
        self.assertEqual(connection.host, "sd.example")
        self.assertEqual(connection.port, 7860)
        call = connection.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["path"], "/sdapi/v1/txt2img")
        self.assertEqual(json.loads(call["body"]), {"prompt": "p"})
        self.assertEqual(result, {"images": ["x"]})

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_get_requests_carry_no_content_type_header(self):
        # A GET has no body to type: Content-Type must never be sent.
        connection = FakeConnection("sd.example", 7860)
        connection.script(FakeResponse(200, b'["a"]'))
        with override_settings(ART_SD_TIMEOUT_SECONDS=10):
            with patch(
                "world.art.sd_worker.http.client.HTTPConnection",
                return_value=connection,
            ):
                result = _http_request("http://sd.example:7860/sdapi/v1/samplers", None)
        call = connection.calls[0]
        self.assertEqual(call["method"], "GET")
        self.assertIsNone(call["body"])
        self.assertNotIn("Content-Type", call["headers"])
        self.assertEqual(result, ["a"])

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-sends-basic-auth-only-from-secret-file-credentials"
    )
    def test_anonymous_credentials_send_no_authorization_header(self):
        connection = FakeConnection("sd.example", 7860)
        connection.script(FakeResponse(200, b"{}"))
        with override_settings(
            ART_SD_TIMEOUT_SECONDS=10, ART_SD_USERNAME="", ART_SD_PASSWORD=""
        ):
            with patch(
                "world.art.sd_worker.http.client.HTTPConnection",
                return_value=connection,
            ):
                _http_json("http://sd.example:7860/x", b"{}")
        self.assertNotIn("Authorization", connection.calls[0]["headers"])

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-sends-basic-auth-only-from-secret-file-credentials"
    )
    def test_half_configured_credentials_stay_anonymous(self):
        for username, password in (("admin", ""), ("", "hunter2")):
            with self.subTest(username=username, password=password):
                connection = FakeConnection("sd.example", 7860)
                connection.script(FakeResponse(200, b"{}"))
                with override_settings(
                    ART_SD_TIMEOUT_SECONDS=10,
                    ART_SD_USERNAME=username,
                    ART_SD_PASSWORD=password,
                ):
                    with patch(
                        "world.art.sd_worker.http.client.HTTPConnection",
                        return_value=connection,
                    ):
                        _http_json("http://sd.example:7860/x", b"{}")
                self.assertNotIn("Authorization", connection.calls[0]["headers"])

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-sends-basic-auth-only-from-secret-file-credentials"
    )
    def test_full_credentials_send_basic_auth_and_never_log_the_password(self):
        connection = FakeConnection("sd.example", 7860)
        connection.script(FakeResponse(500, b"boom hunter2 leak"))
        with override_settings(
            ART_SD_TIMEOUT_SECONDS=10,
            ART_SD_USERNAME="admin",
            ART_SD_PASSWORD="hunter2",
        ):
            with patch(
                "world.art.sd_worker.http.client.HTTPConnection",
                return_value=connection,
            ):
                with self.assertRaises(SDError) as ctx:
                    _http_json("http://sd.example:7860/x", b"{}")
        expected = "Basic " + base64.b64encode(b"admin:hunter2").decode("ascii")
        self.assertEqual(connection.calls[0]["headers"]["Authorization"], expected)
        # The bounded error never echoes the request headers or response body.
        self.assertNotIn("hunter2", str(ctx.exception))

    @covers_requirement(
        "art-sd-server-integration::the-sd-webui-client-enumerates-server-options-through-bounded-get-calls"
    )
    def test_per_call_timeout_override_bounds_connect_and_reads(self):
        # A 10-s diagnostic budget applies even while the generation setting is
        # 600: the connect timeout and every refreshed read timeout derive
        # from the override, never from ART_SD_TIMEOUT_SECONDS.
        connections = []

        def _factory(host, port, timeout=None):
            conn = FakeConnection(host, port, timeout=timeout)
            conn.script(FakeResponse(200, b"0123456789" * 10))
            connections.append(conn)
            return conn

        with override_settings(
            ART_SD_TIMEOUT_SECONDS=600, ART_SD_MAX_RESPONSE_BYTES=1_000_000
        ):
            with patch(
                "world.art.sd_worker.http.client.HTTPConnection",
                side_effect=_factory,
            ):
                with patch(
                    "world.art.sd_worker.time.monotonic",
                    side_effect=[0.0, 0.0, 5.0, 21.0],
                ):
                    with self.assertRaises(SDError) as ctx:
                        _http_json(
                            "http://sd.example:7860/sdapi/v1/samplers",
                            None,
                            timeout_seconds=10.0,
                        )
        self.assertEqual(ctx.exception.code, "sd_timeout")
        self.assertEqual(connections[0].timeout, 10.0)
        self.assertEqual(connections[0].sock.timeouts, [5.0])


class SeedParsingTests(unittest.TestCase):
    """The defensive info.seed extraction matrix (design D3)."""

    def _seed(self, info):
        response = {"images": [base64.b64encode(VALID_PNG).decode("ascii")]}
        if info is not _MISSING:
            response["info"] = info
        client = SDWebUIClient(transport=lambda request: response)
        return client.generate(_scene(), "desc").seed

    @covers_requirement(
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root"
    )
    def test_json_string_info_seed_is_reported(self):
        self.assertEqual(self._seed(json.dumps({"seed": 42})), 42)

    @covers_requirement(
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root"
    )
    def test_zero_seed_is_reported(self):
        self.assertEqual(self._seed(json.dumps({"seed": 0})), 0)

    @covers_requirement(
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root"
    )
    def test_already_decoded_dict_info_is_accepted(self):
        self.assertEqual(self._seed({"seed": 7}), 7)

    @covers_requirement(
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root"
    )
    def test_absent_or_unusable_info_yields_no_seed(self):
        for info in (
            _MISSING,
            None,
            "not json",
            json.dumps({"seed": "42"}),
            json.dumps({"seed": -1}),
            json.dumps({"seed": 4.2}),
            json.dumps({"seed": True}),
            json.dumps({"subseed": 42}),
            json.dumps([1, 2]),
            12345,
        ):
            with self.subTest(info=info):
                self.assertIsNone(self._seed(info))

    @covers_requirement(
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root"
    )
    def test_unparseable_info_never_fails_a_valid_image(self):
        # Garbage info alongside a valid image still returns the image bytes.
        image = SDWebUIClient(
            transport=lambda request: {
                "images": [base64.b64encode(VALID_PNG).decode("ascii")],
                "info": "{{{corrupt",
            }
        ).generate(_scene(), "desc")
        self.assertEqual(image.data, VALID_PNG)
        self.assertIsNone(image.seed)


class StylesModulesRequestTests(unittest.TestCase):
    @covers_requirement(
        "art-sd-server-integration::generation-requests-carry-configured-styles-and-forge-modules-verbatim"
    )
    def test_empty_knobs_omit_styles_and_module_fields(self):
        request = build_txt2img_request(_scene(), "desc")
        self.assertNotIn("styles", request)
        self.assertNotIn("forge_additional_modules", request["override_settings"])
        self.assertNotIn("forge_unet_storage_dtype", request["override_settings"])

    @covers_requirement(
        "art-sd-server-integration::generation-requests-carry-configured-styles-and-forge-modules-verbatim"
    )
    def test_blank_only_knobs_omit_the_fields_too(self):
        with override_settings(ART_SD_STYLES=" , ,, ", ART_SD_MODULES=",  ,"):
            request = build_txt2img_request(_scene(), "desc")
        self.assertNotIn("styles", request)
        self.assertNotIn("forge_additional_modules", request["override_settings"])

    @covers_requirement(
        "art-sd-server-integration::generation-requests-carry-configured-styles-and-forge-modules-verbatim"
    )
    def test_configured_knobs_pass_names_verbatim_with_the_dtype_companion(self):
        with override_settings(
            ART_SD_STYLES=" cinematic , portrait ",
            ART_SD_MODULES="te.safetensors,Detailer preprocessor v3.safetensors",
        ):
            request = build_txt2img_request(_scene(), "desc")
        self.assertEqual(request["styles"], ["cinematic", "portrait"])
        self.assertEqual(
            request["override_settings"]["forge_additional_modules"],
            ["te.safetensors", "Detailer preprocessor v3.safetensors"],
        )
        self.assertEqual(
            request["override_settings"]["forge_unet_storage_dtype"],
            "Automatic (fp16 LoRA)",
        )


class ClientResolutionTests(unittest.TestCase):
    def test_resolves_the_default_internal_client(self):
        client = resolve_sd_client()
        self.assertIsInstance(client, SDWebUIClient)
        self.assertIsInstance(client._transport, type(default_transport))

    def test_resolves_the_fake_client_through_the_setting(self):
        with override_settings(
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient"
        ):
            client = resolve_sd_client()
        self.assertIsInstance(client, FakeSDWebUIClient)

    def test_unresolvable_dotted_path_raises(self):
        with override_settings(ART_SD_CLIENT="world.art.no_such_module.NoSuchClient"):
            with self.assertRaises(Exception):
                resolve_sd_client()


class PrepinTests(unittest.TestCase):
    def setUp(self):
        from world.art import sd_worker

        self._prepinned = sd_worker._samples_format_prepinned
        sd_worker._samples_format_prepinned = False
        self.addCleanup(
            setattr, sd_worker, "_samples_format_prepinned", self._prepinned
        )

    def test_disabled_prepin_never_touches_the_server(self):
        with patch("world.art.sd_worker._http_json", side_effect=AssertionError("must not call")):
            maybe_prepin_samples_format()

    def test_enabled_prepin_skips_when_already_png(self):
        with override_settings(ART_SD_PREPIN_SAMPLES_FORMAT=True):
            with patch(
                "world.art.sd_worker._http_json",
                return_value={"samples_format": "png"},
            ) as http:
                with patch("world.art.sd_worker.log_info") as log:
                    maybe_prepin_samples_format()
        http.assert_called_once()
        log.assert_not_called()

    def test_enabled_prepin_mutates_and_logs_when_value_differs(self):
        calls = []
        responses = [{"samples_format": "webp"}, {"samples_format": "png"}]

        def _http(url, payload):
            calls.append((url, payload))
            return responses[len(calls) - 1]

        with override_settings(ART_SD_PREPIN_SAMPLES_FORMAT=True):
            with patch("world.art.sd_worker._http_json", side_effect=_http) as http:
                with patch("world.art.sd_worker.log_info") as log:
                    maybe_prepin_samples_format()
        self.assertEqual(len(calls), 2)
        self.assertIn("/sdapi/v1/options", calls[0][0])
        self.assertEqual(json.loads(calls[1][1]), {"samples_format": "png"})
        log.assert_called_once()

    def test_enabled_prepin_warns_when_the_server_does_not_confirm(self):
        def _http(url, payload):
            return {"samples_format": "webp"}

        with override_settings(ART_SD_PREPIN_SAMPLES_FORMAT=True):
            with patch("world.art.sd_worker._http_json", side_effect=_http):
                with patch("world.art.sd_worker.log_warn") as log:
                    maybe_prepin_samples_format()
        log.assert_called_once()

    def test_prepin_failure_is_logged_and_never_raises(self):
        with override_settings(ART_SD_PREPIN_SAMPLES_FORMAT=True):
            with patch(
                "world.art.sd_worker._http_json",
                side_effect=SDError("sd_connection_error", "offline"),
            ):
                with patch("world.art.sd_worker.log_warn") as log:
                    maybe_prepin_samples_format()
        log.assert_called_once()

    def test_prepin_runs_only_once_per_process(self):
        with override_settings(ART_SD_PREPIN_SAMPLES_FORMAT=True):
            with patch(
                "world.art.sd_worker._http_json",
                return_value={"samples_format": "webp"},
            ) as http:
                with patch("world.art.sd_worker.log_info"):
                    maybe_prepin_samples_format()
                    maybe_prepin_samples_format()
        self.assertEqual(http.call_count, 2)


if __name__ == "__main__":
    unittest.main()
