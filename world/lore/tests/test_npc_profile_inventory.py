"""Data-contract test: shipped NPC source inventory data contract
Derives the actual NPC source set from the live registries and example files
and asserts it matches ``NPC_SOURCE_INVENTORY`` -- a source without an owner,
or an inventory row naming a source that no longer exists, fails this check.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tools.spec_traceability import covers_requirement

import world.imports.examples as _examples_pkg
from world.ai.director_templates import QUEST_TEMPLATE_POOL
from world.lore.dialogue import DIALOGUE_ROWS
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.npc_profiles.inventory import NPC_SOURCE_INVENTORY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY

EXAMPLES_DIR = Path(_examples_pkg.__file__).resolve().parent

# The nine owning content-change slice labels bound in design.md D1.
OWNER_LABELS = frozenset(
    {
        "altoria_lower",
        "altoria_trade",
        "altoria_guild",
        "altoria_upper",
        "ciaran_homes_a",
        "ciaran_homes_b",
        "companions",
        "generated_quest_cards",
        "import_cards",
    }
)

# The six closed source kinds (design.md D1).
SOURCE_KINDS = frozenset(
    {
        "place_host",
        "dialogue_table",
        "guild_examiner",
        "starting_companion",
        "quest_template_occupant",
        "import_example",
    }
)


class NpcSourceInventoryContractTests(unittest.TestCase):
    """The inventory and the live registries name exactly the same sources."""

    @classmethod
    def setUpClass(cls):
        cls.actual = cls._derive_actual_sources()
        cls.inventory_pairs = {(row.kind, row.key) for row in NPC_SOURCE_INVENTORY}

    @staticmethod
    def _derive_actual_sources() -> set[tuple[str, str]]:
        actual: set[tuple[str, str]] = set()

        for place in PLACE_REGISTRY.values():
            if place.service_id is not None:
                actual.add(("place_host", place.service_id))

        # Every merchant/attendant host's dialogue_key authored kwarg is this
        # place's own answer to "which dialogue table is mine"; it must name
        # exactly the DIALOGUE_ROWS keys, with nothing orphaned on either side.
        dialogue_keys_from_places = {
            value
            for place in PLACE_REGISTRY.values()
            for kwarg_key, value in place.authored_kwargs
            if kwarg_key == "dialogue_key"
        }
        if dialogue_keys_from_places != set(DIALOGUE_ROWS):
            raise AssertionError(
                "place authored_kwargs dialogue_key values diverge from DIALOGUE_ROWS: "
                f"only in places={dialogue_keys_from_places - set(DIALOGUE_ROWS)}, "
                f"only in DIALOGUE_ROWS={set(DIALOGUE_ROWS) - dialogue_keys_from_places}"
            )
        actual.update(("dialogue_table", key) for key in DIALOGUE_ROWS)

        actual.update(("guild_examiner", key) for key in GUILD_RANK_REGISTRY)

        for preset in PLAYER_PRESET_REGISTRY.values():
            for companion in preset.starting_companions:
                actual.add(
                    ("starting_companion", f"{preset.key}:{companion.preset_key}")
                )

        for template in QUEST_TEMPLATE_POOL:
            for stage in template.stages:
                for position, _npc_req in enumerate(stage.npc_reqs):
                    actual.add(
                        (
                            "quest_template_occupant",
                            f"{template.name}:{stage.index}:{position}",
                        )
                    )

        actual.update(
            ("import_example", path.stem) for path in EXAMPLES_DIR.glob("*.json")
        )

        return actual

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-source-inventory-enumerates-every-source-with-an-owner"
    )
    def test_inventory_matches_the_live_registries(self):
        missing = sorted(self.actual - self.inventory_pairs)
        extra = sorted(self.inventory_pairs - self.actual)
        self.assertEqual(
            (missing, extra),
            ([], []),
            f"missing from inventory: {missing}; extra in inventory (no longer exists): {extra}",
        )

    def test_every_row_names_one_of_the_nine_owners(self):
        for row in NPC_SOURCE_INVENTORY:
            with self.subTest(kind=row.kind, key=row.key):
                self.assertIn(row.owner, OWNER_LABELS)

    def test_every_row_names_one_of_the_six_kinds(self):
        for row in NPC_SOURCE_INVENTORY:
            with self.subTest(kind=row.kind, key=row.key):
                self.assertIn(row.kind, SOURCE_KINDS)
