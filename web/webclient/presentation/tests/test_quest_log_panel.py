"""Tests for the version-1 ``quest_log`` presentation panel (change 8).

Presenter shape (stored-order rows, exact field sets, cap truncation,
describe-seam prose parity with the objectives tracker and the services
counter, issuer label resolution, unresolvable-issuance degradation,
host-independent availability, read-only guarantees), strict-reader
degradation, and pure validator rejections. ``covers_requirement``
annotations land at the change's archive/sync commit (objectives panel
P1 precedent): the capability's requirement IDs are unknown to the
current-contract index until then.
"""

import json
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.quest_log import (
    QUEST_LOG_MAX_ROWS,
    QUEST_LOG_SCHEMA_VERSION,
    QuestLogPanelError,
    validate_quest_log,
)
from web.webclient.presentation.registry import (
    UNAVAILABLE_REASON,
    build_production_registry,
)
from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.quests.catalog import register_catalog
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    QuestStage,
    QuestType,
    register_quest_definition,
)
from world.quests.runtime import (
    QuestRecord,
    QuestState,
    fulfill_record,
    set_quest_tracked,
)
from world.quests.tests._fixtures import defeat, quest, register
from world.quests.transitions import apply_quest_log_replacement
from world.rules.clock import get_world_clock
from world.rules.guild import register_adventurer
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
    accept_guild_offer,
    register_guild_offer,
)
from world.rules.quest_issuance import (
    QUEST_ISSUANCE_REGISTRY,
    QuestIssuance,
    Settlement,
    npc_issuer_key,
    register_quest_issuance,
)

TICK = 1000
ALTORIA_BRANCH = "guild_branch_altoria"
UNAVAILABLE_PAYLOAD = {
    "schema_version": QUEST_LOG_SCHEMA_VERSION,
    "available": False,
    "reason": {
        "code": UNAVAILABLE_REASON[0],
        "message": UNAVAILABLE_REASON[1],
    },
}

ROW_FIELDS = {
    "quest_id",
    "definition_key",
    "display_name",
    "state",
    "stage_index",
    "stage_total",
    "stage_progress",
    "objective_quantity",
    "objective_line",
    "deadline_line",
    "detail",
    "tracked",
    "issuer",
    "settlement",
    "reward_line",
    "track",
}


def _registration(branch_key=ALTORIA_BRANCH):
    return {
        "branch_key": branch_key,
        "registered_tick": 0,
        "displayed_stats": {key: 0 for key in REGISTRATION_TRAIT_KEYS},
    }


def _register_auto_commission(definition_key: str, content_key: str) -> str:
    """Register one auto-settled private commission and return its key."""
    issuer_key = npc_issuer_key(content_key=content_key)
    register_quest_issuance(
        QuestIssuance(
            definition_key=definition_key,
            issuer_key=issuer_key,
            reward=QuestReward(copper=40, items=(), merit=0),
            settlement=Settlement.AUTO,
        )
    )
    return issuer_key


class QuestLogPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        # The shipped definitions (``introductory_hunt`` et al.) must be
        # registered before the affinity config loads during
        # ``register_adventurer``: its ``cap_breaks`` reference the catalog.
        register_catalog()
        self._def_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        self._issuance_items = list(QUEST_ISSUANCE_REGISTRY.items())
        get_world_clock()._persist(TICK)
        self.room = create_object(Room, key="plain room")
        self.player = create_object(PlayerCharacter, key="quest-log-tester", location=self.room)
        self.registry = build_production_registry()
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._def_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        QUEST_ISSUANCE_REGISTRY.clear()
        QUEST_ISSUANCE_REGISTRY.update(self._issuance_items)
        super().tearDown()

    def _render(self):
        return self.registry.render("quest_log", self.context)

    def _tracked_active_record(self, record):
        return QuestRecord(
            quest_id=record.quest_id,
            definition_key=record.definition_key,
            issuer_key=record.issuer_key,
            state=QuestState.IN_PROGRESS,
            stage_index=record.stage_index,
            stage_progress=record.stage_progress,
            deadline_tick=record.deadline_tick,
            accepted_tick=record.accepted_tick,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
            tracked=True,
        )

    def test_registry_uses_the_common_unavailable_reason(self):
        spec = self.registry.spec("quest_log")
        self.assertEqual(spec.schema_version, QUEST_LOG_SCHEMA_VERSION)
        self.assertEqual(spec.unavailable_reason, UNAVAILABLE_REASON)

    def test_two_quest_log_serializes_exact_rows(self):
        first = register(quest("log_first"))
        second = register(quest("log_second"))
        r1 = accept_under_auto(self.player, first)
        r2 = accept_under_auto(self.player, second)

        payload = self._render()

        self.assertEqual(payload["schema_version"], QUEST_LOG_SCHEMA_VERSION)
        self.assertTrue(payload["available"])
        self.assertEqual(set(payload), {"schema_version", "available", "rows"})
        self.assertEqual([row["quest_id"] for row in payload["rows"]], [r1.quest_id, r2.quest_id])
        for row in payload["rows"]:
            self.assertEqual(set(row), ROW_FIELDS)
            self.assertEqual(set(row["issuer"]), {"kind", "key", "label"})
            self.assertEqual(set(row["track"]), {
                "action_id", "label", "enabled", "disabled_reason", "quantity",
            })
            self.assertEqual(row["track"]["action_id"], "guild.quest_track")
            self.assertTrue(row["track"]["enabled"])

    def test_empty_log_is_available_with_empty_rows(self):
        payload = self._render()
        self.assertEqual(
            payload,
            {"schema_version": QUEST_LOG_SCHEMA_VERSION, "available": True, "rows": []},
        )

    def test_presenter_mutates_nothing(self):
        definition = register(quest("readonly_quest"))
        record = accept_under_auto(self.player, definition)
        set_quest_tracked(self.player, record.quest_id, True)
        self.player.db.wallet = 500
        before_log = json.dumps(self.player.db.quest_log or [], default=self._json_default)
        self.player.db.inventory = ["healing_potion"]
        before_inventory = json.dumps(list(self.player.db.inventory or []))

        first = self._render()
        second = self._render()

        self.assertEqual(first, second)
        self.assertEqual(json.dumps(self.player.db.quest_log or [], default=self._json_default), before_log)
        self.assertEqual(self.player.db.wallet, 500)
        self.assertEqual(json.dumps(list(self.player.db.inventory or [])), before_inventory)

    def test_log_is_readable_far_from_any_counter(self):
        # The room holds no NPC of any kind; the book still renders every row.
        definition = register(quest("wilderness_quest"))
        record = accept_under_auto(self.player, definition)

        payload = self._render()

        self.assertTrue(payload["available"])
        self.assertEqual([row["quest_id"] for row in payload["rows"]], [record.quest_id])

    def test_private_commission_appears_with_npc_kind_and_auto_settlement(self):
        definition = register(quest("commissioned_quest"))
        issuer_key = _register_auto_commission(definition.key, "grey_granny")
        record = accept_quest_under(self.player, definition.key, issuer_key)

        payload = self._render()

        row = payload["rows"][0]
        self.assertEqual(row["issuer"]["kind"], "npc")
        self.assertEqual(row["issuer"]["key"], issuer_key)
        # The authored name is the entity key, so the label is the remainder.
        self.assertEqual(row["issuer"]["label"], "grey_granny")
        self.assertEqual(row["settlement"], "auto")
        self.assertIn("獎勵：銅 40", row["reward_line"])

    def test_npc_pk_label_resolves_the_live_commissioner(self):
        definition = register(quest("pk_commission"))
        commissioner = create_object(NPC, key="委託人阿土", location=self.room)
        commissioner_pk = commissioner.pk
        issuer_key = npc_issuer_key(pk=commissioner.pk)
        register_quest_issuance(
            QuestIssuance(
                definition_key=definition.key,
                issuer_key=issuer_key,
                reward=QuestReward(copper=10, items=(), merit=0),
                settlement=Settlement.AUTO,
            )
        )
        record = accept_quest_under(self.player, definition.key, issuer_key)

        row = self._render()["rows"][0]
        self.assertEqual(row["issuer"]["kind"], "npc")
        self.assertEqual(row["issuer"]["label"], "委託人阿土")

        # A deleted commissioner falls back to the key remainder.
        commissioner.delete()
        row = self._render()["rows"][0]
        self.assertEqual(row["issuer"]["label"], f"#{commissioner_pk}")

    def test_guild_label_uses_branch_registry_with_remainder_fallback(self):
        staff = create_object(NPC, key="guild master", location=self.room)
        staff.components.add(
            GuildStaff.create(staff, service_id="staff", branch_key=ALTORIA_BRANCH)
        )
        definition = register(quest("branch_label_quest"))
        self.player.race = "human"
        self.player.apply_race_baseline()
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition.key,
                issuer_branch_key=ALTORIA_BRANCH,
                reward=QuestReward(copper=50, items=(), merit=5),
            )
        )
        register_adventurer(self.player, staff=staff)
        record = accept_guild_offer(self.player, staff, definition.key)

        row = self._render()["rows"][0]
        self.assertEqual(row["issuer"]["kind"], "guild")
        self.assertEqual(row["issuer"]["key"], f"guild:{ALTORIA_BRANCH}")
        self.assertEqual(
            row["issuer"]["label"],
            GUILD_BRANCH_REGISTRY[ALTORIA_BRANCH].display_name_zh,
        )
        self.assertEqual(row["settlement"], "counter")

        # An unknown branch falls back to the key remainder.
        orphan = QuestRecord(
            quest_id="orphan_branch:1",
            definition_key=definition.key,
            issuer_key="guild:no_such_branch",
            state=QuestState.IN_PROGRESS,
            stage_index=0,
            stage_progress=0,
            deadline_tick=record.deadline_tick,
            accepted_tick=TICK,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
        )
        apply_quest_log_replacement(self.player, [record, orphan])
        rows = {row["quest_id"]: row for row in self._render()["rows"]}
        self.assertEqual(rows["orphan_branch:1"]["issuer"]["label"], "no_such_branch")
        self.assertIsNone(rows["orphan_branch:1"]["settlement"])
        self.assertIsNone(rows["orphan_branch:1"]["reward_line"])

    def test_quest_book_and_tracker_agree_on_the_same_record(self):
        definition = register(quest("tracker_parity"))
        record = accept_under_auto(self.player, definition)
        set_quest_tracked(self.player, record.quest_id, True)

        quest_log = self._render()["rows"][0]
        objectives = self.registry.render("objectives", self.context)["rows"][0]

        self.assertEqual(quest_log["objective_line"], objectives["objective_line"])
        self.assertEqual(quest_log["deadline_line"], objectives["deadline_line"])

    def test_quest_book_and_counter_agree_with_a_clerk_present(self):
        staff = create_object(NPC, key="parity clerk", location=self.room)
        staff.components.add(
            GuildStaff.create(staff, service_id="staff", branch_key=ALTORIA_BRANCH)
        )
        definition = register(quest("counter_parity"))
        self.player.race = "human"
        self.player.apply_race_baseline()
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition.key,
                issuer_branch_key=ALTORIA_BRANCH,
                reward=QuestReward(copper=80, items=(), merit=10),
            )
        )
        register_adventurer(self.player, staff=staff)
        record = accept_guild_offer(self.player, staff, definition.key)
        set_quest_tracked(self.player, record.quest_id, True)

        quest_row = self._render()["rows"][0]
        services = self.registry.render("services", self.context)
        counter_row = services["guild"]["quests"][0]

        self.assertEqual(counter_row["quest_id"], record.quest_id)
        self.assertEqual(quest_row["objective_line"], counter_row["objective_summary"])
        self.assertEqual(quest_row["deadline_line"], counter_row["deadline_line"])
        self.assertEqual(quest_row["detail"], counter_row["detail"])

    def test_withdrawn_commission_still_lists_its_quest(self):
        definition = register(quest("withdrawn_commission"))
        issuer_key = _register_auto_commission(definition.key, "grey_granny")
        record = accept_quest_under(self.player, definition.key, issuer_key)
        del QUEST_ISSUANCE_REGISTRY[(definition.key, issuer_key)]

        payload = self._render()

        self.assertTrue(payload["available"])
        row = payload["rows"][0]
        self.assertEqual(row["quest_id"], record.quest_id)
        self.assertIsNone(row["reward_line"])
        self.assertIsNone(row["settlement"])
        # No copper, item, or merit figure appears anywhere in the row.
        serialized = json.dumps(row, ensure_ascii=False)
        for forbidden in ("銅", "功績", "獎勵", "治療藥水"):
            self.assertNotIn(forbidden, serialized)

    def test_one_malformed_entry_hides_the_whole_panel_without_repair(self):
        definition = register(quest("degrade_quest"))
        record = accept_under_auto(self.player, definition)
        before = list(self.player.db.quest_log)
        self.player.db.quest_log = [{"quest_id": "broken", "state": "in_progress"}, *before]

        payload = self._render()

        self.assertEqual(payload, UNAVAILABLE_PAYLOAD)
        self.assertEqual(
            self.player.db.quest_log,
            [{"quest_id": "broken", "state": "in_progress"}, *before],
        )

    def test_thirteen_records_truncate_to_the_first_twelve_in_order(self):
        definitions = [register(quest(f"capped_quest_{i}")) for i in range(13)]
        records = [accept_under_auto(self.player, definition) for definition in definitions]

        payload = self._render()

        self.assertEqual(len(payload["rows"]), QUEST_LOG_MAX_ROWS)
        self.assertEqual(
            [row["quest_id"] for row in payload["rows"]],
            [record.quest_id for record in records[:QUEST_LOG_MAX_ROWS]],
        )

    def test_creation_pending_degrades_to_shared_unavailable_form(self):
        self.player.creation_pending = True
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_possessed_puppet_renders_the_owner_records(self):
        definition = register(quest("possessed_owner_quest"))
        record = accept_under_auto(self.player, definition)
        npc = create_object(NPC, key="possessed scout", location=self.room)
        npc.db.possessed_by = self.player.pk
        self.player.db.possession = {"npc_dbid": npc.pk, "since_tick": TICK}

        payload = self.registry.render(
            "quest_log", PresentationContext(actor=npc, protocol_version=1)
        )

        self.assertTrue(payload["available"])
        self.assertEqual(
            [row["quest_id"] for row in payload["rows"]], [record.quest_id]
        )

    def test_completed_record_renders_with_the_terminal_state(self):
        definition = register(
            QuestDefinition(
                key="completable_quest",
                display_name="可完成任務",
                quest_type=QuestType.DEFEAT,
                rank="F",
                stages=(QuestStage(index=0, objective=defeat("low", quantity=1)),),
                deadline_hours=72,
            )
        )
        record = accept_under_auto(self.player, definition)
        completed = fulfill_record(record, QUEST_DEFINITION_REGISTRY[definition.key])
        apply_quest_log_replacement(self.player, [completed])

        row = self._render()["rows"][0]
        self.assertEqual(row["state"], "completed")

    @staticmethod
    def _json_default(obj):
        if hasattr(obj, "items"):
            return dict(obj.items())
        if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
            return list(obj)
        raise TypeError(f"Unserializable: {type(obj)}")


def accept_under_auto(actor, definition):
    """Accept ``definition`` under a fresh auto-settled private commission."""
    return accept_quest_under(actor, definition.key, _ensure_auto(definition.key))


def _ensure_auto(definition_key: str) -> str:
    from world.quests.tests._fixtures import TEST_ISSUER_KEY

    if (definition_key, TEST_ISSUER_KEY) not in QUEST_ISSUANCE_REGISTRY:
        register_quest_issuance(
            QuestIssuance(
                definition_key=definition_key,
                issuer_key=TEST_ISSUER_KEY,
                reward=QuestReward(copper=1, items=(), merit=0),
                settlement=Settlement.AUTO,
            )
        )
    return TEST_ISSUER_KEY


def accept_quest_under(actor, definition_key: str, issuer_key: str):
    from world.quests.runtime import accept_quest

    return accept_quest(actor, definition_key, issuer_key)


class QuestLogValidatorTests(unittest.TestCase):
    def _valid_row(self, **overrides):
        row = {
            "quest_id": "introductory_hunt:1",
            "definition_key": "introductory_hunt",
            "display_name": "討伐低階魔物",
            "state": "in_progress",
            "stage_index": 0,
            "stage_total": 1,
            "stage_progress": 0,
            "objective_quantity": 1,
            "objective_line": "討伐 1 隻低階魔物",
            "deadline_line": "期限：剩餘 72 小時",
            "detail": "可完成任務\n狀態：進行中",
            "tracked": False,
            "issuer": {
                "kind": "guild",
                "key": "guild:guild_branch_altoria",
                "label": "埃洛西恩冒險者公會 阿爾托利亞分會",
            },
            "settlement": "counter",
            "reward_line": "獎勵：銅 50、功績 25",
            "track": {
                "action_id": "guild.quest_track",
                "label": "追蹤",
                "enabled": True,
                "disabled_reason": None,
                "quantity": None,
            },
        }
        row.update(overrides)
        return row

    def _valid_payload(self, **overrides):
        payload = {
            "schema_version": QUEST_LOG_SCHEMA_VERSION,
            "available": True,
            "rows": [self._valid_row()],
        }
        payload.update(overrides)
        return payload

    def test_valid_payload_normalizes_cleanly(self):
        self.assertEqual(validate_quest_log(self._valid_payload()), self._valid_payload())

    def test_null_settlement_reward_and_deadline_are_permitted(self):
        row = self._valid_row(settlement=None, reward_line=None, deadline_line=None)
        self.assertEqual(validate_quest_log(self._valid_payload(rows=[row])), self._valid_payload(rows=[row]))

    def test_thirteenth_row_is_rejected(self):
        rows = [self._valid_row(quest_id=f"q:{i}") for i in range(QUEST_LOG_MAX_ROWS + 1)]
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=rows))

    def test_duplicate_quest_id_is_rejected(self):
        rows = [self._valid_row(quest_id="q:1"), self._valid_row(quest_id="q:1")]
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=rows))

    def test_missing_or_extra_row_keys_are_rejected(self):
        row_missing = self._valid_row()
        del row_missing["stage_total"]
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[row_missing]))
        row_extra = self._valid_row(extra_field=True)
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[row_extra]))

    def test_unknown_state_is_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(state="running")]))
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(state=None)]))

    def test_unknown_settlement_is_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(settlement="later")]))

    def test_settlement_and_reward_line_must_be_null_together(self):
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(settlement=None)])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(reward_line=None)])
            )

    def test_negative_or_bad_type_numbers_are_rejected(self):
        for field in ("stage_index", "stage_progress"):
            with self.assertRaises(ProtocolValidationError):
                validate_quest_log(self._valid_payload(rows=[self._valid_row(**{field: -1})]))
        for field in ("stage_total", "objective_quantity"):
            with self.assertRaises(ProtocolValidationError):
                validate_quest_log(self._valid_payload(rows=[self._valid_row(**{field: 0})]))
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(stage_progress=1.5)]))

    def test_over_bound_strings_fail_closed(self):
        # An over-bound value raises rather than truncating (the shared
        # string helper raises the ProtocolValidationError base; the
        # surrogate and emptiness guards raise the panel subclass).
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(quest_id="a" * 65)]))
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(detail="字" * 513)]))
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(reward_line="銅" * 129)]))
        with self.assertRaises(QuestLogPanelError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(quest_id="")]))
        with self.assertRaises(QuestLogPanelError):
            validate_quest_log(self._valid_payload(rows=[self._valid_row(display_name=" ")]))

    def test_unpaired_surrogates_are_rejected(self):
        with self.assertRaises(QuestLogPanelError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(display_name="bad\ud800name")])
            )
        with self.assertRaises(QuestLogPanelError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(issuer=self._valid_row()["issuer"] | {"label": "\udbff"})])
            )

    def test_issuer_shape_is_exact(self):
        issuer = self._valid_row()["issuer"]
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(issuer={**issuer, "extra": 1})])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(issuer={**issuer, "kind": "monster"})])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(issuer={**issuer, "label": ""})])
            )

    def test_issuer_key_grammar_and_kind_coherence_are_enforced(self):
        issuer = self._valid_row()["issuer"]
        # A malformed key rejects even though its kind is a legal namespace.
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(issuer={**issuer, "key": "not-an-issuer"})])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(issuer={**issuer, "key": "guild:a:b"})])
            )
        # A grammar-valid key under the wrong declared kind rejects.
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(issuer={**issuer, "kind": "npc", "key": f"guild:{ALTORIA_BRANCH}"})])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(issuer={**issuer, "kind": "guild", "key": "npc:grey_granny"})])
            )
        # Every valid form passes: guild, authored npc, and pk npc.
        for kind, key in (
            ("guild", f"guild:{ALTORIA_BRANCH}"),
            ("npc", "npc:grey_granny"),
            ("npc", "npc:#1234"),
        ):
            row = self._valid_row(issuer={**issuer, "kind": kind, "key": key})
            self.assertEqual(validate_quest_log(self._valid_payload(rows=[row])), self._valid_payload(rows=[row]))

    def test_track_descriptor_is_pinned_enabled_without_bounds(self):
        track = self._valid_row()["track"]
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(track={**track, "action_id": "shop.buy"})])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(track={**track, "enabled": False})])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(track={**track, "quantity": {"min": 1, "max": 2}})])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(
                self._valid_payload(rows=[self._valid_row(track={**track, "extra": None})])
            )

    def test_unavailable_form_is_rejected_by_the_available_validator(self):
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log({"schema_version": 1, "available": False, "rows": []})

    def test_panel_key_set_is_exact(self):
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log({**self._valid_payload(), "extra": 1})
        payload = self._valid_payload()
        del payload["rows"]
        with self.assertRaises(ProtocolValidationError):
            validate_quest_log(payload)


if __name__ == "__main__":
    unittest.main()
