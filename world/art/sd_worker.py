"""The internal sd-webui client: request building, bounded transport, validation.

This module replaces the external subprocess worker (design D11 amendment): the
engine now owns an in-process client that POSTs ``/sdapi/v1/txt2img`` to the
configured ``ART_SD_BASE_URL``, validates the response envelope, and returns a
``GeneratedImage`` (validated PNG bytes plus the server-reported generation
seed). It also exposes bounded GET enumeration of the server's models,
samplers, schedulers, styles, and modules for the ``@art options`` staff
diagnostic. It is the only module that opens an sd-webui connection.

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
from dataclasses import dataclass
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

# Enforced option-enumeration bounds (art-sd-server-integration): the five
# public list_* wrappers take no parameters, so these are invariants, not
# caller-adjustable defaults.
_OPTIONS_MAX_ITEMS = 100
_OPTIONS_TIMEOUT_SECONDS = 10.0

# The fixed Forge companion setting for forge_additional_modules, verbatim
# from the verified reference plugin.
_FORGE_UNET_STORAGE_DTYPE = "Automatic (fp16 LoRA)"


class SDError(Exception):
    """One bounded, named sd-webui failure; ``code`` is the settle error code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class GeneratedImage:
    """One generated image: validated PNG bytes plus the server seed.

    ``seed`` is the server-reported generation seed parsed defensively from
    the response ``info`` field, or ``None`` when the server reported no
    usable seed. A seedless image is still a perfectly good image.
    """

    data: bytes
    seed: int | None


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


def _split_name_list(raw: str) -> list[str]:
    """Split a free-text CSV knob into verbatim non-empty name entries."""
    return [
        item for item in (part.strip() for part in str(raw or "").split(",")) if item
    ]


def build_txt2img_request(subject: ArtSubject, description: str) -> dict[str, Any]:
    """Build the txt2img request body for one subject.

    Fills steps/cfg from settings, width/height from the subject's aspect ratio
    (scene 16:9, portrait 3:4), passes through a non-empty sampler/scheduler/
    checkpoint, and always requests ``samples_format: "png"`` request-scoped
    with ``override_settings_restore_afterwards: true``. Non-empty
    ``ART_SD_STYLES`` / ``ART_SD_MODULES`` CSV knobs pass through verbatim as
    the ``styles`` field and the Forge ``forge_additional_modules`` companion
    pair; empty knobs omit the fields entirely (like sampler/scheduler).
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
    modules = _split_name_list(settings.ART_SD_MODULES)
    if modules:
        override["forge_additional_modules"] = modules
        override["forge_unet_storage_dtype"] = _FORGE_UNET_STORAGE_DTYPE
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
    styles = _split_name_list(settings.ART_SD_STYLES)
    if styles:
        request["styles"] = styles
    return request


def _base_url() -> str:
    return str(settings.ART_SD_BASE_URL).rstrip("/")


def _basic_auth_header() -> dict[str, str]:
    """The Basic auth header iff BOTH secret-file credentials are set.

    A half-configured pair (username without password, or vice versa) is a
    documented misconfiguration and stays anonymous — no ``user:``-style
    header is ever sent. The password never appears in any log line or error
    derived from this header.
    """
    username = str(settings.ART_SD_USERNAME or "")
    password = str(settings.ART_SD_PASSWORD or "")
    if not username or not password:
        return {}
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _http_request(
    url: str, payload: bytes | None, timeout_seconds: float | None = None
) -> Any:
    """Send one request and return the parsed JSON body (any top-level shape).

    Enforces a total wall-clock deadline over the exchange: the budget is
    ``timeout_seconds`` when given (the bounded diagnostic calls) or the
    ``ART_SD_TIMEOUT_SECONDS`` setting otherwise; the connection is opened with
    a socket timeout bounded by the remaining budget, every body chunk read is
    bounded by the budget still left at that moment (the socket timeout is
    refreshed before each read), and the connection is closed when the budget
    is exhausted. DNS resolution is the one step stdlib cannot bound from this
    thread -- it is bounded by the operating-system resolver, like any other
    stdlib client. The scheme is restricted to ``http``/``https`` and redirects
    are never followed (http.client has no redirect logic, so a 3xx is a
    bounded ``sd_http_error``), so a misconfigured base URL cannot probe
    internal services or silently change targets. The response body is capped
    at ``ART_SD_MAX_RESPONSE_BYTES`` before any unbounded allocation. A GET
    carries no ``Content-Type`` (there is no body to type); every request
    carries Basic auth only when both credentials are configured.
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
    budget = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else float(settings.ART_SD_TIMEOUT_SECONDS)
    )
    deadline = time.monotonic() + budget
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise SDError("sd_timeout", "sd-webui request deadline expired before connect")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    headers: dict[str, str] = {}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    headers.update(_basic_auth_header())
    method = "POST" if payload is not None else "GET"
    timeout = min(budget, remaining)
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
    return body


def _http_json(
    url: str, payload: bytes | None, timeout_seconds: float | None = None
) -> dict[str, Any]:
    """``_http_request`` narrowed to a JSON object (the txt2img envelope)."""
    body = _http_request(url, payload, timeout_seconds)
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


def _list_options(path: str, *, item_keys: tuple[str, ...]) -> list[str]:
    """GET one option endpoint and return the verbatim selectable names.

    Bounded by design (art-sd-server-integration): the fixed 10-s per-call
    timeout cap, the existing response-size cap, and a 100-item list cap. A
    non-list body, an oversized list, a non-dict item, or an item without any
    string fallback field is ``sd_malformed_response``; names are returned
    verbatim (never normalised) so staff can copy them exactly, with only
    whitespace-empty names dropped.
    """
    body = _http_request(
        f"{_base_url()}{path}", None, timeout_seconds=_OPTIONS_TIMEOUT_SECONDS
    )
    if not isinstance(body, list):
        raise SDError(
            "sd_malformed_response", f"option endpoint {path} returned a non-list body"
        )
    if len(body) > _OPTIONS_MAX_ITEMS:
        raise SDError(
            "sd_malformed_response",
            f"option endpoint {path} returned more than {_OPTIONS_MAX_ITEMS} items",
        )
    names: list[str] = []
    for item in body:
        if not isinstance(item, dict):
            raise SDError(
                "sd_malformed_response",
                f"option endpoint {path} returned a non-object item",
            )
        chosen: str | None = None
        for key in item_keys:
            value = item.get(key)
            if isinstance(value, str):
                chosen = value
                break
        if chosen is None:
            raise SDError(
                "sd_malformed_response",
                f"option endpoint {path} returned an item without a name field",
            )
        if not chosen.strip():
            continue
        names.append(chosen)
    return names


def list_models() -> list[str]:
    """The server's exact model titles (``title`` then ``model_name``)."""
    return _list_options("/sdapi/v1/sd-models", item_keys=("title", "model_name"))


def list_samplers() -> list[str]:
    """The server's exact sampler names."""
    return _list_options("/sdapi/v1/samplers", item_keys=("name",))


def list_schedulers() -> list[str]:
    """The server's scheduler labels (``label`` then ``name``)."""
    return _list_options("/sdapi/v1/schedulers", item_keys=("label", "name"))


def list_styles() -> list[str]:
    """The server's exact prompt-style names."""
    return _list_options("/sdapi/v1/prompt-styles", item_keys=("name",))


def list_modules() -> list[str]:
    """The server's Forge module file names (Forge forks only)."""
    return _list_options("/sdapi/v1/sd-modules", item_keys=("model_name",))


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


def _parse_seed(response: dict[str, Any]) -> int | None:
    """Defensively extract ``info.seed`` from an envelope; never raises.

    ``info`` may be absent, a JSON string (the A1111/Forge shape), an
    already-decoded dict (some proxies), or garbage. A usable seed is a
    non-negative int (bool rejected). Any other shape yields ``None``: a
    seedless image is still a perfectly good image.
    """
    info = response.get("info")
    if isinstance(info, str):
        try:
            info = json.loads(info)
        except ValueError:
            return None
    if not isinstance(info, dict):
        return None
    seed = info.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        return None
    return seed


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
    returns a ``GeneratedImage``. The default transport is a synchronous
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

    def generate(self, subject: ArtSubject, description: str) -> GeneratedImage:
        """Generate one image for a subject, or raise a named ``SDError``.

        Prompt-library render failures pass through to the caller (the worker
        maps them to ``sd_prompt_error``); every transport, envelope, and
        validation failure becomes a named ``SDError``, so no unexpected
        exception escapes this method. The returned seed is the server-reported
        generation seed, or ``None`` when absent/unparseable — never job-fatal.
        """
        request = build_txt2img_request(subject, description)
        try:
            response = self._transport(request)
            data = _decode_image(response)
            return GeneratedImage(data=data, seed=_parse_seed(response))
        except SDError:
            raise
        except Exception as error:  # noqa: BLE001 - bounded; never escapes unbounded
            raise SDError(
                "sd_internal_error", f"unexpected sd-webui client failure: {error}"
            ) from error
