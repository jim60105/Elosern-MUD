"""Slice of ``test_defeat_aftermath_core``: ViolationHookGuardTests, WeakDebuffRulebookTests."""
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


class WeakDebuffRulebookTests(DefeatAftermathBase):
    """The ``defeat_weak`` settle-time mount and ordinary decay (D-C2)."""

    @covers_requirement(
        "defeat-aftermath-core::defeat-weak-debuff-is-mounted-at-settle-time",
        "defeat-aftermath-core::hostile-defeat-floors-player-hp-at-1-and-marks-the-player-knocked-out",
    )
    def test_defeat_mounts_weak_debuff_and_it_expires_ordinarily(self):
        self._defeat_by_forfeit()
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        # The floor writes HP 1; the recovery advance then wakes the player
        # at exactly ceil(100 * 0.05) = 5 (defeat-aftermath-recovery).
        self.assertEqual(self.player.traits.hp.current, 5)
        # The recovery window already consumed 8 of the buff's 300 seconds.
        tick_buffs(self.player, 291)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        tick_buffs(self.player, 1)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))


class ViolationHookGuardTests(DefeatAftermathBase):
    """The ``DEFEAT_ADULT_SCENES`` guard around the violation hook (D-C4)."""

    def setUp(self):
        super().setUp()
        # DA4 registers the violation engine at import; save and restore that
        # exact body so these guard tests can install their own probes without
        # leaking hook state into other suites in the same process.
        saved_hook = defeat_aftermath_violation_module._VIOLATION_HOOK
        self.addCleanup(
            setattr,
            defeat_aftermath_violation_module,
            "_VIOLATION_HOOK",
            saved_hook,
        )
        defeat_aftermath_violation_module._VIOLATION_HOOK = None

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-adult-scenes-setting-exists-and-guards-the-violation-hook"
    )
    def test_flag_on_calls_the_registered_hook_body(self):
        calls = []
        register_violation_hook(lambda context: calls.append(context))
        self._defeat_by_forfeit()
        self.assertEqual(len(calls), 1)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-adult-scenes-setting-exists-and-guards-the-violation-hook"
    )
    @override_settings(DEFEAT_ADULT_SCENES=False)
    def test_flag_off_never_calls_the_hook_and_settles_the_core_path(self):
        calls = []
        register_violation_hook(lambda context: calls.append(context))
        result = self._defeat_by_forfeit()
        self.assertEqual(calls, [])
        # Core-only losses are unchanged with the flag off; the recovery
        # phase is core settlement math and still wakes at the target.
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(result["outcome"], "defeat")

    def test_duplicate_or_invalid_registrations_fail_loudly(self):
        def hook(context):
            return None

        register_violation_hook(hook)
        with self.assertRaises(RuntimeError):
            register_violation_hook(lambda battlefield, session: None)
        register_violation_hook(hook)  # identical re-registration is idempotent
        with self.assertRaises(ValueError):
            register_violation_hook("not callable")
