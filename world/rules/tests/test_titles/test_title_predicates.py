"""Slice of ``test_titles``: TitlePredicateTests."""
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
    _defeated,
    _event_log,
)


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
            family=TitlePredicateFamily.MASTERY_OWNED, element="ember"
        )
        self.entity.db.skills = {"active": [], "passive": []}
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.db.skills = {"active": ["ember_mastery"], "passive": []}
        self.assertTrue(predicate_satisfied(self.entity, _event_log(), predicate))

    def test_lineage_complete_needs_ownership_and_the_crown_cap(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.LINEAGE_COMPLETE, root_skill_key="fire_lineage"
        )
        self.entity.db.skills = {"active": ["fire_lineage"], "passive": []}
        with patch("world.rules.titles.planner.skill_proficiency_level", return_value=9):
            self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        with patch("world.rules.titles.planner.skill_proficiency_level", return_value=10):
            self.assertTrue(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.db.skills = {"active": [], "passive": []}
        with patch("world.rules.titles.planner.skill_proficiency_level", return_value=10):
            self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))

    def test_quest_completed_tolerates_a_corrupt_log(self):
        predicate = TitlePredicate(
            family=TitlePredicateFamily.QUEST_COMPLETED, quest_key="introductory_hunt"
        )
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        self.entity.db.quest_log = [{"not": "a record"}]
        self.assertFalse(predicate_satisfied(self.entity, _event_log(), predicate))
        from world.quests.runtime import QuestRecord, QuestState, to_storage
        from world.quests.tests._fixtures import TEST_ISSUER_KEY

        record = QuestRecord(
            quest_id="q-1",
            definition_key="introductory_hunt",
            issuer_key=TEST_ISSUER_KEY,
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
