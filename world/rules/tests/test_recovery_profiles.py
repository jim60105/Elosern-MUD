"""Synthetic behavior tests for sustained recovery rate profiles and timed defense riders.

Covers requirements from openspec change light-sustained-recovery:
- buff-handler-integration::recovery-profiles-restore-living-recipients-with-explicit-snapshot-and-live-inputs
- buff-handler-integration::finite-recovery-ticks-and-refresh-are-deterministic-across-elapsed-time-partitions
- buff-handler-integration::buff-verification-establishes-mechanics-rather-than-catalog-correspondence
"""
import copy
import math
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    RecoveryRatePolicy,
    apply_buff,
    entity_active_buffs,
    get_recovery_policy,
    load_buff_definitions,
    remove_by_selector,
    tick_buffs,
)
from world.rules.action import ActionRequest, ActionResolver, PendingEffect
from world.rules.clock import WorldClock, AdvanceSource, CLOCK_YAML
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.sexual_state import EXPOSURE_LEVELS
from world.rules.stored_sexual_reads import StoredLevel


class RecoveryProfileBehaviorTests(EvenniaTestCase):
    """Behavior tests for sustained recovery profiles and timed defense markers."""

    def setUp(self):
        super().setUp()
        self.caster = create_object(PlayerCharacter, key="test-caster")
        self.recipient = create_object(PlayerCharacter, key="test-recipient")
        self.caster.race = "human"
        self.recipient.race = "human"
        self.caster.apply_race_baseline()
        self.recipient.apply_race_baseline()
        self.caster.traits.hp.base = 100
        self.caster.traits.hp.current = 100
        self.recipient.traits.hp.base = 100
        self.recipient.traits.hp.current = 50

    def _register_synth_buff(self, definition: BuffDefinition):
        patcher = patch.dict(BUFF_DEFINITIONS, {definition.key: definition}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return definition

    def test_malformed_recovery_policies_rejected_at_definition_load(self):
        """Mutually exclusive fixed/recovery rate validation rejects invalid policies."""
        import tempfile
        from pathlib import Path

        def _try_load(yaml_content: str):
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
                f.write(yaml_content)
                f.flush()
                tmp_path = Path(f.name)
            try:
                load_buff_definitions(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)

        # Both delta and recovery
        with self.assertRaises(ValueError):
            _try_load("""
- key: bad_both
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      target: hp
      delta: 5
      recovery: {base: 12}
""")

        # Neither delta nor recovery
        with self.assertRaises(ValueError):
            _try_load("""
- key: bad_none
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      target: hp
""")

        # Target not hp
        with self.assertRaises(ValueError):
            _try_load("""
- key: bad_target
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      recovery: {target: mp, base: 10}
""")

        # Negative base
        with self.assertRaises(ValueError):
            _try_load("""
- key: bad_base
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      recovery: {base: -5}
""")

        # Non-multiple of settlement quantum (quantum is 10)
        with self.assertRaises(ValueError):
            _try_load("""
- key: bad_quantum
  duration: 30
  tick_interval: 7
  modifiers:
    rate:
      recovery: {base: 12}
""")

    def test_live_recipient_and_captured_caster_inputs_differ(self):
        """Scenario: Live recipient and captured caster inputs differ.

        WHEN recipient exposure changes after application and the caster later changes equipment or is deleted
        THEN the next tick reflects new recipient exposure but the original caster modifier and does not require the caster object
        """
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_sustained_recovery",
                duration=30,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 12,
                            "exposure_percent_per_ordinal": 0.1,
                        }
                    }
                },
            )
        )
        # Recipient exposure ordinal 1 ("低" or equivalent)
        # EXPOSURE_LEVELS: index 1
        self.recipient.sexual.exposure.value = EXPOSURE_LEVELS[1]

        # Caster snapshot heal_gain +20%, grace 1.0
        apply_buff(
            self.recipient,
            "synth_sustained_recovery",
            snapshot_heal_gain="+20%",
            snapshot_grace_multiplier=1.0,
            source_pk=self.caster.pk,
        )

        # Before tick, recipient HP is 50/100.
        # Now change recipient exposure to index 3 ("高")
        self.recipient.sexual.exposure.value = EXPOSURE_LEVELS[3]

        # Delete / clear caster
        self.caster.delete()
        self.caster = None

        # Tick 10 seconds:
        # base = 12
        # recipient ordinal = 3 -> (1 + 0.1 * 3) = 1.3
        # snapshot heal_gain = 20% -> (1 + 0.2) = 1.2
        # snapshot grace = 1.0
        # raw amount = floor(12 * 1.3 * 1.2 * 1.0) = floor(18.72) = 18
        hp_before = self.recipient.traits.hp.current
        records = tick_buffs(self.recipient, 10)
        self.assertEqual(records, ())  # Recovery ticks emit no damaging TickRecords
        self.assertEqual(self.recipient.traits.hp.current, hp_before + 18)

    def test_no_revival_or_overflow(self):
        """Scenario: No revival or overflow.

        WHEN a tick addresses a dead recipient or a living recipient near maximum HP
        THEN dead HP is unchanged and living HP never exceeds its maximum
        """
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_recovery_clamp",
                duration=30,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 20,
                        }
                    }
                },
            )
        )

        # 1. Dead recipient (HP = 0)
        self.recipient.traits.hp.current = 0
        apply_buff(self.recipient, "synth_recovery_clamp")
        tick_buffs(self.recipient, 10)
        self.assertEqual(self.recipient.traits.hp.current, 0)

        # 2. Living recipient near max HP (HP = 95, max = 100)
        self.recipient.traits.hp.current = 95
        # base is 20, exposure 0 -> amount = 20, gap = 5 -> heals 5 to 100
        tick_buffs(self.recipient, 10)
        self.assertEqual(self.recipient.traits.hp.current, 100)

        # Further tick at 100 does not overflow
        tick_buffs(self.recipient, 10)
        self.assertEqual(self.recipient.traits.hp.current, 100)

    def test_finite_recovery_ticks_and_timing_partitions(self):
        """Scenario: Final tick precedes expiration.

        WHEN world time advances 30 seconds at once or in three equal segments
        THEN exactly three recovery ticks occur with no application-time tick and no fourth tick at 40 seconds
        """
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_timing_ward",
                duration=30,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 10,
                        }
                    }
                },
            )
        )

        # Case A: Three equal segments of 10s
        self.recipient.traits.hp.current = 10
        apply_buff(self.recipient, "synth_timing_ward")
        self.assertEqual(self.recipient.traits.hp.current, 10)  # No tick at application!

        # Advance 10s: tick 1 (elapsed 10)
        tick_buffs(self.recipient, 10)
        self.assertEqual(self.recipient.traits.hp.current, 20)

        # Advance 10s: tick 2 (elapsed 20)
        tick_buffs(self.recipient, 10)
        self.assertEqual(self.recipient.traits.hp.current, 30)

        # Advance 10s: tick 3 (elapsed 30)
        tick_buffs(self.recipient, 10)
        self.assertEqual(self.recipient.traits.hp.current, 40)

        # At 30s elapsed with duration 30, remaining_seconds is now 0 (expired)
        self.assertNotIn("synth_timing_ward", entity_active_buffs(self.recipient))

        # Further advance of 10s (elapsed 40) produces no fourth tick
        tick_buffs(self.recipient, 10)
        self.assertEqual(self.recipient.traits.hp.current, 40)

        # Case B: Advance 30 seconds at once
        self.recipient.traits.hp.current = 10
        apply_buff(self.recipient, "synth_timing_ward")
        tick_buffs(self.recipient, 30)
        self.assertEqual(self.recipient.traits.hp.current, 40)  # exactly 3 ticks (30 HP)

    def test_refresh_and_reload_preserve_schedule(self):
        """Scenario: Refresh and reload preserve schedule.

        WHEN a partially elapsed profile is refreshed and refetched
        THEN only the new three-tick schedule runs using the new source snapshots
        """
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_recast_recovery",
                duration=30,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 10,
                        }
                    }
                },
            )
        )
        self.recipient.traits.hp.current = 10

        # Cast 1: base 10, snapshot heal_gain 0% -> 10 HP per tick
        apply_buff(
            self.recipient,
            "synth_recast_recovery",
            snapshot_heal_gain="+0%",
            snapshot_grace_multiplier=1.0,
        )

        # Advance 15s: 1 tick fires at 10s (HP: 10 + 10 = 20), 5s accumulated in tick remainder, remaining 15s
        tick_buffs(self.recipient, 15)
        self.assertEqual(self.recipient.traits.hp.current, 20)

        # Recast: refreshed with new snapshot heal_gain +50% -> 15 HP per tick!
        apply_buff(
            self.recipient,
            "synth_recast_recovery",
            snapshot_heal_gain="+50%",
            snapshot_grace_multiplier=1.0,
        )

        # Verify buff state refetched from recipient
        active_buff = self.recipient.buffs.all["synth_recast_recovery"]
        self.assertEqual(active_buff.remaining_seconds, 30)
        self.assertEqual(active_buff.tick_elapsed_seconds, 0)
        self.assertEqual(active_buff.snapshot_heal_gain, 50.0)

        # Now advance exactly 30s in 10s steps: should fire 3 ticks of 15 HP each
        tick_buffs(self.recipient, 10)  # tick 1 of new cast
        self.assertEqual(self.recipient.traits.hp.current, 35)

        tick_buffs(self.recipient, 10)  # tick 2 of new cast
        self.assertEqual(self.recipient.traits.hp.current, 50)

        tick_buffs(self.recipient, 10)  # tick 3 of new cast
        self.assertEqual(self.recipient.traits.hp.current, 65)

        # Buff is now expired
        self.assertNotIn("synth_recast_recovery", entity_active_buffs(self.recipient))
        tick_buffs(self.recipient, 10)
        self.assertEqual(self.recipient.traits.hp.current, 65)

    def test_removal_cancels_recovery(self):
        """Scenario: Removal cancels recovery.

        WHEN the buff is removed before its next due tick
        THEN no later tick restores HP
        """
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_removal_recovery",
                duration=30,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 15,
                        }
                    }
                },
            )
        )
        self.recipient.traits.hp.current = 20
        apply_buff(self.recipient, "synth_removal_recovery")

        # Advance 5s (halfway to first tick)
        tick_buffs(self.recipient, 5)
        self.assertEqual(self.recipient.traits.hp.current, 20)

        # Remove buff before 10s tick
        removed_count = remove_by_selector(self.recipient, "synth_removal_recovery")
        self.assertEqual(removed_count, 1)
        self.assertNotIn("synth_removal_recovery", entity_active_buffs(self.recipient))

        # Advance 20s
        tick_buffs(self.recipient, 20)
        self.assertEqual(self.recipient.traits.hp.current, 20)

    def test_second_synthetic_configuration_reusable_for_non_light_source(self):
        """A second distinct synthetic configuration proves the recovery profile is generic and reusable."""
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_nature_spring_rejuvenation",
                duration=60,
                tick_interval=20,  # multiple of 10
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 25,
                            "exposure_percent_per_ordinal": 0.05,  # 5% per exposure ordinal
                        }
                    }
                },
            )
        )
        # Recipient exposure ordinal 4 ("極高")
        self.recipient.sexual.exposure.value = EXPOSURE_LEVELS[4]
        self.recipient.traits.hp.current = 10

        # Snapshot heal gain +10%, grace 1.2
        apply_buff(
            self.recipient,
            "synth_nature_spring_rejuvenation",
            snapshot_heal_gain="+10%",
            snapshot_grace_multiplier=1.2,
        )

        # base = 25
        # exposure: (1 + 0.05 * 4) = 1.2
        # heal_gain: (1 + 0.10) = 1.1
        # grace: 1.2
        # raw = floor(25 * 1.2 * 1.1 * 1.2) = floor(39.6) = 39
        tick_buffs(self.recipient, 20)
        self.assertEqual(self.recipient.traits.hp.current, 49)

    def test_synthetic_timed_defense_affects_combat_and_expires(self):
        """Scenario: Synthetic timed defense affects combat.

        WHEN a synthetic refreshable defense marker is applied and then expires
        THEN computed incoming damage is reduced while active and returns to its prior value after expiration without stacking on refresh
        """
        from world.rules.rulebook.schema import Rule
        from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers

        defense_buff = self._register_synth_buff(
            BuffDefinition(
                key="synth_timed_defense_marker",
                duration=60,
                tick_interval=None,
                stacking="refresh",
                modifiers={},
            )
        )
        # Inject synthetic combat rule consuming buff_active: synth_timed_defense_marker
        synth_rule = Rule(
            id="synth_timed_defense_rule",
            when={"buff_active": "synth_timed_defense_marker"},
            then={"defense": 18},
        )
        patcher = patch("world.rules.combat_modifiers._RULES", _RULES + [synth_rule])
        patcher.start()
        self.addCleanup(patcher.stop)

        # Baseline: no buff
        mods_baseline = evaluate_combat_modifiers(self.recipient)
        self.assertEqual(mods_baseline.get("defense", 0), 0)

        # Apply timed defense marker
        apply_buff(self.recipient, "synth_timed_defense_marker")
        mods_active = evaluate_combat_modifiers(self.recipient)
        self.assertEqual(mods_active.get("defense"), 18)

        # Recast: refreshes duration, does not stack defense to 36
        apply_buff(self.recipient, "synth_timed_defense_marker")
        mods_refreshed = evaluate_combat_modifiers(self.recipient)
        self.assertEqual(mods_refreshed.get("defense"), 18)

        # Advance 60s: buff expires
        tick_buffs(self.recipient, 60)
        self.assertNotIn("synth_timed_defense_marker", entity_active_buffs(self.recipient))
        mods_expired = evaluate_combat_modifiers(self.recipient)
        self.assertEqual(mods_expired.get("defense", 0), 0)

    def test_clock_advance_beyond_quanta_budget_never_fabricates_ticks(self):
        """Clock advances beyond max_settlement_quanta never fabricate extra ticks."""
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_clock_ward",
                duration=30,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 10,
                        }
                    }
                },
            )
        )
        self.recipient.traits.hp.rate = 0
        self.recipient.traits.hp.current = 10
        apply_buff(self.recipient, "synth_clock_ward")

        # Advance with CLOCK_YAML max_settlement_quanta mocked to 2 (only 20s processed)
        with patch.dict(CLOCK_YAML, {"max_settlement_quanta": 2}):
            # Even though we advance 100s, max 2 quanta run (20s) -> exactly 2 ticks
            WorldClock().advance(100, AdvanceSource.COMMAND, [self.recipient])
            self.assertEqual(self.recipient.traits.hp.current, 30)
