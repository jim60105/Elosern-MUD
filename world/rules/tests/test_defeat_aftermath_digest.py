"""Defeat digest phase tests (defeat-aftermath-digest-narrative).

Covers the DA6 delta: the closed-vocabulary ``digest`` rulebook section and
its fail-closed loader, the terminal-state first-match digest fed by the
in-memory outcome handoff, shipped-surface buff mounting with conscious
bystanders staying lighter, digest-selected zh-tw wake-line families, and
the Narrator overlay's state-untouched render over the aftermath entries.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase

import world.rules.defeat_aftermath as defeat_aftermath_module
from world.rules import combat_session as combat_session_module
from world.rules.buffs import entity_active_buffs
from world.rules.combat_session import engage, forfeit
from world.rules.defeat_aftermath import (
    DEFEAT_AFTERMATH_RULEBOOK,
    _DIGEST_CONDITION_KEYS,
    load_defeat_aftermath_sections,
)
from world.rules.event_log import render_plain_text
from world.rules.player_messages import DEFEAT_AFTERMATH_TEMPLATES
from tools.spec_traceability import covers_requirement
from world.ai.narrator import render_aftermath

from .test_defeat_aftermath_violation import (
    ViolationBase,
    _aftermath_entries,
    _aftermath_logs,
    _kinds,
)

# The shipped digest table in its minimal valid shape: two conditioned rows
# and the trailing empty-when fallback. Loader fixtures below mutate this
# text so a single malformation is the only reason a load can fail.
_DIGEST_SECTION = (
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

# Every owned section except ``digest``: the loader validates all of them,
# so a digest-section fixture must carry the rest in valid shapes.
_OTHER_SECTIONS = (
    "pg_lines:\n  - '你醒了。'\n"
    "weak_debuff:\n  buff_key: defeat_weak\n"
    "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 21600\n"
    "  wake_fraction: 0.05\n"
    "violation:\n"
    "  violated_wake_line: '測試喚醒。'\n"
    "  archetypes:\n"
    "    哥布林:\n"
    "      victory_pleasure_delta: 2\n"
    "      threshold_ordinal: 1\n"
    "      attempt_cap: 2\n"
    "      attempt_duration_seconds: 120\n"
    "      landed_deltas: {victim_pleasure: 16, aggressor_pleasure: 10}\n"
    "      resisted_deltas: {victim_pleasure: 4, aggressor_pleasure: 3}\n"
    "      credited_counters: [hostile_act_count, interspecies_act_count]\n"
)


def _digest_section(rows_text: str) -> str:
    return "digest:\n  rows:\n" + rows_text


class DigestLoaderTests(unittest.TestCase):
    """The ``digest`` section's fail-closed loader validation (D-D2)."""

    def _load(self, text: str):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(text)
            path = handle.name
        self.addCleanup(os.unlink, path)
        from pathlib import Path

        return load_defeat_aftermath_sections(Path(path))

    def _load_digest(self, rows_text: str):
        return self._load(_OTHER_SECTIONS + _digest_section(rows_text))

    @covers_requirement(
        "defeat-aftermath-digest::each-violated-entity-digests-its-own-body-s-recorded-state",
    )
    def test_shipped_digest_rows_load_with_the_fallback_last(self):
        rulebook = DEFEAT_AFTERMATH_RULEBOOK
        rows = rulebook.digest.rows
        self.assertEqual([row.id for row in rows], ["residue", "humiliated", "none"])
        self.assertEqual(rows[0].outcome, "residue")
        self.assertEqual(rows[0].buff, "aftermath_residue")
        self.assertEqual(rows[1].outcome, "humiliated")
        self.assertEqual(rows[1].buff, "aftermath_humiliated")
        self.assertIsNone(rows[-1].buff)
        self.assertEqual(dict(rows[-1].when), {})

    def test_species_condition_key_fails_closed(self):
        for key in ("species", "race", "persona"):
            with self.subTest(key=key):
                rows_text = (
                    "    - id: residue\n"
                    f"      when:\n        {key}: 史萊姆\n"
                    "      outcome: residue\n"
                    "      buff: aftermath_residue\n"
                    "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
                )
                with self.assertRaises(ValueError):
                    self._load_digest(rows_text)

    def test_unknown_condition_key_fails_closed(self):
        rows_text = (
            "    - id: none\n      when: {no_such_field: 1}\n      outcome: none\n      buff: null\n"
            "    - id: fallback\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_unknown_sensitivity_label_fails_closed(self):
        rows_text = (
            "    - id: residue\n"
            "      when:\n        sensitivity_level: [不可思議]\n"
            "      outcome: residue\n      buff: aftermath_residue\n"
            "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_unknown_shame_label_fails_closed(self):
        rows_text = (
            "    - id: humiliated\n"
            "      when:\n        shame_level: [暴怒]\n"
            "      outcome: humiliated\n      buff: aftermath_humiliated\n"
            "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_non_bool_zero_landed_fails_closed(self):
        rows_text = (
            "    - id: humiliated\n"
            "      when:\n        outcome.zero_landed: 'true'\n"
            "      outcome: humiliated\n      buff: aftermath_humiliated\n"
            "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_climax_range_min_above_max_fails_closed(self):
        rows_text = (
            "    - id: residue\n"
            "      when:\n        outcome.climax_count: {min: 5, max: 1}\n"
            "      outcome: residue\n      buff: aftermath_residue\n"
            "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_arousal_ordinal_out_of_vocabulary_fails_closed(self):
        rows_text = (
            "    - id: residue\n"
            "      when:\n        arousal_ordinal: {min: 9}\n"
            "      outcome: residue\n      buff: aftermath_residue\n"
            "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_none_row_with_buff_fails_closed(self):
        rows_text = (
            "    - id: none\n      when: {}\n      outcome: none\n      buff: aftermath_residue\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_conditioned_row_without_buff_fails_closed(self):
        rows_text = (
            "    - id: residue\n"
            "      when:\n        outcome.climax_count: {min: 1}\n"
            "      outcome: residue\n"
            "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_unknown_buff_key_fails_closed(self):
        rows_text = (
            "    - id: residue\n"
            "      when:\n        outcome.climax_count: {min: 1}\n"
            "      outcome: residue\n      buff: no_such_buff\n"
            "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_non_marker_buff_fails_closed(self):
        # A known rulebook buff that is not a bounds-only world-second
        # marker can never ride the digest table: dark_corrosion carries a
        # rate modifier, focus carries no modifiers at all.
        for buff in ("dark_corrosion", "focus"):
            rows_text = (
                "    - id: residue\n"
                "      when:\n        outcome.climax_count: {min: 1}\n"
                f"      outcome: residue\n      buff: {buff}\n"
                "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
            )
            with self.subTest(buff=buff):
                with self.assertRaises(ValueError):
                    self._load_digest(rows_text)

    def test_unknown_outcome_fails_closed(self):
        rows_text = (
            "    - id: weird\n      when: {}\n      outcome: enchanted\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_last_row_must_be_the_empty_when_fallback(self):
        rows_text = (
            "    - id: none\n      when: {}\n      outcome: none\n      buff: null\n"
            "    - id: residue\n"
            "      when:\n        outcome.climax_count: {min: 1}\n"
            "      outcome: residue\n      buff: aftermath_residue\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_duplicate_row_id_fails_closed(self):
        rows_text = (
            "    - id: residue\n"
            "      when:\n        outcome.climax_count: {min: 1}\n"
            "      outcome: residue\n      buff: aftermath_residue\n"
            "    - id: residue\n      when: {}\n      outcome: none\n      buff: null\n"
        )
        with self.assertRaises(ValueError):
            self._load_digest(rows_text)

    def test_shipped_rows_stay_inside_the_closed_vocabulary(self):
        for row in DEFEAT_AFTERMATH_RULEBOOK.digest.rows:
            self.assertLessEqual(set(row.when), set(_DIGEST_CONDITION_KEYS))


class DigestPhaseTests(ViolationBase, EvenniaTestCase):
    """The digest phase over a full defeat settlement (D-D1/D-D6/D-D7)."""

    def _defeat_capturing(self, target_rolls, resist_rolls):
        """Settle one defeat, capturing the writer's digest outputs."""
        captured = {}
        real_writer = defeat_aftermath_module.run_defeat_aftermath

        def spy(actor, record, battlefield):
            outcome = real_writer(actor, record, battlefield)
            captured["outcomes"] = outcome.violation
            captured["digests"] = outcome.digests
            captured["observations"] = outcome.wake_observations
            return outcome

        with (
            self._patch_purpose_rolls(target_rolls, resist_rolls),
            patch.object(
                defeat_aftermath_module, "run_defeat_aftermath", side_effect=spy
            ),
        ):
            result = forfeit(self.player)
        return result, captured

    @staticmethod
    def _digest_rows(captured):
        return [
            (row.participant, row.digest, row.buff) for row in captured["digests"]
        ]

    @covers_requirement(
        "defeat-aftermath-digest::each-violated-entity-digests-its-own-body-s-recorded-state",
        "defeat-aftermath-digest::digest-outcomes-mount-shipped-surface-buffs-on-violated-entities-and-bystanders-stay-lighter",
    )
    def test_high_sensitivity_with_climax_digests_residue_and_mounts_its_buff(self):
        companion = self._companion("residue companion")
        self._equalize_scores(companion)
        self._arouse(13)
        companion.sexual.sensitivity["私處"].value = "高"
        companion.sexual.climax_phase.value = "接近"
        engage(self.player, self.monster)
        self._knock_out(companion)
        result, captured = self._defeat_capturing([1, 1], [1, 1])
        self.assertEqual(
            self._digest_rows(captured),
            [(str(companion.key), "residue", "aftermath_residue")],
        )
        self.assertIn("aftermath_residue", entity_active_buffs(companion))
        wakes = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "companion_wake"
        ]
        self.assertEqual(
            wakes[0].text_template,
            DEFEAT_AFTERMATH_TEMPLATES["wake_companion_residue"],
        )
        records = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "digest_outcome"
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0].data, {"digest": "residue", "buff": "aftermath_residue"}
        )

    @covers_requirement(
        "defeat-aftermath-digest::each-violated-entity-digests-its-own-body-s-recorded-state",
        "defeat-aftermath-digest::digest-outcomes-mount-shipped-surface-buffs-on-violated-entities-and-bystanders-stay-lighter",
    )
    def test_low_sensitivity_high_shame_zero_landed_digests_humiliated(self):
        companion = self._companion("humiliated companion")
        self._equalize_scores(companion)
        self._arouse(13)
        companion.sexual.shame.value = "強烈"
        engage(self.player, self.monster)
        self._knock_out(companion)
        result, captured = self._defeat_capturing([1, 1], [100, 100])
        self.assertTrue(
            all(outcome.zero_landed for outcome in captured["outcomes"].values())
        )
        self.assertEqual(
            self._digest_rows(captured),
            [(str(companion.key), "humiliated", "aftermath_humiliated")],
        )
        self.assertIn("aftermath_humiliated", entity_active_buffs(companion))
        wakes = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "companion_wake"
        ]
        self.assertEqual(
            wakes[0].text_template,
            DEFEAT_AFTERMATH_TEMPLATES["wake_companion_humiliated"],
        )

    @covers_requirement(
        "defeat-aftermath-digest::each-violated-entity-digests-its-own-body-s-recorded-state",
    )
    def test_mid_band_digest_stays_none_and_keeps_the_fixed_wake_line(self):
        companion = self._companion("steady companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        result, captured = self._defeat_capturing([1, 1], [1, 1])
        self.assertEqual(
            self._digest_rows(captured),
            [(str(companion.key), "none", None)],
        )
        self.assertNotIn("aftermath_residue", entity_active_buffs(companion))
        self.assertNotIn("aftermath_humiliated", entity_active_buffs(companion))
        wakes = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "companion_wake"
        ]
        self.assertEqual(
            wakes[0].text_template, DEFEAT_AFTERMATH_TEMPLATES["companion_wake"]
        )

    @covers_requirement(
        "defeat-aftermath-digest::each-violated-entity-digests-its-own-body-s-recorded-state",
    )
    def test_pinned_shame_body_never_reaches_the_humiliated_band(self):
        # A shame-pinned body with the residue band's inputs digests residue;
        # the same pinned body on the humiliated row's sensitivity band with
        # a zero-landed sequence still falls through to none — the shame
        # band [強烈, 成癮] can never match 無, established without the
        # rulebook reading species.
        for setup, expected in (
            (("sensitive", "climax"), ("residue", "aftermath_residue")),
            (("plain", "zero_landed"), ("none", None)),
        ):
            with self.subTest(setup=setup):
                companion = self._companion(f"pinned {setup[0]} companion")
                self._equalize_scores(companion)
                self._arouse(13)
                companion.sexual.clamp_shame_to("無")
                if setup == ("sensitive", "climax"):
                    companion.sexual.sensitivity["私處"].value = "敏感異常"
                    companion.sexual.climax_phase.value = "接近"
                engage(self.player, self.monster)
                self._knock_out(companion)
                if setup == ("sensitive", "climax"):
                    result, captured = self._defeat_capturing([1, 1], [1, 1])
                else:
                    result, captured = self._defeat_capturing([1, 1], [100, 100])
                self.assertEqual(
                    self._digest_rows(captured),
                    [(str(companion.key), expected[0], expected[1])],
                )

    @covers_requirement(
        "defeat-aftermath-digest::wake-up-lines-are-digest-selected-with-persona-as-flavor-only",
        "defeat-aftermath-digest::digest-outcomes-mount-shipped-surface-buffs-on-violated-entities-and-bystanders-stay-lighter",
    )
    def test_conscious_bystander_receives_observation_only(self):
        victim = self._companion("selected victim")
        witness = self._companion("standing witness")
        self._equalize_scores(victim, witness)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(victim)
        result, captured = self._defeat_capturing([1, 1], [1, 1])
        self.assertEqual(set(captured["outcomes"]), {str(victim.key)})
        self.assertEqual(
            [row.participant for row in captured["observations"]],
            [str(witness.key)],
        )
        self.assertNotIn(
            str(witness.key), [row.participant for row in captured["digests"]]
        )
        observations = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "wake_observation"
        ]
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].actor, str(witness.key))
        self.assertIn(
            str(witness.key),
            observations[0].text_template.format(
                actor=witness.key, target=None, data={}
            ),
        )
        self.assertNotIn("aftermath_residue", entity_active_buffs(witness))
        self.assertNotIn("aftermath_humiliated", entity_active_buffs(witness))

    @covers_requirement(
        "defeat-aftermath-digest::wake-up-lines-are-digest-selected-with-persona-as-flavor-only",
        "defeat-aftermath-digest::digest-outcomes-mount-shipped-surface-buffs-on-violated-entities-and-bystanders-stay-lighter",
    )
    def test_offline_wake_lines_differ_by_digest_only(self):
        # First fixture: a zero-landed sequence against a low-sensitivity,
        # high-shame body digests humiliated. Second fixture: the same
        # companion digesting residue against the same offline (LLM-off)
        # render path. The wake lines come from the two different families
        # and the buff grants differ accordingly.
        companion = self._companion("twice digested companion")
        self._equalize_scores(companion)
        self._arouse(13)
        companion.sexual.shame.value = "強烈"
        engage(self.player, self.monster)
        self._knock_out(companion)
        first, first_captured = self._defeat_capturing([1, 1], [100, 100])
        humiliated_row = self._digest_rows(first_captured)[0]
        humiliated_wake = next(
            entry
            for entry in _aftermath_entries(first)
            if entry.kind == "companion_wake"
        )
        # Second settlement: a fresh winner, the same companion knocked out
        # again, now sensitive and climaxing — the residue band.
        second_monster = self._lore_monster("哥布林")
        second_monster.location = self.room
        # _arouse raises the FIRST monster's pleasure; the fresh winner is
        # aroused directly so its sequence starts.
        second_monster.sexual.pleasure.base = 13
        self._equalize_scores(companion)
        companion.sexual.sensitivity["私處"].value = "高"
        companion.sexual.climax_phase.value = "接近"
        engage(self.player, second_monster)
        self._knock_out(companion)
        second, second_captured = self._defeat_capturing([1, 1], [1, 1])
        residue_row = self._digest_rows(second_captured)[0]
        residue_wake = next(
            entry
            for entry in _aftermath_entries(second)
            if entry.kind == "companion_wake"
        )
        self.assertEqual(
            humiliated_row, (str(companion.key), "humiliated", "aftermath_humiliated")
        )
        self.assertEqual(
            residue_row, (str(companion.key), "residue", "aftermath_residue")
        )
        self.assertEqual(
            humiliated_wake.text_template,
            DEFEAT_AFTERMATH_TEMPLATES["wake_companion_humiliated"],
        )
        self.assertEqual(
            residue_wake.text_template,
            DEFEAT_AFTERMATH_TEMPLATES["wake_companion_residue"],
        )
        self.assertNotEqual(
            humiliated_wake.text_template, residue_wake.text_template
        )

    @covers_requirement(
        "defeat-aftermath-digest::wake-up-lines-are-digest-selected-with-persona-as-flavor-only",
        "defeat-aftermath-digest::digest-outcomes-mount-shipped-surface-buffs-on-violated-entities-and-bystanders-stay-lighter",
    )
    def test_player_digest_reselects_the_self_wake_line(self):
        self._equalize_scores()
        self._arouse(13)
        self.player.sexual.sensitivity["私處"].value = "高"
        self.player.sexual.climax_phase.value = "接近"
        engage(self.player, self.monster)
        result, captured = self._defeat_capturing([1], [1])
        self.assertEqual(
            self._digest_rows(captured),
            [(str(self.player.key), "residue", "aftermath_residue")],
        )
        self.assertIn("aftermath_residue", entity_active_buffs(self.player))
        settle = next(
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "defeat_settle"
        )
        self.assertEqual(
            settle.data["wake"], DEFEAT_AFTERMATH_TEMPLATES["wake_self_residue"]
        )

    @covers_requirement(
        "defeat-aftermath-digest::each-violated-entity-digests-its-own-body-s-recorded-state",
    )
    @override_settings(DEFEAT_ADULT_SCENES=False)
    def test_core_only_defeat_produces_no_digest_rows(self):
        self._equalize_scores()
        self._arouse(13)
        engage(self.player, self.monster)
        result, captured = self._defeat_capturing([1], [1])
        self.assertEqual(captured["outcomes"], {})
        self.assertEqual(captured["digests"], ())
        self.assertEqual(captured["observations"], ())
        self.assertNotIn("digest_outcome", _kinds(_aftermath_entries(result)))
        self.assertNotIn("wake_observation", _kinds(_aftermath_entries(result)))

    @covers_requirement(
        "defeat-aftermath-digest::the-narrator-overlays-aftermath-entries-and-always-degrades-to-templates",
    )
    def test_overlay_render_leaves_the_settled_state_untouched(self):
        companion = self._companion("narrated companion")
        self._equalize_scores(companion)
        self._arouse(13)
        companion.sexual.sensitivity["私處"].value = "高"
        companion.sexual.climax_phase.value = "接近"
        engage(self.player, self.monster)
        self._knock_out(companion)
        result, captured = self._defeat_capturing([1, 1], [1, 1])
        (log,) = _aftermath_logs(result)
        entries = [
            {
                "kind": entry.kind,
                "line": entry.text_template.format(
                    actor=entry.actor, target=entry.target, data=entry.data
                ),
            }
            for entry in log.entries
        ]
        pleasure_before = companion.sexual.pleasure.value
        buffs_before = entity_active_buffs(companion)
        rendered = render_aftermath(
            entries,
            lambda seq: [f"旁白段落{index}" for index in range(len(seq))],
        )
        overlay = rendered.split("\n\n")[1:]
        self.assertEqual(len(overlay), len(entries))
        self.assertEqual(
            overlay, [f"旁白段落{index}" for index in range(len(entries))]
        )
        self.assertEqual(companion.sexual.pleasure.value, pleasure_before)
        self.assertEqual(entity_active_buffs(companion), buffs_before)
        # The deterministic base render stands byte-identical before the
        # overlay paragraphs.
        self.assertTrue(
            rendered.startswith(
                render_plain_text(log)
            )
        )
