"""Correlated transcript recording across the guardrail and the transport (gm-portal-s2a)."""

from base64 import b64encode
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from django.test import override_settings
from twisted.internet import defer
from twisted.internet.task import Clock
from twisted.python.failure import Failure

from tools.spec_traceability import covers_requirement
from world.ai import guardrail as guardrail_module
from world.ai.client import OpenAICompatClient
from world.ai.errors import LLMTransportError
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import CallIdTap, guarded_call
from world.ai.profiles import default_profiles, get_profile, profile_secrets
from world.ai.schemas import ChatRequestDescriptor
from world.observability import transcript

API_KEY = "sk-synthetic-key-0001"
HEADER_TOKEN = "proxy-token-0002"
PASSWORD = "pw:sec/ret"
BASE_URL = "http://alice:pw%3Asec%2Fret@llm.example.test:8080"
SCHEMA = {"type": "object", "required": ["ok"], "properties": {"ok": {"const": True}}}


def _raw(**narrator):
    raw = default_profiles()
    raw["narrator"].update(narrator)
    return raw


def _envelope(text, **extra):
    return json.dumps({"choices": [{"message": {"content": text}}], **extra}).encode()


class _Response:
    def __init__(self, code, body):
        self.code = code
        self.body = body

    def deliverBody(self, receiver):
        receiver.dataReceived(self.body)
        receiver.connectionLost()


class _SequenceAgent:
    """Replays one scripted outcome per request: a response, error, or Deferred."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)

    def request(self, *args, **kwargs):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            return defer.fail(Failure(outcome))
        if isinstance(outcome, defer.Deferred):
            return outcome
        return defer.succeed(outcome)


def _settle(d):
    """Synchronous result (or Failure) of an already-fired Deferred."""
    box = []
    d.addBoth(box.append)
    return box[0]


class _RecordingCase(unittest.TestCase):
    """Real transcript files in a temp directory, isolated guardrail hooks."""

    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for item in (
            patch.object(transcript, "_transcript_dir", return_value=str(self.root)),
            patch.object(transcript, "_today", return_value=date(2026, 10, 7)),
        ):
            item.start()
            self.addCleanup(item.stop)
        enabled = override_settings(LLM_TRANSCRIPT_ENABLED=True)
        enabled.enable()
        self.addCleanup(enabled.disable)
        saved_fallbacks = dict(guardrail_module._degrade_fallbacks)
        saved_validators = {k: dict(v) for k, v in guardrail_module._semantic_validators.items()}
        guardrail_module._degrade_fallbacks.clear()
        guardrail_module._semantic_validators.clear()
        guardrail_module._degrade_fallbacks["narrator"] = lambda: "FALLBACK"

        def restore():
            guardrail_module._degrade_fallbacks.clear()
            guardrail_module._degrade_fallbacks.update(saved_fallbacks)
            guardrail_module._semantic_validators.clear()
            guardrail_module._semantic_validators.update(saved_validators)

        self.addCleanup(restore)

    def records(self):
        path = self.root / "2026-10-07.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def raw_lines(self):
        path = self.root / "2026-10-07.jsonl"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def run_call(self, raw, agent, descriptor=None, wrap=lambda client: client):
        descriptor = descriptor or ChatRequestDescriptor(
            messages=({"role": "user", "content": "說一段旅人的見聞"},), output_schema=SCHEMA,
        )
        with override_settings(LLM_PROFILES=raw), \
                patch.object(guardrail_module, "log_info") as info, \
                patch.object(guardrail_module, "log_debug") as debug, \
                patch("world.ai.client.log_info") as client_info, \
                patch("world.ai.client.log_warn"):
            client = OpenAICompatClient(get_profile("narrator"), reactor=Clock())
            client.agent = agent
            result = _settle(guarded_call("narrator", wrap(client), descriptor))
        return result, info, debug, client_info


class CorrelationTests(_RecordingCase):
    @covers_requirement('llm-transcript::correlated-exchanges-and-terminal-outcomes')
    @covers_requirement('observability-logging::llm-and-narrative-diagnostic-correlation')
    def test_retry_then_degrade_shares_one_call_id_everywhere(self):
        bad = _Response(200, _envelope(json.dumps({"ok": False})))
        agent = _SequenceAgent(bad, _Response(200, _envelope(json.dumps({"ok": False}))))
        result, info, debug, _ = self.run_call(_raw(max_retries=1), agent)
        self.assertEqual(result, "FALLBACK")
        records = self.records()
        exchanges = [r for r in records if r["kind"] == "exchange"]
        outcomes = [r for r in records if r["kind"] == "outcome"]
        self.assertEqual([e["attempt"] for e in exchanges], [0, 1])
        self.assertEqual(len(outcomes), 1)
        call_id = outcomes[0]["call_id"]
        self.assertRegex(call_id, r"^[0-9a-f]{32}$")
        self.assertTrue(all(e["call_id"] == call_id for e in exchanges))
        llm_call = [c.kwargs["context"] for c in info.call_args_list if c.args[0] == "llm_call"]
        self.assertEqual([c["call_id"] for c in llm_call], [call_id])
        retries = [c.kwargs["context"] for c in debug.call_args_list if c.args[0] == "llm_call_retry"]
        self.assertEqual([c["call_id"] for c in retries], [call_id, call_id])
        outcome = outcomes[0]
        self.assertEqual((outcome["result"], outcome["reason"]), ("degraded", "invalid_output"))
        self.assertIsNone(outcome["final_text"])
        self.assertEqual([a["attempt"] for a in outcome["attempts"]], [0, 1])
        self.assertTrue(all(a["validation_errors"] for a in outcome["attempts"]))
        first = exchanges[0]
        self.assertEqual(first["layer"], "narrator")
        self.assertEqual(first["status"], 200)
        self.assertEqual(first["endpoint_host"], "127.0.0.1")
        self.assertEqual(first["request"]["messages"][0]["content"], "說一段旅人的見聞")
        self.assertIsNone(first["error"])
        self.assertIn("choices", first["response"])

    @covers_requirement('llm-transcript::correlated-exchanges-and-terminal-outcomes')
    def test_accepted_response_records_final_text(self):
        good = json.dumps({"ok": True})
        result, *_ = self.run_call(_raw(), _SequenceAgent(_Response(200, _envelope(good))))
        self.assertEqual(result, good)
        outcome = [r for r in self.records() if r["kind"] == "outcome"][0]
        self.assertEqual((outcome["result"], outcome["final_text"]), ("ok", good))
        self.assertEqual(outcome["attempts"], [{"attempt": 0, "validation_errors": []}])
        self.assertEqual(len([r for r in self.records() if r["kind"] == "exchange"]), 1)

    @covers_requirement('llm-transcript::correlated-exchanges-and-terminal-outcomes')
    def test_each_settled_failure_writes_exactly_one_exchange(self):
        cases = {
            "http": (_Response(503, b"overloaded"), 503, "overloaded"),
            "malformed": (_Response(200, b"<html>not json</html>"), 200, "<html>not json</html>"),
            "connection": (ConnectionRefusedError("refused"), None, None),
        }
        for kind, (outcome, status, response) in cases.items():
            with self.subTest(kind=kind):
                (self.root / "2026-10-07.jsonl").unlink(missing_ok=True)
                result, *_ = self.run_call(_raw(), _SequenceAgent(outcome))
                self.assertEqual(result, "FALLBACK")
                exchanges = [r for r in self.records() if r["kind"] == "exchange"]
                self.assertEqual(len(exchanges), 1)
                self.assertEqual(exchanges[0]["status"], status)
                self.assertEqual(exchanges[0]["response"], response)
                self.assertEqual(exchanges[0]["error"]["type"], kind)
                outcome_record = [r for r in self.records() if r["kind"] == "outcome"][0]
                self.assertEqual(outcome_record["reason"], "transport_error")

    def test_timeout_settles_one_exchange_without_a_status(self):
        clock = Clock()
        pending = defer.Deferred()
        with override_settings(LLM_PROFILES=_raw()), \
                patch("world.ai.client.log_warn"), patch.object(guardrail_module, "log_info"):
            client = OpenAICompatClient(get_profile("narrator"), reactor=clock)
            client.agent = _SequenceAgent(pending)
            d = guarded_call("narrator", client, ChatRequestDescriptor(
                messages=({"role": "user", "content": "x"},)))
            clock.advance(get_profile("narrator").timeout_seconds + 1)
            self.assertEqual(_settle(d), "FALLBACK")
        exchanges = [r for r in self.records() if r["kind"] == "exchange"]
        self.assertEqual(len(exchanges), 1)
        self.assertEqual((exchanges[0]["status"], exchanges[0]["error"]["type"]), (None, "timeout"))

    @covers_requirement('llm-transcript::correlated-exchanges-and-terminal-outcomes')
    def test_fake_client_and_disabled_profile_record_outcomes_only(self):
        fake = FakeLLMClient()
        fake.add_response(lambda d: True, "plain text")
        descriptor = ChatRequestDescriptor(messages=({"role": "user", "content": "x"},))
        with override_settings(LLM_PROFILES=_raw()), patch.object(guardrail_module, "log_info"):
            self.assertEqual(_settle(guarded_call("narrator", fake, descriptor)), "plain text")
        self.assertEqual(fake.calls[0].attempt, 0)
        self.assertEqual(fake.calls[0].layer, "narrator")
        with override_settings(LLM_PROFILES=_raw(enabled=False)), patch.object(guardrail_module, "log_info"):
            self.assertEqual(_settle(guarded_call("narrator", fake, descriptor)), "FALLBACK")
        records = self.records()
        self.assertEqual([r["kind"] for r in records], ["outcome", "outcome"])
        self.assertEqual(records[1]["reason"], "profile_disabled")
        self.assertEqual(records[1]["attempts"], [])

    @covers_requirement('llm-transcript::correlated-exchanges-and-terminal-outcomes')
    def test_raising_fallback_records_one_rejected_outcome_and_reraises(self):
        def broken():
            raise RuntimeError("fallback exploded")

        guardrail_module._degrade_fallbacks["narrator"] = broken
        descriptor = ChatRequestDescriptor(messages=({"role": "user", "content": "x"},))
        with override_settings(LLM_PROFILES=_raw(enabled=False)), patch.object(guardrail_module, "log_info"):
            failure = _settle(guarded_call("narrator", FakeLLMClient(), descriptor))
        self.assertIsInstance(failure, Failure)
        self.assertEqual(str(failure.value), "fallback exploded")
        failure.trap(RuntimeError)
        outcomes = self.records()
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["result"], "rejected")
        self.assertEqual(outcomes[0]["reason"], "unexpected_error:RuntimeError")

    @covers_requirement('observability-logging::llm-and-narrative-diagnostic-correlation')
    def test_cached_token_report_carries_the_call_id(self):
        body = _envelope(json.dumps({"ok": True}), usage={"prompt_tokens_details": {"cached_tokens": 12}})
        _, _, _, client_info = self.run_call(_raw(), _SequenceAgent(_Response(200, body)))
        cached = [c.kwargs["context"] for c in client_info.call_args_list
                  if c.args[0] == "llm_cached_tokens_reported"]
        outcome = [r for r in self.records() if r["kind"] == "outcome"][0]
        self.assertEqual(cached[0]["call_id"], outcome["call_id"])


class CallIdTapTests(_RecordingCase):
    def test_tap_names_the_actual_call_and_stays_none_without_one(self):
        tap = CallIdTap(FakeLLMClient())
        self.assertIsNone(tap.latest)
        descriptor = ChatRequestDescriptor(messages=({"role": "user", "content": "x"},))
        with override_settings(LLM_PROFILES=_raw(enabled=False)), patch.object(guardrail_module, "log_info"):
            _settle(guarded_call("narrator", tap, descriptor))
        self.assertEqual(tap.latest, self.records()[0]["call_id"])

    def test_tap_must_be_outermost_to_observe_the_call(self):
        class Forwarding:
            def __init__(self, inner):
                self.inner = inner

            def get_response(self, descriptor):
                return self.inner.get_response(descriptor)

        fake = FakeLLMClient()
        fake.add_response(lambda d: True, "text")
        tap = CallIdTap(fake)
        descriptor = ChatRequestDescriptor(messages=({"role": "user", "content": "x"},))
        with override_settings(LLM_PROFILES=_raw()), patch.object(guardrail_module, "log_info"):
            _settle(guarded_call("narrator", Forwarding(tap), descriptor))
        self.assertIsNone(tap.latest)


class CredentialExclusionTests(_RecordingCase):
    def credentialed(self, **extra):
        return _raw(base_url=BASE_URL, api_key=API_KEY,
                    headers={"Content-Type": ["application/json"], "X-Proxy-Token": [HEADER_TOKEN]},
                    **extra)

    def assert_no_credentials(self, *texts):
        basic = b64encode(f"alice:{PASSWORD}".encode()).decode()
        for text in texts:
            for secret in (API_KEY, HEADER_TOKEN, PASSWORD, "pw%3Asec%2Fret", basic):
                self.assertNotIn(secret, text)

    def test_profile_secrets_cover_key_headers_and_userinfo_forms(self):
        with override_settings(LLM_PROFILES=self.credentialed()):
            secrets = profile_secrets(get_profile("narrator"))
        self.assertIn(API_KEY, secrets)
        self.assertIn(HEADER_TOKEN, secrets)
        self.assertIn(PASSWORD, secrets)
        self.assertIn("pw%3Asec%2Fret", secrets)
        self.assertNotIn("application/json", secrets)
        self.assertNotIn("alice", secrets)

    @covers_requirement('llm-transcript::credential-exclusion-without-prose-redaction')
    def test_failing_request_with_credential_echo_leaks_nothing(self):
        error = ConnectionRefusedError(f"refused Bearer {API_KEY} via {BASE_URL} {HEADER_TOKEN}")
        with patch("world.ai.client.log_warn") as warn, \
                override_settings(LLM_PROFILES=self.credentialed()), \
                patch.object(guardrail_module, "log_info") as info:
            client = OpenAICompatClient(get_profile("narrator"), reactor=Clock())
            client.agent = _SequenceAgent(error)
            self.assertEqual(_settle(guarded_call("narrator", client, ChatRequestDescriptor(
                messages=({"role": "user", "content": "旅人的祕密心事"},)))), "FALLBACK")
        from world.observability.render import format_exception_chain
        rendered = [repr(c) + format_exception_chain(c.kwargs["exc"])
                    for c in warn.call_args_list if c.kwargs.get("exc") is not None]
        self.assert_no_credentials(self.raw_lines(), repr(info.call_args_list), *rendered)
        self.assertIn("旅人的祕密心事", self.raw_lines())
        self.assertNotIn("Authorization", self.raw_lines())
        self.assertEqual(self.records()[0]["endpoint_host"], "llm.example.test")

    @covers_requirement('llm-transcript::credential-exclusion-without-prose-redaction')
    def test_echoed_credentials_in_success_and_raw_bodies_are_scrubbed(self):
        echo = f"echo {API_KEY} {HEADER_TOKEN} {PASSWORD} 溫柔的回答"
        json_body = _envelope(echo, headers={"Authorization": f"Bearer {API_KEY}"})
        result, *_ = self.run_call(
            self.credentialed(), _SequenceAgent(_Response(200, json_body)),
            descriptor=ChatRequestDescriptor(messages=({"role": "user", "content": "x"},)),
        )
        self.assertEqual(result, echo)
        (self.root / "2026-10-07.jsonl").unlink()
        raw_body = f"<pre>{API_KEY} {PASSWORD}</pre>".encode()
        self.run_call(self.credentialed(), _SequenceAgent(_Response(200, raw_body)),
                      descriptor=ChatRequestDescriptor(messages=({"role": "user", "content": "x"},)))
        text = self.raw_lines()
        self.assert_no_credentials(text)
        self.assertIn("[redacted]", text)

    def test_validation_errors_quoting_an_echoed_key_are_scrubbed(self):
        echoed = json.dumps({"ok": API_KEY})
        quoting = ChatRequestDescriptor(
            messages=({"role": "user", "content": "x"},),
            output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        )
        self.run_call(self.credentialed(max_retries=0),
                      _SequenceAgent(_Response(200, _envelope(echoed))), descriptor=quoting)
        outcome = [r for r in self.records() if r["kind"] == "outcome"][0]
        errors = outcome["attempts"][0]["validation_errors"]
        self.assertTrue(errors)
        self.assertIn("[redacted]", " ".join(errors))
        self.assert_no_credentials(self.raw_lines())

    def test_short_values_are_not_treated_as_secrets(self):
        self.assertEqual(transcript.redact("v2 and abc stay", ("v2", "abc")), "v2 and abc stay")
        with override_settings(LLM_PROFILES=_raw(headers={"X-Api-Version": ["v2"]})):
            self.assertNotIn("v2", profile_secrets(get_profile("narrator")))

    @covers_requirement('llm-transcript::credential-exclusion-without-prose-redaction')
    def test_success_outcome_final_text_is_scrubbed_but_keeps_prose(self):
        echo = f"echo {API_KEY} 溫柔的回答"
        self.run_call(
            self.credentialed(), _SequenceAgent(_Response(200, _envelope(echo))),
            descriptor=ChatRequestDescriptor(messages=({"role": "user", "content": "x"},)),
        )
        outcome = [r for r in self.records() if r["kind"] == "outcome"][0]
        self.assertEqual(outcome["final_text"], "echo [redacted] 溫柔的回答")
