"""Tests for the action-options generative layer (action-options-layer).

Covers the bounded-context serializer (fixed truncation order, budget
boundaries, named input errors, blocklist-vs-prompt separation,
byte-determinism, stable positional NPC order), the prompt assembly
(placeholder allowlist parity, rendered vocabulary + npc_index bindings, no
blocklist tokens), the guarded generation pipeline (FakeLLM success path, the
3-5 generation floor, ladder/binding/leak rejections with retry consumption,
transport failures resolving ``None`` without retries, disabled profile with
the stub never called, stage-message mapping), registration semantics
(idempotency, atomic rollback, startup wiring), and the proposal-only
boundary. Pure ``unittest`` — no database, no network, no live LLM.
"""

import json
import unittest
from dataclasses import fields
from unittest.mock import patch

from django.test import override_settings

from web.webclient.presentation.affordances import AffordanceView
from world.ai import action_options
from world.ai import guardrail
from world.ai.action_options import (
    ACTION_OPTIONS_OUTPUT_SCHEMA,
    CONTEXT_KIND,
    FREEFORM_ACTION_CODE,
    MAX_AFFORDANCES,
    MAX_MONSTER_ENTRIES,
    MAX_NARRATIVE_TAIL_LENGTH,
    MAX_NPC_DIGEST_LENGTH,
    MAX_NPC_ENTRIES,
    MAX_OBJECTIVE_LENGTH,
    MAX_ROOM_NAME_LENGTH,
    MAX_ROOM_SUMMARY_LENGTH,
    ActionOptionsClientRequiredError,
    ActionOptionsContext,
    ActionOptionsInputError,
    ActionOptionsNPCEntry,
    ActionOptionsNotRegisteredError,
    OptionSet,
    build_action_options_prompt,
    build_options_context,
    generate_action_options,
    register_action_options,
)
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import DuplicateSchemaError, _OUTPUT_SCHEMAS
from world.prompts.loader import UnexpectedPromptValueError, render_prompt
from world.prompts.registry import PROMPT_SPECS

from tools.spec_traceability import covers_requirement

FINGERPRINT = "fp_0123456789"

MOVE_PARAMS = {"exit_ref": "7", "current_node": "grid-0-0-0"}
LOOK_PARAMS = {"room": True}
WAIT_PARAMS = {"daypart": "noon"}


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


def _action(action_id="explore.move", label="往東走", params=None, *, freeform=False):
    return AffordanceView(
        action_id=action_id,
        label=label,
        params=dict(params) if params is not None else {},
        freeform=freeform,
        navigation=False,
        enabled=True,
        disabled_reason=None,
    )


def _freeform(npc_id):
    return AffordanceView(
        action_id=FREEFORM_ACTION_CODE,
        label="自由交談",
        params={"npc_id": npc_id},
        freeform=True,
        navigation=False,
        enabled=True,
        disabled_reason=None,
    )


def _navigation():
    return AffordanceView(
        surface="guild",
        label="公會",
        navigation=True,
        enabled=True,
        disabled_reason=None,
    )


def _default_affordances():
    return (
        _action("explore.move", "往東走", MOVE_PARAMS),
        _action("explore.look", "查看房間", LOOK_PARAMS),
        _action("explore.wait", "等待片刻", WAIT_PARAMS),
        _freeform(1001),
        _freeform(1002),
        _navigation(),
    )


def _npc_entries():
    return [
        {
            "npc_id": 1001,
            "display_name": "艾洛希雅",
            "dialogue_key": "guard_greet",
            "persona_digest": "南門守衛，性格沉穩。",
            "public_tier": "友好",
        },
        {
            "npc_id": 1002,
            "display_name": "莉亞娜",
            "dialogue_key": "merchant_greet",
            "persona_digest": "布商，說話輕快。",
            "public_tier": "熟悉",
        },
    ]


def _context(**overrides):
    values = {
        "room_name": "王都阿爾托利亞",
        "room_summary": "繁華的商貿都市，石板街道上人來人往。",
        "narrative_tail": "你看見衛兵在城門前低聲交談，隨後各自回到崗位。",
        "npc_entries": _npc_entries(),
        "monster_entries": [{"monster_id": 7, "display_name": "森林狼", "threat_tier": "低"}],
        "objective": "前往市政廳謁見執政官",
        "affordances": _default_affordances(),
        "secret_tokens": ("8741", "hidden_trait_hp"),
    }
    values.update(overrides)
    return build_options_context(**values)


def _payload(cards):
    return json.dumps({"context_kind": CONTEXT_KIND, "cards": cards}, ensure_ascii=False)


def _known_card(action_code="explore.move", label="往東走", params=None, hint=None):
    card = {"action_code": action_code, "label": label}
    if params is not None:
        card["params"] = dict(params)
    if hint is not None:
        card["hint"] = hint
    return card


def _look_card(hint=None):
    return _known_card("explore.look", "查看房間", None, hint)


def _freeform_card(npc_index, label="與她交談", hint=None):
    card = {"npc_index": npc_index, "label": label}
    if hint is not None:
        card["hint"] = hint
    return card


def _three_card_payload():
    return _payload([_known_card(), _look_card(), _freeform_card(0)])


class ActionOptionsContextBuilderTests(unittest.TestCase):
    """Bounded-context serializer (task 1.4)."""

    @covers_requirement("action-options-layer::bounded-context-serialization-is-public-only-and-truncation-ordered")
    def test_over_budget_context_truncates_in_the_fixed_order(self):
        tail = "頭" * 100 + "尾" * 600
        digests = ["丙" * 200 for _ in range(10)]
        npc_entries = [
            {
                "npc_id": index,
                "display_name": f"居民{index}",
                "persona_digest": digests[index],
            }
            for index in range(10)
        ]
        affordances = tuple(
            _action("explore.move", "往東走", MOVE_PARAMS) for _ in range(16)
        )
        context = build_options_context(
            room_name="王都阿爾托利亞",
            room_summary="繁華" * 150,
            narrative_tail=tail,
            npc_entries=npc_entries,
            affordances=affordances,
            objective="目標" * 60,
        )
        self.assertEqual(context.narrative_tail, "尾" * 600)
        self.assertTrue(
            all(len(entry.persona_digest) == 160 for entry in context.npc_entries)
        )
        self.assertEqual([entry.npc_id for entry in context.npc_entries], list(range(2, 10)))
        self.assertEqual(len(context.affordances), 16)
        self.assertEqual(context.room_name, "王都阿爾托利亞")
        self.assertEqual(len(context.room_summary), 300)
        self.assertEqual(len(context.objective), 120)

    @covers_requirement("action-options-layer::bounded-context-serialization-is-public-only-and-truncation-ordered")
    def test_monster_entries_drop_the_oldest_beyond_the_cap(self):
        monsters = [
            {"monster_id": index, "display_name": f"野獸{index}"}
            for index in range(MAX_MONSTER_ENTRIES + 1)
        ]
        context = build_options_context(
            room_name="名",
            room_summary="述",
            narrative_tail="尾",
            npc_entries=[],
            monster_entries=monsters,
            affordances=(),
        )
        self.assertEqual(
            [entry.monster_id for entry in context.monster_entries], [1, 2, 3, 4]
        )

    @covers_requirement("action-options-layer::bounded-context-serialization-is-public-only-and-truncation-ordered")
    def test_never_truncated_budget_boundaries(self):
        affordances = tuple(
            _action("explore.move", "往東走", MOVE_PARAMS) for _ in range(MAX_AFFORDANCES)
        )
        npc_entries = [
            {"npc_id": index, "display_name": f"居民{index}"}
            for index in range(MAX_NPC_ENTRIES)
        ]
        context = build_options_context(
            room_name="名" * MAX_ROOM_NAME_LENGTH,
            room_summary="述" * MAX_ROOM_SUMMARY_LENGTH,
            narrative_tail="尾" * (MAX_NARRATIVE_TAIL_LENGTH + 1),
            npc_entries=npc_entries,
            affordances=affordances,
            objective="標" * (MAX_OBJECTIVE_LENGTH + 1),
        )
        self.assertEqual(len(context.room_name), MAX_ROOM_NAME_LENGTH)
        self.assertEqual(len(context.room_summary), MAX_ROOM_SUMMARY_LENGTH)
        self.assertEqual(len(context.narrative_tail), MAX_NARRATIVE_TAIL_LENGTH)
        self.assertEqual(len(context.npc_entries), MAX_NPC_ENTRIES)
        self.assertEqual(len(context.objective), MAX_OBJECTIVE_LENGTH)
        with self.assertRaises(ActionOptionsInputError):
            build_options_context(
                room_name="名" * (MAX_ROOM_NAME_LENGTH + 1),
                room_summary="述",
                narrative_tail="尾",
                npc_entries=[],
                affordances=(),
            )
        with self.assertRaises(ActionOptionsInputError):
            build_options_context(
                room_name="名",
                room_summary="述" * (MAX_ROOM_SUMMARY_LENGTH + 1),
                narrative_tail="尾",
                npc_entries=[],
                affordances=(),
            )
        with self.assertRaises(ActionOptionsInputError):
            build_options_context(
                room_name="名",
                room_summary="述",
                narrative_tail="尾",
                npc_entries=[],
                affordances=(_action(),) * (MAX_AFFORDANCES + 1),
            )

    @covers_requirement("action-options-layer::bounded-context-serialization-is-public-only-and-truncation-ordered")
    def test_leak_blocklist_is_composed_but_never_prompted(self):
        context = _context()
        self.assertEqual(context.leak_blocklist, frozenset({"8741", "hidden_trait_hp"}))
        system, user = build_action_options_prompt(context)
        for message in (system, user):
            self.assertNotIn("8741", message["content"])
            self.assertNotIn("hidden_trait_hp", message["content"])

    def test_malformed_entry_inputs_raise_the_named_input_error(self):
        with self.assertRaises(ActionOptionsInputError):
            build_options_context(
                room_name="名",
                room_summary="述",
                narrative_tail="尾",
                npc_entries=[{"npc_id": 1}],
                affordances=(),
            )
        with self.assertRaises(ActionOptionsInputError):
            build_options_context(
                room_name="名",
                room_summary="述",
                narrative_tail="尾",
                npc_entries=[],
                monster_entries=[{"monster_id": 1}],
                affordances=(),
            )
        with self.assertRaises(ActionOptionsInputError):
            ActionOptionsContext(
                room_name="名",
                room_summary="述",
                npc_entries=(
                    ActionOptionsNPCEntry(npc_id=1, display_name="居民", persona_digest=""),
                ),
                monster_entries=(),
                objective=None,
                narrative_tail="尾",
                affordances=(object(),),
                leak_blocklist=frozenset(),
            )
        with self.assertRaises(ActionOptionsInputError):
            ActionOptionsNPCEntry(npc_id=1, display_name="居民", persona_digest=None)

    @covers_requirement("action-options-layer::bounded-context-serialization-is-public-only-and-truncation-ordered")
    def test_identical_input_produces_byte_identical_context_and_order(self):
        first = _context()
        second = _context()
        self.assertEqual(first, second)
        self.assertEqual(
            build_action_options_prompt(first), build_action_options_prompt(second)
        )
        self.assertEqual(
            [entry.npc_id for entry in first.npc_entries], [1001, 1002]
        )

    def test_entry_point_catches_the_named_input_error_and_resolves_none(self):
        _reset_all()
        register_action_options()
        client = FakeLLMClient()
        with patch.object(
            action_options,
            "build_action_options_prompt",
            side_effect=ActionOptionsInputError("affordances exceed the maximum of 16 entries"),
        ):
            with override_settings(LLM_PROFILES=_profiles()):
                d = generate_action_options(_context(), client, fingerprint=FINGERPRINT)
                result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(client.calls, [])
        _reset_all()


class ActionOptionsPromptTests(unittest.TestCase):
    """Prompt assembly (tasks 2.1-2.3)."""

    @covers_requirement("action-options-layer::prompt-assembly-honors-the-registered-placeholder-allowlist")
    def test_rendered_user_message_exposes_the_vocabulary_and_bindings(self):
        system, user = build_action_options_prompt(_context())
        content = user["content"]
        self.assertIn("explore.move", content)
        self.assertIn("action_id", content)
        self.assertIn("npc_index", content)
        self.assertIn("艾洛希雅", content)
        self.assertIn("1001", content)
        self.assertNotIn("公會", content)
        self.assertNotIn("8741", content)
        self.assertNotIn("hidden_trait_hp", content)
        self.assertEqual(system["role"], "system")
        self.assertEqual(user["role"], "user")

    @covers_requirement("action-options-layer::prompt-assembly-honors-the-registered-placeholder-allowlist")
    def test_placeholder_allowlists_match_the_serialized_context_fields(self):
        field_names = tuple(
            field.name for field in fields(ActionOptionsContext)
            if field.name != "leak_blocklist"
        )
        self.assertEqual(
            PROMPT_SPECS["action_options.user"].allowed_placeholders, field_names
        )
        self.assertEqual(PROMPT_SPECS["action_options.system"].allowed_placeholders, ())

    @covers_requirement("action-options-layer::prompt-assembly-honors-the-registered-placeholder-allowlist")
    def test_system_message_carries_no_context_tokens(self):
        context = _context()
        system, _ = build_action_options_prompt(context)
        for value in (context.room_name, context.narrative_tail, context.objective):
            self.assertNotIn(value, system["content"])

    def test_an_unregistered_substitution_value_fails_loudly(self):
        with self.assertRaises(UnexpectedPromptValueError):
            render_prompt("action_options.user", room_name="名", bogus="x")


class ActionOptionsGenerationTests(unittest.TestCase):
    """Generation pipeline on FakeLLMClient (tasks 3.3-3.4)."""

    def setUp(self):
        _reset_all()
        register_action_options()

    def tearDown(self):
        _reset_all()

    def _run(self, client, **profile_overrides):
        with override_settings(LLM_PROFILES=_profiles(**profile_overrides)):
            d = generate_action_options(_context(), client, fingerprint=FINGERPRINT)
            return await_result(d)

    @covers_requirement("action-options-layer::generation-resolves-to-an-optionset-or-the-none-degrade-outcome")
    def test_valid_three_card_proposal_resolves_without_retry(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _three_card_payload())
        result = self._run(client)
        self.assertEqual(len(client.calls), 1)
        self.assertIsInstance(result, OptionSet)
        self.assertEqual(result.fingerprint, FINGERPRINT)
        self.assertEqual(result.status, "ready")
        self.assertEqual(
            [card.action_code for card in result.cards],
            ["explore.move", "explore.look", FREEFORM_ACTION_CODE],
        )
        self.assertEqual(result.cards[0].params, MOVE_PARAMS)
        self.assertEqual(result.cards[2].params, {"npc_id": 1001})
        for message in client.calls[0].messages:
            self.assertNotIn(FINGERPRINT, message["content"])

    @covers_requirement("action-options-layer::generation-resolves-to-an-optionset-or-the-none-degrade-outcome")
    def test_valid_five_card_proposal_resolves(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _payload(
                [
                    _known_card(),
                    _look_card(),
                    _freeform_card(0),
                    _freeform_card(1),
                    _known_card("explore.wait", "等待片刻"),
                ]
            ),
        )
        result = self._run(client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(result.cards), 5)

    @covers_requirement("action-options-layer::generation-resolves-to-an-optionset-or-the-none-degrade-outcome")
    def test_disabled_profile_resolves_none_without_transport(self):
        client = FakeLLMClient()
        result = self._run(client, action_options={"enabled": False})
        self.assertIsNone(result)
        self.assertEqual(client.calls, [])

    @covers_requirement("action-options-layer::generation-resolves-to-an-optionset-or-the-none-degrade-outcome")
    def test_disabled_profile_resolves_none_even_when_unregistered(self):
        _reset_all()
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_profiles(action_options={"enabled": False})):
            d = generate_action_options(_context(), client, fingerprint=FINGERPRINT)
            result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(client.calls, [])

    @covers_requirement("action-options-layer::generation-resolves-to-an-optionset-or-the-none-degrade-outcome")
    def test_transport_failures_resolve_none_with_exactly_one_call(self):
        for failure in ("add_timeout", "add_http_error", "add_connection_error", "add_malformed_body"):
            with self.subTest(failure=failure):
                client = FakeLLMClient()
                getattr(client, failure)(lambda d: True)
                result = self._run(client)
                self.assertIsNone(result)
                self.assertEqual(len(client.calls), 1)

    @covers_requirement("action-options-layer::validation-failures-retry-within-the-bounded-budget")
    def test_zero_and_two_card_sets_retry_the_generation_floor(self):
        for cards in ([], [_known_card()], [_known_card(), _look_card()]):
            with self.subTest(count=len(cards)):
                client = FakeLLMClient()
                client.add_response(lambda d: len(d.messages) == 2, _payload(cards))
                client.add_response(
                    lambda d: len(d.messages) == 3, _three_card_payload()
                )
                result = self._run(client)
                self.assertEqual(len(client.calls), 2)
                self.assertIn(
                    "generation rule", client.calls[1].messages[-1]["content"]
                )
                self.assertEqual(len(result.cards), 3)

    @covers_requirement("action-options-layer::validation-failures-retry-within-the-bounded-budget")
    def test_exhausted_retries_degrade_to_none(self):
        client = FakeLLMClient()
        for _ in range(3):
            client.add_response(lambda d: True, _payload([_known_card()]))
        result = self._run(client)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 3)

    @covers_requirement("action-options-layer::validation-failures-retry-within-the-bounded-budget")
    def test_six_card_set_is_rejected_by_the_ladder_and_retried(self):
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, _payload([_known_card()] * 6))
        client.add_response(lambda d: len(d.messages) == 3, _three_card_payload())
        result = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn(
            "stage 4: card_count_out_of_range",
            client.calls[1].messages[-1]["content"],
        )
        self.assertEqual(len(result.cards), 3)

    @covers_requirement("action-options-layer::validation-failures-retry-within-the-bounded-budget")
    def test_non_cjk_label_maps_to_a_stage_six_message(self):
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, _payload([_known_card(label="hello")]))
        client.add_response(lambda d: len(d.messages) == 3, _three_card_payload())
        result = self._run(client)
        self.assertIn(
            "stage 6: non_cjk_label", client.calls[1].messages[-1]["content"]
        )
        self.assertEqual(len(result.cards), 3)

    @covers_requirement("action-options-layer::validation-failures-retry-within-the-bounded-budget")
    def test_leak_blocklist_rejection_is_retried_with_the_stage_message(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _payload([_known_card(hint="真實血量是 8741")]),
        )
        client.add_response(lambda d: len(d.messages) == 3, _three_card_payload())
        result = self._run(client)
        self.assertIn(
            "stage 10: leak_detected", client.calls[1].messages[-1]["content"]
        )
        self.assertEqual(len(result.cards), 3)

    @covers_requirement("action-options-layer::freeform-npc-references-are-bound-before-validation")
    def test_single_and_multiple_npc_references_resolve(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _payload([_freeform_card(0), _freeform_card(1), _known_card()]),
        )
        result = self._run(client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result.cards[0].params, {"npc_id": 1001})
        self.assertEqual(result.cards[1].params, {"npc_id": 1002})
        self.assertEqual(
            result.cards[0].action_code, FREEFORM_ACTION_CODE
        )

    @covers_requirement("action-options-layer::freeform-npc-references-are-bound-before-validation")
    def test_unknown_npc_index_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2, _payload([_freeform_card(9)])
        )
        client.add_response(lambda d: len(d.messages) == 3, _three_card_payload())
        result = self._run(client)
        self.assertIn(
            "outside the bound NPC list", client.calls[1].messages[-1]["content"]
        )
        self.assertEqual(len(result.cards), 3)

    @covers_requirement("action-options-layer::freeform-npc-references-are-bound-before-validation")
    def test_duplicate_target_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _payload([_freeform_card(0), _freeform_card(0)]),
        )
        client.add_response(lambda d: len(d.messages) == 3, _three_card_payload())
        result = self._run(client)
        self.assertIn("binds target", client.calls[1].messages[-1]["content"])
        self.assertIn("twice", client.calls[1].messages[-1]["content"])
        self.assertEqual(len(result.cards), 3)

    def test_explicit_none_client_is_rejected(self):
        with override_settings(LLM_PROFILES=_profiles()):
            d = generate_action_options(_context(), None, fingerprint=FINGERPRINT)
            failure = await_result(d)
        self.assertTrue(failure.check(ActionOptionsClientRequiredError))

    def test_generation_requires_registration(self):
        _reset_all()
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_profiles()):
            d = generate_action_options(_context(), client, fingerprint=FINGERPRINT)
            failure = await_result(d)
        self.assertTrue(failure.check(ActionOptionsNotRegisteredError))

    @covers_requirement("action-options-layer::the-layer-is-strictly-proposal-only")
    def test_the_resolved_proposal_is_frozen_with_no_mutable_containers(self):
        from dataclasses import FrozenInstanceError

        client = FakeLLMClient()
        client.add_response(lambda d: True, _three_card_payload())
        result = self._run(client)
        self.assertIsInstance(result, OptionSet)
        with self.assertRaises(FrozenInstanceError):
            result.cards = ()
        with self.assertRaises(FrozenInstanceError):
            result.cards[0].params = {}


class ActionOptionsRegistrationTests(unittest.TestCase):
    """Registration semantics (tasks 3.1, 4.2)."""

    def setUp(self):
        _reset_all()

    def tearDown(self):
        _reset_all()

    @covers_requirement("action-options-layer::guardrail-hooks-install-atomically-and-idempotently")
    def test_double_registration_is_a_noop(self):
        register_action_options()
        register_action_options()
        self.assertTrue(action_options._is_registered())
        self.assertIs(
            guardrail._degrade_fallbacks["action_options"],
            action_options._degrade_fallback,
        )
        self.assertIs(_OUTPUT_SCHEMAS["action_options"], ACTION_OPTIONS_OUTPUT_SCHEMA)

    @covers_requirement("action-options-layer::guardrail-hooks-install-atomically-and-idempotently")
    def test_partial_failure_rolls_back_its_own_hooks(self):
        with patch(
            "world.ai.action_options.register_output_schema",
            side_effect=DuplicateSchemaError("action_options"),
        ):
            with self.assertRaises(DuplicateSchemaError):
                register_action_options()
        self.assertFalse(action_options._is_registered())
        self.assertNotIn("action_options", guardrail._degrade_fallbacks)
        self.assertNotIn("action_options", _OUTPUT_SCHEMAS)


class ActionOptionsStartupRegistrationTests(unittest.TestCase):
    """Startup wiring (tasks 4.1-4.2)."""

    def setUp(self):
        _reset_all()

    def tearDown(self):
        _reset_all()

    @covers_requirement("action-options-layer::guardrail-hooks-install-atomically-and-idempotently")
    def test_startup_seam_registers_the_layer(self):
        from server.conf.at_server_startstop import _register_action_options_layer

        _register_action_options_layer()
        self.assertTrue(action_options._is_registered())

    @covers_requirement("action-options-layer::guardrail-hooks-install-atomically-and-idempotently")
    def test_startup_seam_survives_a_conflicting_registration(self):
        from server.conf.at_server_startstop import _register_action_options_layer

        guardrail.register_degrade_fallback("action_options", lambda: "foreign")
        _register_action_options_layer()
        self.assertFalse(action_options._is_registered())

    @covers_requirement("action-options-layer::guardrail-hooks-install-atomically-and-idempotently")
    def test_startup_seam_skips_when_the_profile_slot_is_missing(self):
        from server.conf.at_server_startstop import _register_action_options_layer

        with patch.object(
            guardrail,
            "LAYER_NAMES",
            ("narrator", "npc_dialogue", "scenario_director", "scene_builder", "character_creation"),
        ):
            _register_action_options_layer()
        self.assertFalse(action_options._is_registered())

    @covers_requirement("action-options-layer::guardrail-hooks-install-atomically-and-idempotently")
    def test_startup_seam_skips_on_a_duplicate_schema_registration(self):
        from server.conf.at_server_startstop import _register_action_options_layer

        with patch(
            "world.ai.action_options.register_output_schema",
            side_effect=DuplicateSchemaError("action_options"),
        ):
            _register_action_options_layer()
        self.assertFalse(action_options._is_registered())


if __name__ == "__main__":
    unittest.main()
