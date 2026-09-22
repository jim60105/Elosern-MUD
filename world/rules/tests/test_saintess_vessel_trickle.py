"""Data-contract test: saintess vessel trickle and preset integration smoke contract

Behavior suite for 聖光涓流 (saintess-vessel D2): the vessel holder's idle
arousal never leaves the 微興奮～中等 band on the world clock, moves at most
±1 per advance, and re-arms after ordinary decay re-entry; non-holders are
byte-identical. Shipped preset/skill keys appear here because the task 5.3
end-to-end smoke activates the shipped Saintess preset and casts the shipped
ceremonial ward through the real action pipeline.

The direction draw is a stateless crc32(id:tick) hash (design D2b), so every
advance outcome is deterministic; where an assertion needs a specific draw
(e.g. proving the step writes again after decay), the test selects the
advance whose resulting tick yields that draw instead of rolling dice.
"""

import zlib
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase, EvenniaTest

from typeclasses.characters import PlayerCharacter

from world.rules.action import ActionRequest, ActionResolver
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.pleasure import apply_pleasure_gain
from world.rules.targeting import RoomActionContext
from world.rules.tests.combat_fixtures import grant_lineage

VESSEL_KEY = "saintess_vessel"
WARD_KEY = "sanctified_ward"
PRESET_KEY = "violet_altoria"
GRANT_EVENT = "saintess_vessel_granted"
BAND_FLOOR = 15
BAND_CEILING = 59


def _trickle_draw(entity, resulting_tick: int) -> int:
    """The stateless crc32 direction the trickle step computes (D2b)."""
    identity = str(getattr(entity, "id", None) or getattr(entity, "key", entity))
    return zlib.crc32(f"{identity}:{resulting_tick}".encode("utf-8")) % 2


def _first_down_draw_tick(entity, from_tick: int) -> int:
    """Return the first tick after ``from_tick`` whose draw is minus."""
    tick = from_tick
    while _trickle_draw(entity, tick) != 0:
        tick += 1
    return tick


def _first_up_draw_tick(entity, from_tick: int) -> int:
    """Return the first tick after ``from_tick`` whose draw is plus."""
    tick = from_tick
    while _trickle_draw(entity, tick) != 1:
        tick += 1
    return tick


def _holder(key: str = "saintess holder"):
    entity = create_object(PlayerCharacter, key=key)
    entity.race = "human"
    entity.apply_race_baseline()
    entity.db.skills = {"active": [], "passive": [VESSEL_KEY]}
    return entity


class SaintessTrickleBehaviorTests(EvenniaTestCase):
    """The 聖光涓流 band guarantees, determinism, and non-holder neutrality."""

    def test_fully_idle_holder_is_pinned_to_fifteen_in_one_advance(self):
        holder = _holder()
        holder.sexual.pleasure.base = 0
        WorldClock(tick=0).advance(30, AdvanceSource.SKIP, [holder])
        self.assertEqual(holder.sexual.pleasure.base, 15)
        self.assertEqual(holder.sexual.arousal.level, "微興奮")

    def test_mid_band_advances_stay_in_band_move_at_most_one_and_visibly_move(self):
        holder = _holder()
        holder.sexual.pleasure.base = 30
        clock = WorldClock(tick=0)
        readings = [30]
        for _ in range(12):
            clock.advance(6, AdvanceSource.SKIP, [holder])
            readings.append(holder.sexual.pleasure.base)
        for index in range(1, len(readings)):
            self.assertGreaterEqual(readings[index], BAND_FLOOR, readings)
            self.assertLessEqual(readings[index], BAND_CEILING, readings)
            self.assertLessEqual(abs(readings[index] - readings[index - 1]), 1)
        # The gauge visibly moves: the first advance from the interior 30
        # always lands on 29 or 31 (no endpoint zero-collapse exists there),
        # so at least one reading differs from the starting value.
        self.assertTrue(any(reading != 30 for reading in readings[1:]), readings)

    def test_fluctuation_direction_follows_the_stateless_tick_hash(self):
        # The design pins the direction to the crc32(id:tick) hash (D2b), so
        # BOTH signed outcomes must be observable for one entity: select a
        # plus-draw advance and a minus-draw advance from an interior value
        # and assert the exact signed move — a constant-direction
        # implementation cannot satisfy both.
        holder = _holder()
        holder.sexual.pleasure.base = 30
        clock = WorldClock(tick=0)
        up_tick = _first_up_draw_tick(holder, clock.tick + 1)
        clock.advance(up_tick - clock.tick, AdvanceSource.SKIP, [holder])
        self.assertEqual(holder.sexual.pleasure.base, 31)
        down_tick = _first_down_draw_tick(holder, clock.tick + 1)
        clock.advance(down_tick - clock.tick, AdvanceSource.SKIP, [holder])
        self.assertEqual(holder.sexual.pleasure.base, 30)

    def test_floor_oscillation_never_reads_calm(self):
        # D2b's binding guarantee at the floor: never below 15 after any
        # settlement, at most ±1 per advance, and the level never leaves
        # 微興奮 (no stateless draw can promise strict 15↔16 alternation).
        holder = _holder()
        holder.sexual.pleasure.base = 15
        clock = WorldClock(tick=0)
        previous = 15
        for _ in range(24):
            clock.advance(6, AdvanceSource.SKIP, [holder])
            self.assertGreaterEqual(holder.sexual.pleasure.base, BAND_FLOOR)
            self.assertLessEqual(
                abs(holder.sexual.pleasure.base - previous), 1
            )
            previous = holder.sexual.pleasure.base
            self.assertNotEqual(holder.sexual.arousal.level, "平靜")

    def test_holder_at_seventy_decays_ordinarily_and_rearms_on_band_reentry(self):
        holder = _holder()
        holder.sexual.pleasure.base = 70
        clock = WorldClock(tick=0)
        # At or above 高度 the step is a no-op: a short advance with no decay
        # due must not move the gauge at all (no writer call).
        with patch("world.rules.pleasure.apply_pleasure_gain") as gain_mock:
            clock.advance(6, AdvanceSource.SKIP, [holder])
        gain_mock.assert_not_called()
        self.assertEqual(holder.sexual.pleasure.base, 70)
        # One full decay interval: 高度 60-84 crosses one band to the 中等
        # ceiling region; the holder floor keeps her at 59, then the step
        # clamps the post-decay draw inside [15, 59].
        clock.advance(1800, AdvanceSource.SKIP, [holder])
        self.assertIn(holder.sexual.pleasure.base, (58, 59))
        # Re-entry re-arms the step: pick the next advance whose draw is
        # minus, so the write (not a zero-collapse) is what we observe.
        at_reentry = holder.sexual.pleasure.base
        down_tick = _first_down_draw_tick(holder, clock.tick + 1)
        delta = down_tick - clock.tick
        clock.advance(delta, AdvanceSource.SKIP, [holder])
        self.assertEqual(holder.sexual.pleasure.base, at_reentry - 1)
        self.assertGreaterEqual(holder.sexual.pleasure.base, BAND_FLOOR)

    def test_retried_failed_advance_recomputes_the_identical_single_apply_step(self):
        holder = _holder()
        holder.sexual.pleasure.base = 30
        clock = WorldClock(tick=100)
        real_gain = apply_pleasure_gain
        calls = []

        def recording_gain(entity, gain, *, stimulus=True):
            calls.append((entity, gain, stimulus))
            return real_gain(entity, gain, stimulus=stimulus)

        with (
            patch("world.rules.pleasure.apply_pleasure_gain", side_effect=recording_gain),
        ):
            with (
                patch(
                    "world.rules.clock._settle_boundary_stages",
                    side_effect=RuntimeError("simulated post-trickle failure"),
                ),
                self.assertRaises(RuntimeError),
            ):
                clock.advance(6, AdvanceSource.SKIP, [holder])
            # The failed attempt applied the trickle exactly once and the
            # advance rollback restored the holder's gauge.
            self.assertEqual(len(calls), 1)
            self.assertFalse(calls[0][2])
            self.assertEqual(holder.sexual.pleasure.base, 30)
            # The retry recomputes the identical draw (same resulting tick,
            # same restored state) and applies the single-apply value: both
            # attempts made the same one call.
            clock.advance(6, AdvanceSource.SKIP, [holder])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], calls[1][0])
        self.assertEqual(calls[0][1], calls[1][1])
        self.assertEqual(calls[0][2], calls[1][2])
        self.assertEqual(holder.sexual.pleasure.base, 30 + calls[1][1])

    def test_non_holder_settlement_is_byte_identical(self):
        plain = create_object(PlayerCharacter, key="non-holder trickle")
        plain.race = "human"
        plain.apply_race_baseline()
        plain.db.skills = {"active": [], "passive": []}
        plain.sexual.pleasure.base = 20

        def sexual_record(entity):
            return entity.attributes.get(
                "sexual_traits", default={}, category="traits"
            )

        before = sexual_record(plain)
        with patch("world.rules.pleasure.apply_pleasure_gain") as gain_mock:
            clock = WorldClock(tick=0)
            for _ in range(6):
                clock.advance(6, AdvanceSource.SKIP, [plain])
        gain_mock.assert_not_called()
        self.assertEqual(sexual_record(plain), before)
        self.assertEqual(plain.sexual.pleasure.base, 20)

    def test_non_holder_decay_still_crosses_to_the_calm_floor(self):
        # The unchanged 平靜-floor decay path: a non-holder at 20 (微興奮)
        # crossing one full decay interval lands on 14 (the 微興奮 floor minus
        # one) exactly as before this change — never the holder's 15 floor.
        plain = create_object(PlayerCharacter, key="non-holder decay trickle")
        plain.race = "human"
        plain.apply_race_baseline()
        plain.db.skills = {"active": [], "passive": []}
        plain.sexual.pleasure.base = 20
        WorldClock(tick=0).advance(1800, AdvanceSource.SKIP, [plain])
        self.assertEqual(plain.sexual.pleasure.base, 14)
        self.assertEqual(plain.sexual.arousal.level, "平靜")

    @covers_requirement("saintess-vessel::saintess-trickle-pins-the-holder-s-idle-arousal-inside-the-idle-band")
    def test_idle_trickle_never_opens_a_climax_below_the_gate(self):
        # F5: a holder parked at 接近 after an earlier 極限 spike is advanced
        # inside the band; the non-stimulus trickle write must not promote
        # the phase and must not stage any extension.
        holder = _holder()
        holder.sexual.pleasure.base = 15
        holder.sexual.climax_phase.value = "接近"
        holder.sexual.pleasure.base = 30
        clock = WorldClock(tick=0)
        for _ in range(12):
            clock.advance(6, AdvanceSource.SKIP, [holder])
            self.assertEqual(holder.sexual.climax_phase.level, "接近")
            self.assertEqual(holder.sexual.pending_climax_extension, 0)


class SaintessVesselPresetSmokeTests(EvenniaTest):
    """Task 5.3 end-to-end: preset grant, clock trickle, ceremonial ward cast."""

    def test_preset_activation_trickle_and_ward_cast_smoke(self):
        holder = self.char1
        holder.race = "human"
        holder.apply_race_baseline()
        self.account.at_post_create_character(holder)

        from world.rules.character_creation import (
            CharacterCreationRequest,
            activate_player_character,
        )

        with (
            patch("world.rules.character_creation.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            activate_player_character(
                self.account,
                holder,
                CharacterCreationRequest(mode="preset", preset_key=PRESET_KEY),
            )
        grant_events = [
            call.args[0] for call in info.call_args_list if call.args
        ]
        self.assertEqual(grant_events, [GRANT_EVENT])
        (event,), kwargs = info.call_args
        self.assertEqual(kwargs["context"]["source"], "preset")
        self.assertEqual(kwargs["context"]["passive"], VESSEL_KEY)
        self.assertIn(VESSEL_KEY, holder.db.skills["passive"])

        # 聖光涓流: a freshly activated holder is at zero — one advance pins
        # her to the 微興奮 floor, later advances stay inside the band.
        holder.sexual.pleasure.base = 0
        clock = WorldClock(tick=0)
        clock.advance(30, AdvanceSource.SKIP, [holder])
        self.assertEqual(holder.sexual.pleasure.base, 15)

        # At 中等 arousal the holder casts the shipped ceremonial ward; the
        # cast mounts the ward's HOT with the one-time tier grace 1 + 0.1x2.
        holder.sexual.pleasure.base = 40
        self.assertEqual(holder.sexual.arousal.value, 2)
        target = self.char2
        target.race = "human"
        target.apply_race_baseline()
        grant_lineage(holder, [WARD_KEY], passive=[VESSEL_KEY])
        holder.traits.mp.current = 200
        result = ActionResolver.resolve(
            ActionRequest(holder, WARD_KEY, [target], RoomActionContext(self.room1))
        )
        self.assertEqual(
            result.outcome,
            "success",
            f"{result.reason}: {result.detail}",
        )
        ward = target.buffs.all[WARD_KEY]
        self.assertAlmostEqual(ward.snapshot_grace_multiplier, 1.2, places=2)

        # Post-cast advances keep the gauge pinned inside the band, moving
        # ±1 per advance from the interior 40 (no zero-collapse endpoints).
        readings = [holder.sexual.pleasure.base]
        for _ in range(3):
            clock.advance(6, AdvanceSource.SKIP, [holder])
            readings.append(holder.sexual.pleasure.base)
        for index in range(1, len(readings)):
            self.assertGreaterEqual(readings[index], BAND_FLOOR)
            self.assertLessEqual(readings[index], BAND_CEILING)
            self.assertEqual(abs(readings[index] - readings[index - 1]), 1,
                             readings)