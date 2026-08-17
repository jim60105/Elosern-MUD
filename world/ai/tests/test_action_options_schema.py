"""Tests for the action-options card schema and validation ladder.

Covers the frozen ``OptionSet``/``SuggestionCard`` vocabulary construction
(mutable-container rejection, closed enums, params value shapes), the fixed
12-stage validation ladder with one named rejection per stage, the stage-9
canonical replacement against the change-1 affordance vocabulary, the freeform
binding-only exception, the leak gates on label/hint, the enrichment helper,
and the exact-field JSON contract parser. Pure ``unittest`` — no database, no
network, no live LLM.
"""

import unittest

from tools.spec_traceability import covers_requirement

from web.webclient.presentation.affordances import AffordanceView
from world.ai.action_options import (
    CARD_KINDS,
    CARD_COUNT_OUT_OF_RANGE,
    CONTEXT_KIND,
    DIGIT_IN_LABEL,
    EMPTY_LABEL,
    FREEFORM_ACTION_CODE,
    HINT_TOO_LONG,
    LABEL_TOO_LONG,
    LADDER_CODES,
    LEAK_DETECTED,
    MAX_CARDS,
    MAX_HINT_LENGTH,
    MAX_LABEL_LENGTH,
    MAX_PARAMS,
    MAX_SAFE_INTEGER,
    NEGATIVE_MEMO_TTL,
    NO_SUCH_AFFORDANCE,
    NON_CJK_LABEL,
    OptionsValidationError,
    OptionSet,
    PLACEHOLDER_LABEL,
    SCHEMA_VIOLATION,
    SuggestionCard,
    UNKNOWN_ACTION_CODE,
    UNKNOWN_TARGET,
    enrich_options_payload,
    parse_action_options_payload,
    validate_optionset,
)

FINGERPRINT = "fp_0123456789"

MOVE_PARAMS = {"exit_ref": "7", "current_node": "grid-0-0-0"}
LOOK_ROOM_PARAMS = {"room": True}


def _action(
    action_id="explore.move",
    label="往東走",
    params=None,
    *,
    freeform=False,
    enabled=True,
):
    return AffordanceView(
        action_id=action_id,
        label=label,
        params=dict(params) if params is not None else {},
        freeform=freeform,
        navigation=False,
        enabled=enabled,
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


def _known_card(action_code="explore.move", label="往東走", params=None, hint=None):
    card = {
        "kind": "known_action",
        "action_code": action_code,
        "label": label,
        "params": dict(params) if params is not None else {},
    }
    if hint is not None:
        card["hint"] = hint
    return card


def _freeform_card(npc_id, label="與她交談", hint=None):
    card = {
        "kind": "freeform",
        "action_code": FREEFORM_ACTION_CODE,
        "label": label,
        "params": {"npc_id": npc_id},
    }
    if hint is not None:
        card["hint"] = hint
    return card


def _raw(cards, context_kind=CONTEXT_KIND):
    return {"context_kind": context_kind, "cards": cards}


def _affordances(*entries):
    return tuple(entries)


class VocabularyConstructionTests(unittest.TestCase):
    @covers_requirement("ai-action-options-schema::world-ai-action-options-py-defines-the-frozen-one-wire-shape-card-vocabulary")
    def test_mutable_containers_nested_in_params_are_rejected(self):
        with self.assertRaises(TypeError):
            SuggestionCard(
                kind="known_action",
                action_code="explore.move",
                label="往東走",
                params={"exit_ref": ["1", "2"]},
            )
        with self.assertRaises(TypeError):
            SuggestionCard(
                kind="known_action",
                action_code="explore.move",
                label="往東走",
                params={"nested": {"exit_ref": "1"}},
            )

    @covers_requirement("ai-action-options-schema::world-ai-action-options-py-defines-the-frozen-one-wire-shape-card-vocabulary")
    def test_mutable_cards_list_is_rejected(self):
        card = SuggestionCard(
            kind="known_action",
            action_code="explore.move",
            label="往東走",
            params=MOVE_PARAMS,
        )
        with self.assertRaises(TypeError):
            OptionSet(fingerprint=FINGERPRINT, cards=[card])

    @covers_requirement("ai-action-options-schema::world-ai-action-options-py-defines-the-frozen-one-wire-shape-card-vocabulary")
    def test_transport_statuses_are_rejected_at_construction(self):
        card = SuggestionCard(
            kind="known_action",
            action_code="explore.move",
            label="往東走",
            params=MOVE_PARAMS,
        )
        for status in ("generating", "degraded"):
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    OptionSet(
                        fingerprint=FINGERPRINT, status=status, cards=(card,)
                    )
        optionset = OptionSet(fingerprint=FINGERPRINT, cards=(card,))
        self.assertEqual(optionset.status, "ready")

    @covers_requirement("ai-action-options-schema::world-ai-action-options-py-defines-the-frozen-one-wire-shape-card-vocabulary")
    def test_closed_kind_enum(self):
        with self.assertRaises(ValueError):
            SuggestionCard(
                kind="navigate",
                action_code="explore.move",
                label="往東走",
                params=MOVE_PARAMS,
            )
        self.assertEqual(CARD_KINDS, ("known_action", "freeform"))

    def test_params_shapes_at_boundary_and_one_past(self):
        boundary = {f"k{i}": i for i in range(MAX_PARAMS)}
        card = SuggestionCard(
            kind="known_action",
            action_code="explore.move",
            label="往東走",
            params=boundary,
        )
        self.assertEqual(len(card.params), MAX_PARAMS)
        over = {f"k{i}": i for i in range(MAX_PARAMS + 1)}
        with self.assertRaises(ValueError):
            SuggestionCard(
                kind="known_action",
                action_code="explore.move",
                label="往東走",
                params=over,
            )

    def test_params_int_and_string_bounds(self):
        SuggestionCard(
            kind="known_action",
            action_code="explore.move",
            label="往東走",
            params={"npc_id": MAX_SAFE_INTEGER},
        )
        with self.assertRaises(ValueError):
            SuggestionCard(
                kind="known_action",
                action_code="explore.move",
                label="往東走",
                params={"npc_id": MAX_SAFE_INTEGER + 1},
            )
        SuggestionCard(
            kind="known_action",
            action_code="explore.move",
            label="往東走",
            params={"keyword_id": "長" * 32},
        )
        with self.assertRaises(ValueError):
            SuggestionCard(
                kind="known_action",
                action_code="explore.move",
                label="往東走",
                params={"keyword_id": "長" * 33},
            )

    def test_boolean_room_survey_marker_is_accepted(self):
        card = SuggestionCard(
            kind="known_action",
            action_code="explore.look",
            label="查看房間",
            params=LOOK_ROOM_PARAMS,
        )
        self.assertIs(card.params["room"], True)

    def test_any_other_boolean_params_are_rejected(self):
        for params in (
            {"room": False},
            {"enabled": True},
            {"room": True, "extra": 1},
            {"flag": True},
        ):
            with self.subTest(params=params):
                with self.assertRaises(ValueError):
                    SuggestionCard(
                        kind="known_action",
                        action_code="explore.look",
                        label="查看房間",
                        params=params,
                    )


class LadderStageTests(unittest.TestCase):
    """One test per rejection code plus first-failure-wins ordering."""

    def _assert_rejects(self, code, raw, affordances=None, leak_blocklist=frozenset()):
        with self.assertRaises(OptionsValidationError) as ctx:
            validate_optionset(
                raw,
                fingerprint=FINGERPRINT,
                affordances=affordances
                if affordances is not None
                else _affordances(_action()),
                leak_blocklist=leak_blocklist,
            )
        self.assertEqual(ctx.exception.code, code)
        return ctx.exception

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_structure_stage_rejects_extra_top_level_keys(self):
        raw = _raw([_known_card()])
        raw["version"] = 3
        self._assert_rejects(SCHEMA_VIOLATION, raw)

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_fingerprint_stage_rejects_opaque_shape(self):
        for fingerprint in ("short", "has whitespace here", "x" * 65):
            with self.subTest(fingerprint=fingerprint):
                with self.assertRaises(OptionsValidationError) as ctx:
                    validate_optionset(
                        _raw([_known_card()]),
                        fingerprint=fingerprint,
                        affordances=_affordances(_action()),
                    )
                self.assertEqual(ctx.exception.code, SCHEMA_VIOLATION)

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_kind_stage_rejects_unknown_context_kind(self):
        self._assert_rejects(
            SCHEMA_VIOLATION, _raw([_known_card()], context_kind="combat")
        )

    @covers_requirement("ai-action-options-schema::the-schema-defines-exact-caps-and-a-status-dependent-card-count-contract")
    def test_card_count_accepts_zero_to_five(self):
        affordances = _affordances(
            _action("explore.move", "往東走", MOVE_PARAMS),
            _action("explore.look", "查看", {"target_id": 1}),
            _action("explore.wait", "等待", {"daypart": "noon"}),
            _action("explore.engage", "戰鬥", {"monster_id": 1}),
            _action("explore.talk_scripted", "問候", {"npc_id": 1, "keyword_id": "hello"}),
        )
        cards = [
            _known_card("explore.move", "往東走", MOVE_PARAMS),
            _known_card("explore.look", "查看", {"target_id": 1}),
            _known_card("explore.wait", "等待", {"daypart": "noon"}),
            _known_card("explore.engage", "戰鬥", {"monster_id": 1}),
            _known_card("explore.talk_scripted", "問候", {"npc_id": 1, "keyword_id": "hello"}),
        ]
        for count in range(MAX_CARDS + 1):
            with self.subTest(count=count):
                result = validate_optionset(
                    _raw(cards[:count]),
                    fingerprint=FINGERPRINT,
                    affordances=affordances,
                )
                self.assertEqual(len(result.cards), count)

    @covers_requirement("ai-action-options-schema::the-schema-defines-exact-caps-and-a-status-dependent-card-count-contract")
    def test_six_cards_reject_with_card_count_out_of_range(self):
        affordances = _affordances(
            _action("explore.look", "查看一", {"target_id": 1}),
            _action("explore.look", "查看二", {"target_id": 2}),
            _action("explore.look", "查看三", {"target_id": 3}),
            _action("explore.look", "查看四", {"target_id": 4}),
            _action("explore.look", "查看五", {"target_id": 5}),
            _action("explore.look", "查看六", {"target_id": 6}),
        )
        self._assert_rejects(
            CARD_COUNT_OUT_OF_RANGE,
            _raw(
                [
                    _known_card("explore.look", "查看一", {"target_id": 1}),
                    _known_card("explore.look", "查看二", {"target_id": 2}),
                    _known_card("explore.look", "查看三", {"target_id": 3}),
                    _known_card("explore.look", "查看四", {"target_id": 4}),
                    _known_card("explore.look", "查看五", {"target_id": 5}),
                    _known_card("explore.look", "查看六", {"target_id": 6}),
                ]
            ),
            affordances=affordances,
        )

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_card_keys_stage_rejects_unknown_card_keys(self):
        card = _known_card()
        card["target"] = "intruder"
        self._assert_rejects(SCHEMA_VIOLATION, _raw([card]))
        bad_kind = _known_card()
        bad_kind["kind"] = "navigate"
        self._assert_rejects(SCHEMA_VIOLATION, _raw([bad_kind]))

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_label_stage_rejects_empty_too_long_and_ascii(self):
        self._assert_rejects(EMPTY_LABEL, _raw([_known_card(label="")]))
        self._assert_rejects(
            LABEL_TOO_LONG, _raw([_known_card(label="長" * (MAX_LABEL_LENGTH + 1))])
        )
        self._assert_rejects(NON_CJK_LABEL, _raw([_known_card(label="hello")]))

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_placeholder_gate_rejects_brace_tokens(self):
        self._assert_rejects(
            PLACEHOLDER_LABEL, _raw([_known_card(label="帶上 {name}")])
        )
        self._assert_rejects(
            PLACEHOLDER_LABEL,
            _raw([_known_card(hint="對 {unknown} 使用")]),
        )

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_digit_gate_rejects_ascii_digits_in_label(self):
        self._assert_rejects(
            DIGIT_IN_LABEL, _raw([_known_card(label="3 個敵人")])
        )
        self._assert_rejects(
            DIGIT_IN_LABEL,
            _raw([_known_card(hint="真實血量是 87")]),
        )

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_unknown_action_code_rejects_unregistered_code(self):
        self._assert_rejects(
            UNKNOWN_ACTION_CODE,
            _raw([_known_card(action_code="explore.teleport")]),
        )

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_no_such_affordance_rejects_registered_but_not_current(self):
        self._assert_rejects(
            NO_SUCH_AFFORDANCE,
            _raw([_known_card(action_code="explore.engage", params={"monster_id": 1})]),
            affordances=_affordances(_action()),
        )

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_unknown_target_rejects_unbound_freeform(self):
        self._assert_rejects(
            UNKNOWN_TARGET,
            _raw([_freeform_card(npc_id=9999)]),
            affordances=_affordances(_freeform(1001)),
        )

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_hint_gate_rejects_too_long_hint(self):
        self._assert_rejects(
            HINT_TOO_LONG,
            _raw([_known_card(hint="很" * (MAX_HINT_LENGTH + 1))]),
        )

    @covers_requirement("ai-action-options-schema::leak-gates-apply-to-model-visible-text-only-and-expose-no-hidden-values")
    def test_leak_gate_rejects_blocklisted_tokens_in_hint(self):
        self._assert_rejects(
            LEAK_DETECTED,
            _raw([_known_card(hint="敵人的真實血量是 87")]),
            leak_blocklist=frozenset({"87"}),
        )

    @covers_requirement("ai-action-options-schema::the-validation-ladder-runs-12-fixed-stages-with-one-named-rejection-code-each")
    def test_first_failure_wins_ordering(self):
        raw = _raw([_known_card()])
        raw["version"] = 3
        raw["cards"][0]["label"] = "長" * (MAX_LABEL_LENGTH + 1)
        error = self._assert_rejects(SCHEMA_VIOLATION, raw)
        self.assertIn("fingerprint, context_kind, status, and cards", str(error))

    def test_ladder_code_set_is_exactly_the_twelve_codes(self):
        self.assertEqual(
            set(LADDER_CODES),
            {
                SCHEMA_VIOLATION,
                CARD_COUNT_OUT_OF_RANGE,
                EMPTY_LABEL,
                LABEL_TOO_LONG,
                NON_CJK_LABEL,
                PLACEHOLDER_LABEL,
                DIGIT_IN_LABEL,
                UNKNOWN_ACTION_CODE,
                NO_SUCH_AFFORDANCE,
                UNKNOWN_TARGET,
                HINT_TOO_LONG,
                LEAK_DETECTED,
            },
        )


class CanonicalMatchTests(unittest.TestCase):
    def _validate(self, raw, affordances, leak_blocklist=frozenset()):
        return validate_optionset(
            raw,
            fingerprint=FINGERPRINT,
            affordances=affordances,
            leak_blocklist=leak_blocklist,
        )

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_valid_now_known_card_passes_with_canonical_replacement(self):
        move = _action("explore.move", "往東走", MOVE_PARAMS)
        raw = _raw([_known_card(params={"exit_ref": "999"})])
        result = self._validate(raw, _affordances(move))
        card = result.cards[0]
        self.assertEqual(card.action_code, "explore.move")
        self.assertEqual(card.params, MOVE_PARAMS)

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_known_card_with_omitted_params_passes(self):
        move = _action("explore.move", "往東走", MOVE_PARAMS)
        raw = {
            "context_kind": CONTEXT_KIND,
            "cards": [
                {
                    "kind": "known_action",
                    "action_code": "explore.move",
                    "label": "往東走",
                }
            ],
        }
        result = self._validate(raw, _affordances(move))
        self.assertEqual(result.cards[0].params, MOVE_PARAMS)

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_multi_entry_code_disambiguates_by_model_params(self):
        east = _action("explore.move", "往東走", {"exit_ref": "7", "current_node": "grid-0-0-0"})
        west = _action("explore.move", "往西走", {"exit_ref": "8", "current_node": "grid-0-0-0"})
        raw = _raw([_known_card(params={"exit_ref": "8", "current_node": "grid-0-0-0"})])
        result = self._validate(raw, _affordances(east, west))
        self.assertEqual(result.cards[0].params["exit_ref"], "8")

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_ambiguous_multi_entry_code_rejects(self):
        east = _action("explore.move", "往東走", {"exit_ref": "7", "current_node": "grid-0-0-0"})
        west = _action("explore.move", "往西走", {"exit_ref": "8", "current_node": "grid-0-0-0"})
        with self.assertRaises(OptionsValidationError) as ctx:
            self._validate(_raw([_known_card()]), _affordances(east, west))
        self.assertEqual(ctx.exception.code, NO_SUCH_AFFORDANCE)

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_disabled_affordance_cannot_back_a_card(self):
        locked = AffordanceView(
            action_id="explore.move",
            label="往東走",
            params=MOVE_PARAMS,
            freeform=False,
            navigation=False,
            enabled=False,
            disabled_reason=("locked", "此出口目前無法通行。"),
        )
        raw = _raw([_known_card(params=MOVE_PARAMS)])
        with self.assertRaises(OptionsValidationError) as ctx:
            self._validate(raw, _affordances(locked))
        self.assertEqual(ctx.exception.code, NO_SUCH_AFFORDANCE)

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_navigation_entries_never_back_a_card(self):
        raw = _raw([_known_card(action_code="explore.move", params={"exit_ref": "7"})])
        with self.assertRaises(OptionsValidationError) as ctx:
            self._validate(raw, _affordances(_navigation()))
        self.assertEqual(ctx.exception.code, NO_SUCH_AFFORDANCE)

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_freeform_card_binds_present_target(self):
        npc = _freeform(1001)
        raw = _raw([_freeform_card(npc_id=1001)])
        result = self._validate(raw, _affordances(npc))
        card = result.cards[0]
        self.assertEqual(card.kind, "freeform")
        self.assertEqual(card.action_code, FREEFORM_ACTION_CODE)
        self.assertEqual(card.params, {"npc_id": 1001})

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_freeform_card_params_stay_exactly_the_binding_shape(self):
        npc = AffordanceView(
            action_id=FREEFORM_ACTION_CODE,
            label="自由交談",
            params={"npc_id": 1001, "extra": "x"},
            freeform=True,
            navigation=False,
            enabled=True,
            disabled_reason=None,
        )
        raw = _raw([_freeform_card(npc_id=1001)])
        with self.assertRaises(OptionsValidationError) as ctx:
            self._validate(raw, _affordances(npc))
        self.assertEqual(ctx.exception.code, UNKNOWN_TARGET)
        # A well-formed affordance still yields exactly the binding shape.
        result = self._validate(raw, _affordances(_freeform(1001)))
        self.assertEqual(result.cards[0].params, {"npc_id": 1001})

    @covers_requirement("ai-action-options-schema::stage-9-enforces-canonical-replacement-against-the-affordance-vocabulary")
    def test_freeform_wrong_params_shape_rejects(self):
        card = _freeform_card(npc_id=1001)
        card["params"] = {"npc_id": "1001"}
        with self.assertRaises(OptionsValidationError) as ctx:
            self._validate(_raw([card]), _affordances(_freeform(1001)))
        self.assertEqual(ctx.exception.code, UNKNOWN_TARGET)

    @covers_requirement("ai-action-options-schema::enrichment-injects-caller-side-fields-before-validation")
    def test_validated_card_params_byte_equal_fixture_affordance(self):
        move = _action("explore.move", "往東走", MOVE_PARAMS)
        result = self._validate(_raw([_known_card()]), _affordances(move))
        self.assertEqual(dict(result.cards[0].params), move.params)


class LeakGateTests(unittest.TestCase):
    def _assert_leak(self, blocklist, label="往東走", hint=None):
        card = _known_card(label=label)
        if hint is not None:
            card["hint"] = hint
        with self.assertRaises(OptionsValidationError) as ctx:
            validate_optionset(
                _raw([card]),
                fingerprint=FINGERPRINT,
                affordances=_affordances(_action()),
                leak_blocklist=frozenset(blocklist),
            )
        self.assertEqual(ctx.exception.code, LEAK_DETECTED)

    @covers_requirement("ai-action-options-schema::leak-gates-apply-to-model-visible-text-only-and-expose-no-hidden-values")
    def test_true_trait_number_in_label_is_rejected(self):
        # Fullwidth digits pass the ASCII digit gate but NFKC-normalize into
        # the blocklist token, so the leak predicate (not the digit gate) is
        # what fires — mirroring npc_dialogue's no-leak validator shape.
        self._assert_leak({"87"}, label="敵人的真實血量是８７")

    @covers_requirement("ai-action-options-schema::leak-gates-apply-to-model-visible-text-only-and-expose-no-hidden-values")
    def test_affinity_number_in_hint_is_rejected(self):
        self._assert_leak({"1001"}, hint="好感度達到 1001")

    @covers_requirement("ai-action-options-schema::leak-gates-apply-to-model-visible-text-only-and-expose-no-hidden-values")
    def test_disguised_value_token_is_rejected(self):
        self._assert_leak({"真實力量"}, label="隱藏了真實力量的差距")

    @covers_requirement("ai-action-options-schema::leak-gates-apply-to-model-visible-text-only-and-expose-no-hidden-values")
    def test_fabricated_hidden_token_is_rejected(self):
        self._assert_leak({"上古祕寶"}, hint="找尋上古祕寶的線索")

    @covers_requirement("ai-action-options-schema::leak-gates-apply-to-model-visible-text-only-and-expose-no-hidden-values")
    def test_params_are_exempt_from_the_blocklist(self):
        move = _action("explore.move", "往東走", MOVE_PARAMS)
        result = validate_optionset(
            _raw([_known_card(params=MOVE_PARAMS)]),
            fingerprint=FINGERPRINT,
            affordances=_affordances(move),
            leak_blocklist=frozenset({"7"}),
        )
        self.assertEqual(dict(result.cards[0].params), MOVE_PARAMS)


class EnrichmentTests(unittest.TestCase):
    @covers_requirement("ai-action-options-schema::enrichment-injects-caller-side-fields-before-validation")
    def test_enrichment_injects_fingerprint_and_status(self):
        raw = _raw([_known_card()])
        enriched = enrich_options_payload(raw, fingerprint=FINGERPRINT)
        self.assertEqual(enriched["fingerprint"], FINGERPRINT)
        self.assertEqual(enriched["status"], "ready")
        self.assertEqual(enriched["context_kind"], CONTEXT_KIND)

    @covers_requirement("ai-action-options-schema::enrichment-injects-caller-side-fields-before-validation")
    def test_freeform_cards_receive_the_fixed_action_code_automatically(self):
        raw = _raw(
            [
                {
                    "label": "與她交談",
                    "params": {"npc_id": 1001},
                }
            ]
        )
        enriched = enrich_options_payload(raw, fingerprint=FINGERPRINT)
        card = enriched["cards"][0]
        self.assertEqual(card["kind"], "freeform")
        self.assertEqual(card["action_code"], FREEFORM_ACTION_CODE)
        result = validate_optionset(
            raw,
            fingerprint=FINGERPRINT,
            affordances=_affordances(_freeform(1001)),
        )
        self.assertEqual(result.cards[0].kind, "freeform")
        self.assertEqual(result.cards[0].action_code, FREEFORM_ACTION_CODE)

    @covers_requirement("ai-action-options-schema::enrichment-injects-caller-side-fields-before-validation")
    def test_enrichment_marks_known_action_cards(self):
        raw = _raw([_known_card()])
        enriched = enrich_options_payload(raw, fingerprint=FINGERPRINT)
        self.assertEqual(enriched["cards"][0]["kind"], "known_action")

    def test_enrichment_rejects_non_object_raw(self):
        with self.assertRaises(OptionsValidationError) as ctx:
            enrich_options_payload("nonsense", fingerprint=FINGERPRINT)
        self.assertEqual(ctx.exception.code, SCHEMA_VIOLATION)


class JsonContractTests(unittest.TestCase):
    @covers_requirement("ai-action-options-schema::the-llm-json-output-contract-is-enforced-by-exact-field-parsing")
    def test_parses_sample_known_action_payload(self):
        payload = {
            "context_kind": CONTEXT_KIND,
            "cards": [
                {
                    "action_code": "explore.move",
                    "label": "往東走",
                    "params": {"exit_ref": "7"},
                }
            ],
        }
        parsed = parse_action_options_payload(payload)
        self.assertEqual(parsed["cards"][0]["action_code"], "explore.move")

    @covers_requirement("ai-action-options-schema::the-llm-json-output-contract-is-enforced-by-exact-field-parsing")
    def test_parses_sample_freeform_payload_with_npc_index(self):
        payload = {
            "context_kind": CONTEXT_KIND,
            "cards": [{"npc_index": 0, "label": "與她交談"}],
        }
        parsed = parse_action_options_payload(payload)
        self.assertEqual(parsed["cards"][0]["npc_index"], 0)

    @covers_requirement("ai-action-options-schema::the-llm-json-output-contract-is-enforced-by-exact-field-parsing")
    def test_unknown_card_key_is_rejected(self):
        for extra in ("target", "score"):
            with self.subTest(extra=extra):
                payload = {
                    "context_kind": CONTEXT_KIND,
                    "cards": [
                        {
                            "action_code": "explore.move",
                            "label": "往東走",
                            extra: "intruder",
                        }
                    ],
                }
                with self.assertRaises(OptionsValidationError) as ctx:
                    parse_action_options_payload(payload)
                self.assertEqual(ctx.exception.code, SCHEMA_VIOLATION)

    @covers_requirement("ai-action-options-schema::the-llm-json-output-contract-is-enforced-by-exact-field-parsing")
    def test_ambiguous_card_form_is_rejected(self):
        payload = {
            "context_kind": CONTEXT_KIND,
            "cards": [
                {
                    "action_code": "explore.move",
                    "npc_index": 0,
                    "label": "往東走",
                }
            ],
        }
        with self.assertRaises(OptionsValidationError) as ctx:
            parse_action_options_payload(payload)
        self.assertEqual(ctx.exception.code, SCHEMA_VIOLATION)

    @covers_requirement("ai-action-options-schema::the-llm-json-output-contract-is-enforced-by-exact-field-parsing")
    def test_top_level_unknown_keys_are_rejected(self):
        payload = {
            "context_kind": CONTEXT_KIND,
            "cards": [],
            "version": 3,
        }
        with self.assertRaises(OptionsValidationError) as ctx:
            parse_action_options_payload(payload)
        self.assertEqual(ctx.exception.code, SCHEMA_VIOLATION)

    @covers_requirement("ai-action-options-schema::the-llm-json-output-contract-is-enforced-by-exact-field-parsing")
    def test_absent_caller_side_fields_are_handled_at_enrichment(self):
        payload = {
            "context_kind": CONTEXT_KIND,
            "cards": [{"npc_index": 0, "label": "與她交談"}],
        }
        parsed = parse_action_options_payload(payload)
        # The npc_index fixture path is layer-owned: the generative layer
        # resolves npc_index against the prompt's bound NPC list into
        # {"npc_id": int} params before validation. Enrichment here only adds
        # the caller-side fingerprint/status and the freeform action_code.
        parsed["cards"][0] = {"params": {"npc_id": 1001}, "label": "與她交談"}
        result = validate_optionset(
            parsed,
            fingerprint=FINGERPRINT,
            affordances=_affordances(_freeform(1001)),
        )
        self.assertEqual(result.fingerprint, FINGERPRINT)
        self.assertEqual(result.cards[0].action_code, FREEFORM_ACTION_CODE)


if __name__ == "__main__":
    unittest.main()
