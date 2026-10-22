"""Slice of ``test_defeat_aftermath_violation``: AttemptLoopTests, PoolAndDigestTests, EventLogOrderTests, FlagOffTests.
"""
import unittest
from dataclasses import replace as dataclass_replace
from unittest.mock import patch
from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
import world.rules.defeat_aftermath as defeat_aftermath_module
import world.rules.defeat_aftermath.violation as defeat_aftermath_violation_module
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.rules import clock as clock_module
from world.rules import combat_session as combat_session_module
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    forfeit,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.defeat_aftermath import (
    DEFEAT_AFTERMATH_RULEBOOK,
    load_defeat_aftermath_sections,
    register_violation_hook,
    run_violation_sequence,
)
from world.rules.clock import WorldClock
from world.rules.event_log import render_plain_text
from world.rules.party import join_party
from world.rules.state_derived_roll import derived_roll
from world.narrative.action_adapters import capture_milestone_snapshot
from world.narrative.models import NarrativeEvent
from world.narrative.recent_deeds import select_authorized_recent_deeds
from tools.spec_traceability import covers_requirement
from .._combat_session_helpers import BattlefieldIsolation, _player


from ._support import (
    ViolationBase,
    _aftermath_entries,
    _aftermath_logs,
    _kinds,
    recovery_seconds,
    wake_target,
)


class AttemptLoopTests(ViolationBase):
    """The attempt loop: caps, deltas, counters, clock, and the stop rule."""

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
        "defeat-aftermath-violation-sequence::each-attempt-advances-the-world-clock-by-its-declared-duration",
        "defeat-aftermath-violation-sequence::each-attempt-rolls-the-shipped-resist-contest-with-the-victim-defending",
    )
    def test_all_landed_sequence_runs_to_the_cap_and_spends_the_clock(self):
        self._equalize_scores()
        self._arouse(13)
        with self._patch_rolls([1, 1]):
            result = self._defeat()
        entries = _aftermath_entries(result)
        self.assertEqual(_kinds(entries).count("violation_attempt"), 2)
        self.assertEqual(_kinds(entries).count("violation_act"), 2)
        self.assertEqual(_kinds(entries).count("violation_resisted"), 0)
        # Symmetric crediting: both bodies carry the declared counters.
        for entity in (self.player, self.monster):
            self.assertEqual(entity.sexual.hostile_act_count, 2)
            self.assertEqual(entity.sexual.interspecies_act_count, 2)
        # Combat 6s + two 120s attempts + the recovery solve's own published
        # seconds (the empty attempt scope never regenerates the victim, so the
        # solve still runs from HP 1 to the wake target).
        self.assertEqual(self.clock.tick, 6 + 2 * 120 + recovery_seconds(result))
        self.assertEqual(self.player.traits.hp.current, wake_target(self.player))
        # The wake prose switched to the violated variant; the core's
        # defeat_settle data fields survive the rewrite.
        settle = next(entry for entry in entries if entry.kind == "defeat_settle")
        self.assertEqual(
            settle.data["wake"], DEFEAT_AFTERMATH_RULEBOOK.violation.violated_wake_line
        )
        self.assertEqual(settle.data["hp_after"], 1)
        # Landed deltas: victim +16, aggressor +10 (goblin row) on top of
        # the victory delta, applied once per landed attempt.
        self.assertEqual(self.player.sexual.pleasure.value, 2 * 16)
        self.assertEqual(self.monster.sexual.pleasure.value, 13 + 2 + 2 * 10)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::first-successful-resistance-cancels-that-violator-s-remaining-attempts",
        "defeat-aftermath-violation-sequence::each-attempt-rolls-the-shipped-resist-contest-with-the-victim-defending",
    )
    def test_resisted_attempt_shrinks_deltas_and_stops_the_violator(self):
        self._equalize_scores()
        self._arouse(13)
        with self._patch_rolls([100, 1]):
            result = self._defeat()
        entries = _aftermath_entries(result)
        # The second (would-be landed) attempt never executes.
        self.assertEqual(_kinds(entries).count("violation_attempt"), 1)
        self.assertEqual(_kinds(entries).count("violation_resisted"), 1)
        self.assertEqual(_kinds(entries).count("violation_act"), 0)
        # No counter credits on a resisted attempt, either side.
        for entity in (self.player, self.monster):
            self.assertEqual(entity.sexual.hostile_act_count, 0)
            self.assertEqual(entity.sexual.interspecies_act_count, 0)
        # Only the shrunk deltas apply.
        self.assertEqual(self.player.sexual.pleasure.value, 4)
        self.assertEqual(self.monster.sexual.pleasure.value, 13 + 2 + 3)
        # Zero landed attempts: the PG wake template stays.
        settle = next(entry for entry in entries if entry.kind == "defeat_settle")
        self.assertEqual(settle.data["wake"], DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0])
        # The resisted attempt still spends its declared duration, plus the
        # recovery solve's own published seconds.
        self.assertEqual(self.clock.tick, 6 + 120 + recovery_seconds(result))

    @covers_requirement(
        "defeat-aftermath-violation-sequence::each-attempt-rolls-the-shipped-resist-contest-with-the-victim-defending",
    )
    def test_auto_comply_records_no_roll(self):
        # A victim already mid-climax auto-complies through the shipped
        # short-circuit: the contest returns before the dice, and the entry
        # records that faithfully (roll None, auto_comply true).
        self._equalize_scores()
        self._arouse(13)
        self.player.sexual.climax_phase.value = "進行中"
        self.player.attributes.add("climax_turns", 1, category="sexual_state")
        consumed = []
        real_roll = defeat_aftermath_violation_module.derived_roll

        def counting_roll(*args):
            consumed.append(args)
            return real_roll(*args)

        with patch.object(
            defeat_aftermath_violation_module,
            "derived_roll",
            side_effect=counting_roll,
        ):
            result = self._defeat()
        self.assertEqual(consumed, [])
        entries = [
            e for e in _aftermath_entries(result) if e.kind == "violation_attempt"
        ]
        # Both cap attempts auto-comply: the mid-climax victim cannot resist,
        # and the empty attempt scope never advances climax_turns.
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertIsNone(entry.data["roll"])
            self.assertTrue(entry.data["auto_comply"])

    @covers_requirement(
        "defeat-aftermath-violation-sequence::living-defeat-winners-gain-archetype-victory-arousal",
        "defeat-aftermath-violation-sequence::each-attempt-rolls-the-shipped-resist-contest-with-the-victim-defending",
    )
    def test_climax_onset_counts_once_per_act_entry(self):
        self._equalize_scores()
        self._arouse(13)
        self.player.sexual.pleasure.base = 84
        with self._patch_rolls([1, 1]):
            result = self._defeat()
        acts = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "violation_act"
        ]
        # Attempt 1 walks 極限→接近; attempt 2 walks 接近→進行中: exactly one
        # onset, flagged on the second act entry only.
        self.assertEqual([entry.data["climax"] for entry in acts], [False, True])

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_attempt_identities_distinguish_ordinals_victims_and_aftermaths(self):
        """Scenario: each attempt is identified by engagement/aggressor/ordinal/victim."""
        self._equalize_scores()
        self._arouse(13)
        engage(self.player, self.monster)
        first_record = read_session(self.player)
        with self._patch_rolls([1, 1]):
            self._settle()
        first_sources = sorted(
            NarrativeEvent.objects.filter(
                event_type="adult_action",
                content__act_key="defeat_violation",
            ).values_list("source_id", flat=True)
        )
        self.assertEqual(
            first_sources,
            [
                f"defeat:{first_record.engagement_id}:{self.monster.pk}"
                f":attempt:{attempt}:victim:{self.player.pk}"
                for attempt in (0, 1)
            ],
        )

        # A later aftermath is a distinct engagement: it never reuses one of
        # the earlier identities.
        second_monster = self._lore_monster("哥布林")
        second_monster.location = self.room
        self._equalize_scores(second_monster)
        second_monster.sexual.pleasure.base = 13
        engage(self.player, second_monster)
        second_record = read_session(self.player)
        self.assertNotEqual(second_record.engagement_id, first_record.engagement_id)
        with patch(
            "world.rules.combat.battlefield.roll_d100", return_value=1
        ), patch("world.rules.combat.damage.roll_d100", return_value=1), patch(
            "world.rules.combat.rounds.roll_d100", return_value=1
        ), self._patch_rolls([1, 1]):
            submit_player_action(self.player, BASIC_ATTACK_KEY, [second_monster])
            forfeit(self.player)
        second_sources = {
            source
            for source in NarrativeEvent.objects.filter(
                event_type="adult_action",
                content__act_key="defeat_violation",
            ).values_list("source_id", flat=True)
        } - set(first_sources)
        self.assertTrue(second_sources)
        for source in second_sources:
            self.assertIn(second_record.engagement_id, source)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_resisted_attempt_records_the_crossing_it_actually_caused(self):
        """Scenario: a resisted attempt keeps resistance and its real transition."""
        self._equalize_scores()
        self._arouse(13)
        self.player.sexual.climax_phase.value = "接近"
        self.player.sexual.pleasure.base = 40
        engage(self.player, self.monster)
        record = read_session(self.player)
        with self._patch_rolls([100]):
            self._settle()
        event = NarrativeEvent.objects.get(
            event_type="adult_action",
            source_id=(
                f"defeat:{record.engagement_id}:{self.monster.pk}"
                f":attempt:0:victim:{self.player.pk}"
            ),
        )
        self.assertTrue(event.content["outcomes"]["resistance"][0]["resisted"])
        self.assertEqual(
            [row["event"] for row in event.content["outcomes"]["transitions"]],
            ["climax_onset"],
        )
        self.assertEqual(event.content["outcomes"]["counters"], [])
        self.assertEqual(
            [row["identifier"] for row in event.content["milestones"]],
            ["climax_onset"],
        )
        room = self.player.location
        self.assertEqual(
            event.content["location"], {"id": str(room.pk), "label": room.key}
        )
        self.assertEqual(event.location, str(room.pk))
        milestone = NarrativeEvent.objects.get(
            event_type="adult_milestone",
            content__action_source_id=event.source_id,
        )
        self.assertEqual(
            milestone.content["location"], {"id": str(room.pk), "label": room.key}
        )
        self.assertEqual(milestone.location, str(room.pk))
        # The later digest/settlement phases may move the phase on; the
        # attempt's own record is the transition-time evidence.
        self.assertNotEqual(self.player.sexual.climax_phase.level, "接近")
        self.assertEqual(self.player.sexual.hostile_act_count, 0)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_landed_attempt_records_the_counter_unlock_it_actually_crossed(self):
        """A landed attempt's own counter credit unlocks only at the real threshold."""
        self._equalize_scores()
        self._arouse(13)
        for _ in range(4):
            self.player.sexual.record_hostile_act()
        engage(self.player, self.monster)
        record = read_session(self.player)
        with self._patch_rolls([1, 1]):
            self._settle()
        first = NarrativeEvent.objects.get(
            event_type="adult_action",
            source_id=(
                f"defeat:{record.engagement_id}:{self.monster.pk}"
                f":attempt:0:victim:{self.player.pk}"
            ),
        )
        self.assertFalse(first.content["outcomes"]["resistance"][0]["resisted"])
        self.assertIn(
            "act_unlock",
            [row["milestone_kind"] for row in first.content["milestones"]],
        )
        counters = first.content["outcomes"]["counters"]
        self.assertEqual(
            {row["target_id"] for row in counters},
            {str(self.player.pk), str(self.monster.pk)},
        )

        # A threshold already met before the attempt is never dated as recent.
        while self.player.sexual.hostile_act_count < 5:
            self.player.sexual.record_hostile_act()
        second_monster = self._lore_monster("哥布林")
        second_monster.location = self.room
        self._equalize_scores(second_monster)
        second_monster.sexual.pleasure.base = 13
        engage(self.player, second_monster)
        second_record = read_session(self.player)
        with patch(
            "world.rules.combat.battlefield.roll_d100", return_value=1
        ), patch("world.rules.combat.damage.roll_d100", return_value=1), patch(
            "world.rules.combat.rounds.roll_d100", return_value=1
        ), self._patch_rolls([1, 1]):
            submit_player_action(self.player, BASIC_ATTACK_KEY, [second_monster])
            forfeit(self.player)
        for event in NarrativeEvent.objects.filter(
            event_type="adult_action",
            content__act_key="defeat_violation",
            source_id__startswith=f"defeat:{second_record.engagement_id}:",
        ):
            self.assertNotIn(
                "act_unlock",
                [row["milestone_kind"] for row in event.content["milestones"]],
            )


class PoolAndDigestTests(ViolationBase):
    """The victim pool's player baseline and the digest handoff (D-V7)."""

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-attempts-select-victims-from-the-target-pool",
    )
    def test_every_attempt_targets_the_player_and_the_companion_is_untouched(self):
        # A conscious companion is not a victim: the full pool is the player
        # plus KNOCKED-OUT companions, so a standing companion stays outside
        # it and every attempt keeps targeting the player.
        companion = create_object(NPC, key="violation companion")
        companion.location = self.room
        join_party(companion, self.player)
        self._equalize_scores()
        self._arouse(13)
        companion_pleasure = 50
        companion.sexual.pleasure.base = companion_pleasure
        with self._patch_rolls([1, 1]):
            result = self._defeat()
        acts = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "violation_act"
        ]
        self.assertTrue(acts)
        for entry in acts:
            self.assertEqual(entry.target, str(self.player.key))
        self.assertEqual(companion.sexual.pleasure.value, companion_pleasure)
        self.assertEqual(companion.sexual.hostile_act_count, 0)
        self.assertEqual(companion.sexual.interspecies_act_count, 0)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_unselected_pool_member_and_untouched_ally_receive_no_adult_evidence(self):
        """Scenario: no invented participation for unselected or untouched allies."""
        unselected = self._companion("unselected companion")
        untouched = self._companion("untouched standing ally")
        self._equalize_scores(unselected, untouched)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(unselected)
        # The target draw selects pool index 0 (the player) for both attempts.
        with self._patch_purpose_rolls([0, 0], [1, 1]):
            self._settle()

        actions = list(
            NarrativeEvent.objects.filter(
                event_type="adult_action",
                content__act_key="defeat_violation",
            )
        )
        self.assertEqual(len(actions), 2)
        for event in actions:
            self.assertEqual(
                [row["id"] for row in event.content["recipients"]],
                [str(self.player.pk)],
            )
            for entity in (unselected, untouched):
                self.assertNotIn(str(entity.pk), event.content["field_access"])
                self.assertNotIn(str(entity.pk), event.participants)
        milestone_entities = {
            event.content["entity_id"]
            for event in NarrativeEvent.objects.filter(event_type="adult_milestone")
        }
        self.assertEqual(milestone_entities - {str(self.player.pk)}, set())

        # No disclosure either: neither ally is authorized any adult group,
        # and no forbidden source rides inside another factual group.
        forbidden = {event.source_id for event in actions} | {
            event.source_id
            for event in NarrativeEvent.objects.filter(event_type="adult_milestone")
        }
        for entity in (unselected, untouched):
            selection = select_authorized_recent_deeds(
                entity, frozen_tick=self.clock.tick
            )
            self.assertFalse(
                {group.group_type for group in selection.groups}
                & {"adult_action", "adult_milestone"}
            )
            cited = {
                source_id
                for group in selection.groups
                for source_id in group.source_ids
            }
            self.assertFalse(cited & forbidden)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::the-sequence-hands-digest-ready-outcomes-to-the-same-settlement-call",
    )
    def test_digest_outcome_matches_the_eventlog_and_is_not_persisted(self):
        self._equalize_scores()
        self._arouse(13)
        captured = {}
        real_writer = defeat_aftermath_module.run_defeat_aftermath

        def spy(actor, record, battlefield):
            outcome = real_writer(actor, record, battlefield)
            captured["outcomes"] = outcome.violation
            return outcome

        self.player.sexual.pleasure.base = 84
        with (
            self._patch_rolls([1, 100]),
            patch.object(
                defeat_aftermath_module, "run_defeat_aftermath", side_effect=spy
            ),
        ):
            result = self._defeat()
        entries = _aftermath_entries(result)
        # The handoff is the per-participant mapping (companion-victims
        # D-P3); a solo pool carries exactly the player's outcome.
        self.assertEqual(set(captured["outcomes"]), {str(self.player.key)})
        outcome = captured["outcomes"][str(self.player.key)]
        self.assertIsInstance(outcome, defeat_aftermath_module.ViolationOutcome)
        self.assertEqual(
            outcome.selected,
            _kinds(entries).count("violation_attempt"),
        )
        self.assertEqual(outcome.landed, _kinds(entries).count("violation_act"))
        self.assertEqual(
            outcome.resisted, _kinds(entries).count("violation_resisted")
        )
        self.assertEqual(
            outcome.climax_delta,
            sum(
                1
                for entry in entries
                if entry.kind == "violation_act" and entry.data["climax"]
            ),
        )
        self.assertFalse(outcome.zero_landed)
        # In-memory only: the settlement result carries no ViolationOutcome
        # object anywhere in its handoff.
        self.assertNotIn(
            defeat_aftermath_module.ViolationOutcome,
            [type(value) for value in result.values()],
        )


class EventLogOrderTests(ViolationBase):
    """The hook splice: violation kinds between defeat_settle and departure."""

    @covers_requirement(
        "defeat-aftermath-violation-sequence::the-sequence-registers-into-the-core-s-guarded-hook-and-emits-declared-eventlog-kinds",
    )
    def test_violation_entries_splice_between_the_core_kinds(self):
        slime = self._lore_monster("史萊姆")
        slime.location = self.room
        slime.sexual.pleasure.base = 13
        self._equalize_scores()
        self._arouse(13)
        engage(self.player, self.monster)
        # One session, two violators: extend the durable record's enemies
        # (the coercion suites' persisted-record seam) so both winners are
        # living foes at settlement.
        from dataclasses import replace as dataclass_replace

        from world.rules import combat_session as combat_session_module

        record = read_session(self.player)
        combat_session_module._persist(
            self.player,
            dataclass_replace(
                record, enemy_ids=(*record.enemy_ids, int(slime.pk))
            ),
        )
        with self._patch_rolls([1, 1]):
            with patch("world.rules.combat.battlefield.roll_d100", return_value=1), patch("world.rules.combat.damage.roll_d100", return_value=1), patch("world.rules.combat.rounds.roll_d100", return_value=1):
                submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
            result = forfeit(self.player)
        kinds = _kinds(_aftermath_entries(result))
        self.assertEqual(
            kinds,
            [
                "defeat_settle",
                "violation_attempt",
                "violation_act",
                "violation_attempt",
                "violation_act",
                "violation_attempt",
                "violation_act",
                "violation_attempt",
                "violation_act",
                "weak_granted",
                "recovery_advance",
                "digest_outcome",
            ],
        )

    @covers_requirement(
        "defeat-aftermath-violation-sequence::the-sequence-registers-into-the-core-s-guarded-hook-and-emits-declared-eventlog-kinds",
    )
    def test_violation_kinds_render_their_zh_tw_template_lines(self):
        self._equalize_scores()
        self._arouse(13)
        with self._patch_rolls([1, 100]):
            result = self._defeat()
        (log,) = _aftermath_logs(result)
        lines = render_plain_text(log).splitlines()
        self.assertEqual(len(lines), len(log.entries))
        self.assertTrue(all(line.strip() for line in lines))
        from world.rules.player_messages import DEFEAT_AFTERMATH_TEMPLATES

        rendered_attempts = [
            line
            for entry, line in zip(log.entries, lines)
            if entry.kind == "violation_attempt"
        ]
        self.assertEqual(
            rendered_attempts,
            [
                DEFEAT_AFTERMATH_TEMPLATES["violation_attempt"].format(
                    actor=entry.actor, target=entry.target, data=entry.data
                )
                for entry in log.entries
                if entry.kind == "violation_attempt"
            ],
        )


class FlagOffTests(ViolationBase):
    """The flag-off state is structurally the core settlement (D-V6)."""

    @covers_requirement(
        "defeat-aftermath-violation-sequence::the-sequence-registers-into-the-core-s-guarded-hook-and-emits-declared-eventlog-kinds",
    )
    @override_settings(DEFEAT_ADULT_SCENES=False)
    def test_flag_off_settles_exactly_the_core_path(self):
        self._equalize_scores()
        self._arouse(90)
        result = self._defeat()
        kinds = _kinds(_aftermath_entries(result))
        for kind in ("violation_attempt", "violation_act", "violation_resisted"):
            self.assertNotIn(kind, kinds)
        # No victory arousal, no deltas, no credits with the flag off: the
        # aroused monster keeps exactly the pleasure the fight left it.
        self.assertEqual(self.monster.sexual.pleasure.value, 90)
        self.assertEqual(self.player.sexual.pleasure.value, 0)
        self.assertEqual(self.monster.sexual.hostile_act_count, 0)
        self.assertEqual(self.player.sexual.hostile_act_count, 0)
        settle = next(
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "defeat_settle"
        )
        self.assertEqual(settle.data["wake"], DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0])
        self.assertEqual(self.player.traits.hp.current, wake_target(self.player))
