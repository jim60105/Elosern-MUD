"""Tests for the epithet-nomination generative layer (title-system D4, change G).

Covers the closed 5-candidate output contract (happy path, count rejects,
malformed JSON, overlong basis/display whole-round voids), the deterministic
collision filter matrix (form, fixed-registry collision, live-collection
collision, deleted-name renomination, in-batch duplicates, top-three cuts),
degrade semantics (disabled profile / transport failure resolve to ``None``
without a ballot), prompt-shape rules (collision vocabulary never appears in
the prompt text), and registration semantics. Pure ``unittest`` — no database,
no network, no live LLM: the client is always ``FakeLLMClient``.
"""

import json
import unittest
from types import SimpleNamespace

from django.test import override_settings

from world.ai import guardrail
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.ai.title_nomination import (
    BALLOT_TOP,
    BASIS_MAX_CHARS,
    CANDIDATES_PER_ROUND,
    DISPLAY_WIRE_MAX_CHARS,
    SUMMARY_MAX_TOTAL_CHARS,
    EpithetCandidate,
    NominationContext,
    TITLE_NOMINATION_OUTPUT_SCHEMA,
    TitleNominationClientRequiredError,
    build_nomination_prompt,
    display_form_valid,
    filter_candidates,
    generate_epithet_candidates,
    register_title_nomination,
    summarize_event_logs,
)


def _profiles(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _reset_all():
    guardrail._semantic_validators.clear()
    guardrail._degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


PLAYER = "艾洛希雅"
FIXED = frozenset({"F級冒險者", "受矚者"})
OWNED = frozenset({"南門新客"})


def _context(**overrides):
    base = {
        "player_name": PLAYER,
        "full_title": "F級冒險者　南門新客",
        "declined": (),
        "owned_epithet_displays": OWNED,
        "fixed_displays": FIXED,
        "event_logs": (),
    }
    base.update(overrides)
    return NominationContext(**base)


def _candidate(index: int, display: str | None = None, basis: str | None = None):
    # Displays default to pure-CJK names (the display form gate rejects
    # digits); basis carries no form gate at all — schema + storage parse
    # (non-empty, <=80) are its only bounds, per the spec filter list.
    numeral = "一二三四五六七八九十"[index - 1]
    return {
        "display": display if display is not None else f"異名{numeral}",
        "basis": basis if basis is not None else f"事蹟引用{index}",
    }


def _reply(candidates):
    return json.dumps({"candidates": list(candidates)}, ensure_ascii=False)


def _good_reply():
    return _reply(
        [
            _candidate(1, "火焰之心"),
            _candidate(2, "破曉之刃"),
            _candidate(3, "沉默守望"),
            _candidate(4, "荒野行者"),
            _candidate(5, "月影之舞"),
        ]
    )


def _client_replying(text):
    client = FakeLLMClient()
    client.add_response(lambda descriptor: True, text)
    return client


class FilterMatrixTests(unittest.TestCase):
    """The deterministic collision filters, in fixed order, first-survivor."""

    def _filter(self, candidates, **over):
        kwargs = {
            "player_name": PLAYER,
            "fixed_displays": FIXED,
            "owned_epithet_displays": OWNED,
        }
        kwargs.update(over)
        return filter_candidates(candidates, **kwargs)

    def test_form_gate_accepts_pure_cjk_2_to_8(self):
        self.assertTrue(display_form_valid("火焰之心", PLAYER))
        self.assertTrue(display_form_valid("火心", PLAYER))
        self.assertTrue(display_form_valid("一二三四五六七八", PLAYER))

    def test_form_gate_rejects_bad_shape(self):
        for bad in (
            "火",                   # too short
            "一二三四五六七八九",   # 9 characters
            "火 心",                # whitespace
            "火　心",               # full-width space
            "Hero",                 # no CJK at all
            "火Rune",               # mixed non-CJK
            "，異名",               # punctuation is not a CJK ideograph
            "",
            None,
            12,
        ):
            with self.subTest(display=bad):
                self.assertFalse(display_form_valid(bad, PLAYER))

    def test_player_name_substring_rejected(self):
        self.assertFalse(display_form_valid("艾洛希雅之友", PLAYER))
        self.assertFalse(display_form_valid("小艾洛希雅", PLAYER))

    def test_fixed_registry_collision_rejected(self):
        survivors = self._filter([_candidate(1, "F級冒險者"), _candidate(2, "新月")])
        self.assertEqual([c.display for c in survivors], ["新月"])

    def test_live_collection_collision_rejected(self):
        survivors = self._filter([_candidate(1, "南門新客"), _candidate(2, "新月")])
        self.assertEqual([c.display for c in survivors], ["新月"])

    def test_deleted_name_is_renominable(self):
        # The collection is read live: a deleted epithet is simply absent
        # from owned_epithet_displays, so the same name survives again.
        survivors = self._filter(
            [_candidate(1, "南門新客")], owned_epithet_displays=frozenset()
        )
        self.assertEqual([c.display for c in survivors], ["南門新客"])

    def test_in_batch_duplicates_keep_first(self):
        survivors = self._filter(
            [
                _candidate(1, "新月", basis="第一段事蹟"),
                _candidate(2, "新月", basis="重複段"),
                _candidate(3, "流星"),
            ]
        )
        self.assertEqual(
            [(c.display, c.basis) for c in survivors],
            [("新月", "第一段事蹟"), ("流星", "事蹟引用3")],
        )

    def test_top_three_cut(self):
        survivors = self._filter([_candidate(i) for i in range(1, 6)])
        self.assertEqual(len(survivors), BALLOT_TOP)
        self.assertEqual(
            [c.display for c in survivors], ["異名一", "異名二", "異名三"]
        )

    def test_survivor_counts_2_1_0(self):
        two = self._filter(
            [
                _candidate(1),
                _candidate(2),
                _candidate(3, "F級冒險者"),
                _candidate(4, "火"),
            ]
        )
        self.assertEqual(len(two), 2)
        one = self._filter([_candidate(1, "新月"), _candidate(2, "新月")])
        self.assertEqual([c.display for c in one], ["新月"])
        zero = self._filter([_candidate(i, "南門新客") for i in range(1, 6)])
        self.assertEqual(zero, ())

    def test_basis_has_no_form_gate(self):
        # The spec's per-candidate filter list gates the DISPLAY form only;
        # the basis's bounds are the schema (string, <=80) and the storage
        # parse (non-empty). A Latin or digit-only basis survives.
        survivors = self._filter(
            [
                _candidate(1, "新月", basis="Victory at Dawn"),
                _candidate(2, "流星", basis="123"),
                _candidate(3, "白虹", basis="  "),
                _candidate(4, "長夜", basis=""),
                _candidate(5, "斷罪", basis=None),
            ]
        )
        self.assertEqual(
            [(c.display, c.basis) for c in survivors],
            [("新月", "Victory at Dawn"), ("流星", "123"), ("白虹", "  ")],
        )


class SchemaBoundaryTests(unittest.TestCase):
    """The closed schema: exactly five, wire bounds, whole-round voids."""

    def setUp(self):
        _reset_all()
        register_title_nomination()
        self.addCleanup(_reset_all)

    def test_five_good_candidates_return_top_three(self):
        client = _client_replying(_good_reply())
        with override_settings(LLM_PROFILES=_profiles()):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertEqual(
            result,
            (
                EpithetCandidate("火焰之心", "事蹟引用1"),
                EpithetCandidate("破曉之刃", "事蹟引用2"),
                EpithetCandidate("沉默守望", "事蹟引用3"),
            ),
        )
        self.assertEqual(len(client.calls), 1)

    def test_wrong_count_voids_round(self):
        for count in (CANDIDATES_PER_ROUND - 1, CANDIDATES_PER_ROUND + 1):
            with self.subTest(count=count):
                text = _reply([_candidate(i) for i in range(1, count + 1)])
                client = _client_replying(text)
                with override_settings(
                    LLM_PROFILES=_profiles(title_nomination={"max_retries": 0})
                ):
                    result = await_result(
                        generate_epithet_candidates(_context(), client)
                    )
                self.assertIsNone(result)

    def test_malformed_json_voids_round(self):
        client = _client_replying("{not json")
        with override_settings(LLM_PROFILES=_profiles()):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertIsNone(result)

    def test_basis_over_80_voids_whole_round(self):
        long_basis = "事" * (BASIS_MAX_CHARS + 1)
        text = _reply(
            [
                _candidate(1, "火焰之心", long_basis),
                _candidate(2),
                _candidate(3),
                _candidate(4),
                _candidate(5),
            ]
        )
        client = _client_replying(text)
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"max_retries": 0})
        ):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertIsNone(result)

    def test_basis_exactly_80_survives(self):
        basis = "事" * BASIS_MAX_CHARS
        text = _reply(
            [
                _candidate(1, "火焰之心", basis),
                _candidate(2),
                _candidate(3),
                _candidate(4),
                _candidate(5),
            ]
        )
        client = _client_replying(text)
        with override_settings(LLM_PROFILES=_profiles()):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertEqual(result[0].basis, basis)

    def test_display_over_wire_bound_voids_round(self):
        text = _reply(
            [
                _candidate(1, "火" * (DISPLAY_WIRE_MAX_CHARS + 1)),
                _candidate(2),
                _candidate(3),
                _candidate(4),
                _candidate(5),
            ]
        )
        client = _client_replying(text)
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"max_retries": 0})
        ):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertIsNone(result)

    def test_extra_fields_void_round(self):
        candidates = [
            {**_candidate(i, f"異名{i}"), "extra": 1}
            for i in range(1, CANDIDATES_PER_ROUND + 1)
        ]
        client = _client_replying(_reply(candidates))
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"max_retries": 0})
        ):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertIsNone(result)


class DegradeTests(unittest.TestCase):
    """Offline, disabled, and transport failures never produce a ballot."""

    def setUp(self):
        _reset_all()
        register_title_nomination()
        self.addCleanup(_reset_all)

    def test_disabled_profile_never_touches_transport(self):
        client = _client_replying(_good_reply())
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"enabled": False})
        ):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertIsNone(result)
        self.assertEqual(client.calls, [])

    def test_timeout_resolves_none(self):
        client = FakeLLMClient()
        client.add_timeout(lambda descriptor: True)
        with override_settings(LLM_PROFILES=_profiles()):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertIsNone(result)

    def test_all_candidates_filtered_returns_empty_tuple_not_none(self):
        text = _reply([_candidate(i, "南門新客") for i in range(1, 6)])
        client = _client_replying(text)
        with override_settings(LLM_PROFILES=_profiles()):
            result = await_result(generate_epithet_candidates(_context(), client))
        self.assertEqual(result, ())

    def test_explicit_none_client_rejected_before_transport(self):
        with override_settings(LLM_PROFILES=_profiles()):
            failure = await_result(generate_epithet_candidates(_context(), None))
        self.assertTrue(failure.check(TitleNominationClientRequiredError))


class PromptShapeTests(unittest.TestCase):
    """Collision vocabulary is absent from the prompt; digest is present."""

    def test_prompt_carries_context_and_empty_summary(self):
        system, user = build_nomination_prompt(
            _context(declined=("舊異名", "另一個名"))
        )
        self.assertIn("5", system["content"])
        self.assertIn(PLAYER, user["content"])
        self.assertIn("舊異名、另一個名", user["content"])
        summary_line = user["content"].split(
            "近期事件紀錄（JSON；可能為空）：", 1
        )[1].split("\n", 1)[0]
        self.assertEqual(json.loads(summary_line), {"event_logs": []})

    def test_prompt_never_states_collision_rules(self):
        system, user = build_nomination_prompt(_context())
        # The prompt may state form rules only; the collision rules
        # (registry/collection matching, duplicate handling) are code-only.
        for token in ("稱號冊", "收藏", "重複", "registry", "FIXED_TITLE"):
            with self.subTest(token=token):
                self.assertNotIn(token, system["content"])
                self.assertNotIn(token, user["content"])


class EventSummaryTests(unittest.TestCase):
    """The bounded recent-event feed shape."""

    def _log(self, filler=0):
        entries = [
            SimpleNamespace(
                kind="damage",
                actor="elosia",
                target="monster",
                text_template="{actor}造成了傷害",
            )
        ] * 3
        for _ in range(filler):
            entries.append(
                SimpleNamespace(
                    kind="damage",
                    actor="x" * 5000,
                    target=None,
                    text_template="y" * 5000,
                )
            )
        return SimpleNamespace(
            actor="elosia",
            skill_key="basic_attack",
            targets=("monster",),
            entries=entries,
        )

    def test_empty_feed_serializes_empty_record(self):
        self.assertEqual(summarize_event_logs(()), '{"event_logs": []}')

    def test_feed_is_bounded_and_json(self):
        text = summarize_event_logs([self._log() for _ in range(40)])
        parsed = json.loads(text)
        self.assertLessEqual(len(parsed["event_logs"]), 8)

    def test_oversized_feed_stays_within_total_bound(self):
        text = summarize_event_logs([self._log(filler=30)])
        json.loads(text)
        self.assertLessEqual(len(text), SUMMARY_MAX_TOTAL_CHARS)

    def test_single_oversized_log_is_trimmed_to_the_bound(self):
        # One log alone can exceed the budget; the newest entries are kept
        # and the serialized feed still honors the hard cap.
        text = summarize_event_logs([self._log(filler=200)])
        parsed = json.loads(text)
        self.assertLessEqual(len(text), SUMMARY_MAX_TOTAL_CHARS)
        self.assertLessEqual(len(parsed["event_logs"]), 1)


class RegistrationTests(unittest.TestCase):
    """Startup registration is idempotent and required for generation."""

    def test_re_registration_is_idempotent(self):
        _reset_all()
        register_title_nomination()
        register_title_nomination()
        self.assertIs(
            _OUTPUT_SCHEMAS.get("title_nomination"), TITLE_NOMINATION_OUTPUT_SCHEMA
        )
        self.addCleanup(_reset_all)

    def test_generation_requires_registration(self):
        _reset_all()
        client = _client_replying(_good_reply())
        with override_settings(LLM_PROFILES=_profiles()):
            failure = await_result(generate_epithet_candidates(_context(), client))
        self.assertTrue(failure.check(RuntimeError))
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
