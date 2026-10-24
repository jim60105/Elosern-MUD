"""Durable per-body accepted sleep receipt and passive wake lifecycle.

Covers the fix-body-sleep-lifecycle contract: one accepted receipt per body,
duration versus recovery targets, capped partial recovery, reload/retry
identity, missing/corrupt receipts that never repair or refill, explicit
all-party entry and the all-sleeper passive settlement that leaves control
alone.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.fatigue import (
    SleepPosture,
    read_fatigue_state,
    write_fatigue_state,
)
from world.rules.party import join_party
from world.rules.possession import current_possession, enter_possession
from world.rules.sleep_receipt import (
    MODE_DURATION,
    MODE_RECOVERY,
    RECEIPT_ATTRIBUTE,
    SleepReceipt,
    SleepReceiptError,
    forced_wake_seconds,
    full_recovery_seconds,
    read_sleep_receipt,
    recovery_target_tick,
    validate_receipt,
    write_sleep_receipt,
)
from world.rules.time_skip import (
    ALREADY_RECOVERED_MESSAGE,
    MAX_SKIP_SECONDS,
    PARTIAL_RECOVERY_MESSAGE,
    SleepRefused,
    _RESULT_LEDGER,
    advance_wait,
    begin_sleep,
    continue_sleep,
    enter_party_sleep,
    enter_sleep,
    seconds_to_full_regen,
)


def _full_gauges(entity):
    for key in ("hp", "mp", "sp"):
        gauge = getattr(entity.traits, key)
        gauge.current = gauge.max
        gauge.rate = 0.0


class _Attrs:
    """Minimal mutable attribute store for pure receipt probes."""

    def __init__(self, **values):
        self.values = dict(values)

    def has(self, key, category=None):
        return key in self.values

    def get(self, key, default=None, category=None):
        return self.values.get(key, default)

    def add(self, key, value, category=None):
        self.values[key] = value

    def remove(self, key, category=None):
        self.values.pop(key, None)


class _Gauge:
    def __init__(self, value, maximum, rate=0):
        self.value = value
        self.current = value
        self.max = maximum
        self.rate = rate


def _probe(reserve, posture=SleepPosture.AWAKE, **gauges):
    full = _Gauge(100, 100, 0)
    return SimpleNamespace(
        traits=SimpleNamespace(
            hp=gauges.get("hp", full),
            mp=gauges.get("mp", full),
            sp=gauges.get("sp", full),
        ),
        attributes=_Attrs(
            mental_reserve_units=reserve, sleep_posture=posture.value
        ),
    )


def _receipt(**overrides):
    payload = {
        "sleep_id": "synthetic",
        "body_id": 1,
        "owner_id": 1,
        "kind": "voluntary",
        "mode": MODE_RECOVERY,
        "entry_tick": 100,
        "target_tick": 15100,
        "limit_tick": 15100,
        "settled_through_tick": 100,
        "revision": 0,
        "state": "sleeping",
        "accepted_seconds": 15000,
        "partial": False,
        "entry_operation_id": "synthetic",
        "last_operation_id": None,
        "last_result": None,
    }
    payload.update(overrides)
    return validate_receipt(payload)


class SleepTargetPureTests(unittest.TestCase):
    """Target arithmetic and receipt validation without clock advancement."""

    def test_uncapped_recovery_drives_the_capped_partial_target(self):
        body = _probe(360000, hp=_Gauge(1, 100000, 1))
        raw = full_recovery_seconds(body)
        self.assertGreater(raw, MAX_SKIP_SECONDS)
        self.assertEqual(seconds_to_full_regen(body), MAX_SKIP_SECONDS)

    def test_slowest_gauge_or_reserve_time_governs_recovery(self):
        body = _probe(
            345600,
            hp=_Gauge(0, 1200, 1),
            mp=_Gauge(0, 600, 1),
            sp=_Gauge(0, 900, 1),
        )
        self.assertEqual(full_recovery_seconds(body), 1200)

    def test_recovery_boundary_reevaluates_without_extending_the_cap(self):
        body = _probe(180000)
        receipt = _receipt()
        self.assertEqual(recovery_target_tick(body, receipt, 100), 15100)
        # An accepted external effect that lowers HP moves the boundary later,
        # but the accepted cap still wins.
        body.traits.hp = _Gauge(1, 100000, 1)
        self.assertEqual(recovery_target_tick(body, receipt, 100), 15100)
        # A cheaper recovery moves the boundary earlier without replacing it.
        body.traits.hp = _Gauge(100, 100, 0)
        body.attributes.add("mental_reserve_units", 350000)
        self.assertEqual(recovery_target_tick(body, receipt, 100), 934)

    def test_corrupt_receipt_shape_is_rejected_without_repair(self):
        for payload in (
            {"sleep_id": "x"},
            {"sleep_id": "x", "kind": "unknown"},
            "not-a-mapping",
        ):
            with self.assertRaises(SleepReceiptError):
                validate_receipt(payload)
        body = _probe(180000)
        body.attributes.add(RECEIPT_ATTRIBUTE, {"sleep_id": "broken"})
        with self.assertRaises(SleepReceiptError):
            read_sleep_receipt(body)


class SleepEntryLifecycleTests(EvenniaTest):
    """Entry, continuation, replay and passive wake through the real clock."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        _full_gauges(self.player)
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        _RESULT_LEDGER.clear()

    def _companion(self, reserve=180000, posture=SleepPosture.AWAKE):
        npc = create_object(NPC, key=f"companion-{reserve}", location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        _full_gauges(npc)
        join_party(npc, self.player)
        write_fatigue_state(npc, reserve, posture)
        return npc

    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-"
        "capped-at-a-configured-maximum"
    )
    def test_recovery_entry_accepts_full_targets_at_zero_time(self):
        before = int(get_world_clock().tick)
        entry = enter_sleep(self.player)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertEqual(entry.accepted_seconds, 15000)
        self.assertIs(
            read_fatigue_state(self.player).posture, SleepPosture.VOLUNTARY
        )
        receipt = read_sleep_receipt(self.player)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.sleep_id, entry.sleep_id)
        self.assertEqual(receipt.target_tick, before + 15000)

    def test_already_recovered_entry_reconciles_awake_without_fabrication(self):
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)
        entry = enter_sleep(self.player)
        self.assertIsNone(entry.receipt)
        self.assertEqual(entry.requested_seconds, 0)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        outcome = begin_sleep(self.player)
        self.assertEqual(outcome.message, ALREADY_RECOVERED_MESSAGE)
        self.assertEqual(outcome.result.elapsed_seconds, 0)
        self.assertFalse(outcome.result.woke)

    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-"
        "capped-at-a-configured-maximum"
    )
    def test_explicit_duration_deadline_is_not_shortened_by_saturation(self):
        for key in ("hp", "mp", "sp"):
            gauge = getattr(self.player.traits, key)
            gauge.current = gauge.max
            gauge.rate = 0.0
        write_fatigue_state(self.player, 359988, SleepPosture.AWAKE)  # 1s to full
        before = int(get_world_clock().tick)
        entry = enter_sleep(self.player, mode=MODE_DURATION, seconds=7200)
        result = continue_sleep(self.player, entry)
        self.assertEqual(result.elapsed_seconds, 7200)
        self.assertEqual(int(get_world_clock().tick) - before, 7200)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertTrue(result.completed)
        self.assertFalse(result.partial)

    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-"
        "capped-at-a-configured-maximum"
    )
    def test_capped_recovery_wakes_at_the_limit_and_reports_partial(self):
        # The authored cap is 12 hours; a low test cap proves the same branch
        # without fabricating an unattainable gauge gap.
        with patch("world.rules.time_skip.MAX_SKIP_SECONDS", 100):
            entry = enter_sleep(self.player)
            self.assertEqual(entry.accepted_seconds, 100)
            self.assertTrue(entry.partial)
            result = continue_sleep(self.player, entry)
        self.assertEqual(result.elapsed_seconds, 100)
        self.assertTrue(result.partial)
        self.assertIn(PARTIAL_RECOVERY_MESSAGE, result.summary)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)

    def test_active_receipt_is_never_replaced(self):
        entry = enter_sleep(self.player, mode=MODE_DURATION, seconds=3600)
        target = read_sleep_receipt(self.player).target_tick
        with self.assertRaises(SleepRefused) as ctx:
            enter_sleep(self.player, mode=MODE_DURATION, seconds=1800)
        self.assertEqual(ctx.exception.code, "already_asleep")
        self.assertIn("sleep continue", ctx.exception.message)
        with self.assertRaises(SleepRefused):
            begin_sleep(
                self.player,
                mode=MODE_DURATION,
                seconds=1800,
                allow_continue=False,
            )
        self.assertEqual(read_sleep_receipt(self.player).target_tick, target)
        self.assertEqual(read_sleep_receipt(self.player).sleep_id, entry.sleep_id)

    def test_concurrent_entry_wins_over_a_stale_preflight(self):
        receipt = SleepReceipt(
            sleep_id="competing-plan",
            body_id=int(self.player.pk),
            owner_id=int(self.player.pk),
            kind="voluntary",
            mode=MODE_DURATION,
            entry_tick=int(get_world_clock().tick),
            target_tick=int(get_world_clock().tick) + 3600,
            limit_tick=int(get_world_clock().tick) + 3600,
            settled_through_tick=int(get_world_clock().tick),
            revision=0,
            state="sleeping",
            accepted_seconds=3600,
            partial=False,
            entry_operation_id="competing-plan",
        )

        def _competing(entities):
            body = entities[0]
            state = read_fatigue_state(body)
            write_fatigue_state(
                body, state.reserve_units, SleepPosture.VOLUNTARY
            )
            write_sleep_receipt(body, receipt)

        with patch(
            "world.rules.time_skip._lock_members", side_effect=_competing
        ), self.assertRaises(SleepRefused) as ctx:
            enter_sleep(self.player, mode=MODE_DURATION, seconds=1800)
        self.assertEqual(ctx.exception.code, "already_asleep")
        # This request wrote nothing: its pre-write snapshots restored the
        # simulated interleaving, so no second plan survives from it.
        self.assertIsNone(read_sleep_receipt(self.player))
        self.assertIs(
            read_fatigue_state(self.player).posture, SleepPosture.AWAKE
        )

    def test_owner_wakes_while_possessed_companion_waits(self):
        companion = self._companion()
        entry = enter_sleep(self.player)
        self.assertTrue(entry.handoff_offered)
        enter_possession(self.player, companion)
        before = int(get_world_clock().tick)
        result = advance_wait(companion, 20000)
        self.assertEqual(result.elapsed_seconds, 15000)
        self.assertEqual(int(get_world_clock().tick) - before, 15000)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertEqual(
            current_possession(self.player)["npc_dbid"], int(companion.pk)
        )
        self.assertIs(self.session.puppet, companion)
        self.assertEqual(read_sleep_receipt(self.player).state, "completed")

    @covers_requirement(
        "party-time-settlement::per-member-mental-time-uses-actual-posture-and-"
        "activity"
    )
    def test_owner_wakes_while_another_companion_sleeps(self):
        second = self._companion(324000)
        owner_target = 1000  # 348000 reserve at 12 units/second
        write_fatigue_state(self.player, 348000, SleepPosture.AWAKE)
        enter_sleep(self.player)
        enter_possession(self.player, second)
        entry = enter_sleep(second)
        before = int(get_world_clock().tick)
        continue_sleep(second, entry)
        self.assertEqual(int(get_world_clock().tick) - before, owner_target)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertIs(read_fatigue_state(second).posture, SleepPosture.VOLUNTARY)
        self.assertEqual(
            current_possession(self.player)["npc_dbid"], int(second.pk)
        )

    def test_duration_sleeper_stays_asleep_while_reserve_saturates(self):
        companion = self._companion()
        write_fatigue_state(self.player, 359988, SleepPosture.AWAKE)
        enter_sleep(self.player, mode=MODE_DURATION, seconds=7200)
        advance_wait(companion, 3600)
        self.assertEqual(
            read_fatigue_state(self.player).reserve_units, 360000
        )
        self.assertIs(
            read_fatigue_state(self.player).posture, SleepPosture.VOLUNTARY
        )
        advance_wait(companion, 10000)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertEqual(read_sleep_receipt(self.player).state, "completed")

    def test_retry_after_reload_returns_the_committed_result(self):
        entry = enter_sleep(self.player)
        first = continue_sleep(
            self.player, entry, operation_id="synthetic-sleep-reload"
        )
        tick_after = int(get_world_clock().tick)
        _RESULT_LEDGER.clear()  # process reload: only the durable receipt survives
        second = continue_sleep(
            self.player, entry, operation_id="synthetic-sleep-reload"
        )
        self.assertEqual(int(get_world_clock().tick), tick_after)
        self.assertTrue(second.replayed)
        self.assertEqual(second.elapsed_seconds, first.elapsed_seconds)
        self.assertEqual(second.sleep_id, first.sleep_id)
        self.assertEqual(second.events, ())

    def test_stale_revision_rejects_without_advancing(self):
        enter_sleep(self.player)
        before = int(get_world_clock().tick)
        with self.assertRaises(SleepRefused) as ctx:
            continue_sleep(self.player, expected_revision=99)
        self.assertEqual(ctx.exception.code, "stale_sleep")
        self.assertEqual(int(get_world_clock().tick), before)

    def test_missing_receipt_is_never_repaired_or_woken(self):
        write_fatigue_state(self.player, 180000, SleepPosture.VOLUNTARY)
        companion = self._companion()
        before = int(get_world_clock().tick)
        advance_wait(companion, 600)
        self.assertEqual(int(get_world_clock().tick) - before, 600)
        self.assertEqual(
            read_fatigue_state(self.player).reserve_units, 180000
        )
        self.assertIs(
            read_fatigue_state(self.player).posture, SleepPosture.VOLUNTARY
        )
        self.assertIsNone(read_sleep_receipt(self.player))
        with self.assertRaises(SleepRefused) as ctx:
            continue_sleep(self.player)
        self.assertEqual(ctx.exception.code, "missing_sleep_receipt")

    def test_corrupt_receipt_is_never_refilled_or_woken(self):
        write_fatigue_state(self.player, 180000, SleepPosture.VOLUNTARY)
        self.player.attributes.add(RECEIPT_ATTRIBUTE, {"sleep_id": "broken"})
        companion = self._companion()
        before = int(get_world_clock().tick)
        # A corrupt record fails the whole advance closed before any resource,
        # posture or clock write: nothing is repaired, refilled or woken.
        with self.assertRaises(SleepReceiptError):
            advance_wait(companion, 600)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertEqual(
            read_fatigue_state(self.player).reserve_units, 180000
        )
        self.assertIs(
            read_fatigue_state(self.player).posture, SleepPosture.VOLUNTARY
        )
        with self.assertRaises(SleepRefused) as ctx:
            continue_sleep(self.player)
        self.assertEqual(ctx.exception.code, "corrupt_sleep_receipt")

    def test_late_failure_restores_tick_reserve_posture_and_receipt(self):
        write_fatigue_state(self.player, 348000, SleepPosture.AWAKE)
        enter_sleep(self.player)
        companion = self._companion()
        before = int(get_world_clock().tick)
        with patch(
            "world.rules.clock._schedule_voluntary_wake",
            side_effect=RuntimeError("synthetic late failure"),
        ), self.assertRaises(RuntimeError):
            advance_wait(companion, 5000)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertEqual(
            read_fatigue_state(self.player).reserve_units, 348000
        )
        self.assertIs(
            read_fatigue_state(self.player).posture, SleepPosture.VOLUNTARY
        )
        receipt = read_sleep_receipt(self.player)
        self.assertEqual(receipt.state, "sleeping")
        self.assertEqual(receipt.revision, 0)
        self.assertEqual(receipt.settled_through_tick, before)

    def test_two_continuations_at_one_revision_commit_once(self):
        entry = enter_sleep(self.player)
        first = continue_sleep(
            self.player, entry, expected_revision=0, operation_id="synthetic-c1"
        )
        tick_after = int(get_world_clock().tick)
        self.assertTrue(first.completed)
        with self.assertRaises(SleepRefused) as ctx:
            continue_sleep(
                self.player,
                entry,
                expected_revision=0,
                operation_id="synthetic-c2",
            )
        self.assertEqual(ctx.exception.code, "stale_sleep")
        self.assertEqual(int(get_world_clock().tick), tick_after)

    def test_indivisible_action_subdivides_only_at_the_voluntary_deadline(self):
        from world.rules.mental_time import indivisible_plan

        companion = self._companion(360000)
        write_fatigue_state(self.player, 348000, SleepPosture.AWAKE)  # 1000s
        entry = enter_sleep(self.player)
        before = int(get_world_clock().tick)
        clock = get_world_clock()
        clock.advance(
            7200,
            AdvanceSource.SKIP,
            (self.player, companion),
            mental=indivisible_plan((self.player, companion)),
        )
        self.assertEqual(int(get_world_clock().tick) - before, 7200)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertIs(read_sleep_receipt(self.player).state, "completed")
        self.assertEqual(read_sleep_receipt(self.player).sleep_id, entry.sleep_id)
        # 1000s sleeping then 6200s at the ordinary awake rate (-4/s).
        self.assertEqual(read_fatigue_state(self.player).reserve_units, 335200)
        # The full action duration still settles the awake companion.
        self.assertEqual(read_fatigue_state(companion).reserve_units, 331200)

    def test_indivisible_boundary_uses_pre_action_gauges(self):
        from world.rules.mental_time import indivisible_plan

        companion = self._companion(360000)
        mp = self.player.traits.mp
        mp.base = 1200
        mp.current = 0
        mp.rate = 1.0
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)
        entry = enter_sleep(self.player)
        self.assertEqual(entry.accepted_seconds, 1200)
        from world.rules.sleep_receipt import next_sleep_offset

        clock = get_world_clock()
        self.assertEqual(
            next_sleep_offset(self.player, read_sleep_receipt(self.player), clock.tick),
            1200,
        )
        clock.advance(
            1800,
            AdvanceSource.SKIP,
            (self.player, companion),
            mental=indivisible_plan((self.player, companion)),
        )
        # The action's own gauge regeneration must not move the boundary: the
        # body sleeps its accepted 1200 seconds and stays awake for 600.
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertEqual(read_sleep_receipt(self.player).state, "completed")
        self.assertEqual(read_fatigue_state(self.player).reserve_units, 357600)

    def test_real_sleep_command_accepts_an_explicit_duration(self):
        from commands.skip import CmdSleep

        command = CmdSleep()
        command.caller = self.player
        command.args = "2h"
        before = int(get_world_clock().tick)
        with patch.object(self.player, "msg"):
            command.func()
        self.assertEqual(int(get_world_clock().tick) - before, 7200)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertEqual(read_sleep_receipt(self.player).state, "completed")

    def test_real_party_sleep_command_enters_without_spending_time(self):
        from commands.skip import CmdSleep

        companion = self._companion()
        command = CmdSleep()
        command.caller = self.player
        command.args = "all"
        before = int(get_world_clock().tick)
        with patch.object(self.player, "msg"):
            command.func()
        self.assertEqual(int(get_world_clock().tick), before)
        for member in (self.player, companion):
            self.assertIs(
                read_fatigue_state(member).posture, SleepPosture.VOLUNTARY
            )
            self.assertIsNotNone(read_sleep_receipt(member))

    def test_forced_depletion_creates_a_threshold_receipt(self):
        write_fatigue_state(self.player, 1200, SleepPosture.AWAKE)
        result = advance_wait(self.player, 600)
        self.assertEqual(result.elapsed_seconds, 300)
        receipt = read_sleep_receipt(self.player)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.kind, "forced")
        self.assertEqual(receipt.mode, "forced_threshold")
        self.assertEqual(
            receipt.accepted_seconds,
            forced_wake_seconds(self.player),
        )


class PartySleepEntryTests(EvenniaTest):
    """Explicit all-party entry: preflight, atomicity, repetition, remote scope."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        _full_gauges(self.player)
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)

    def _member(self, key, *, room=None, reserve=180000, posture=SleepPosture.AWAKE):
        npc = create_object(NPC, key=key, location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        _full_gauges(npc)
        join_party(npc, self.player)
        write_fatigue_state(npc, reserve, posture)
        if room is not None:
            npc.location = room
        return npc

    def test_party_entry_commits_awake_bodies_and_retains_existing_plans(self):
        awake = self._member("清醒同伴")
        forced = self._member("強制沉睡", reserve=0, posture=SleepPosture.FORCED)
        remote = self._member("遠端同伴", room=self.room2)
        before = int(get_world_clock().tick)
        outcome = enter_party_sleep(self.player, operation_id="synthetic-party")
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertEqual(len(outcome.entries), 2)
        for member in (self.player, awake):
            self.assertIs(
                read_fatigue_state(member).posture, SleepPosture.VOLUNTARY
            )
            self.assertIsNotNone(read_sleep_receipt(member))
        self.assertIs(
            read_fatigue_state(forced).posture, SleepPosture.FORCED
        )
        self.assertIsNone(read_sleep_receipt(forced))
        self.assertIs(read_fatigue_state(remote).posture, SleepPosture.AWAKE)
        self.assertIsNone(read_sleep_receipt(remote))
        first_ids = {entry.member.pk: entry.sleep_id for entry in outcome.entries}
        repeat = enter_party_sleep(self.player, operation_id="synthetic-party")
        self.assertEqual(
            {entry.member.pk: entry.sleep_id for entry in repeat.entries},
            first_ids,
        )

    def test_existing_voluntary_receipt_keeps_its_identity(self):
        sleeper = self._member("已入睡同伴")
        entry = enter_sleep(sleeper)
        outcome = enter_party_sleep(self.player)
        self.assertNotIn(
            sleeper.pk, [item.member.pk for item in outcome.entries]
        )
        self.assertEqual(read_sleep_receipt(sleeper).sleep_id, entry.sleep_id)
        self.assertIs(
            read_fatigue_state(sleeper).posture, SleepPosture.VOLUNTARY
        )

    def test_one_ineligible_member_refuses_the_whole_operation(self):
        plain = self._member("倒地同伴")
        plain.traits.hp.current = 0
        before = int(get_world_clock().tick)
        with self.assertRaises(SleepRefused):
            enter_party_sleep(self.player)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertIs(
            read_fatigue_state(self.player).posture, SleepPosture.AWAKE
        )
        self.assertIsNone(read_sleep_receipt(self.player))

    def test_late_member_write_failure_restores_every_body(self):
        companion = self._member("同伴")
        from world.rules import sleep_receipt as receipt_module

        real_write = receipt_module.write_sleep_receipt
        calls = {"count": 0}

        def _fail_on_second(entity, receipt):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("synthetic second write failure")
            return real_write(entity, receipt)

        with patch(
            "world.rules.time_skip.write_sleep_receipt",
            side_effect=_fail_on_second,
        ), self.assertRaises(RuntimeError):
            enter_party_sleep(self.player)
        for member in (self.player, companion):
            self.assertIs(
                read_fatigue_state(member).posture, SleepPosture.AWAKE
            )
            self.assertIsNone(read_sleep_receipt(member))

    @covers_requirement(
        "party-time-settlement::skip-advances-settle-the-present-party"
    )
    def test_skipping_alone_selects_nobody_for_sleep(self):
        companion = self._member("同伴")
        advance_wait(self.player, 60)
        self.assertIs(
            read_fatigue_state(companion).posture, SleepPosture.AWAKE
        )
        self.assertIsNone(read_sleep_receipt(companion))
        self.assertIsNone(read_sleep_receipt(self.player))
