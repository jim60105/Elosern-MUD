"""Fixed-fixture reader tests: NPCs (task 2.2 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
NPC kind: every player-character field with the plain authored name, service
components, the seven-section persona card with its version, today's schedule
with the current slot, and the dialogue key. Its ``gm-runtime-state``
requirement annotation was attached when the delta spec synced into the main
spec at archive.
"""

from __future__ import annotations

import types
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.components import GuildStaff, ScriptedDialogue
from typeclasses.npcs import NPC
from world.lore.dialogue.shape import (
    AuthoredDialogue,
    AuthoredTopic,
    DialogueService,
)
from world.lore.scenes import Scene, Speech
from world.rules import npc_schedules
from world.rules.npc_persona import initialize_npc_persona
from world.rules.npc_services import CONTEXT_REQUIRED_MESSAGE, UNREADABLE_MESSAGE
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


def _scene(scene_id: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="打擾了。"),
            Speech(speaker="host", text="請說。"),
        ),
    )


#: The synthetic dialogue source of the inspected host: one unconditional
#: topic advertising a service and one predecessor-gated (therefore withheld
#: without a player context) topic advertising another.
OPEN_TOPIC = AuthoredTopic(
    topic_id="t_reader_dialogue.topic_01",
    keyword="近況",
    label="詢問近況",
    fallback=_scene("t_reader_dialogue.topic_01_scene"),
)
HIDDEN_TOPIC = AuthoredTopic(
    topic_id="t_reader_dialogue.topic_02",
    keyword="後續",
    label="追問後續",
    fallback=_scene("t_reader_dialogue.topic_02_scene"),
    predecessors=(OPEN_TOPIC.topic_id,),
    disclosure="pure_chain",
)
DIALOGUE = AuthoredDialogue(
    greeting=None,
    topics=(OPEN_TOPIC, HIDDEN_TOPIC),
    services=(
        DialogueService(key="t_report", topic_id=OPEN_TOPIC.topic_id, label="交談回報"),
        DialogueService(
            key="t_follow_up", topic_id=HIDDEN_TOPIC.topic_id, label="追問後續"
        ),
    ),
)

NPC_SECTIONS = [
    "npc_identity",
    "persona",
    "services",
    "capability_diagnostics",
    "schedule",
    "narrative_tabs",
]


def _attribute_rows(entity):
    """Every stored Attribute of the host, values included."""
    return sorted(
        (str(attribute.key), str(attribute.category or ""), repr(attribute.value))
        for attribute in entity.attributes.all()
    )


def _group(section, title):
    for entry in section["groups"]:
        if entry["title"] == title:
            return entry
    raise AssertionError(
        f"group {title!r} missing from {[entry.get('title') for entry in section['groups']]}"
    )


class NpcReaderTests(EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, "races", "static_tiers", "subraces")
        super().setUp()
        self.npc = create.create_object(NPC, key="t_reader_npc", location=self.room1)
        self.npc.race = SYNTH_RACE
        self.npc.apply_race_baseline()
        restore_gauges_to_full(self.npc)
        self.npc.attributes.add("npc_title", "合成頭銜")
        # The authored table is an immutable mapping; replace the module
        # attribute for the duration of the test (the same seam the dialogue
        # suites use).
        table = patch("world.rules.dialogue.DIALOGUE_TABLE", {"t_reader_dialogue": DIALOGUE})
        table.start()
        self.addCleanup(table.stop)
        self.dialogue = ScriptedDialogue.create(self.npc, dialogue_key="t_reader_dialogue")
        self.dialogue.service_binding = "person"
        self.npc.components.add(self.dialogue)
        self.staff = GuildStaff.create(
            self.npc, service_id="t_reader_service", branch_key="t_reader_branch"
        )
        self.staff.service_binding = "place"
        self.staff.anchor_room_id = self.room1.pk
        self.npc.components.add(self.staff)
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

    @covers_requirement('npc-identity-titles::every-npc-identity-surface-uses-the-plain-authored-name')
    def test_identity_reports_the_plain_name_and_dialogue_key(self):
        detail = npcs.detail(self.npc)
        identity = section_of(detail, "npc_identity")
        # The stored title is inert: the reader shows the authored plain name,
        # never the title and never a duplicate profession summary row.
        self.assertEqual(row_value(identity, "名稱"), self.npc.key)
        self.assertNotIn("合成頭銜", str(identity))
        labels = [entry["label"] for entry in identity["rows"]]
        self.assertNotIn("稱號", labels)
        self.assertNotIn("職業", labels)
        self.assertEqual(row_value(identity, "對話鍵"), "t_reader_dialogue")

    def test_labels_agree_with_the_text_and_exploration_name(self):
        # One plain-name source: the GM label, the identity row, the item
        # label and the text/webclient display name all read the same key.
        detail = npcs.detail(self.npc)
        item = npcs.item_of(self.npc)
        display_name = self.npc.get_display_name()
        self.assertEqual(detail["label"], display_name)
        self.assertEqual(item["label"], display_name)
        self.assertEqual(row_value(section_of(detail, "npc_identity"), "名稱"), display_name)

    def test_persona_card_exposes_seven_sections_and_the_version(self):
        detail = npcs.detail(self.npc)
        persona = section_of(detail, "persona")
        self.assertEqual(
            group_titles(persona),
            ["身分", "外貌", "性格", "語氣", "生平", "習慣", "人際連結"],
        )
        self.assertIn("版本 1", persona["note"])
        self.assertIn("世代", persona["note"])

    @covers_requirement(
        "gm-runtime-state::npc-service-inspection-separates-context-from-configuration"
    )
    def test_services_are_the_projection_entries_with_context_required_availability(self):
        detail = npcs.detail(self.npc)
        services = section_of(detail, "services")
        self.assertEqual(
            column_values(services, "service"),
            ["guild.register", "guild.board", "guild.report", "dialogue.t_report"],
        )
        self.assertEqual(
            column_values(services, "availability"), ["context_required"] * 4
        )
        self.assertEqual(
            column_values(services, "reason"), [CONTEXT_REQUIRED_MESSAGE] * 4
        )
        routes = column_values(services, "route")
        self.assertEqual(routes[0], f"guild register @#{self.npc.pk}")
        self.assertEqual(routes[-1], f"talk {self.npc.key}")
        # The withheld association and its topic identity never reach the
        # player-facing summary.
        self.assertNotIn("t_follow_up", str(services))
        self.assertNotIn(HIDDEN_TOPIC.topic_id, str(services))

    @covers_requirement(
        "gm-runtime-state::npc-service-inspection-separates-context-from-configuration"
    )
    def test_a_present_player_never_changes_the_management_summary(self):
        self.char1.location = self.room1
        services = section_of(npcs.detail(self.npc), "services")
        self.assertEqual(
            column_values(services, "availability"), ["context_required"] * 4
        )

    @covers_requirement(
        "gm-runtime-state::npc-service-inspection-separates-context-from-configuration"
    )
    def test_capability_diagnostics_keep_configuration_out_of_the_summary(self):
        detail = npcs.detail(self.npc)
        diagnostics = section_of(detail, "capability_diagnostics")
        staff = _group(diagnostics, GuildStaff.name)
        self.assertEqual(row_value(staff, "綁定"), "place")
        self.assertEqual(row_value(staff, "錨點"), f"#{self.room1.pk}")
        self.assertIn("service_id=t_reader_service", row_value(staff, "設定"))
        self.assertEqual(row_value(staff, "狀態"), "正常")
        dialogue = _group(diagnostics, ScriptedDialogue.name)
        self.assertEqual(row_value(dialogue, "綁定"), "person")
        associations = _group(diagnostics, "對話服務關聯")
        self.assertEqual(
            [entry["key"] for entry in associations["rows"]],
            ["t_follow_up", "t_report"],
        )
        self.assertIn(HIDDEN_TOPIC.topic_id, str(associations))
        # The service summary stays free of the component-field inventory.
        self.assertNotIn("service_id=t_reader_service", str(section_of(detail, "services")))

    @covers_requirement(
        "gm-runtime-state::npc-service-inspection-separates-context-from-configuration"
    )
    def test_an_unresolvable_anchor_is_reported_without_losing_the_entry(self):
        self.staff.anchor_room_id = self.room1.pk + 99999
        detail = npcs.detail(self.npc)
        services = section_of(detail, "services")
        self.assertNotIn("error", services)
        self.assertIn("guild.register", column_values(services, "service"))
        staff = _group(section_of(detail, "capability_diagnostics"), GuildStaff.name)
        self.assertIn("錨點無法解析", row_value(staff, "狀態"))

    @covers_requirement(
        "gm-runtime-state::npc-service-inspection-separates-context-from-configuration"
    )
    def test_an_unresolvable_declared_dialogue_source_is_a_section_error(self):
        with patch(
            "world.rules.dialogue_sources.dialogue_source_for_host",
            return_value=None,
        ):
            detail = npcs.detail(self.npc)
        services = section_of(detail, "services")
        self.assertEqual(services["error"]["code"], "source_unavailable")
        self.assertEqual(services["error"]["message"], UNREADABLE_MESSAGE)
        associations = _group(
            section_of(detail, "capability_diagnostics"), "對話服務關聯"
        )
        self.assertIn("無法解析", row_value(associations, "狀態"))

    def test_a_plain_npc_has_no_service_entries_and_no_capability_groups(self):
        plain = create.create_object(NPC, key="t_reader_plain", location=self.room1)
        plain.race = SYNTH_RACE
        plain.apply_race_baseline()
        restore_gauges_to_full(plain)
        detail = npcs.detail(plain)
        self.assertEqual(section_of(detail, "services")["type"], "empty")
        self.assertEqual(section_of(detail, "capability_diagnostics")["type"], "empty")
        self.assertEqual(failed_sections(detail), {})

    def test_narrative_only_dialogue_is_not_a_configuration_error(self):
        narrative = AuthoredDialogue(greeting=None, topics=(), services=())
        with patch(
            "world.rules.dialogue.DIALOGUE_TABLE",
            {"t_reader_dialogue": DIALOGUE, "t_reader_narrative": narrative},
        ):
            host = create.create_object(NPC, key="t_reader_narrative", location=self.room1)
            host.race = SYNTH_RACE
            host.apply_race_baseline()
            restore_gauges_to_full(host)
            dialogue = ScriptedDialogue.create(host, dialogue_key="t_reader_narrative")
            host.components.add(dialogue)
            diagnostics = section_of(npcs.detail(host), "capability_diagnostics")
        group_ = _group(diagnostics, ScriptedDialogue.name)
        self.assertEqual(row_value(group_, "狀態"), "正常")
        self.assertIn("純敘事", str(group_))

    def test_a_person_binding_reports_its_stored_anchor_without_a_false_failure(self):
        self.dialogue.anchor_room_id = self.room1.pk
        diagnostics = section_of(npcs.detail(self.npc), "capability_diagnostics")
        group_ = _group(diagnostics, ScriptedDialogue.name)
        anchor = row_value(group_, "錨點")
        self.assertIn(f"#{self.room1.pk}", anchor)
        self.assertNotIn("無法解析", anchor)
        self.assertIn("person 綁定不應帶錨點", row_value(group_, "狀態"))

    @covers_requirement(
        "gm-runtime-state::npc-service-inspection-separates-context-from-configuration"
    )
    def test_a_malformed_declared_dialogue_key_is_unreadable_not_empty(self):
        host = create.create_object(NPC, key="t_reader_broken_key", location=self.room1)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key="scene_role:broken")
        )
        detail = npcs.detail(host)
        services = section_of(detail, "services")
        self.assertEqual(services["error"]["code"], "source_unavailable")
        associations = _group(
            section_of(detail, "capability_diagnostics"), "對話服務關聯"
        )
        self.assertIn("無法解析", row_value(associations, "狀態"))

    def test_item_fields_keep_only_the_room_summary(self):
        item = npcs.item_of(self.npc)
        labels = [field["label"] for field in item["fields"]]
        self.assertEqual(labels, ["所在房間"])

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
        before = _attribute_rows(self.npc)
        npcs.detail(self.npc)
        npcs.item_of(self.npc)
        self.assertEqual(_attribute_rows(self.npc), before)
        self.assertEqual(stored_attribute_keys(self.npc), {
            (key, category) for key, category, _value in before
        })

    def test_a_malformed_host_read_writes_nothing(self):
        self.staff.anchor_room_id = self.room1.pk + 99999
        before = _attribute_rows(self.npc)
        with CaptureQueriesContext(connection) as queries:
            npcs.detail(self.npc)
        writes = [
            query["sql"]
            for query in queries
            if query["sql"].lstrip().split(" ", 1)[0].upper()
            in {"INSERT", "UPDATE", "DELETE", "REPLACE"}
        ]
        self.assertEqual(writes, [])
        self.assertEqual(_attribute_rows(self.npc), before)
        # The gameplay malformed-binding debounce is the gate's own flag; a
        # management read never arms it.
        self.assertIsNone(getattr(self.npc.ndb, "service_gate_malformed_warned", None))

    def test_owner_identity_requires_and_resolves_a_dbref(self):
        with self.assertRaises(Exception) as missing:
            npcs.owner_identity({})
        self.assertEqual(missing.exception.code, "invalid_filter")
        self.assertEqual(npcs.owner_identity({"owner": f"#{self.npc.pk}"})[0], str(self.npc.pk))
