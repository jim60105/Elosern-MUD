"""Tests for the version-1 ``objectives`` presentation panel (webclient-align-06).

Presenter shape (quest-log order, describe-seam reuse, host-independent
availability, integer reward copper, deadline line), empty-tracked availability,
terminal/untracked omission, corrupt-log degradation, and pure validator
rejections. ``covers_requirement`` annotations land at the change's archive/sync
commit (magic-xp P1 precedent).
"""

from copy import deepcopy
import json
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.objectives import (
    MAX_OBJECTIVE_LINE_CODE_POINTS,
    MAX_QUEST_ID_CODE_POINTS,
    OBJECTIVES_MAX_ROWS,
    OBJECTIVES_SCHEMA_VERSION,
    ObjectivesPanelError,
    validate_objectives,
)
from web.webclient.presentation.registry import UNAVAILABLE_REASON, build_production_registry
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    register_quest_definition,
)
from world.quests.describe import describe_deadline, describe_objective
from world.quests.runtime import (
    MAX_TRACKED_QUESTS,
    QuestRecord,
    QuestState,
    accept_quest,
    set_quest_tracked,
    to_storage,
)
from world.quests.tests._fixtures import defeat, quest, register
from world.quests.transitions import apply_quest_log_replacement
from world.rules.clock import get_world_clock
from world.rules.guild import REGISTRATION_TRAIT_KEYS
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
    register_guild_offer,
)

TICK = 1000
UNAVAILABLE_PAYLOAD = {
    "schema_version": OBJECTIVES_SCHEMA_VERSION,
    "available": False,
    "reason": {
        "code": UNAVAILABLE_REASON[0],
        "message": UNAVAILABLE_REASON[1],
    },
}


def _registration(branch_key="guild_branch_altoria"):
    return {
        "branch_key": branch_key,
        "registered_tick": 0,
        "displayed_stats": {key: 0 for key in REGISTRATION_TRAIT_KEYS},
    }


class ObjectivesPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self._def_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        get_world_clock()._persist(TICK)
        self.room = create_object(Room, key="plain room")
        self.player = create_object(PlayerCharacter, key="objective-tester", location=self.room)
        self.registry = build_production_registry()
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._def_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()

    def _render(self):
        return self.registry.render("objectives", self.context)

    def test_cap_mirrors_runtime_cap(self):
        self.assertEqual(OBJECTIVES_MAX_ROWS, MAX_TRACKED_QUESTS)

    def test_empty_tracked_quests_is_available_with_empty_rows(self):
        payload = self._render()
        self.assertEqual(
            payload,
            {
                "schema_version": OBJECTIVES_SCHEMA_VERSION,
                "available": True,
                "rows": [],
            },
        )

    def test_tracked_active_quest_serializes_with_describe_seams(self):
        # 2 stages, deadline 72h, offer reward 80 copper.
        stage_zero = QuestStage(index=0, objective=defeat("low", quantity=1))
        stage_one = QuestStage(index=1, objective=defeat("low", quantity=5))
        def_record = register(
            QuestDefinition(
                key="tracked_def",
                display_name="討伐哥布林精銳",
                quest_type=QuestType.DEFEAT,
                rank="F",
                stages=(stage_zero, stage_one),
                deadline_hours=72,
            )
        )
        register_guild_offer(
            GuildQuestOffer(
                definition_key=def_record.key,
                issuer_branch_key="guild_branch_altoria",
                reward=QuestReward(copper=80, items=(), merit=10),
            )
        )
        self.player.db.guild_registration = _registration()
        record = accept_quest(self.player, def_record.key)
        # Advance to stage 1, progress 2.
        advanced = QuestRecord(
            quest_id=record.quest_id,
            definition_key=record.definition_key,
            state=QuestState.IN_PROGRESS,
            stage_index=1,
            stage_progress=2,
            deadline_tick=record.deadline_tick,
            accepted_tick=record.accepted_tick,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
            tracked=True,
        )
        apply_quest_log_replacement(self.player, [advanced])

        payload = self._render()
        self.assertEqual(payload["schema_version"], OBJECTIVES_SCHEMA_VERSION)
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["rows"]), 1)
        row = payload["rows"][0]
        self.assertEqual(row["quest_id"], record.quest_id)
        self.assertEqual(row["display_name"], def_record.display_name)
        self.assertEqual(row["objective_line"], describe_objective(stage_one.objective))
        self.assertEqual(row["stage_index"], 1)
        self.assertEqual(row["stage_total"], 2)
        self.assertEqual(row["stage_progress"], 2)
        self.assertEqual(row["objective_quantity"], 5)
        self.assertEqual(row["reward_copper"], 80)
        self.assertEqual(
            row["deadline_line"], describe_deadline(record.deadline_tick, TICK)
        )

    def test_host_independent_outside_guild_hall(self):
        # The room has no GuildStaff host, yet the objectives panel renders.
        def_record = register(quest("outdoor_quest"))
        record = accept_quest(self.player, def_record.key)
        set_quest_tracked(self.player, record.quest_id, True)
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["rows"]), 1)
        self.assertEqual(payload["rows"][0]["quest_id"], record.quest_id)
        # Without registration, reward_copper is null.
        self.assertIsNone(payload["rows"][0]["reward_copper"])

    def test_untracked_and_terminal_records_are_omitted(self):
        d1 = register(quest("q_active_tracked_1"))
        d2 = register(quest("q_active_untracked"))
        d3 = register(quest("q_active_tracked_2"))
        d4 = register(quest("q_failed_tracked"))

        r1 = accept_quest(self.player, d1.key)
        r2 = accept_quest(self.player, d2.key)
        r3 = accept_quest(self.player, d3.key)
        r4 = accept_quest(self.player, d4.key)

        set_quest_tracked(self.player, r1.quest_id, True)
        set_quest_tracked(self.player, r3.quest_id, True)
        set_quest_tracked(self.player, r4.quest_id, True)

        # Abandon r4 (becomes FAILED).
        from world.quests.runtime import abandon_quest
        abandon_quest(self.player, r4.quest_id)

        payload = self._render()
        self.assertEqual(
            [row["quest_id"] for row in payload["rows"]],
            [r1.quest_id, r3.quest_id],
        )

    def test_corrupt_quest_log_degrades_to_shared_unavailable_form(self):
        self.player.db.quest_log = [{"junk": "entry"}]
        payload = self._render()
        self.assertEqual(payload, UNAVAILABLE_PAYLOAD)

    def test_creation_pending_degrades_to_shared_unavailable_form(self):
        self.player.creation_pending = True
        payload = self._render()
        self.assertEqual(payload, UNAVAILABLE_PAYLOAD)

    @staticmethod
    def _json_default(obj):
        if hasattr(obj, "items"):
            return dict(obj.items())
        if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
            return list(obj)
        raise TypeError(f"Unserializable: {type(obj)}")

    def test_presenter_is_read_only(self):
        d = register(quest("ro_quest"))
        record = accept_quest(self.player, d.key)
        set_quest_tracked(self.player, record.quest_id, True)
        before = json.dumps(self.player.db.quest_log or [], default=self._json_default)
        self._render()
        self.assertEqual(json.dumps(self.player.db.quest_log or [], default=self._json_default), before)


class ObjectivesValidatorTests(unittest.TestCase):
    def _valid_row(self, **overrides):
        row = {
            "quest_id": "introductory_hunt:1",
            "display_name": "討伐低階魔物",
            "objective_line": "討伐 1 隻低階魔物",
            "stage_index": 0,
            "stage_total": 1,
            "stage_progress": 0,
            "objective_quantity": 1,
            "reward_copper": 50,
            "deadline_line": "期限：剩餘 72 小時",
        }
        row.update(overrides)
        return row

    def _valid_payload(self, **overrides):
        payload = {
            "schema_version": OBJECTIVES_SCHEMA_VERSION,
            "available": True,
            "rows": [self._valid_row()],
        }
        payload.update(overrides)
        return payload

    def test_valid_payload_normalizes_cleanly(self):
        payload = self._valid_payload()
        self.assertEqual(validate_objectives(payload), payload)

    def test_null_reward_and_null_deadline_are_permitted(self):
        row = self._valid_row(reward_copper=None, deadline_line=None)
        payload = self._valid_payload(rows=[row])
        self.assertEqual(validate_objectives(payload), payload)

    def test_fourth_row_is_rejected(self):
        rows = [self._valid_row(quest_id=f"q:{i}") for i in range(4)]
        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=rows))

    def test_duplicate_quest_id_is_rejected(self):
        rows = [self._valid_row(quest_id="q:1"), self._valid_row(quest_id="q:1")]
        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=rows))

    def test_missing_or_unknown_row_keys_rejected(self):
        row_missing = self._valid_row()
        del row_missing["stage_progress"]
        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=[row_missing]))

        row_extra = self._valid_row(extra_field=True)
        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=[row_extra]))

    def test_negative_or_bad_type_numbers_rejected(self):
        for bad in (-1, "0", 1.5, True):
            with self.assertRaises(ProtocolValidationError):
                validate_objectives(self._valid_payload(rows=[self._valid_row(stage_progress=bad)]))

        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=[self._valid_row(reward_copper=-1)]))

        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=[self._valid_row(reward_copper="50")]))

    def test_empty_or_over_bound_strings_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=[self._valid_row(quest_id="")]))
        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=[self._valid_row(display_name=" ")]))
        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=[self._valid_row(objective_line="a" * (MAX_OBJECTIVE_LINE_CODE_POINTS + 1))]))

    def test_unpaired_surrogates_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_objectives(self._valid_payload(rows=[self._valid_row(display_name="bad\ud800name")]))

    def test_unavailable_form_rejected_by_available_validator(self):
        with self.assertRaises(ProtocolValidationError):
            validate_objectives({"schema_version": 1, "available": False, "rows": []})
