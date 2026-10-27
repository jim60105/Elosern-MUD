"""Data-contract test: lore cross-registry sync contract
Evennia integration checks for idempotent lore synchronization."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from types import MappingProxyType

from evennia.scripts.models import ScriptDB
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTestCase

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.lore.sync import (
    _ALL_REGISTRIES,
    _db_safe,
    _plain,
    geography_registries,
    sync_all,
    sync_one,
)
from world.tests.geography_fixture import publish_shipped_geography


def setUpModule():
    publish_shipped_geography()


def _mirrored_registries():
    return {**_ALL_REGISTRIES, **geography_registries()}


class LoreSyncTests(EvenniaTestCase):
    def _lore_records(self):
        records = []
        for category, registry in _mirrored_registries().items():
            for key, entry in registry.items():
                matches = search_script(f"lore:{category}:{key}")
                self.assertEqual(len(matches), 1, f"duplicate or missing {category}:{key}")
                self.assertEqual(matches[0].db.fields, _db_safe(_plain(entry)))
                records.append(matches[0])
        return records

    @covers_requirement("title-system::the-fixed-title-lore-registry-validates-and-syncs-idempotently")
    def test_sync_all_is_idempotent_and_complete(self):
        expected = sum(len(registry) for registry in _mirrored_registries().values())

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

    @covers_requirement("anchor-placement::anchor-placement-registry-is-mirrored-into-lorerecord-scripts-idempotently")
    def test_anchor_placements_record_is_mirrored_and_idempotent(self):
        expected = _db_safe(_plain(ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]))

        sync_all()
        records = search_script("lore:anchor_placements:capital_altoria")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].db.category, "anchor_placements")
        self.assertEqual(records[0].db.fields, expected)

        sync_all()
        records = search_script("lore:anchor_placements:capital_altoria")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].db.fields, expected)

    @covers_requirement("lore-startup-sync::every-lore-registry-entry-is-mirrored-into-the-db-keyed-by-key", "wilderness-terrain::wilderness-region-registry-is-mirrored-into-lorerecord-scripts-idempotently")
    @covers_requirement("lore-startup-sync::a-code-side-change-to-a-registry-is-reflected-on-the-next-sync")
    def test_wilderness_registry_records_are_mirrored_and_idempotent(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.lore.wilderness_regions import regions

        sync_all()
        for key in regions():
            matches = search_script(f"lore:wilderness_regions:{key}")
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].db.category, "wilderness_regions")
        entry_records = search_script("lore:wilderness_entries:capital_altoria")
        self.assertEqual(len(entry_records), 1)
        self.assertEqual(entry_records[0].db.category, "wilderness_entries")

        sync_all()
        total_wilderness = len(regions()) + len(WILDERNESS_ENTRY_REGISTRY)
        self.assertEqual(
            ScriptDB.objects.filter(db_key__startswith="lore:wilderness_").count(),
            total_wilderness,
        )

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_wilderness_entry_v2_payload_is_mirrored_in_primitive_shape(self):
        from world.lore.wilderness_entry import (
            WildernessEntryPoint,
            WildernessGate,
        )
        from world.maps import map_data
        from elosern_map_core.references import settlement_node_ref

        # A v2-typed extra entry proves the mirror preserves the NESTED dataclass
        # payload (gates -> tuple of primitive dicts, shape -> tuple of str) and
        # stays idempotent across two sync_all() calls.
        probe = WildernessEntryPoint(
            "capital_altoria",
            ("#",),
            (860, 1080),
            (WildernessGate("n", settlement_node_ref("capital_altoria", "south_gate")),),
        )
        previous = map_data.current()
        entries = dict(previous.wilderness_entries)
        entries["capital_altoria"] = probe
        map_data.publish(
            replace(previous, wilderness_entries=MappingProxyType(entries))
        )
        try:
            sync_all()
            first = search_script("lore:wilderness_entries:capital_altoria")
            sync_all()
            second = search_script("lore:wilderness_entries:capital_altoria")
        finally:
            map_data.publish(previous)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(first[0].id, second[0].id)
        self.assertEqual(first[0].db.fields, _db_safe(_plain(probe)))
        self.assertEqual(
            first[0].db.fields["gates"],
            (
                {
                    "return_direction": "n",
                    "destination": {
                        "domain": "settlement_node",
                        "map_id": "capital_altoria",
                        "object_id": "south_gate",
                        "cell": None,
                    },
                },
            ),
        )
        self.assertEqual(first[0].db.fields["shape"], ("#",))

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_sync_all_refuses_to_mirror_a_malformed_registry(self):
        from world.lore.wilderness_entry import WildernessEntryPoint
        from world.maps import map_data

        malformed = WildernessEntryPoint("capital_altoria", (), (0, 0), ())
        previous = map_data.current()
        entries = dict(previous.wilderness_entries)
        entries["capital_altoria"] = malformed
        map_data.publish(
            replace(previous, wilderness_entries=MappingProxyType(entries))
        )
        try:
            with self.assertRaises(ValueError):
                sync_all()
        finally:
            map_data.publish(previous)
        # Nothing was created: the validation error precedes every mirror write.
        self.assertEqual(
            ScriptDB.objects.filter(db_key__startswith="lore:wilderness_entries:").count(), 0
        )

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits", "grid-room-sync::sync-grid-is-idempotent-across-repeated-calls-and-server-starts", "lore-startup-sync::sync-is-idempotent-across-repeated-server-starts")
    def test_sync_one_updates_existing_record(self):
        entry = RACE_REGISTRY["human"]
        sync_one("test_races", entry.key, entry)
        changed = replace(entry, learning_multiplier=0.5)
        sync_one("test_races", changed.key, changed)

        records = search_script("lore:test_races:human")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].db.fields["learning_multiplier"], 0.5)
