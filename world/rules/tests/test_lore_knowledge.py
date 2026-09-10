"""Pure tests for the lore codex writer and readers (lore-knowledge-codex).

Covers the closed category-to-registry mapping, the append-only sole writer
(repeat no-op, unknown category and unresolvable-key rejection, subrace-under-
race rejection), the deterministic discovered-only listing with corrupt-record
degradation, per-category card rendering, the named errors, and the
sole-writer boundary (no other module writes ``lore_discovered``).

Runs against the synthetic lore-catalog family (data independence): every
codex registry is scoped to kit rows, and the mapping-identity checks resolve
the CURRENT registry objects at runtime.
"""

import unittest

from tools.spec_traceability import covers_requirement

from world.rules.lore_knowledge import (
    CODE_CATEGORIES,
    LoreCategoryError,
    LoreKeyError,
    LoreRecordError,
    KNOWLEDGE_ATTR,
    list_discovered,
    lore_card,
    record_lore_reveal,
)
from world.tests.synthetic_data import synthetic_registries

from ._knowledge_probes import (
    live_anchor_registry,
    live_element_registry,
    live_guild_rank_registry,
    live_magic_tier_registry,
    live_monster_tier_registry,
    live_nation_registry,
    live_race_registry,
    live_region_registry,
    live_subrace_registry,
)


def _expected_registries():
    """The CURRENT registry object per codex category (runtime lookups)."""
    return {
        "race": live_race_registry(),
        "nation": live_nation_registry(),
        "region": live_region_registry(),
        "monster": live_monster_tier_registry(),
        "element": live_element_registry(),
        "magic": live_magic_tier_registry(),
        "anchor": live_anchor_registry(),
        "guild": live_guild_rank_registry(),
    }


EXPECTED_CARD_FIELDS = {
    "race": ("key", "description"),
    "nation": ("display_name_zh", "capital_anchor_key"),
    "region": ("display_name_zh", "terrain_flavor_zh"),
    "monster": ("display_name_zh", "description", "example_monsters_zh"),
    "element": ("display_name_zh", "description"),
    "magic": ("display_name_zh", "description"),
    "anchor": ("display_name_zh", "description"),
    "guild": ("key", "description"),
}


def _first_key(registry):
    """The first key of a live registry (deterministic insertion order)."""
    return next(iter(registry))


class _StubDb:
    """Evennia-like ``db`` attribute surface: missing attributes read as None."""

    def __getattr__(self, name):
        return None


class _Stub:
    """A minimal player stand-in exposing only the ``db`` attribute surface."""

    def __init__(self):
        self.db = _StubDb()


def _player(**attrs):
    stub = _Stub()
    for key, value in attrs.items():
        setattr(stub.db, key, value)
    return stub


_LORE_LOGICALS = (
    "races",
    "subraces",
    "nations",
    "regions",
    "monster_tiers",
    "elements",
    "magic_tiers",
    "anchors",
    "guild_ranks",
)


@synthetic_registries(*_LORE_LOGICALS)
class CodexMappingTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::the-codex-defines-a-closed-category-to-registry-mapping")
    def test_every_category_resolves_to_exactly_one_registry(self):
        expected = _expected_registries()
        self.assertEqual(set(CODE_CATEGORIES), set(expected))
        for category, registry in expected.items():
            with self.subTest(category=category):
                self.assertIs(CODE_CATEGORIES[category].registry, registry)
                self.assertEqual(
                    CODE_CATEGORIES[category].card_fields,
                    EXPECTED_CARD_FIELDS[category],
                )

    @covers_requirement("lore-knowledge::the-codex-defines-a-closed-category-to-registry-mapping")
    def test_a_key_is_validated_against_its_category_registry(self):
        race = _first_key(live_race_registry())
        player = _player()
        record_lore_reveal(player, "race", race)
        self.assertEqual(player.db.lore_discovered, {f"race:{race}"})

    @covers_requirement("lore-knowledge::the-codex-defines-a-closed-category-to-registry-mapping")
    def test_a_subrace_key_is_not_a_race_entry(self):
        subraces = live_subrace_registry()
        subrace = _first_key(subraces)
        self.assertIn(subrace, subraces)
        self.assertNotIn(subrace, live_race_registry())
        player = _player()
        with self.assertRaises(LoreKeyError):
            record_lore_reveal(player, "race", subrace)
        self.assertIsNone(player.db.lore_discovered)


@synthetic_registries(*_LORE_LOGICALS)
class SoleWriterTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::the-codex-stores-discovered-entries-append-only-under-one-sole-writer")
    def test_first_reveal_records_the_namespaced_entry(self):
        race = _first_key(live_race_registry())
        player = _player()
        record_lore_reveal(player, "race", race)
        self.assertEqual(player.db.lore_discovered, {f"race:{race}"})

    @covers_requirement("lore-knowledge::the-codex-stores-discovered-entries-append-only-under-one-sole-writer")
    def test_repeat_reveal_is_a_no_op(self):
        nation = _first_key(live_nation_registry())
        player = _player()
        record_lore_reveal(player, "nation", nation)
        record_lore_reveal(player, "nation", nation)
        self.assertEqual(player.db.lore_discovered, {f"nation:{nation}"})

    @covers_requirement("lore-knowledge::the-codex-stores-discovered-entries-append-only-under-one-sole-writer")
    def test_unknown_category_rejects_without_change(self):
        player = _player()
        with self.assertRaises(LoreCategoryError):
            record_lore_reveal(player, "bogus", "x")
        self.assertIsNone(player.db.lore_discovered)

    def test_unresolvable_key_rejects_without_change(self):
        player = _player()
        with self.assertRaises(LoreKeyError):
            record_lore_reveal(player, "element", "bogus")
        self.assertIsNone(player.db.lore_discovered)

    def test_corrupt_record_rejects_instead_of_resetting(self):
        player = _player(lore_discovered={42})
        with self.assertRaises(LoreRecordError):
            record_lore_reveal(player, "race", _first_key(live_race_registry()))
        self.assertEqual(player.db.lore_discovered, {42})

    @covers_requirement("lore-knowledge::the-codex-stores-discovered-entries-append-only-under-one-sole-writer")
    def test_no_other_module_writes_the_codex_record(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        writer = root / "rules" / "lore_knowledge.py"
        references = []
        for path in sorted(root.rglob("*.py")):
            if "/tests/" in str(path) or "/__pycache__/" in str(path):
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if "lore_discovered" in line:
                    references.append(
                        f"{path.relative_to(root)}:{lineno}:{line.strip()}"
                    )
        outside = [
            reference
            for reference in references
            if not reference.startswith("rules/lore_knowledge.py")
        ]
        self.assertEqual(outside, [])
        self.assertTrue(any("lore_discovered" in line for line in references))


@synthetic_registries(*_LORE_LOGICALS)
class ListingTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::the-codex-reader-returns-a-deterministic-listing-of-discovered-entries")
    def test_listing_is_deterministic_and_discovered_only(self):
        race = _first_key(live_race_registry())
        region = _first_key(live_region_registry())
        guild = _first_key(live_guild_rank_registry())
        glowmire, borrowed = tuple(live_element_registry())
        player = _player()
        record_lore_reveal(player, "race", race)
        record_lore_reveal(player, "region", region)
        record_lore_reveal(player, "guild", guild)
        record_lore_reveal(player, "element", borrowed)
        record_lore_reveal(player, "element", glowmire)
        # Listing groups by category in CODE_CATEGORIES order, keys sorted.
        self.assertEqual(
            list_discovered(player),
            (
                ("race", race),
                ("region", region),
                ("element", min(glowmire, borrowed)),
                ("element", max(glowmire, borrowed)),
                ("guild", guild),
            ),
        )

    def test_no_record_lists_as_empty(self):
        self.assertEqual(list_discovered(_player()), ())

    @covers_requirement("lore-knowledge::the-codex-reader-returns-a-deterministic-listing-of-discovered-entries")
    def test_corrupt_record_degrades_without_reset_or_fabrication(self):
        race = _first_key(live_race_registry())
        good = f"race:{race}"
        for corrupt in (
            "not-a-set",
            {good, 42},
            {race},
            {good, "bogus:x"},
            {good, "race:unresolvable"},
        ):
            with self.subTest(record=corrupt):
                player = _player(lore_discovered=corrupt)
                with self.assertRaises(LoreRecordError):
                    list_discovered(player)
                self.assertEqual(player.db.lore_discovered, corrupt)


@synthetic_registries(*_LORE_LOGICALS)
class CardRenderingTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::each-category-renders-its-own-player-facing-card")
    def test_race_card_renders_key_and_description(self):
        race = _first_key(live_race_registry())
        card = lore_card("race", race)
        self.assertEqual(
            card,
            {"key": race, "description": live_race_registry()[race].description},
        )

    @covers_requirement("lore-knowledge::each-category-renders-its-own-player-facing-card")
    def test_region_card_includes_terrain_flavor_entries(self):
        regions = live_region_registry()
        region = _first_key(regions)
        card = lore_card("region", region)
        self.assertEqual(card["display_name_zh"], regions[region].display_name_zh)
        self.assertIn(
            regions[region].terrain_flavor_zh[0], card["terrain_flavor_zh"]
        )
        self.assertEqual(
            len(card["terrain_flavor_zh"].splitlines()),
            len(regions[region].terrain_flavor_zh),
        )

    def test_nation_card_renders_display_name_and_capital(self):
        nations = live_nation_registry()
        nation = _first_key(nations)
        card = lore_card("nation", nation)
        self.assertEqual(card["display_name_zh"], nations[nation].display_name_zh)
        self.assertEqual(
            card["capital_anchor_key"], nations[nation].capital_anchor_key
        )

    def test_monster_card_renders_examples_as_entries(self):
        tiers = live_monster_tier_registry()
        tier = _first_key(tiers)
        card = lore_card("monster", tier)
        self.assertEqual(card["display_name_zh"], tiers[tier].display_name_zh)
        self.assertIn(tiers[tier].example_monsters_zh[0], card["example_monsters_zh"])

    def test_guild_card_renders_key_and_description(self):
        ranks = live_guild_rank_registry()
        rank = _first_key(ranks)
        card = lore_card("guild", rank)
        self.assertEqual(card["key"], rank)
        self.assertEqual(card["description"], ranks[rank].description)

    def test_every_category_card_renders_exactly_its_declared_fields(self):
        entries = {
            "race": _first_key(live_race_registry()),
            "nation": _first_key(live_nation_registry()),
            "region": _first_key(live_region_registry()),
            "monster": _first_key(live_monster_tier_registry()),
            "element": _first_key(live_element_registry()),
            "magic": _first_key(live_magic_tier_registry()),
            "anchor": _first_key(live_anchor_registry()),
            "guild": _first_key(live_guild_rank_registry()),
        }
        for category, key in entries.items():
            with self.subTest(category=category):
                card = lore_card(category, key)
                self.assertEqual(
                    tuple(card), CODE_CATEGORIES[category].card_fields
                )
                self.assertTrue(all(isinstance(value, str) for value in card.values()))
                self.assertTrue(all(value for value in card.values()))

    @covers_requirement("lore-knowledge::each-category-renders-its-own-player-facing-card")
    def test_unresolvable_key_raises_a_named_error(self):
        with self.assertRaises(LoreKeyError):
            lore_card("race", "bogus")

    def test_unknown_category_raises_a_named_error(self):
        with self.assertRaises(LoreCategoryError):
            lore_card("bogus", "elf")


if __name__ == "__main__":
    unittest.main()
