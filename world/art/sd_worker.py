"""The internal sd-webui client: request building, bounded transport, validation.

This module replaces the external subprocess worker (design D11 amendment): the
engine now owns an in-process client that POSTs ``/sdapi/v1/txt2img`` to the
configured ``ART_SD_BASE_URL``, validates the response envelope, and returns the
decoded PNG bytes. It is the only module that opens an sd-webui connection.

The client is the swappable seam: ``ART_SD_CLIENT`` names the dotted path of the
client class (default ``world.art.sd_worker.SDWebUIClient``), so tests and the
browser harness inject ``FakeSDWebUIClient`` and never open a socket.

Every failure mode maps to exactly one named ``SDError`` code so the worker can
settle the subject ``failed`` with a bounded error:
``sd_connection_error``, ``sd_timeout``, ``sd_http_error``,
``sd_malformed_response``, ``sd_no_image``, ``sd_decode_error``, ``sd_not_png``,
``sd_response_too_large``, ``sd_image_dimensions_too_large``. Prompt-template
render failures, client-resolution failures, and unexpected internal errors are
deliberately not ``SDError``s: ``world/art/worker.py`` wraps the per-subject
pipeline and maps them to ``sd_prompt_error``, ``sd_client_config_error``, and
``sd_internal_error`` so every claimed subject reaches a terminal settle.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Callable
from django.conf import settings
from evennia import logger
import hashlib
import http.client
import importlib
import json
import socket
import struct
import threading
import time
import urllib.parse
from typing import Any

from world.art.subjects import ArtSubject, ArtSubjectKind
from world.prompts.loader import render_prompt

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# The IHDR chunk occupies bytes 8..24 of a PNG: length(4) + "IHDR"(4) +
# width(4) + height(4). A shorter body cannot carry parseable dimensions.
_PNG_IHDR_END = 24
_PNG_IHDR_CHUNK = b"IHDR"
_PNG_IHDR_LENGTH = 13

_READ_CHUNK_BYTES = 65536


class SDError(Exception):
    """One bounded, named sd-webui failure; ``code`` is the settle error code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def render_prompt_pair(subject: ArtSubject, description: str) -> tuple[str, str]:
    """Render the positive and negative prompts for one subject.

    The positive template is ``art.scene_prompt`` for scenes and
    ``art.portrait_prompt`` for portraits, with the deterministic
    ``description`` substituted; the negative prompt is the shared
    ``art.negative_prompt`` text. Both come exclusively from the prompt
    library (``prompts/art.yaml``), never from Python constants.
    """
    if subject.kind is ArtSubjectKind.SCENE:
        positive = render_prompt("art.scene_prompt", description=description)
    else:
        positive = render_prompt("art.portrait_prompt", description=description)
    return positive, render_prompt("art.negative_prompt")


def prompt_digest(subject: ArtSubject, description: str) -> str:
    """Deterministic sha256 of the rendered positive+negative prompt pair.

    The pair is serialized as canonical JSON so two different prompt pairs can
    never produce the same digest. The queue record stores this digest
    alongside ``source_hash`` so an admin edit of an ``art.*`` template
    surfaces through the existing ``hash_changed`` review flag instead of
    silently drifting the image away from the prompt library.
    """
    positive, negative = render_prompt_pair(subject, description)
    pair = json.dumps([positive, negative], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(pair.encode("utf-8")).hexdigest()


def build_txt2img_request(subject: ArtSubject, description: str) -> dict[str, Any]:
    """Build the txt2img request body for one subject.

    Fills steps/cfg from settings, width/height from the subject's aspect ratio
    (scene 16:9, portrait 3:4), passes through a non-empty sampler/scheduler/
    checkpoint, and always requests ``samples_format: "png"`` request-scoped
    with ``override_settings_restore_afterwards: true``.
    """
    positive, negative = render_prompt_pair(subject, description)
    if subject.kind is ArtSubjectKind.SCENE:
        width = int(settings.ART_SD_SCENE_WIDTH)
        height = int(settings.ART_SD_SCENE_HEIGHT)
    else:
        width = int(settings.ART_SD_PORTRAIT_WIDTH)
        height = int(settings.ART_SD_PORTRAIT_HEIGHT)
    override: dict[str, Any] = {"samples_format": "png"}
    if settings.ART_SD_CHECKPOINT:
        override["sd_model_checkpoint"] = settings.ART_SD_CHECKPOINT
    request: dict[str, Any] = {
        "prompt": positive,
        "negative_prompt": negative,
        "steps": int(settings.ART_SD_STEPS),
        "cfg_scale": float(settings.ART_SD_CFG_SCALE),
        "width": width,
        "height": height,
        "override_settings": override,
        "override_settings_restore_afterwards": True,
    }
    if settings.ART_SD_SAMPLER:
        request["sampler_name"] = settings.ART_SD_SAMPLER
    if settings.ART_SD_SCHEDULER:
        request["scheduler"] = settings.ART_SD_SCHEDULER
    return request


def _base_url() -> str:
    return str(settings.ART_SD_BASE_URL).rstrip("/")


def _http_json(url: str, payload: bytes | None) -> dict[str, Any]:
    """Send a JSON request to ``url`` and return the parsed JSON object.

    Enforces a total wall-clock deadline over the exchange: the connection is
    opened with a socket timeout bounded by the remaining budget, every body
    chunk read is bounded by the budget still left at that moment (the socket
    timeout is refreshed before each read), and the connection is closed when
    the budget is exhausted. DNS resolution is the one step stdlib cannot
    bound from this thread -- it is bounded by the operating-system resolver,
    like any other stdlib client. The scheme is restricted to ``http``/
    ``https`` and redirects are never followed (http.client has no redirect
    logic, so a 3xx is a bounded ``sd_http_error``), so a misconfigured base
    URL cannot probe internal services or silently change targets. The
    response body is capped at ``ART_SD_MAX_RESPONSE_BYTES`` before any
    unbounded allocation.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        raise SDError(
            "sd_connection_error",
            f"sd-webui base URL uses unsupported scheme {parsed.scheme!r}",
        )
    if not parsed.hostname:
        raise SDError("sd_connection_error", "sd-webui base URL has no host")
    try:
        port = parsed.port
    except ValueError as error:
        raise SDError(
            "sd_connection_error", f"sd-webui base URL has an invalid port: {error}"
        ) from error
    deadline = time.monotonic() + float(settings.ART_SD_TIMEOUT_SECONDS)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise SDError("sd_timeout", "sd-webui request deadline expired before connect")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    headers = {"Content-Type": "application/json"}
    method = "POST" if payload is not None else "GET"
    timeout = min(float(settings.ART_SD_TIMEOUT_SECONDS), remaining)
    if parsed.scheme == "https":
        connection = http.client.HTTPSConnection(
            parsed.hostname, port or 443, timeout=timeout
        )
    else:
        connection = http.client.HTTPConnection(
            parsed.hostname, port or 80, timeout=timeout
        )
    try:
        try:
            connection.request(method, path, body=payload, headers=headers)
            response = connection.getresponse()
            try:
                if response.status != 200:
                    raise SDError(
                        "sd_http_error",
                        f"sd-webui returned HTTP {response.status} {response.reason}",
                    )
                raw = _read_body_capped(response, connection, deadline)
            finally:
                response.close()
        except SDError:
            raise
        except socket.timeout as error:
            raise SDError("sd_timeout", "sd-webui socket operation timed out") from error
        except (http.client.HTTPException, OSError) as error:
            raise SDError(
                "sd_connection_error", f"cannot reach sd-webui: {error}"
            ) from error
    finally:
        connection.close()
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SDError(
            "sd_malformed_response", f"sd-webui returned a non-JSON body: {error}"
        ) from error
    if not isinstance(body, dict):
        raise SDError("sd_malformed_response", "sd-webui returned a non-object JSON body")
    return body


def _read_body_capped(response, connection, deadline: float) -> bytes:
    """Read the response body in chunks against the deadline and size cap.

    Before every chunk the socket timeout is refreshed to the budget still
    remaining, so a read that stalls past the total deadline is cut off by the
    socket timeout and mapped to ``sd_timeout`` by the caller.
    """
    cap = int(settings.ART_SD_MAX_RESPONSE_BYTES)
    chunks: list[bytes] = []
    total = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SDError("sd_timeout", "sd-webui response exceeded the total deadline")
        sock = getattr(connection, "sock", None)
        if sock is not None:
            try:
                sock.settimeout(remaining)
            except OSError:
                pass
        chunk = response.read(_READ_CHUNK_BYTES)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > cap:
            raise SDError(
                "sd_response_too_large",
                f"sd-webui response exceeded {cap} bytes",
            )
        chunks.append(chunk)


def default_transport(request: dict[str, Any]) -> dict[str, Any]:
    """The real transport: POST the request to the txt2img endpoint."""
    return _http_json(f"{_base_url()}/sdapi/v1/txt2img", json.dumps(request).encode("utf-8"))


def _decode_image(response: dict[str, Any]) -> bytes:
    """Validate the sd-webui envelope and return the decoded PNG bytes.

    Validates: non-empty ``images``, ``images[0]`` base64 text that decodes
    under the response cap, PNG magic bytes, and an IHDR whose width, height,
    and total pixels stay within the configured caps.
    """
    if not isinstance(response, dict):
        raise SDError("sd_malformed_response", "transport returned a non-object envelope")
    images = response.get("images")
    if not isinstance(images, list) or not images:
        raise SDError("sd_no_image", "txt2img response carries no images")
    payload = images[0]
    if not isinstance(payload, str):
        raise SDError("sd_malformed_response", "txt2img images[0] is not base64 text")
    cap = int(settings.ART_SD_MAX_RESPONSE_BYTES)
    if len(payload) > cap:
        raise SDError("sd_response_too_large", f"base64 payload exceeded {cap} bytes")
    try:
        png = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as error:
        raise SDError("sd_decode_error", f"txt2img image is not valid base64: {error}") from error
    if not png.startswith(_PNG_MAGIC):
        raise SDError("sd_not_png", "decoded image is not a PNG")
    if len(png) < _PNG_IHDR_END:
        raise SDError("sd_not_png", "decoded PNG is missing its IHDR chunk")
    if png[12:16] != _PNG_IHDR_CHUNK:
        raise SDError("sd_not_png", "decoded PNG has no IHDR chunk")
    if struct.unpack(">I", png[8:12])[0] != _PNG_IHDR_LENGTH:
        raise SDError("sd_not_png", "decoded PNG has an invalid IHDR length")
    width, height = struct.unpack(">II", png[16:24])
    if width < 1 or height < 1:
        raise SDError("sd_not_png", "decoded PNG has invalid dimensions")
    max_dimension = int(settings.ART_SD_MAX_IMAGE_DIMENSIONS)
    max_pixels = int(settings.ART_SD_MAX_IMAGE_PIXELS)
    if width > max_dimension or height > max_dimension or width * height > max_pixels:
        raise SDError(
            "sd_image_dimensions_too_large",
            f"decoded PNG {width}x{height} exceeds the dimension/pixel caps",
        )
    return png


_prepin_lock = threading.Lock()
_samples_format_prepinned = False


def maybe_prepin_samples_format() -> None:
    """Optionally pin ``samples_format=png`` on the server once per process.

    sd-webui/Forge validates ``samples_format`` before applying
    ``override_settings``, so a server whose persistent value is unsupported
    (e.g. ``avif``) rejects txt2img even with the request-scoped override. The
    pre-pin permanently mutates the shared server's persistent default, so it
    runs only when the deployment opted in with ``ART_SD_PREPIN_SAMPLES_FORMAT``
    and only once per process under a lock-protected guard. It logs when it
    actually mutates the server and never fails a job on its own failure.
    """
    if not settings.ART_SD_PREPIN_SAMPLES_FORMAT:
        return
    global _samples_format_prepinned
    with _prepin_lock:
        if _samples_format_prepinned:
            return
        _samples_format_prepinned = True
    try:
        current = _http_json(f"{_base_url()}/sdapi/v1/options", None).get("samples_format")
        if current == "png":
            return
        result = _http_json(
            f"{_base_url()}/sdapi/v1/options",
            json.dumps({"samples_format": "png"}).encode("utf-8"),
        )
        if result.get("samples_format") != "png":
            logger.log_warn(
                "art sd-webui: samples_format pre-pin was not confirmed by the server"
            )
        else:
            logger.log_info("art sd-webui: pinned samples_format to png on the server")
    except Exception as error:  # noqa: BLE001 - the pre-pin never fails a job
        logger.log_warn(f"art sd-webui: samples_format pre-pin failed: {error}")


def resolve_sd_client() -> SDWebUIClient:
    """Instantiate the ``ART_SD_CLIENT`` dotted-path class (the swappable seam)."""
    dotted = settings.ART_SD_CLIENT
    module_name, separator, class_name = dotted.rpartition(".")
    if not separator:
        raise ValueError(f"ART_SD_CLIENT {dotted!r} is not a dotted module path")
    module = importlib.import_module(module_name)
    client_class = getattr(module, class_name)
    return client_class()


class SDWebUIClient:
    """In-process txt2img client for the configured sd-webui server.

    ``generate(subject, description)`` builds the request from the prompt
    library and generation settings, POSTs it through an injectable transport
    callable (``transport(request) -> dict``), validates the response, and
    returns the decoded PNG bytes. The default transport is a synchronous
    stdlib ``http.client`` exchange with a bounded total deadline and resource
    caps; the caller (the art worker) always invokes it on a background
    Twisted thread, never the reactor thread.
    """

    def __init__(
        self,
        transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ):
        maybe_prepin_samples_format()
        self._transport = transport or default_transport

    def generate(self, subject: ArtSubject, description: str) -> bytes:
        """Generate one PNG for a subject, or raise a named ``SDError``.

        Prompt-library render failures pass through to the caller (the worker
        maps them to ``sd_prompt_error``); every transport, envelope, and
        validation failure becomes a named ``SDError``, so no unexpected
        exception escapes this method.
        """
        request = build_txt2img_request(subject, description)
        try:
            response = self._transport(request)
            return _decode_image(response)
        except SDError:
            raise
        except Exception as error:  # noqa: BLE001 - bounded; never escapes unbounded
            raise SDError(
                "sd_internal_error", f"unexpected sd-webui client failure: {error}"
            ) from error
