"""Behavior tests for lifecycle recent deeds (quest, exam, and combat evidence).

OpenSpec change: record-lifecycle-recent-deeds
Specs: openspec/specs/narrative-events/spec.md
"""

from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.objects import Object
from typeclasses.rooms import Room
from world.rules.combat.battlefield import Battlefield
from world.lore.guild import GUILD_RANK_REGISTRY, GuildRank
from world.lore.titles import (
    FixedTitleDef,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.narrative.events import (
    build_encounter_source_id,
    get_committed_award_results,
    record_narrative_event,
)
from world.narrative.models import NarrativeEvent
from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
    register_quest_definition,
)
from world.quests.runtime import (
    QuestRecord,
    QuestState,
    accept_quest,
    find_record,
    fulfill_record,
    read_records,
)
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    TEST_ISSUER_KEY,
    _ensure_test_issuance,
    npc_issuer_key,
    register_quest_issuance,
    Settlement,
)
from world.quests.transitions import (
    apply_quest_log_delta,
    apply_quest_log_replacement,
    snapshot_quest_log,
)
from world.rules.combat_session import (
    CombatSessionRecord,
    read_session,
    settle_session,
)
from world.rules.combat_session.lifecycle import engage, engage_group
from world.rules.guild_exams import (
    ExamReason,
    ExamState,
    GuildExamRecord,
    settle_exam_outcome,
    start_guild_exam,
    to_storage as exam_to_storage,
)
from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.rules.tests._combat_session_helpers import _monster, _player
from world.rules.titles import (
    AutomaticTitleAward,
    award_first_quest_epithet,
    award_guild_rank_title,
    read_title_state,
)
from world.tests.synthetic_data import SYNTH_STARTER_EPITHET, SYNTH_TITLES


_SYNTH_RANK_KEY = "t_lifecycle_exam_rank"
_SYNTH_FIXED_KEY = "t_lifecycle_exam_title"
_SYNTH_RANK = GuildRank(
    _SYNTH_RANK_KEY, 1, 10, 100, "Synthetic lifecycle exam rank.", _SYNTH_FIXED_KEY
)


class RecentDeedsLifecycleBehaviorTests(
    BattlefieldIsolation, QuestRegistryIsolation, EvenniaTestCase
):
    """Behavior tests for quest, examination, and combat narrative evidence."""

    def setUp(self):
        super().setUp()
        self.char = _player("t_lifecycle_player")
        self.char.location = create_object(Room, key="t_lifecycle_room")
        self.char.db.wallet = 100

        self.starter_patcher = patch(
            "world.lore.titles.STARTER_EPITHET", SYNTH_STARTER_EPITHET
        )
        self.starter_patcher.start()
        self.addCleanup(self.starter_patcher.stop)

        ranks = dict(GUILD_RANK_REGISTRY)
        ranks[_SYNTH_RANK_KEY] = _SYNTH_RANK
        self.rank_patcher = patch("world.lore.guild.GUILD_RANK_REGISTRY", ranks)
        self.rank_patcher.start()
        self.addCleanup(self.rank_patcher.stop)

        titles = dict(SYNTH_TITLES)
        titles[_SYNTH_FIXED_KEY] = FixedTitleDef(
            key=_SYNTH_FIXED_KEY,
            display_name_zh="測試晉階者",
            category=TitleCategory.GUILD,
            flavor_zh="考核合格的證明。",
            hint_zh="通過公會晉階考核的證明。",
            predicate=TitlePredicate(
                family=TitlePredicateFamily.GUILD_RANK_REACHED,
                guild_rank=_SYNTH_RANK_KEY,
            ),
        )
        self.title_patcher = patch(
            "world.lore.titles.FIXED_TITLE_REGISTRY", titles
        )
        self.title_patcher.start()
        self.addCleanup(self.title_patcher.stop)

        self._definition = self._register_two_stage_quest()

    def _register_two_stage_quest(self) -> QuestDefinition:
        definition = QuestDefinition(
            key="t_lifecycle_quest",
            display_name="測試委託",
            quest_type=QuestType.DEFEAT,
            rank="F",
            stages=(
                QuestStage(
                    index=0,
                    objective=QuestObjective(
                        kind=ObjectiveKind.DEFEAT,
                        quantity=2,
                        monster_tier="low",
                    ),
                ),
                QuestStage(
                    index=1,
                    objective=QuestObjective(
                        kind=ObjectiveKind.DEFEAT,
                        quantity=1,
                        monster_tier="mid",
                    ),
                ),
            ),
        )
        register_quest_definition(definition)
        _ensure_test_issuance(definition.key)
        return definition

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_quest_acceptance_and_partial_progress_create_no_completion_fact(self):
        """Acceptance and intermediate stage progress do not emit completion facts."""
        record = accept_quest(self.char, self._definition.key, TEST_ISSUER_KEY)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)

        source_id = f"quest:{record.quest_id}:completion:{self.char.pk}"
        self.assertIsNone(
            NarrativeEvent.objects.filter(source_id=source_id).first()
        )

        # Progress stage 0 to stage 1 (intermediate advance)
        advanced = fulfill_record(record, self._definition)
        self.assertEqual(advanced.state, QuestState.IN_PROGRESS)
        self.assertEqual(advanced.stage_index, 1)
        apply_quest_log_replacement(self.char, [advanced])

        self.assertIsNone(
            NarrativeEvent.objects.filter(source_id=source_id).first()
        )

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_quest_completion_creates_durable_fact(self):
        """Final stage fulfillment persists a source-keyed quest completion fact."""
        record = accept_quest(self.char, self._definition.key, TEST_ISSUER_KEY)
        advanced = fulfill_record(record, self._definition)
        completed = fulfill_record(advanced, self._definition)
        self.assertEqual(completed.state, QuestState.COMPLETED)

        apply_quest_log_replacement(self.char, [completed])

        source_id = f"quest:{completed.quest_id}:completion:{self.char.pk}"
        event = NarrativeEvent.objects.filter(source_id=source_id).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "quest_completion")
        self.assertEqual(event.participants, [str(self.char.pk)])
        self.assertEqual(event.content["quest_id"], completed.quest_id)
        self.assertEqual(event.content["definition_key"], self._definition.key)
        self.assertEqual(event.content["outcome"], "completed")
        self.assertEqual(
            event.content["completed_objective"]["kind"], "defeat"
        )
        self.assertEqual(event.content["completed_objective"]["quantity"], 1)
        self.assertEqual(
            event.content["completed_objective"]["monster_tier"], "mid"
        )

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_passed_exam_retains_rank_and_creates_fact(self):
        """Passed examination stores exam identity, attained rank, and award results."""
        self.char.guild_rank = "F"
        exam_id = f"exam:{self.char.pk}:pass:1"
        session_id = f"guild_exam:{self.char.pk}:{exam_id}"
        record = GuildExamRecord(
            exam_id=exam_id,
            character_id=int(self.char.pk),
            target_rank="E",
            requested_by="counter",
            opponent_id=9999,
            session_id=session_id,
            state=ExamState.ACTIVE,
            terminal_reason=None,
        )
        self.char.db.guild_exams = [exam_to_storage(record)]

        session = CombatSessionRecord(
            session_id=session_id,
            mode="guild_exam",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(9999,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=2,
            exam_id=exam_id,
        )

        res = settle_exam_outcome(self.char, session, None, "exam_passed")
        self.assertTrue(res["passed"])
        self.assertEqual(self.char.guild_rank, "E")

        source_id = f"guild_exam:{exam_id}:settlement:{self.char.pk}"
        event = NarrativeEvent.objects.filter(source_id=source_id).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "guild_exam_settlement")
        self.assertEqual(event.content["exam_id"], exam_id)
        self.assertTrue(event.content["passed"])
        self.assertEqual(event.content["target_rank"], "E")
        self.assertEqual(event.content["attained_rank"], "E")
        self.assertEqual(len(event.content.get("award_results", [])), 1)

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_failed_exam_creates_no_completion_fact(self):
        """Failed examination does not create completion deeds."""
        self.char.guild_rank = "F"
        exam_id = f"exam:{self.char.pk}:fail:1"
        session_id = f"guild_exam:{self.char.pk}:{exam_id}"
        record = GuildExamRecord(
            exam_id=exam_id,
            character_id=int(self.char.pk),
            target_rank=_SYNTH_RANK_KEY,
            requested_by="counter",
            opponent_id=9999,
            session_id=session_id,
            state=ExamState.ACTIVE,
            terminal_reason=None,
        )
        self.char.db.guild_exams = [exam_to_storage(record)]

        session = CombatSessionRecord(
            session_id=session_id,
            mode="guild_exam",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(9999,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=1,
            exam_id=exam_id,
        )

        res = settle_exam_outcome(self.char, session, None, "exam_failed")
        self.assertFalse(res["passed"])
        self.assertEqual(self.char.guild_rank, "F")

        source_id = f"guild_exam:{exam_id}:settlement:{self.char.pk}"
        self.assertIsNone(
            NarrativeEvent.objects.filter(source_id=source_id).first()
        )

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_quest_and_exam_producer_failure_aborts_settlement(self):
        """Failure writing the narrative fact rolls back gameplay, awards, and caches."""
        # 1. Quest fault rollback
        record = accept_quest(self.char, self._definition.key, TEST_ISSUER_KEY)
        advanced = fulfill_record(record, self._definition)
        completed = fulfill_record(advanced, self._definition)
        apply_quest_log_replacement(self.char, [advanced])

        before_log = deepcopy(self.char.db.quest_log)
        source_id = f"quest:{completed.quest_id}:completion:{self.char.pk}"

        with patch(
            "world.narrative.events.record_narrative_event",
            side_effect=RuntimeError("injected quest narrative error"),
        ):
            with self.assertRaises(RuntimeError):
                apply_quest_log_replacement(self.char, [completed])

        self.assertEqual(self.char.db.quest_log, before_log)
        self.assertIsNone(
            NarrativeEvent.objects.filter(source_id=source_id).first()
        )

        # 2. Exam fault rollback
        self.char.guild_rank = "F"
        exam_id = f"exam:{self.char.pk}:fault:1"
        exam_session_id = f"guild_exam:{self.char.pk}:{exam_id}"
        exam_rec = GuildExamRecord(
            exam_id=exam_id,
            character_id=int(self.char.pk),
            target_rank=_SYNTH_RANK_KEY,
            requested_by="counter",
            opponent_id=9999,
            session_id=exam_session_id,
            state=ExamState.ACTIVE,
            terminal_reason=None,
        )
        self.char.db.guild_exams = [exam_to_storage(exam_rec)]
        exam_session = CombatSessionRecord(
            session_id=exam_session_id,
            mode="guild_exam",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(9999,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=2,
            exam_id=exam_id,
        )

        exam_source = f"guild_exam:{exam_id}:settlement:{self.char.pk}"
        with patch(
            "world.narrative.events.record_narrative_event",
            side_effect=RuntimeError("injected exam narrative error"),
        ):
            with self.assertRaises(RuntimeError):
                settle_exam_outcome(
                    self.char, exam_session, None, "exam_passed"
                )

        self.assertEqual(self.char.guild_rank, "F")
        self.assertEqual(
            self.char.db.guild_exams[0]["state"], ExamState.ACTIVE.value
        )
        self.assertIsNone(
            NarrativeEvent.objects.filter(source_id=exam_source).first()
        )

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_exam_replay_is_idempotent_and_preserves_awards(self):
        """Replayed examination settlement returns original awards and creates no duplicate fact."""
        self.char.guild_rank = "F"
        exam_id = f"exam:{self.char.pk}:replay:1"
        replay_session_id = f"guild_exam:{self.char.pk}:{exam_id}"
        record = GuildExamRecord(
            exam_id=exam_id,
            character_id=int(self.char.pk),
            target_rank=_SYNTH_RANK_KEY,
            requested_by="counter",
            opponent_id=9999,
            session_id=replay_session_id,
            state=ExamState.ACTIVE,
            terminal_reason=None,
        )
        self.char.db.guild_exams = [exam_to_storage(record)]
        session = CombatSessionRecord(
            session_id=replay_session_id,
            mode="guild_exam",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(9999,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=2,
            exam_id=exam_id,
        )

        first_res = settle_exam_outcome(
            self.char, session, None, "exam_passed"
        )
        self.assertEqual(len(first_res["title_awards"]), 1)

        source_id = f"guild_exam:{exam_id}:settlement:{self.char.pk}"
        self.assertEqual(
            NarrativeEvent.objects.filter(source_id=source_id).count(), 1
        )

        # Replay with updated record state
        replayed_res = settle_exam_outcome(
            self.char, session, None, "exam_passed"
        )
        self.assertEqual(replayed_res["state"], ExamState.PASSED.value)
        self.assertEqual(
            replayed_res["title_awards"], first_res["title_awards"]
        )
        self.assertEqual(
            NarrativeEvent.objects.filter(source_id=source_id).count(), 1
        )

    @covers_requirement(
        "narrative-events::completed-combat-evidence-preserves-the-actual-encounter-outcome"
    )
    def test_combat_hostile_victory_defeat_escape_distinct(self):
        """Hostile encounters record distinct victory, defeat, and escape outcomes."""
        enemy = _player("t_enemy")
        enemy.location = self.char.location

        for outcome, expected_outcome in (
            ("victory", "victory"),
            ("defeat", "defeat"),
            ("fled", "escape"),
        ):
            with self.subTest(outcome=outcome):
                session = CombatSessionRecord(
                    session_id=f"hostile:{self.char.pk}:outcome:{outcome}",
                    engagement_id=f"hostile:{self.char.pk}:outcome:{outcome}:1",
                    mode="hostile",
                    room_id=self.char.location.pk,
                    player_ids=(int(self.char.pk),),
                    enemy_ids=(int(enemy.pk),),
                    fled_ids=(),
                    knocked_out_ids=(),
                    rounds_elapsed=3,
                    exam_id=None,
                )
                battlefield = Battlefield(
                    teams={
                        "allies": frozenset({str(self.char.key)}),
                        "foes": frozenset({str(enemy.key)}),
                    },
                    roster={
                        str(self.char.key): self.char,
                        str(enemy.key): enemy,
                    },
                )
                settle_session(self.char, session, battlefield, outcome)

                source_id = build_encounter_source_id(
                    session.engagement_id, kind="terminal", ordinal=1
                )
                event = NarrativeEvent.objects.filter(
                    source_id=source_id
                ).first()
                self.assertIsNotNone(event)
                self.assertEqual(event.event_type, "combat_encounter")
                self.assertEqual(event.content["outcome"], expected_outcome)
                self.assertEqual(event.content["mode"], "hostile")
                self.assertEqual(
                    event.content["participant_ids"], [str(self.char.pk)]
                )
                self.assertEqual(
                    event.content["opponent_ids"], [str(enemy.pk)]
                )
                self.assertIn(str(self.char.pk), event.content["display_snapshots"])
                self.assertIn(str(enemy.pk), event.content["display_snapshots"])

    @covers_requirement(
        "narrative-events::completed-combat-evidence-preserves-the-actual-encounter-outcome"
    )
    def test_exam_combat_outcome_never_lethal_victory(self):
        """Guild exam encounters record exam outcomes and never become lethal victories."""
        host = _player("t_host")
        host.location = self.char.location

        session = CombatSessionRecord(
            session_id=f"guild_exam:{self.char.pk}:ex1",
            engagement_id=f"guild_exam:{self.char.pk}:ex1:1",
            mode="guild_exam",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(int(host.pk),),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=2,
            exam_id="ex1",
        )
        battlefield = Battlefield(
            teams={
                "allies": frozenset({str(self.char.key)}),
                "foes": frozenset({str(host.key)}),
            },
            roster={str(self.char.key): self.char, str(host.key): host},
        )
        settle_session(self.char, session, battlefield, "exam_passed")

        source_id = build_encounter_source_id(
            session.engagement_id, kind="terminal", ordinal=1
        )
        event = NarrativeEvent.objects.filter(source_id=source_id).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.content["outcome"], "exam_passed")
        self.assertEqual(event.content["mode"], "guild_exam")
        self.assertNotEqual(event.content["outcome"], "victory")

    @covers_requirement(
        "narrative-events::completed-combat-evidence-preserves-the-actual-encounter-outcome"
    )
    def test_compressed_rounds_retain_stable_summary(self):
        """Compressed encounters produce the identical terminal summary shape and stable source."""
        enemy = _player("t_enemy_comp")
        enemy.location = self.char.location

        session = CombatSessionRecord(
            session_id=f"hostile:{self.char.pk}:compressed:1",
            engagement_id=f"hostile:{self.char.pk}:compressed:1:1",
            mode="hostile",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(int(enemy.pk),),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=4,
            exam_id=None,
        )
        battlefield = Battlefield(
            teams={
                "allies": frozenset({str(self.char.key)}),
                "foes": frozenset({str(enemy.key)}),
            },
            roster={str(self.char.key): self.char, str(enemy.key): enemy},
        )
        settle_session(
            self.char,
            session,
            battlefield,
            "victory",
            opening="compressed",
        )

        source_id = build_encounter_source_id(
            session.engagement_id, kind="terminal", ordinal=1
        )
        event = NarrativeEvent.objects.filter(source_id=source_id).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.content["outcome"], "victory")
        self.assertEqual(event.content["rounds_elapsed"], 4)
        self.assertEqual(
            event.content["participant_ids"], [str(self.char.pk)]
        )

    @covers_requirement(
        "narrative-events::completed-combat-evidence-preserves-the-actual-encounter-outcome"
    )
    def test_distinct_same_tick_encounters_never_collapse(self):
        """Two separate engagements started in the same tick keep distinct durable identities."""
        enemy_a = _monster("t_enemy_a")
        enemy_b = _monster("t_enemy_b")
        enemy_a.location = self.char.location
        enemy_b.location = self.char.location

        # Engagement 1
        engage_group(self.char, [enemy_a])
        session_1 = read_session(self.char)
        self.assertIsNotNone(session_1.engagement_id)
        settle_session(self.char, session_1, None, "victory")

        # Engagement 2 in same tick
        engage_group(self.char, [enemy_b])
        session_2 = read_session(self.char)
        self.assertIsNotNone(session_2.engagement_id)
        self.assertNotEqual(session_1.engagement_id, session_2.engagement_id)
        settle_session(self.char, session_2, None, "defeat")

        source_1 = build_encounter_source_id(
            session_1.engagement_id, kind="terminal", ordinal=1
        )
        source_2 = build_encounter_source_id(
            session_2.engagement_id, kind="terminal", ordinal=1
        )
        self.assertNotEqual(source_1, source_2)

        ev1 = NarrativeEvent.objects.filter(source_id=source_1).first()
        ev2 = NarrativeEvent.objects.filter(source_id=source_2).first()
        self.assertEqual(ev1.content["outcome"], "victory")
        self.assertEqual(ev2.content["outcome"], "defeat")
        self.assertEqual(ev1.content["opponent_ids"], [str(enemy_a.pk)])
        self.assertEqual(ev2.content["opponent_ids"], [str(enemy_b.pk)])

    @covers_requirement(
        "narrative-events::completed-combat-evidence-preserves-the-actual-encounter-outcome"
    )
    def test_combat_rollback_and_replay(self):
        """Rollback restores encounter state without fact; replay is idempotent."""
        enemy = _player("t_enemy_replay")
        enemy.location = self.char.location

        session = CombatSessionRecord(
            session_id=f"hostile:{self.char.pk}:rr:1",
            engagement_id=f"hostile:{self.char.pk}:rr:1:1",
            mode="hostile",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(int(enemy.pk),),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=1,
            exam_id=None,
        )
        battlefield = Battlefield(
            teams={
                "allies": frozenset({str(self.char.key)}),
                "foes": frozenset({str(enemy.key)}),
            },
            roster={str(self.char.key): self.char, str(enemy.key): enemy},
        )
        source_id = build_encounter_source_id(
            session.engagement_id, kind="terminal", ordinal=1
        )

        # 1. Rollback
        with patch(
            "world.narrative.events.record_narrative_event",
            side_effect=RuntimeError("injected combat narrative fault"),
        ):
            with self.assertRaises(RuntimeError):
                settle_session(self.char, session, battlefield, "victory")

        self.assertIsNone(
            NarrativeEvent.objects.filter(source_id=source_id).first()
        )

        # 2. Commit
        res1 = settle_session(self.char, session, battlefield, "victory")
        self.assertEqual(res1["outcome"], "victory")
        self.assertEqual(
            NarrativeEvent.objects.filter(source_id=source_id).count(), 1
        )

        # 3. Replay
        res2 = settle_session(self.char, session, battlefield, "victory")
        self.assertEqual(res2["outcome"], "victory")
        self.assertEqual(
            NarrativeEvent.objects.filter(source_id=source_id).count(), 1
        )

        # 4. Escape replay preserves original gameplay outcome
        escape_session = CombatSessionRecord(
            session_id=f"hostile:{self.char.pk}:escape_replay:1",
            engagement_id=f"hostile:{self.char.pk}:escape_replay:1:1",
            mode="hostile",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(int(enemy.pk),),
            fled_ids=(int(self.char.pk),),
            knocked_out_ids=(),
            rounds_elapsed=1,
            exam_id=None,
        )
        esc_res1 = settle_session(self.char, escape_session, battlefield, "fled")
        self.assertEqual(esc_res1["outcome"], "fled")
        esc_res2 = settle_session(self.char, escape_session, battlefield, "fled")
        self.assertEqual(esc_res2["outcome"], "fled")

    @covers_requirement(
        "narrative-events::completed-combat-evidence-preserves-the-actual-encounter-outcome"
    )
    def test_no_battlefield_fallback_preserves_roster(self):
        """When battlefield is None, participant and opponent IDs are preserved from record."""
        session = CombatSessionRecord(
            session_id=f"hostile:{self.char.pk}:nobf:1",
            engagement_id=f"hostile:{self.char.pk}:nobf:1:1",
            mode="hostile",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(8888, 9999),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=1,
            exam_id=None,
        )
        settle_session(self.char, session, None, "defeat")

        source_id = build_encounter_source_id(
            session.engagement_id, kind="terminal", ordinal=1
        )
        event = NarrativeEvent.objects.filter(source_id=source_id).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.content["participant_ids"], [str(self.char.pk)])
        self.assertEqual(event.content["opponent_ids"], ["8888", "9999"])
        self.assertIn("8888", event.content["display_snapshots"])
        self.assertIn("9999", event.content["display_snapshots"])

    @covers_requirement(
        "narrative-events::completed-combat-evidence-preserves-the-actual-encounter-outcome"
    )
    def test_combat_failure_after_exam_promotion_restores_title_cache(self):
        """Combat fact failure in outer settlement transaction restores cached exam titles."""
        self.char.guild_rank = "F"
        exam_id = f"exam:{self.char.pk}:outer_fault:1"
        exam_sess_id = f"guild_exam:{self.char.pk}:{exam_id}"
        exam_rec = GuildExamRecord(
            exam_id=exam_id,
            character_id=int(self.char.pk),
            target_rank="E",
            requested_by="counter",
            opponent_id=9999,
            session_id=exam_sess_id,
            state=ExamState.ACTIVE,
            terminal_reason=None,
        )
        self.char.db.guild_exams = [exam_to_storage(exam_rec)]

        session = CombatSessionRecord(
            session_id=exam_sess_id,
            engagement_id=f"guild_exam:{self.char.pk}:{exam_id}:1",
            mode="guild_exam",
            room_id=self.char.location.pk,
            player_ids=(int(self.char.pk),),
            enemy_ids=(9999,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=2,
            exam_id=exam_id,
        )

        real_record_event = record_narrative_event

        def fail_on_combat(source_id, event_type, *args, **kwargs):
            if event_type == "combat_encounter":
                raise RuntimeError("simulated combat narrative failure")
            return real_record_event(
                source_id=source_id, event_type=event_type, *args, **kwargs
            )

        from world.rules.combat_session.settlement import _settle_with_restore

        with patch(
            "world.narrative.events.record_narrative_event",
            side_effect=fail_on_combat,
        ):
            with self.assertRaises(RuntimeError):
                _settle_with_restore(self.char, session, None, "exam_passed")

        # Verify attributes restored both in storage and in Evennia's cache
        self.assertEqual(self.char.guild_rank, "F")
        self.assertEqual(
            self.char.db.guild_exams[0]["state"], ExamState.ACTIVE.value
        )
        _, equipped = read_title_state(self.char)
        self.assertNotEqual(equipped.get("fixed"), "g_e_rank")
