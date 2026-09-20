"""Slice of ``test_titles``: TitlePlannerTests."""
from tools.spec_traceability import covers_requirement
import ast
import contextlib
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
from world.lore.titles import (
    FixedTitleDef,
    StarterEpithet,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.rules import titles as titles_module
from world.rules.titles import removal as titles_removal_module
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
    MAX_REMOVAL_RECORDS,
    MAX_TITLE_ENTRIES,
    PENDING_BALLOT_KEY,
    REMOVALS_LOG_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    TitleEquipError,
    TitleRemovalError,
    TitleRemovalReason,
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
    epithet_removal_gate,
    fixed_display_name,
    grant_rank_title,
    grant_first_quest_epithet,
    nomination_cooldown_active,
    nomination_suppressed,
    owned_epithet_displays,
    persist_nomination_ballot,
    predicate_satisfied,
    read_pending_ballot,
    read_title_state,
    register_title_planner,
    remove_epithet,
    removal_digest,
    removal_records,
    safe_full_title,
    safe_pending_ballot,
    title_context_entries,
    title_event_effect_planner,
)
from world.rules.tests.test_cast_settlement import (
    _CastSettlementTestCase,
    _raising_stage,
)
from world.lore.guild import GuildRank
from world.tests.synthetic_data import make_title
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._knowledge_probes import basic_attack_key, live_fixed_title_registry, live_guild_rank_registry, live_registry

from ._support import (
    T_E_DISPLAY,
    T_E_KEY,
    _COUNTER_ROW_KEY,
    _FIRST_KILL_ROW,
    _Request,
    _defeated,
    _event_log,
    _open_title_scope,
    _patched_fixed_registry,
    _with_counter_row,
)


class TitlePlannerTests(EvenniaTest):
    """The planner stages grants; only the commit applies them (D4/D5)."""

    def setUp(self):
        _open_title_scope(self)
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
            skill_key="probe_action",
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
        with _patched_fixed_registry({"t_first_high": _FIRST_KILL_ROW}):
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
        self.actor.db.skills = [{"active": "probe_skill"}]
        for family, parameter, value in (
            (TitlePredicateFamily.MASTERY_OWNED, "element", "ember"),
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
                with _patched_fixed_registry({"t_contained": row}):
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
                root_skill_key="probe_skill",
            ),
        )
        self.actor.db.skills = {"active": ["probe_skill"], "passive": []}
        self.actor.db.skill_proficiency = {"probe_skill": "not-a-number"}
        with _patched_fixed_registry({"t_lineage": row}):
            with self.assertRaises(TitleDataError):
                predicate_satisfied(self.actor, _event_log(), row.predicate)
            self.assertEqual(self._plan(), [])

    def test_an_uneventful_action_stages_nothing(self):
        self.assertEqual(title_event_effect_planner(self._request(), _event_log()), [])

    def test_the_paired_rank_row_is_satisfied_by_the_current_rank(self):
        # The scoped ladder's E row fires for exactly its rank; the pairing
        # shape (rank letter -> its own fixed-title row) is what the planner
        # reads, whichever rows the shipped ladder happens to carry.
        self.actor.db.guild_rank = "E"
        effects = title_event_effect_planner(self._request(), _event_log())
        self.assertEqual([effect.notify for effect in effects], [f"獲得稱號：{T_E_DISPLAY}"])
        for effect in effects:
            effect.apply()
        self.assertEqual(banked_fixed_keys(self.actor), (T_E_KEY,))
        self.assertEqual(compose_full_title(self.actor), T_E_DISPLAY)
        self.assertEqual(title_event_effect_planner(self._request(), _event_log()), [])

    def test_every_paired_row_is_reachable_through_its_own_predicate(self):
        # Every scoped ladder row fires for exactly its rank and no other.
        for rank, definition in sorted(live_guild_rank_registry().items()):
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
        self.actor.db.guild_rank = "E"
        self.assertEqual(
            [effect.description for effect in self._plan()],
            [f"title_granted|{T_E_KEY}"],
        )

    def test_registration_is_idempotent_in_the_planner_registry(self):
        register_title_planner()
        register_title_planner()
        self.assertIs(
            _EVENT_EFFECT_PLANNERS["title"], titles_module.title_event_effect_planner
        )
        _EVENT_EFFECT_PLANNERS.pop("title", None)
        self.assertNotIn("title", _EVENT_EFFECT_PLANNERS)
