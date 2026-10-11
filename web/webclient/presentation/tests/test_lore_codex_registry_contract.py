"""Data-contract test: every registered lore entry is representable by the codex panel

Exercise the production presentation boundary for every legal registry identity.
"""

import unittest
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from world.rules.lore_knowledge import CODE_CATEGORIES


class LoreCodexRegistryContractTests(unittest.TestCase):
    @covers_requirement(
        "webclient-lore-codex-panel::the-lore-codex-panel-is-an-exact-read-only-version-1-presentation-panel"
    )
    def test_every_legal_registry_entry_remains_available_and_identifiable(self):
        registry = build_production_registry()
        for category, codex in CODE_CATEGORIES.items():
            for key, entry in codex.registry.items():
                with self.subTest(category=category, key=key):
                    discovered = {f"{category}:{key}"}
                    actor = SimpleNamespace(
                        pk=42, db=SimpleNamespace(lore_discovered=set(discovered))
                    )
                    payload = registry.render(
                        "lore_codex",
                        PresentationContext(actor=actor, protocol_version=1),
                    )
                    self.assertTrue(payload["available"], (category, key, payload))
                    identities = [
                        (group["key"], row["key"])
                        for group in payload["categories"]
                        for row in group["entries"]
                    ]
                    self.assertEqual(identities, [(category, key)])
                    group = next(
                        group for group in payload["categories"]
                        if group["key"] == category
                    )
                    self.assertEqual(group["entries"][0]["title"], entry.display_name_zh)
                    self.assertEqual(actor.db.lore_discovered, discovered)
