"""Request admission for the local service (pure ASGI middleware).

Order, for every HTTP request, before any route runs, lock is taken or file is
read:

1. ``Host`` must be one of the exact loopback ``host:port`` values the service
   was started for (blocks DNS rebinding).
2. ``Origin``, when sent, must be this service's own origin (``null`` and every
   other origin, including other localhost ports, are foreign).
   ``Sec-Fetch-Site``, when sent, must be ``same-origin`` or ``none``.
3. Only ``GET``/``HEAD``/``POST`` are served.
4. A ``POST`` additionally requires a matching ``Origin``, the current launch
   token in ``X-Map-Editor-Token``, ``Content-Type: application/json`` and a
   body within the size bound -- checked from ``Content-Length`` before
   reading, and counted while reading for a body without one.

No CORS header is ever emitted. Every response carries a restrictive Content
Security Policy, so the page can load nothing but this origin's own assets.
"""

from __future__ import annotations

import hmac
import json
from collections.abc import Callable

TOKEN_HEADER = "x-map-editor-token"
SAFE_FETCH_SITES = frozenset({"same-origin", "none"})
ALLOWED_METHODS = frozenset({"GET", "HEAD", "POST"})

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
)
SECURITY_HEADERS = (
    (b"content-security-policy", CONTENT_SECURITY_POLICY.encode("ascii")),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"cross-origin-resource-policy", b"same-origin"),
    (b"x-frame-options", b"DENY"),
)


def error_body(code: str, message: str) -> bytes:
    return json.dumps({"error": {"code": code, "message": message}}).encode("utf-8")


class AdmissionMiddleware:
    """Reject foreign, unauthenticated or oversized requests up front."""

    def __init__(
        self,
        app,
        *,
        allowed_hosts: frozenset[str],
        allowed_origins: frozenset[str],
        token: Callable[[], str],
        max_body_bytes: int,
    ) -> None:
        self.app = app
        self.allowed_hosts = allowed_hosts
        self.allowed_origins = allowed_origins
        self.token = token
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secured_send(message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if not name.lower().startswith(b"access-control-")
                ]
                headers.extend(SECURITY_HEADERS)
                if scope.get("path", "").startswith("/api/"):
                    headers.append((b"cache-control", b"no-store"))
                message = {**message, "headers": headers}
            await send(message)

        rejection = self._admit_headers(scope)
        if rejection is not None:
            await self._reject(secured_send, *rejection)
            return
        if scope["method"] != "POST":
            await self.app(scope, receive, secured_send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_body_bytes:
                await self._reject(secured_send, 413, "body_too_large", "the request body exceeds the limit")
                return
            if not message.get("more_body", False):
                break
        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, secured_send)

    def _admit_headers(self, scope) -> tuple[int, str, str] | None:
        headers: dict[str, list[str]] = {}
        for raw_name, raw_value in scope.get("headers", []):
            headers.setdefault(raw_name.decode("latin-1").lower(), []).append(
                raw_value.decode("latin-1")
            )

        def single(name: str) -> str | None:
            values = headers.get(name)
            if not values:
                return None
            if len(values) > 1:
                return "\0duplicate"
            return values[0]

        host = single("host")
        if host is None or host not in self.allowed_hosts:
            return 403, "forbidden_host", "the Host header is not this local service"
        origin = single("origin")
        if origin is not None and origin not in self.allowed_origins:
            return 403, "forbidden_origin", "requests from another origin are refused"
        fetch_site = single("sec-fetch-site")
        if fetch_site is not None and fetch_site not in SAFE_FETCH_SITES:
            return 403, "forbidden_origin", "cross-origin requests are refused"
        method = scope["method"]
        if method not in ALLOWED_METHODS:
            return 405, "method_not_allowed", "only GET, HEAD and POST are served"
        if method != "POST":
            return None
        if origin is None:
            return 403, "forbidden_origin", "a mutating request must name this origin"
        token = single(TOKEN_HEADER)
        if token is None or not hmac.compare_digest(token.encode("utf-8"), self.token().encode("utf-8")):
            return 401, "unauthorized", "the launch-session token is missing or not current"
        content_type = (single("content-type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return 415, "unsupported_media_type", "mutating requests carry application/json"
        length = single("content-length")
        if length is not None:
            if not length.isdigit():
                return 400, "invalid_content_length", "Content-Length is not a decimal byte count"
            if int(length) > self.max_body_bytes:
                return 413, "body_too_large", "the request body exceeds the limit"
        return None

    @staticmethod
    async def _reject(send, status: int, code: str, message: str) -> None:
        body = error_body(code, message)
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


__all__ = ["AdmissionMiddleware", "CONTENT_SECURITY_POLICY", "TOKEN_HEADER", "error_body"]
