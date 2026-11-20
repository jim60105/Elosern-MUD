"""Behavior coverage for paid inn lodging, city sleep and paid recovery."""

from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.components import Lodging
from typeclasses.npcs import NPC
from typeclasses.rooms import LodgingGuestRoom
from world.rules import city_sleep, lodging
from world.rules.clock import AdvanceSource, WorldClock, get_world_clock
from world.rules.fatigue import (
    POSTURE_ATTRIBUTE,
    RESERVE_ATTRIBUTE,
    FatigueActivity,
    IntervalCompletion,
    SleepPosture,
    read_optional_fatigue_state,
    write_fatigue_state,
)
from world.rules.mental_time import plan_for
from world.rules.party import join_party
from world.rules.rest_bonuses import (
    award_walking_allowance,
    consume_walking_allowance,
    read_access,
    read_paid_sleep,
    read_street_nap,
    read_street_refusals,
    read_walking_allowance,
)
from world.rules.sleep_receipt import (
    STATE_COMPLETED,
    STATE_INTERRUPTED,
    full_recovery_seconds,
    read_sleep_receipt,
)
from world.rules.time_skip import (
    SleepRefused,
    begin_sleep,
    continue_sleep,
    enter_sleep,
)
TEST_INN = "test_inn"
TEST_INNKEEPER = "test_innkeeper"
TEST_SHOP = "test_shop"
TEST_SHELTER = "test_shelter"
TEST_CITY = "test_city"
TEST_VILLAGE = "test_village"


def _place(key, settlement, *, lodging_capability=False):
    components = (
        (SimpleNamespace(type="lodging", kwargs={}),)
        if lodging_capability
        else ()
    )
    return SimpleNamespace(
        key=key,
        settlement_key=settlement,
        components=components,
    )


def _interiors(*keys):
    return SimpleNamespace(rooms={key: object() for key in keys})


def _host(room):
    host = create_object(NPC, key="旅店老闆", location=room)
    component = Lodging.create(host, service_id=TEST_INNKEEPER)
    host.components.add(component)
    component = host.components.get(Lodging.get_component_slot())
    component.service_binding = "place"
    component.anchor_room_id = int(room.pk)
    return host


class LodgingCheckInTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.db.wallet = 200
        self.room1.tags.add(TEST_INN)
        place = _place(TEST_INN, TEST_CITY, lodging_capability=True)
        places = patch.object(
            city_sleep, "_place_for_room", return_value=place
        )
        places.start()
        self.addCleanup(places.stop)
        lobby_key = patch.object(
            lodging, "_lobby_place_key", return_value=TEST_INN
        )
        lobby_key.start()
        self.addCleanup(lobby_key.stop)
        interiors = patch.object(
            city_sleep,
            "_published_interiors",
            return_value=_interiors(TEST_INN),
        )
        interiors.start()
        self.addCleanup(interiors.stop)
        self.host = _host(self.room1)

    def _companion(self, key, location=None):
        npc = create_object(NPC, key=key, location=location or self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        return npc

    def test_quote_and_confirm_charge_present_party_and_move_it(self):
        companion = self._companion("在場同伴")
        remote = self._companion("遠端同伴")
        remote.location = self.room2
        quote = lodging.quote_for(self.player, self.host)
        self.assertEqual(quote.unit_price, city_sleep.get_policy().price_per_guest_copper)
        self.assertEqual(quote.guest_ids, (int(self.player.pk), int(companion.pk)))
        self.assertEqual(quote.total, 2 * quote.unit_price)
        from world.rules.npc_services import project_npc_services

        projection = project_npc_services(self.player, self.player, self.host)
        entry = next(
            item for item in projection.entries if item.key == "lodging.stay"
        )
        self.assertTrue(entry.enabled)
        self.assertEqual(entry.route.command, "lodging")
        result = lodging.confirm_check_in(
            self.player, self.host, quote_id=quote.quote_id
        )
        self.assertEqual(self.player.db.wallet, 200 - quote.total)
        self.assertIsInstance(self.player.location, LodgingGuestRoom)
        self.assertIs(self.player.location, companion.location)
        self.assertIs(remote.location, self.room2)
        self.assertIsNotNone(read_access(self.player))
        self.assertIsNotNone(read_access(companion))
        self.assertIsNone(read_access(remote))
        self.assertEqual(result.room_id, int(self.player.location.pk))

    def test_stale_wallet_and_blocked_guest_change_nothing(self):
        quote = lodging.quote_for(self.player, self.host)
        self.player.db.wallet = 0
        with self.assertRaises(lodging.LodgingError):
            lodging.confirm_check_in(self.player, self.host, quote_id=quote.quote_id)
        self.assertEqual(self.player.db.wallet, 0)
        self.assertIs(self.player.location, self.room1)
        self.assertIsNone(lodging.read_booking(self.room1))

        self.player.db.wallet = 200
        companion = self._companion("沉睡同伴")
        write_fatigue_state(companion, 100000, SleepPosture.FORCED)
        with self.assertRaises(lodging.LodgingError):
            lodging.confirm_check_in(self.player, self.host)
        self.assertIs(self.player.location, self.room1)
        self.assertIsNone(lodging.read_booking(self.room1))

    def test_unauthorized_entry_and_departure_close_the_booking(self):
        companion = self._companion("同伴")
        quote = lodging.quote_for(self.player, self.host)
        lodging.confirm_check_in(self.player, self.host, quote_id=quote.quote_id)
        room = self.player.location
        intruder = create_object(
            self.player.__class__, key="未登記旅客", location=self.room1
        )
        messages = []
        intruder.msg = messages.append
        self.assertFalse(intruder.move_to(room))
        self.assertIs(intruder.location, self.room1)
        self.assertNotIn(intruder, room.contents)
        self.assertTrue(messages)

        self.player.move_to(self.room1)
        booking = lodging.read_booking(self.room1)
        self.assertIsNotNone(booking)
        self.assertNotIn(int(self.player.pk), booking["guest_ids"])
        self.assertIsNone(read_access(self.player))
        companion.move_to(self.room1)
        self.assertIsNone(lodging.read_booking(self.room1))

    def test_repeated_stay_reuses_one_persistent_room(self):
        quote = lodging.quote_for(self.player, self.host)
        first = lodging.confirm_check_in(
            self.player, self.host, quote_id=quote.quote_id
        )
        self.player.move_to(self.room1)
        quote = lodging.quote_for(self.player, self.host)
        second = lodging.confirm_check_in(
            self.player, self.host, quote_id=quote.quote_id
        )
        self.assertEqual(first.room_id, second.room_id)
        self.assertIsInstance(self.player.location, LodgingGuestRoom)

    def test_failure_after_debit_and_partial_move_restores_every_surface(self):
        companion = self._companion("受困同伴")
        quote = lodging.quote_for(self.player, self.host)
        real = lodging.may_enter_guest_room

        def refuse_companion(entity, room):
            return int(getattr(entity, "pk", 0) or 0) != int(companion.pk)

        before = (self.player.location, companion.location, self.player.db.wallet)
        with patch.object(lodging, "may_enter_guest_room", side_effect=refuse_companion):
            with self.assertRaises(lodging.LodgingError):
                lodging.confirm_check_in(
                    self.player, self.host, quote_id=quote.quote_id
                )
        self.assertIs(self.player.location, before[0])
        self.assertIs(companion.location, before[1])
        self.assertEqual(self.player.db.wallet, before[2])
        self.assertIsNone(lodging.read_booking(self.room1))
        self.assertIsNone(read_access(self.player))
        self.assertIsNone(read_access(companion))
        room = lodging.read_guest_room(self.room1, TEST_INN)
        if room is not None:
            self.assertFalse(real(companion, room))


class PaidSleepTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.db.wallet = 100
        self.room1.tags.add(TEST_INN)
        place = _place(TEST_INN, TEST_CITY, lodging_capability=True)
        places = patch.object(
            city_sleep, "_place_for_room", return_value=place
        )
        places.start()
        self.addCleanup(places.stop)
        lobby_key = patch.object(
            lodging, "_lobby_place_key", return_value=TEST_INN
        )
        lobby_key.start()
        self.addCleanup(lobby_key.stop)
        interiors = patch.object(
            city_sleep,
            "_published_interiors",
            return_value=_interiors(TEST_INN),
        )
        interiors.start()
        self.addCleanup(interiors.stop)
        self.host = _host(self.room1)

    def _check_in(self):
        quote = lodging.quote_for(self.player, self.host)
        lodging.confirm_check_in(self.player, self.host, quote_id=quote.quote_id)

    def test_recovery_target_uses_doubled_rate_and_paid_sleep_is_bound(self):
        self._check_in()
        for key in ("hp", "mp", "sp"):
            gauge = getattr(self.player.traits, key)
            gauge.current = gauge.max
        write_fatigue_state(self.player, 72000, SleepPosture.AWAKE)
        entry = enter_sleep(self.player, mode="recovery")
        expected = (360000 - 72000) // 24
        self.assertEqual(entry.accepted_seconds, expected)
        self.assertEqual(
            read_paid_sleep(self.player)["sleep_id"], entry.sleep_id
        )
        result = continue_sleep(self.player, entry)
        self.assertEqual(result.elapsed_seconds, expected)
        receipt = read_sleep_receipt(self.player)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.state, STATE_COMPLETED)
        self.assertEqual(read_optional_fatigue_state(self.player).reserve_units, 360000)
        self.assertEqual(read_walking_allowance(self.player), 7200)
        self.assertIsNone(read_paid_sleep(self.player))

    def test_allowance_never_stacks_and_replay_cannot_refill_it(self):
        self._check_in()
        for key in ("hp", "mp", "sp"):
            gauge = getattr(self.player.traits, key)
            gauge.current = gauge.max
        write_fatigue_state(self.player, 72000, SleepPosture.AWAKE)
        entry = enter_sleep(self.player, mode="recovery")
        continue_sleep(self.player, entry)
        self.assertEqual(read_walking_allowance(self.player), 7200)
        consume_walking_allowance(self.player, 3600)
        self.assertEqual(read_walking_allowance(self.player), 3600)
        self.assertFalse(
            award_walking_allowance(self.player, entry.sleep_id)
        )
        self.assertEqual(read_walking_allowance(self.player), 3600)

    def test_paid_sleep_doubles_a_depleted_gauge_rate(self):
        self._check_in()
        gauge = self.player.traits.hp
        gauge.current = gauge.max - 1200
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)
        ordinary = full_recovery_seconds(self.player, paid=False)
        paid = full_recovery_seconds(self.player, paid=True)
        self.assertGreater(ordinary, 0)
        self.assertEqual(paid, (ordinary + 1) // 2)

    def test_paid_sleep_actually_fills_all_four_resources_faster(self):
        self._check_in()
        for key in ("hp", "mp", "sp"):
            gauge = getattr(self.player.traits, key)
            gauge.current = gauge.max - 2400
        write_fatigue_state(self.player, 240000, SleepPosture.AWAKE)
        entry = enter_sleep(self.player, mode="recovery")
        self.assertGreater(entry.accepted_seconds, 0)
        self.assertEqual(entry.accepted_seconds, full_recovery_seconds(self.player, paid=True))
        continue_sleep(self.player, entry)
        for key in ("hp", "mp", "sp"):
            gauge = getattr(self.player.traits, key)
            self.assertGreaterEqual(float(gauge.current), float(gauge.max))
        self.assertEqual(read_optional_fatigue_state(self.player).reserve_units, 360000)
        self.assertIsNotNone(read_access(self.player))
        with self.assertRaises(SleepRefused):
            enter_sleep(self.player, mode="duration", seconds=60)


class CitySleepPolicyTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        places_by_room = {
            TEST_SHOP: _place(TEST_SHOP, TEST_CITY),
            TEST_SHELTER: _place(TEST_SHELTER, TEST_VILLAGE),
        }
        places = patch.object(
            city_sleep,
            "_place_for_room",
            side_effect=lambda room, room_id: places_by_room.get(room_id),
        )
        places.start()
        self.addCleanup(places.stop)
        interiors = patch.object(
            city_sleep,
            "_published_interiors",
            return_value=_interiors(TEST_SHOP, TEST_SHELTER),
        )
        interiors.start()
        self.addCleanup(interiors.stop)
        city = patch.object(
            city_sleep,
            "_city_location",
            side_effect=lambda key: key == TEST_CITY,
        )
        city.start()
        self.addCleanup(city.stop)

    def test_city_interior_refuses_while_village_interior_and_outdoors_stay_open(self):
        self.room1.tags.add(TEST_SHOP)
        self.assertEqual(
            city_sleep.classify_room(self.room1).kind,
            city_sleep.SleepLocation.REFUSED,
        )
        with self.assertRaises(SleepRefused):
            enter_sleep(self.player, mode="duration", seconds=60)

        self.room1.tags.remove(TEST_SHOP)
        self.room1.tags.add(TEST_SHELTER)
        self.assertEqual(
            city_sleep.classify_room(self.room1).kind,
            city_sleep.SleepLocation.OPEN,
        )
        entry = enter_sleep(self.player, mode="duration", seconds=60)
        self.assertIsNotNone(entry.receipt)

    def test_patrol_ends_street_nap_and_refuses_same_day_again(self):
        place = city_sleep.SleepPlace(
            city_sleep.SleepLocation.STREET,
            settlement_key=TEST_CITY,
            street=f"{TEST_CITY}:test_street",
        )
        with patch.object(city_sleep, "classify_room", return_value=place):
            entry = enter_sleep(self.player, mode="duration", seconds=10000)
            self.assertGreater(entry.target_tick, 3600)
            self.assertEqual(
                read_street_nap(self.player)["patrol_tick"], 3600
            )
            clock = get_world_clock()
            clock.advance(
                3600,
                AdvanceSource.SKIP,
                (self.player,),
                mental=plan_for((self.player,)),
            )
            receipt = read_sleep_receipt(self.player)
            self.assertEqual(receipt.state, STATE_INTERRUPTED)
            self.assertIs(
                read_optional_fatigue_state(self.player).posture,
                SleepPosture.AWAKE,
            )
            self.assertIsNone(read_street_nap(self.player))
            self.assertEqual(
                read_street_refusals(self.player),
                {place.street: 0},
            )
            with self.assertRaises(SleepRefused):
                enter_sleep(self.player, mode="duration", seconds=60)

    def test_patrol_does_not_wake_a_forced_sleeper(self):
        write_fatigue_state(self.player, 0, SleepPosture.FORCED)
        clock = get_world_clock()
        clock.advance(3600, AdvanceSource.SKIP, (self.player,))
        self.assertIs(
            read_optional_fatigue_state(self.player).posture,
            SleepPosture.FORCED,
        )

    def test_another_bodys_advance_still_ends_the_nap_at_the_patrol(self):
        place = city_sleep.SleepPlace(
            city_sleep.SleepLocation.STREET,
            settlement_key=TEST_CITY,
            street=f"{TEST_CITY}:test_street",
        )
        with patch.object(city_sleep, "classify_room", return_value=place):
            enter_sleep(self.player, mode="duration", seconds=10000)
        other = create_object(self.player.__class__, key="路人", location=self.room2)
        clock = get_world_clock()
        clock.advance(
            3600,
            AdvanceSource.SKIP,
            (other,),
            mental=plan_for((other,)),
        )
        self.assertEqual(
            read_sleep_receipt(self.player).state, STATE_INTERRUPTED
        )
        self.assertEqual(read_street_refusals(self.player), {place.street: 0})

    def test_patrol_arithmetic_is_authored_and_deterministic(self):
        policy = city_sleep.get_policy()
        self.assertEqual(
            city_sleep.next_patrol_tick(0), policy.patrol_phase_offset_seconds
        )
        self.assertEqual(
            city_sleep.next_patrol_tick(policy.patrol_phase_offset_seconds),
            policy.patrol_phase_offset_seconds + policy.patrol_interval_seconds,
        )

    def test_street_refusal_expires_on_the_next_game_day(self):
        from world.rules.rest_bonuses import (
            record_street_refusal,
            street_refused,
        )

        record_street_refusal(self.player, "street", 0)
        self.assertTrue(street_refused(self.player, "street", 0))
        self.assertFalse(street_refused(self.player, "street", 1))

    def test_street_nap_shows_only_a_general_warning(self):
        place = city_sleep.SleepPlace(
            city_sleep.SleepLocation.STREET,
            settlement_key=TEST_CITY,
            street=f"{TEST_CITY}:test_street",
        )
        with patch.object(city_sleep, "classify_room", return_value=place):
            outcome = begin_sleep(self.player, mode="duration", seconds=600)
        self.assertIsNotNone(outcome.warning)
        self.assertNotIn("3600", outcome.warning)


class TravelAllowanceTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)

    def test_clock_settles_the_exact_piecewise_consumption(self):
        from world.rules.rest_bonuses import write_walking_allowance

        write_walking_allowance(self.player, 5)
        clock = WorldClock(0)
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            clock.advance(
                10,
                AdvanceSource.COMMAND,
                (self.player,),
                mental=plan_for(
                    (self.player,),
                    awake_activity=FatigueActivity.FOOT_TRAVEL,
                    completion=IntervalCompletion.INDIVISIBLE,
                ),
            )
        self.assertEqual(
            read_optional_fatigue_state(self.player).reserve_units,
            360000 - 70,
        )
        self.assertEqual(read_walking_allowance(self.player), 0)

    def test_pre_destination_depletion_uses_the_allowance_boundary(self):
        from world.rules.rest_bonuses import ALLOWANCE_ATTRIBUTE
        from world.rules.travel_cost import (
            MovementPreflightRefused,
            refuse_pre_destination_depletion,
        )

        class _Attributes:
            def __init__(self, values):
                self.values = values

            def has(self, key, category=None):
                return key in self.values

            def get(self, key, category=None, default=None):
                return self.values.get(key, default)

        def member(reserve):
            return SimpleNamespace(
                attributes=_Attributes(
                    {
                        RESERVE_ATTRIBUTE: reserve,
                        POSTURE_ATTRIBUTE: "awake",
                        ALLOWANCE_ATTRIBUTE: 5,
                    }
                )
            )

        refuse_pre_destination_depletion(10, [member(70)])
        with self.assertRaises(MovementPreflightRefused):
            refuse_pre_destination_depletion(10, [member(69)])

    def test_prediction_advance_matches_the_piecewise_allowance(self):
        from world.rules.travel_plan import TravellerState

        state = TravellerState(
            reserve_units=360000,
            posture=SleepPosture.AWAKE,
            allowance_seconds=5,
        )
        advanced = state.advance(10)
        self.assertEqual(advanced.reserve_units, 360000 - 70)
        self.assertEqual(advanced.allowance_seconds, 0)
