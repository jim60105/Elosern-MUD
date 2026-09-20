"""Synthetic aftermath fixtures and shared isolation bases for the `test_defeat_aftermath_core` slices.

Module-level fixtures, helpers, and bases moved verbatim from the
original flat module (not a collected test module).
"""

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
            "world.rules.combat_session.settlement.get_world_clock",
            "world.rules.clock.get_world_clock",
        ):
            patcher = patch(target, return_value=self.clock)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _defeat_by_forfeit(self, target=None):
        """Drive one hostile defeat settlement through ``forfeit``."""
        engage(self.player, target or self.monster)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=1), patch("world.rules.combat.damage.roll_d100", return_value=1), patch("world.rules.combat.rounds.roll_d100", return_value=1):
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
