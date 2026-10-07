"""Fixed-fixture reader tests: monsters (task 2.2 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
monster kind: identity and provenance (species, variant, derived threat tier,
danger grade, and the numeric source that actually built the individual), the
owning site or ambient placement, the loot table, and the behaviour profile.
Its ``gm-runtime-state`` requirement annotations were attached when the delta
spec synced into the main spec at archive.
"""

from __future__ import annotations

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from world.rules.monster_behaviour import BEHAVIOUR_PROFILES, MONSTER_BEHAVIOUR_YAML
from world.rules.monster_individual import construct_species_individual
from world.rules.traits import (
    NUMERIC_SOURCE_APPROVED_PROFILE,
    NUMERIC_SOURCE_INTERIM_TIER_BAND,
)
from world.tests.synthetic_data import (
    SYNTH_MONSTER_SITES,
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_VARIANTS,
)

from tools.spec_traceability import covers_requirement
from web.gm.readers import monsters
from web.gm.readers._entities import read_attr, stored_attribute_keys
from web.gm.tests._state_support import (
    column_values,
    failed_sections,
    open_synthetic_scope,
    row_value,
    section_keys,
    section_of,
)

SPECIES = "t_whisper_quail"
ORDINARY = "t_whisper_quail_ordinary"
STRONGER = "t_whisper_quail_stronger"
SITE = "t_breakwater_nest"

EXPECTED_SECTIONS = [
    "identity",
    "numeric",
    "placement",
    "loot",
    "behaviour",
    "resources",
    "conditions",
    "traits",
    "links",
]


class MonsterReaderTests(EvenniaTest):
    def setUp(self):
        # ``ambient_placements`` is part of the scope: an individual without a
        # site key resolves its region through the ambient placement registry,
        # so the absence of that catalog would make the placement section
        # report a missing region instead of the kit's own rule.
        open_synthetic_scope(
            self,
            "monster_species",
            "monster_variants",
            "monster_tiers",
            "ambient_placements",
            "monster_sites",
        )
        super().setUp()

    def _individual(self, variant: str = ORDINARY):
        monster = construct_species_individual(SPECIES, variant)
        # The kit's band declares zero MP/SP maxima; the strict status read
        # model refuses a non-positive gauge, so the trait-backed sections
        # are exercised with a living (positive) resource baseline.
        monster.traits.mp.base = 10
        monster.traits.sp.base = 10
        monster.traits.mp.current = 10
        monster.traits.sp.current = 10
        return monster

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_species_identity_and_interim_numeric_source_are_reported(self):
        monster = self._individual()
        # The kit's tier key is deliberately absent from the shipped behaviour
        # rulebook's tier→archetype map, so the behaviour section would carry a
        # contained source_unavailable slot. Register the tier for this case
        # (the rulebook lookup is the authoritative read) so the assertion
        # below is about the numeric-source projection, not that gap.
        tier = SYNTH_MONSTER_VARIANTS[ORDINARY].threat_tier
        archetype = next(iter(BEHAVIOUR_PROFILES))
        with patch.dict(MONSTER_BEHAVIOUR_YAML["tier_default_archetype"], {tier: archetype}):
            detail = monsters.detail(monster)
        self.assertEqual(section_keys(detail), EXPECTED_SECTIONS)
        self.assertEqual(failed_sections(detail), {})
        identity = section_of(detail, "identity")
        self.assertEqual(
            row_value(identity, "物種"), SYNTH_MONSTER_SPECIES[SPECIES].display_name_zh
        )
        self.assertEqual(
            row_value(identity, "變體"), SYNTH_MONSTER_VARIANTS[ORDINARY].display_name_zh
        )
        self.assertEqual(
            row_value(identity, "威脅階級"), SYNTH_MONSTER_VARIANTS[ORDINARY].threat_tier
        )
        self.assertEqual(row_value(identity, "危險等級"), "—")
        self.assertEqual(
            row_value(identity, "數值來源"),
            monsters.NUMERIC_SOURCE_LABELS[NUMERIC_SOURCE_INTERIM_TIER_BAND],
        )

    @covers_requirement("gm-world-data::authored-browser-and-runtime-links")
    def test_species_and_variant_rows_link_to_their_authored_entries(self):
        # gm-portal-s4-world-data §4.4: registry-key runtime fields open the
        # authored entry page through the shared link component.
        monster = self._individual()
        identity = section_of(monsters.detail(monster), "identity")
        links = {entry["label"]: entry.get("link") for entry in identity["rows"]}
        self.assertEqual(
            links["物種"], {"kind": "registry", "registry": "monster_species", "id": SPECIES}
        )
        self.assertEqual(
            links["變體"], {"kind": "registry", "registry": "monster_variants", "id": ORDINARY}
        )
        listed = {entry["label"]: entry.get("link") for entry in monsters.item_of(monster)["fields"]}
        self.assertEqual(listed["物種"]["id"], SPECIES)
        self.assertEqual(listed["變體"]["registry"], "monster_variants")
        # The individual's stored identity is untouched by the link lookup.
        self.assertEqual(read_attr(monster, "species_key", default=None), SPECIES)

    def test_approved_profile_variant_reports_its_own_numeric_source(self):
        monster = self._individual(STRONGER)
        detail = monsters.detail(monster)
        identity = section_of(detail, "identity")
        self.assertEqual(
            row_value(identity, "數值來源"),
            monsters.NUMERIC_SOURCE_LABELS[NUMERIC_SOURCE_APPROVED_PROFILE],
        )
        self.assertEqual(
            row_value(identity, "危險等級"), SYNTH_MONSTER_VARIANTS[STRONGER].danger_grade
        )
        numeric = section_of(detail, "numeric")
        self.assertIn("hp=", row_value(numeric, "已核可數值"))

    def test_placement_reports_a_site_or_the_ambient_region(self):
        monster = self._individual()
        ambient = section_of(monsters.detail(monster), "placement")
        self.assertEqual(row_value(ambient, "歸屬"), "環境散布")
        self.assertEqual(row_value(ambient, "區域"), monsters.region_of(monster))
        monster.db.site_key = SITE
        site = section_of(monsters.detail(monster), "placement")
        self.assertEqual(row_value(site, "歸屬"), "據點")
        self.assertEqual(row_value(site, "據點"), SITE)
        self.assertEqual(row_value(site, "區域"), SYNTH_MONSTER_SITES[SITE].region_key)
        self.assertIn(",", row_value(site, "座標"))

    def test_loot_table_rows_cover_item_keys_and_quantity_rows(self):
        monster = self._individual()
        monster.db.loot_table = [
            "t_ember_spray",
            {"item_key": "t_iron_fang", "quantity": 2, "chance": 0.25},
        ]
        loot = section_of(monsters.detail(monster), "loot")
        self.assertEqual(column_values(loot, "key"), ["t_ember_spray", "t_iron_fang"])
        self.assertEqual(column_values(loot, "quantity"), [1, 2])
        self.assertEqual(column_values(loot, "chance"), ["—", 0.25])

    def test_behaviour_profile_resolves_through_the_tier_default(self):
        monster = self._individual()
        tier = SYNTH_MONSTER_VARIANTS[ORDINARY].threat_tier
        archetype = next(iter(BEHAVIOUR_PROFILES))
        with patch.dict(MONSTER_BEHAVIOUR_YAML["tier_default_archetype"], {tier: archetype}):
            behaviour = section_of(monsters.detail(monster), "behaviour")
            self.assertEqual(row_value(behaviour, "行為鍵"), "（使用階級預設）")
            self.assertEqual(
                row_value(behaviour, "目標策略"),
                BEHAVIOUR_PROFILES[archetype].target_strategy,
            )

    @covers_requirement("gm-runtime-state::independent-failures-and-precise-lookup-errors")
    def test_a_failing_section_leaves_the_others_readable(self):
        # An unregistered tier key cannot resolve a behaviour profile; the
        # refusal stays in that slot while the rest of the page renders.
        monster = self._individual()
        detail = monsters.detail(monster)
        failures = failed_sections(detail)
        self.assertEqual(failures.get("behaviour"), "source_unavailable")
        self.assertNotIn("identity", failures)
        self.assertNotIn("loot", failures)
        self.assertNotIn("traits", failures)

    def test_inspection_never_provisions_the_autocreating_descriptors(self):
        monster = self._individual()
        before = stored_attribute_keys(monster)
        self.assertIsNone(read_attr(monster, "behaviour_tree", default=None))
        monsters.detail(monster)
        monsters.item_of(monster)
        self.assertEqual(stored_attribute_keys(monster), before)
        self.assertIsNone(read_attr(monster, "behaviour_tree", default=None))

    def test_list_row_is_summary_only(self):
        monster = self._individual()
        item = monsters.item_of(monster)
        self.assertEqual(item["kind"], "monsters")
        self.assertEqual(item["id"], str(monster.pk))
        labels = [field["label"] for field in item["fields"]]
        self.assertEqual(labels, ["物種", "變體", "威脅階級", "數值來源"])
