"""Exact ``title_ballot`` schema and presenter tests (title-epithet-nomination).

Covers the v1 shared bounds (1..3 candidates, 64-code-point display,
80-code-point basis), the strictly-ascending 1-based indices, the exact
available/unavailable field sets, the envelope byte guarantee, and the
presenter's never-raise degradation: absent ballot, missing/None actor, and
present-but-malformed ballot state all render the zero-candidate payload.
Ballot state is staged only through the rules-layer writers.
"""

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
    unavailable_payload,
)
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.title_ballot import (
    TITLE_BALLOT_MAX_BASIS_CODE_POINTS,
    TITLE_BALLOT_MAX_CANDIDATES,
    TITLE_BALLOT_MAX_DISPLAY_CODE_POINTS,
    TITLE_BALLOT_SCHEMA_VERSION,
    TitleBallotPanelError,
    title_ballot_presenter,
    validate_title_ballot,
)
from world.rules.clock import get_world_clock
from world.rules.titles import (
    BALLOT_BASIS_MAX_CHARS,
    MAX_BALLOT_CANDIDATES,
    MAX_EPITHET_DISPLAY_CODE_POINTS,
    PENDING_BALLOT_KEY,
    persist_nomination_ballot,
    safe_pending_ballot,
)

_CANDIDATE = {"display": "破城先鋒", "basis": "率先破門，功在任何人之先。"}


def _candidate(index, **overrides):
    value = {"index": index, **_CANDIDATE}
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": TITLE_BALLOT_SCHEMA_VERSION,
        "available": True,
        "kind": "title_ballot",
        "candidates": [_candidate(1)],
    }
    value.update(overrides)
    return value


class TitleBallotSchemaTests(unittest.TestCase):
    def test_minimal_and_maximal_ballots_normalize(self):
        for count in range(TITLE_BALLOT_MAX_CANDIDATES + 1):
            panel = _valid_panel(
                candidates=[
                    _candidate(
                        index,
                        display="長" * TITLE_BALLOT_MAX_DISPLAY_CODE_POINTS,
                        basis="援" * TITLE_BALLOT_MAX_BASIS_CODE_POINTS,
                    )
                    for index in range(1, count + 1)
                ]
            )
            normalized = validate_title_ballot(panel)
            self.assertEqual(len(normalized["candidates"]), count)
            self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)

    def test_empty_candidate_list_is_the_legitimate_idle_form(self):
        normalized = validate_title_ballot(_valid_panel(candidates=[]))
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["candidates"], [])

    def test_unknown_missing_and_bad_kind_reject(self):
        with self.assertRaises(ProtocolValidationError):
            validate_title_ballot(_valid_panel(extra=1))
        missing = _valid_panel()
        del missing["candidates"]
        with self.assertRaises(ProtocolValidationError):
            validate_title_ballot(missing)
        with self.assertRaises(ProtocolValidationError):
            validate_title_ballot(_valid_panel(kind="services"))
        with self.assertRaises(TitleBallotPanelError):
            validate_title_ballot(_valid_panel(schema_version=2))
        with self.assertRaises(ProtocolValidationError):
            validate_title_ballot("not-a-panel")

    def test_candidate_field_set_is_exact(self):
        for bad in (
            _candidate(1, extra=1),
            {"index": 1, "display": "破城先鋒"},
            {"index": 1, "basis": "援"},
            {"display": "破城先鋒", "basis": "援"},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ProtocolValidationError):
                    validate_title_ballot(_valid_panel(candidates=[bad]))

    def test_indices_must_be_strictly_one_based_ascending(self):
        for candidates in (
            [_candidate(0)],
            [_candidate(2)],
            [_candidate(1), _candidate(1)],
            [_candidate(2), _candidate(1)],
            [_candidate(1), _candidate(3)],
        ):
            with self.subTest(candidates=candidates):
                with self.assertRaises(ProtocolValidationError):
                    validate_title_ballot(_valid_panel(candidates=candidates))

    def test_more_candidates_than_the_cap_reject(self):
        candidates = [
            _candidate(index) for index in range(1, TITLE_BALLOT_MAX_CANDIDATES + 2)
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_title_ballot(_valid_panel(candidates=candidates))

    def test_display_and_basis_bounds_are_exact(self):
        at_display_cap = _candidate(
            1, display="長" * TITLE_BALLOT_MAX_DISPLAY_CODE_POINTS
        )
        validate_title_ballot(_valid_panel(candidates=[at_display_cap]))
        with self.assertRaises(ProtocolValidationError):
            validate_title_ballot(
                _valid_panel(
                    candidates=[
                        _candidate(
                            1, display="長" * (TITLE_BALLOT_MAX_DISPLAY_CODE_POINTS + 1)
                        )
                    ]
                )
            )
        at_basis_cap = _candidate(1, basis="援" * TITLE_BALLOT_MAX_BASIS_CODE_POINTS)
        validate_title_ballot(_valid_panel(candidates=[at_basis_cap]))
        with self.assertRaises(ProtocolValidationError):
            validate_title_ballot(
                _valid_panel(
                    candidates=[
                        _candidate(
                            1, basis="援" * (TITLE_BALLOT_MAX_BASIS_CODE_POINTS + 1)
                        )
                    ]
                )
            )

    def test_empty_and_non_string_text_fields_reject(self):
        for bad in (
            _candidate(1, display=""),
            _candidate(1, basis=""),
            _candidate(1, display=None),
            _candidate(1, basis=7),
            {"index": True, "display": "破城先鋒", "basis": "率先破門。"},
            {"index": "1", "display": "破城先鋒", "basis": "率先破門。"},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ProtocolValidationError):
                    validate_title_ballot(_valid_panel(candidates=[bad]))

    def test_candidates_must_be_a_list(self):
        with self.assertRaises(ProtocolValidationError):
            validate_title_ballot(_valid_panel(candidates={"1": _CANDIDATE}))

    def test_panel_bounds_mirror_the_rules_writer_caps(self):
        # The wire bounds are owned by world.rules.titles (the single ballot
        # writer validates storage against them); the panel may never ship a
        # payload the storage layer could not have produced.
        self.assertEqual(TITLE_BALLOT_MAX_CANDIDATES, MAX_BALLOT_CANDIDATES)
        self.assertEqual(
            TITLE_BALLOT_MAX_DISPLAY_CODE_POINTS, MAX_EPITHET_DISPLAY_CODE_POINTS
        )
        self.assertEqual(TITLE_BALLOT_MAX_BASIS_CODE_POINTS, BALLOT_BASIS_MAX_CHARS)


class TitleBallotPresenterTests(EvenniaTestCase):
    def setUp(self):
        get_world_clock()
        self.player = create_object(PlayerCharacter, key="ballot presenter")
        self.player.race = "human"
        self.player.apply_race_baseline()

    def _context(self, actor=None):
        return PresentationContext(
            actor=self.player if actor is None else actor, protocol_version=1
        )

    def _render(self, actor=None):
        return build_production_registry().render("title_ballot", self._context(actor))

    def test_absent_ballot_renders_the_zero_candidate_form(self):
        payload = self._render()
        self.assertEqual(
            payload,
            {
                "schema_version": TITLE_BALLOT_SCHEMA_VERSION,
                "available": True,
                "kind": "title_ballot",
                "candidates": [],
            },
        )

    def test_persisted_ballot_renders_one_based_ascending_candidates(self):
        self.assertTrue(
            persist_nomination_ballot(
                self.player,
                [
                    {"display": "破城先鋒", "basis": "率先破門。"},
                    {"display": "夜襲之人", "basis": "夜半三度出入敵陣。"},
                    {"display": "不屈之壁", "basis": "重傷仍守住隘口。"},
                ],
            )
        )
        payload = self._render()
        self.assertEqual(
            [entry["index"] for entry in payload["candidates"]], [1, 2, 3]
        )
        self.assertEqual(payload["candidates"][0]["display"], "破城先鋒")
        self.assertEqual(payload["candidates"][1]["basis"], "夜半三度出入敵陣。")

    def test_basis_renders_verbatim_with_never_a_truncation(self):
        basis = "援" * TITLE_BALLOT_MAX_BASIS_CODE_POINTS
        self.assertTrue(
            persist_nomination_ballot(
                self.player, [{"display": "滿格引用", "basis": basis}]
            )
        )
        payload = self._render()
        self.assertEqual(payload["candidates"][0]["basis"], basis)

    def test_none_actor_renders_the_zero_candidate_form(self):
        payload = self._render(actor=None)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["candidates"], [])

    def test_malformed_ballot_degrades_to_zero_candidates(self):
        self.player.attributes.add(PENDING_BALLOT_KEY, [{"nope": True}])
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["candidates"], [])

    def test_presenter_output_is_the_safe_rules_read_verbatim(self):
        self.assertTrue(persist_nomination_ballot(self.player, [dict(_CANDIDATE)]))
        payload = self._render()
        self.assertEqual(
            payload["candidates"],
            [
                {"index": index, **entry}
                for index, entry in enumerate(safe_pending_ballot(self.player), start=1)
            ],
        )

    def test_registry_spec_owns_the_stable_unavailable_pair(self):
        registry = build_production_registry()
        spec = registry.spec("title_ballot")
        self.assertEqual(spec.schema_version, TITLE_BALLOT_SCHEMA_VERSION)
        self.assertEqual(
            spec.unavailable_reason, ("ballot_unavailable", "異名提名目前無法顯示")
        )
        self.assertEqual(
            registry.build_unavailable("title_ballot"),
            unavailable_payload(
                TITLE_BALLOT_SCHEMA_VERSION,
                "ballot_unavailable",
                "異名提名目前無法顯示",
            ),
        )

    def test_presenter_directly_matches_the_registry_render(self):
        self.assertEqual(title_ballot_presenter(self._context()), self._render())
