"""Deterministic title state, predicates, planner, and guild-pairing tests.

Covers the title-system storage contract (D1/D4/D5/D8): the strict fail-closed
reader, the compose matrix, dedupe/idempotent banking with D8 auto-equip, the
swap-only equip surface with leak-free stable rejections, the seven predicate
families, the event-effect planner's commit-window grant (a notification only
survives when the outer settlement commits), and the guild pairing (starter
pair on registration, rank title on promotion) with rollback that can neither
lose nor double-grant. Also pins the structural invariant that no
delete/unequip mutator exists anywhere in the module or its command.
"""

from tools.spec_traceability import covers_requirement

import functools
import inspect
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.titles import (
    FIXED_TITLE_REGISTRY,
    STARTER_EPITHET,
    FixedTitleDef,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.rules import titles as titles_module
from world.rules.action import (
    CommitFailed,
    PendingEffect,
    _EVENT_EFFECT_PLANNERS,
    _commit,
    ActionRequest,
)
from world.rules.cast_settlement import settle_out_of_combat_cast
from world.rules.clock import CLOCK_YAML, WorldClock, _EVENT_SOURCES
from world.rules.event_log import EventEntry, EventLog, render_plain_text
from world.rules.guild import register_adventurer
from world.rules.titles import (
    DECLINED_LOG_KEY,
    MAX_DECLINE_RECORDS,
    MAX_TITLE_ENTRIES,
    PENDING_BALLOT_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    TitleEquipError,
    accept_epithet,
    bank_epithet,
    bank_fixed,
    banked_epithets,
    banked_fixed_keys,
    compose_full_title,
    compose_title,
    decline_epithet_ballot,
    decline_records,
    declined_digest,
    equip_epithet,
    equip_fixed,
    fixed_display_name,
    grant_rank_title,
    grant_starter_pair,
    nomination_cooldown_active,
    nomination_suppressed,
    owned_epithet_displays,
    persist_nomination_ballot,
    predicate_satisfied,
    read_pending_ballot,
    read_title_state,
    register_title_planner,
    safe_full_title,
    safe_pending_ballot,
    title_context_entries,
    title_event_effect_planner,
)
from world.rules.tests.test_cast_settlement import (
    _CastSettlementTestCase,
    _raising_stage,
)

_FIXED = {"kind": "fixed", "key": "g_f_rank", "granted_tick": 3}
_EPITHET = {
    "kind": "epithet",
    "display": "南門新客",
    "origin_quote": "你在南門守衛的目送下踏入阿爾托利亞。",
    "granted_tick": 4,
}

# A counter-driven row used only by tests: the shipped registry holds the
# seven guild pairings, so the injectable faces are exercised here instead.
_COUNTER_ROW_KEY = "t_watched_legend"
_COUNTER_ROW = FixedTitleDef(
    _COUNTER_ROW_KEY,
    "受矚者",
    TitleCategory.ROMANCE,
    "众人的目光落在你身上，你已不再闪避。",
    "累積足夠的被觀看次數即可獲得。",
    TitlePredicate(
        family=TitlePredicateFamily.COUNTER_THRESHOLD, counter="watched_count", threshold=1
    ),
)

def _with_counter_row(func):
    """Run one test with the counter-driven row injected into the registry.

    The patch has to outlive the grant: composition resolves a banked key
    through the live registry, so an assertion made after the context closes
    would (correctly) see the key fallback rather than the display name.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # The published registry is an immutable proxy, so the seam replaces
        # the module attribute wholesale (merged with the shipped rows) for
        # the duration of the test.
        with patch(
            "world.rules.titles.FIXED_TITLE_REGISTRY",
            {**FIXED_TITLE_REGISTRY, _COUNTER_ROW_KEY: _COUNTER_ROW},
        ):
            return func(self, *args, **kwargs)

    return wrapper




def _event_log(*entries: EventEntry) -> EventLog:
    return EventLog(
        actor="tester",
        skill_key="basic_attack",
        targets=("monster",),
        entries=entries,
        time_cost_seconds=1,
    )


def _defeated(tier: str, target_id: int = 7) -> EventEntry:
    return EventEntry(
        kind="target_defeated",
        actor="tester",
        target="monster",
        data={"target_id": target_id, "monster_tier": tier},
        text_template="{actor}擊敗{target}",
    )


class _Request:
    """Minimal action-request surrogate carrying only an actor."""

    def __init__(self, actor):
        self.actor = actor


class TitleStateTests(EvenniaTest):
    """The two attributes, the strict reader, and the swap-only surface."""

    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="title-state-holder")

    def _prime(self, collection, equipped):
        self.entity.attributes.add(TITLE_COLLECTION_KEY, collection)
        self.entity.attributes.add(TITLE_EQUIPPED_KEY, equipped)

    @covers_requirement("title-system::title-state-is-a-two-kind-collection-and-a-two-slot-equip-record")
    def test_missing_attributes_read_as_the_empty_state(self):
        self.assertEqual(
            read_title_state(self.entity), ([], {"fixed": None, "epithet": None})
        )
        self.assertEqual(compose_full_title(self.entity), "")
        self.assertEqual(banked_fixed_keys(self.entity), ())
        self.assertEqual(banked_epithets(self.entity), ())
        self.assertEqual(title_context_entries(self.entity), ())

    @covers_requirement("title-system::compose-title-is-the-single-pure-composition-of-the-full-title")
    def test_compose_matrix_joins_non_empty_parts_fixed_first(self):
        self.assertEqual(compose_title(None, None), "")
        self.assertEqual(compose_title("F級冒險者", None), "F級冒險者")
        self.assertEqual(compose_title(None, "南門新客"), "南門新客")
        self.assertEqual(compose_title("F級冒險者", "南門新客"), "F級冒險者　南門新客")

    def test_fixed_key_resolves_to_the_registry_display(self):
        self.assertEqual(fixed_display_name("g_s_rank"), "S級傳說")
        # An unregistered key degrades to the key itself, never to a guess.
        self.assertEqual(fixed_display_name("g_unknown"), "g_unknown")

    @covers_requirement("title-system::compose-title-is-the-single-pure-composition-of-the-full-title")
    def test_compose_reads_only_the_equipped_slots(self):
        self._prime(
            [
                _FIXED,
                {**_FIXED, "key": "g_e_rank"},
                _EPITHET,
                {**_EPITHET, "display": "夜行者"},
            ],
            {"fixed": "g_e_rank", "epithet": "夜行者"},
        )
        self.assertEqual(compose_full_title(self.entity), "E級斥候　夜行者")

    @covers_requirement("title-system::slot-non-empty-is-an-invariant-with-auto-equip-and-no-unequip", "title-system::title-state-is-a-two-kind-collection-and-a-two-slot-equip-record")
    def test_bank_fixed_auto_equips_once_and_dedupes(self):
        self.assertTrue(bank_fixed(self.entity, "g_f_rank", 1))
        collection, equipped = read_title_state(self.entity)
        self.assertEqual(equipped["fixed"], "g_f_rank")
        self.assertEqual(collection[0]["granted_tick"], 1)
        # A duplicate key is a silent no-op: order and tick both stay put.
        self.assertFalse(bank_fixed(self.entity, "g_f_rank", 99))
        self.assertEqual(read_title_state(self.entity)[0], collection)

    @covers_requirement("title-system::slot-non-empty-is-an-invariant-with-auto-equip-and-no-unequip", "title-system::title-state-is-a-two-kind-collection-and-a-two-slot-equip-record")
    def test_bank_epithet_auto_equips_once_and_dedupes(self):
        self.assertTrue(bank_epithet(self.entity, "南門新客", "守衛的目送", 2))
        _, equipped = read_title_state(self.entity)
        self.assertEqual(equipped["epithet"], "南門新客")
        before = read_title_state(self.entity)[0]
        self.assertFalse(bank_epithet(self.entity, "南門新客", "另一段引文", 55))
        self.assertEqual(read_title_state(self.entity)[0], before)

    @covers_requirement("title-system::narrative-consumers-compose-predicates-read-the-collection")
    def test_mechanical_reads_cover_the_whole_collection_not_the_slots(self):
        bank_fixed(self.entity, "g_f_rank", 1)
        bank_fixed(self.entity, "g_e_rank", 2)
        bank_epithet(self.entity, "南門新客", "守衛的目送", 3)
        bank_epithet(self.entity, "夜行者", "夜裡的眼", 4)
        # Only the first entry of each kind auto-equipped; the later ones
        # never touched a slot.
        _, equipped = read_title_state(self.entity)
        self.assertEqual(equipped, {"fixed": "g_f_rank", "epithet": "南門新客"})
        # The mechanical reads still see every banked entry in the collection.
        self.assertEqual(banked_fixed_keys(self.entity), ("g_f_rank", "g_e_rank"))
        self.assertEqual(
            tuple(entry["display"] for entry in banked_epithets(self.entity)),
            ("南門新客", "夜行者"),
        )

    def test_bank_fixed_rejects_malformed_input_without_touching_state(self):
        bank_fixed(self.entity, "g_f_rank", 1)
        bank_epithet(self.entity, "南門新客", "守衛的目送", 1)
        before = deepcopy(read_title_state(self.entity))
        cases = (
            ("", 1),
            ("g_unknown_rank", 1),
            ("S級傳說", 1),
            ("g_e_rank", -1),
            ("g_e_rank", 1.0),
            ("g_e_rank", True),
            ("g_e_rank", "1"),
            (None, 1),
            (7, 1),
        )
        for key, tick in cases:
            with self.subTest(key=key, tick=tick):
                with self.assertRaises(TitleDataError):
                    bank_fixed(self.entity, key, tick)
                self.assertEqual(read_title_state(self.entity), before)

    def test_bank_epithet_rejects_malformed_input_without_touching_state(self):
        from world.rules.titles import MAX_EPITHET_DISPLAY_CODE_POINTS

        bank_fixed(self.entity, "g_f_rank", 1)
        bank_epithet(self.entity, "南門新客", "守衛的目送", 1)
        before = deepcopy(read_title_state(self.entity))
        oversized = "長" * (MAX_EPITHET_DISPLAY_CODE_POINTS + 1)
        cases = (
            ("", "引文", 1),
            ("　", "引文", 1),
            ("   ", "引文", 1),
            ("新異名", "", 1),
            ("新異名", " ", 1),
            (7, "引文", 1),
            ("新異名", 7, 1),
            (None, "引文", 1),
            ("新異名", None, 1),
            (oversized, "引文", 1),
            ("新異名", "引文", -1),
            ("新異名", "引文", 1.5),
        )
        for display, quote, tick in cases:
            with self.subTest(display=display):
                with self.assertRaises(TitleDataError):
                    bank_epithet(self.entity, display, quote, tick)
                self.assertEqual(read_title_state(self.entity), before)
        # The cap itself stays bankable, so the bound is not off-by-one.
        boundary = "長" * MAX_EPITHET_DISPLAY_CODE_POINTS
        self.assertTrue(bank_epithet(self.entity, boundary, "引文", 2))
        self.assertIn(boundary, [e["display"] for e in banked_epithets(self.entity)])

    @covers_requirement("title-system::slot-non-empty-is-an-invariant-with-auto-equip-and-no-unequip", "title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_no_mutator_sequence_empties_an_occupied_slot(self):
        bank_fixed(self.entity, "g_f_rank", 1)
        bank_epithet(self.entity, "南門新客", "守衛的目送", 1)
        sequence = [
            lambda: bank_fixed(self.entity, "g_e_rank", 2),
            lambda: bank_epithet(self.entity, "夜行者", "夜裡的眼", 2),
            lambda: equip_fixed(self.entity, "g_e_rank"),
            lambda: equip_epithet(self.entity, "夜行者"),
            lambda: equip_fixed(self.entity, "g_f_rank"),
            lambda: equip_epithet(self.entity, "南門新客"),
            lambda: bank_fixed(self.entity, "g_d_rank", 3),
        ]
        for step in sequence:
            step()
            _, equipped = read_title_state(self.entity)
            self.assertIsNotNone(equipped["fixed"])
            self.assertIsNotNone(equipped["epithet"])
        # Rejected mutators cannot empty a slot either.
        for attempt in (
            lambda: equip_fixed(self.entity, "S級傳說"),
            lambda: equip_epithet(self.entity, "未存在"),
        ):
            with self.assertRaises(TitleEquipError):
                attempt()
            _, equipped = read_title_state(self.entity)
            self.assertIsNotNone(equipped["fixed"])
            self.assertIsNotNone(equipped["epithet"])

    @covers_requirement("title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_equip_accepts_key_or_display_and_returns_the_display(self):
        bank_fixed(self.entity, "g_f_rank", 1)
        bank_fixed(self.entity, "g_e_rank", 2)
        self.assertEqual(equip_fixed(self.entity, "g_e_rank"), "E級斥候")
        self.assertEqual(compose_full_title(self.entity), "E級斥候")
        self.assertEqual(equip_fixed(self.entity, "F級冒險者"), "F級冒險者")
        self.assertEqual(read_title_state(self.entity)[1]["fixed"], "g_f_rank")
        self.assertEqual(equip_fixed(self.entity, "F級冒險者"), "F級冒險者")
        bank_epithet(self.entity, "南門新客", "守衛的目送", 1)
        bank_epithet(self.entity, "夜行者", "夜裡的眼", 2)
        self.assertEqual(equip_epithet(self.entity, "夜行者"), "夜行者")
        self.assertEqual(compose_full_title(self.entity), "F級冒險者　夜行者")

    @covers_requirement("title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_equip_rejections_name_only_the_request_and_leak_no_candidates(self):
        bank_fixed(self.entity, "g_f_rank", 1)
        bank_epithet(self.entity, "南門新客", "守衛的目送", 1)
        with self.assertRaises(TitleEquipError) as caught:
            equip_fixed(self.entity, "S級傳說")
        message = str(caught.exception)
        self.assertIn("S級傳說", message)
        # No oracle: the rejection never lists what the player does hold.
        for hidden in ("F級冒險者", "南門新客", "g_f_rank"):
            self.assertNotIn(hidden, message)
        # Wrong-kind and unknown identifiers share the same rejection type.
        with self.assertRaises(TitleEquipError):
            equip_fixed(self.entity, "南門新客")
        with self.assertRaises(TitleEquipError):
            equip_epithet(self.entity, "F級冒險者")
        with self.assertRaises(TitleEquipError):
            equip_epithet(self.entity, "g_f_rank")

    def _malformed_states(self):
        return {
            "collection is not a list": ("not a list", {"fixed": None, "epithet": None}),
            "collection holds a non-mapping": (["x"], {"fixed": None, "epithet": None}),
            "entry has unknown fields": (
                [{**_FIXED, "extra": 1}],
                {"fixed": None, "epithet": None},
            ),
            "entry has unknown kind": (
                [{"kind": "rank", "key": "g_f_rank", "granted_tick": 1}],
                {"fixed": None, "epithet": None},
            ),
            "fixed entry misses its key": (
                [{"kind": "fixed", "granted_tick": 1}],
                {"fixed": None, "epithet": None},
            ),
            "epithet entry misses its quote": (
                [{"kind": "epithet", "display": "南門新客", "granted_tick": 1}],
                {"fixed": None, "epithet": None},
            ),
            "granted_tick is boolean": (
                [{**_FIXED, "granted_tick": True}],
                {"fixed": None, "epithet": None},
            ),
            "granted_tick is negative": (
                [{**_FIXED, "granted_tick": -1}],
                {"fixed": None, "epithet": None},
            ),
            "identifier is blank": (
                [{"kind": "epithet", "display": "", "origin_quote": "x", "granted_tick": 1}],
                {"fixed": None, "epithet": None},
            ),
            "duplicate fixed key": (
                [_FIXED, dict(_FIXED)],
                {"fixed": "g_f_rank", "epithet": None},
            ),
            "duplicate epithet display": (
                [_EPITHET, dict(_EPITHET)],
                {"fixed": None, "epithet": "南門新客"},
            ),
            "equipped is not a mapping": ([], "fixed"),
            "equipped has unknown fields": (
                [],
                {"fixed": None, "epithet": None, "extra": 1},
            ),
            "equipped misses a field": ([], {"fixed": None}),
            "equipped slot is blank": ([], {"fixed": "", "epithet": None}),
            "non-empty collection with an empty fixed slot": (
                [_FIXED],
                {"fixed": None, "epithet": None},
            ),
            "non-empty collection with an empty epithet slot": (
                [_EPITHET],
                {"fixed": None, "epithet": None},
            ),
            "fixed slot names an unbanked key": (
                [_FIXED],
                {"fixed": "g_e_rank", "epithet": None},
            ),
            "fixed slot names a banked epithet": (
                [_FIXED, _EPITHET],
                {"fixed": "南門新客", "epithet": "南門新客"},
            ),
            "epithet slot names an unbanked display": (
                [_EPITHET],
                {"fixed": None, "epithet": "夜行者"},
            ),
        }

    @covers_requirement("title-system::title-state-is-a-two-kind-collection-and-a-two-slot-equip-record")
    def test_malformed_state_fails_closed_on_every_surface(self):
        mutators = {
            "read": lambda entity: read_title_state(entity),
            "compose": lambda entity: compose_full_title(entity),
            "bank_fixed": lambda entity: bank_fixed(entity, "g_d_rank", 9),
            "bank_epithet": lambda entity: bank_epithet(entity, "新異名", "引文", 9),
            "equip_fixed": lambda entity: equip_fixed(entity, "g_f_rank"),
            "equip_epithet": lambda entity: equip_epithet(entity, "南門新客"),
            "banked_fixed_keys": lambda entity: banked_fixed_keys(entity),
            "banked_epithets": lambda entity: banked_epithets(entity),
            "context_entries": lambda entity: title_context_entries(entity),
        }
        for label, (collection, equipped) in self._malformed_states().items():
            with self.subTest(state=label):
                self._prime(collection, equipped)
                for name, mutate in mutators.items():
                    with self.assertRaises(TitleDataError, msg=f"{label} via {name}"):
                        mutate(self.entity)
                    # A failing mutator writes nothing: the state stays corrupt
                    # rather than being silently repaired or overwritten.
                    self.assertEqual(
                        self.entity.attributes.get(TITLE_COLLECTION_KEY, default=None),
                        collection,
                    )

    def test_safe_full_title_degrades_for_narrative_surfaces(self):
        self._prime([_FIXED], {"fixed": None, "epithet": None})
        self.assertEqual(safe_full_title(self.entity), "")
        self.assertEqual(safe_full_title(create_object(PlayerCharacter, key="t-blank")), "")

    def test_context_entries_are_bounded_and_most_recent_first(self):
        for index in range(7):
            bank_epithet(self.entity, f"異名{index}", f"引文{index}", index)
        entries = title_context_entries(self.entity)
        self.assertEqual(len(entries), MAX_TITLE_ENTRIES)
        self.assertEqual(
            [entry["display"] for entry in entries],
            ["異名6", "異名5", "異名4", "異名3", "異名2"],
        )
        self.assertEqual(entries[0]["basis"], "引文6")
        self.assertEqual(title_context_entries(self.entity, limit=1), (entries[0],))
        self.assertEqual(title_context_entries(self.entity, limit=0), ())
        for bad_limit in (True, -1, "5", None):
            with self.subTest(limit=bad_limit), self.assertRaises(ValueError):
                title_context_entries(self.entity, limit=bad_limit)

    @covers_requirement("title-system::slot-non-empty-is-an-invariant-with-auto-equip-and-no-unequip", "title-system::title-state-is-a-two-kind-collection-and-a-two-slot-equip-record")
    def test_module_exposes_no_delete_or_unequip_mutator(self):
        forbidden = (
            "clear",
            "remove",
            "delete",
            "unequip",
            "unbank",
            "discard",
            "withdraw",
            "forget",
            "reset",
        )
        defined = {
            name
            for name, member in vars(titles_module).items()
            if not name.startswith("_") and callable(member)
        }
        offenders = {
            name for name in defined for word in forbidden if word in name.lower()
        }
        self.assertEqual(offenders, set())
        # The command surface is swap-only too: no `title clear`, no unequip verb.
        from commands import title as title_command

        methods = {
            name
            for name, member in inspect.getmembers(
                title_command.CmdTitle, predicate=inspect.isfunction
            )
            if not name.startswith("_")
        }
        offenders = {
            name for name in methods for word in forbidden if word in name.lower()
        }
        self.assertEqual(offenders, set())
        source = inspect.getsource(title_command.CmdTitle)
        for word in ("clear", "unequip", "卸下"):
            self.assertNotIn(word, source)


class TitlePredicateTests(EvenniaTest):
    """One focused test per declarative predicate family (D2 §6.2)."""

    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="title-predicate-holder")

    def test_guild_rank_reached_reads_the_current_rank(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank="D"
        )
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.db.guild_rank = "D"
        self.assertTrue(predicate_satisfied(self.entity, _event_log(), predicate))

    def test_first_kill_tier_reads_only_the_current_action_log(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.FIRST_KILL_TIER, monster_tier="high"
        )
        self.assertFalse(
            predicate_satisfied(self.entity, _event_log(_defeated("low")), predicate)
        )
        self.assertTrue(
            predicate_satisfied(self.entity, _event_log(_defeated("high")), predicate)
        )
        # A non-kill entry never satisfies the family, tier data or not.
        self.assertFalse(
            predicate_satisfied(
                self.entity,
                _event_log(
                    EventEntry(
                        kind="damage",
                        actor="tester",
                        target="monster",
                        data={"monster_tier": "high"},
                        text_template="{actor}傷害{target}",
                    )
                ),
                predicate,
            )
        )

    def test_mastery_owned_reads_skill_ownership(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.MASTERY_OWNED, element="fire"
        )
        self.entity.db.skills = {"active": [], "passive": []}
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.db.skills = {"active": ["fire_mastery"], "passive": []}
        self.assertTrue(predicate_satisfied(self.entity, _event_log(), predicate))

    def test_lineage_complete_needs_ownership_and_the_crown_cap(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.LINEAGE_COMPLETE, root_skill_key="fire_lineage"
        )
        self.entity.db.skills = {"active": ["fire_lineage"], "passive": []}
        with patch("world.rules.titles.skill_proficiency_level", return_value=9):
            self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        with patch("world.rules.titles.skill_proficiency_level", return_value=10):
            self.assertTrue(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.db.skills = {"active": [], "passive": []}
        with patch("world.rules.titles.skill_proficiency_level", return_value=10):
            self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))

    def test_quest_completed_tolerates_a_corrupt_log(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.QUEST_COMPLETED, quest_key="introductory_hunt"
        )
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.db.quest_log = [{"not": "a record"}]
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        from world.quests.runtime import QuestRecord, QuestState, to_storage

        record = QuestRecord(
            quest_id="q-1",
            definition_key="introductory_hunt",
            state=QuestState.COMPLETED,
            stage_index=0,
            stage_progress=1,
            deadline_tick=None,
            accepted_tick=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
        )
        self.entity.db.quest_log = [to_storage(record)]
        # Definition consistency is the quest suite's contract; only the
        # predicate's own state matching is under test here.
        with patch("world.quests.runtime.validate_record_runtime"):
            self.assertTrue(predicate_satisfied(self.entity, _event_log(), predicate))

    def test_sexual_experience_reads_the_stored_member_set(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.SEXUAL_EXPERIENCE, experience_type="自慰"
        )
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.attributes.add(
            "experience_types", frozenset({"自慰"}), category="sexual_state"
        )
        self.assertTrue(predicate_satisfied(self.entity, _event_log(), predicate))

    def test_counter_threshold_compares_the_lifetime_counter(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.COUNTER_THRESHOLD, counter="watched_count", threshold=3
        )
        self.entity.attributes.add(
            "sexual_traits",
            {"watched_count": {"trait_type": "counter", "base": 2, "min": 0}},
            category="traits",
        )
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.attributes.add(
            "sexual_traits",
            {"watched_count": {"trait_type": "counter", "base": 3, "min": 0}},
            category="traits",
        )
        self.assertTrue(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.attributes.add(
            "sexual_traits",
            {
                "watched_count": {
                    "trait_type": "counter",
                    "base": "many",
                    "min": 0,
                }
            },
            category="traits",
        )
        with self.assertRaises(TitleDataError):
            predicate_satisfied(self.entity, _event_log(), predicate)


class TitlePlannerTests(EvenniaTest):
    """The planner stages grants; only the commit applies them (D4/D5)."""

    def setUp(self):
        super().setUp()
        self.planners = dict(_EVENT_EFFECT_PLANNERS)
        self.actor = create_object(PlayerCharacter, key="title-planner-actor")

    def tearDown(self):
        _EVENT_EFFECT_PLANNERS.clear()
        _EVENT_EFFECT_PLANNERS.update(self.planners)
        super().tearDown()

    def _request(self):
        from world.rules.targeting import RoomActionContext

        return ActionRequest(
            actor=self.actor,
            skill_key="basic_attack",
            targets=[],
            context=RoomActionContext(None, {}),
        )

    def _plan(self, *entries):
        return title_event_effect_planner(self._request(), _event_log(*entries))

    @_with_counter_row
    @covers_requirement("title-system::fixed-title-grants-ride-the-triggering-action-s-atomic-transaction")
    def test_planning_writes_nothing_until_the_commit_runs(self):
        self.actor.attributes.add(
            "sexual_traits", {"watched_count": {"trait_type": "counter", "name": "Watched_Count", "base": 4, "min": 0}},
            category="traits"
        )
        effects = self._plan()
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0].surfaces, frozenset({"titles"}))
        self.assertEqual(effects[0].description, f"title_granted|{_COUNTER_ROW_KEY}")
        self.assertEqual(effects[0].notify, "獲得稱號：受矚者")
        self.assertEqual(
            read_title_state(self.actor), ([], {"fixed": None, "epithet": None})
        )
        effects[0].apply()
        self.assertEqual(banked_fixed_keys(self.actor), (_COUNTER_ROW_KEY,))
        self.assertEqual(compose_full_title(self.actor), "受矚者")

    def test_one_grant_per_action_and_key_idempotency(self):
        with patch(
            "world.rules.titles.FIXED_TITLE_REGISTRY",
            {"t_first_high": _FIRST_KILL_ROW},
        ):
            first = title_event_effect_planner(self._request(), _event_log(_defeated("high", 1), _defeated("high", 2)))
            self.assertEqual(len(first), 1)
            first[0].apply()
            self.assertEqual(
                title_event_effect_planner(self._request(), _event_log(_defeated("high", 3))),
                [],
            )

    def test_malformed_foreign_state_skips_rows_and_never_rejects_the_action(self):
        # A predicate reading another subsystem's corrupted storage must not
        # propagate out of the planner: the row grants nothing, the action
        # stands. ``db.skills`` as a non-mapping makes both the handler fold
        # and the no-create fallback fail.
        self.actor.db.skills = [{"active": "basic_attack"}]
        for family, parameter, value in (
            (TitlePredicateFamily.MASTERY_OWNED, "element", "fire"),
            (TitlePredicateFamily.LINEAGE_COMPLETE, "root_skill_key", "firebolt"),
        ):
            with self.subTest(family=family.value):
                row = FixedTitleDef(
                    "t_contained",
                    "受試者",
                    TitleCategory.COMBAT,
                    "風味文字。",
                    "提示文字。",
                    TitlePredicate(family=family, **{parameter: value}),
                )
                with patch("world.rules.titles.FIXED_TITLE_REGISTRY", {"t_contained": row}):
                    with self.assertRaises(TitleDataError):
                        predicate_satisfied(self.actor, _event_log(), row.predicate)
                    self.assertEqual(self._plan(), [])

    def test_malformed_proficiency_state_fails_the_lineage_row_closed(self):
        row = FixedTitleDef(
            "t_lineage",
            "宗師",
            TitleCategory.SPELL,
            "風味文字。",
            "提示文字。",
            TitlePredicate(
                family=TitlePredicateFamily.LINEAGE_COMPLETE,
                root_skill_key="basic_attack",
            ),
        )
        self.actor.db.skill_proficiency = {"basic_attack": "not-a-number"}
        with patch("world.rules.titles.FIXED_TITLE_REGISTRY", {"t_lineage": row}):
            with self.assertRaises(TitleDataError):
                predicate_satisfied(self.actor, _event_log(), row.predicate)
            self.assertEqual(self._plan(), [])

    def test_an_uneventful_action_stages_nothing(self):
        self.assertEqual(title_event_effect_planner(self._request(), _event_log()), [])

    def test_shipped_guild_rows_are_satisfied_by_the_current_rank(self):
        self.actor.db.guild_rank = "C"
        effects = title_event_effect_planner(self._request(), _event_log())
        self.assertEqual([effect.notify for effect in effects], ["獲得稱號：C級騎士"])
        for effect in effects:
            effect.apply()
        self.assertEqual(banked_fixed_keys(self.actor), ("g_c_rank",))
        self.assertEqual(compose_full_title(self.actor), "C級騎士")
        self.assertEqual(title_event_effect_planner(self._request(), _event_log()), [])

    def test_every_shipped_row_is_reachable_through_its_own_predicate(self):
        # The registry's seven rows are all guild pairings: each one fires for
        # exactly its rank and for no other rank.
        for rank, definition in sorted(GUILD_RANK_REGISTRY.items()):
            with self.subTest(rank=rank):
                holder = create_object(PlayerCharacter, key=f"t-plan-{rank}")
                holder.db.guild_rank = rank
                effects = title_event_effect_planner(_Request(holder), _event_log())
                self.assertEqual([effect.description for effect in effects], [f"title_granted|{definition.title_key}"])

    @_with_counter_row
    def test_corrupted_title_state_stages_nothing_instead_of_rejecting_the_action(self):
        self.actor.attributes.add(
            "sexual_traits", {"watched_count": {"trait_type": "counter", "name": "Watched_Count", "base": 4, "min": 0}},
            category="traits"
        )
        self.actor.attributes.add(TITLE_COLLECTION_KEY, "damaged")
        self.assertEqual(self._plan(), [])

    def test_non_player_actors_are_never_granted_titles(self):
        npc = create_object(NPC, key="title-planner-npc")
        self.assertEqual(title_event_effect_planner(_Request(npc), _event_log()), [])

    @_with_counter_row
    def test_a_corrupted_counter_skips_only_its_own_row(self):
        self.actor.attributes.add(
            "sexual_traits", {"watched_count": "not-a-trait-record"}, category="traits"
        )
        # The counter row's predicate fails closed and is skipped; the action
        # is never rejected, and a row reading healthy state still fires.
        self.assertEqual(self._plan(), [])
        self.actor.db.guild_rank = "D"
        self.assertEqual(
            [effect.description for effect in self._plan()],
            ["title_granted|g_d_rank"],
        )

    def test_registration_is_idempotent_in_the_planner_registry(self):
        register_title_planner()
        register_title_planner()
        self.assertIs(
            _EVENT_EFFECT_PLANNERS["title"], titles_module.title_event_effect_planner
        )
        _EVENT_EFFECT_PLANNERS.pop("title", None)
        self.assertNotIn("title", _EVENT_EFFECT_PLANNERS)


_FIRST_KILL_ROW = FixedTitleDef(
    "t_first_high",
    "高階獵手",
    TitleCategory.COMBAT,
    "你把第一隻高階魔物留在身後。",
    "擊敗第一隻高階魔物即可獲得。",
    TitlePredicate(
        family=TitlePredicateFamily.FIRST_KILL_TIER, monster_tier="high"
    ),
)


class TitleCommitRollbackTests(EvenniaTest):
    """A failed commit restores title state exactly (no lost or double grant)."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="title-commit-actor")

    def _bank_effect(self, key="g_f_rank"):
        return PendingEffect(
            self.actor,
            f"title_granted|{key}",
            frozenset({"titles"}),
            lambda: bank_fixed(self.actor, key, 5),
            notify=f"獲得稱號：{fixed_display_name(key)}",
        )

    def _raising_effect(self):
        return PendingEffect(
            self.actor,
            "injected failure",
            frozenset({"titles"}),
            lambda: (_ for _ in ()).throw(RuntimeError("injected")),
        )

    def test_failed_commit_restores_absent_title_state(self):
        with self.assertRaises(CommitFailed):
            _commit([self._bank_effect(), self._raising_effect()])
        self.assertEqual(
            read_title_state(self.actor), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.actor.attributes.has(TITLE_COLLECTION_KEY))

    def test_failed_commit_restores_a_pre_existing_collection(self):
        bank_fixed(self.actor, "g_f_rank", 1)
        before = deepcopy(read_title_state(self.actor))
        with self.assertRaises(CommitFailed):
            _commit([self._bank_effect("g_e_rank"), self._raising_effect()])
        self.assertEqual(read_title_state(self.actor), before)

    def test_a_successful_commit_grants_once(self):
        _commit([self._bank_effect("g_f_rank")])
        self.assertEqual(banked_fixed_keys(self.actor), ("g_f_rank",))


class TitleCastGrantSettlementTests(_CastSettlementTestCase):
    """The planner grant rides the cast's outer settlement transaction."""

    def setUp(self):
        super().setUp()
        self.planners = dict(_EVENT_EFFECT_PLANNERS)
        register_title_planner()
        self.char1.db.disguised_stats = {"atk_phys": 1}
        # Raised through the sanctioned mutator: a hand-forced one-key
        # ``sexual_traits`` record is not durable on an actor whose sexual
        # handler is mounted (the proxy flushes its own record back).
        for _ in range(3):
            self.char1.sexual.record_watched()

    def tearDown(self):
        _EVENT_EFFECT_PLANNERS.clear()
        _EVENT_EFFECT_PLANNERS.update(self.planners)
        super().tearDown()

    def _settle(self, clock):
        return settle_out_of_combat_cast(self._request(), clock=clock)

    @_with_counter_row
    @covers_requirement("title-system::fixed-title-grants-ride-the-triggering-action-s-atomic-transaction")
    def test_grant_and_notification_commit_with_the_cast(self):
        settlement = self._settle(WorldClock())
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ("獲得稱號：受矚者",))
        self.assertEqual(banked_fixed_keys(self.char1), (_COUNTER_ROW_KEY,))
        self.assertEqual(compose_full_title(self.char1), "受矚者")

    @_with_counter_row
    def test_a_second_cast_neither_regrants_nor_notifies(self):
        self._settle(WorldClock())
        settlement = self._settle(WorldClock())
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ())
        self.assertEqual(banked_fixed_keys(self.char1), (_COUNTER_ROW_KEY,))

    @_with_counter_row
    @covers_requirement("title-system::fixed-title-grants-ride-the-triggering-action-s-atomic-transaction")
    def test_clock_boundary_failure_rolls_the_grant_back_and_drops_the_notice(self):
        _EVENT_SOURCES["shop_hours"] = _raising_stage()
        with self.assertRaises(RuntimeError):
            self._settle(WorldClock())
        self.assertEqual(
            read_title_state(self.char1), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.char1.attributes.has(TITLE_COLLECTION_KEY))
        self.assertIsNone(self._raw_attribute(self.char1, TITLE_COLLECTION_KEY))
        # Restore the shipped boundary stages (the injected key may not have
        # existed before): clear-then-update mirrors the class's own teardown.
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self._sources)
        settlement = self._settle(WorldClock())
        self.assertEqual(settlement.notifications, ("獲得稱號：受矚者",))
        self.assertEqual(banked_fixed_keys(self.char1), (_COUNTER_ROW_KEY,))

    @_with_counter_row
    def test_final_clock_persistence_failure_rolls_the_grant_back(self):
        clock = WorldClock()
        clock._persist = lambda tick: (_ for _ in ()).throw(
            RuntimeError("simulated persist failure")
        )
        with self.assertRaises(RuntimeError):
            self._settle(clock)
        self.assertEqual(
            read_title_state(self.char1), ([], {"fixed": None, "epithet": None})
        )
        self.assertIsNone(self._raw_attribute(self.char1, TITLE_EQUIPPED_KEY))


class TitleGuildPairingTests(EvenniaTest):
    """Registration banks the starter pair; promotion banks the rank title."""

    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.room = create_object(Room, key="title guild lobby")
        self.player = create_object(PlayerCharacter, key="title guild player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.staff = create_object(NPC, key="title guild staff", location=self.room)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key="guild_branch_altoria"
            )
        )

    @covers_requirement("title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_starter_pair_grants_and_auto_equips_both_slots(self):
        with patch("world.rules.titles.get_world_clock", return_value=WorldClock(42)):
            lines = grant_starter_pair(self.player)
        self.assertEqual(lines, ("獲得稱號：F級冒險者", "獲得異名：南門新客"))
        self.assertEqual(compose_full_title(self.player), "F級冒險者　南門新客")
        collection, equipped = read_title_state(self.player)
        self.assertEqual(equipped, {"fixed": "g_f_rank", "epithet": STARTER_EPITHET.display})
        self.assertEqual([entry["granted_tick"] for entry in collection], [42, 42])
        self.assertEqual(collection[1]["origin_quote"], STARTER_EPITHET.origin_basis)

    def test_a_second_starter_grant_is_silent_and_inert(self):
        first = grant_starter_pair(self.player)
        before = deepcopy(read_title_state(self.player))
        self.assertEqual(grant_starter_pair(self.player), ())
        self.assertEqual(read_title_state(self.player), before)
        self.assertEqual(first, ("獲得稱號：F級冒險者", "獲得異名：南門新客"))

    @covers_requirement("title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_rank_titles_pair_one_to_one_with_the_guild_ranks(self):
        for rank, definition in GUILD_RANK_REGISTRY.items():
            with self.subTest(rank=rank):
                title_row = FIXED_TITLE_REGISTRY[definition.title_key]
                holder = create_object(PlayerCharacter, key=f"title-rank-{rank}")
                self.assertEqual(
                    grant_rank_title(holder, rank),
                    (f"獲得稱號：{title_row.display_name_zh}",),
                )
                self.assertEqual(compose_full_title(holder), title_row.display_name_zh)
                self.assertEqual(grant_rank_title(holder, rank), ())
        # An unknown rank grants nothing at all.
        self.assertEqual(grant_rank_title(self.player, "Z"), ())
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )

    @covers_requirement("guild-registration::guild-registration-grants-the-paired-starter-titles-atomically", "title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_registration_banks_the_starter_pair(self):
        record = register_adventurer(self.player, staff=self.staff)
        self.assertEqual(
            record["title_notifications"],
            ["獲得稱號：F級冒險者", "獲得異名：南門新客"],
        )
        self.assertEqual(compose_full_title(self.player), "F級冒險者　南門新客")

    @covers_requirement("guild-registration::guild-registration-grants-the-paired-starter-titles-atomically", "title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_registration_rollback_leaves_no_titles_and_cannot_double_grant(self):
        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                register_adventurer(self.player, staff=self.staff)
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.player.attributes.has(TITLE_COLLECTION_KEY))
        # The retry grants each entry exactly once.
        record = register_adventurer(self.player, staff=self.staff)
        self.assertEqual(len(record["title_notifications"]), 2)
        self.assertEqual(len(banked_fixed_keys(self.player)), 1)
        self.assertEqual(len(banked_epithets(self.player)), 1)

    def _arm_exam(self, target_rank: str) -> str:
        """Attach one ACTIVE exam record without running the exam pipeline.

        ``settle_exam_outcome`` only reads the session's mode/exam ID and the
        stored record; spawning the examiner and battlefield is
        ``test_guild_exams.py``'s contract, not the title surface's.
        """
        from world.rules.guild_exams import ExamState, GuildExamRecord, to_storage

        exam_id = f"{self.player.pk}:{target_rank}:1"
        record = GuildExamRecord(
            exam_id=exam_id,
            character_id=int(self.player.pk),
            target_rank=target_rank,
            requested_by="command",
            opponent_id=1,
            session_id=f"guild_exam:{self.player.pk}:1:{target_rank}:1",
            state=ExamState.ACTIVE,
            terminal_reason=None,
        )
        self.player.db.guild_exams = [to_storage(record)]
        return exam_id

    def _settle(self, exam_id: str, outcome: str):
        from world.rules.guild_exams import settle_exam_outcome

        return settle_exam_outcome(
            self.player,
            SimpleNamespace(mode="guild_exam", exam_id=exam_id),
            None,
            outcome,
        )

    @covers_requirement("title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically", "title-system::narrative-consumers-compose-predicates-read-the-collection")
    def test_promotion_banks_the_rank_title_inside_the_transaction(self):
        register_adventurer(self.player, staff=self.staff)
        exam_id = self._arm_exam("E")
        result = self._settle(exam_id, "exam_passed")
        self.assertEqual(result["passed"], True)
        self.assertEqual(result["title_notifications"], ["獲得稱號：E級斥候"])
        self.assertEqual(self.player.guild_rank, "E")
        self.assertEqual(
            banked_fixed_keys(self.player), ("g_f_rank", "g_e_rank")
        )
        # D8: the fixed slot was occupied, so promotion never re-equips.
        _, equipped = read_title_state(self.player)
        self.assertEqual(equipped["fixed"], "g_f_rank")

    def test_a_failed_exam_grants_nothing(self):
        register_adventurer(self.player, staff=self.staff)
        before = deepcopy(read_title_state(self.player))
        result = self._settle(self._arm_exam("E"), "exam_failed")
        self.assertNotIn("title_notifications", result)
        self.assertEqual(self.player.guild_rank, "F")
        self.assertEqual(read_title_state(self.player), before)

    @covers_requirement("title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_promotion_rollback_revokes_the_grant_and_the_notice(self):
        register_adventurer(self.player, staff=self.staff)
        exam_id = self._arm_exam("E")
        before_collection, before_equipped = read_title_state(self.player)
        from world.rules.guild_exams import _read_exams

        with patch(
            "world.rules.titles.grant_rank_title",
            side_effect=RuntimeError("db failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._settle(exam_id, "exam_passed")
        # The rank write, the exam write, and the title write are one unit:
        # the promotion leaves nothing behind.
        self.assertEqual(self.player.guild_rank, "F")
        self.assertEqual([r.state.value for r in _read_exams(self.player)], ["active"])
        self.assertEqual(read_title_state(self.player), (before_collection, before_equipped))
        # Exactly one retry settles and grants once.
        result = self._settle(exam_id, "exam_passed")
        self.assertEqual(result["title_notifications"], ["獲得稱號：E級斥候"])
        self.assertEqual(len(banked_fixed_keys(self.player)), 2)

    def test_exam_pass_fires_observers_once_and_fail_does_not(self):
        from world.rules import guild_exams

        calls: list = []
        observer = lambda actor, rank: calls.append((actor, rank))  # noqa: E731
        guild_exams._EXAM_PASS_OBSERVERS.append(observer)
        self.addCleanup(
            lambda: guild_exams._EXAM_PASS_OBSERVERS.remove(observer)
        )
        register_adventurer(self.player, staff=self.staff)
        failed_id = self._arm_exam("E")
        result = self._settle(failed_id, "exam_failed")
        self.assertIs(result["passed"], False)
        self.assertEqual(calls, [])
        passed_id = self._arm_exam("E")
        self._settle(passed_id, "exam_passed")
        self.assertEqual(calls, [(self.player, "E")])
        # Replay of the settled exam returns early: no second notice.
        replay = self._settle(passed_id, "exam_passed")
        self.assertNotIn("passed", replay)
        self.assertEqual(replay["state"], "passed")
        self.assertEqual(len(calls), 1)

    def test_raising_exam_observer_cannot_break_settlement(self):
        from world.rules import guild_exams

        def explode(*args):
            raise RuntimeError("observer boom")

        guild_exams._EXAM_PASS_OBSERVERS.append(explode)
        self.addCleanup(
            lambda: guild_exams._EXAM_PASS_OBSERVERS.remove(explode)
        )
        register_adventurer(self.player, staff=self.staff)
        result = self._settle(self._arm_exam("E"), "exam_passed")
        self.assertIs(result["passed"], True)
        self.assertEqual(self.player.guild_rank, "E")


_DAY = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]


def _ballot(*pairs):
    return [{"display": display, "basis": basis} for display, basis in pairs]


class EpithetNominationRulesTests(EvenniaTest):
    """Ballot face, suppression/cooldown, and the three rules-layer writers."""

    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="ballot-holder")

    def _persist(self, *pairs):
        return persist_nomination_ballot(self.entity, _ballot(*pairs))

    def test_absent_faces_read_empty(self):
        self.assertEqual(read_pending_ballot(self.entity), ())
        self.assertEqual(safe_pending_ballot(self.entity), ())
        self.assertEqual(decline_records(self.entity), ())
        self.assertFalse(nomination_suppressed(self.entity))

    def test_persist_round_trips_the_ballot(self):
        self.assertTrue(self._persist(("火焰之心", "烧毁匪寨"), ("新月", "月下救人")))
        self.assertEqual(
            read_pending_ballot(self.entity),
            (
                {"display": "火焰之心", "basis": "烧毁匪寨"},
                {"display": "新月", "basis": "月下救人"},
            ),
        )
        self.assertEqual(safe_pending_ballot(self.entity), read_pending_ballot(self.entity))

    def test_persist_rejects_invalid_shapes_without_writing(self):
        cases = [
            [],
            _ballot(("甲名", "事"), ("乙名", "事"), ("丙名", "事"), ("丁名", "事")),
            [{"display": "只有顯示"}],
            [{"display": "", "basis": "空"}],
            [{"display": "甲名", "basis": "事" * 81}],
            [{"display": "甲" * 65, "basis": "短"}],
            "not-a-sequence-of-mappings",
        ]
        for candidates in cases:
            with self.subTest(candidates=str(candidates)[:24]):
                self.assertFalse(persist_nomination_ballot(self.entity, candidates))
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))

    def test_single_pending_ballot_blocks_replacement(self):
        self._persist(("甲名", "一"))
        self.assertFalse(self._persist(("乙名", "二")))
        self.assertEqual(read_pending_ballot(self.entity)[0]["display"], "甲名")

    def test_malformed_ballot_fails_closed(self):
        self.entity.attributes.add(PENDING_BALLOT_KEY, [{"display": "缺 basis"}])
        with self.assertRaises(TitleDataError):
            read_pending_ballot(self.entity)
        self.assertEqual(safe_pending_ballot(self.entity), ())
        self.assertTrue(nomination_suppressed(self.entity))
        self.assertFalse(self._persist(("甲名", "一")))

    def test_accept_without_ballot_is_a_stable_reason(self):
        with self.assertRaises(TitleBallotError) as caught:
            accept_epithet(self.entity, 1)
        self.assertIs(caught.exception.reason, TitleBallotReason.NO_PENDING_BALLOT)

    def test_accept_index_validation(self):
        self._persist(("甲名", "一"), ("乙名", "二"))
        for bad in (0, 3, -1, "1", True, None):
            with self.subTest(index=bad), self.assertRaises(TitleBallotError) as caught:
                accept_epithet(self.entity, bad)
            self.assertIs(
                caught.exception.reason, TitleBallotReason.BALLOT_INDEX_OUT_OF_RANGE
            )
        self.assertEqual(len(read_pending_ballot(self.entity)), 2)

    def test_accept_banks_auto_equips_and_clears(self):
        bank_fixed(self.entity, "g_f_rank", 1)
        self._persist(("火焰之心", "焚盡匪寨"))
        display, banked = accept_epithet(self.entity, 1)
        self.assertEqual((display, banked), ("火焰之心", True))
        collection, equipped = read_title_state(self.entity)
        epithet = [entry for entry in collection if entry["kind"] == "epithet"]
        self.assertEqual(len(epithet), 1)
        self.assertEqual(epithet[0]["origin_quote"], "焚盡匪寨")
        self.assertEqual(epithet[0]["granted_tick"], get_world_clock_tick())
        self.assertEqual(equipped["epithet"], "火焰之心")
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))
        # Accepting never starts a cooldown.
        self.assertFalse(nomination_suppressed(self.entity))

    def test_accept_with_occupied_slot_banks_without_touching_it(self):
        grant_starter_pair(self.entity)
        self._persist(("新月", "月下救人"))
        _, equipped_before = read_title_state(self.entity)
        self.assertEqual(equipped_before["epithet"], STARTER_EPITHET.display)
        accept_epithet(self.entity, 1)
        _, equipped_after = read_title_state(self.entity)
        self.assertEqual(equipped_after["epithet"], STARTER_EPITHET.display)

    def test_duplicate_display_accept_consumes_ballot_without_new_entry(self):
        grant_starter_pair(self.entity)
        self._persist((STARTER_EPITHET.display, "再次入票的事蹟"))
        display, banked = accept_epithet(self.entity, 1)
        self.assertEqual((display, banked), (STARTER_EPITHET.display, False))
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))
        self.assertEqual(len(banked_epithets(self.entity)), 1)

    def test_replay_accept_reports_no_pending_ballot(self):
        self._persist(("甲名", "一"))
        accept_epithet(self.entity, 1)
        with self.assertRaises(TitleBallotError) as caught:
            accept_epithet(self.entity, 1)
        self.assertIs(caught.exception.reason, TitleBallotReason.NO_PENDING_BALLOT)

    def test_accept_failure_restores_every_attribute(self):
        bank_fixed(self.entity, "g_f_rank", 1)
        self._persist(("甲名", "一"))
        before = read_title_state(self.entity)
        with patch.object(
            self.entity.attributes, "remove", side_effect=RuntimeError("db failure")
        ):
            with self.assertRaises(RuntimeError):
                accept_epithet(self.entity, 1)
        self.assertEqual(read_title_state(self.entity), before)
        self.assertEqual(len(read_pending_ballot(self.entity)), 1)
        # One retry after the fault clears everything exactly once.
        accept_epithet(self.entity, 1)
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))
        self.assertEqual(len(banked_epithets(self.entity)), 1)

    def test_decline_records_emits_and_suppresses(self):
        self._persist(("甲名", "一"), ("乙名", "二"))
        event_log = decline_epithet_ballot(self.entity)
        text = render_plain_text(event_log)
        self.assertIn("甲名", text)
        self.assertIn("乙名", text)
        self.assertEqual(event_log.entries[0].kind, "title_epithet_declined")
        self.assertEqual(
            event_log.entries[0].data["displays"], ["甲名", "乙名"]
        )
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))
        records = decline_records(self.entity)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["displays"], ("甲名", "乙名"))
        self.assertTrue(nomination_suppressed(self.entity))

    def test_decline_without_ballot_is_a_stable_reason(self):
        with self.assertRaises(TitleBallotError) as caught:
            decline_epithet_ballot(self.entity)
        self.assertIs(
            caught.exception.reason, TitleBallotReason.NO_PENDING_BALLOT
        )
        self.assertEqual(decline_records(self.entity), ())
        self.assertFalse(nomination_suppressed(self.entity))

    def _force_decline_cycle(self, display: str, tick: int) -> None:
        """Write a ballot directly (cooldown bypass) and decline at ``tick``.

        ``get_world_clock`` builds a fresh instance per call, so the decline
        clock is pinned through the titles-module binding instead of mutating
        one instance.
        """
        from unittest.mock import patch

        from world.rules.clock import WorldClock

        self.entity.attributes.add(PENDING_BALLOT_KEY, _ballot((display, "事蹟")))
        with patch(
            "world.rules.titles.get_world_clock",
            return_value=WorldClock(tick),
        ):
            decline_epithet_ballot(self.entity)

    def test_decline_log_is_bounded_newest_first(self):
        for index in range(1, 6):
            self._force_decline_cycle(f"異名{index}", index * _DAY)
        records = decline_records(self.entity)
        self.assertEqual(len(records), MAX_DECLINE_RECORDS)
        self.assertEqual(records[0]["tick"], 5 * _DAY)
        self.assertEqual(records[0]["displays"], ("異名5",))
        digest = declined_digest(self.entity)
        self.assertEqual(digest, ("異名5", "異名4", "異名3"))

    def test_cooldown_arithmetic_across_boundaries(self):
        self.entity.attributes.add(
            DECLINED_LOG_KEY, [{"tick": 5 * _DAY + 100, "displays": ["甲名"]}]
        )
        # Same day and after the FIRST boundary: suppressed.
        self.assertTrue(nomination_cooldown_active(self.entity, 5 * _DAY + 500))
        self.assertTrue(nomination_cooldown_active(self.entity, 6 * _DAY))
        # The SECOND boundary resumes; multi-day jumps behave by subtraction.
        self.assertFalse(nomination_cooldown_active(self.entity, 7 * _DAY))
        self.assertFalse(nomination_cooldown_active(self.entity, 40 * _DAY))
        # With no ballot stored, suppression is exactly the cooldown.
        self.assertTrue(nomination_suppressed(self.entity, 6 * _DAY))
        self.assertFalse(nomination_suppressed(self.entity, 7 * _DAY))

    def test_bad_now_tick_is_rejected(self):
        self.entity.attributes.add(
            DECLINED_LOG_KEY, [{"tick": 1, "displays": ["甲名"]}]
        )
        for bad in (-1, True, "5"):
            with self.subTest(now=bad), self.assertRaises(TitleDataError):
                nomination_cooldown_active(self.entity, bad)

    def test_ballot_survives_cache_reset(self):
        self._persist(("甲名", "一"))
        self.entity.attributes.reset_cache()
        self.assertEqual(read_pending_ballot(self.entity)[0]["display"], "甲名")

    def test_owned_displays_and_digest_reads(self):
        grant_starter_pair(self.entity)
        self.assertEqual(
                owned_epithet_displays(self.entity),
                frozenset({STARTER_EPITHET.display}),
        )
        self.assertEqual(declined_digest(self.entity), ())
        for bad_limit in (True, -1, "5", None):
            with self.subTest(limit=bad_limit), self.assertRaises(ValueError):
                declined_digest(self.entity, bad_limit)

    def test_persist_rechecks_suppression_after_proposal(self):
        # Race: a ballot appears between the service pre-check and the
        # writer's re-check. The writer must refuse without touching it.
        first = self._persist(("先來", "一"))
        self.assertTrue(first)
        self.assertFalse(self._persist(("後來", "二")))
        self.assertEqual(
            read_pending_ballot(self.entity),
            ({"display": "先來", "basis": "一"},),
        )


def get_world_clock_tick() -> int:
    from world.rules.clock import get_world_clock

    return get_world_clock().tick
