"""Tests for the OpenAI-compatible async client (llm-client)."""

from unittest.mock import patch
import json
import unittest

from django.test import override_settings
from twisted.internet import defer
from twisted.internet.task import Clock
from twisted.python.failure import Failure

from evennia.utils.test_resources import EvenniaTestCase

from world.ai.client import OpenAICompatClient
from world.ai.errors import LLMTransportError
from world.ai.profiles import default_profiles, get_profile
from world.ai.schemas import (
    CHAT_COMPLETION_ENVELOPE_SCHEMA,
    ChatRequestDescriptor,
    validate_chat_completion_envelope,
)

from tools.spec_traceability import covers_requirement


def narrator_profile():
    return get_profile("narrator")


def make_client(profile=None, reactor=None):
    return OpenAICompatClient(profile or narrator_profile(), reactor=reactor)


def await_result(d):
    """Consume a synchronously-resolved Deferred and return its value/failure."""
    result = d.result
    d.addErrback(lambda f: None)
    return result


class FakeResponse:
    def __init__(self, code, body):
        self.code = code
        self.body = body

    def deliverBody(self, receiver):
        receiver.dataReceived(self.body)
        receiver.connectionLost()


class HeadlessResponse(FakeResponse):
    def deliverBody(self, receiver):
        pass


class StubAgent:
    def __init__(self, outcome):
        self._outcome = outcome

    def request(self, *args, **kwargs):
        if isinstance(self._outcome, Exception):
            return defer.fail(Failure(self._outcome))
        if isinstance(self._outcome, defer.Deferred):
            return self._outcome
        return defer.succeed(self._outcome)


def envelope(text):
    return json.dumps({"choices": [{"message": {"content": text}}]}).encode()


class ClientConstructionTests(unittest.TestCase):
    def test_constructs_with_a_profile_and_honors_injected_reactor(self):
        clock = Clock()
        profile = narrator_profile()
        client = OpenAICompatClient(profile, reactor=clock)
        self.assertIs(client.profile, profile)
        self.assertIs(client._reactor, clock)
        self.assertIsNotNone(client.agent)

    def test_never_reads_global_llm_settings(self):
        with override_settings(
            LLM_HOST="http://not-read.example",
            LLM_PATH="/not-read",
            LLM_HEADERS={"X-Sentinel": ["yes"]},
        ):
            client = make_client()
            self.assertEqual(client.profile.base_url, narrator_profile().base_url)

    def test_requires_a_profile(self):
        with self.assertRaises(TypeError):
            OpenAICompatClient(None)  # type: ignore[arg-type]


class RequestBodyTests(unittest.TestCase):
    def _body(self, supports_response_format, descriptor):
        from world.ai.profiles import LLMProfile

        profile_values = dict(default_profiles()["narrator"])
        profile_values["supports_response_format"] = supports_response_format
        client = OpenAICompatClient(LLMProfile(**profile_values), reactor=Clock())
        return client._format_request_body(descriptor)

    @covers_requirement("llm-client::openai-compatible-chat-completions-client")
    def test_payload_uses_openai_chat_contract(self):
        body = self._body(
            False,
            ChatRequestDescriptor(
                messages=({"role": "system", "content": "s"}, {"role": "user", "content": "u"})
            ),
        )
        self.assertEqual(body["model"], narrator_profile().model)
        self.assertEqual(
            body["messages"],
            [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        )
        self.assertEqual(body["temperature"], narrator_profile().temperature)
        self.assertEqual(body["max_tokens"], narrator_profile().max_tokens)

    @covers_requirement(
        "llm-client::openai-compatible-chat-completions-client",
        "llm-profiles::structured-output-is-opt-in-per-layer",
    )
    def test_response_format_included_only_when_both_sides_opt_in(self):
        descriptor = ChatRequestDescriptor(
            messages=({"role": "user", "content": "u"},),
            output_schema={"type": "object"},
            schema_id="reward",
        )
        body = self._body(True, descriptor)
        self.assertIn("response_format", body)
        self.assertEqual(body["response_format"]["type"], "json_schema")
        self.assertEqual(body["response_format"]["json_schema"]["name"], "reward")

    @covers_requirement(
        "llm-client::openai-compatible-chat-completions-client",
        "llm-profiles::structured-output-is-opt-in-per-layer",
    )
    def test_response_format_omitted_when_capability_flag_is_false(self):
        descriptor = ChatRequestDescriptor(
            messages=({"role": "user", "content": "u"},),
            output_schema={"type": "object"},
            schema_id="reward",
        )
        body = self._body(False, descriptor)
        self.assertNotIn("response_format", body)

    def test_response_format_omitted_when_schema_is_absent(self):
        descriptor = ChatRequestDescriptor(
            messages=({"role": "user", "content": "u"},)
        )
        body = self._body(True, descriptor)
        self.assertNotIn("response_format", body)

    def test_registered_schema_id_is_resolved_for_response_format(self):
        from world.ai.schemas import register_output_schema
        from world.ai.schemas.registry import _OUTPUT_SCHEMAS

        try:
            register_output_schema("reward", {"type": "object"})
            descriptor = ChatRequestDescriptor(
                messages=({"role": "user", "content": "u"},), schema_id="reward"
            )
            body = self._body(True, descriptor)
            self.assertIn("response_format", body)
            self.assertEqual(
                body["response_format"]["json_schema"]["schema"], {"type": "object"}
            )
        finally:
            _OUTPUT_SCHEMAS.clear()


class ClientResponseTests(EvenniaTestCase):
    @covers_requirement("llm-client::openai-compatible-chat-completions-client")
    def test_successful_chat_completion_returns_message_content(self):
        client = make_client(reactor=Clock())
        client.agent = StubAgent(FakeResponse(200, envelope("hello world")))
        d = client.get_response(
            ChatRequestDescriptor(messages=({"role": "user", "content": "hi"},))
        )
        self.assertEqual(await_result(d), "hello world")

    @covers_requirement("llm-client::safe-failure-signaling-without-exceptions-escaping")
    def test_non_200_status_resolves_as_safe_failure(self):
        client = make_client(reactor=Clock())
        client.agent = StubAgent(FakeResponse(500, b'{"error": "nope"}'))
        d = client.get_response(
            ChatRequestDescriptor(messages=({"role": "user", "content": "hi"},))
        )
        failure = await_result(d)
        self.assertTrue(failure.check(LLMTransportError))

    @covers_requirement("llm-client::safe-failure-signaling-without-exceptions-escaping")
    def test_connection_error_resolves_as_safe_failure(self):
        client = make_client(reactor=Clock())
        client.agent = StubAgent(ConnectionError("refused"))
        d = client.get_response(
            ChatRequestDescriptor(messages=({"role": "user", "content": "hi"},))
        )
        failure = await_result(d)
        self.assertTrue(failure.check(LLMTransportError))

    @covers_requirement("llm-client::safe-failure-signaling-without-exceptions-escaping")
    def test_malformed_body_fails_without_crashing(self):
        client = make_client(reactor=Clock())
        client.agent = StubAgent(FakeResponse(200, b"not-json"))
        d = client.get_response(
            ChatRequestDescriptor(messages=({"role": "user", "content": "hi"},))
        )
        failure = await_result(d)
        self.assertTrue(failure.check(LLMTransportError))

    def test_envelope_missing_content_fails(self):
        client = make_client(reactor=Clock())
        body = json.dumps({"choices": [{"message": {}}]}).encode()
        client.agent = StubAgent(FakeResponse(200, body))
        d = client.get_response(
            ChatRequestDescriptor(messages=({"role": "user", "content": "hi"},))
        )
        failure = await_result(d)
        self.assertTrue(failure.check(LLMTransportError))


class ClientTimeoutTests(EvenniaTestCase):
    @covers_requirement("llm-client::asynchronous-calls-with-bounded-request-timeouts")
    def test_slow_endpoint_abandoned_at_timeout_bound(self):
        clock = Clock()
        client = make_client(reactor=clock)
        never = defer.Deferred()
        client.agent = StubAgent(never)
        d = client.get_response(
            ChatRequestDescriptor(messages=({"role": "user", "content": "hi"},))
        )
        self.assertFalse(d.called)
        clock.advance(narrator_profile().timeout_seconds + 1)
        failure = await_result(d)
        self.assertTrue(failure.check(LLMTransportError))
        self.assertEqual(failure.value.kind, "timeout")

    @covers_requirement("llm-client::asynchronous-calls-with-bounded-request-timeouts")
    def test_headers_but_no_body_abandoned_at_timeout_bound(self):
        clock = Clock()
        client = make_client(reactor=clock)
        client.agent = StubAgent(HeadlessResponse(200, b""))
        d = client.get_response(
            ChatRequestDescriptor(messages=({"role": "user", "content": "hi"},))
        )
        self.assertIsInstance(d, defer.Deferred)
        clock.advance(narrator_profile().timeout_seconds + 1)
        failure = await_result(d)
        self.assertTrue(failure.check(LLMTransportError))

    @covers_requirement("llm-client::asynchronous-calls-with-bounded-request-timeouts")
    def test_server_is_not_blocked_while_waiting(self):
        clock = Clock()
        client = make_client(reactor=clock)
        never = defer.Deferred()
        client.agent = StubAgent(never)
        d = client.get_response(
            ChatRequestDescriptor(messages=({"role": "user", "content": "hi"},))
        )
        self.assertIsInstance(d, defer.Deferred)
        self.assertFalse(d.called)


class ResponseEnvelopeSchemaTests(unittest.TestCase):
    def test_envelope_schema_importable_and_valid(self):
        self.assertIn("choices", CHAT_COMPLETION_ENVELOPE_SCHEMA["required"])
        self.assertEqual(
            validate_chat_completion_envelope({"choices": [{"message": {"content": "x"}}]}),
            [],
        )

    def test_envelope_schema_rejects_invalid_shapes(self):
        self.assertTrue(validate_chat_completion_envelope({"choices": []}))
        self.assertTrue(validate_chat_completion_envelope({}))
        self.assertTrue(
            validate_chat_completion_envelope({"choices": [{"message": {"content": 5}}]})
        )
