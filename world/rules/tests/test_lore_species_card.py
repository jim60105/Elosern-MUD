"""Tests for the canonical stage-gated monster species card (lore-codex-schema-v2).

``species_card`` renders a species at its sighted or defeated research stage.
Every species, variant, tier, rank and region here is a synthetic kit row or
a factory-built row; no shipped key or display string appears.
"""

import unittest

from world.rules.lore_knowledge import (
    DEFEATED_FIELDS,
    SIGHTED_FIELDS,
    LoreKeyError,
    species_card,
)
from world.tests.synthetic_data import (
    make_guild_rank,
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
    make_region,
    synthetic_registries,
)

_SPECIES = "t_card_species"
_DEFAULT = "t_card_default"
_GRADED = "t_card_graded"
_UNGRADED_DANGER = "t_card_unknown_grade"
_STRONGER = "t_card_stronger"
_TIER = "t_card_tier"
_RANK = "t_card_rank"
_REGION_A = "t_card_region_a"
_REGION_B = "t_card_region_b"

_AUTHOR_MARKERS = ("（私密真相標記）", "（私密解釋標記）", "（私密猜想標記）")

_EXTRA = {
    "monster_tiers": {_TIER: make_monster_tier(_TIER, display_name_zh="測卡危級")},
    "guild_ranks": {_RANK: make_guild_rank(_RANK)},
    "regions": {
        _REGION_A: make_region(_REGION_A, display_name_zh="測卡甲地"),
        _REGION_B: make_region(_REGION_B, display_name_zh="測卡乙地"),
    },
    "monster_species": {
        _SPECIES: make_monster_species(
            _SPECIES,
            display_name_zh="測卡獸",
            published_appearance_zh="測卡外觀",
            published_description_zh="測卡描述",
            published_ecology_zh="測卡生態",
            habitat_tags=(_REGION_B, "t_card_missing_region", _REGION_A),
            author_hidden_truth_zh=_AUTHOR_MARKERS[0],
            author_explanation_zh=_AUTHOR_MARKERS[1],
            author_conjecture_zh=_AUTHOR_MARKERS[2],
            default_variant_key=_DEFAULT,
        )
    },
    "monster_variants": {
        _DEFAULT: make_monster_variant(
            _DEFAULT,
            species_key=_SPECIES,
            display_name_zh="測卡常型",
            threat_tier=_TIER,
            ordinary_variant=True,
            danger_grade=None,
        ),
        _STRONGER: make_monster_variant(
            _STRONGER,
            species_key=_SPECIES,
            display_name_zh="測卡強型",
            threat_tier=_TIER,
            ordinary_variant=False,
            danger_grade=None,
        ),
        _GRADED: make_monster_variant(
            _GRADED,
            species_key=_SPECIES,
            display_name_zh="測卡級型",
            threat_tier=_TIER,
            ordinary_variant=True,
            danger_grade=_RANK,
        ),
        _UNGRADED_DANGER: make_monster_variant(
            _UNGRADED_DANGER,
            species_key=_SPECIES,
            display_name_zh="測卡無級型",
            threat_tier=_TIER,
            ordinary_variant=True,
            danger_grade="t_card_absent_rank",
        ),
    },
}


@synthetic_registries(
    "monster_species",
    "monster_variants",
    "monster_tiers",
    "guild_ranks",
    "regions",
    extra=_EXTRA,
)
class SpeciesCardTests(unittest.TestCase):
    def test_sighted_card_carries_only_the_sighted_fields(self):
        card, locked = species_card(_SPECIES, "sighted")
        self.assertEqual(tuple(card), SIGHTED_FIELDS)
        self.assertEqual(
            SIGHTED_FIELDS, ("display_name_zh", "published_appearance_zh", "threat_tier")
        )
        self.assertEqual(
            locked,
            ("published_description_zh", "published_ecology_zh", "habitat_tags", "variants"),
        )
        self.assertEqual(card["display_name_zh"], "測卡獸")
        self.assertEqual(card["published_appearance_zh"], "測卡外觀")
        # Defeated-stage values never ride a sighted card.
        for value in ("測卡描述", "測卡生態", "測卡甲地", "測卡常型"):
            self.assertNotIn(value, "".join(card.values()))

    def test_defeated_card_carries_every_field_in_order(self):
        card, locked = species_card(_SPECIES, "defeated")
        self.assertEqual(tuple(card), SIGHTED_FIELDS + DEFEATED_FIELDS)
        self.assertEqual(len(card), 7)
        self.assertEqual(locked, ())
        self.assertEqual(card["published_description_zh"], "測卡描述")
        self.assertEqual(card["published_ecology_zh"], "測卡生態")

    def test_threat_tier_is_the_default_variant_tier_display_name(self):
        for stage in ("sighted", "defeated"):
            with self.subTest(stage=stage):
                card, _ = species_card(_SPECIES, stage)
                self.assertEqual(card["threat_tier"], "測卡危級")

    def test_variants_list_only_ordinary_variants_with_resolvable_grades(self):
        card, _ = species_card(_SPECIES, "defeated")
        rank_name = make_guild_rank(_RANK).display_name_zh
        # Variant registry order; the stronger (non-ordinary) variant is
        # absent and an unresolvable grade falls back to the bare name.
        self.assertEqual(
            card["variants"].split("\n"),
            ["測卡常型", f"測卡級型・{rank_name}", "測卡無級型"],
        )

    def test_habitat_renders_resolved_region_names_and_skips_unresolvable_tags(self):
        card, _ = species_card(_SPECIES, "defeated")
        self.assertEqual(card["habitat_tags"], "測卡乙地、測卡甲地")
        self.assertNotIn("t_card", card["habitat_tags"])

    def test_author_private_text_appears_at_neither_stage(self):
        for stage in ("sighted", "defeated"):
            card, _ = species_card(_SPECIES, stage)
            text = "".join(card.values())
            for marker in _AUTHOR_MARKERS:
                with self.subTest(stage=stage, marker=marker):
                    self.assertNotIn(marker, text)

    def test_unknown_key_and_unknown_stage_raise_named_errors(self):
        with self.assertRaises(LoreKeyError):
            species_card("t_card_no_such_species", "sighted")
        # The key is checked before the stage.
        with self.assertRaises(LoreKeyError):
            species_card("t_card_no_such_species", "bogus")
        with self.assertRaises(ValueError) as raised:
            species_card(_SPECIES, "bogus")
        self.assertNotIsInstance(raised.exception, LoreKeyError)


if __name__ == "__main__":
    unittest.main()
