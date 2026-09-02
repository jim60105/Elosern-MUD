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

from world.observability import log_warn
from world.observability.sanitize import safe_endpoint

# Verbatim-passthrough sampling knobs (endpoint design §4.2 request order).
_TOKEN_FIELDS: tuple[str, ...] = (
    "frequency_penalty",
    "presence_penalty",
    "top_k",
    "top_p",
    "repetition_penalty",
    "min_p",
    "top_a",
)


def _request_headers(profile: LLMProfile) -> dict[str, list[str]]:
    """Build the wire headers: derived entries first, explicit ones win.

    ``Authorization``/``X-Title``/``HTTP-Referer`` are derived from the
    profile fields only when those fields are non-empty; the profile's frozen
    ``headers`` mapping is overlaid last so an explicitly configured header
    replaces a derived entry (design D-B2; the overlay is exact-case at the
    mapping level, and Twisted's ``Headers`` then normalizes names
    case-insensitively, so an explicit header wins on the wire either way).
    The api key reaches only the derived ``Authorization`` value — never a
    log line or error string.
    """
    headers: dict[str, list[str]] = {}
    if profile.api_key:
        headers["Authorization"] = [f"Bearer {profile.api_key}"]
    if profile.app_title:
        headers["X-Title"] = [profile.app_title]
    if profile.app_url:
        headers["HTTP-Referer"] = [profile.app_url]
    for name, values in profile.headers.items():
        headers[name] = list(values)
    return headers


class _RedactedChainLink(Exception):
    """Stand-in for a chain link whose text carried the api key.

    Instances are built with the original link's type name so the rendered
    ``tb`` segment still identifies the exception type while its message is
    scrubbed.
    """


def _copy_chain_link(link: BaseException, api_key: str) -> BaseException:
    """Copy one chain link, scrubbing the key from its observable text.

    A type-preserving copy keeps ``args``, ``__dict__`` (so ``kind``-style
    attributes survive) and the traceback (so the rendered raise site is the
    real one). If the key still appears in the copy's ``str()`` — a custom
    ``__str__`` closing over the credential — the copy degrades to a
    name-preserving ``_RedactedChainLink`` with the scrubbed message.
    """
    try:
        copy = type(link).__new__(type(link))
        copy.__dict__.update(link.__dict__)
        copy.args = tuple(
            value.replace(api_key, "[redacted]")
            if isinstance(value, str) and api_key in value
            else value
            for value in link.args
        )
    except Exception:  # observability: ignore R2: copy failure must not raise — an uncopyable link degrades to the scrubbing stand-in below, never a log that could carry the key
        copy = None
    if copy is None or (copy is not None and api_key in str(copy)):
        message = str(link).replace(api_key, "[redacted]")
        copy = type(
            type(link).__name__,
            (_RedactedChainLink,),
            {"__module__": type(link).__module__},
        )(message)
    copy.__traceback__ = link.__traceback__
    copy.__suppress_context__ = link.__suppress_context__
    return copy


def _redact_chain(error: BaseException, api_key: str) -> BaseException:
    """Return the exception chain with every link's text key-scrubbed.

    The observability facade renders the full ``__cause__``/``__context__``
    chain into the log line, and a hostile endpoint can smuggle the bearer
    key into an exception chained to the scrubbed ``LLMTransportError``. The
    api-key non-disclosure invariant is fail-closed, so the emitted chain is
    a copy with each link scrubbed; when no link carries the key the
    original error is returned untouched.
    """
    from world.observability.render import _chain

    links = _chain(error)
    if not api_key or not any(api_key in str(link) for link in links):
        return error
    outer: BaseException | None = None
    # ``_chain`` is innermost-first; rebuild outermost-first so every inner
    # copy relinks to its outer neighbour's replacement.
    for index in range(len(links) - 1, -1, -1):
        link = links[index]
        copy = _copy_chain_link(link, api_key)
        if outer is not None:
            neighbour = links[index + 1]
            if link.__cause__ is neighbour:
                copy.__cause__ = outer
            elif link.__context__ is neighbour:
                copy.__context__ = outer
        outer = copy
    assert outer is not None
    return outer


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

        Composition follows the endpoint design §4.2 order: base fields, then
        ``max_completion_tokens`` superseding ``max_tokens`` (C-10), then each
        configured sampling field verbatim with ``None`` omission, then the
        reasoning mapping, then the ``response_format`` gate. A profile with
        no optional endpoint field set produces a byte-identical body to the
        pre-configuration client (C-5).

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
        }
        if self.profile.max_completion_tokens is not None:
            body["max_completion_tokens"] = self.profile.max_completion_tokens
        else:
            body["max_tokens"] = self.profile.max_tokens
        for name in _TOKEN_FIELDS:
            value = getattr(self.profile, name)
            if value is not None:
                body[name] = value
        self._apply_reasoning(body, self.profile)
        if self.profile.supports_response_format and output_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": descriptor.schema_id or "output",
                    "schema": output_schema,
                },
            }
        return body

    @staticmethod
    def _apply_reasoning(body: dict, profile: LLMProfile) -> None:
        """Map the reasoning intent onto the profile's carrier style (D-B1).

        Exhaustive case table, and no empty container is ever emitted: an
        unset intent (both fields ``None``) and the ``off`` style send
        nothing; ``openrouter`` nests a ``reasoning`` object carrying the
        non-``None`` subset of ``enabled``/``effort``; ``vllm`` carries only
        ``chat_template_kwargs.enable_thinking`` (``effort`` has no vLLM
        carrier, so an effort-only vllm profile sends nothing).
        """
        if profile.reasoning_style == "off":
            return
        if profile.reasoning_enabled is None and profile.reasoning_effort is None:
            return
        if profile.reasoning_style == "vllm":
            if profile.reasoning_enabled is not None:
                body["chat_template_kwargs"] = {
                    "enable_thinking": profile.reasoning_enabled
                }
            return
        reasoning: dict = {}
        if profile.reasoning_enabled is not None:
            reasoning["enabled"] = profile.reasoning_enabled
        if profile.reasoning_effort is not None:
            reasoning["effort"] = profile.reasoning_effort
        if reasoning:
            body["reasoning"] = reasoning

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
            # Envelope-validation messages quote the offending instance
            # value, and a hostile endpoint may echo a request header (the
            # bearer key) back inside it — scrub before it becomes observable.
            raise LLMTransportError(
                "malformed", self._scrub_key("; ".join(errors))
            )
        return payload["choices"][0]["message"]["content"]

    def _scrub_key(self, message: str) -> str:
        """Central credential scrub for every dynamically formed error.

        Fail-closed for the api-key non-disclosure invariant: any string that
        can reach a caller or the safe log path passes through here, so no
        endpoint- or transport-controlled text can carry the key out.
        """
        if self.profile.api_key:
            return message.replace(self.profile.api_key, "[redacted]")
        return message

    def _handle_llm_error(self, failure):
        """Map connection failures to a safe ``LLMTransportError`` errback."""
        failure.trap(Exception)
        message = failure.getErrorMessage() or failure.type.__name__
        # Transport error text is not header-controlled in practice, but the
        # api-key invariant is fail-closed: the message is endpoint-adjacent,
        # so it goes through the same central scrub.
        raise LLMTransportError(
            "connection", f"request failed: {self._scrub_key(message)}"
        )

    def _on_timeout(self, result, timeout):
        """Translate a ``Deferred.addTimeout`` cancellation to a transport error."""
        raise LLMTransportError("timeout", f"request timed out after {timeout}s")

    def _safe_log_error(self, failure):
        """Log one bounded transport diagnostic containing no prompt, body, or player text.

        ``LLMTransportError`` messages are static or key-scrubbed at
        construction, but the facade also renders the chained links, so the
        emitted chain is scrubbed link-by-link first. Residual unexpected
        failure values never passed through the scrub, so their chain stays
        fail-closed: only the exception type is logged.
        """
        error = failure.value
        if isinstance(error, LLMTransportError):
            log_warn(
                "llm_transport_error",
                context={
                    "endpoint": safe_endpoint(
                        self.profile.base_url.rstrip("/") + self.profile.path
                    ),
                    "kind": error.kind,
                },
                exc=_redact_chain(error, self.profile.api_key),
            )
        else:
            log_warn(
                "llm_client_unexpected_error",
                context={"kind": "unexpected", "exc_type": type(error).__name__},
            )
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
            headers=Headers(_request_headers(self.profile)),
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
