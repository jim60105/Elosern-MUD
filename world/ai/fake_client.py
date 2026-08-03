"""Deterministic Deferred-returning test double for ``OpenAICompatClient``.

``FakeLLMClient`` never opens a socket. It replays recorded fixtures keyed by a
stable request matcher and supports scripted transport-style failures (timeout,
HTTP error, connection error, unparseable non-JSON body) so guardrail tests can
drive the degrade path offline. It errbacks with the same ``LLMTransportError``
failure signatures as the real client.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from twisted.internet import defer
from twisted.python.failure import Failure

from world.ai.errors import LLMTransportError
from world.ai.schemas.descriptor import ChatRequestDescriptor

Matcher = Callable[[ChatRequestDescriptor], bool] | str


class MissingFixtureError(KeyError):
    """Raised when a request matches no recorded fixture."""


def request_signature(descriptor: ChatRequestDescriptor) -> str:
    """Return a stable, order-insensitive signature for one request."""
    return json.dumps(
        {
            "messages": list(descriptor.messages),
            "schema_id": descriptor.schema_id,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


class FakeLLMClient:
    """Replay double with the same ``get_response`` interface as the client."""

    def __init__(self):
        self._fixtures: list[tuple[Matcher, Any]] = []
        self.calls: list[ChatRequestDescriptor] = []

    def add_response(self, matcher: Matcher, text: str) -> None:
        """Record a text fixture for requests matching ``matcher``."""
        self._fixtures.append((matcher, text))

    def add_failure(self, matcher: Matcher, error: LLMTransportError) -> None:
        """Record a transport-failure fixture for requests matching ``matcher``."""
        self._fixtures.append((matcher, error))

    def add_timeout(self, matcher: Matcher) -> None:
        self.add_failure(matcher, LLMTransportError("timeout", "simulated timeout"))

    def add_http_error(self, matcher: Matcher) -> None:
        self.add_failure(matcher, LLMTransportError("http", "simulated HTTP error"))

    def add_connection_error(self, matcher: Matcher) -> None:
        self.add_failure(matcher, LLMTransportError("connection", "simulated connection error"))

    def add_malformed_body(self, matcher: Matcher) -> None:
        self.add_failure(matcher, LLMTransportError("malformed", "simulated non-JSON body"))

    def _matches(self, matcher: Matcher, descriptor: ChatRequestDescriptor) -> bool:
        if callable(matcher):
            return matcher(descriptor)
        return request_signature(descriptor) == matcher

    def get_response(self, descriptor: ChatRequestDescriptor):
        """Resolve the first matching fixture, or errback with a named error."""
        self.calls.append(descriptor)
        for matcher, outcome in self._fixtures:
            if not self._matches(matcher, descriptor):
                continue
            if isinstance(outcome, LLMTransportError):
                return defer.fail(Failure(outcome))
            return defer.succeed(outcome)
        return defer.fail(Failure(MissingFixtureError(request_signature(descriptor))))
