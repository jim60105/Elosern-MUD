"""Shop-hours and caravan clock-source tests (tasks 10.1-10.6)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.clock import AdvanceSource, _STAGE_ORDER, register_event_source
from world.rules.guild_config import CATALOG, load_catalog_into_cache
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.shop_hours import _boundary_ticks, settle_shop_hours
from world.rules.caravan_arrivals import settle_caravan_arrivals
from world.rules.guild_economy import sync_guild_economy
from world.rules.tests.combat_fixtures import BattlefieldIsolation


class ClockRegistryIsolation(BattlefieldIsolation, QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        self._previous_catalog = CATALOG
        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        global CATALOG
        CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


import unittest

from world.rules.shop_hours import _boundary_ticks


class ShopHoursArithmeticTests(unittest.TestCase):
    HOUR = 3600
    DAY = 86400

    def test_no_boundary_crossed_emits_nothing(self):
        self.assertEqual(
            _boundary_ticks("shop", 8, 20, 10 * self.HOUR, 12 * self.HOUR),
            [],
        )

    def test_same_day_crossed_emits_open_then_close(self):
        ticks = _boundary_ticks("shop", 8, 20, 7 * self.HOUR, 21 * self.HOUR)
        self.assertEqual(
            ticks,
            [(8 * self.HOUR, "open"), (20 * self.HOUR, "close")],
        )

    def test_overnight_interval_closes_then_opens(self):
        # A 20:00->08:00 shop is OPEN overnight; crossing from 19:00 on day 0
        # to 09:00 on day 1 emits the day-0 20:00 open and the day-1 08:00
        # close.
        ticks = _boundary_ticks(
            "shop",
            20,
            8,
            19 * self.HOUR,
            self.DAY + 9 * self.HOUR,
        )
        self.assertEqual(
            ticks,
            [(20 * self.HOUR, "open"), (self.DAY + 8 * self.HOUR, "close")],
        )

    @covers_requirement("shop-economy::opening-status-is-clock-derived-and-emits-ordered-boundary-events")
    def test_multi_boundary_skip_emits_each_transition(self):
        ticks = _boundary_ticks(
            "shop",
            8,
            20,
            7 * self.HOUR,
            2 * self.DAY + 21 * self.HOUR,
        )
        kinds = [kind for _, kind in ticks]
        self.assertEqual(
            kinds,
            ["open", "close", "open", "close", "open", "close"],
        )


class ShopHoursSettlementTests(ClockRegistryIsolation, EvenniaTest):
    def test_settlement_emits_json_safe_events(self):
        events = settle_shop_hours(7 * 3600, 21 * 3600)
        self.assertTrue(any(event.kind == "shop_hours" for event in events))
        for event in events:
            self.assertIsInstance(event.due_tick, int)
            self.assertIn(event.payload["kind"], ("open", "close"))


class CaravanArrivalTests(ClockRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        load_catalog_into_cache()
        self.store = create_object(Room, key="store")
        self.merchant_npc = create_object(NPC, key="merchant", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="merchant",
            shop_key="altoria_general_store",
        )
        self.merchant_npc.components.add(self.merchant)

    def test_daily_restock_fills_only_to_cap(self):
        # healing_potion: max_stock 5, restock_quantity 2. Stock 4 crosses the
        # day boundary and gains exactly 1 (capped at max 5).
        self.merchant.merchant_stock = {"meal": 20, "healing_potion": 4, "plain_sword": 1}
        self.merchant.last_restock_day = 0
        with patch("world.rules.clock.get_world_clock") as clock:
            # Day 1 boundary crossed: restock_hour 6, end_tick = 1 day + 7h.
            clock.return_value.tick = 86400 + 7 * 3600
            events = settle_caravan_arrivals(0, 86400 + 7 * 3600)
        self.assertEqual(len(events), 1)
        meal_payload = next(e for e in events if e.payload["shop_key"] == "altoria_general_store")
        self.assertIn("healing_potion", meal_payload.payload["items_added"])
        self.assertEqual(self.merchant.merchant_stock["healing_potion"], 5)
        self.assertEqual(self.merchant.last_restock_day, 1)

    @covers_requirement("shop-economy::caravan-arrivals-restock-once-per-crossed-merchant-day-up-to-cap")
    def test_multi_day_skip_catches_up_deterministically(self):
        self.merchant.merchant_stock = {"meal": 0, "healing_potion": 0, "plain_sword": 0}
        self.merchant.last_restock_day = 0
        end_tick = 3 * 86400 + 7 * 3600
        with patch("world.rules.clock.get_world_clock") as clock:
            clock.return_value.tick = end_tick
            events = settle_caravan_arrivals(0, end_tick)
        # Three days crossed -> three caravan events.
        self.assertEqual(
            len([e for e in events if e.kind == "caravan_arrivals"]),
            3,
        )
        # At most three restocks; stock never exceeds max.
        self.assertLessEqual(self.merchant.merchant_stock["meal"], 20)
        self.assertLessEqual(self.merchant.merchant_stock["healing_potion"], 5)

    def test_one_restock_per_day(self):
        self.merchant.merchant_stock = {"meal": 0, "healing_potion": 0, "plain_sword": 0}
        self.merchant.last_restock_day = 0
        end_tick = 86400 + 7 * 3600
        with patch("world.rules.clock.get_world_clock") as clock:
            clock.return_value.tick = end_tick
            events = settle_caravan_arrivals(0, end_tick)
        self.assertEqual(len(events), 1)
        self.assertEqual(self.merchant.last_restock_day, 1)

    def test_malformed_merchant_is_isolated(self):
        bad_npc = create_object(NPC, key="bad merchant", location=self.store)
        bad_merchant = Merchant.create(bad_npc, service_id="bad", shop_key="altoria_general_store")
        bad_npc.components.add(bad_merchant)
        bad_merchant.merchant_stock = {"meal": "oops"}
        bad_merchant.last_restock_day = 0
        # The good merchant still settles; the malformed one is skipped.
        self.merchant.merchant_stock = {"meal": 0, "healing_potion": 0, "plain_sword": 0}
        self.merchant.last_restock_day = 0
        end_tick = 86400 + 7 * 3600
        with patch("world.rules.clock.get_world_clock") as clock:
            clock.return_value.tick = end_tick
            events = settle_caravan_arrivals(0, end_tick)
        self.assertEqual(len(events), 1)
        self.assertEqual(bad_merchant.merchant_stock, {"meal": "oops"})
        self.assertGreaterEqual(self.merchant.merchant_stock["meal"], 5)


class CaravanRollbackCacheTests(ClockRegistryIsolation, EvenniaTest):
    """A rolled-back advance restores merchant stock caches (F5)."""

    def setUp(self):
        super().setUp()
        import world.rules.clock as clock_module

        load_catalog_into_cache()
        self.store = create_object(Room, key="store")
        self.merchant_npc = create_object(NPC, key="merchant", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="merchant",
            shop_key="altoria_general_store",
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {"meal": 0, "healing_potion": 0, "plain_sword": 0}
        self.merchant.last_restock_day = 0
        self._sources = dict(clock_module._EVENT_SOURCES)

    def tearDown(self):
        import world.rules.clock as clock_module

        clock_module._EVENT_SOURCES.clear()
        clock_module._EVENT_SOURCES.update(self._sources)
        super().tearDown()

    def _raw_attribute(self, obj, key):
        row = (
            obj.db_attributes.through.objects.filter(
                objectdb_id=obj.pk, attribute__db_key=key
            )
            .values_list("attribute__db_value", flat=True)
            .first()
        )
        return None if row is None else row

    @covers_requirement("world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities")
    def test_failing_persist_restores_merchant_stock_and_restock_day(self):
        from evennia.utils.search import search_script
        from world.rules.caravan_arrivals import register_caravan_arrivals
        from world.rules.clock import get_world_clock

        # Advance into day 0's late afternoon so a further advance crosses the
        # day-1 06:00 restock boundary without exceeding the one-day bound.
        get_world_clock().advance(60000, AdvanceSource.SKIP, [])
        register_caravan_arrivals()
        clock = get_world_clock()
        before_tick = clock.tick
        before_stock = dict(self.merchant.merchant_stock)
        before_day = self.merchant.last_restock_day
        script = search_script("world_clock")[0]

        def failing_persist(tick):
            script.db.tick = tick
            raise RuntimeError("simulated persist failure")

        clock._persist = failing_persist
        with self.assertRaises(RuntimeError):
            clock.advance(60000, AdvanceSource.SKIP, [])

        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(script.db.tick, before_tick)
        self.assertEqual(self.merchant.merchant_stock, before_stock)
        self.assertEqual(self.merchant.last_restock_day, before_day)
        from world.rules.caravan_arrivals import _merchant_surface_keys

        stock_key, day_key = _merchant_surface_keys()
        self.assertEqual(self._raw_attribute(self.merchant_npc, stock_key), before_stock)
        self.assertEqual(self._raw_attribute(self.merchant_npc, day_key), before_day)


class StageOrderAndRegistrationTests(ClockRegistryIsolation, EvenniaTest):
    @covers_requirement("settlement-stage-order::caravan-arrivals-shop-hours-quest-deadlines-and-npc-schedules-are-declared")
    def test_caravan_precedes_shop_hours_in_stage_order(self):
        self.assertLess(
            _STAGE_ORDER.index("caravan_arrivals"),
            _STAGE_ORDER.index("shop_hours"),
        )

    def test_sources_register_in_sync_guild_economy(self):
        from world.rules.clock import _EVENT_SOURCES

        sync_guild_economy()
        self.assertIn("caravan_arrivals", _EVENT_SOURCES)
        self.assertIn("shop_hours", _EVENT_SOURCES)

    def test_quest_deadlines_still_after_shop_hours(self):
        self.assertLess(
            _STAGE_ORDER.index("shop_hours"),
            _STAGE_ORDER.index("quest_deadlines"),
        )


if __name__ == "__main__":
    unittest.main()
