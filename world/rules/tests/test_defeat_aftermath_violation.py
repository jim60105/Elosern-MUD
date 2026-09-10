"""Defeat violation sequence tests (defeat-aftermath-violation-sequence).

Covers the DA4 delta: victory arousal, the archetype threshold gate with its
attempt cap, state-derived dice, the shipped resist contest with the victim
defending, symmetric counter credits, per-attempt world-clock advances, the
first-resistance violator stop, the zero-landed PG variant, the guarded-hook
registration with its EventLog splice, and the in-memory digest handoff.
"""

import unittest
from dataclasses import replace as dataclass_replace
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

import world.rules.defeat_aftermath as defeat_aftermath_module
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
from tools.spec_traceability import covers_requirement

from ._combat_session_helpers import BattlefieldIsolation, _player

def _aftermath_logs(result):
    """Return the defeat aftermath EventLog of one settlement result."""
    return [
        log for log in result["logs"] if log.skill_key == "defeat_aftermath"
    ]


def _aftermath_entries(result):
    """Return the aftermath's ordered EventEntry list of one settlement."""
    (log,) = _aftermath_logs(result)
    return list(log.entries)


def _kinds(entries):
    return [entry.kind for entry in entries]


class ViolationBase(BattlefieldIsolation, EvenniaTestCase):
    """Shared clock isolation, hook save/restore, and lore-keyed winners.

    The production hook body registers at import (DA4 D-V6). Every test
    saves the process-wide hook and restores exactly that value, then
    re-registers the engine, so test order can never leave the global in a
    mutated state (rubber-duck implementation review finding 5).
    """

    def setUp(self):
        super().setUp()
        # The resist contest's affinity config validates quest keys against
        # the quest definition registry (same bootstrap as the coercion suites).
        register_catalog()
        self.room = create_object(Room, key="violation arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = self._lore_monster("哥布林")
        self.monster.location = self.room
        self.clock = WorldClock()
        for target in (
            "world.rules.combat_session.get_world_clock",
            "world.rules.clock.get_world_clock",
        ):
            patcher = patch(target, return_value=self.clock)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(
            setattr,
            defeat_aftermath_module,
            "_VIOLATION_HOOK",
            defeat_aftermath_module._VIOLATION_HOOK,
        )
        register_violation_hook(run_violation_sequence)

    def _lore_monster(self, name, atk=10):
        """Create one tier-floor monster keyed by a lore species name."""
        monster = create_object(Monster, key=name)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = 100
        monster.traits.hp.current = 100
        monster.traits.atk_phys.base = atk
        return monster

    def _companion(self, key):
        """Create one co-located companion bound to the player's party."""
        companion = create_object(NPC, key=key)
        companion.location = self.room
        companion.race = "human"
        companion.apply_race_baseline()
        join_party(companion, self.player)
        return companion

    def _equalize_scores(self, *extra):
        """Make the resist contest a pure roll gate: resisted iff roll >= 51.

        With equal blended scores on both sides the shipped contest formula
        (roll + resister_score >= 51 + actor_score) reduces to the raw roll.
        """
        for entity in (self.player, self.monster, *extra):
            entity.traits.agility.base = 10
            entity.traits.atk_phys.base = 10

    def _arouse(self, pleasure):
        """Raise the winner's pleasure to simulate mid-fight accumulation."""
        self.monster.sexual.pleasure.base = pleasure

    def _defeat(self):
        """Drive one hostile defeat settlement through ``forfeit``."""
        engage(self.player, self.monster)
        return self._settle()

    def _settle(self):
        """Lose and forfeit the already-engaged session."""
        with patch("world.rules.combat.roll_d100", return_value=1):
            submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        return forfeit(self.player)

    def _knock_out(self, companion):
        """Mark one companion knocked out on the durable record (and floor)."""
        companion.traits.hp.current = 1
        record = read_session(self.player)
        combat_session_module._persist(
            self.player,
            dataclass_replace(
                record,
                knocked_out_ids=(*record.knocked_out_ids, int(companion.pk)),
            ),
        )

    def _flee(self, companion):
        """Mark one companion fled on the durable record."""
        record = read_session(self.player)
        combat_session_module._persist(
            self.player,
            dataclass_replace(
                record,
                fled_ids=(*record.fled_ids, int(companion.pk)),
            ),
        )

    def _patch_rolls(self, rolls):
        """Patch the engine's derivation to return ``rolls`` by attempt index."""
        return patch.object(
            defeat_aftermath_module,
            "derived_roll",
            side_effect=lambda *args: rolls[args[3]],
        )

    def _patch_purpose_rolls(self, target_rolls, resist_rolls):
        """Patch the derivation purpose-aware (companion-victims D-P1).

        ``target_rolls[attempt_index]`` feeds the target-selection draws
        (purpose ``target``); ``resist_rolls[attempt_index]`` feeds the
        resist contests (purpose ``resist``).
        """

        def roll(session_id, violator_key, victim_key, attempt_index, purpose):
            if purpose == "target":
                return target_rolls[attempt_index]
            return resist_rolls[attempt_index]

        return patch.object(
            defeat_aftermath_module,
            "derived_roll",
            side_effect=roll,
        )


class EventSourceIsolation:
    """Snapshot/restore the process-global clock event-source registry."""

    def isolate_event_sources(self) -> None:
        backup = dict(clock_module._EVENT_SOURCES)
        clock_module._EVENT_SOURCES.clear()
        self.addCleanup(self._restore_event_sources, backup)

    def _restore_event_sources(self, backup) -> None:
        clock_module._EVENT_SOURCES.clear()
        clock_module._EVENT_SOURCES.update(backup)


class StateDerivedRollTests(unittest.TestCase):
    """The pure derivation: deterministic, key-sensitive, d100-bounded."""

    def test_repeated_calls_with_identical_keys_are_identical(self):
        first = derived_roll("hostile:1:100", "7", "3", 0, "resist")
        second = derived_roll("hostile:1:100", "7", "3", 0, "resist")
        self.assertEqual(first, second)

    def test_every_key_field_shifts_the_roll(self):
        base_args = ("hostile:1:100", "7", "3", 0, "resist")
        base = derived_roll(*base_args)
        shifted = 0
        for field in range(5):
            variants = set()
            for delta in range(1, 9):
                args = list(base_args)
                args[field] = (
                    delta if field == 3 else f"{args[field]}#{delta}"
                )
                variants.add(derived_roll(*args))
            if base not in variants and len(variants) > 1:
                shifted += 1
        # Every field materially participates in the digest: mutating it
        # moves the roll for this sample of keys (one benign collision on a
        # mutated value would still leave len(variants) > 1).
        self.assertEqual(shifted, 5)

    def test_rolls_stay_in_the_d100_range(self):
        for index in range(200):
            value = derived_roll("hostile:1:100", str(index), "3", index, "resist")
            self.assertGreaterEqual(value, 1)
            self.assertLessEqual(value, 100)

    def test_distribution_over_the_key_space_is_bounded(self):
        samples = 4000
        buckets = [0] * 101
        for index in range(samples):
            buckets[
                derived_roll("hostile:1:100", str(index), "3", index, "resist")
            ] += 1
        observed = buckets[1:]
        expected = samples / 100
        # A keyed hash is not a casino die; the design pins only uniformity
        # across the key space within generous bounds (D-V4 risk note).
        self.assertGreater(min(observed), expected * 0.4)
        self.assertLess(max(observed), expected * 1.7)

    def test_malformed_keys_fail_closed(self):
        with self.assertRaises(ValueError):
            derived_roll("", "7", "3", 0, "resist")
        for bad in ("|hostile", "hostile|"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    derived_roll(bad, "7", "3", 0, "resist")
                with self.assertRaises(ValueError):
                    derived_roll("hostile:1:100", bad, "3", 0, "resist")
                with self.assertRaises(ValueError):
                    derived_roll("hostile:1:100", "7", bad, 0, "resist")
                with self.assertRaises(ValueError):
                    derived_roll("hostile:1:100", "7", "3", 0, bad)
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100|7", "7", "3", 0, "resist")
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100", "7", "", 0, "resist")
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100", "7", "3", -1, "resist")
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100", "7", "3", 0, "")
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100", "7", "3", True, "resist")


class ThresholdGateTests(ViolationBase):
    """Victory arousal and the archetype threshold gate (D-V2)."""

    @covers_requirement(
        "defeat-aftermath-violation-sequence::living-defeat-winners-gain-archetype-victory-arousal",
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
    )
    def test_below_threshold_winner_gains_the_delta_but_never_violates(self):
        result = self._defeat()
        entries = _aftermath_entries(result)
        self.assertNotIn("violation_attempt", _kinds(entries))
        # The goblin row's victory delta landed even without a sequence.
        self.assertEqual(self.monster.sexual.pleasure.value, 2)
        # The player's sexual state is untouched on the PG path.
        self.assertEqual(self.player.sexual.pleasure.value, 0)
        self.assertEqual(self.player.sexual.hostile_act_count, 0)
        self.assertEqual(self.player.sexual.interspecies_act_count, 0)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::living-defeat-winners-gain-archetype-victory-arousal",
    )
    def test_mid_fight_arousal_carries_into_the_victory_gate(self):
        # One pleasure point below the 微興奮 band floor: only the victory
        # delta pushes the goblin over its threshold (the design's emergent
        # chain — the player's own casts provoke the violation).
        self._arouse(13)
        result = self._defeat()
        self.assertIn("violation_attempt", _kinds(_aftermath_entries(result)))

    @covers_requirement(
        "defeat-aftermath-violation-sequence::living-defeat-winners-gain-archetype-victory-arousal",
    )
    def test_pleasure_overflow_clamps_without_wrapping(self):
        self._arouse(99)
        result = self._defeat()
        self.assertEqual(self.monster.sexual.pleasure.value, 100)
        self.assertEqual(self.monster.sexual.arousal.level, "極限")
        self.assertIn("violation_attempt", _kinds(_aftermath_entries(result)))

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
    )
    def test_missing_archetype_row_is_inert_and_logs_once(self):
        self.monster.key = "defeat goblin"
        self._arouse(90)
        with patch.object(defeat_aftermath_module, "log_warn") as warn:
            result = self._defeat()
        self.assertNotIn("violation_attempt", _kinds(_aftermath_entries(result)))
        warnings = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "defeat_aftermath_violation_archetype_missing"
        ]
        self.assertEqual(len(warnings), 1)
        context = warnings[0].kwargs["context"]
        self.assertEqual(context["archetype"], "defeat goblin")
        self.assertIn("tick", context)


class ViolationRulebookTests(unittest.TestCase):
    """The ``violation`` section's fail-closed loader validation (D-V2)."""

    VALID_HEADER = (
        "pg_lines:\n  - '你醒了。'\nweak_debuff:\n  buff_key: defeat_weak\n"
        "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 21600\n"
        "  wake_fraction: 0.05\n"
        # The DA6-owned digest section: every owned section must be present
        # and valid for any single section's mutation to be the only failure.
        "digest:\n"
        "  rows:\n"
        "    - id: residue\n"
        "      when:\n"
        "        sensitivity_level: [高, 極高, 敏感異常]\n"
        "        outcome.climax_count: {min: 1}\n"
        "      outcome: residue\n"
        "      buff: aftermath_residue\n"
        "    - id: humiliated\n"
        "      when:\n"
        "        sensitivity_level: [普通]\n"
        "        shame_level: [強烈, 成癮]\n"
        "        outcome.zero_landed: true\n"
        "      outcome: humiliated\n"
        "      buff: aftermath_humiliated\n"
        "    - id: none\n"
        "      when: {}\n"
        "      outcome: none\n"
        "      buff: null\n"
    )

    def setUp(self):
        self._paths = []

    def tearDown(self):
        import os

        for path in self._paths:
            os.unlink(path)

    def _load(self, section_text):
        """Write one YAML body with the given violation section and load it."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(self.VALID_HEADER + section_text)
            path = handle.name
        self._paths.append(path)
        return load_defeat_aftermath_sections(Path(path))

    @staticmethod
    def _row(**overrides):
        fields = {
            "victory_pleasure_delta": "2",
            "threshold_ordinal": "1",
            "attempt_cap": "2",
            "attempt_duration_seconds": "120",
            "landed_deltas": "{victim_pleasure: 16, aggressor_pleasure: 10}",
            "resisted_deltas": "{victim_pleasure: 4, aggressor_pleasure: 3}",
            "credited_counters": "[hostile_act_count, interspecies_act_count]",
        }
        fields.update(overrides)
        return "".join(f"      {key}: {value}\n" for key, value in fields.items())

    def _section(self, wake_line="  violated_wake_line: '測試喚醒。'\n", row=None):
        return (
            "violation:\n"
            + wake_line
            + "  archetypes:\n"
            + "    哥布林:\n"
            + (row if row is not None else self._row())
        )

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
    )
    def test_valid_section_loads_immutable_rows(self):
        rulebook = self._load(self._section())
        row = rulebook.violation.rows["哥布林"]
        self.assertEqual(row.victory_pleasure_delta, 2)
        self.assertEqual(row.threshold_ordinal, 1)
        self.assertEqual(row.attempt_cap, 2)
        self.assertEqual(
            row.credited_counters, ("hostile_act_count", "interspecies_act_count")
        )

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
    )
    def test_non_lore_species_key_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section().replace("哥布林", "goblin"))

    def test_shame_key_is_rejected(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section(row=self._row(threshold_ordinal="1\n      shame: 輕微"))
            )

    def test_unknown_row_key_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section(row=self._row(threshold_ordinal="1\n      baseline: {}"))
            )

    def test_direction_bound_counter_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section(
                    row=self._row(credited_counters="[hostile_act_count, watched_count]")
                )
            )

    def test_unknown_counter_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section(row=self._row(credited_counters="[not_a_counter]")))

    def test_duplicate_credit_counter_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section(
                    row=self._row(credited_counters="[hostile_act_count, hostile_act_count]")
                )
            )

    def test_threshold_ordinal_out_of_vocabulary_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section(row=self._row(threshold_ordinal="5")))

    def test_unknown_delta_key_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section(row=self._row(landed_deltas="{victim_shame: 1}")))

    def test_empty_deltas_fail_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section(row=self._row(landed_deltas="{}")))

    def test_missing_wake_line_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section().replace("  violated_wake_line: '測試喚醒。'\n", "")
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
        # Combat 6s + two 120s attempts + the 8s recovery solve (the empty
        # attempt scope never regenerates the victim, so the solve still runs
        # from HP 1 to the 5% target).
        self.assertEqual(self.clock.tick, 6 + 2 * 120 + 8)
        self.assertEqual(self.player.traits.hp.current, 5)
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
        # The resisted attempt still spends its declared duration.
        self.assertEqual(self.clock.tick, 6 + 120 + 8)

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
        real_roll = defeat_aftermath_module.derived_roll

        def counting_roll(*args):
            consumed.append(args)
            return real_roll(*args)

        with patch.object(
            defeat_aftermath_module, "derived_roll", side_effect=counting_roll
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


class CompanionPoolTests(ViolationBase):
    """The full violation pool: companion victims, exclusion, and wakes."""

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-attempts-select-victims-from-the-target-pool",
        "defeat-aftermath-violation-sequence::each-attempt-rolls-the-shipped-resist-contest-with-the-victim-defending",
    )
    def test_knocked_out_companion_takes_her_own_writes_and_credits(self):
        companion = self._companion("violated companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        # Pool = [player, companion]; both target draws pick slot 1 (the
        # companion) and both contests land.
        with self._patch_purpose_rolls([1, 1], [1, 1]):
            result = forfeit(self.player)
        entries = _aftermath_entries(result)
        self.assertEqual(_kinds(entries).count("violation_attempt"), 2)
        self.assertEqual(_kinds(entries).count("violation_act"), 2)
        for entry in entries:
            if entry.kind in ("violation_attempt", "violation_act"):
                self.assertEqual(entry.target, str(companion.key))
        # Her own deltas and counters, never proxied through the player.
        self.assertEqual(companion.sexual.pleasure.value, 2 * 16)
        self.assertEqual(companion.sexual.hostile_act_count, 2)
        self.assertEqual(companion.sexual.interspecies_act_count, 2)
        # Symmetric crediting: the violator credits exactly once per attempt.
        self.assertEqual(self.monster.sexual.hostile_act_count, 2)
        self.assertEqual(self.monster.sexual.interspecies_act_count, 2)
        self.assertEqual(self.monster.sexual.pleasure.value, 13 + 2 + 2 * 10)
        # The player was never targeted and stays untouched.
        self.assertEqual(self.player.sexual.pleasure.value, 0)
        self.assertEqual(self.player.sexual.hostile_act_count, 0)
        # Attempts landed only on her: the player's wake prose stays PG.
        settle = next(entry for entry in entries if entry.kind == "defeat_settle")
        self.assertEqual(settle.data["wake"], DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0])
        # Two executed attempts spend their declared durations; the recovery
        # solve then walks HP 1 to the 5% wake target (no round seconds).
        self.assertEqual(self.clock.tick, 2 * 120 + 8)
        self.assertEqual(self.player.traits.hp.current, 5)

    def test_fled_companion_is_excluded_before_the_draw(self):
        fled_companion = self._companion("zulu companion")
        knocked = self._companion("alpha companion")
        self._equalize_scores(knocked)
        self._arouse(13)
        engage(self.player, self.monster)
        self._flee(fled_companion)
        self._knock_out(knocked)
        # Pool = [player, knocked]: the fled companion is filtered out
        # before the draw, so slot 1 resolves to the knocked-out companion
        # even though the fled companion's key sorts first.
        with self._patch_purpose_rolls([1, 1], [1, 100]):
            result = forfeit(self.player)
        entries = _aftermath_entries(result)
        self.assertEqual(_kinds(entries).count("violation_act"), 1)
        self.assertEqual(
            [entry.target for entry in entries if entry.kind == "violation_act"],
            [str(knocked.key)],
        )
        # Landed deltas (16) plus the resisted attempt's shrunk delta (4).
        self.assertEqual(knocked.sexual.pleasure.value, 16 + 4)
        self.assertEqual(knocked.sexual.hostile_act_count, 1)
        # The fled companion's records are untouched: never selected.
        self.assertEqual(fled_companion.sexual.pleasure.value, 0)
        self.assertEqual(fled_companion.sexual.hostile_act_count, 0)
        self.assertEqual(fled_companion.sexual.interspecies_act_count, 0)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-attempts-select-victims-from-the-target-pool",
    )
    def test_all_allies_fled_settles_like_the_solo_baseline(self):
        companion = self._companion("departed companion")
        self._equalize_scores()
        self._arouse(13)
        engage(self.player, self.monster)
        self._flee(companion)
        with self._patch_purpose_rolls([1, 1], [1, 1]) as rolls:
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
                "weak_granted",
                "recovery_advance",
                "digest_outcome",
            ],
        )
        # A solo pool never touches the target dice: the pinned baseline's
        # derivation call shape (resist draws only) is preserved.
        for call in rolls.call_args_list:
            self.assertEqual(call.args[4], "resist")
        # Every attempt targeted the player; the fled companion is untouched.
        for entry in _aftermath_entries(result):
            if entry.kind in ("violation_attempt", "violation_act"):
                self.assertEqual(entry.target, str(self.player.key))
        self.assertEqual(companion.sexual.pleasure.value, 0)
        self.assertEqual(companion.sexual.hostile_act_count, 0)

    def test_mixed_two_victim_sequence_credits_the_violator_once_per_attempt(self):
        companion = self._companion("mixed companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        # Attempt 0 draws slot 1 (the companion), attempt 1 slot 0 (the
        # player); both contests land.
        with patch.object(defeat_aftermath_module, "log_info") as info:
            with self._patch_purpose_rolls([1, 0], [1, 1]):
                with self.captureOnCommitCallbacks(execute=True):
                    result = forfeit(self.player)
        acts = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "violation_act"
        ]
        self.assertEqual(
            [entry.target for entry in acts],
            [str(companion.key), str(self.player.key)],
        )
        # One credit per attempt against the violator — never one per victim
        # per attempt (the double-credit risk D-P2 names).
        self.assertEqual(self.monster.sexual.hostile_act_count, 2)
        self.assertEqual(self.monster.sexual.interspecies_act_count, 2)
        self.assertEqual(companion.sexual.hostile_act_count, 1)
        self.assertEqual(self.player.sexual.hostile_act_count, 1)
        # Boundary telemetry: victims counts distinct selected participants.
        boundary = [
            call.kwargs["context"]
            for call in info.call_args_list
            if call.args and call.args[0] == "defeat_aftermath_violation"
        ]
        self.assertEqual(len(boundary), 1)
        self.assertEqual(boundary[0]["victims"], 2)
        self.assertEqual(boundary[0]["attempts"], 2)
        self.assertEqual(boundary[0]["landed"], 2)

    def test_unselected_pool_companion_gets_no_outcome_and_no_wake_line(self):
        companion = self._companion("overlooked companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        captured = {}
        real_writer = defeat_aftermath_module.run_defeat_aftermath

        def spy(actor, record, battlefield):
            outcome = real_writer(actor, record, battlefield)
            captured["outcomes"] = outcome.violation
            return outcome

        with (
            self._patch_purpose_rolls([0, 0], [1, 1]),
            patch.object(
                defeat_aftermath_module, "run_defeat_aftermath", side_effect=spy
            ),
        ):
            result = forfeit(self.player)
        # Both attempts drew slot 0 (the player): the companion is absent
        # from the outcome mapping (D-P3) and gets no wake observation.
        self.assertEqual(set(captured["outcomes"]), {str(self.player.key)})
        self.assertNotIn("companion_wake", _kinds(_aftermath_entries(result)))
        self.assertEqual(companion.sexual.pleasure.value, 0)
        self.assertEqual(companion.sexual.hostile_act_count, 0)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::knocked-out-companions-wake-with-their-own-digest-observation",
    )
    def test_companion_wake_observation_is_rendered_with_matching_counts(self):
        companion = self._companion("waking companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        with self._patch_purpose_rolls([1, 1], [1, 1]):
            result = forfeit(self.player)
        (log,) = _aftermath_logs(result)
        wakes = [entry for entry in log.entries if entry.kind == "companion_wake"]
        self.assertEqual(len(wakes), 1)
        wake = wakes[0]
        self.assertEqual(wake.actor, str(companion.key))
        self.assertEqual(
            wake.data,
            {
                "selected": 2,
                "landed": 2,
                "resisted": 0,
                "climax": 0,
                "zero_landed": False,
            },
        )
        # The counts equal the EventLog's own entry counts for her.
        self.assertEqual(
            wake.data["selected"],
            sum(
                1
                for entry in log.entries
                if entry.kind == "violation_attempt"
                and entry.target == str(companion.key)
            ),
        )
        self.assertEqual(
            wake.data["landed"],
            sum(
                1
                for entry in log.entries
                if entry.kind == "violation_act"
                and entry.target == str(companion.key)
            ),
        )
        # The observation renders exactly once, naming her.
        lines = render_plain_text(log).splitlines()
        rendered = [
            line
            for entry, line in zip(log.entries, lines)
            if entry.kind == "companion_wake"
        ]
        self.assertEqual(len(rendered), 1)
        self.assertIn(str(companion.key), rendered[0])

    def test_companion_violation_entries_render_their_companion_templates(self):
        from world.rules.player_messages import DEFEAT_AFTERMATH_TEMPLATES

        companion = self._companion("observed companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        # Attempt 0 lands on her; attempt 1 is resisted by her (and is the
        # violator's last under the stop rule).
        with self._patch_purpose_rolls([1, 1], [1, 100]):
            result = forfeit(self.player)
        (log,) = _aftermath_logs(result)
        entries = [
            entry for entry in log.entries if entry.kind.startswith("violation_")
        ]
        self.assertEqual(
            [entry.kind for entry in entries],
            [
                "violation_attempt",
                "violation_act",
                "violation_attempt",
                "violation_resisted",
            ],
        )
        for entry in entries:
            self.assertEqual(entry.target, str(companion.key))
        self.assertEqual(
            [entry.text_template for entry in entries],
            [
                DEFEAT_AFTERMATH_TEMPLATES["violation_attempt_companion"],
                DEFEAT_AFTERMATH_TEMPLATES["violation_act_companion"],
                DEFEAT_AFTERMATH_TEMPLATES["violation_attempt_companion"],
                DEFEAT_AFTERMATH_TEMPLATES["violation_resisted_companion"],
            ],
        )
        lines = render_plain_text(log).splitlines()
        rendered = [
            line
            for entry, line in zip(log.entries, lines)
            if entry.kind.startswith("violation_")
        ]
        for line in rendered:
            self.assertIn(str(companion.key), line)

    def test_pool_order_is_canonical_across_paths(self):
        zulu = self._companion("zulu companion")  # created first: lower pk
        alpha = self._companion("alpha companion")  # created second: higher pk
        standing = self._companion("standing companion")
        engage(self.player, self.monster)
        self._knock_out(zulu)
        self._knock_out(alpha)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        pool_live = defeat_aftermath_module._violation_pool(
            self.player, record, battlefield
        )
        pool_degraded = defeat_aftermath_module._violation_pool(
            self.player, record, None
        )
        # Canonical order (player first, companions by ascending pk) is
        # identical from both paths even though the keys sort differently.
        self.assertEqual(pool_live, pool_degraded)
        self.assertEqual(
            [str(entity.key) for entity in pool_live],
            [str(self.player.key), "zulu companion", "alpha companion"],
        )
        # A conscious companion is never a pool member.
        self.assertNotIn(
            str(standing.key), [str(entity.key) for entity in pool_live]
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
            with patch("world.rules.combat.roll_d100", return_value=1):
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
        self.assertEqual(self.player.traits.hp.current, 5)


class RollbackReplayTests(EventSourceIsolation, ViolationBase):
    """State-derived dice: a rolled-back retry re-derives the sequence."""

    def setUp(self):
        super().setUp()
        self.isolate_event_sources()

    @covers_requirement(
        "defeat-aftermath-violation-sequence::sequence-dice-are-state-derived-pure-values",
    )
    def test_rolled_back_settlement_rederives_the_identical_sequence(self):
        self._equalize_scores()
        self._arouse(13)
        # Force every contest to land through the shipped score formula (the
        # monster towers over the victim), so both cap attempts execute with
        # their real state-derived rolls and the injection aligns.
        self.monster.traits.agility.base = 500
        self.monster.traits.atk_phys.base = 500
        player_pleasure_before = self.player.sexual.pleasure.value
        monster_pleasure_before = self.monster.sexual.pleasure.value
        real_roll = defeat_aftermath_module.derived_roll
        calls = []

        def recording_roll(session_id, violator_key, victim_key, attempt_index, purpose):
            value = real_roll(
                session_id, violator_key, victim_key, attempt_index, purpose
            )
            calls.append(
                (session_id, violator_key, victim_key, attempt_index, purpose, value)
            )
            return value

        advancing = patch.object(
            defeat_aftermath_module,
            "_advance_attempt_clock",
            side_effect=[None, RuntimeError("injected")],
        )
        with (
            patch.object(
                defeat_aftermath_module, "derived_roll", side_effect=recording_roll
            ),
            advancing,
            self.assertRaises(RuntimeError),
        ):
            self._defeat()
        # The aborted run consumed both cap attempts' rolls: attempt 1's
        # deltas and entry were already applied when its advance failed.
        first_run_calls = list(calls)
        self.assertEqual(len(first_run_calls), 2)
        # Every write is absent: sexual state, counters, floor, session.
        self.assertEqual(self.player.sexual.pleasure.value, player_pleasure_before)
        self.assertEqual(self.monster.sexual.pleasure.value, monster_pleasure_before)
        self.assertEqual(self.player.sexual.hostile_act_count, 0)
        self.assertEqual(self.monster.sexual.hostile_act_count, 0)
        self.assertIsNotNone(self.player.db.active_combat)
        # The retry re-derives the identical roll for the same durable state
        # and completes the whole sequence exactly once.
        with patch.object(
            defeat_aftermath_module, "derived_roll", side_effect=recording_roll
        ):
            # The durable session is still active after the rollback, so the
            # retry is a bare re-settlement (no re-engage, no extra round).
            result = forfeit(self.player)
        self.assertEqual(calls[len(first_run_calls):], first_run_calls)
        self.assertEqual(_kinds(_aftermath_entries(result)).count("violation_act"), 2)
        self.assertEqual(self.player.sexual.hostile_act_count, 2)
        self.assertEqual(self.monster.sexual.hostile_act_count, 2)
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertEqual(self.clock.tick, 6 + 2 * 120 + 8)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::sequence-dice-are-state-derived-pure-values",
        "defeat-aftermath-violation-sequence::violation-attempts-select-victims-from-the-target-pool",
    )
    def test_rolled_back_mixed_pool_rederives_the_identical_selection(self):
        companion = self._companion("replayed companion")
        self._equalize_scores(companion)
        self._arouse(13)
        # The monster towers over both victims: every contest lands through
        # the shipped formula, so the real state-derived target draws and
        # resist rolls both execute.
        self.monster.traits.agility.base = 500
        self.monster.traits.atk_phys.base = 500
        engage(self.player, self.monster)
        self._knock_out(companion)
        real_roll = defeat_aftermath_module.derived_roll
        calls = []

        def recording_roll(*args):
            value = real_roll(*args)
            calls.append((*args, value))
            return value

        advancing = patch.object(
            defeat_aftermath_module,
            "_advance_attempt_clock",
            side_effect=[None, RuntimeError("injected")],
        )
        with (
            patch.object(
                defeat_aftermath_module, "derived_roll", side_effect=recording_roll
            ),
            advancing,
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        first_run_calls = list(calls)
        # Each executed attempt consumed exactly one target draw and one
        # resist roll; the first advance succeeded, the second failed.
        self.assertEqual(len(first_run_calls), 4)
        self.assertEqual(
            [call[4] for call in first_run_calls],
            ["target", "resist", "target", "resist"],
        )
        # The retry re-derives the identical draws (same victims, same
        # contests) for the same durable state and completes exactly once.
        with patch.object(
            defeat_aftermath_module, "derived_roll", side_effect=recording_roll
        ):
            result = forfeit(self.player)
        self.assertEqual(calls[len(first_run_calls):], first_run_calls)
        acts = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "violation_act"
        ]
        self.assertEqual(len(acts), 2)
        # Per-victim consistency: each body's counters equal the acts that
        # targeted it; the violator credited once per attempt overall.
        for victim in (self.player, companion):
            targeted = sum(
                1 for entry in acts if entry.target == str(victim.key)
            )
            self.assertEqual(victim.sexual.hostile_act_count, targeted)
        self.assertEqual(self.monster.sexual.hostile_act_count, 2)
