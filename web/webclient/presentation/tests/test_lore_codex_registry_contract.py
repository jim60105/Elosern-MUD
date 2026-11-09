"""Data-contract test: every registered lore entry is representable by the codex panel

Exercise the production presentation boundary for every legal registry identity,
and every shipped species' defeated card against the panel's card bounds.
"""

import unittest
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.lore_codex import (
    LORE_CODEX_MAX_CARD_FIELDS,
    LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS,
    LORE_CODEX_MAX_TITLE_CODE_POINTS,
    LORE_CODEX_MAX_VARIANT_LINES,
)
from web.webclient.presentation.registry import build_production_registry
from world.rules.lore_knowledge import CODE_CATEGORIES, species_card
from world.tests.geography_fixture import GeographyPublicationMixin


class LoreCodexRegistryContractTests(GeographyPublicationMixin, unittest.TestCase):
    """Every map-owned category reads the published shipped map world."""

    @covers_requirement(
        "webclient-lore-codex-panel::the-lore-codex-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_every_legal_registry_entry_remains_available_and_identifiable(self):
        registry = build_production_registry()
        for category, codex in CODE_CATEGORIES.items():
            for key, entry in codex.registry.items():
                with self.subTest(category=category, key=key):
                    discovered = {f"{category}:{key}"}
                    actor = SimpleNamespace(
                        pk=42,
                        db=SimpleNamespace(
                            lore_discovered=set(discovered), lore_species_defeated=None
                        ),
                    )
                    payload = registry.render(
                        "lore_codex",
                        PresentationContext(actor=actor, protocol_version=1),
                    )
                    self.assertTrue(payload["available"], (category, key, payload))
                    entries = [
                        (group["key"], slot)
                        for group in payload["categories"]
                        for tier in group["groups"]
                        for slot in tier["slots"]
                        if "key" in slot
                    ]
                    self.assertEqual(
                        [(group, slot["key"]) for group, slot in entries], [(category, key)]
                    )
                    self.assertEqual(entries[0][1]["title"], entry.display_name_zh)
                    self.assertEqual(actor.db.lore_discovered, discovered)

    def test_every_shipped_species_defeated_card_fits_the_panel_bounds(self):
        for key in CODE_CATEGORIES["monster"].registry:
            with self.subTest(species=key):
                card, locked = species_card(key, "defeated")
                self.assertEqual(locked, ())
                self.assertLessEqual(len(card), LORE_CODEX_MAX_CARD_FIELDS)
                self.assertTrue(card["display_name_zh"].strip())
                self.assertLessEqual(
                    len(card["display_name_zh"]), LORE_CODEX_MAX_TITLE_CODE_POINTS
                )
                for name, value in card.items():
                    self.assertLessEqual(
                        len(value), LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS, name
                    )
                self.assertLessEqual(
                    len(card["variants"].split("\n")), LORE_CODEX_MAX_VARIANT_LINES
                )
