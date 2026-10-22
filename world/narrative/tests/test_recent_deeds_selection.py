"""Behavior tests for recent-deed eligibility, authorized window, aggregation, and bounded JSON rendering.

OpenSpec change: select-authorized-recent-deeds
Specs: openspec/specs/title-system/spec.md
"""

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.narrative.events import record_narrative_event
from world.narrative.models import NarrativeEvent
from world.narrative.recent_deeds import (
    RECENT_DEEDS_JSON_CODE_POINTS_LIMIT,
    canonical_two_day_seconds,
    compute_recent_deeds_window,
    select_authorized_recent_deeds,
)


class RecentDeedsSelectionBehaviorTests(EvenniaTestCase):
    """Behavior tests for authorized recent deed selection, grouping, and bounded rendering."""

    def setUp(self):
        super().setUp()
        self.char = create_object(PlayerCharacter, key="t_sel_player")
        self.other_char = create_object(PlayerCharacter, key="t_sel_other")
        self.room = create_object(Room, key="t_sel_room")
        self.char.location = self.room
        self.other_char.location = self.room
        self.player_pk = str(self.char.pk)
        self.other_pk = str(self.other_char.pk)

    @covers_requirement("title-system::recent-deeds-use-a-frozen-inclusive-two-day-world-window")
    def test_inclusive_bounds_and_future_exclusion(self):
        """Scenario: Inclusive bounds.

        Records exist at lower bound, one tick earlier, T, and T + 1.
        Only lower bound and T qualify; future records and records before lower bound excluded.
        """
        t = 200000
        duration = canonical_two_day_seconds()
        lower = t - duration

        # 1. Before lower bound: lower - 1
        record_narrative_event(
            source_id="quest:before_lower",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q1", "definition_key": "dk1", "completed_objective": "obj1", "outcome": "completed"},
            participants=[self.player_pk],
            tick=lower - 1,
        )
        # 2. Exactly at lower bound
        record_narrative_event(
            source_id="quest:at_lower",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q2", "definition_key": "dk2", "completed_objective": "obj2", "outcome": "completed"},
            participants=[self.player_pk],
            tick=lower,
        )
        # 3. Inside window
        record_narrative_event(
            source_id="quest:inside",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q3", "definition_key": "dk3", "completed_objective": "obj3", "outcome": "completed"},
            participants=[self.player_pk],
            tick=t - 100,
        )
        # 4. Exactly at T
        record_narrative_event(
            source_id="quest:at_t",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q4", "definition_key": "dk4", "completed_objective": "obj4", "outcome": "completed"},
            participants=[self.player_pk],
            tick=t,
        )
        # 5. Future record: T + 1
        record_narrative_event(
            source_id="quest:future",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q5", "definition_key": "dk5", "completed_objective": "obj5", "outcome": "completed"},
            participants=[self.player_pk],
            tick=t + 1,
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t)
        retained_sources = result.source_ids

        self.assertIn("quest:at_lower", retained_sources)
        self.assertIn("quest:inside", retained_sources)
        self.assertIn("quest:at_t", retained_sources)
        self.assertNotIn("quest:before_lower", retained_sources)
        self.assertNotIn("quest:future", retained_sources)

    @covers_requirement("title-system::recent-deeds-use-a-frozen-inclusive-two-day-world-window")
    def test_canonical_duration_and_zero_clamp(self):
        """Scenario: Canonical duration and zero clamp.

        When T is less than two configured world days, lower bound is 0 and duration is 172800.
        """
        duration = canonical_two_day_seconds()
        self.assertEqual(duration, 172800)

        t_small = 50000
        lower, upper = compute_recent_deeds_window(t_small)
        self.assertEqual(lower, 0)
        self.assertEqual(upper, t_small)

        # Record at tick 0 should be included when T = 50000
        record_narrative_event(
            source_id="quest:zero_tick",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_zero", "definition_key": "dk_zero", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player_pk],
            tick=0,
        )
        result = select_authorized_recent_deeds(self.char, frozen_tick=t_small)
        self.assertIn("quest:zero_tick", result.source_ids)

    @covers_requirement("title-system::recent-deeds-use-a-frozen-inclusive-two-day-world-window")
    def test_expired_repetitions_do_not_count_and_selection_does_not_consume(self):
        """Scenario: Expired repetitions do not count.

        Matching repeated actions straddling window boundary only count retained occurrences.
        Later requests can reuse deeds without consumption.
        """
        t = 200000
        lower, _ = compute_recent_deeds_window(t)

        # Action repeated 3 times before window
        for i in range(1, 4):
            record_narrative_event(
                source_id=f"action:straddle:before:{i}",
                event_type="skill_use",
                content={
                    "location": {"id": "", "label": ""},
                    "skill_key": "fireball",
                    "actor": {"id": self.player_pk, "name": "Caster"},
                    "recipients": [{"id": self.other_pk, "name": "Target"}],
                    "effects": [{"damage": 10}],
                },
                participants=[self.player_pk, self.other_pk],
                tick=lower - 100 + i,
            )

        # Action repeated 2 times inside window
        for i in range(1, 3):
            record_narrative_event(
                source_id=f"action:straddle:inside:{i}",
                event_type="skill_use",
                content={
                    "location": {"id": "", "label": ""},
                    "skill_key": "fireball",
                    "actor": {"id": self.player_pk, "name": "Caster"},
                    "recipients": [{"id": self.other_pk, "name": "Target"}],
                    "effects": [{"damage": 10}],
                },
                participants=[self.player_pk, self.other_pk],
                tick=lower + 10 + i,
            )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertEqual(len(result.groups), 1)
        group = result.groups[0]
        # Only the 2 occurrences inside the window count
        self.assertEqual(group.count, 2)
        self.assertEqual(len(group.source_ids), 2)
        self.assertIn("action:straddle:inside:1", group.source_ids)
        self.assertIn("action:straddle:inside:2", group.source_ids)

        # Second request reuses the same events (unconsumed)
        result2 = select_authorized_recent_deeds(self.char, frozen_tick=t + 10)
        self.assertEqual(len(result2.groups), 1)
        self.assertEqual(result2.groups[0].count, 2)

    @covers_requirement("title-system::recent-deed-eligibility-is-closed-and-personally-authorized")
    def test_closed_evidence_set(self):
        """Scenario: Closed evidence set.

        Only authorized supported deterministic deeds enter the stream;
        narrator prose, model statements, movement, waiting, commerce, conversation, and protection are excluded.
        """
        t = 100000

        # Admitted types
        record_narrative_event(
            source_id="quest:admitted",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q1", "definition_key": "dk1", "completed_objective": "obj1", "outcome": "completed"},
            participants=[self.player_pk],
            tick=t,
        )
        record_narrative_event(
            source_id="exam:admitted",
            event_type="guild_exam_settlement",
            content={"location": {"id": "", "label": ""}, "exam_id": "e1", "attained_rank": "D", "target_rank": "D", "passed": True},
            participants=[self.player_pk],
            tick=t,
        )
        record_narrative_event(
            source_id="combat:admitted",
            event_type="combat_encounter",
            content={"location": {"id": "", "label": ""}, "encounter_id": "s1:1", "session_id": "s1", "outcome": "victory", "mode": "hostile", "participant_ids": [self.player_pk]},
            participants=[self.player_pk],
            tick=t,
        )

        # Excluded types
        record_narrative_event(
            source_id="prot:excluded",
            event_type="encounter_protection",
            content={"encounter_outcome": "victory"},
            participants=[self.player_pk],
            tick=t,
        )
        record_narrative_event(
            source_id="claim:excluded",
            event_type="claim_receipt",
            content={"statement": "model statement"},
            participants=[self.player_pk],
            tick=t,
        )
        record_narrative_event(
            source_id="beat:excluded",
            event_type="narrative_beat",
            content={"summary": "narrator beat"},
            participants=[self.player_pk],
            tick=t,
        )
        record_narrative_event(
            source_id="move:excluded",
            event_type="wilderness_move",
            content={"destination": "forest"},
            participants=[self.player_pk],
            tick=t,
        )
        record_narrative_event(
            source_id="mail:excluded",
            event_type="correspondence_read",
            content={"letter_source_id": "let1"},
            participants=[self.player_pk],
            tick=t,
        )
        # Failed exam is excluded
        record_narrative_event(
            source_id="exam:failed_excluded",
            event_type="guild_exam_settlement",
            content={"location": {"id": "", "label": ""}, "exam_id": "e_fail", "attained_rank": "E", "passed": False},
            participants=[self.player_pk],
            tick=t,
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertIn("quest:admitted", result.source_ids)
        self.assertIn("exam:admitted", result.source_ids)
        self.assertIn("combat:admitted", result.source_ids)

        self.assertNotIn("prot:excluded", result.source_ids)
        self.assertNotIn("claim:excluded", result.source_ids)
        self.assertNotIn("beat:excluded", result.source_ids)
        self.assertNotIn("move:excluded", result.source_ids)
        self.assertNotIn("mail:excluded", result.source_ids)
        self.assertNotIn("exam:failed_excluded", result.source_ids)

    @covers_requirement("title-system::recent-deed-eligibility-is-closed-and-personally-authorized")
    def test_field_privacy_precedes_counts_and_invariance(self):
        """Scenario: Field privacy precedes counts.

        When a participant record contains another character's private or unknown state,
        those fields influence neither rendered facts nor aggregate counts and summaries.
        Mutations to another character's private fields produce zero change in returned output.
        """
        t = 50000

        def make_adult_content(other_private_roll: int, other_auto_comply: bool, other_milestone: str):
            data = {
                "action_source_id": "adult:priv_test",
                "act_key": "caress",
                "act_name": "溫柔愛撫",
                "actor": {"id": self.player_pk, "name": "ActorPlayer"},
                "recipients": [{"id": self.other_pk, "name": "OtherTarget"}],
                "outcomes": {
                    "resistance": [
                        {
                            "actor_id": self.player_pk,
                            "target_id": self.other_pk,
                            "target_name": "OtherTarget",
                            "resisted": False,
                            "roll": other_private_roll,           # PRIVATE to other
                            "auto_comply": other_auto_comply,     # PRIVATE to other
                        }
                    ],
                    "effects": [
                        {
                            "kind": "pleasure_gain",
                            "actor_id": self.player_pk,
                            "target_id": self.other_pk,
                            "target_name": "OtherTarget",
                            "result": {"amount": 11},
                        }
                    ],
                },
                "milestones": [
                    {
                        "source_id": "ms:player:1",
                        "milestone_kind": "experience_type",
                        "identifier": "caress_exp",
                        "entity_id": self.player_pk,
                    },
                    {
                        "source_id": "ms:other:1",
                        "milestone_kind": "state_transition",
                        "identifier": other_milestone,            # PRIVATE to other
                        "entity_id": self.other_pk,
                    },
                ],
                "field_access": {
                    self.player_pk: ["actor", "act_key", "recipients", "resistance_verdict", "physical_effects", "actor_milestones"],
                    self.other_pk: ["target_own_outcome", "resistance_verdict", "effects_on_target", "target_milestones"],
                },
                # Explicit unknown: this synthetic payload settles no location.
            "location": {"id": "", "label": ""},
            }
            return data

        # Baseline event
        event1, _, _ = record_narrative_event(
            source_id="adult:priv_test",
            event_type="adult_action",
            content=make_adult_content(15, False, "virginity_loss"),
            participants=[self.player_pk, self.other_pk],
            tick=t,
        )

        res1 = select_authorized_recent_deeds(self.char, frozen_tick=t)
        rendered1 = res1.rendered_json

        # Assert private fields are NOT present in rendered facts
        self.assertNotIn("roll", rendered1)
        self.assertNotIn("auto_comply", rendered1)
        self.assertNotIn("virginity_loss", rendered1)
        self.assertIn("ActorPlayer", rendered1)
        self.assertIn("caress_exp", rendered1)

        # Invariance test: mutate the other character's private fields (roll, auto_comply, private milestone)
        event1.content = make_adult_content(99, True, "climax_onset")
        event1.save()

        res2 = select_authorized_recent_deeds(self.char, frozen_tick=t)
        rendered2 = res2.rendered_json

        # The returned JSON, group counts, and source_ids MUST BE 100% IDENTICAL
        self.assertEqual(rendered1, rendered2)
        self.assertEqual(res1.source_ids, res2.source_ids)
        self.assertEqual(res1.groups[0].count, res2.groups[0].count)

    @covers_requirement("title-system::recent-deed-eligibility-is-closed-and-personally-authorized")
    def test_malformed_record_fails_closed(self):
        """Scenario: Malformed record fails closed.

        When one eligible source is malformed beside a usable record,
        only the malformed source is omitted with a diagnostic; no substitute facts are manufactured.
        """
        t = 50000

        # Usable valid record
        record_narrative_event(
            source_id="quest:usable",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_ok", "definition_key": "dk_ok", "completed_objective": "obj_ok", "outcome": "completed"},
            participants=[self.player_pk],
            tick=t,
        )
        # Malformed record (missing definition_key and outcome)
        record_narrative_event(
            source_id="quest:corrupt",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_bad"},
            participants=[self.player_pk],
            tick=t,
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertIn("quest:usable", result.source_ids)
        self.assertNotIn("quest:corrupt", result.source_ids)

        # Malformed passed field (string "true" instead of bool True)
        record_narrative_event(
            source_id="exam:string_passed",
            event_type="guild_exam_settlement",
            content={"location": {"id": "", "label": ""}, "exam_id": "e_str", "target_rank": "D", "attained_rank": "D", "passed": "true"},
            participants=[self.player_pk],
            tick=t,
        )
        res_exam = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertNotIn("exam:string_passed", res_exam.source_ids)

        # Malformed adult action (missing act_key and empty actor id)
        record_narrative_event(
            source_id="adult:no_actor",
            event_type="adult_action",
            content={
                "location": {"id": "", "label": ""},
                "action_source_id": "adult:no_actor",
                "actor": {"id": ""},
                "recipients": [],
                "field_access": {self.player_pk: ["actor"]},
            },
            participants=[self.player_pk],
            tick=t,
        )
        res_adult = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertNotIn("adult:no_actor", res_adult.source_ids)

    @covers_requirement("title-system::recent-deed-groups-retain-outcomes-and-stable-provenance")
    def test_context_boundaries_stop_repetition_and_encounters_never_merge(self):
        """Scenario: Context boundaries stop repetition.

        Consecutive actions change roles, participants, action type or encounter -> new repetition group.
        Different encounters never merge.
        Interruption A, B, A creates distinct runs.
        """
        t = 50000

        # Run 1: fireball on other_pk (2 times)
        for i in (1, 2):
            record_narrative_event(
                source_id=f"act:run1:{i}",
                event_type="skill_use",
                content={
                    "location": {"id": "", "label": ""},
                    "skill_key": "fireball",
                    "actor": {"id": self.player_pk},
                    "recipients": [{"id": self.other_pk}],
                    "effects": [{"dmg": 10}],
                },
                participants=[self.player_pk, self.other_pk],
                tick=t + i,
            )

        # Run 2: ice_bolt on other_pk (different action type)
        record_narrative_event(
            source_id="act:run2:1",
            event_type="skill_use",
            content={
                "location": {"id": "", "label": ""},
                "skill_key": "ice_bolt",
                "actor": {"id": self.player_pk},
                "recipients": [{"id": self.other_pk}],
                "effects": [{"dmg": 5}],
            },
            participants=[self.player_pk, self.other_pk],
            tick=t + 10,
        )

        # Run 3: fireball on other_pk again (A, B, A interruption)
        record_narrative_event(
            source_id="act:run3:1",
            event_type="skill_use",
            content={
                "location": {"id": "", "label": ""},
                "skill_key": "fireball",
                "actor": {"id": self.player_pk},
                "recipients": [{"id": self.other_pk}],
                "effects": [{"dmg": 10}],
            },
            participants=[self.player_pk, self.other_pk],
            tick=t + 20,
        )

        # Separate encounters: Encounter 1 and Encounter 2
        record_narrative_event(
            source_id="enc:enc1",
            event_type="combat_encounter",
            content={"location": {"id": "", "label": ""}, "encounter_id": "sess_1:1", "session_id": "sess_1", "outcome": "victory"},
            participants=[self.player_pk],
            tick=t + 30,
        )
        record_narrative_event(
            source_id="enc:enc2",
            event_type="combat_encounter",
            content={"location": {"id": "", "label": ""}, "encounter_id": "sess_2:1", "session_id": "sess_2", "outcome": "escape"},
            participants=[self.player_pk],
            tick=t + 40,
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 50)
        # Should have: Run 1 (fireball, count=2), Run 2 (ice_bolt, count=1), Run 3 (fireball, count=1), enc1, enc2
        # Exactly 5 distinct groups! Run 1 and Run 3 must NOT merge!
        self.assertEqual(len(result.groups), 5)

        fireball_groups = [g for g in result.groups if g.facts.get("skill_key") == "fireball"]
        self.assertEqual(len(fireball_groups), 2)
        counts = sorted(g.count for g in fireball_groups)
        self.assertEqual(counts, [1, 2])

        enc_groups = [g for g in result.groups if g.group_type == "combat_encounter"]
        self.assertEqual(len(enc_groups), 2)
        enc_encounters = {g.facts["encounter_id"] for g in enc_groups}
        self.assertEqual(enc_encounters, {"sess_1:1", "sess_2:1"})
        # The reusable transport token stays diagnostic only.
        self.assertEqual(
            {g.facts["session_id"] for g in enc_groups}, {"sess_1", "sess_2"}
        )

    @covers_requirement("title-system::recent-deed-groups-retain-outcomes-and-stable-provenance")
    def test_action_milestones_do_not_double_count_and_no_invented_aggregate_identity(self):
        """Scenario: Action milestones do not double count & No invented aggregate identity.

        One action with effects and milestone retains both with required source IDs and counts once.
        Group lists immutable source IDs and claims no new persisted aggregate ID.
        """
        t = 50000
        action_source = "adult:action:comb_test"
        ms_source = "adult:milestone:comb_test"

        record_narrative_event(
            source_id=action_source,
            event_type="adult_action",
            content={
                "location": {"id": "", "label": ""},
                "action_source_id": action_source,
                "act_key": "embrace",
                "act_name": "相擁",
                "actor": {"id": self.player_pk},
                "recipients": [{"id": self.other_pk}],
                # A committed settled effect, in the one admitted shape: an
                # unsupported effect row fails the whole record closed.
                "outcomes": {
                    "effects": [
                        {
                            "kind": "pleasure_gain",
                            "actor_id": self.player_pk,
                            "target_id": self.other_pk,
                            "target_name": "相擁之人",
                            "result": {"amount": 6},
                        }
                    ]
                },
                "milestones": [],
                "field_access": {
                    self.player_pk: ["actor", "act_key", "recipients", "resistance_verdict", "physical_effects", "actor_milestones"],
                },
            },
            participants=[self.player_pk, self.other_pk],
            tick=t,
        )
        record_narrative_event(
            source_id=ms_source,
            event_type="adult_milestone",
            content={
                "location": {"id": "", "label": ""},
                "action_source_id": action_source,
                "milestone_kind": "state_transition",
                "identifier": "emotional_bond",
                "entity_id": self.player_pk,
                "details": {"type": "warmth_deepened"},
            },
            participants=[self.player_pk],
            tick=t,
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertEqual(len(result.groups), 1)
        group = result.groups[0]
        # Counts that action occurrence ONCE
        self.assertEqual(group.count, 1)
        # Lists both immutable source IDs
        self.assertEqual(sorted(group.source_ids), sorted([action_source, ms_source]))
        # Facts contain both effects and milestone
        self.assertIn("pleasure_gain", str(group.facts))
        self.assertIn("emotional_bond", str(group.facts))
        # No invented aggregate event ID in the group dict
        self.assertNotIn("aggregate_id", group.facts)
        self.assertNotIn("event_id", group.to_dict())

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_deterministic_tie_and_eight_group_cap(self):
        """Scenario: Deterministic tie and cap.

        More than 8 groups share latest ticks -> newest 8 follow stable source tie order.
        """
        t = 100000

        # Create 12 quest completion groups sharing tick t
        for i in range(1, 13):
            # source_ids "quest:batch:01" to "quest:batch:12"
            sid = f"quest:batch:{i:02d}"
            record_narrative_event(
                source_id=sid,
                event_type="quest_completion",
                content={"location": {"id": "", "label": ""}, "quest_id": f"q_{i}", "definition_key": f"dk_{i}", "completed_objective": f"obj_{i}", "outcome": "completed"},
                participants=[self.player_pk],
                tick=t,
            )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertEqual(len(result.groups), 8)
        # Sorting is (-tick, primary_source_id ASC)
        expected_sources = [f"quest:batch:{i:02d}" for i in range(1, 9)]
        actual_sources = [g.primary_source_id for g in result.groups]
        self.assertEqual(actual_sources, expected_sources)

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_unicode_budget_and_oversized_group_omission(self):
        """Scenario: Unicode and oversized groups.

        Groups exceeding 8000 Unicode code points drop older complete groups.
        Oversized singleton groups are omitted.
        """
        t = 50000

        # Group 1 (newest): Oversized singleton exceeding 8000 chars alone!
        huge_text = "繁體中文測試事實超長字串" * 700  # 8400 chars > 8000 code points
        record_narrative_event(
            source_id="quest:huge_newest",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_huge", "definition_key": "dk_huge", "completed_objective": huge_text, "outcome": "completed"},
            participants=[self.player_pk],
            tick=t + 10,
        )

        # Group 2 (older): Normal small group
        record_narrative_event(
            source_id="quest:normal_older",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_small", "definition_key": "dk_small", "completed_objective": "small obj", "outcome": "completed"},
            participants=[self.player_pk],
            tick=t,
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 20)
        # Oversized newest singleton must be omitted; normal older group must be retained!
        self.assertNotIn("quest:huge_newest", result.source_ids)
        self.assertIn("quest:normal_older", result.source_ids)
        self.assertLessEqual(len(result.rendered_json), RECENT_DEEDS_JSON_CODE_POINTS_LIMIT)

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_no_renderable_evidence_empty_rendering(self):
        """Scenario: No renderable evidence.

        When every eligible group is too large or no eligible groups exist,
        feed is empty (meaning empty material: {"recent_deeds": []}).
        """
        t = 50000
        huge_text = "超大型文字資料" * 1500
        record_narrative_event(
            source_id="quest:only_huge",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q1", "definition_key": "dk1", "completed_objective": huge_text, "outcome": "completed"},
            participants=[self.player_pk],
            tick=t,
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertEqual(len(result.groups), 0)
        self.assertEqual(len(result.source_ids), 0)
        self.assertEqual(result.rendered_json, '{"recent_deeds":[]}')


def _adult_action_content(
    *,
    source_id: str,
    player_pk: str,
    actor_name: str,
    other_pk: str,
    other_name: str,
    transitions: list[dict] | None = None,
    counters: list[dict] | None = None,
    effects: list[dict] | None = None,
    resistance: list[dict] | None = None,
    milestones: list[dict] | None = None,
    act_key: str = "caress",
) -> dict:
    """One adult_action payload in the shape the settlement adapter produces."""
    return {
        "action_source_id": source_id,
        "act_key": act_key,
        "act_name": "溫柔愛撫",
        "actor": {"id": player_pk, "name": actor_name, "role": "actor"},
        "recipients": [{"id": other_pk, "name": other_name, "role": "recipient"}],
        "outcomes": {
            "transitions": transitions or [],
            "counters": counters or [],
            "resistance": resistance or [],
            "effects": effects or [],
        },
        "milestones": milestones or [],
        "field_access": {
            player_pk: [
                "actor",
                "act_key",
                "recipients",
                "resistance_verdict",
                "physical_effects",
                "own_state_transitions",
                "own_counter_changes",
                "actor_milestones",
            ],
            other_pk: [
                "target_own_outcome",
                "resistance_verdict",
                "effects_on_target",
                "target_state_transitions",
                "target_counter_changes",
                "target_milestones",
            ],
        },
    "location": {"id": "", "label": ""},
    }


class AdultResultFamilyAggregationTests(EvenniaTestCase):
    """Authorized adult result families survive projection, grouping and rendering."""

    def setUp(self):
        super().setUp()
        self.char = create_object(PlayerCharacter, key="t_fam_player")
        self.other_char = create_object(PlayerCharacter, key="t_fam_other")
        self.control = create_object(PlayerCharacter, key="t_fam_control")
        self.player_pk = str(self.char.pk)
        self.other_pk = str(self.other_char.pk)

    def _content(self, source_id: str, **overrides) -> dict:
        return _adult_action_content(
            source_id=source_id,
            player_pk=self.player_pk,
            actor_name=self.char.key,
            other_pk=self.other_pk,
            other_name=self.other_char.key,
            **overrides,
        )

    def _record(self, source_id: str, tick: int, **overrides) -> NarrativeEvent:
        event, _, _ = record_narrative_event(
            source_id=source_id,
            event_type="adult_action",
            content=self._content(source_id, **overrides),
            participants=[self.player_pk, self.other_pk],
            tick=tick,
        )
        return event

    def _milestone(self, source_id: str, parent: str, tick: int, identifier: str) -> None:
        record_narrative_event(
            source_id=source_id,
            event_type="adult_milestone",
            content={
                "location": {"id": "", "label": ""},
                "action_source_id": parent,
                "milestone_kind": "state_transition",
                "identifier": identifier,
                "entity_id": self.player_pk,
                "details": {"transition": identifier},
            },
            participants=[self.player_pk],
            tick=tick,
            visibility="private",
        )

    @covers_requirement(
        "title-system::recent-deed-eligibility-is-closed-and-personally-authorized",
        "title-system::authorized-adult-result-families-survive-aggregation",
    )
    def test_own_state_families_respect_per_participant_knowability(self):
        """Scenario: Other participant state stays absent.

        WHEN the actor and the recipient view one adult action
        THEN each sees only their own authorized transition, counter and effect
        families, and a present non-participant sees nothing at all.
        """
        t = 50000
        content = self._content(
            "adult:families:1",
            transitions=[
                {"target_id": self.player_pk, "target_name": self.char.key, "event": "own_transition"},
                {"target_id": self.other_pk, "target_name": self.other_char.key, "event": "other_transition"},
            ],
            counters=[
                {"target_id": self.player_pk, "target_name": self.char.key, "counter": "own_counter"},
                {"target_id": self.other_pk, "target_name": self.other_char.key, "counter": "other_counter_a"},
            ],
            effects=[
                {
                    "kind": "pleasure_gain",
                    "actor_id": self.player_pk,
                    "target_id": self.player_pk,
                    "target_name": self.char.key,
                    "result": {"amount": 6},
                },
                {
                    "kind": "pleasure_gain",
                    "actor_id": self.player_pk,
                    "target_id": self.other_pk,
                    "target_name": self.other_char.key,
                    "result": {"amount": 11},
                },
            ],
            resistance=[
                {
                    "actor_id": self.player_pk,
                    "target_id": self.other_pk,
                    "target_name": self.other_char.key,
                    "resisted": False,
                    "auto_comply": False,
                    "roll": 42,
                }
            ],
        )
        event, _, _ = record_narrative_event(
            source_id="adult:families:1",
            event_type="adult_action",
            content=content,
            participants=[self.player_pk, self.other_pk],
            tick=t,
        )

        actor_facts = json.loads(
            select_authorized_recent_deeds(self.char, frozen_tick=t).rendered_json
        )["recent_deeds"][0]["facts"]
        actor_outcomes = actor_facts["outcomes"]
        self.assertEqual(
            [row["event"] for row in actor_outcomes["transitions"]],
            ["own_transition"],
        )
        self.assertEqual(
            [row["counter"] for row in actor_outcomes["counters"]],
            ["own_counter"],
        )
        # The actor's existing physical-effect permission covers every committed
        # effect of the occurrence, while the recipient sees only their own.
        self.assertEqual(
            {row["target_id"] for row in actor_outcomes["effects"]},
            {self.player_pk, self.other_pk},
        )
        self.assertEqual(
            actor_outcomes["resistance"],
            [
                {
                    "target_id": self.other_pk,
                    "target_name": self.other_char.key,
                    "resisted": False,
                }
            ],
        )

        recipient_facts = json.loads(
            select_authorized_recent_deeds(self.other_char, frozen_tick=t).rendered_json
        )["recent_deeds"][0]["facts"]
        recipient_outcomes = recipient_facts["outcomes"]
        self.assertEqual(
            [row["event"] for row in recipient_outcomes["transitions"]],
            ["other_transition"],
        )
        self.assertEqual(
            [row["counter"] for row in recipient_outcomes["counters"]],
            ["other_counter_a"],
        )
        self.assertEqual(
            {row["target_id"] for row in recipient_outcomes["effects"]},
            {self.other_pk},
        )
        self.assertNotIn("own_counter", json.dumps(recipient_facts))

        # A present non-participant is not attributed any role or fact.
        control_result = select_authorized_recent_deeds(self.control, frozen_tick=t)
        self.assertEqual(control_result.groups, ())
        self.assertEqual(control_result.rendered_json, '{"recent_deeds":[]}')

        # Another participant's private counter value changes nothing rendered.
        content["outcomes"]["counters"][1]["counter"] = "other_counter_b"
        event.content = content
        event.save()
        rerendered = select_authorized_recent_deeds(self.char, frozen_tick=t)
        self.assertEqual(
            json.loads(rerendered.rendered_json)["recent_deeds"][0]["facts"],
            actor_facts,
        )

    @covers_requirement(
        "title-system::recent-deed-groups-retain-outcomes-and-stable-provenance",
        "title-system::authorized-adult-result-families-survive-aggregation",
    )
    def test_grouped_run_retains_every_family_from_later_occurrences(self):
        """Scenario: Own adult outcomes reach the rendered feed.

        WHEN two consecutive matching adult occurrences settle different
        transitions, counters, effects and resistance verdicts
        THEN the rendered group retains every family, its actual roles and all
        supporting source IDs.
        """
        t = 50000
        self._record(
            "adult:run:1",
            t,
            transitions=[{"target_id": self.player_pk, "target_name": self.char.key, "event": "first_only"}],
            counters=[{"target_id": self.player_pk, "target_name": self.char.key, "counter": "first_counter"}],
            effects=[
                {
                    "kind": "pleasure_gain",
                    "actor_id": self.player_pk,
                    "target_id": self.player_pk,
                    "target_name": self.char.key,
                    "result": {"amount": 6},
                }
            ],
            resistance=[
                {
                    "actor_id": self.player_pk,
                    "target_id": self.other_pk,
                    "target_name": self.other_char.key,
                    "resisted": False,
                    "auto_comply": False,
                    "roll": 42,
                }
            ],
        )
        self._record(
            "adult:run:2",
            t + 1,
            transitions=[{"target_id": self.player_pk, "target_name": self.char.key, "event": "second_only"}],
            counters=[{"target_id": self.player_pk, "target_name": self.char.key, "counter": "second_counter"}],
            effects=[
                {
                    "kind": "buff_applied",
                    "actor_id": self.player_pk,
                    "target_id": self.other_pk,
                    "target_name": self.other_char.key,
                    "result": {"buff_key": "t_family_buff"},
                }
            ],
            resistance=[
                {
                    "actor_id": self.player_pk,
                    "target_id": self.other_pk,
                    "target_name": self.other_char.key,
                    "resisted": True,
                    "auto_comply": False,
                    "roll": 90,
                }
            ],
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 10)
        self.assertEqual(len(result.groups), 1)
        group = json.loads(result.rendered_json)["recent_deeds"][0]
        self.assertEqual(group["group_type"], "adult_action")
        self.assertEqual(group["count"], 2)
        self.assertEqual(group["source_ids"], ["adult:run:1", "adult:run:2"])
        outcomes = group["facts"]["outcomes"]
        self.assertEqual(
            [row["event"] for row in outcomes["transitions"]],
            ["first_only", "second_only"],
        )
        self.assertEqual(
            [row["counter"] for row in outcomes["counters"]],
            ["first_counter", "second_counter"],
        )
        self.assertEqual(
            [row["result"] for row in outcomes["effects"]],
            [{"amount": 6}, {"buff_key": "t_family_buff"}],
        )
        self.assertEqual(
            [(row["resisted"], row["target_id"]) for row in outcomes["resistance"]],
            [(False, self.other_pk), (True, self.other_pk)],
        )
        self.assertNotIn('"roll":', group["facts"].__repr__())

    @covers_requirement(
        "title-system::recent-deed-groups-retain-outcomes-and-stable-provenance",
        "title-system::authorized-adult-result-families-survive-aggregation",
    )
    def test_attached_milestone_is_not_a_separate_occurrence_boundary(self):
        """Scenario: Attached milestone is not a separate action boundary.

        WHEN consecutive matching occurrences carry a milestone attached to the
        first action and no independent intervening occurrence
        THEN compression retains both actions and the milestone with count two
        and every supporting source.
        """
        t = 50000
        self._record("adult:joined:1", t)
        self._record("adult:joined:2", t + 1)
        self._milestone("adult:joined:1:milestone", "adult:joined:1", t, "joined_transition")
        # A milestone whose parent action is not admitted in the window stays an
        # independent occurrence.
        self._milestone("adult:outside:milestone", "adult:outside", t + 5, "outside_transition")

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 10)
        self.assertEqual(
            sorted(group.group_type for group in result.groups),
            ["adult_action", "adult_milestone"],
        )
        joined = next(
            group for group in result.groups if group.group_type == "adult_action"
        )
        self.assertEqual(joined.count, 2)
        self.assertEqual(
            joined.source_ids,
            ["adult:joined:1", "adult:joined:1:milestone", "adult:joined:2"],
        )
        self.assertEqual(
            [row["identifier"] for row in joined.facts["milestones"]],
            ["joined_transition"],
        )
        standalone = next(
            group for group in result.groups if group.group_type == "adult_milestone"
        )
        self.assertEqual(standalone.count, 1)
        self.assertEqual(standalone.source_ids, ["adult:outside:milestone"])

    @covers_requirement(
        "title-system::recent-deed-groups-retain-outcomes-and-stable-provenance"
    )
    def test_independent_milestone_still_stops_a_repetition_run(self):
        """Scenario: Context boundaries stop repetition.

        WHEN an independent occurrence sits between two otherwise matching
        actions
        THEN it starts a new repetition group instead of being absorbed.
        """
        t = 60000
        self._record("adult:split:1", t)
        record_narrative_event(
            source_id="adult:split:independent",
            event_type="adult_milestone",
            content={
                "location": {"id": "", "label": ""},
                "action_source_id": "",
                "milestone_kind": "state_transition",
                "identifier": "independent_transition",
                "entity_id": self.player_pk,
                "details": {"transition": "independent_transition"},
            },
            participants=[self.player_pk],
            tick=t + 1,
            visibility="private",
        )
        self._record("adult:split:2", t + 2)

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 10)
        action_groups = [
            group for group in result.groups if group.group_type == "adult_action"
        ]
        self.assertEqual([group.count for group in action_groups], [1, 1])
        self.assertEqual(
            sorted(source for group in action_groups for source in group.source_ids),
            ["adult:split:1", "adult:split:2"],
        )
        self.assertIn(
            "adult:split:independent",
            [source for group in result.groups for source in group.source_ids],
        )


class SettledLocationContextTests(EvenniaTestCase):
    """Settled location references survive selection, grouping and rendering."""

    def setUp(self):
        super().setUp()
        self.char = create_object(PlayerCharacter, key="t_loc_player")
        self.other = create_object(PlayerCharacter, key="t_loc_other")
        self.room_a = create_object(Room, key="t_loc_room_a")
        self.room_b = create_object(Room, key="t_loc_room_b")
        self.char.location = self.room_a
        self.other.location = self.room_a
        self.player_pk = str(self.char.pk)
        self.other_pk = str(self.other.pk)

    def _location(self, room):
        return {"known": True, "id": str(room.pk), "label": room.key}

    def _record_action(
        self,
        source_id,
        room,
        tick,
        *,
        skill_key="fireball",
        encounter_id=None,
    ):
        content = {
            "location": {"id": str(room.pk), "label": room.key},
            "action_source_id": source_id,
            "skill_key": skill_key,
            "skill_name": skill_key,
            "actor": {"id": self.player_pk, "name": self.char.key, "role": "actor"},
            "recipients": [
                {"id": self.other_pk, "name": self.other.key, "role": "recipient"}
            ],
            "effects": [
                {
                    "kind": "damage",
                    "actor_id": self.player_pk,
                    "target_id": self.other_pk,
                    "target_name": self.other.key,
                    "result": {"amount": 3, "hit": True},
                }
            ],
            "claim_limits": {
                "rescue_claimed": False,
                "protection_claimed": False,
                "exceptional_difficulty": False,
            },
        }
        if encounter_id is not None:
            content["encounter_context"] = {"encounter_id": encounter_id}
        record_narrative_event(
            source_id=source_id,
            event_type="skill_use",
            content=content,
            participants=[self.player_pk, self.other_pk],
            location=str(room.pk),
            tick=tick,
        )

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_compressed_run_keeps_each_occurrence_time_and_place(self):
        """Scenario: Different locations are rendered without misattribution.

        WHEN consecutive matching occurrences settle in different rooms
        THEN the compressed group keeps every occurrence's own tick and
        location instead of assigning the first location to all of them.
        """
        t = 1000
        self._record_action("act:loc:1", self.room_a, t)
        self._record_action("act:loc:2", self.room_b, t + 10)

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 20)
        self.assertEqual(len(result.groups), 1)
        group = result.groups[0]
        self.assertEqual(group.count, 2)
        self.assertEqual(group.latest_tick, t + 10)
        self.assertEqual(sorted(group.source_ids), ["act:loc:1", "act:loc:2"])
        self.assertEqual(group.facts["tick"], t)
        self.assertEqual(group.facts["location"], self._location(self.room_a))
        self.assertEqual(
            group.facts["occurrences"],
            [
                {
                    "source_id": "act:loc:1",
                    "tick": t,
                    "location": self._location(self.room_a),
                },
                {
                    "source_id": "act:loc:2",
                    "tick": t + 10,
                    "location": self._location(self.room_b),
                },
            ],
        )

        rendered = json.loads(result.rendered_json)["recent_deeds"][0]
        self.assertEqual(rendered["latest_tick"], t + 10)
        self.assertEqual(
            rendered["facts"]["occurrences"][1],
            {
                "source_id": "act:loc:2",
                "tick": t + 10,
                "location": self._location(self.room_b),
            },
        )
        # The retained occurrence's committed outcome survives its place.
        self.assertEqual(
            rendered["facts"]["effects"][0]["result"], {"amount": 3, "hit": True}
        )
        self.assertEqual(sorted(result.source_ids), ["act:loc:1", "act:loc:2"])

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_compressed_run_keeps_each_occurrence_tick_in_one_room(self):
        """A same-room run still keeps every occurrence's own committed time."""
        t = 1500
        self._record_action("act:same:1", self.room_a, t)
        self._record_action("act:same:2", self.room_a, t + 5)

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 10)
        group = result.groups[0]
        self.assertEqual(group.count, 2)
        self.assertEqual(
            [
                (row["source_id"], row["tick"])
                for row in group.facts["occurrences"]
            ],
            [("act:same:1", t), ("act:same:2", t + 5)],
        )
        self.assertEqual(
            {json.dumps(row["location"], sort_keys=True) for row in group.facts["occurrences"]},
            {json.dumps(self._location(self.room_a), sort_keys=True)},
        )

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_encounter_action_in_another_room_keeps_its_own_location(self):
        """Scenario: Different locations are rendered without misattribution.

        WHEN an encounter settles in one room and its admitted action in
        another THEN each fact states its own room and time.
        """
        t = 2000
        record_narrative_event(
            source_id="enc:loc:1",
            event_type="combat_encounter",
            content={
                "location": {"id": str(self.room_a.pk), "label": self.room_a.key},
                "encounter_id": "eng:loc:1",
                "session_id": "sess:loc",
                "outcome": "victory",
                "gameplay_outcome": "victory",
                "mode": "hostile",
                "participant_ids": [self.player_pk],
                "opponent_ids": ["999999"],
                "rounds_elapsed": 2,
                "display_snapshots": {},
            },
            participants=[self.player_pk],
            location=str(self.room_a.pk),
            tick=t + 20,
        )
        self._record_action("act:loc:enc", self.room_b, t, encounter_id="eng:loc:1")

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 30)
        self.assertEqual(len(result.groups), 1)
        group = result.groups[0]
        self.assertEqual(group.group_type, "combat_encounter")
        self.assertEqual(group.latest_tick, t + 20)
        self.assertEqual(group.facts["tick"], t + 20)
        self.assertEqual(group.facts["location"], self._location(self.room_a))
        action_summary = group.facts["actions"][0]
        self.assertEqual(action_summary["latest_tick"], t)
        self.assertEqual(action_summary["facts"]["tick"], t)
        self.assertEqual(
            action_summary["facts"]["location"], self._location(self.room_b)
        )
        self.assertEqual(sorted(group.source_ids), ["act:loc:enc", "enc:loc:1"])

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_unknown_location_renders_explicitly_unknown(self):
        """A fact whose producer stated no location stays explicitly unknown."""
        record_narrative_event(
            source_id="quest:loc:unknown",
            event_type="quest_completion",
            content={
                "location": {"id": "", "label": ""},
                "quest_id": "q_unknown",
                "definition_key": "dk_unknown",
                "completed_objective": "obj",
                "outcome": "completed",
            },
            participants=[self.player_pk],
            location="",
            tick=3000,
        )

        result = select_authorized_recent_deeds(self.char, frozen_tick=3010)
        group = result.groups[0]
        self.assertEqual(group.facts["location"], {"known": False})
        rendered = json.loads(result.rendered_json)["recent_deeds"][0]
        self.assertEqual(rendered["facts"]["location"], {"known": False})

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_committed_objective_snapshot_survives_room_rename_and_removal(self):
        """Scenario: Renamed room does not change a committed fact.

        WHEN the settled room is renamed and then removed after settlement
        THEN the request still renders the committed identity and label without
        consulting the quest registry or a live room.
        """
        t = 4000
        room_pk = str(self.room_a.pk)
        room_key = self.room_a.key
        record_narrative_event(
            source_id="quest:loc:snapshot",
            event_type="quest_completion",
            content={
                "location": {"id": room_pk, "label": room_key},
                "quest_id": "q_snapshot",
                "definition_key": "dk_snapshot",
                "completed_objective": {
                    "kind": "deliver",
                    "quantity": 1,
                    "stage_index": 1,
                    "destination_room_id": int(room_pk),
                    "destination_room_label": room_key,
                    "bound_identities": [
                        {
                            "role": "recipient",
                            "identity": self.other.pk,
                            "label": self.other.key,
                        }
                    ],
                },
                "outcome": "completed",
            },
            participants=[self.player_pk],
            location=room_pk,
            tick=t,
        )
        first = select_authorized_recent_deeds(self.char, frozen_tick=t + 10)

        self.room_a.key = "t_loc_room_renamed"
        self.room_a.save()
        self.room_a.delete()

        with patch(
            "world.quests.runtime.definition_for",
            side_effect=AssertionError("selection resolved the quest registry"),
        ):
            again = select_authorized_recent_deeds(self.char, frozen_tick=t + 10)

        self.assertEqual(again.rendered_json, first.rendered_json)
        self.assertEqual(tuple(again.source_ids), ("quest:loc:snapshot",))
        self.assertEqual(again.frozen_tick, t + 10)
        facts = json.loads(again.rendered_json)["recent_deeds"][0]["facts"]
        self.assertEqual(
            facts["location"], {"known": True, "id": room_pk, "label": room_key}
        )
        self.assertEqual(facts["completed_objective"]["destination_room_id"], int(room_pk))
        self.assertEqual(
            facts["completed_objective"]["destination_room_label"], room_key
        )
        self.assertEqual(
            facts["completed_objective"]["bound_identities"][0]["label"],
            self.other.key,
        )

    @covers_requirement("title-system::recent-deed-rendering-has-complete-bounded-groups")
    def test_location_context_growth_drops_only_whole_groups(self):
        """Scenario: Context growth removes only whole groups.

        WHEN authorized location context pushes the envelope past 8000 code
        points THEN the oldest complete groups are dropped and every retained
        group keeps its source IDs, outcomes and per-occurrence references.
        """
        t = 10000
        long_label = "t_loc_" + "x" * 110
        rooms = [
            create_object(Room, key=f"{long_label}{index}") for index in range(2)
        ]
        expected_ticks: dict[str, int] = {}
        group_sources: dict[int, list[str]] = {}
        for group_index in range(8):
            sources = []
            for occurrence in range(8):
                source_id = f"act:budget:{group_index}:{occurrence}"
                tick = t + group_index * 100 + occurrence
                self._record_action(
                    source_id,
                    rooms[occurrence % 2],
                    tick,
                    skill_key=f"budget_skill_{group_index}",
                )
                expected_ticks[source_id] = tick
                sources.append(source_id)
            group_sources[group_index] = sources

        result = select_authorized_recent_deeds(self.char, frozen_tick=t + 1000)
        self.assertLess(len(result.groups), 8)
        self.assertLessEqual(
            len(result.rendered_json), RECENT_DEEDS_JSON_CODE_POINTS_LIMIT
        )
        retained_sources = set(result.source_ids)
        # Whole-group removal: a dropped group never leaves a partial source set.
        for sources in group_sources.values():
            self.assertIn(
                len(retained_sources.intersection(sources)), (0, len(sources))
            )
        # The newest groups are the retained ones.
        self.assertTrue(set(group_sources[0]).isdisjoint(retained_sources))
        self.assertTrue(set(group_sources[7]).issubset(retained_sources))
        for group in result.groups:
            self.assertEqual(group.group_type, "skill_use")
            self.assertEqual(group.count, 8)
            occurrences = group.facts["occurrences"]
            self.assertEqual(
                sorted(group.source_ids),
                sorted(row["source_id"] for row in occurrences),
            )
            self.assertEqual(
                [row["tick"] for row in occurrences],
                [expected_ticks[row["source_id"]] for row in occurrences],
            )
            self.assertEqual(
                len({row["location"]["id"] for row in occurrences}), 2
            )
            self.assertEqual(group.latest_tick, max(expected_ticks[s] for s in group.source_ids))
            self.assertEqual(
                group.facts["effects"][0]["result"], {"amount": 3, "hit": True}
            )
