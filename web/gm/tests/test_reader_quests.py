"""Fixed-fixture reader tests: quest records (task 2.3 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
quest-record kind: definition key, issuer, status/stage, progress counters,
bound/ protected targets, deadline, rewards and the owning character — plus the
generated-quest payload — with the owner-scoped record identity preserved. The
``gm-runtime-state::*`` requirement IDs this module covers enter the
traceability index when the change's delta spec is synced at archive.
"""

from __future__ import annotations

from dataclasses import replace

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from world.quests.runtime import QuestRecord, QuestState, read_records
from world.quests.transitions import apply_quest_log_replacement
from world.tests.synthetic_data import (
    SYNTH_GUILD_ISSUER_KEY,
    SYNTH_QUEST_REWARDS,
    SYNTH_QUESTS,
)

from web.gm.readers import quests
from web.gm.readers._entities import stored_attribute_keys
from web.gm.tests._state_support import (
    failed_sections,
    link_kinds,
    open_synthetic_scope,
    row_value,
    section_keys,
    section_of,
)

QUEST_KEY = "t_tarn_messenger"
HUNT_KEY = "t_ember_cull"

EXPECTED_SECTIONS = [
    "identity",
    "definition",
    "targets",
    "stage_room",
    "rewards",
    "payload",
]


class QuestReaderTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        open_synthetic_scope(self, "quest_definitions", "quest_issuances", "items")
        super().setUp()
        self.owner = create.create_object(PlayerCharacter, key="t_reader_quest_owner")
        self.record = self._write_record(QUEST_KEY, SYNTH_GUILD_ISSUER_KEY)

    def _write_record(self, definition_key: str, issuer_key: str, **overrides) -> QuestRecord:
        """Stage one valid stage-zero record through the production writer."""
        record = replace(
            QuestRecord(
                quest_id=f"{definition_key}:1",
                definition_key=definition_key,
                issuer_key=issuer_key,
                state=QuestState.IN_PROGRESS,
                stage_index=0,
                stage_progress=0,
                deadline_tick=None,
                accepted_tick=0,
                stage_room_id=None,
                objective_target_ids=(),
                protected_entity_ids=(),
                failure_reason=None,
            ),
            **overrides,
        )
        apply_quest_log_replacement(self.owner, [*read_records(self.owner), record])
        return record

    def test_detail_exposes_every_curated_quest_section(self):
        detail = quests.detail_for_record(self.record, self.owner)
        self.assertEqual(detail["kind"], "quests")
        self.assertEqual(detail["id"], self.record.quest_id)
        self.assertEqual(detail["owner_dbref"], self.owner.pk)
        self.assertEqual(section_keys(detail), EXPECTED_SECTIONS)
        self.assertEqual(failed_sections(detail), {})

    def test_identity_reports_stage_state_and_the_owning_character_link(self):
        detail = quests.detail_for_record(self.record, self.owner)
        identity = section_of(detail, "identity")
        self.assertEqual(row_value(identity, "任務編號"), self.record.quest_id)
        self.assertEqual(row_value(identity, "定義鍵"), QUEST_KEY)
        self.assertEqual(row_value(identity, "狀態"), "進行中")
        self.assertEqual(row_value(identity, "擁有角色"), f"#{self.owner.pk}")
        owner_row = next(row for row in identity["rows"] if row["label"] == "擁有角色")
        self.assertEqual(owner_row["link"]["kind"], "characters")

    def test_definition_section_reads_the_registered_definition(self):
        detail = quests.detail_for_record(self.record, self.owner)
        definition = section_of(detail, "definition")
        self.assertEqual(
            row_value(definition, "名稱"), SYNTH_QUESTS[QUEST_KEY].display_name
        )
        self.assertEqual(row_value(definition, "目前目標"), "reach")

    def test_rewards_come_from_the_registered_issuance(self):
        detail = quests.detail_for_record(self.record, self.owner)
        rewards = section_of(detail, "rewards")
        self.assertEqual(row_value(rewards, "發布識別"), self.record.issuer_key)
        self.assertEqual(row_value(rewards, "銅幣"), SYNTH_QUEST_REWARDS[QUEST_KEY].copper)
        self.assertEqual(row_value(rewards, "功績"), SYNTH_QUEST_REWARDS[QUEST_KEY].merit)
        # This reward grants no items, so no 物品 row is invented.
        self.assertNotIn("物品", [row["label"] for row in rewards["rows"]])

    def test_an_item_granting_reward_lists_its_items(self):
        hunt = self._write_record(HUNT_KEY, SYNTH_GUILD_ISSUER_KEY)
        rewards = section_of(quests.detail_for_record(hunt, self.owner), "rewards")
        self.assertEqual(row_value(rewards, "銅幣"), SYNTH_QUEST_REWARDS[HUNT_KEY].copper)
        self.assertIn("× 1", row_value(rewards, "物品"))

    def test_a_hunt_record_links_its_bound_targets(self):
        hunt = self._write_record(
            HUNT_KEY, SYNTH_GUILD_ISSUER_KEY, objective_target_ids=(self.obj1.pk,)
        )
        detail = quests.detail_for_record(hunt, self.owner)
        targets = section_of(detail, "targets")
        self.assertEqual(targets["rows"][0]["cells"]["target"]["value"], f"#{self.obj1.pk}")
        self.assertEqual(targets["rows"][0]["cells"]["target"]["link"]["kind"], "object")

    def test_a_generated_quest_is_not_stored_so_its_payload_section_is_empty(self):
        detail = quests.detail_for_record(self.record, self.owner)
        payload = section_of(detail, "payload")
        self.assertEqual(payload["type"], "empty")

    def test_bound_quest_ids_are_scoped_by_their_owner(self):
        records = quests.owner_records(f"#{self.owner.pk}")
        self.assertEqual([record.quest_id for record in records], [self.record.quest_id])
        item = quests.item_of(records[0], self.owner)
        self.assertEqual(item["kind"], "quests")
        self.assertEqual(item["id"], self.record.quest_id)
        self.assertEqual(
            [field["label"] for field in item["fields"]],
            ["定義鍵", "狀態", "階段", "擁有角色"],
        )

    def test_resolve_owner_refuses_a_missing_or_malformed_owner(self):
        for value in (None, "", "not-a-dbref"):
            with self.subTest(owner=value), self.assertRaises(Exception) as raised:
                quests.resolve_owner(value)
            self.assertEqual(raised.exception.code, "invalid_filter")
        with self.assertRaises(Exception) as missing:
            quests.resolve_owner("#999999")
        self.assertEqual(missing.exception.code, "object_not_found")

    def test_generated_quest_projection_reports_the_stored_payload(self):
        payload = {
            "definition": {"key": "t_gen", "name": "合成生成任務"},
            "issuance": {
                "issuer_key": SYNTH_GUILD_ISSUER_KEY,
                "settlement": "counter",
                "reward": {"copper": 7, "merit": 2, "items": []},
            },
            "requirements": ["t_requirement"],
        }
        item = quests.generated_item_of(payload, 3)
        self.assertEqual(item["id"], "generated:3")
        self.assertEqual(item["kind"], "quests")
        self.assertEqual(
            [field["label"] for field in item["fields"]],
            ["定義鍵", "發布識別", "來源"],
        )
        detail = quests.generated_detail(payload)
        self.assertEqual(section_keys(detail), ["identity", "rewards", "requirements", "payload"])
        self.assertEqual(failed_sections(detail), {})
        self.assertEqual(row_value(section_of(detail, "rewards"), "銅幣"), 7)
        self.assertEqual(section_of(detail, "payload")["type"], "tree")

    def test_reading_a_quest_record_writes_nothing(self):
        before = stored_attribute_keys(self.owner)
        quests.owner_records(f"#{self.owner.pk}")
        quests.detail_for_record(self.record, self.owner)
        quests.generated_payloads()
        self.assertEqual(stored_attribute_keys(self.owner), before)

    def test_list_link_kinds_carry_the_owner_identity(self):
        detail = quests.detail_for_record(self.record, self.owner)
        self.assertLessEqual({"characters"}, link_kinds(detail))
