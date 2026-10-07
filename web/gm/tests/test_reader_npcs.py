"""Fixed-fixture reader tests: NPCs (task 2.2 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
NPC kind: every player-character field plus title/profession, service
components, the seven-section persona card with its version, today's schedule
with the current slot, and the dialogue key. Its ``gm-runtime-state``
requirement annotation was attached when the delta spec synced into the main
spec at archive.
"""

from __future__ import annotations

import types
from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.components import GuildStaff, ScriptedDialogue
from typeclasses.npcs import NPC
from world.rules import npc_schedules
from world.rules.npc_persona import initialize_npc_persona
from world.rules.traits import restore_gauges_to_full
from world.tests.synthetic_data import SYNTH_RACES

from tools.spec_traceability import covers_requirement
from web.gm.readers import npcs
from web.gm.readers._entities import stored_attribute_keys
from web.gm.tests._state_support import (
    column_values,
    failed_sections,
    group_titles,
    link_kinds,
    open_synthetic_scope,
    row_value,
    section_keys,
    section_of,
)

SYNTH_RACE = "t_duskmari"

CARD = {
    "identity": {"public": "合成記錄員", "hidden": "曾為信差"},
    "appearance": "穿著灰色短褂",
    "personality": "謹慎而親切",
    "speech_style": "說話簡短",
    "life_story": "在渡口整理往來紀錄",
    "habit": "每天擦拭筆尖",
    "social_connection": "",
}

NPC_SECTIONS = ["npc_identity", "persona", "services", "schedule", "narrative_tabs"]


class NpcReaderTests(EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, "races", "static_tiers", "subraces")
        super().setUp()
        self.npc = create.create_object(NPC, key="t_reader_npc", location=self.room1)
        self.npc.race = SYNTH_RACE
        self.npc.apply_race_baseline()
        restore_gauges_to_full(self.npc)
        self.npc.npc_title = "合成頭銜"
        self.dialogue = ScriptedDialogue.create(self.npc, dialogue_key="t_reader_dialogue")
        self.npc.components.add(self.dialogue)
        self.npc.components.add(
            GuildStaff.create(self.npc, service_id="t_reader_service", branch_key="t_reader_branch")
        )
        initialize_npc_persona(self.npc, CARD, {"kind": "import", "record": "t-reader-npc"})

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_detail_carries_character_sections_plus_the_npc_only_ones(self):
        detail = npcs.detail(self.npc)
        keys = section_keys(detail)
        for key in NPC_SECTIONS:
            self.assertIn(key, keys)
        # The shared character projection still leads the payload.
        self.assertEqual(keys[0], "identity")
        self.assertEqual(failed_sections(detail), {})

    def test_identity_reports_title_profession_and_dialogue_key(self):
        detail = npcs.detail(self.npc)
        identity = section_of(detail, "npc_identity")
        self.assertIn("合成頭銜", row_value(identity, "名稱"))
        self.assertEqual(row_value(identity, "稱號"), "合成頭銜")
        self.assertEqual(row_value(identity, "對話鍵"), "t_reader_dialogue")
        professions = row_value(identity, "職業")
        self.assertIn("腳本對話", professions)
        self.assertIn("公會櫃檯", professions)

    def test_persona_card_exposes_seven_sections_and_the_version(self):
        detail = npcs.detail(self.npc)
        persona = section_of(detail, "persona")
        self.assertEqual(
            group_titles(persona),
            ["身分", "外貌", "性格", "語氣", "生平", "習慣", "人際連結"],
        )
        self.assertIn("版本 1", persona["note"])
        self.assertIn("世代", persona["note"])

    def test_services_table_lists_each_existing_component(self):
        detail = npcs.detail(self.npc)
        services = section_of(detail, "services")
        slots = column_values(services, "slot")
        self.assertIn(ScriptedDialogue.name, slots)
        self.assertIn(GuildStaff.name, slots)
        self.assertIn("t_reader_service", " ".join(column_values(services, "fields")))

    def test_schedule_marks_today_plan_and_the_current_slot(self):
        states = npc_schedules.get_rulebook().states
        schedule = {
            "schema_version": npc_schedules.SCHEMA_VERSION,
            "entries": [
                {"tick_offset": 0, "kind": "state", "state": states[0]},
                {"tick_offset": 7200, "kind": "state", "state": states[0]},
            ],
        }
        with patch(
            "world.rules.npc_schedules.get_world_clock",
            return_value=types.SimpleNamespace(tick=3600),
        ):
            npc_schedules.set_npc_schedule(self.npc, schedule)
        with patch(
            "world.rules.clock.read_world_clock",
            return_value=types.SimpleNamespace(tick=3600),
        ):
            detail = npcs.detail(self.npc)
        table = section_of(detail, "schedule")
        self.assertEqual(column_values(table, "offset"), [0, 7200])
        self.assertEqual(table["rows"][0]["cells"]["offset"]["tone"], "gold")
        self.assertNotIn("tone", table["rows"][1]["cells"]["offset"])
        self.assertIn("目前時段 tick_offset=0", table["note"])

    def test_absent_schedule_reports_an_empty_payload(self):
        detail = npcs.detail(self.npc)
        schedule = section_of(detail, "schedule")
        self.assertEqual(schedule["type"], "empty")
        self.assertIn("沒有排程", schedule["note"])

    def test_narrative_tab_links_point_at_the_memory_snapshot_and_dialogue_views(self):
        detail = npcs.detail(self.npc)
        tabs = section_of(detail, "narrative_tabs")
        kinds = link_kinds(tabs)
        self.assertLessEqual({"memories", "snapshots", "dialogue"}, kinds)
        labels = {chip["label"]: chip["link"] for chip in tabs["chips"]}
        self.assertEqual(labels["對話"]["id"], str(self.npc.pk))

    def test_reading_an_npc_creates_no_attributes(self):
        before = stored_attribute_keys(self.npc)
        npcs.detail(self.npc)
        npcs.item_of(self.npc)
        self.assertEqual(stored_attribute_keys(self.npc), before)

    def test_owner_identity_requires_and_resolves_a_dbref(self):
        with self.assertRaises(Exception) as missing:
            npcs.owner_identity({})
        self.assertEqual(missing.exception.code, "invalid_filter")
        self.assertEqual(npcs.owner_identity({"owner": f"#{self.npc.pk}"})[0], str(self.npc.pk))
