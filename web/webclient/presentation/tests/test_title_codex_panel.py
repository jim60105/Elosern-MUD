"""Exact ``title_codex`` schema and presenter boundary tests (title-codex-removal).

Covers the fourth mirror of the shared bounds (rules read-model owner, panel
validator, JS validator, boundary tests here): at-cap/over-cap rows, the
closed category set, the hint/flavor exclusivity re-asserted on the wire, the
exact available/unavailable field sets, the envelope byte guarantee, the
trim order (trailing epithet rows drop first, then trailing fixed rows, while
the header always describes the full view), the registry's stable unavailable
pair for malformed title state, and the degraded ballot tab.
"""

import unittest
from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
    unavailable_payload,
)
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.title_codex import (
    TITLE_CODEX_BASIS_WIRE_MAX,
    TITLE_CODEX_CATEGORIES,
    TITLE_CODEX_MAX_BALLOT,
    TITLE_CODEX_MAX_BASIS_CODE_POINTS,
    TITLE_CODEX_MAX_DISPLAY_CODE_POINTS,
    TITLE_CODEX_MAX_FULL_TITLE_CODE_POINTS,
    TITLE_CODEX_MAX_ROWS,
    TITLE_CODEX_SCHEMA_VERSION,
    TitleCodexPanelError,
    title_codex_presenter,
    validate_title_codex,
)
from world.lore.titles import FIXED_TITLE_REGISTRY, TitleCategory
from world.rules.title_view import (
    TITLE_MAX_BASIS_CHARS,
    TITLE_MAX_DISPLAY_CHARS,
    TITLE_MAX_ROWS,
)
from world.rules.titles import (
    MAX_FULL_TITLE_CODE_POINTS,
    TITLE_COLLECTION_KEY,
    bank_epithet,
    bank_fixed,
    grant_starter_pair,
)

# Distinguishes "no actor passed" from an explicit None actor.
_UNSET = object()


def _fixed_row(**overrides):
    value = {
        "key": "g_f_rank",
        "display": "F級冒險者",
        "category": "guild",
        "hint": "",
        "flavor": "公會註冊的起點。",
        "unlocked": True,
        "granted_tick": 120,
    }
    value.update(overrides)
    return value


def _epithet_row(**overrides):
    value = {
        "display": "南門新客",
        "basis": "初入南門。",
        "granted_tick": 121,
        "equipped": True,
        "can_remove": False,
    }
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": TITLE_CODEX_SCHEMA_VERSION,
        "available": True,
        "kind": "title_codex",
        "fixed_rows": [_fixed_row()],
        "epithet_rows": [_epithet_row()],
        "equipped": {"fixed": "g_f_rank", "epithet": "南門新客"},
        "full_title": "F級冒險者　南門新客",
        "unlocked": 1,
        "total": len(FIXED_TITLE_REGISTRY),
        "pending_ballot": [],
    }
    value.update(overrides)
    return value


class TitleCodexSchemaTests(unittest.TestCase):
    def test_minimal_payload_normalizes_and_respects_the_envelope(self):
        normalized = validate_title_codex(_valid_panel())
        self.assertEqual(normalized["kind"], "title_codex")
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)

    def test_bounds_mirror_the_rules_read_model_owner(self):
        # The four-mirror contract: the panel may never ship bounds the
        # read model does not own, nor accept a payload it could not build.
        self.assertEqual(TITLE_CODEX_MAX_ROWS, TITLE_MAX_ROWS)
        self.assertEqual(
            TITLE_CODEX_MAX_DISPLAY_CODE_POINTS, TITLE_MAX_DISPLAY_CHARS
        )
        self.assertEqual(TITLE_CODEX_MAX_BASIS_CODE_POINTS, TITLE_MAX_BASIS_CHARS)
        self.assertEqual(
            TITLE_CODEX_MAX_FULL_TITLE_CODE_POINTS, MAX_FULL_TITLE_CODE_POINTS
        )
        # The closed category vocabulary is the full TitleCategory enum,
        # not merely the categories the current registry happens to use.
        self.assertEqual(
            TITLE_CODEX_CATEGORIES,
            frozenset(member.value for member in TitleCategory),
        )

    def test_exact_available_field_set_and_version_discipline(self):
        for bad in (
            {**_valid_panel(), "extra": 1},
            {k: v for k, v in _valid_panel().items() if k != "total"},
            _valid_panel(schema_version=2),
            _valid_panel(available=False),
            _valid_panel(kind="title_ballot"),
        ):
            with self.subTest(bad=str(sorted(bad))[:80]):
                with self.assertRaises(ProtocolValidationError):
                    validate_title_codex(bad)

    def test_row_counts_accept_the_cap_and_reject_over_cap(self):
        at_cap = [_epithet_row(display=f"異名{index}") for index in range(TITLE_CODEX_MAX_ROWS)]
        validate_title_codex(_valid_panel(epithet_rows=at_cap))
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(_valid_panel(epithet_rows=[*at_cap, _epithet_row(display="過界")]))
        fixed_at_cap = [
            _fixed_row(key=f"row_{index}", unlocked=False, hint="提示", flavor="")
            for index in range(TITLE_CODEX_MAX_ROWS)
        ]
        validate_title_codex(
            _valid_panel(
                fixed_rows=fixed_at_cap,
                unlocked=0,
                equipped={"fixed": None, "epithet": "南門新客"},
                full_title="南門新客",
            )
        )
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(_valid_panel(fixed_rows=[*fixed_at_cap, _fixed_row(key="over", unlocked=False, hint="提示", flavor="")]))

    def test_category_closed_set_and_string_caps(self):
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(_valid_panel(fixed_rows=[_fixed_row(category="commerce")]))
        display_cap = "長" * TITLE_CODEX_MAX_DISPLAY_CODE_POINTS
        basis_cap = "援" * TITLE_CODEX_MAX_BASIS_CODE_POINTS
        validate_title_codex(
            _valid_panel(
                full_title="銜" * TITLE_CODEX_MAX_FULL_TITLE_CODE_POINTS,
                epithet_rows=[_epithet_row(display=display_cap, basis=basis_cap)],
            )
        )
        for bad in (
            _epithet_row(display="長" * (TITLE_CODEX_MAX_DISPLAY_CODE_POINTS + 1)),
            _epithet_row(basis="援" * (TITLE_CODEX_MAX_BASIS_CODE_POINTS + 1)),
            _epithet_row(display=""),
            _epithet_row(display=None),
        ):
            with self.subTest(bad=str(sorted(bad))[:60]):
                with self.assertRaises(ProtocolValidationError):
                    validate_title_codex(_valid_panel(epithet_rows=[bad]))
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(
                _valid_panel(full_title="銜" * (TITLE_CODEX_MAX_FULL_TITLE_CODE_POINTS + 1))
            )

    def test_hint_flavor_exclusivity_is_reasserted_on_the_wire(self):
        for bad in (
            # Unlocked rows must not smuggle a hint.
            _fixed_row(unlocked=True, hint="提示"),
            # Locked rows must not smuggle a flavor.
            _fixed_row(unlocked=False, hint="提示", flavor="風味"),
        ):
            with self.subTest(row=str(sorted(bad))[:60]):
                with self.assertRaises(ProtocolValidationError):
                    validate_title_codex(_valid_panel(fixed_rows=[bad]))
        # The legitimate locked form round-trips.
        locked = _fixed_row(unlocked=False, hint="完成公會註冊", flavor="", granted_tick=0)
        normalized = validate_title_codex(
            _valid_panel(fixed_rows=[locked], unlocked=0,
                         equipped={"fixed": None, "epithet": "南門新客"},
                         full_title="南門新客")
        )
        self.assertEqual(normalized["fixed_rows"][0]["hint"], "完成公會註冊")

    def test_counters_equipped_and_ballot_shape(self):
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(_valid_panel(unlocked=8))
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(_valid_panel(equipped={"fixed": "BAD KEY", "epithet": "南門新客"}))
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(_valid_panel(equipped={"fixed": None, "epithet": ""}))
        validate_title_codex(
            _valid_panel(equipped={"fixed": None, "epithet": None}, full_title="")
        )
        entry = {"display": "破城先鋒", "basis": "率先破門。"}
        validate_title_codex(_valid_panel(pending_ballot=[entry]))
        for bad in (
            [{**entry, "index": 1}],
            [{"display": "破城先鋒"}],
            [{"display": "", "basis": "援"}],
            [{"display": "破城先鋒", "basis": "援" * (TITLE_CODEX_BASIS_WIRE_MAX + 1)}],
        ):
            with self.subTest(bad=str(sorted(bad[0]))[:60]):
                with self.assertRaises(ProtocolValidationError):
                    validate_title_codex(_valid_panel(pending_ballot=bad))
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(
                _valid_panel(pending_ballot=[entry] * (TITLE_CODEX_MAX_BALLOT + 1))
            )

    def test_all_ceilings_hand_built_payload_fails_the_envelope(self):
        # The validator enforces the serialized byte size directly, so a
        # hand-built maximal payload fails closed instead of being emitted.
        fixed = [
            _fixed_row(
                key=f"k{index}",
                display="長" * TITLE_CODEX_MAX_DISPLAY_CODE_POINTS,
                unlocked=False,
                hint="援" * TITLE_CODEX_MAX_BASIS_CODE_POINTS,
                flavor="",
            )
            for index in range(TITLE_CODEX_MAX_ROWS)
        ]
        epithets = [
            _epithet_row(
                display=f"異名{index}" + "長" * 40,
                basis="援" * TITLE_CODEX_MAX_BASIS_CODE_POINTS,
            )
            for index in range(TITLE_CODEX_MAX_ROWS)
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_title_codex(
                _valid_panel(fixed_rows=fixed, epithet_rows=epithets, unlocked=0)
            )


class _FakeView:
    """A presenter-level fake carrying cap-respecting fat rows."""

    def __init__(self, fixed, epithets):
        self.fixed_rows = [SimpleNamespace(**row) for row in fixed]
        self.epithet_rows = [SimpleNamespace(**row) for row in epithets]
        self.equipped = {"fixed": None, "epithet": "甲"}
        self.full_title = "甲"
        self.unlocked = 0
        self.total = 7
        self.pending_ballot = ()


class _FakeContext:
    def __init__(self, actor):
        self.actor = actor
        self.protocol_version = 1


def _fat_fixed(index: int) -> dict:
    return {
        "key": f"k{index}",
        "display": "長" * TITLE_CODEX_MAX_DISPLAY_CODE_POINTS,
        "category": "guild",
        "hint": "援" * TITLE_CODEX_MAX_BASIS_CODE_POINTS,
        "flavor": "",
        "unlocked": False,
        "granted_tick": 0,
    }


def _fat_epithet(index: int) -> dict:
    return {
        "display": f"異名{index}",
        "basis": "援" * TITLE_CODEX_MAX_BASIS_CODE_POINTS,
        "granted_tick": index,
        "equipped": False,
        "can_remove": True,
    }


class TitleCodexTrimTests(unittest.TestCase):
    """The declared trim order, exercised on the presenter internals."""

    def _patched_presenter(self, view):
        from unittest.mock import patch

        import web.webclient.presentation.title_codex as module

        with patch.object(module, "build_title_codex_view", return_value=view):
            return module.title_codex_presenter(_FakeContext(object()))

    def test_two_full_fat_lists_trim_epithets_first_fixed_untouched(self):
        # The largest payload a real view can emit: both row lists at the
        # 50-row cap with every string at its ceiling. It overflows the
        # envelope, and the DECLARED order drops trailing epithet rows
        # first — fixed rows stay whole while any epithet row remains.
        view = _FakeView(
            [_fat_fixed(index) for index in range(TITLE_CODEX_MAX_ROWS)],
            [_fat_epithet(index) for index in range(TITLE_CODEX_MAX_ROWS)],
        )
        payload = self._patched_presenter(view)
        self.assertTrue(payload["available"])
        self.assertLess(len(payload["epithet_rows"]), TITLE_CODEX_MAX_ROWS)
        self.assertEqual(len(payload["fixed_rows"]), TITLE_CODEX_MAX_ROWS)
        # The KEPT rows are the leading prefix (newest-first head survives).
        self.assertEqual(
            [row["display"] for row in payload["epithet_rows"]],
            [f"異名{index}" for index in range(len(payload["epithet_rows"]))],
        )
        # The header always describes the FULL untruncated view.
        self.assertEqual(payload["total"], 7)
        self.assertEqual(payload["unlocked"], 0)
        self.assertEqual(payload["full_title"], "甲")
        self.assertEqual(payload["equipped"], {"fixed": None, "epithet": "甲"})
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        self.assertEqual(validate_title_codex(payload), payload)

    def test_within_envelope_payload_is_never_trimmed(self):
        view = _FakeView(
            [_fat_fixed(1)],
            [_fat_epithet(index) for index in range(1, 4)],
        )
        payload = self._patched_presenter(view)
        self.assertEqual(len(payload["fixed_rows"]), 1)
        self.assertEqual(len(payload["epithet_rows"]), 3)

    def test_malformed_state_maps_to_registry_unavailable(self):
        from unittest.mock import patch

        import web.webclient.presentation.title_codex as module
        from web.webclient.presentation.registry import PanelUnavailableError
        from world.rules.title_view import TitleDataError

        with patch.object(
            module, "build_title_codex_view", side_effect=TitleDataError("bad")
        ):
            with self.assertRaises(PanelUnavailableError):
                module.title_codex_presenter(_FakeContext(None))


class TitleCodexPresenterTests(EvenniaTestCase):
    def setUp(self):
        self.player = create_object(PlayerCharacter, key="codex presenter")
        self.player.race = "human"
        self.player.apply_race_baseline()

    def _context(self, actor=_UNSET):
        return PresentationContext(
            actor=self.player if actor is _UNSET else actor, protocol_version=1
        )

    def _render(self, actor=_UNSET):
        return build_production_registry().render("title_codex", self._context(actor))

    def test_fresh_character_renders_the_full_locked_registry(self):
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["fixed_rows"]), len(FIXED_TITLE_REGISTRY))
        self.assertEqual(payload["epithet_rows"], [])
        self.assertEqual(payload["unlocked"], 0)
        self.assertEqual(payload["total"], len(FIXED_TITLE_REGISTRY))
        self.assertEqual(payload["full_title"], "")
        self.assertEqual(payload["equipped"], {"fixed": None, "epithet": None})

    def test_granted_state_renders_verbatim_rows_and_flags(self):
        grant_starter_pair(self.player)
        bank_epithet(self.player, "破城先鋒", "率先破門。", 500)
        payload = self._render()
        self.assertEqual(payload["full_title"], "F級冒險者　南門新客")
        self.assertEqual(payload["equipped"], {"fixed": "g_f_rank", "epithet": "南門新客"})
        self.assertEqual(payload["unlocked"], 1)
        by_display = {row["display"]: row for row in payload["epithet_rows"]}
        # Newest-first: 破城先鋒 (tick 500) precedes the starter (real tick).
        self.assertEqual(
            [row["display"] for row in payload["epithet_rows"]],
            ["破城先鋒", "南門新客"],
        )
        self.assertTrue(by_display["破城先鋒"]["can_remove"])
        self.assertFalse(by_display["南門新客"]["can_remove"])
        self.assertTrue(by_display["南門新客"]["equipped"])
        # Output passes its own validator (self-certifying presenter).
        self.assertEqual(validate_title_codex(payload), payload)

    def test_none_actor_renders_the_registry_unavailable_form(self):
        registry = build_production_registry()
        self.assertEqual(
            registry.render("title_codex", self._context(actor=None)),
            registry.build_unavailable("title_codex"),
        )

    def test_malformed_title_state_renders_the_stable_unavailable_pair(self):
        self.player.attributes.add(TITLE_COLLECTION_KEY, "not-a-list")
        registry = build_production_registry()
        self.assertEqual(
            self._render(),
            unavailable_payload(
                TITLE_CODEX_SCHEMA_VERSION,
                "codex_unavailable",
                "稱號冊目前無法顯示",
            ),
        )

    @covers_requirement("title-system::the-ballot-persists-unchanged-until-consent")
    def test_malformed_ballot_degrades_only_the_ballot_field(self):
        bank_epithet(self.player, "南門新客", "初入南門。", 1)
        self.player.attributes.add("pending_title_ballot", "not-a-ballot")
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["pending_ballot"], [])
        self.assertEqual(
            [row["display"] for row in payload["epithet_rows"]], ["南門新客"]
        )

    def test_registry_spec_owns_the_stable_unavailable_pair(self):
        registry = build_production_registry()
        spec = registry.spec("title_codex")
        self.assertEqual(spec.schema_version, TITLE_CODEX_SCHEMA_VERSION)
        self.assertEqual(
            spec.unavailable_reason, ("codex_unavailable", "稱號冊目前無法顯示")
        )
        self.assertEqual(
            registry.build_unavailable("title_codex"),
            unavailable_payload(
                TITLE_CODEX_SCHEMA_VERSION,
                "codex_unavailable",
                "稱號冊目前無法顯示",
            ),
        )

    def test_presenter_directly_matches_the_registry_render(self):
        grant_starter_pair(self.player)
        self.assertEqual(title_codex_presenter(self._context()), self._render())
