"""Pure tests for the lore codex writer and readers (lore-knowledge-codex).

Covers the closed category-to-registry mapping, the append-only sole writer
(repeat no-op, unknown category and unresolvable-key rejection, subrace-under-
race rejection), the deterministic discovered-only listing with corrupt-record
degradation, per-category card rendering, the named errors, and the
sole-writer boundary (no other module writes ``lore_discovered``).
"""

import unittest

from tools.spec_traceability import covers_requirement

from world.lore.anchors import ANCHOR_REGISTRY
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.magic import MAGIC_TIER_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.nations import NATION_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
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


EXPECTED_REGISTRIES = {
    "race": RACE_REGISTRY,
    "nation": NATION_REGISTRY,
    "region": WILDERNESS_REGION_REGISTRY,
    "monster": MONSTER_TIER_REGISTRY,
    "element": ELEMENT_REGISTRY,
    "magic": MAGIC_TIER_REGISTRY,
    "anchor": ANCHOR_REGISTRY,
    "guild": GUILD_RANK_REGISTRY,
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


class CodexMappingTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::the-codex-defines-a-closed-category-to-registry-mapping")
    def test_every_category_resolves_to_exactly_one_registry(self):
        self.assertEqual(set(CODE_CATEGORIES), set(EXPECTED_REGISTRIES))
        for category, registry in EXPECTED_REGISTRIES.items():
            with self.subTest(category=category):
                self.assertIs(CODE_CATEGORIES[category].registry, registry)
                self.assertEqual(
                    CODE_CATEGORIES[category].card_fields,
                    EXPECTED_CARD_FIELDS[category],
                )

    @covers_requirement("lore-knowledge::the-codex-defines-a-closed-category-to-registry-mapping")
    def test_a_key_is_validated_against_its_category_registry(self):
        player = _player()
        record_lore_reveal(player, "race", "elf")
        self.assertEqual(player.db.lore_discovered, {"race:elf"})

    @covers_requirement("lore-knowledge::the-codex-defines-a-closed-category-to-registry-mapping")
    def test_a_subrace_key_is_not_a_race_entry(self):
        from world.lore.races import SUBRACE_REGISTRY

        self.assertIn("ciaran", SUBRACE_REGISTRY)
        self.assertNotIn("ciaran", RACE_REGISTRY)
        player = _player()
        with self.assertRaises(LoreKeyError):
            record_lore_reveal(player, "race", "ciaran")
        self.assertIsNone(player.db.lore_discovered)


class SoleWriterTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::the-codex-stores-discovered-entries-append-only-under-one-sole-writer")
    def test_first_reveal_records_the_namespaced_entry(self):
        player = _player()
        record_lore_reveal(player, "race", "elf")
        self.assertEqual(player.db.lore_discovered, {"race:elf"})

    @covers_requirement("lore-knowledge::the-codex-stores-discovered-entries-append-only-under-one-sole-writer")
    def test_repeat_reveal_is_a_no_op(self):
        player = _player()
        record_lore_reveal(player, "nation", "grandia")
        record_lore_reveal(player, "nation", "grandia")
        self.assertEqual(player.db.lore_discovered, {"nation:grandia"})

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
            record_lore_reveal(player, "race", "elf")
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


class ListingTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::the-codex-reader-returns-a-deterministic-listing-of-discovered-entries")
    def test_listing_is_deterministic_and_discovered_only(self):
        player = _player()
        record_lore_reveal(player, "race", "elf")
        record_lore_reveal(player, "region", "eastern_plains")
        record_lore_reveal(player, "guild", "F")
        record_lore_reveal(player, "race", "human")
        self.assertEqual(
            list_discovered(player),
            (
                ("race", "elf"),
                ("race", "human"),
                ("region", "eastern_plains"),
                ("guild", "F"),
            ),
        )

    def test_no_record_lists_as_empty(self):
        self.assertEqual(list_discovered(_player()), ())

    @covers_requirement("lore-knowledge::the-codex-reader-returns-a-deterministic-listing-of-discovered-entries")
    def test_corrupt_record_degrades_without_reset_or_fabrication(self):
        for corrupt in (
            "not-a-set",
            {"race:elf", 42},
            {"elf"},
            {"race:elf", "bogus:x"},
            {"race:elf", "race:unresolvable"},
        ):
            with self.subTest(record=corrupt):
                player = _player(lore_discovered=corrupt)
                with self.assertRaises(LoreRecordError):
                    list_discovered(player)
                self.assertEqual(player.db.lore_discovered, corrupt)


class CardRenderingTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::each-category-renders-its-own-player-facing-card")
    def test_race_card_renders_key_and_description(self):
        card = lore_card("race", "elf")
        self.assertEqual(
            card, {"key": "elf", "description": RACE_REGISTRY["elf"].description}
        )

    @covers_requirement("lore-knowledge::each-category-renders-its-own-player-facing-card")
    def test_region_card_includes_terrain_flavor_entries(self):
        card = lore_card("region", "eastern_plains")
        self.assertEqual(card["display_name_zh"], "東部大平原")
        self.assertIn(
            "一望無際的麥田隨風起伏", card["terrain_flavor_zh"]
        )
        self.assertEqual(
            len(card["terrain_flavor_zh"].splitlines()),
            len(WILDERNESS_REGION_REGISTRY["eastern_plains"].terrain_flavor_zh),
        )

    def test_nation_card_renders_display_name_and_capital(self):
        card = lore_card("nation", "grandia")
        self.assertEqual(card["display_name_zh"], "格蘭迪亞帝國")
        self.assertEqual(card["capital_anchor_key"], "capital_grandia")

    def test_monster_card_renders_examples_as_entries(self):
        card = lore_card("monster", "low")
        self.assertEqual(card["display_name_zh"], "低階")
        self.assertIn("史萊姆", card["example_monsters_zh"])

    def test_guild_card_renders_key_and_description(self):
        card = lore_card("guild", "F")
        self.assertEqual(card["key"], "F")
        self.assertEqual(card["description"], GUILD_RANK_REGISTRY["F"].description)

    def test_every_category_card_renders_exactly_its_declared_fields(self):
        entries = {
            "race": "elf",
            "nation": "grandia",
            "region": "eastern_plains",
            "monster": "low",
            "element": "fire",
            "magic": "apprentice",
            "anchor": "capital_grandia",
            "guild": "F",
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
