"""Clean-process startup smokes for the single authored item catalog.

Evidence for the archived consolidate-item-authoring task 1.2: each case copies
the shipped ``content/items/`` catalog to a temporary directory, appends one
malformed row, and runs the real loaders through the startup's own
``equipment_rulebook_validation`` step in a fresh interpreter. The smoke drives
publication (the item loader), the two effect loaders through the production
startup gate, and the real ``at_server_start`` hook up to a sentinel installed
at ``sync_map_world``; a rejection must arrive before that sentinel.

The startup steps before the gate (map adoption, rite adoption, clock init) are
replaced with no-ops and the one at ``sync_map_world`` records a sentinel, so a
failure can only come from the real item validator and persistence, network,
and map-freshness work never runs. The shipped files are snapshotted and must
stay byte-identical.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_CATALOG = REPOSITORY_ROOT / "content" / "items"

_SCRIPT = r'''
import os
import sys
from pathlib import Path

case, catalog, repository_root = sys.argv[1:4]
sys.path.insert(0, repository_root)
os.environ["DJANGO_SETTINGS_MODULE"] = "server.conf.settings"

import django

django.setup()
import evennia

evennia._init(portal_mode=True)

from server.conf.at_server_startstop import (
    STARTUP_STEP_ORDER,
    at_server_start,
)

gate_position = STARTUP_STEP_ORDER.index("equipment_rulebook_validation")
sync_position = STARTUP_STEP_ORDER.index("sync_map_world")
assert gate_position < sync_position, "the item gate must precede sync_map_world"

from unittest.mock import patch

import world.lore.items as package
import world.lore.items.assembly as assembly

reached_sync = []


def _isolated_step():
    """Stand-in for unrelated adoption, clock, and synchronization work."""


def _sync_map_world():
    reached_sync.append(True)


try:
    candidate = assembly.load_item_catalog(Path(catalog))
    package.ITEM_REGISTRY = candidate.definitions
    package.ITEM_SOURCES = candidate.sources
    package.ITEM_USE_EFFECT_INPUTS = candidate.use_effect_inputs
    package.ITEM_EQUIPMENT_EFFECT_INPUTS = candidate.equipment_effect_inputs
    with (
        patch("world.maps.runtime.adopt", _isolated_step),
        patch("world.maps.runtime.synchronize", _sync_map_world),
        patch("world.lore.rites.load_published", _isolated_step),
        patch("world.rules.clock.get_world_clock", _isolated_step),
    ):
        at_server_start()
except ValueError as error:
    print("REJECTED", type(error).__name__, flush=True)
    print("MESSAGE", str(error), flush=True)
else:
    print("NOT_REJECTED", case, flush=True)
    raise SystemExit(3)

print("SYNC_REACHED", bool(reached_sync), flush=True)
if reached_sync:
    raise SystemExit(4)
'''

_MALFORMED_ROW = """  - key: t_probe_row
    display_name_zh: 探針列
    price_table_key: t_meal
    sellable: sometimes
    presentation:
      kind: misc
      icon_key: misc
      rarity: common
      summary_zh: 合成探針列摘要。
"""

_MALFORMED_USE_EFFECT = """  - key: t_probe_usable
    display_name_zh: 探針藥水
    price_table_key: t_meal
    sellable: true
    presentation:
      kind: misc
      icon_key: misc
      rarity: common
      summary_zh: 合成探針藥水摘要。
    use_mechanics:
      consumable: true
      combat_allowed: true
      effects:
        - stat: luck
          amount: 1
"""

_MALFORMED_EQUIPMENT_EFFECT = """  - key: t_probe_armor
    display_name_zh: 探針護甲
    price_table_key: t_meal
    sellable: true
    presentation:
      kind: armor
      icon_key: armor
      rarity: common
      summary_zh: 合成探針護甲摘要。
    equipment_slot: armor
    equipment_effects:
      adjustments:
        mp_cost: 5
"""


class ItemCatalogStartupSmokeTests(unittest.TestCase):
    """Drive the real startup item gate in one interpreter per case."""

    def _temporary_catalog(self, extra_row: str) -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        for source in SHIPPED_CATALOG.glob("*.yaml"):
            shutil.copy2(source, root / source.name)
        slice_path = root / "core_items.yaml"
        text = slice_path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        slice_path.write_text(text + extra_row, encoding="utf-8")
        return root

    def _run_smoke(self, case: str, extra_row: str) -> subprocess.CompletedProcess:
        before = self._shipped_snapshot()
        catalog = self._temporary_catalog(extra_row)
        result = subprocess.run(
            [sys.executable, "-c", _SCRIPT, case, str(catalog), str(REPOSITORY_ROOT)],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(
            self._shipped_snapshot(),
            before,
            "the smoke must not touch the shipped catalog",
        )
        return result

    @staticmethod
    def _shipped_snapshot() -> dict[str, bytes]:
        return {
            path.name: path.read_bytes() for path in SHIPPED_CATALOG.glob("*.yaml")
        }

    def _assert_rejected(
        self, result: subprocess.CompletedProcess, error_name: str, *fragments: str
    ) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertIn(f"REJECTED {error_name}", result.stdout)
        self.assertIn("SYNC_REACHED False", result.stdout)
        for fragment in fragments:
            self.assertIn(fragment, result.stdout)

    def test_a_malformed_row_is_rejected_before_sync_map_world(self):
        result = self._run_smoke("row", _MALFORMED_ROW)
        self._assert_rejected(
            result,
            "ItemCatalogError",
            "core_items.yaml.items[",
            ".sellable must be a boolean",
        )

    def test_an_invalid_usable_effect_is_rejected_before_sync_map_world(self):
        result = self._run_smoke("use_effect", _MALFORMED_USE_EFFECT)
        self._assert_rejected(
            result,
            "ItemEffectsRulebookError",
            "core_items.yaml",
            "t_probe_usable",
            "unknown stat 'luck'",
        )

    def test_an_invalid_equipment_effect_is_rejected_before_sync_map_world(self):
        result = self._run_smoke("equipment_effect", _MALFORMED_EQUIPMENT_EFFECT)
        self._assert_rejected(
            result,
            "EquipmentEffectsRulebookError",
            "core_items.yaml",
            "t_probe_armor",
            "must be a signed percent string",
        )


if __name__ == "__main__":
    unittest.main()
