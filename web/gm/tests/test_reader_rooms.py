"""Fixed-fixture reader tests: rooms (task 2.3 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
room kind: coordinates and place kind, exits with their destinations, the
occupants grouped by kind, and instance ownership/lifetime read back without
provisioning a single Attribute. Its ``gm-runtime-state`` requirement
annotations were attached when the delta spec synced into the main spec at
archive.
"""

from __future__ import annotations

from django.test import Client
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, GridRoom, InstanceRoom, Room

from tools.spec_traceability import covers_requirement
from web.gm.readers import rooms
from web.gm.readers._entities import read_attr, stored_attribute_keys
from web.gm.tests._state_support import (
    column_values,
    failed_sections,
    group_titles,
    link_ids,
    link_kinds,
    row_value,
    section_keys,
    section_of,
)

EXPECTED_SECTIONS = ["identity", "exits", "occupants", "instance"]


class RoomReaderTests(EvenniaTest):
    room_typeclass = Room

    def setUp(self):
        super().setUp()
        self.here = create.create_object(Room, key="t_reader_room")
        self.there = create.create_object(Room, key="t_reader_room_far")
        self.door = create.create_object(
            Exit, key="north", location=self.here, destination=self.there
        )
        self.npc = create.create_object(NPC, key="t_reader_room_npc", location=self.here)

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_detail_carries_the_four_room_sections(self):
        detail = rooms.detail(self.here)
        self.assertEqual(detail["kind"], "rooms")
        self.assertEqual(detail["dbref"], self.here.pk)
        self.assertEqual(section_keys(detail), EXPECTED_SECTIONS)
        self.assertEqual(failed_sections(detail), {})

    def test_identity_reports_the_place_kind_and_omits_absent_coordinates(self):
        detail = rooms.detail(self.here)
        identity = section_of(detail, "identity")
        self.assertEqual(row_value(identity, "名稱"), "t_reader_room")
        self.assertEqual(row_value(identity, "地點類型"), "房間")
        # A plain room has no xyz; the row must be absent, not fabricated.
        self.assertNotIn("座標", [row["label"] for row in identity["rows"]])
        self.assertIsNone(rooms.coordinates(self.here))

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_room_api_preserves_named_and_numeric_grid_layers_without_writes(self):
        client = Client()
        client.force_login(self.account)
        for room_type, xyz in (
            (GridRoom, (-3, 0, "t_named_grid_map")),
            (AnchorRoom, (0, -4, "t_named_anchor_map")),
            (GridRoom, (2, -5, -1)),
            (AnchorRoom, (-2, 3, 0)),
        ):
            with self.subTest(room_type=room_type.__name__, xyz=xyz):
                room, errors = room_type.create(key="t_reader_grid_layer", xyz=xyz)
                self.assertEqual(errors, [])
                before_attrs = stored_attribute_keys(room)
                before_tags = room.tags.all(return_key_and_category=True)
                expected = ", ".join(str(part) for part in xyz)

                response = client.get("/gm/api/state/rooms")
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertIs(payload["ok"], True)
                item = next(
                    item
                    for item in payload["data"]["items"]
                    if item["id"] == str(room.pk)
                )
                self.assertEqual(row_value({"rows": item["fields"]}, "座標"), expected)

                response = client.get(f"/gm/api/state/rooms/{room.pk}")
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertIs(payload["ok"], True)
                detail = payload["data"]
                self.assertEqual(failed_sections(detail), {})
                self.assertEqual(row_value(section_of(detail, "identity"), "座標"), expected)
                self.assertEqual(stored_attribute_keys(room), before_attrs)
                self.assertEqual(room.tags.all(return_key_and_category=True), before_tags)

    def test_incomplete_grid_coordinates_are_absent_in_list_and_detail_api(self):
        room = create.create_object(GridRoom, key="t_reader_unplaced_grid")
        client = Client()
        client.force_login(self.account)
        response = client.get("/gm/api/state/rooms")
        self.assertEqual(response.status_code, 200)
        item = next(
            item for item in response.json()["data"]["items"] if item["id"] == str(room.pk)
        )
        self.assertEqual(row_value({"rows": item["fields"]}, "座標"), "—")

        response = client.get(f"/gm/api/state/rooms/{room.pk}")
        self.assertEqual(response.status_code, 200)
        detail = response.json()["data"]
        self.assertEqual(failed_sections(detail), {})
        identity = section_of(detail, "identity")
        self.assertNotIn("座標", [entry["label"] for entry in identity["rows"]])

    def test_exits_table_links_direction_and_destination(self):
        detail = rooms.detail(self.here)
        exits = section_of(detail, "exits")
        self.assertEqual(column_values(exits, "direction"), ["north"])
        cells = exits["rows"][0]["cells"]
        self.assertEqual(cells["exit"]["value"], f"#{self.door.pk}")
        self.assertEqual(cells["destination"]["value"], f"#{self.there.pk}")
        self.assertEqual(cells["destination"]["link"]["kind"], "rooms")
        self.assertEqual(cells["exit"]["link"]["kind"], "object")

    def test_occupants_are_grouped_by_kind(self):
        detail = rooms.detail(self.here)
        occupants = section_of(detail, "occupants")
        self.assertEqual(group_titles(occupants), ["NPC"])
        self.assertEqual(occupants["groups"][0]["rows"][0]["value"], f"#{self.npc.pk}")
        self.assertEqual(occupants["groups"][0]["rows"][0]["link"]["kind"], "npcs")
        self.assertLessEqual({"npcs"}, link_kinds(occupants))

    def test_empty_room_reports_an_empty_occupant_payload(self):
        detail = rooms.detail(self.there)
        occupants = section_of(detail, "occupants")
        self.assertEqual(occupants["type"], "empty")

    def test_a_non_instance_room_reports_an_empty_instance_section(self):
        detail = rooms.detail(self.here)
        instance = section_of(detail, "instance")
        self.assertEqual(instance["type"], "empty")
        self.assertIsNone(read_attr(self.here, "expire_tick", default=None))

    def test_instance_room_reports_lifetime_naming_and_owned_entities(self):
        instance_room = create.create_object(InstanceRoom, key="t_reader_instance")
        instance_room.db.expire_tick = 7200
        instance_room.db.named = True
        instance_room.db.pin_reasons = ["t_story_pin"]
        instance_room.db.owned_entities = [self.npc]
        instance_room.db.origin_room = self.here
        section = section_of(rooms.detail(instance_room), "instance")
        self.assertEqual(group_titles(section), ["實例狀態", "擁有的實體"])
        state = section["groups"][0]["rows"]
        values = {row["label"]: row["value"] for row in state}
        self.assertEqual(values["到期 tick"], 7200)
        self.assertEqual(values["已命名"], "是")
        self.assertEqual(values["釘住原因"], "t_story_pin")
        self.assertEqual(values["來源房間"], f"#{self.here.pk}")
        owned = section["groups"][1]["rows"]
        self.assertEqual(owned[0]["link"]["kind"], "object")
        self.assertEqual(link_ids(section, "object"), [str(self.npc.pk)])

    @covers_requirement("gm-runtime-state::protected-read-only-inspection-boundary")
    def test_a_missing_expire_tick_reads_as_promoted_without_creating_it(self):
        instance_room = create.create_object(InstanceRoom, key="t_reader_instance_open")
        before = stored_attribute_keys(instance_room)
        detail = rooms.detail(instance_room)
        # With no owned entities the instance projection is a plain ledger.
        state = section_of(detail, "instance")["rows"]
        values = {row["label"]: row["value"] for row in state}
        self.assertEqual(values["到期 tick"], "已提升為永久")
        self.assertIsNone(read_attr(instance_room, "expire_tick", default=None))
        self.assertEqual(stored_attribute_keys(instance_room), before)

    def test_list_item_is_summary_only(self):
        item = rooms.item_of(self.here)
        self.assertEqual(item["kind"], "rooms")
        self.assertEqual(item["id"], str(self.here.pk))
        self.assertEqual(
            [field["label"] for field in item["fields"]],
            ["地點類型", "座標", "出口數"],
        )

    def test_reading_a_room_creates_no_attributes(self):
        before = stored_attribute_keys(self.here)
        rooms.detail(self.here)
        rooms.item_of(self.here)
        self.assertEqual(stored_attribute_keys(self.here), before)
