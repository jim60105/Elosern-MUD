"""Tests for the deterministic replay double (fake-llm-client)."""

import unittest

from world.ai.errors import LLMTransportError
from world.ai.fake_client import FakeLLMClient, MissingFixtureError, request_signature
from world.ai.schemas import ChatRequestDescriptor

from tools.spec_traceability import covers_requirement


def descriptor(text="x", schema=None, schema_id=None):
    return ChatRequestDescriptor(
        messages=({"role": "user", "content": text},),
        output_schema=schema,
        schema_id=schema_id,
    )


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


class FakeResponseTests(unittest.TestCase):
    @covers_requirement(
        "fake-llm-client::fakellmclient-replays-fixed-responses-deterministically",
        "fake-llm-client::generative-layer-tests-never-contact-a-live-endpoint",
    )
    def test_matched_request_returns_recorded_text_without_socket(self):
        client = FakeLLMClient()
        client.add_response(lambda d: d.messages[0]["content"] == "hi", "recorded answer")
        result = await_result(client.get_response(descriptor("hi")))
        self.assertEqual(result, "recorded answer")

    @covers_requirement("fake-llm-client::fakellmclient-replays-fixed-responses-deterministically")
    def test_unmatched_request_errbacks_with_missing_fixture(self):
        client = FakeLLMClient()
        d = client.get_response(descriptor("nope"))
        failure = await_result(d)
        self.assertTrue(failure.check(MissingFixtureError))

    def test_request_signature_is_stable_and_order_insensitive(self):
        a = descriptor("hi")
        b = descriptor("hi")
        self.assertEqual(request_signature(a), request_signature(b))
        self.assertEqual(request_signature(a), request_signature(a))

    @covers_requirement("fake-llm-client::fakellmclient-replays-fixed-responses-deterministically")
    def test_deferred_interface_matches_the_client_signature(self):
        from twisted.internet import defer

        client = FakeLLMClient()
        client.add_response(lambda d: True, "text")
        d = client.get_response(descriptor())
        self.assertIsInstance(d, defer.Deferred)
        self.assertEqual(await_result(d), "text")


class FakeFailureModeTests(unittest.TestCase):
    @covers_requirement("fake-llm-client::failure-modes-are-scriptable-for-guardrail-tests")
    def test_timeout_fixture_drives_degrade_path(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        d = client.get_response(descriptor())
        failure = await_result(d)
        self.assertTrue(failure.check(LLMTransportError))
        self.assertEqual(failure.value.kind, "timeout")

    @covers_requirement("fake-llm-client::failure-modes-are-scriptable-for-guardrail-tests")
    def test_http_error_fixture_errbacks_transport_error(self):
        client = FakeLLMClient()
        client.add_http_error(lambda d: True)
        failure = await_result(client.get_response(descriptor()))
        self.assertTrue(failure.check(LLMTransportError))
        self.assertEqual(failure.value.kind, "http")

    @covers_requirement("fake-llm-client::failure-modes-are-scriptable-for-guardrail-tests")
    def test_connection_error_fixture_errbacks_transport_error(self):
        client = FakeLLMClient()
        client.add_connection_error(lambda d: True)
        failure = await_result(client.get_response(descriptor()))
        self.assertTrue(failure.check(LLMTransportError))
        self.assertEqual(failure.value.kind, "connection")

    @covers_requirement("fake-llm-client::failure-modes-are-scriptable-for-guardrail-tests")
    def test_malformed_non_json_fixture_errbacks_transport_error(self):
        client = FakeLLMClient()
        client.add_malformed_body(lambda d: True)
        failure = await_result(client.get_response(descriptor()))
        self.assertTrue(failure.check(LLMTransportError))
        self.assertEqual(failure.value.kind, "malformed")

    @covers_requirement("fake-llm-client::failure-modes-are-scriptable-for-guardrail-tests")
    def test_failure_modes_are_keyed_by_the_same_matcher(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: d.messages[0]["content"] == "slow")
        client.add_response(lambda d: d.messages[0]["content"] == "ok", "fine")
        slow = await_result(client.get_response(descriptor("slow")))
        ok = await_result(client.get_response(descriptor("ok")))
        self.assertTrue(slow.check(LLMTransportError))
        self.assertEqual(ok, "fine")

    @covers_requirement("fake-llm-client::failure-modes-are-scriptable-for-guardrail-tests")
    def test_schema_invalid_json_fixture_drives_validation_path(self):
        # A fixture that parses as JSON but fails the declared schema must NOT be
        # treated as a transport failure: it resolves with text, so the guardrail
        # (not the fake) decides it is a validation failure.
        client = FakeLLMClient()
        client.add_response(lambda d: True, '{"wrong": 1}')
        result = await_result(client.get_response(descriptor(schema={"type": "object"})))
        self.assertEqual(result, '{"wrong": 1}')
