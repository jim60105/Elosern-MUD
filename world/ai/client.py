"""OpenAI-compatible asynchronous chat-completion client (llm-client).

``OpenAICompatClient`` subclasses Evennia's ``LLMClient`` and keeps its Twisted
async skeleton (connection pool, ``Agent``, ``StringProducer``,
``SimpleResponseReceiver``) while overriding the request payload for OpenAI's
``/v1/chat/completions`` contract, the response parsing, and the per-request
timeout. The governing configuration comes from one frozen ``LLMProfile``
rather than the global ``LLM_*`` settings.
"""

from __future__ import annotations

import json

from twisted.internet import reactor as global_reactor
from twisted.web.client import Agent, HTTPConnectionPool
from twisted.web.http_headers import Headers

from evennia.contrib.rpg.llm.llm_client import (
    LLMClient,
    QuietHTTP11ClientFactory,
    SimpleResponseReceiver,
    StringProducer,
)

from world.ai.errors import LLMTransportError
from world.ai.profiles import LLMProfile
from world.ai.schemas.descriptor import ChatRequestDescriptor
from world.ai.schemas.registry import resolve_output_schema
from world.ai.schemas.response import validate_chat_completion_envelope

from evennia import logger

_SAFE_LOG_PREFIX = "LLM client"


class OpenAICompatClient(LLMClient):
    """Async OpenAI ``/v1/chat/completions`` client governed by one profile."""

    def __init__(self, profile: LLMProfile, reactor=None):
        """Build the Twisted transport on an injected reactor.

        Unlike the parent constructor, this does not read the global ``LLM_*``
        settings: the profile is the single source of endpoint configuration.
        An injected reactor (``twisted.internet.task.Clock`` in tests) is
        honored without patching the module-global reactor.
        """
        if not isinstance(profile, LLMProfile):
            raise TypeError("profile must be an LLMProfile")
        self.profile = profile
        self._reactor = reactor if reactor is not None else global_reactor
        self._conn_pool = HTTPConnectionPool(self._reactor)
        self._conn_pool._factory = QuietHTTP11ClientFactory
        self.agent = Agent(self._reactor, pool=self._conn_pool)

    def _format_request_body(self, descriptor: ChatRequestDescriptor) -> dict:
        """Build the OpenAI ``/v1/chat/completions`` request body.

        ``response_format`` is included only when the profile declares endpoint
        support AND the descriptor declares an output schema (inline or via a
        registered ``schema_id``).
        """
        output_schema = resolve_output_schema(
            descriptor.output_schema, descriptor.schema_id
        )
        body: dict = {
            "model": self.profile.model,
            "messages": list(descriptor.messages),
            "temperature": self.profile.temperature,
            "max_tokens": self.profile.max_tokens,
        }
        if self.profile.supports_response_format and output_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": descriptor.schema_id or "output",
                    "schema": output_schema,
                },
            }
        return body

    def _parse_response(self, result):
        """Parse a ``(status_code, body)`` result into the generated text."""
        status_code, body = result
        if status_code != 200:
            raise LLMTransportError(
                "http", f"endpoint returned HTTP {status_code}"
            )
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
            raise LLMTransportError("malformed", "response body is not valid JSON") from exc
        errors = validate_chat_completion_envelope(payload)
        if errors:
            raise LLMTransportError("malformed", "; ".join(errors))
        return payload["choices"][0]["message"]["content"]

    def _handle_llm_error(self, failure):
        """Map connection failures to a safe ``LLMTransportError`` errback."""
        failure.trap(Exception)
        message = failure.getErrorMessage() or failure.type.__name__
        raise LLMTransportError("connection", f"request failed: {message}")

    def _on_timeout(self, result, timeout):
        """Translate a ``Deferred.addTimeout`` cancellation to a transport error."""
        raise LLMTransportError("timeout", f"request timed out after {timeout}s")

    def _safe_log_error(self, failure):
        """Log a safe error summary containing no prompt, body, or player text."""
        error = failure.value
        if isinstance(error, LLMTransportError):
            logger.log_info(f"{_SAFE_LOG_PREFIX} {error.kind} failure")
        else:
            logger.log_info(f"{_SAFE_LOG_PREFIX} unexpected failure")
        return failure

    def get_response(self, descriptor: ChatRequestDescriptor):
        """Send one chat completion and resolve with the generated text.

        Returns a Deferred. Transport failures (connection, HTTP, malformed
        body, timeout) errback with ``LLMTransportError``; the timeout covers
        the complete exchange through response-body parsing.
        """
        request_body = self._format_request_body(descriptor)
        url = self.profile.base_url.rstrip("/") + self.profile.path
        d = self.agent.request(
            b"POST",
            bytes(url, "utf-8"),
            headers=Headers(self.profile.headers),
            bodyProducer=StringProducer(json.dumps(request_body)),
        )
        d = d.addCallback(self._handle_llm_response_body)
        d = d.addErrback(self._handle_llm_error)
        d = d.addCallback(self._parse_response)
        d = d.addTimeout(
            self.profile.timeout_seconds,
            self._reactor,
            onTimeoutCancel=self._on_timeout,
        )
        d = d.addErrback(self._safe_log_error)
        return d
