"""Evennia integration checks for idempotent lore synchronization."""

from dataclasses import asdict, replace

from evennia.scripts.models import ScriptDB
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTest

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.lore.sync import _ALL_REGISTRIES, _db_safe, sync_all, sync_one


class LoreSyncTests(EvenniaTest):
    def _lore_records(self):
        records = []
        for category, registry in _ALL_REGISTRIES.items():
            for key, entry in registry.items():
                matches = search_script(f"lore:{category}:{key}")
                self.assertEqual(len(matches), 1, f"duplicate or missing {category}:{key}")
                self.assertEqual(matches[0].db.fields, _db_safe(asdict(entry)))
                records.append(matches[0])
        return records

    def test_sync_all_is_idempotent_and_complete(self):
        expected = sum(len(registry) for registry in _ALL_REGISTRIES.values())

        sync_all()
        first = self._lore_records()
        self.assertEqual(len(first), expected)
        self.assertEqual(
            ScriptDB.objects.filter(db_key__startswith="lore:").count(),
            expected,
        )

        sync_all()
        second = self._lore_records()
        self.assertEqual(len(second), expected)
        self.assertEqual(
            ScriptDB.objects.filter(db_key__startswith="lore:").count(),
            expected,
        )
        self.assertEqual({record.id for record in first}, {record.id for record in second})

        elf = search_script("lore:races:elf")
        self.assertEqual(len(elf), 1)
        self.assertEqual(elf[0].db.category, "races")
        self.assertEqual(elf[0].db.fields["lifespan"], (800, 1200))
        capital = search_script("lore:anchors:capital_grandia")
        self.assertEqual(capital[0].db.fields["kind"], "capital")

    def test_anchor_placements_record_is_mirrored_and_idempotent(self):
        expected = _db_safe(asdict(ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]))

        sync_all()
        records = search_script("lore:anchor_placements:capital_altoria")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].db.category, "anchor_placements")
        self.assertEqual(records[0].db.fields, expected)

        sync_all()
        records = search_script("lore:anchor_placements:capital_altoria")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].db.fields, expected)

    def test_sync_one_updates_existing_record(self):
        entry = RACE_REGISTRY["human"]
        sync_one("test_races", entry.key, entry)
        changed = replace(entry, magic_cap=91)
        sync_one("test_races", changed.key, changed)

        records = search_script("lore:test_races:human")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].db.fields["magic_cap"], 91)
