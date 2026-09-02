"""Tests for the OpenAI-compatible async client (llm-client)."""

from unittest.mock import patch
import json
import unittest

from django.test import override_settings
from twisted.internet import defer
from twisted.internet.task import Clock
from twisted.python.failure import Failure
from twisted.web.http_headers import Headers

from evennia.utils.test_resources import EvenniaTestCase

from world.ai.client import OpenAICompatClient
from world.ai.errors import LLMTransportError
from world.ai.profiles import LLMProfile, ProfileValidationError, default_profiles, get_profile
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
        self.calls = []

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self._outcome, Exception):
            return defer.fail(Failure(self._outcome))
        if isinstance(self._outcome, defer.Deferred):
            return self._outcome
        return defer.succeed(self._outcome)


def captured_body(agent):
    """Decode the JSON body of the single captured get_response request."""
    assert len(agent.calls) == 1, "expected exactly one captured request"
    _, kwargs = agent.calls[0]
    return json.loads(kwargs["bodyProducer"].body.decode("utf-8"))


def captured_headers(agent):
    """Raw wire headers of the captured request, lower-cased for asserts.

    Goes through Twisted's ``Headers`` normalization boundary: the assertion
    sees what the transport would send, not the intermediate Python dict.
    """
    assert len(agent.calls) == 1, "expected exactly one captured request"
    _, kwargs = agent.calls[0]
    return {
        name.decode("utf-8").lower(): [value.decode("utf-8") for value in values]
        for name, values in kwargs["headers"].getAllRawHeaders()
    }


def wire_profile(**overrides):
    """A narrator profile with the given endpoint-field overrides applied."""
    values = dict(default_profiles()["narrator"])
    values.update(overrides)
    return LLMProfile(**values)


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

    def test_default_configured_body_is_byte_compatible(self):
        """Design D-A6 guard: with no environment/setting overrides the
        payload bytes equal exactly the pre-endpoint-knob serialization; the
        optional endpoint fields serialize as nothing when unset (the
        wire-configuration change keeps this byte identity as its baseline
        requirement)."""
        from world.ai.profiles import LLMProfile

        import json

        body = self._body(
            False,
            ChatRequestDescriptor(
                messages=({"role": "user", "content": "u"},)
            ),
        )
        profile = LLMProfile(**dict(default_profiles()["narrator"]))
        self.assertEqual(
            body,
            {
                "model": profile.model,
                "messages": [{"role": "user", "content": "u"}],
                "temperature": profile.temperature,
                "max_tokens": profile.max_tokens,
            },
        )
        # The wire is json.dumps(request_body) exactly as get_response
        # serializes it — pin the literal legacy payload bytes, not just the
        # dict shape, so key order/separators/encoding regressions surface.
        self.assertEqual(
            json.dumps(body),
            '{"model": "llama3.2", "messages": [{"role": "user", '
            '"content": "u"}], "temperature": 0.7, "max_tokens": 250}',
        )

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


def send_once(profile, descriptor=None):
    """Send one request through a capturing StubAgent; return the agent.

    Every wire-level assertion goes through the captured ``get_response``
    request — a builder helper that ``get_response`` forgot to call cannot
    pass these tests.
    """
    client = OpenAICompatClient(profile, reactor=Clock())
    client.agent = StubAgent(FakeResponse(200, envelope("ok")))
    d = client.get_response(
        descriptor
        or ChatRequestDescriptor(messages=({"role": "user", "content": "u"},))
    )
    assert not isinstance(await_result(d), Failure), "request must succeed"
    return client.agent


class WireBodyTests(unittest.TestCase):
    """Serialization of the composed body on the captured transport request."""

    @covers_requirement(
        "llm-client::openai-compatible-chat-completions-client",
        "llm-client::a-default-profile-produces-an-unchanged-wire-format",
    )
    def test_default_profile_body_and_headers_are_unchanged_on_the_wire(self):
        agent = send_once(wire_profile())
        _, kwargs = agent.calls[0]
        self.assertEqual(
            kwargs["bodyProducer"].body.decode("utf-8"),
            '{"model": "llama3.2", "messages": [{"role": "user", '
            '"content": "u"}], "temperature": 0.7, "max_tokens": 250}',
        )
        self.assertEqual(
            captured_headers(agent), {"content-type": ["application/json"]}
        )

    @covers_requirement("llm-client::openai-compatible-chat-completions-client")
    def test_configured_sampling_fields_pass_through_verbatim(self):
        agent = send_once(wire_profile(top_p=0.9, frequency_penalty=-1.0))
        body = captured_body(agent)
        self.assertEqual(body["top_p"], 0.9)
        self.assertEqual(body["frequency_penalty"], -1.0)
        for other in ("presence_penalty", "top_k", "repetition_penalty", "min_p", "top_a"):
            self.assertNotIn(other, body)

    @covers_requirement("llm-client::openai-compatible-chat-completions-client")
    def test_all_seven_sampling_fields_serialize_when_configured(self):
        agent = send_once(
            wire_profile(
                frequency_penalty=0.5,
                presence_penalty=-0.5,
                top_k=40,
                top_p=0.95,
                repetition_penalty=1.1,
                min_p=0.05,
                top_a=0.2,
            )
        )
        body = captured_body(agent)
        for field, value in (
            ("frequency_penalty", 0.5),
            ("presence_penalty", -0.5),
            ("top_k", 40),
            ("top_p", 0.95),
            ("repetition_penalty", 1.1),
            ("min_p", 0.05),
            ("top_a", 0.2),
        ):
            self.assertEqual(body[field], value)
        self.assertNotIn("max_completion_tokens", body)
        self.assertEqual(body["max_tokens"], 250)

    @covers_requirement("llm-client::openai-compatible-chat-completions-client")
    def test_max_completion_tokens_supersedes_max_tokens(self):
        agent = send_once(wire_profile(max_completion_tokens=400))
        body = captured_body(agent)
        self.assertEqual(body["max_completion_tokens"], 400)
        self.assertNotIn("max_tokens", body)

    @covers_requirement(
        "llm-client::openai-compatible-chat-completions-client",
        "llm-profiles::structured-output-is-opt-in-per-layer",
    )
    def test_response_format_gate_survives_on_the_wire(self):
        descriptor = ChatRequestDescriptor(
            messages=({"role": "user", "content": "u"},),
            output_schema={"type": "object"},
            schema_id="reward",
        )
        body = captured_body(send_once(wire_profile(supports_response_format=True), descriptor))
        self.assertEqual(body["response_format"]["type"], "json_schema")
        body = captured_body(send_once(wire_profile(), descriptor))
        self.assertNotIn("response_format", body)

    @covers_requirement("llm-client::openai-compatible-chat-completions-client")
    def test_openrouter_reasoning_case_table(self):
        cases = {
            "enabled-only": ({"reasoning_enabled": True}, {"reasoning": {"enabled": True}}),
            "effort-only": ({"reasoning_effort": "high"}, {"reasoning": {"effort": "high"}}),
            "both": (
                {"reasoning_enabled": False, "reasoning_effort": "low"},
                {"reasoning": {"enabled": False, "effort": "low"}},
            ),
            "unset": ({}, {}),
        }
        for label, (overrides, expected) in cases.items():
            with self.subTest(label):
                body = captured_body(send_once(wire_profile(**overrides)))
                if expected:
                    self.assertEqual(body["reasoning"], expected["reasoning"])
                else:
                    self.assertNotIn("reasoning", body)
                self.assertNotIn("chat_template_kwargs", body)
                self.assertNotIn("enable_thinking", body)

    @covers_requirement("llm-client::openai-compatible-chat-completions-client")
    def test_vllm_reasoning_case_table(self):
        cases = {
            "enabled-only": ({"reasoning_enabled": True}, {"enable_thinking": True}),
            "enabled-and-effort": (
                {"reasoning_enabled": True, "reasoning_effort": "high"},
                {"enable_thinking": True},
            ),
            "disabled": ({"reasoning_enabled": False}, {"enable_thinking": False}),
            "effort-only": ({"reasoning_effort": "high"}, None),
            "unset": ({}, None),
        }
        for label, (overrides, expected) in cases.items():
            with self.subTest(label):
                body = captured_body(
                    send_once(wire_profile(reasoning_style="vllm", **overrides))
                )
                if expected is None:
                    self.assertNotIn("chat_template_kwargs", body)
                else:
                    self.assertEqual(body["chat_template_kwargs"], expected)
                self.assertNotIn("reasoning", body)

    @covers_requirement("llm-client::openai-compatible-chat-completions-client")
    def test_off_style_and_unset_never_emit_reasoning(self):
        for style in ("openrouter", "vllm", "off"):
            with self.subTest(style):
                body = captured_body(
                    send_once(
                        wire_profile(
                            reasoning_style=style,
                            reasoning_enabled=True,
                            reasoning_effort="high",
                        )
                        if style == "off"
                        else wire_profile(reasoning_style=style)
                    )
                )
                self.assertNotIn("reasoning", body)
                self.assertNotIn("chat_template_kwargs", body)


class WireHeaderTests(unittest.TestCase):
    """Header composition observed on the captured transport request."""

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_configured_key_authenticates_the_request(self):
        headers = captured_headers(send_once(wire_profile(api_key="sk-or-test")))
        self.assertEqual(headers["authorization"], ["Bearer sk-or-test"])

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_empty_key_sends_no_authorization_header(self):
        headers = captured_headers(send_once(wire_profile()))
        self.assertNotIn("authorization", headers)

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_attribution_headers_appear_only_when_configured(self):
        headers = captured_headers(send_once(wire_profile(app_title="Elosern")))
        self.assertEqual(headers["x-title"], ["Elosern"])
        self.assertNotIn("http-referer", headers)
        headers = captured_headers(send_once(wire_profile(app_url="https://example.test")))
        self.assertEqual(headers["http-referer"], ["https://example.test"])
        self.assertNotIn("x-title", headers)

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_explicit_headers_win_over_derived_values(self):
        headers = captured_headers(
            send_once(
                wire_profile(
                    app_title="Elosern",
                    headers={"Content-Type": ("application/json",), "X-Title": ("Other",)},
                )
            )
        )
        self.assertEqual(headers["x-title"], ["Other"])

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_differently_cased_explicit_header_still_wins_on_the_wire(self):
        # Twisted's Headers normalizes names case-insensitively: an explicit
        # lowercase x-title replaces the derived X-Title, never doubling up.
        headers = captured_headers(
            send_once(
                wire_profile(
                    app_title="Elosern",
                    headers={"Content-Type": ("application/json",), "x-title": ("Other",)},
                )
            )
        )
        self.assertEqual(headers["x-title"], ["Other"])

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_default_profile_sends_exactly_the_frozen_mapping(self):
        agent = send_once(wire_profile())
        self.assertEqual(
            captured_headers(agent),
            {
                name.decode("utf-8").lower(): [v.decode("utf-8") for v in values]
                for name, values in Headers(
                    wire_profile().headers
                ).getAllRawHeaders()
            },
        )

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_authorization_is_never_double_emitted(self):
        headers = captured_headers(
            send_once(
                wire_profile(
                    api_key="sk-or-test",
                    headers={"Content-Type": ("application/json",)},
                )
            )
        )
        self.assertEqual(len(headers["authorization"]), 1)
        # Smuggling an Authorization through the profile mapping is impossible
        # by construction: the upstream deny-set rejects it at construction.
        with self.assertRaises(ProfileValidationError):
            wire_profile(headers={"Authorization": ("Bearer sk-smuggled",)})

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_a_transport_failure_never_surfaces_the_key(self):
        secret = "sk-secret-do-not-log"

        class HostileError(Exception):
            def __str__(self):
                return f"connection reset while sending Authorization: Bearer {secret}"

        profile = wire_profile(api_key=secret)
        outcomes = {
            "connection": HostileError(),
            "http": FakeResponse(401, b'{"error":"bad key"}'),
            "malformed": FakeResponse(200, b"not-json"),
            "timeout": defer.Deferred(),
        }
        for label, outcome in outcomes.items():
            with self.subTest(label):
                clock = Clock()
                client = OpenAICompatClient(profile, reactor=clock)
                client.agent = StubAgent(outcome)
                with patch("world.ai.client.log_warn") as logged:
                    d = client.get_response(
                        ChatRequestDescriptor(
                            messages=({"role": "user", "content": "u"},)
                        )
                    )
                    if label == "timeout":
                        clock.advance(profile.timeout_seconds + 1)
                    failure = await_result(d)
                    self.assertTrue(failure.check(LLMTransportError))
                    observable = " ".join(
                        [
                            str(failure.value),
                            repr(failure.value),
                            failure.getErrorMessage(),
                            *[
                                " ".join(
                                    str(arg)
                                    for arg in (*call.args, *call.kwargs.values())
                                )
                                for call in logged.call_args_list
                            ],
                        ]
                    )
                    self.assertNotIn(secret, observable)
                    if label == "connection":
                        self.assertIn("[redacted]", str(failure.value))

    @covers_requirement(
        "llm-client::request-headers-carry-authentication-and-attribution-without-leaking-the-key"
    )
    def test_hostile_invalid_envelope_cannot_echo_the_key_back(self):
        # A misbehaving endpoint may echo a request header (the bearer key)
        # inside a schema-invalid envelope; jsonschema quotes the offending
        # value, so the malformed error must be scrubbed too.
        secret = "sk-secret-do-not-log"
        hostile = json.dumps(
            {"choices": [{"message": {"content": [secret]}}]}
        ).encode()
        client = OpenAICompatClient(wire_profile(api_key=secret), reactor=Clock())
        client.agent = StubAgent(FakeResponse(200, hostile))
        with patch("world.ai.client.log_warn") as logged:
            d = client.get_response(
                ChatRequestDescriptor(messages=({"role": "user", "content": "u"},))
            )
            failure = await_result(d)
            self.assertTrue(failure.check(LLMTransportError))
            observable = " ".join(
                [
                    str(failure.value),
                    repr(failure.value),
                    failure.getErrorMessage(),
                    *[
                        " ".join(
                            str(arg) for arg in (*call.args, *call.kwargs.values())
                        )
                        for call in logged.call_args_list
                    ],
                ]
            )
            self.assertNotIn(secret, observable)
            self.assertIn("[redacted]", str(failure.value))


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
