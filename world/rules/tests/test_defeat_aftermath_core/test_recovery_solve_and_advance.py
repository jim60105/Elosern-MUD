"""Slice of ``test_defeat_aftermath_core``: RecoveryAdvanceTests, RecoverySolveTests."""
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


class RecoverySolveTests(unittest.TestCase):
    """The pure scaled-regen solve (task 2.1, D-R1/D-R2)."""

    def test_matches_brute_force_minimum_and_cap_classification(self):
        for current in (0, 1, 3, 7):
            for carried in (0.0, 0.25, 0.5, 0.9):
                for rate in (0.0, 0.3, 1.0, 1.3, 2.0):
                    for scale in (0.5, 1.0):
                        for target in (1, 4, 5, 9):
                            with self.subTest(
                                current=current,
                                carried=carried,
                                rate=rate,
                                scale=scale,
                                target=target,
                            ):
                                seconds, capped = solve_recovery_seconds(
                                    current, carried, rate, scale, target, 6
                                )
                                scaled = rate * scale

                                def model(offset):
                                    return math.floor(
                                        current + carried + scaled * offset
                                    )

                                if current + carried >= target:
                                    self.assertEqual((seconds, capped), (0, False))
                                    continue
                                if scaled <= 0:
                                    self.assertTrue(capped)
                                    self.assertEqual(seconds, 6)
                                    continue
                                reachable = any(
                                    model(offset) >= target for offset in range(0, 7)
                                )
                                self.assertEqual(capped, not reachable)
                                if reachable:
                                    minimum = next(
                                        offset
                                        for offset in range(0, 7)
                                        if model(offset) >= target
                                    )
                                    self.assertEqual(seconds, minimum)
                                    self.assertTrue(model(seconds) >= target)
                                    if seconds > 0:
                                        self.assertTrue(model(seconds - 1) < target)
                                else:
                                    self.assertEqual(seconds, 6)

    def test_cap_bound_exact_solution_is_not_capped(self):
        self.assertEqual(solve_recovery_seconds(1, 0.0, 1.0, 0.5, 5, 8), (8, False))

    def test_float_boundary_at_the_cap_reports_capped(self):
        # The closed form proposes exactly the cap, but the float model misses
        # the target there: floor(1 + 8 * 0.4999999999999999) = 4 < 5, while
        # ceil(4 / 0.4999999999999999) rounds past the cap (duck finding 2).
        self.assertEqual(
            solve_recovery_seconds(1, 0.0, 1.0, 0.4999999999999999, 5, 8), (8, True)
        )

    def test_zero_and_negative_scaled_rates_are_capped(self):
        self.assertEqual(solve_recovery_seconds(1, 0.0, 0.0, 0.5, 5, 9), (9, True))
        self.assertEqual(solve_recovery_seconds(1, 0.0, 1.0, 0.0, 5, 9), (9, True))

    def test_already_above_target_is_inert(self):
        self.assertEqual(solve_recovery_seconds(5, 0.0, 1.0, 0.5, 5, 9), (0, False))
        # A carried sub-unit fraction is not yet credited HP: current 4 with
        # 0.9 carried still needs one second to floor past the target.
        self.assertEqual(solve_recovery_seconds(4, 0.9, 1.0, 0.5, 5, 9), (1, False))


class RecoveryAdvanceTests(DefeatAftermathBase):
    """Exact-target wake, overshoot clamp, inert path, and the capped edge."""

    def _spied_defeat(self):
        real = self.clock.advance
        calls = []

        def spy(seconds, source, entities):
            calls.append((seconds, source))
            return real(seconds, source, entities)

        with patch.object(self.clock, "advance", side_effect=spy):
            result = self._defeat_by_forfeit()
        return result, calls

    def _aftermath_entries(self, result):
        return [
            entry
            for log in result["logs"]
            if log.skill_key == "defeat_aftermath"
            for entry in log.entries
        ]

    @covers_requirement(
        "defeat-aftermath-recovery::defeat-recovery-advances-the-clock-to-the-5-wake-target"
    )
    def test_wakes_at_exactly_five_percent_with_the_new_source(self):
        before = self.clock.tick
        result, calls = self._spied_defeat()
        self.assertEqual(
            calls,
            [
                (6, AdvanceSource.COMBAT),
                (8, AdvanceSource.DEFEAT_AFTERMATH),
            ],
        )
        self.assertEqual(self.clock.tick, before + 14)
        self.assertEqual(self.player.traits.hp.current, 5)
        recovery = [
            entry for entry in self._aftermath_entries(result)
            if entry.kind == "recovery_advance"
        ]
        self.assertEqual(len(recovery), 1)
        self.assertEqual(recovery[0].data, {"seconds": 8, "hp_wake": 5})

    @covers_requirement(
        "defeat-aftermath-recovery::defeat-recovery-advances-the-clock-to-the-5-wake-target"
    )
    def test_coarse_rate_overshoot_clamps_to_the_target(self):
        # Virtual scaled rate 0.65/s: t = ceil(4 / 0.65) = 7; the real 1.3/s
        # advance lands floor(1 + 9.1) = 10, and the clamp pins HP to 5.
        self.player.traits.hp.rate = 1.3
        result, calls = self._spied_defeat()
        self.assertEqual(calls[1], (7, AdvanceSource.DEFEAT_AFTERMATH))
        self.assertEqual(self.player.traits.hp.current, 5)

    @covers_requirement(
        "defeat-aftermath-recovery::defeat-recovery-advances-the-clock-to-the-5-wake-target"
    )
    def test_already_at_target_settles_inertly(self):
        # max 20 -> target ceil(1) = 1 == the floored HP: no advance, no
        # clamp, no recovery entry (delta requirement 1, inert scenario).
        self.player.traits.hp.base = 20
        self.player.traits.hp.current = 20
        before = self.clock.tick
        result, calls = self._spied_defeat()
        self.assertEqual(calls, [(6, AdvanceSource.COMBAT)])
        self.assertEqual(self.clock.tick, before + 6)
        self.assertEqual(self.player.traits.hp.current, 1)
        self.assertNotIn(
            "recovery_advance",
            [entry.kind for entry in self._aftermath_entries(result)],
        )

    @covers_requirement(
        "defeat-aftermath-recovery::unreachable-recovery-is-capped-and-reported-never-truncated-silently"
    )
    def test_zero_rate_hits_the_cap_with_one_error_event(self):
        self.player.traits.hp.rate = 0
        with patch("world.rules.defeat_aftermath.aftermath.log_error") as error:
            result, calls = self._spied_defeat()
        self.assertEqual(calls[1], (21600, AdvanceSource.DEFEAT_AFTERMATH))
        # The capped virtual model produced no regen: HP rests at 1, below
        # the target, and never clamps upward (delta requirement 2).
        self.assertEqual(self.player.traits.hp.current, 1)
        self.assertEqual(error.call_count, 1)
        context = error.call_args.kwargs["context"]
        self.assertEqual(context["target"], 5)
        self.assertTrue(context["capped"])
        self.assertIn("tick", context)
        self.assertIn("char", context)
        self.assertEqual(
            [entry.kind for entry in self._aftermath_entries(result)],
            ["defeat_settle", "weak_granted", "recovery_advance"],
        )

    @covers_requirement(
        "defeat-aftermath-recovery::unreachable-recovery-is-capped-and-reported-never-truncated-silently"
    )
    def test_positive_rate_cap_writes_the_virtual_model_state(self):
        # Virtual scaled rate 0.00005/s over the 21600s cap: the virtual
        # model lands at floor(1 + 1.08) = 2 with a .08 carried remainder,
        # while the real un-scaled advance lands at 3 with .16 — the
        # aftermath must settle the stored gauge at the virtual state,
        # remainder included (final duck finding 1).
        self.player.traits.hp.rate = 0.0001
        with patch("world.rules.defeat_aftermath.aftermath.log_error") as error:
            result, calls = self._spied_defeat()
        self.assertEqual(calls[1], (21600, AdvanceSource.DEFEAT_AFTERMATH))
        self.assertEqual(self.player.traits.hp.current, 2)
        self.assertAlmostEqual(self.player.traits.hp.regen_remainder, 0.08, places=6)
        self.assertEqual(error.call_count, 1)
        self.assertEqual(error.call_args.kwargs["context"]["target"], 5)
