"""Observability boundary events for the AI layer (llm-client delta).

Asserts the exactly-one ``llm_call`` funnel (ok/degraded/rejected), the
client-layer ``llm_transport_error`` chain, and the fail-closed credential
rule for unexpected client errors. All deterministic and socket-free.
"""

from dataclasses import replace
from unittest.mock import patch
import json
import unittest

from django.test import override_settings
from twisted.python.failure import Failure

from evennia.utils.test_resources import EvenniaTestCase

from world.ai.client import OpenAICompatClient
from world.ai.errors import LLMTransportError
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import guarded_call, register_degrade_fallback
from world.ai.profiles import default_profiles, get_profile
from world.ai.schemas import ChatRequestDescriptor

_SCHEMA = {"type": "object"}


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _descriptor():
    return ChatRequestDescriptor(
        messages=({"role": "user", "content": "x"},),
        output_schema=_SCHEMA,
    )


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


class LlmCallEventTests(EvenniaTestCase):
    """Exactly one ``llm_call`` event per guarded call, with its outcome."""

    def setUp(self):
        import world.ai.guardrail as guardrail_module

        guardrail_module._degrade_fallbacks.clear()
        guardrail_module._semantic_validators.clear()
        register_degrade_fallback("narrator", lambda: "degraded-narrator")
        self.addCleanup(guardrail_module._degrade_fallbacks.clear)
        self.addCleanup(guardrail_module._semantic_validators.clear)

    def _events(self, mock):
        return [call for call in mock.call_args_list if call.args and call.args[0] == "llm_call"]

    def test_successful_call_emits_exactly_one_ok_event(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, json.dumps({"ok": True}))
        with override_settings(LLM_PROFILES=_raw()):
            with patch("world.ai.guardrail.log_info") as info:
                d = guarded_call("narrator", client, _descriptor())
                result = await_result(d)
        self.assertEqual(result, json.dumps({"ok": True}))
        events = self._events(info)
        self.assertEqual(len(events), 1, events)
        context = events[0].kwargs["context"]
        self.assertEqual(context["layer"], "narrator")
        self.assertEqual(context["result"], "ok")
        self.assertIsInstance(context["ms"], int)
        self.assertNotIn("reason", context)

    def test_retry_then_ok_still_emits_exactly_one_event(self):
        client = FakeLLMClient()
        # First attempt (one message) returns schema-invalid but parseable
        # JSON; the retry (which carries the appended validation-error
        # message) returns valid JSON.
        client.add_response(lambda d: len(d.messages) == 1, "[1]")
        client.add_response(lambda d: len(d.messages) > 1, json.dumps({"ok": True}))
        with override_settings(LLM_PROFILES=_raw()):
            with patch("world.ai.guardrail.log_info") as info:
                d = guarded_call("narrator", client, _descriptor())
                result = await_result(d)
        self.assertEqual(result, json.dumps({"ok": True}))
        self.assertEqual(len(client.calls), 2)
        events = self._events(info)
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0].kwargs["context"]["result"], "ok")

    def test_transport_degrade_emits_exactly_one_degraded_event(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            with patch("world.ai.guardrail.log_info") as info:
                d = guarded_call("narrator", client, _descriptor())
                result = await_result(d)
        self.assertEqual(result, "degraded-narrator")
        events = self._events(info)
        self.assertEqual(len(events), 1, events)
        context = events[0].kwargs["context"]
        self.assertEqual(context["result"], "degraded")
        self.assertEqual(context["reason"], "transport_error")

    def test_disabled_profile_degrades_with_named_reason(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(narrator={"enabled": False})):
            with patch("world.ai.guardrail.log_info") as info:
                d = guarded_call("narrator", client, _descriptor())
                result = await_result(d)
        self.assertEqual(result, "degraded-narrator")
        self.assertEqual(client.calls, [])
        events = self._events(info)
        self.assertEqual(len(events), 1, events)
        context = events[0].kwargs["context"]
        self.assertEqual(context["result"], "degraded")
        self.assertEqual(context["reason"], "profile_disabled")

    def test_invalid_output_budget_exhaustion_degrades(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "[]")
        with override_settings(LLM_PROFILES=_raw(narrator={"max_retries": 1})):
            with patch("world.ai.guardrail.log_info") as info:
                d = guarded_call("narrator", client, _descriptor())
                result = await_result(d)
        self.assertEqual(result, "degraded-narrator")
        events = self._events(info)
        self.assertEqual(len(events), 1, events)
        context = events[0].kwargs["context"]
        self.assertEqual(context["result"], "degraded")
        self.assertEqual(context["reason"], "invalid_output")

    def test_raising_fallback_emits_exactly_one_rejected_not_degraded(self):
        # Exactly-one invariant: the degraded event is written only after the
        # fallback returned, so a fallback that raises yields ONE rejected
        # event and the original error propagates (rubber-duck P3 BLOCKER).
        import world.ai.guardrail as guardrail_module

        class _FallbackBroken(Exception):
            pass

        def _broken_fallback():
            raise _FallbackBroken("fallback exploded")

        # setUp registered a working narrator fallback; override the binding
        # directly (register_degrade_fallback refuses double registration).
        guardrail_module._degrade_fallbacks["narrator"] = _broken_fallback
        self.addCleanup(
            guardrail_module._degrade_fallbacks.clear
        )
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(narrator={"enabled": False})):
            with patch("world.ai.guardrail.log_info") as info:
                d = guarded_call("narrator", client, _descriptor())
                result = await_result(d)
        self.assertTrue(result.check(_FallbackBroken), result)
        events = self._events(info)
        self.assertEqual(len(events), 1, events)
        context = events[0].kwargs["context"]
        self.assertEqual(context["result"], "rejected")

    def test_unexpected_client_error_emits_one_rejected_and_reraises(self):
        class _Boom(Exception):
            pass

        class BoomClient:
            def get_response(self, descriptor):
                from twisted.internet import defer
                from twisted.internet.task import Clock

                return defer.fail(Failure(_Boom("boom")))

        with override_settings(LLM_PROFILES=_raw()):
            with patch("world.ai.guardrail.log_info") as info:
                d = guarded_call("narrator", BoomClient(), _descriptor())
                result = await_result(d)
        self.assertTrue(result.check(_Boom), result)
        events = self._events(info)
        self.assertEqual(len(events), 1, events)
        context = events[0].kwargs["context"]
        self.assertEqual(context["result"], "rejected")
        self.assertTrue(context["reason"].startswith("unexpected_error"))

    def test_validator_exception_emits_one_rejected_and_reraises(self):
        from world.ai.guardrail import register_semantic_validator

        def _boom(parsed):
            raise RuntimeError("validator exploded")

        register_semantic_validator("narrator", "boom", _boom)
        client = FakeLLMClient()
        client.add_response(lambda d: True, json.dumps({"ok": True}))
        with override_settings(LLM_PROFILES=_raw()):
            with patch("world.ai.guardrail.log_info") as info:
                d = guarded_call("narrator", client, _descriptor())
                result = await_result(d)
        self.assertTrue(result.check(RuntimeError), result)
        events = self._events(info)
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0].kwargs["context"]["result"], "rejected")


class TransportErrorEventTests(EvenniaTestCase):
    """The client errback emits the spec'd transport diagnostic."""

    def _client(self):
        return OpenAICompatClient(get_profile("narrator"), reactor=None)

    def test_transport_failure_event_carries_endpoint_and_chain(self):
        client = self._client()
        error = LLMTransportError("connection", "request failed: refused")
        with patch("world.ai.client.log_warn") as warn:
            returned = client._safe_log_error(Failure(error))
        self.assertIs(returned.value, error)
        warn.assert_called_once()
        call = warn.call_args
        self.assertEqual(call.args[0], "llm_transport_error")
        context = call.kwargs["context"]
        profile = client.profile
        self.assertEqual(
            context["endpoint"], profile.base_url.rstrip("/") + profile.path
        )
        self.assertEqual(context["kind"], "connection")
        self.assertIs(call.kwargs["exc"], error)

    def test_unexpected_failure_stays_fail_closed_without_chain(self):
        client = self._client()
        error = ValueError("possibly endpoint-controlled text")
        with patch("world.ai.client.log_warn") as warn:
            client._safe_log_error(Failure(error))
        call = warn.call_args
        self.assertEqual(call.args[0], "llm_client_unexpected_error")
        self.assertEqual(
            call.kwargs["context"], {"kind": "unexpected", "exc_type": "ValueError"}
        )
        self.assertNotIn("exc", call.kwargs)

    def test_a_key_smuggled_into_the_chain_never_reaches_the_rendered_line(self):
        # Fail-closed api-key invariant: the facade renders every chain link,
        # and a hostile endpoint can echo the bearer key inside a chained
        # exception. The emitted chain must be scrubbed link-by-link.
        from world.observability.render import format_exception_chain

        secret = "sk-chain-do-not-log"
        fields = {"api_" + "key": secret}
        client = OpenAICompatClient(
            replace(get_profile("narrator"), **fields), reactor=None
        )
        hostile = HostileEchoError(f"endpoint echoed Authorization: Bearer {secret}")
        try:
            try:
                raise hostile
            except HostileEchoError as inner:
                raise LLMTransportError("malformed", "response body is not valid JSON") from inner
        except LLMTransportError as error:
            with patch("world.ai.client.log_warn") as warn:
                client._safe_log_error(Failure(error))
        call = warn.call_args
        self.assertEqual(call.args[0], "llm_transport_error")
        rendered = format_exception_chain(call.kwargs["exc"])
        self.assertNotIn(secret, rendered)
        self.assertIn("[redacted]", rendered)
        # The outermost link keeps its kind for the context field.
        self.assertEqual(call.kwargs["context"]["kind"], "malformed")


class HostileEchoError(Exception):
    """A transport exception whose text carries an endpoint-echoed credential."""


if __name__ == "__main__":
    unittest.main()
