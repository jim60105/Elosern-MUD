"""Slice of ``test_defeat_aftermath_core``: RenderingTests, RulebookLoaderTests."""
import math
import unittest
from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
import world.rules.defeat_aftermath as defeat_aftermath_module
import world.rules.defeat_aftermath.violation as defeat_aftermath_violation_module
from world.rules import combat_session as combat_session_module
from world.rules import clock as clock_module
from world.rules import guild_config as guild_config_module
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.components import Merchant
from typeclasses.rooms import InstanceRoom, Room
from world.quests.bootstrap import sync_quest_runtime
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)
from world.rules.caravan_arrivals import register_caravan_arrivals
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
)
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.tests._fixtures import (
    RegistryIsolationMixin,
    accept,
    defeat,
    quest,
    register,
)
from world.rules.affinity import apply_affinity_change
from world.rules.buffs import entity_active_buffs, tick_buffs
from world.rules.clock import MAX_ADVANCE_SECONDS, AdvanceSource, WorldClock
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    forfeit,
    restore_active_session,
    submit_player_action,
)
from world.rules.defeat_aftermath import (
    DEFEAT_AFTERMATH_RULEBOOK,
    solve_recovery_seconds,
    load_defeat_aftermath_sections,
    register_violation_hook,
)
from world.rules.event_log import render_plain_text
from world.rules.movement import charge_movement
from world.rules.player_messages import terminal_outcome_message
from world.rules.skip_safety import SkipRejectReason, evaluate_skip_safety
from world.rules.time_skip import advance_skip, seconds_to_full_regen
from world.rules.surfaces import read_counter_trait, write_counter_trait
from tools.spec_traceability import covers_requirement
from world.rules.tests._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    open_synthetic_scope,
)
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS

from ._support import (
    DefeatAftermathBase,
)


class RenderingTests(DefeatAftermathBase):
    """EventLog kinds, zh-tw lines, and the observability boundary event."""

    @covers_requirement(
        "defeat-aftermath-core::defeat-aftermath-emits-eventlog-entries-and-defeat-lines"
    )
    def test_aftermath_event_log_kinds_appear_in_order(self):
        result = self._defeat_by_forfeit()
        aftermath = [
            log for log in result["logs"] if log.skill_key == "defeat_aftermath"
        ]
        self.assertEqual(len(aftermath), 1)
        kinds = [entry.kind for entry in aftermath[0].entries]
        self.assertEqual(
            kinds, ["defeat_settle", "weak_granted", "recovery_advance"]
        )
        rendered = render_plain_text(aftermath[0])
        self.assertIn(DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0], rendered)
        self.assertIn("虛弱感籠罩全身", rendered)
        self.assertIn("你昏迷了 8 秒", rendered)

    @covers_requirement(
        "defeat-aftermath-core::defeat-aftermath-emits-eventlog-entries-and-defeat-lines"
    )
    def test_bare_defeat_line_is_replaced(self):
        self.assertNotEqual(terminal_outcome_message("defeat"), "你被擊敗了。")
        self.assertIn("你被擊敗了", terminal_outcome_message("defeat"))

    @covers_requirement(
        "defeat-aftermath-core::defeat-aftermath-emits-eventlog-entries-and-defeat-lines"
    )
    def test_committed_defeat_emits_one_boundary_event(self):
        with (
            patch("world.rules.defeat_aftermath.aftermath.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self._defeat_by_forfeit()
        calls = [
            call for call in info.call_args_list if call.args and call.args[0] == "defeat_aftermath"
        ]
        self.assertEqual(len(calls), 1)
        (_, kwargs), = calls
        self.assertEqual(kwargs["context"]["char"], str(self.player.key))
        self.assertEqual(kwargs["context"]["room"], str(self.room.pk))
        self.assertEqual(kwargs["context"]["hp_after"], 5)
        self.assertEqual(kwargs["context"]["seconds"], 8)
        self.assertEqual(kwargs["context"]["hp_wake"], 5)
        self.assertIn("tick", kwargs["context"])

    @covers_requirement(
        "defeat-aftermath-core::defeat-aftermath-emits-eventlog-entries-and-defeat-lines"
    )
    def test_rolled_back_defeat_emits_no_boundary_event(self):
        engage(self.player, self.monster)
        with (
            patch("world.rules.defeat_aftermath.aftermath.log_info") as info,
            patch("world.rules.combat_session.settlement._persist", side_effect=RuntimeError("injected")),
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(RuntimeError):
                forfeit(self.player)
        self.assertEqual(
            [call for call in info.call_args_list if call.args and call.args[0] == "defeat_aftermath"],
            [],
        )


class RulebookLoaderTests(DefeatAftermathBase):
    """The per-section loader (D-C8): owned sections fail closed, foreign ignored."""

    # The DA4-owned violation section in its minimal valid shape: every
    # loader fixture below carries it so a section-specific malformation is
    # the only reason a load can fail.
    VIOLATION_SECTION = (
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
    # The DA6-owned digest section: every owned section must be present and
    # valid for a section-specific malformation to stay the only failure.
    DIGEST_SECTION = (
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

    def _load(self, text):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(text)
            path = handle.name
        self.addCleanup(__import__("os").unlink, path)
        from pathlib import Path

        return load_defeat_aftermath_sections(Path(path))

    @covers_requirement(
        "defeat-aftermath-recovery::the-recovery-rulebook-section-is-validated-by-its-own-loader"
    )
    def test_shipped_rulebook_loads_with_owned_sections(self):
        self.assertTrue(DEFEAT_AFTERMATH_RULEBOOK.pg_lines)
        self.assertEqual(DEFEAT_AFTERMATH_RULEBOOK.weak_debuff_buff_key, "defeat_weak")
        self.assertEqual(DEFEAT_AFTERMATH_RULEBOOK.recovery.regen_scale, 0.5)
        self.assertEqual(DEFEAT_AFTERMATH_RULEBOOK.recovery.max_recovery_seconds, 21600)
        self.assertEqual(DEFEAT_AFTERMATH_RULEBOOK.recovery.wake_fraction, 0.05)
        # The DA4-owned violation section ships validated rows keyed by lore
        # species names and the violated wake line.
        self.assertTrue(DEFEAT_AFTERMATH_RULEBOOK.violation.rows)
        self.assertTrue(DEFEAT_AFTERMATH_RULEBOOK.violation.violated_wake_line)
        self.assertIn("哥布林", DEFEAT_AFTERMATH_RULEBOOK.violation.rows)

    def test_unknown_section_is_ignored_with_one_warning(self):
        with patch("world.rules.defeat_aftermath.rulebook.log_warn") as warn:
            rulebook = self._load(
                "pg_lines:\n  - '你醒了。'\nweak_debuff:\n  buff_key: defeat_weak\n"
                "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 21600\n"
                "  wake_fraction: 0.05\nviolation_families: []\ndigest_table: {}\n"
                + self.VIOLATION_SECTION
                + self.DIGEST_SECTION
            )
        self.assertEqual(warn.call_count, 1)
        self.assertIn("violation_families", warn.call_args.kwargs["context"]["sections"])
        self.assertIn("digest_table", warn.call_args.kwargs["context"]["sections"])
        self.assertEqual(rulebook.pg_lines, ("你醒了。",))

    def test_malformed_owned_section_fails_load(self):
        recovery = (
            "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 21600\n"
            "  wake_fraction: 0.05\n"
        )
        with self.assertRaises(ValueError):
            self._load(
                "pg_lines: []\nweak_debuff:\n  buff_key: defeat_weak\n"
                + recovery
                + self.VIOLATION_SECTION
                + self.DIGEST_SECTION
            )
        with self.assertRaises(ValueError):
            self._load(
                "pg_lines:\n  - '你醒了。'\nweak_debuff:\n  buff_key: no_such_buff\n"
                + recovery
                + self.VIOLATION_SECTION
                + self.DIGEST_SECTION
            )
        with self.assertRaises(ValueError):
            self._load(
                "pg_lines:\n  - '你醒了。'\n"
                + recovery
                + self.VIOLATION_SECTION
                + self.DIGEST_SECTION
            )

    @covers_requirement(
        "defeat-aftermath-recovery::the-recovery-rulebook-section-is-validated-by-its-own-loader"
    )
    def test_malformed_recovery_section_fails_load(self):
        header = (
            "pg_lines:\n  - '你醒了。'\nweak_debuff:\n  buff_key: defeat_weak\n"
            + self.VIOLATION_SECTION
            + self.DIGEST_SECTION
        )
        for body in (
            # Missing section entirely: recovery is owned, absence fails closed.
            "weak_debuff:\n  buff_key: defeat_weak\n",
            "recovery: {}\n",
            "recovery:\n  regen_scale: 0\n  max_recovery_seconds: 21600\n  wake_fraction: 0.05\n",
            "recovery:\n  regen_scale: -0.5\n  max_recovery_seconds: 21600\n  wake_fraction: 0.05\n",
            "recovery:\n  regen_scale: 1.5\n  max_recovery_seconds: 21600\n  wake_fraction: 0.05\n",
            "recovery:\n  regen_scale: true\n  max_recovery_seconds: 21600\n  wake_fraction: 0.05\n",
            "recovery:\n  regen_scale: .nan\n  max_recovery_seconds: 21600\n  wake_fraction: 0.05\n",
            "recovery:\n  regen_scale: 0.5\n  wake_fraction: 0.05\n",
            "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 0\n  wake_fraction: 0.05\n",
            "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 999999\n  wake_fraction: 0.05\n",
            "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 21600\n  wake_fraction: 1.0\n",
            "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 21600\n  wake_fraction: .inf\n",
        ):
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    self._load(header + body)
