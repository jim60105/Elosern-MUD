"""Behavior tests for authoritative combat deed provenance and encounter joins.

OpenSpec change: preserve-combat-deed-provenance
Specs: openspec/specs/narrative-events/spec.md, openspec/specs/title-system/spec.md
Design: docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md §5.2, §6, §10
Contract: docs/development/combat-deed-provenance.md

The delta specs' two ADDED requirements (combat deed provenance, encounter
grouping) have no canonical requirement id until archive synchronization, so
these tests annotate the closest canonical requirements they establish.
"""

from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.rooms import Room
from world.narrative.action_adapters import (
    build_action_source_id,
    capture_milestone_snapshot,
    record_action_settlement_evidence,
    record_non_resolver_adult_milestones,
)
from world.narrative.events import (
    build_encounter_source_id,
    record_narrative_event,
)
from world.narrative.models import NarrativeEvent, ProjectionProgress
from world.narrative.recent_deeds import select_authorized_recent_deeds
from world.rules.action import ActionRequest
from world.rules.buffs import apply_buff
from world.rules.clock import get_world_clock
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    CombatProvenance,
    ExecutionScopeBase,
    combat_provenance,
)
from world.rules.combat.rounds import _end_of_round_upkeep, run_round
from world.rules.event_log import EventLog
from world.rules.titles.awards import AutomaticTitleAward
from world.rules.combat_initiation import initiate_field_combat
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    read_session,
    reconstruct_battlefield,
    settle_session,
    submit_player_action,
)
from world.rules.overwhelm import resolve_overwhelm

from ._combat_session_helpers import (
    _monster,
    _player,
    engagement_base,
    fail_on_round_persist,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import BattlefieldIsolation


class CombatDeedProvenanceTests(BattlefieldIsolation, EvenniaTestCase):
    """One real encounter's committed occurrences carry one authoritative identity."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "items",
            "item_effect_profiles",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.room = create_object(Room, key="provenance arena")
        self.player = _player("provenance player")
        self.player.location = self.room
        self.player.traits.hp.base = 600
        self.player.traits.hp.current = 600
        self.monster = _monster("provenance goblin", hp=500, atk=1)
        self.monster.location = self.room

    def _player_actions(self, encounter_id: str) -> list[NarrativeEvent]:
        return list(
            NarrativeEvent.objects.filter(
                event_type="skill_use",
                content__actor__id=str(self.player.pk),
                content__encounter_context__encounter_id=encounter_id,
            ).order_by("source_id")
        )

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable",
        "narrative-events::combat-deed-provenance-reaches-every-settlement-path",
        "title-system::encounter-grouping-uses-unique-occurrence-identity",
    )
    def test_repeated_skill_rounds_at_one_tick_keep_distinct_sources(self):
        """Scenario: same skill in distinct combat slots remains distinct."""
        engage(self.player, self.monster)
        record = read_session(self.player)
        tick = get_world_clock().tick

        for _ in range(2):
            result = submit_player_action(
                self.player, BASIC_ATTACK_KEY, [self.monster]
            )
            self.assertEqual(result["outcome"], "round", result)

        # World time never advanced between the two committed occurrences.
        self.assertEqual(get_world_clock().tick, tick)

        actions = self._player_actions(record.engagement_id)
        self.assertEqual(len(actions), 2)
        self.assertEqual(
            [event.source_id for event in actions],
            [
                f"action:combat:{record.engagement_id}:r1:s0:"
                f"{self.player.pk}:{BASIC_ATTACK_KEY}",
                f"action:combat:{record.engagement_id}:r2:s0:"
                f"{self.player.pk}:{BASIC_ATTACK_KEY}",
            ],
        )
        for event in actions:
            self.assertEqual(
                event.content["encounter_context"],
                {
                    "encounter_id": record.engagement_id,
                    "session_id": record.session_id,
                    "round_number": int(event.source_id.split(":r")[1].split(":")[0]),
                    "slot_ordinal": 0,
                },
            )

        # Settling the real encounter keeps both occurrences in one group with
        # their own sources and counts.
        settle_session(
            self.player, record, reconstruct_battlefield(self.player, record), "victory"
        )
        selected = select_authorized_recent_deeds(
            self.player, frozen_tick=get_world_clock().tick
        )
        groups = [g for g in selected.groups if g.group_type == "combat_encounter"]
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.facts["encounter_id"], record.engagement_id)
        self.assertEqual(group.facts["outcome"], "victory")
        self.assertTrue(
            {event.source_id for event in actions} <= set(group.source_ids)
        )
        own_summaries = [
            summary
            for summary in group.facts["actions"]
            if summary["facts"]["actor"]["id"] == str(self.player.pk)
        ]
        # The enemy's own round-1 action interleaves in the chronological
        # stream, so the player's two occurrences are two runs of one action;
        # every run keeps its own source and count and none is lost.
        self.assertGreaterEqual(len(own_summaries), 1)
        self.assertEqual(sum(summary["count"] for summary in own_summaries), 2)
        for summary in own_summaries:
            self.assertEqual(summary["action_type"], BASIC_ATTACK_KEY)

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable",
        "narrative-events::combat-deed-provenance-reaches-every-settlement-path",
    )
    def test_opening_hostile_engagement_carries_its_own_provenance(self):
        """An opening action commits under the engagement it opened."""
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=50),
            patch("world.rules.combat.damage.roll_d100", return_value=50),
            patch("world.rules.combat.rounds.roll_d100", return_value=50),
        ):
            result = initiate_field_combat(
                self.player, BASIC_ATTACK_KEY, self.monster
            )
        self.assertEqual(result["outcome"], "round", result)
        record = read_session(self.player)
        self.assertIsNotNone(record)
        actions = self._player_actions(record.engagement_id)
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            actions[0].source_id,
            f"action:combat:{record.engagement_id}:r1:s0:"
            f"{self.player.pk}:{BASIC_ATTACK_KEY}",
        )
        self.assertEqual(
            actions[0].content["encounter_context"]["session_id"],
            record.session_id,
        )

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable",
        "narrative-events::combat-deed-provenance-reaches-every-settlement-path",
    )
    def test_compressed_rounds_keep_the_engagement_and_real_round_ordinals(self):
        """Compressed execution preserves the encounter identity it resolves under."""
        engage(self.player, self.monster)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        for trait_key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, trait_key).base = 200

        def provider(entity, field):
            if entity is self.player:
                return ActionRequest(
                    self.player,
                    BASIC_ATTACK_KEY,
                    [self.monster],
                    BattlefieldActionContext(field),
                )
            return None

        with patch("world.rules.combat.battlefield.roll_d100", return_value=50):
            result = resolve_overwhelm(
                battlefield,
                provider,
                max_rounds=2,
                decision_scope_base=ExecutionScopeBase(
                    session_id=record.session_id,
                    round_index=record.rounds_elapsed + 1,
                    engagement_id=record.engagement_id,
                ),
            )
        self.assertGreaterEqual(result.rounds_elapsed, 2)

        actions = self._player_actions(record.engagement_id)
        self.assertEqual(
            [event.source_id for event in actions],
            [
                f"action:combat:{record.engagement_id}:r1:s0:"
                f"{self.player.pk}:{BASIC_ATTACK_KEY}",
                f"action:combat:{record.engagement_id}:r2:s0:"
                f"{self.player.pk}:{BASIC_ATTACK_KEY}",
            ],
        )

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable",
        "narrative-events::combat-deed-provenance-reaches-every-settlement-path",
    )
    def test_two_real_slots_of_one_actor_commit_distinct_occurrences(self):
        """Scenario: same skill in distinct combat slots remains distinct."""
        engage(self.player, self.monster)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        # The extra-action grant provisions a second real slot for this actor.
        apply_buff(self.player, "lightning_extra_action")
        tick = get_world_clock().tick

        def provider(entity, field):
            if entity is self.player:
                return ActionRequest(
                    self.player,
                    BASIC_ATTACK_KEY,
                    [self.monster],
                    BattlefieldActionContext(field),
                )
            return None

        with patch("world.rules.combat.battlefield.roll_d100", return_value=50):
            run_round(
                battlefield,
                provider,
                decision_scope_base=engagement_base(
                    engagement_id=f"{record.engagement_id}:slots",
                    round_index=1,
                ),
            )
        self.assertEqual(get_world_clock().tick, tick)

        actions = self._player_actions(f"{record.engagement_id}:slots")
        self.assertEqual(
            [event.source_id for event in actions],
            [
                f"action:combat:{record.engagement_id}:slots:r1:s0:"
                f"{self.player.pk}:{BASIC_ATTACK_KEY}",
                f"action:combat:{record.engagement_id}:slots:r1:s1:"
                f"{self.player.pk}:{BASIC_ATTACK_KEY}",
            ],
        )
        self.assertEqual(
            {event.content["encounter_context"]["slot_ordinal"] for event in actions},
            {0, 1},
        )
        self.assertEqual({event.tick for event in actions}, {tick})
        self.assertEqual(len({event.source_id for event in actions}), 2)

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable"
    )
    def test_replaying_a_committed_action_and_upkeep_reuses_source_and_awards(self):
        """Scenario: combat evidence replay reuses occurrence identity."""
        engage(self.player, self.monster)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        provenance = CombatProvenance(
            engagement_id=record.engagement_id,
            round_ordinal=1,
            slot_ordinal=0,
            session_id=record.session_id,
        )
        occurrence = (
            f"action:combat:{record.engagement_id}:r1:s0:"
            f"{self.player.pk}:{BASIC_ATTACK_KEY}"
        )
        award = AutomaticTitleAward(
            source_id=occurrence,
            recipient_id=str(self.player.pk),
            kind="fixed",
            title_id="t_provenance_award",
            granted_tick=5,
            display_name="合成事蹟稱號",
        )
        request = ActionRequest(
            self.player,
            BASIC_ATTACK_KEY,
            [self.monster],
            BattlefieldActionContext(battlefield),
            source_id=occurrence,
        )
        event_log = EventLog(str(self.player.key), BASIC_ATTACK_KEY, (), (), 0)

        with combat_provenance(provenance):
            first, _ = record_action_settlement_evidence(
                request,
                event_log,
                (award,),
                {},
                delivered_targets=[self.monster],
            )
            ProjectionProgress.objects.filter(source_id=occurrence).update(
                status="completed"
            )
            committed_content = dict(first.content)
            counts = (
                NarrativeEvent.objects.count(),
                ProjectionProgress.objects.count(),
            )
            # The same committed settlement notification is re-delivered with
            # no awards at all: the replay must not erase them.
            replayed, _ = record_action_settlement_evidence(
                request,
                event_log,
                (),
                {},
                delivered_targets=[self.monster],
            )
        self.assertEqual(replayed.pk, first.pk)
        self.assertEqual(replayed.content, committed_content)
        self.assertEqual(
            replayed.content["award_results"][0]["title_id"], "t_provenance_award"
        )
        self.assertEqual(
            (NarrativeEvent.objects.count(), ProjectionProgress.objects.count()),
            counts,
        )
        self.assertEqual(
            ProjectionProgress.objects.get(source_id=occurrence).status, "completed"
        )

        # The upkeep boundary's own committed notification replays the same
        # way: the recorder allocates one immutable milestone source per
        # transition under (engagement, round, entity, transition), and
        # re-delivering each committed notification reuses that source and its
        # completed progress row without a second occurrence.
        snapshot = capture_milestone_snapshot(self.player)
        self.player.sexual.virgin = False
        self.player.sexual.record_climax_count()
        self.player.sexual.climax_phase.value = "進行中"
        upkeep_round = CombatProvenance(
            engagement_id=record.engagement_id,
            round_ordinal=2,
            session_id=record.session_id,
        )
        with combat_provenance(upkeep_round):
            record_non_resolver_adult_milestones(
                self.player,
                snapshot,
                source_id=(
                    f"combat:{record.engagement_id}:round:2:upkeep:"
                    f"{self.player.pk}"
                ),
                tick=get_world_clock().tick,
                encounter_provenance=upkeep_round,
            )
        milestones = list(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone",
                content__encounter_context__encounter_id=record.engagement_id,
            )
        )
        self.assertGreaterEqual(len(milestones), 2)
        milestone_sources = [event.source_id for event in milestones]
        upkeep_counts = (
            NarrativeEvent.objects.count(),
            ProjectionProgress.objects.count(),
        )
        upkeep_contents = [dict(event.content) for event in milestones]
        for event, content in zip(milestones, upkeep_contents):
            ProjectionProgress.objects.filter(source_id=event.source_id).update(
                status="completed"
            )
            replayed_event, _, created = record_narrative_event(
                source_id=event.source_id,
                event_type=event.event_type,
                content=content,
                participants=event.participants,
                location=event.location,
                tick=event.tick,
                visibility=event.visibility,
            )
            self.assertFalse(created)
            self.assertEqual(replayed_event.pk, event.pk)
            self.assertEqual(replayed_event.content, content)
        self.assertEqual(
            (NarrativeEvent.objects.count(), ProjectionProgress.objects.count()),
            upkeep_counts,
        )
        for source in milestone_sources:
            self.assertEqual(
                ProjectionProgress.objects.get(source_id=source).status, "completed"
            )

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable",
        "narrative-events::combat-deed-provenance-reaches-every-settlement-path",
    )
    def test_missing_or_contradictory_combat_provenance_fails_closed(self):
        """A malformed combat source is never relabeled as an out-of-combat cast."""
        battlefield = Battlefield(
            {"party": frozenset({str(self.player.key)}), "foes": frozenset()},
            {str(self.player.key): self.player},
        )
        request = ActionRequest(
            self.player,
            BASIC_ATTACK_KEY,
            [self.monster],
            BattlefieldActionContext(battlefield),
        )

        # A combat context with no provenance is malformed required evidence.
        with self.assertRaises(ValueError):
            build_action_source_id(request)

        # An empty engagement identity cannot identify a committed occurrence.
        with combat_provenance(CombatProvenance("", 1, 0, "hostile:1:0")):
            with self.assertRaises(ValueError):
                build_action_source_id(request)

        # An inherited source that disagrees with the resolved occurrence is
        # rejected instead of committing the action under a cast identity.
        cast_source = ActionRequest(
            self.player,
            BASIC_ATTACK_KEY,
            [self.monster],
            BattlefieldActionContext(battlefield),
            source_id=f"action:cast:{self.player.pk}:{BASIC_ATTACK_KEY}:7",
        )
        with combat_provenance(CombatProvenance("hostile:1:0:1", 1, 0, "hostile:1:0")):
            with self.assertRaises(ValueError):
                build_action_source_id(cast_source)
            authoritative = build_action_source_id(request)
            self.assertEqual(
                authoritative,
                f"action:combat:hostile:1:0:1:r1:s0:"
                f"{self.player.pk}:{BASIC_ATTACK_KEY}",
            )
        self.assertEqual(NarrativeEvent.objects.count(), 0)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions"
    )
    def test_upkeep_sources_distinguish_rounds_entities_and_transitions(self):
        """An upkeep occurrence is identified by engagement, round, entity and transition."""
        self.player.sexual.climax_phase.value = "進行中"
        self.assertEqual(self.player.sexual.climax_count, 0)
        battlefield = Battlefield(
            {"party": frozenset({str(self.player.key)}), "foes": frozenset()},
            {str(self.player.key): self.player},
        )
        # Look-alike optional attributes must not become the identity.
        battlefield.session_id = "not_authoritative"
        battlefield.round_number = 8
        provenance = CombatProvenance("hostile:900:1", 2, session_id="hostile:900:0")

        with combat_provenance(provenance):
            _end_of_round_upkeep(battlefield)

        first = NarrativeEvent.objects.get(
            event_type="adult_milestone",
            content__identifier="first_climax",
        )
        self.assertEqual(
            first.source_id,
            f"combat:hostile:900:1:round:2:upkeep:{self.player.pk}"
            f":milestone:{self.player.pk}:state_transition:first_climax",
        )
        self.assertEqual(
            first.content["encounter_context"]["encounter_id"], "hostile:900:1"
        )
        self.assertEqual(first.content["encounter_context"]["round_number"], 2)

        # Several transitions resolved by one round's upkeep boundary keep
        # their own sources: the transition discriminator is part of identity.
        snapshot = capture_milestone_snapshot(self.player)
        self.player.sexual.virgin = False
        self.player.sexual.record_climax_count()
        self.player.sexual.climax_phase.value = "進行中"
        with combat_provenance(provenance):
            record_non_resolver_adult_milestones(
                self.player,
                snapshot,
                source_id=(
                    f"combat:hostile:900:1:round:2:upkeep:{self.player.pk}"
                ),
                tick=get_world_clock().tick,
                encounter_provenance=provenance,
            )
        recorded = list(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone",
                content__encounter_context__encounter_id="hostile:900:1",
            )
        )
        self.assertGreaterEqual(len(recorded), 3)
        self.assertEqual(len({event.source_id for event in recorded}), len(recorded))

    @covers_requirement(
        "title-system::recent-deed-groups-retain-outcomes-and-stable-provenance",
        "title-system::encounter-grouping-uses-unique-occurrence-identity",
    )
    def test_zero_time_reengagement_retains_both_terminal_encounters(self):
        """Scenario: zero-time reengagement survives selection."""
        terminals: list[tuple[str, str]] = []
        for outcome in ("victory", "escape"):
            engage(self.player, self.monster)
            record = read_session(self.player)
            battlefield = reconstruct_battlefield(self.player, record)
            settle_session(self.player, record, battlefield, outcome)
            terminals.append((record.engagement_id, record.session_id))
        # Neither settlement consumed a round, so both terminal encounters
        # committed in one tick and reused one transport session token.
        self.assertEqual(terminals[0][1], terminals[1][1])
        self.assertNotEqual(terminals[0][0], terminals[1][0])
        terminal_events = [
            NarrativeEvent.objects.get(
                source_id=build_encounter_source_id(
                    encounter_id, kind="terminal", ordinal=1
                )
            )
            for encounter_id, _session_id in terminals
        ]
        self.assertEqual(terminal_events[0].tick, terminal_events[1].tick)
        tick = terminal_events[0].tick

        # One committed action per engagement, joined only through its own
        # encounter identity.
        for encounter_id, session_id in terminals:
            record_narrative_event(
                source_id=f"action:combat:{encounter_id}:r1:s0:{self.player.pk}:{BASIC_ATTACK_KEY}",
                event_type="skill_use",
                content={
                    "action_source_id": f"action:combat:{encounter_id}:r1:s0:{self.player.pk}:{BASIC_ATTACK_KEY}",
                    "skill_key": BASIC_ATTACK_KEY,
                    "skill_name": "普通攻擊",
                    "category": "physical",
                    "encounter_context": {
                        "encounter_id": encounter_id,
                        "session_id": session_id,
                        "round_number": 1,
                        "slot_ordinal": 0,
                    },
                    "actor": {"id": str(self.player.pk), "name": self.player.key, "role": "actor"},
                    "recipients": [{"id": str(self.monster.pk), "name": self.monster.key, "role": "recipient"}],
                    "effects": [],
                },
                participants=[str(self.player.pk), str(self.monster.pk)],
                tick=tick,
                visibility="public",
            )

        result = select_authorized_recent_deeds(self.player, frozen_tick=tick)
        groups = [g for g in result.groups if g.group_type == "combat_encounter"]
        self.assertEqual(len(groups), 2)
        self.assertEqual(
            {g.facts["encounter_id"] for g in groups},
            {terminals[0][0], terminals[1][0]},
        )
        # Each retained terminal keeps its own outcome and its own action only.
        for group in groups:
            encounter_id = group.facts["encounter_id"]
            own = {f"action:combat:{encounter_id}:r1:s0:{self.player.pk}:{BASIC_ATTACK_KEY}"}
            self.assertTrue(own.issubset(set(group.source_ids)))
            self.assertIn(
                build_encounter_source_id(encounter_id, kind="terminal", ordinal=1),
                group.source_ids,
            )
            other = [e for e, _s in terminals if e != encounter_id][0]
            self.assertNotIn(
                f"action:combat:{other}:r1:s0:{self.player.pk}:{BASIC_ATTACK_KEY}",
                group.source_ids,
            )
        self.assertEqual(
            sorted(group.facts["outcome"] for group in groups),
            ["escape", "victory"],
        )

    @covers_requirement(
        "title-system::recent-deeds-use-a-frozen-inclusive-two-day-world-window",
        "title-system::encounter-grouping-uses-unique-occurrence-identity",
    )
    def test_window_filtering_precedes_the_encounter_join(self):
        """Scenario: window filtering precedes the encounter join."""
        from world.narrative.recent_deeds import compute_recent_deeds_window

        tick = get_world_clock().tick or 400000
        if tick < 200000:
            tick = 400000
        lower, _upper = compute_recent_deeds_window(tick)
        encounter_id = "hostile:1:0:1"
        record_narrative_event(
            source_id=build_encounter_source_id(encounter_id, kind="terminal", ordinal=1),
            event_type="combat_encounter",
            content={
                "encounter_id": encounter_id,
                "session_id": "hostile:1:0",
                "outcome": "victory",
                "mode": "hostile",
                "participant_ids": [str(self.player.pk)],
            },
            participants=[str(self.player.pk)],
            tick=tick,
        )
        expired_source = f"action:combat:{encounter_id}:r1:s0:{self.player.pk}:{BASIC_ATTACK_KEY}"
        kept_source = f"action:combat:{encounter_id}:r2:s0:{self.player.pk}:{BASIC_ATTACK_KEY}"

        def _action(source: str, tick_value: int, round_number: int) -> None:
            record_narrative_event(
                source_id=source,
                event_type="skill_use",
                content={
                    "action_source_id": source,
                    "skill_key": BASIC_ATTACK_KEY,
                    "skill_name": "普通攻擊",
                    "category": "physical",
                    "encounter_context": {
                        "encounter_id": encounter_id,
                        "session_id": "hostile:1:0",
                        "round_number": round_number,
                        "slot_ordinal": 0,
                    },
                    "actor": {"id": str(self.player.pk), "name": self.player.key, "role": "actor"},
                    "recipients": [],
                    "effects": [],
                },
                participants=[str(self.player.pk)],
                tick=tick_value,
            )

        _action(expired_source, lower - 1, 1)
        _action(kept_source, tick, 2)

        result = select_authorized_recent_deeds(self.player, frozen_tick=tick)
        groups = [g for g in result.groups if g.group_type == "combat_encounter"]
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertIn(kept_source, group.source_ids)
        self.assertNotIn(expired_source, group.source_ids)
        self.assertNotIn(expired_source, result.source_ids)
        summaries = group.facts["actions"]
        self.assertEqual([summary["count"] for summary in summaries], [1])

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable"
    )
    def test_replayed_settlement_reuses_sources_and_never_erases_awards(self):
        """Scenario: combat evidence replay reuses occurrence identity."""
        engage(self.player, self.monster)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        result = submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        self.assertEqual(result["outcome"], "round", result)
        settle_session(self.player, record, battlefield, "victory")

        terminal_source = build_encounter_source_id(
            record.engagement_id, kind="terminal", ordinal=1
        )
        terminal = NarrativeEvent.objects.get(source_id=terminal_source)
        committed_awards = list(terminal.content.get("award_results", []))
        ProjectionProgress.objects.filter(source_id=terminal_source).update(
            status="completed"
        )
        counts = (
            NarrativeEvent.objects.count(),
            ProjectionProgress.objects.count(),
        )

        replayed = settle_session(
            self.player,
            replace(record, settled_tick=terminal.tick),
            battlefield,
            "defeat",
        )
        self.assertEqual(replayed["outcome"], terminal.content["outcome"])
        self.assertEqual(
            (NarrativeEvent.objects.count(), ProjectionProgress.objects.count()),
            counts,
        )
        terminal.refresh_from_db()
        self.assertEqual(terminal.content.get("award_results", []), committed_awards)
        self.assertEqual(
            terminal.content["outcome"], terminal.content["gameplay_outcome"]
        )
        self.assertEqual(
            ProjectionProgress.objects.get(source_id=terminal_source).status,
            "completed",
        )

    @covers_requirement(
        "narrative-events::narrative-facts-commit-atomically-with-covered-gameplay"
    )
    def test_an_injected_failure_after_evidence_recording_rolls_every_surface_back(self):
        engage(self.player, self.monster)
        monster_hp = self.monster.traits.hp.current
        with patch(
            "world.rules.combat_session.rounds._persist",
            side_effect=fail_on_round_persist(),
        ), patch("world.rules.combat.battlefield.roll_d100", return_value=50):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])

        self.assertEqual(self.monster.traits.hp.current, monster_hp)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        self.assertEqual(ProjectionProgress.objects.count(), 0)
