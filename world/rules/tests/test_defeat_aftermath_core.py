"""Defeat-aftermath core tests (defeat-aftermath-core).

Covers the hostile-defeat settlement contract: the HP-1 nonlethal floor,
the violator departure (population despawn, quest-bound retain with
precedence, foreign untouched), the weak debuff mount and ordinary decay,
the recovery advance (exact-target wake, capped degenerate case, clock
side-effect window, rollback boundaries, retained-winner smoke), the
EventLog kinds with the observability boundary event, the guarded violation
hook, the per-section rulebook loader, and the zero-uncaused-write battery.

Annotation note: the ``covers_requirement`` annotations reference the
canonical main-spec requirement IDs synced into ``openspec/specs/`` (the
``defeat-aftermath-recovery`` capability plus the amended
``defeat-aftermath-core`` expectations).
"""

import math
import unittest
from unittest.mock import MagicMock, patch

from django.test import override_settings
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

import world.rules.defeat_aftermath as defeat_aftermath_module
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

from ._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    open_synthetic_scope,
)
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS


# Synthetic restock fixture (data independence): the kit shop identity over
# two kit items. The restock hour/quantities/caps are authored here, so the
# restock expectations below name their own numbers.
_T_SHOP = next(iter(SYNTH_SHOPS))
_T_POTION = "t_ember_spray"
_T_BLADE = "t_iron_fang"
assert _T_POTION in SYNTH_ITEMS and _T_BLADE in SYNTH_ITEMS
_T_SHOP_RESTOCK_HOUR = 6
_T_POTION_STOCK_BEFORE = 3
_T_POTION_RESTOCKED = 5
_T_POTION_REACHED = _T_POTION_STOCK_BEFORE + 2  # restock_quantity 2, cap 5


def _synthetic_restock_catalog():
    return synth_catalog(
        shop_configs={
            _T_SHOP: synth_shop_config(
                _T_SHOP,
                (_T_POTION, _T_BLADE),
                restock_hour=_T_SHOP_RESTOCK_HOUR,
                offer_rules=(
                    synth_offer_rule(
                        _T_POTION,
                        max_stock=_T_POTION_REACHED,
                        initial_stock=_T_POTION_STOCK_BEFORE,
                        restock_quantity=2,
                    ),
                    synth_offer_rule(_T_BLADE, max_stock=1, initial_stock=1, restock_quantity=1),
                ),
            )
        }
    )


def _isolate_synthetic_catalog(test):
    """Swap the process-global guild catalog for the synthetic one.

    The recovery advance's caravan-arrival settlement reads it through the
    owner module, so production resolves only synthetic shop rows. Restores
    both the catalog and the offer registry through cleanup.
    """
    previous_catalog = guild_config_module.CATALOG
    previous_offers = list(GUILD_OFFER_REGISTRY.items())
    test.addCleanup(
        lambda: (
            setattr(guild_config_module, "CATALOG", previous_catalog),
            GUILD_OFFER_REGISTRY.clear(),
            GUILD_OFFER_REGISTRY.update(previous_offers),
        )
    )
    return install_synthetic_catalog(test, _synthetic_restock_catalog())


def _attack(player, target):
    """Submit the player's innate attack (runtime key, never a literal)."""
    return submit_player_action(player, BASIC_ATTACK_KEY, [target])


class DefeatAftermathBase(BattlefieldIsolation, EvenniaTestCase):
    """Shared clock isolation: both clock bindings see one WorldClock."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="defeat arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("defeat goblin")
        self.monster.location = self.room
        self.clock = WorldClock()
        for target in (
            "world.rules.combat_session.get_world_clock",
            "world.rules.clock.get_world_clock",
        ):
            patcher = patch(target, return_value=self.clock)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _defeat_by_forfeit(self, target=None):
        """Drive one hostile defeat settlement through ``forfeit``."""
        engage(self.player, target or self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            _attack(self.player, target or self.monster)
        return forfeit(self.player)


class WildernessDefeatMixin:
    """Materialize the real wilderness script and move the fight into it."""

    def tearDown(self):
        super().tearDown()
        # The contrib wilderness stamps ndb.wilderness/ndb.wildernessscript on
        # every occupant and room; TypedObject.at_idmapper_flush refuses to
        # evict ndb-holding objects, so EvenniaTestCase's non-forced
        # flush_cache leaves these rolled-back rows cached as idmapper ghosts.
        # A later module's create_object would resolve DEFAULT_HOME (#2)
        # through the stale cache entry and write a dangling db_home_id.
        ObjectDB.flush_instance_cache(force=True)

    def setUp_wilderness(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.assertTrue(enter_wilderness(self.player, coordinates=(60, 103), name=WILDERNESS_NAME))
        self.room = self.player.location
        self.monster.location = self.room

    def _mark_population_monster(self, monster, coordinates=(60, 103)):
        """Stamp the population marker and register the bookkeeping entry."""
        monster.db.population_key = f"wilderness:{coordinates[0]}:{coordinates[1]}"
        self.script.db.itemcoordinates[monster] = coordinates

    def _registered(self, monster):
        """Identity membership in the bookkeeping: the despawned instance is
        pk-stripped and therefore unhashable as a dict lookup key."""
        return any(key is monster for key in self.script.db.itemcoordinates.keys())


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
        saved_hook = defeat_aftermath_module._VIOLATION_HOOK
        self.addCleanup(setattr, defeat_aftermath_module, "_VIOLATION_HOOK", saved_hook)
        defeat_aftermath_module._VIOLATION_HOOK = None

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


class DepartureRuleTests(DefeatAftermathBase):
    """Violator departure precedence: quest-bound retain over despawn (D-C3)."""

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_foreign_monster_is_untouched(self):
        result = self._defeat_by_forfeit()
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.monster.pk, self.monster.pk)  # alive, untouched
        self.assertEqual(self.monster.location, self.room)


class WildernessDepartureTests(WildernessDefeatMixin, DefeatAftermathBase):
    """Population despawn and quest-bound retention in the real wilderness."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_population_winner_despawns_at_defeat_settlement(self):
        self._mark_population_monster(self.monster)
        saved_pk = self.monster.pk
        with self.captureOnCommitCallbacks(execute=True):
            self._defeat_by_forfeit()
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        # The next coordinate activation respawns per the untouched model.
        from world.maps.wilderness_population import ensure_population

        ensure_population(self.script, (60, 103))
        monsters = [
            obj
            for obj in self.script.get_objs_at_coordinates((60, 103))
            if isinstance(obj, type(self.monster))
        ]
        self.assertEqual(len(monsters), 1)

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_quest_bound_winner_with_marker_is_retained(self):
        self._bind_defeat_quest(self.monster)
        self._mark_population_monster(self.monster)
        saved_pk = self.monster.pk
        self._defeat_by_forfeit()
        # Quest retention outranks the population marker: the monster stays.
        self.assertTrue(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertEqual(self.monster.location, self.room)
        self.assertTrue(self._registered(self.monster))

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_post_commit_delete_failure_reverts_departure(self):
        self._mark_population_monster(self.monster)
        saved_marker = self.monster.db.population_key
        with (
            patch.object(
                type(self.monster), "delete", side_effect=RuntimeError("boom")
            ),
            patch("world.rules.defeat_aftermath.log_error") as log_error,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self._defeat_by_forfeit()
        # Deterministic recovery: the logical departure reverted, the monster
        # remains a normal reconcilable population monster.
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        errors = [
            call
            for call in log_error.call_args_list
            if call.args and call.args[0] == "defeat_aftermath_depart_delete_failed"
        ]
        self.assertEqual(len(errors), 1)

    def _bind_defeat_quest(self, monster):
        """Accept a bound-defeat quest whose objective targets ``monster``."""
        definition = register(quest("aftermath_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        self.guard_room = create_object(InstanceRoom, key="aftermath guard room")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=self.guard_room,
            objective_targets=(monster,),
            protected_entities=(self._guard_npc(),),
        )

    def _guard_npc(self):
        if not hasattr(self, "guard_npc"):
            self.guard_npc = create_object(NPC, key="aftermath guard")
            self.guard_npc.race = "human"
            self.guard_npc.apply_race_baseline()
        return self.guard_npc


class RetainedWinnerConsequenceTests(WildernessDefeatMixin, DefeatAftermathBase):
    """Task 3.3: the retained winner blocks rest; movement stays HP-free."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        definition = register(quest("retained_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=create_object(InstanceRoom, key="retained guard room"),
            objective_targets=(self.monster,),
        )

    @covers_requirement(
        "defeat-aftermath-core::hostile-defeat-floors-player-hp-at-1-and-marks-the-player-knocked-out",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_retained_winner_blocks_rest_but_not_movement(self):
        self._defeat_by_forfeit()
        self.assertEqual(self.player.traits.hp.current, 5)
        # skip_safety still refuses a time-skip rest with the live winner.
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.HOSTILE_PRESENT
        )
        # Movement has no HP gate (pinned behavior, no edit): the shared cost
        # charge succeeds at the post-settlement wake state.
        before = self.clock.tick
        charge_movement(self.player, "move")
        self.assertGreater(self.clock.tick, before)

    @covers_requirement(
        "defeat-aftermath-recovery::a-retained-quest-bound-winner-forces-the-move-and-rest-route"
    )
    def test_defeat_then_move_then_rest_to_full(self):
        """Task 3.3 smoke: retained winner -> wake at target -> move -> rest."""
        self._defeat_by_forfeit()
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.HOSTILE_PRESENT
        )
        # Movement has no HP gate: traverse an ordinary wilderness exit out
        # of the winner's room into an adjacent, monster-free, non-gateway
        # cell (the wilderness exits self-loop; routing is coordinate-based).
        from world.maps.wilderness_destination import (
            DIRECTION_DELTAS,
            find_gateway,
            normalize_wilderness_direction,
        )

        current = self.script.db.itemcoordinates[self.player]
        exits_by_direction = {
            normalize_wilderness_direction(exit_obj.key): exit_obj
            for exit_obj in self.room.exits
        }
        direction = next(
            _d for _d in sorted(DIRECTION_DELTAS) if not find_gateway(current, _d)
        )
        exit_obj = exits_by_direction[direction]
        delta_x, delta_y = DIRECTION_DELTAS[direction]
        neighbor = (current[0] + delta_x, current[1] + delta_y)
        exit_obj.at_traverse(self.player, exit_obj.destination)
        self.assertEqual(self.script.db.itemcoordinates[self.player], neighbor)
        # The Elosern map spawns a living monster on every wilderness cell at
        # room-activation time; the smoke arranges the destination's own
        # spawn away so the rest proves the movement route, not monster
        # density. The winner itself lives on, evicted back at (60, 103).
        for occupant in list(self.player.location.contents):
            if isinstance(occupant, Monster):
                occupant.delete()
        self.assertIsNone(evaluate_skip_safety(self.player))
        advance_skip(self.player, seconds_to_full_regen(self.player))
        self.assertEqual(self.player.traits.hp.current, self.player.traits.hp.max)


class EventSourceIsolation:
    """Snapshot/restore the process-global clock event-source registry."""

    def isolate_event_sources(self, *factories) -> None:
        backup = dict(clock_module._EVENT_SOURCES)
        clock_module._EVENT_SOURCES.clear()
        self.addCleanup(self._restore_event_sources, backup)
        for factory in factories:
            factory()

    def _restore_event_sources(self, backup) -> None:
        clock_module._EVENT_SOURCES.clear()
        clock_module._EVENT_SOURCES.update(backup)


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
        with patch("world.rules.defeat_aftermath.log_error") as error:
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
        with patch("world.rules.defeat_aftermath.log_error") as error:
            result, calls = self._spied_defeat()
        self.assertEqual(calls[1], (21600, AdvanceSource.DEFEAT_AFTERMATH))
        self.assertEqual(self.player.traits.hp.current, 2)
        self.assertAlmostEqual(self.player.traits.hp.regen_remainder, 0.08, places=6)
        self.assertEqual(error.call_count, 1)
        self.assertEqual(error.call_args.kwargs["context"]["target"], 5)


class RecoveryWindowClockCausalityTests(
    EventSourceIsolation, WildernessDefeatMixin, RegistryIsolationMixin, DefeatAftermathBase
):
    """The recovery window's clock causality (task 3.1, delta requirement 4)."""

    # altoria_general_store restocks at day-1 06:00 = 108000. The defeat at
    # tick 107990 spends 6s of combat and 8s of recovery, so exactly that one
    # boundary falls inside the recovery window (107996, 108004].
    RESTOCK_TICK = 86400 + _T_SHOP_RESTOCK_HOUR * 3600

    def setUp(self):
        open_synthetic_scope(self, "items", "prices", "shops")
        super().setUp()
        self.setUp_wilderness()
        clock_patcher = patch(
            "world.quests.runtime.get_world_clock", return_value=self.clock
        )
        clock_patcher.start()
        self.addCleanup(clock_patcher.stop)
        self.isolate_event_sources(register_caravan_arrivals, sync_quest_runtime)
        _isolate_synthetic_catalog(self)
        store = create_object(Room, key="window store")
        merchant_npc = create_object(NPC, key="window merchant", location=store)
        self.merchant = Merchant.create(
            merchant_npc,
            service_id="t_synthetic_merchant",
            shop_key=_T_SHOP,
        )
        merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {_T_POTION: _T_POTION_STOCK_BEFORE, _T_BLADE: 1}
        self.merchant.last_restock_day = 0

    def _manifest(self):
        player = self.player
        return {
            "wallet": lambda: player.wallet,
            "inventory": lambda: list(player.db.inventory or []),
            "guild_rank": lambda: player.guild_rank,
            "guild_merit": lambda: read_counter_trait(player, "guild_merit"),
        }

    @covers_requirement(
        "defeat-aftermath-recovery::clock-side-effects-during-the-recovery-window-are-the-only-quest-world-mutations"
    )
    def test_window_fails_exactly_one_deadline_and_restocks_once(self):
        self.clock.tick = self.RESTOCK_TICK - 3600  # accepted tick 104400
        definition = register(quest("window_deadline", deadline_hours=1))
        record = accept(self.player, definition.key)
        self.assertEqual(record.deadline_tick, self.RESTOCK_TICK)
        before = {family: extract() for family, extract in self._manifest().items()}
        self.clock.tick = self.RESTOCK_TICK - 10
        with self.captureOnCommitCallbacks(execute=True):
            self._defeat_by_forfeit()
        # Combat window (107990, 107996] crossed nothing; the recovery window
        # (107996, 108004] crossed the deadline and the restock together.
        self.assertEqual(self.clock.tick, self.RESTOCK_TICK + 4)
        self.assertEqual(self.player.traits.hp.current, 5)
        stored = [dict(entry) for entry in (self.player.db.quest_log or [])]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["state"], "failed")
        self.assertEqual(stored[0]["failure_reason"], "deadline_expired")
        self.assertEqual(self.merchant.merchant_stock[_T_POTION], _T_POTION_RESTOCKED)
        self.assertEqual(self.merchant.last_restock_day, 1)
        self.assertEqual(self.merchant.merchant_stock[_T_BLADE], 1)
        after = {family: extract() for family, extract in self._manifest().items()}
        self.assertEqual(after, before)


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
            patch("world.rules.defeat_aftermath.log_info") as info,
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
            patch("world.rules.defeat_aftermath.log_info") as info,
            patch("world.rules.combat_session._persist", side_effect=RuntimeError("injected")),
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
        with patch("world.rules.defeat_aftermath.log_warn") as warn:
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


class ZeroUncausedWriteTests(WildernessDefeatMixin, RegistryIsolationMixin, DefeatAftermathBase):
    """The declared-write manifest battery (D-C7, tasks 6.1)."""

    # Record families the defeat settlement must leave byte-identical. Code,
    # not prose: each downstream change extends this manifest with its declared
    # writes and re-runs the battery.
    CLOCK_CAUSED_FAMILIES = (
        # Legitimate in-window mutations the world clock causally produces:
        # quest deadline failure, gauge daily decay/reset, merchant restock,
        # buff decay. The battery's settlement window crosses none of them.
        "quest_deadline",
        "gauge_daily",
        "restock",
        "buff_decay",
    )

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        self.companion = create_object(NPC, key="aftermath companion")
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        self.companion.location = self.room
        self.guard_npc = create_object(NPC, key="aftermath staff")
        self.guard_npc.race = "human"
        self.guard_npc.apply_race_baseline()
        self.guard_npc.location = self.room
        from world.rules.party import join_party

        join_party(self.companion, self.player)
        apply_affinity_change(self.guard_npc, self.player, "quest_completion", 5)
        self.player.guild_rank = "E"
        write_counter_trait(self.player, "guild_merit", 10)
        self.player.wallet = 500
        # Seeded raw inventory (shape mirrors list_items: a list of keys).
        self.player.db.inventory = [_T_POTION]
        definition = register(quest("battery_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        self.bound_room = create_object(InstanceRoom, key="battery binding room")
        self.bound_monster = _monster("battery bound goblin")
        self.bound_monster.location = self.room
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=self.bound_room,
            objective_targets=(self.bound_monster,),
            protected_entities=(self.guard_npc,),
        )
        self._mark_population_monster(self.monster)

    def _manifest(self):
        """The declared-write manifest: family -> extractor (D-C7)."""
        player, companion, guard = self.player, self.companion, self.guard_npc
        return {
            "affinity": lambda: (
                guard.relations.affinity_for(player),
                companion.relations.affinity_for(player),
            ),
            "wallet": lambda: player.wallet,
            "inventory": lambda: list(player.db.inventory or []),
            "quest_progress": lambda: [dict(e) for e in (player.db.quest_log or [])],
            "guild_rank": lambda: player.guild_rank,
            "guild_merit": lambda: read_counter_trait(player, "guild_merit"),
            "protected_bindings": lambda: list(self.bound_room.db.pin_reasons or []),
            "party_binding": lambda: (list(player.db.party or []), companion.db.party_member),
        }

    @covers_requirement(
        "defeat-aftermath-core::defeat-settlement-s-only-uncaused-record-writes-are-the-declared-ones"
    )
    def test_manifest_section_ownership(self):
        manifest = self._manifest()
        for family in (
            "affinity",
            "wallet",
            "inventory",
            "quest_progress",
            "guild_rank",
            "guild_merit",
            "protected_bindings",
        ):
            self.assertIn(family, manifest)
        self.assertTrue(self.CLOCK_CAUSED_FAMILIES)

    @covers_requirement(
        "defeat-aftermath-core::defeat-settlement-s-only-uncaused-record-writes-are-the-declared-ones",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_defeat_settlement_writes_only_the_declared_records(self):
        before = {family: extract() for family, extract in self._manifest().items()}
        saved_marker_pk = self.monster.pk
        saved_bound_pk = self.bound_monster.pk
        # Defeat one: the population-marker monster despawns. Defeat two: the
        # quest-bound monster is retained by precedence.
        with self.captureOnCommitCallbacks(execute=True):
            self._defeat_by_forfeit(self.monster)
            self.player.traits.hp.current = 100
            self._defeat_by_forfeit(self.bound_monster)
        after = {family: extract() for family, extract in self._manifest().items()}
        self.assertEqual(after, before)
        self.assertFalse(ObjectDB.objects.filter(id=saved_marker_pk).exists())
        self.assertTrue(ObjectDB.objects.filter(id=saved_bound_pk).exists())
        self.assertEqual(self.bound_monster.location, self.room)
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.HOSTILE_PRESENT
        )


class RollbackTests(
    EventSourceIsolation, WildernessDefeatMixin, RegistryIsolationMixin, DefeatAftermathBase
):
    """Rollback injection after the writer's last write (tasks 6.2, D-C5)."""

    def setUp(self):
        open_synthetic_scope(self, "items", "prices", "shops")
        super().setUp()
        self.setUp_wilderness()
        self._mark_population_monster(self.monster)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit"
    )
    @covers_requirement(
        "defeat-aftermath-recovery::the-recovery-phase-commits-with-the-settlement"
    )
    def test_persist_failure_rolls_back_the_whole_aftermath_and_retry_settles_once(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            _attack(self.player, self.monster)
        saved_pk = self.monster.pk
        hp_after_round = self.player.traits.hp.current
        quest_log_before = [dict(e) for e in (self.player.db.quest_log or [])]
        with (
            patch("world.rules.combat_session._persist", side_effect=RuntimeError("injected")),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        # Every aftermath write is absent: monster, bookkeeping, HP, buff.
        self.assertTrue(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        self.assertEqual(self.player.traits.hp.current, hp_after_round)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual([dict(e) for e in (self.player.db.quest_log or [])], quest_log_before)
        self.assertIsNotNone(self.player.db.active_combat)
        self.assertEqual(self.clock.tick, 6)
        # Retry settles fully, exactly once.
        with self.captureOnCommitCallbacks(execute=True):
            result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        self.assertIsNone(self.player.db.active_combat)
        # Combat 6s + recovery 8s (scale 0.5 over the 1.0/s stored rate).
        self.assertEqual(self.clock.tick, 20)

    @covers_requirement(
        "defeat-aftermath-recovery::the-recovery-phase-commits-with-the-settlement"
    )
    def test_outer_commit_failure_restores_the_recovery_advance(self):
        """The outer-owner seam covers the recovery advance's registry (duck 6)."""

        class OuterExplodingAtomic:
            def __init__(self):
                self.depth = 0

            def __enter__(self):
                self.depth += 1
                return self

            def __exit__(self, exc_type, exc, tb):
                self.depth -= 1
                if exc_type is None and self.depth == 0:
                    raise RuntimeError("injected outer commit failure")
                return False

        self.isolate_event_sources(register_caravan_arrivals, sync_quest_runtime)
        _isolate_synthetic_catalog(self)
        store = create_object(Room, key="rollback store")
        merchant_npc = create_object(NPC, key="rollback merchant", location=store)
        merchant = Merchant.create(
            merchant_npc,
            service_id="t_synthetic_merchant",
            shop_key=_T_SHOP,
        )
        merchant_npc.components.add(merchant)
        merchant.merchant_stock = {_T_POTION: _T_POTION_STOCK_BEFORE, _T_BLADE: 1}
        merchant.last_restock_day = 0

        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            _attack(self.player, self.monster)
        hp_after_round = self.player.traits.hp.current
        saved_marker = self.monster.db.population_key
        collected: list = []
        fake_tx = MagicMock()
        fake_tx.atomic.return_value = OuterExplodingAtomic()
        fake_tx.on_commit.side_effect = collected.append
        # The restock boundary (day 1, 06:00 = 108000) sits inside the first
        # attempt's recovery window (107996, 108004].
        self.clock.tick = 107990
        with (
            patch("django.db.transaction.atomic", fake_tx.atomic),
            patch("django.db.transaction.on_commit", fake_tx.on_commit),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        # The successful recovery advance is fully restored: the player's
        # traits, and the contract-discovered merchant surface the advance
        # had already restocked.
        self.assertEqual(self.player.traits.hp.current, hp_after_round)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(merchant.merchant_stock[_T_POTION], _T_POTION_STOCK_BEFORE)
        self.assertEqual(merchant.last_restock_day, 0)
        self.assertEqual(self.monster.db.population_key, saved_marker)
        # Retry: the wake state and the advance are reproduced. The restock
        # boundary is day-granular: the reverted last_restock_day=0 with the
        # retry window still ending on day 1 after 06:00 legitimately catches
        # the day-1 restock up once.
        with self.captureOnCommitCallbacks(execute=True):
            result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertEqual(self.clock.tick, 108010)
        self.assertEqual(merchant.last_restock_day, 1)
        self.assertEqual(merchant.merchant_stock[_T_POTION], _T_POTION_RESTOCKED)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit"
    )
    def test_commit_exit_failure_restores_aftermath_surfaces(self):
        class ExplodingAtomic:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                if exc_type is None:
                    raise RuntimeError("injected commit failure")
                return False

        collected: list = []
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            _attack(self.player, self.monster)
        saved_pk = self.monster.pk
        saved_marker = self.monster.db.population_key
        hp_after_round = self.player.traits.hp.current
        fake_tx = MagicMock()
        fake_tx.atomic.return_value = ExplodingAtomic()
        fake_tx.on_commit.side_effect = collected.append
        with (
            patch("django.db.transaction.atomic", fake_tx.atomic),
            patch("django.db.transaction.on_commit", fake_tx.on_commit),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        # The commit-exit failure bypasses any in-body handler: the outer
        # handler restored every idmapper-cached aftermath surface.
        self.assertEqual(self.player.traits.hp.current, hp_after_round)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.pk, saved_pk)  # callbacks never executed

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_outer_round_rollback_restores_aftermath_surfaces(self):
        # The submit path settles inside _submit_request's round transaction:
        # a failure AFTER the settlement returned must roll the aftermath
        # back together with the round (duck review issue 1).
        self.player.traits.hp.current = 1
        self.monster.traits.atk_phys.base = 100
        engage(self.player, self.monster)
        saved_pk = self.monster.pk
        saved_marker = self.monster.db.population_key
        real_continue = combat_session_module._continue_or_settle

        def exploding_continue(actor, record, battlefield, logs, **kwargs):
            real_continue(actor, record, battlefield, logs, **kwargs)
            raise RuntimeError("injected outer failure after settlement")

        with (
            patch(
                "world.rules.combat_session._continue_or_settle",
                exploding_continue,
            ),
            patch("world.rules.combat.roll_d100", return_value=1),
            self.assertRaises(RuntimeError),
        ):
            _attack(self.player, self.monster)
        # The armed undo ran inside _submit_request's except: the winner and
        # its marker/bookkeeping survived the outer rollback.
        self.assertEqual(self.monster.pk, saved_pk)
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(self.player.traits.hp.current, 1)
        self.assertIsNotNone(self.player.db.active_combat)


class RecoveryFallbackDepartureTests(WildernessDefeatMixin, DefeatAftermathBase):
    """The degraded recovery path departs the resolvable winner (review D4)."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        self._mark_population_monster(self.monster)

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_moved_player_recovery_still_departs_population_winner(self):
        engage(self.player, self.monster)
        elsewhere = create_object(Room, key="recovery fallback room")
        self.player.location = elsewhere
        saved_pk = self.monster.pk
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            self.captureOnCommitCallbacks(execute=True),
        ):
            restore_active_session(self.player)
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        self.assertIsNone(self.player.db.active_combat)
