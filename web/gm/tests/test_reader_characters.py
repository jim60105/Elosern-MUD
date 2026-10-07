"""Fixed-fixture reader tests: player characters (task 2.1 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
player-character kind, including the two hard invariants: stored truth and
``disguised_stats`` are emitted side by side (the disguise labelled 僅顯示用 and
never merged into a true trait), and currency stays integer copper with a
derived display. The ``gm-runtime-state::*`` requirement IDs this module covers
enter the traceability index when the change's delta spec is synced at archive.
"""

from __future__ import annotations

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from world.rules.traits import restore_gauges_to_full
from world.tests.synthetic_data import SYNTH_RACES

from web.gm.readers import characters
from web.gm.readers._entities import (
    read_attr,
    stored_attribute_keys,
)
from web.gm.tests._state_support import (
    column_values,
    failed_sections,
    field_value,
    link_kinds,
    open_synthetic_scope,
    row_by_key,
    row_value,
    section_keys,
    section_of,
)

SYNTH_RACE = "t_duskmari"

EXPECTED_SECTIONS = [
    "identity",
    "resources",
    "conditions",
    "traits",
    "disguise",
    "breakdown",
    "skills",
    "lineage",
    "equipment",
    "inventory",
    "wallet",
    "guild",
    "titles",
    "affinity",
    "party",
    "possession",
    "sexual",
    "links",
]

def _open_character_scope(case) -> None:
    open_synthetic_scope(case, "races", "static_tiers", "subraces")


class CharacterReaderTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_character_scope(self)
        super().setUp()
        self.player = create.create_object(
            PlayerCharacter, key="t_reader_player", location=self.room1
        )
        self.player.race = SYNTH_RACE
        self.player.apply_race_baseline()
        restore_gauges_to_full(self.player)
        self.player.sex = "female"
        self.player.age = 24
        self.player.apparent_age = 19
        self.player.db.wallet = 12_345
        self.player.db.inventory = ["t_ember_spray", "t_ember_spray", "t_iron_fang"]
        self.player.db.equipment = {
            "weapon_main": "t_iron_fang",
            "accessories": ["t_wayfarer_pass"],
        }
        self.player.guild_rank = "t_bronze"

    def test_detail_exposes_every_curated_character_section(self):
        detail = characters.character_detail(self.player)
        self.assertEqual(detail["kind"], "characters")
        self.assertEqual(detail["dbref"], self.player.pk)
        self.assertEqual(section_keys(detail), EXPECTED_SECTIONS)
        self.assertEqual(failed_sections(detail), {})

    def test_identity_reports_stored_identity_fields(self):
        detail = characters.character_detail(self.player)
        identity = section_of(detail, "identity")
        self.assertEqual(row_value(identity, "年齡"), 24)
        self.assertEqual(row_value(identity, "外觀年齡"), 19)
        self.assertEqual(row_value(identity, "性別"), "female")
        self.assertEqual(row_value(identity, "種族"), SYNTH_RACES[SYNTH_RACE].display_name_zh)
        self.assertEqual(row_value(identity, "當前房間"), f"#{self.room1.pk}")

    def test_disguise_is_emitted_separately_and_never_replaces_true_traits(self):
        true_attack = int(self.player.traits.atk_phys.value)
        self.player.db.disguised_stats = {"atk_phys": true_attack - 5}
        detail = characters.character_detail(self.player)
        traits = section_of(detail, "traits")
        self.assertEqual(row_by_key(traits, "atk_phys")["value"], true_attack)
        disguise = section_of(detail, "disguise")
        self.assertIn("僅顯示用", disguise["note"])
        self.assertEqual(row_by_key(disguise, "atk_phys")["value"], true_attack - 5)

    def test_breakdown_decomposes_each_trait_from_base_to_effective(self):
        detail = characters.character_detail(self.player)
        breakdown = section_of(detail, "breakdown")
        hp = next(group for group in breakdown["groups"] if group["key"] == "hp")
        self.assertEqual(hp["rows"][0]["label"], "基礎")
        self.assertTrue(hp["note"].startswith("有效值 "))

    def test_wallet_stays_integer_copper_with_a_derived_display(self):
        detail = characters.character_detail(self.player)
        wallet = section_of(detail, "wallet")
        self.assertEqual(row_value(wallet, "銅幣（整數）"), 12_345)
        self.assertEqual(row_value(wallet, "換算"), characters.money_display(12_345))
        self.assertIsInstance(row_value(wallet, "銅幣（整數）"), int)

    def test_inventory_counts_and_equipment_slots_are_projected(self):
        detail = characters.character_detail(self.player)
        inventory = section_of(detail, "inventory")
        self.assertEqual(column_values(inventory, "key"), ["t_ember_spray", "t_iron_fang"])
        self.assertEqual(column_values(inventory, "quantity"), [2, 1])
        equipment = section_of(detail, "equipment")
        self.assertEqual(column_values(equipment, "slot"), ["weapon_main", "accessory"])
        self.assertEqual(column_values(equipment, "key"), ["t_iron_fang", "t_wayfarer_pass"])

    def test_every_relationship_identifier_is_a_link(self):
        detail = characters.character_detail(self.player)
        links = section_of(detail, "links")
        kinds = link_kinds(links)
        self.assertLessEqual({"rooms", "quests", "memories", "dialogue"}, kinds)

    def test_links_expose_the_current_room_and_quests(self):
        detail = characters.character_detail(self.player)
        links = section_of(detail, "links")
        ids = {chip["label"]: chip["link"]["kind"] for chip in links["chips"]}
        self.assertEqual(ids[self.room1.key], "rooms")
        self.assertEqual(ids["任務紀錄"], "quests")

    def test_list_item_is_summary_only(self):
        item = characters.character_list_item(self.player)
        self.assertEqual(item["kind"], "characters")
        self.assertEqual(item["id"], str(self.player.pk))
        self.assertEqual(set(field_value(item, label) is not None for label in (
            "待完成建立",
            "種族",
            "所在位置",
        )), {True})


class MissingStoredDefaultTests(EvenniaTest):
    """A missing stored Attribute is reported, never materialized (design §2)."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_character_scope(self)
        super().setUp()
        self.player = create.create_object(
            PlayerCharacter, key="t_reader_pending", location=self.room1
        )
        self.player.race = SYNTH_RACE
        self.player.apply_race_baseline()
        restore_gauges_to_full(self.player)
        # The wallet Attribute is deliberately absent from a freshly created
        # shell; a product read must not fill it in.
        self.player.attributes.remove("wallet")

    def test_missing_wallet_reports_a_section_error_without_creating_it(self):
        before = stored_attribute_keys(self.player)
        self.assertIsNone(read_attr(self.player, "wallet", default=None))
        detail = characters.character_detail(self.player)
        failures = failed_sections(detail)
        self.assertIn("wallet", failures)
        self.assertEqual(failures["wallet"], "source_unavailable")
        # Everything that does not depend on the wallet still renders.
        self.assertNotIn("identity", failures)
        self.assertNotIn("resources", failures)
        self.assertIsNone(read_attr(self.player, "wallet", default=None))
        self.assertEqual(stored_attribute_keys(self.player), before)
