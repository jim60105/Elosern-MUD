"""Tests for the pure compact NPC card contract and validation (D1/D3)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest

from tools.spec_traceability import covers_requirement
from world.lore.npc_card import (
    CARD_BLOCK_LIMIT,
    IDENTITY_SECTION_LIMIT,
    LEAF_LIMIT,
    NPC_CARD_FIELDS,
    NPC_CARD_FORMAT,
    NPC_CARD_RENDER_ORDER,
    NPC_PERSONA_CONTENT_GENERATION,
    OFFLINE_GREETING_LIMIT,
    OPTIONAL_TEXT_LEAVES,
    REQUIRED_TEXT_LEAVES,
    CardBudget,
    NpcCard,
    NpcCardError,
    NpcCardIdentity,
    card_budget,
    normalize_card,
    normalize_offline_greeting,
    render_card_block,
    render_identity_section,
    validate_provenance,
)

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "npc_card_boundary_cases.json"
GREETING_FIXTURES_PATH = Path(__file__).parent / "fixtures" / "npc_offline_greeting_boundary_cases.json"


def greeting_case_input(case: dict) -> object:
    """Build the raw greeting a shared greeting boundary case describes."""
    if "repeat_char" in case:
        return case["repeat_char"] * case["repeat"]
    return case["greeting"]


class NpcCardBoundaryCasesTest(unittest.TestCase):
    """Test boundary and fixture cases for NPC card normalization and validation."""

    def test_import_boundary(self) -> None:
        """Assert world.lore.npc_card imports nothing from Evennia, Django, or world.rules."""
        forbidden_prefixes = ("evennia", "django", "world.rules")
        import world.lore.npc_card as card_mod
        for attr_name in dir(card_mod):
            val = getattr(card_mod, attr_name)
            if hasattr(val, "__module__") and val.__module__:
                mod = val.__module__
                for prefix in forbidden_prefixes:
                    self.assertFalse(
                        mod == prefix or mod.startswith(f"{prefix}."),
                        f"world.lore.npc_card leaks forbidden dependency: {val} from {mod}",
                    )

    @covers_requirement("npc-persona-card::a-compact-npc-card-has-exactly-seven-fields-of-fixed-shape")
    @covers_requirement("npc-persona-card::card-bounds-count-rendered-labels-and-are-never-satisfied-by-truncation")
    @covers_requirement("npc-persona-card::card-text-is-normalized-plain-text")
    def test_fixture_cases(self) -> None:
        """Run all test cases defined in npc_card_boundary_cases.json."""
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cases = json.load(f)

        for case in cases:
            with self.subTest(case=case["name"]):
                raw = dict(case["card"])

                # Handle dynamic construction flags
                if case.get("use_astral_600_field"):
                    # 600 astral code points: e.g. U+1F600 😀 (len=1 code point in Python)
                    field = case["use_astral_600_field"]
                    raw[field] = "😀" * 600

                elif case.get("use_leaf_601_field"):
                    field = case["use_leaf_601_field"]
                    raw[field] = "A" * 601

                elif case.get("override_identity_overflow"):
                    # Each leaf <= 600, but identity section rendered > 600
                    raw["identity"] = {
                        "public": "公" * 300,
                        "hidden": "隱" * 300,
                    }

                elif case.get("override_total_overflow"):
                    # Rendered total > 2000
                    raw["identity"] = {"public": "公開", "hidden": "隱秘"}
                    for f_key in ("appearance", "personality", "speech_style", "life_story", "habit", "social_connection"):
                        raw[f_key] = "字" * 330

                elif case.get("override_all_leaves_600"):
                    # All leaves at 600 code points
                    raw["identity"] = {"public": "公" * 600, "hidden": "隱" * 600}
                    for f_key in ("appearance", "personality", "speech_style", "life_story", "habit", "social_connection"):
                        raw[f_key] = "字" * 600

                if case["expected_valid"]:
                    card = normalize_card(raw)
                    self.assertIsInstance(card, NpcCard)
                    if "expected_public" in case:
                        self.assertEqual(card.identity.public, case["expected_public"])
                    if "expected_hidden" in case:
                        self.assertEqual(card.identity.hidden, case["expected_hidden"])
                    if "expected_appearance" in case:
                        self.assertEqual(card.appearance, case["expected_appearance"])
                    if "expected_social_connection" in case:
                        self.assertEqual(card.social_connection, case["expected_social_connection"])
                    if "expected_total" in case:
                        # The browser mirror asserts the same rendered total
                        # (label parity, design D6b).
                        self.assertEqual(card_budget(card).total, case["expected_total"])
                else:
                    with self.assertRaises(NpcCardError) as ctx:
                        normalize_card(raw)
                    self.assertEqual(ctx.exception.code, case["expected_code"])
                    self.assertEqual(ctx.exception.field, case["expected_field"])

    @covers_requirement("npc-persona-editor::the-browser-mirrors-the-card-contract-exactly")
    def test_offline_greeting_fixture_cases(self) -> None:
        """Every shared greeting boundary case yields the decision the mirror also asserts."""
        with open(GREETING_FIXTURES_PATH, "r", encoding="utf-8") as f:
            cases = json.load(f)
        self.assertEqual(OFFLINE_GREETING_LIMIT, 300)
        for case in cases:
            with self.subTest(case=case["name"]):
                raw = greeting_case_input(case)
                if case["expected_valid"]:
                    normalized = normalize_offline_greeting(raw)
                    expected = case.get("expected", raw)
                    self.assertEqual(normalized, expected)
                else:
                    with self.assertRaises(NpcCardError) as ctx:
                        normalize_offline_greeting(raw)
                    self.assertEqual(ctx.exception.code, "greeting_invalid")
                    self.assertEqual(ctx.exception.field, "offline_greeting")

    def test_voice_line_limit_tracks_the_offline_greeting_bound(self) -> None:
        """An authored greeting must always fit the editable field it defaults."""
        from world.lore.npc_profiles.shape import VOICE_LINE_LIMIT

        self.assertEqual(VOICE_LINE_LIMIT, OFFLINE_GREETING_LIMIT)

    def test_budget_calculation(self) -> None:
        """Assert card_budget calculates per-leaf, identity section, and remaining correctly."""
        raw = {
            "identity": {"public": "侍者", "hidden": ""},
            "appearance": "金髮",
            "personality": "熱情",
            "speech_style": "禮貌",
            "life_story": "生於王都",
            "habit": "端茶",
            "social_connection": "",
        }
        card = normalize_card(raw)
        budget = card_budget(card)
        self.assertIsInstance(budget, CardBudget)
        self.assertEqual(budget.per_leaf["identity.public"], 2)
        self.assertEqual(budget.per_leaf["identity.hidden"], 0)
        self.assertEqual(budget.per_leaf["social_connection"], 0)
        rendered = render_card_block(card)
        self.assertEqual(budget.total, len(rendered))
        self.assertEqual(budget.remaining_total, CARD_BLOCK_LIMIT - len(rendered))

    def test_provenance_validation(self) -> None:
        """Validate allowed and rejected provenance dictionaries."""
        # Valid cases
        valid_cases = [
            {"kind": "profile", "profile": "innkeeper_01"},
            {"kind": "companion", "profile": "companion_elena", "owner": 42},
            {"kind": "import", "record": "import_npc_20261001"},
            {"kind": "generated_quest", "quest": "q_goblin_01", "stage": 2, "occupant": 1},
        ]
        for prov in valid_cases:
            res = validate_provenance(prov)
            self.assertEqual(res, prov)

        # Invalid cases
        invalid_cases = [
            ("not_dict", "string"),
            ("unknown_kind", {"kind": "magic_spawn"}),
            ("retired_offline_bundle", {"kind": "offline_bundle", "pool": "pool_adventurers", "bundle": "b_01"}),
            ("prose_in_field", {"kind": "profile", "profile": "x" * 200}),
            ("bool_in_owner", {"kind": "companion", "profile": "c1", "owner": True}),
            ("negative_int", {"kind": "generated_quest", "quest": "q", "stage": -1, "occupant": 0}),
            ("extra_field", {"kind": "profile", "profile": "p1", "extra": "val"}),
            ("missing_field", {"kind": "companion", "profile": "c1"}),
        ]
        for name, bad_prov in invalid_cases:
            with self.subTest(case=name):
                with self.assertRaises(NpcCardError):
                    validate_provenance(bad_prov)
