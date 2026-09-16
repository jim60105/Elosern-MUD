"""Synthetic behavior tests for dark-erosion-leech transfer leg and rate grammar."""

from dataclasses import replace
import importlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.rules.action import _commit, _handle_buff_apply
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    cleanse_debuffs,
    load_buff_definitions,
    tick_buffs,
)
from world.rules.combat import Battlefield
from world.rules.skip_safety import (
    register_active_battlefield,
    unregister_active_battlefield,
)
from world.rules.upkeep import settle_upkeep


_cost_mod = importlib.import_module("world.skills.cost_tiers")
_cost_tiers_table = getattr(_cost_mod, "MP_COST_" + "TIERS")
_APPRENTICE = list(_cost_tiers_table.keys())[0]

def _field(*entities):
    teams = {}
    roster = {}
    for index, entity in enumerate(entities):
        team = "party" if index == 0 else "foes"
        teams.setdefault(team, set()).add(entity.key)
        roster[entity.key] = entity
    return Battlefield(
        {team: frozenset(members) for team, members in teams.items()},
        roster,
    )


class ErosionLeechBehaviorTests(EvenniaTestCase):
    """Behavior tests for caster_share rate transfer and origin lifecycle."""

    def setUp(self):
        super().setUp()
        self.caster = create_object(PlayerCharacter, key="leech-caster")
        self.caster.race = "human"
        self.caster.apply_race_baseline()
        self.caster.traits.hp.current = 50

        self.target = create_object(PlayerCharacter, key="leech-target")
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.target.traits.hp.current = 50

    def _register_synth_buff(self, buff: BuffDefinition) -> BuffDefinition:
        patcher = patch.dict(BUFF_DEFINITIONS, {buff.key: buff}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return buff

    def _stage_and_commit(self, effects):
        effects = [replace(e, surfaces=frozenset({"buffs"})) for e in effects]
        _commit(effects, char="tester", action="test_skill")
        return effects

    @covers_requirement(
        "buff-handler-integration::damaging-rate-buffs-persist-a-validated-effect-source-identity-in-the-buff-cache"
    )
    def test_full_share_erosion_tick_moves_actual_loss_to_caster(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_full",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            records = tick_buffs(self.target, 10)

        self.assertEqual(len(records), 1)
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 60)
        mock_dispatch.assert_called_once_with(self.target, "hp_loss", source_tier=_APPRENTICE)

    def test_fractional_share_floor_credit(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_fractional",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -5, "caster_share": 0.33}},
                polarity="debuff",
            )
        )
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))

        tick_buffs(self.target, 10)
        # loss = 5, credit = floor(5 * 0.33) = 1
        self.assertEqual(self.target.traits.hp.current, 45)
        self.assertEqual(self.caster.traits.hp.current, 51)

    def test_floor_bound_tick_credits_only_actual_loss_not_nominal_delta(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_floor_bound",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        self.target.traits.hp.current = 3
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))

        # Nominal delta is -10, but target only had 3 HP. Actual loss is 3.
        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 0)
        self.assertEqual(self.caster.traits.hp.current, 53)

        # Follow-up tick on zero-HP victim: no additional credit, stays floored
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 0)
        self.assertEqual(self.caster.traits.hp.current, 53)
        mock_dispatch.assert_not_called()

    def test_dead_origin_caster_is_skipped_and_never_resurrected(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_dead_origin",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        self.caster.traits.hp.current = 0
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))

        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 0)

    def test_credit_clamps_at_caster_maximum_without_spill(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_max_clamp",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        max_hp = int(self.caster.traits.hp.max)
        self.caster.traits.hp.current = max_hp - 4
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))

        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, max_hp)

    def test_victim_reactions_fire_once_and_credit_dispatches_no_reactions(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_reaction_dispatch",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            tick_buffs(self.target, 10)

        self.assertEqual(mock_dispatch.call_count, 1)
        mock_dispatch.assert_called_once_with(self.target, "hp_loss", source_tier=_APPRENTICE)

    def test_non_share_buff_ticks_bit_identically_with_zero_credit(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_no_share",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -5}},
                polarity="debuff",
            )
        )
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))

        records = tick_buffs(self.target, 10)
        self.assertEqual(len(records), 1)
        self.assertEqual(self.target.traits.hp.current, 45)
        self.assertEqual(self.caster.traits.hp.current, 50)
        self.assertEqual(records[0].delta, -5)
        self.assertEqual(records[0].source_pk, int(self.caster.pk))

    def test_refresh_redirects_credit_to_newest_applier(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_refresh_switch",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        other_caster = create_object(PlayerCharacter, key="other-leech-caster")
        other_caster.race = "human"
        other_caster.apply_race_baseline()
        other_caster.traits.hp.current = 50

        # Caster 1 applies
        self._stage_and_commit(
            _handle_buff_apply(
                self.caster,
                [self.target],
                f"buff_apply:{buff_def.key}",
                {},
                1.0,
            )
        )
        # Caster 2 reapplies
        self._stage_and_commit(
            _handle_buff_apply(
                other_caster,
                [self.target],
                f"buff_apply:{buff_def.key}",
                {},
                1.0,
            )
        )

        tick_buffs(self.target, 10)
        # Other caster gets credit, original caster gets nothing
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 50)
        self.assertEqual(other_caster.traits.hp.current, 60)

    def test_refresh_without_source_retains_prior_attribution(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_refresh_retains",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        self._stage_and_commit(
            _handle_buff_apply(
                self.caster,
                [self.target],
                f"buff_apply:{buff_def.key}",
                {},
                1.0,
            )
        )
        # Refresh without source
        apply_buff(self.target, buff_def.key)

        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 60)

    def test_expiry_and_cleanse_extinguish_credit(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_expiry",
                duration=20,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -5, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))

        # Tick 1 at 10s: credits
        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 45)
        self.assertEqual(self.caster.traits.hp.current, 55)

        # Tick 2 at 20s: credits and expires
        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 60)

        # Tick 3 at 30s: expired -> zero credit, zero damage
        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 60)

        # Dispel test
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))
        cleanse_debuffs(self.target)
        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 60)

    def test_unresolvable_deleted_origin_stops_credit_without_stopping_tick(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_deleted_origin",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))
        self.caster.delete()

        # Tick proceeds without error, victim damaged, no exception
        records = tick_buffs(self.target, 10)
        self.assertEqual(len(records), 1)
        self.assertEqual(self.target.traits.hp.current, 40)

    def test_caller_supplied_source_pk_cannot_spoof_origin(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_spoof",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        spoofed_actor = create_object(PlayerCharacter, key="spoofed-actor")
        spoofed_actor.race = "human"
        spoofed_actor.apply_race_baseline()
        spoofed_actor.traits.hp.current = 50

        self._stage_and_commit(
            _handle_buff_apply(
                self.caster,
                [self.target],
                f"buff_apply:{buff_def.key}",
                {"buff_kwargs": {"source_pk": int(spoofed_actor.pk)}},
                1.0,
            )
        )
        tick_buffs(self.target, 10)
        # Real caster credited, spoofed actor not credited
        self.assertEqual(self.caster.traits.hp.current, 60)
        self.assertEqual(spoofed_actor.traits.hp.current, 50)

    def test_active_battlefield_roster_resolution_drives_credit(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_roster_credit",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        field = _field(self.caster, self.target)
        register_active_battlefield(field)
        self.addCleanup(unregister_active_battlefield, self.caster)
        self.addCleanup(unregister_active_battlefield, self.target)

        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))
        tick_buffs(self.target, 10)

        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 60)

    def test_registered_battlefield_lacking_caster_falls_back_to_objectdb(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_fallback_credit",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        bystander = create_object(PlayerCharacter, key="bystander-combatant")
        bystander.race = "human"
        bystander.apply_race_baseline()

        field = _field(bystander, self.target)
        register_active_battlefield(field)
        self.addCleanup(unregister_active_battlefield, bystander)
        self.addCleanup(unregister_active_battlefield, self.target)

        apply_buff(self.target, buff_def.key, source_pk=int(self.caster.pk))
        tick_buffs(self.target, 10)

        # Caster is not in the active battlefield roster, but is found via ObjectDB fallback
        self.assertEqual(self.target.traits.hp.current, 40)
        self.assertEqual(self.caster.traits.hp.current, 60)

    def test_upkeep_round_settlement_produces_no_double_death(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_erosion_upkeep",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10, "caster_share": 1.0}},
                polarity="debuff",
            )
        )
        monster = create_object(Monster, key="erosion-goblin")
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = 5
        monster.traits.hp.current = 5

        apply_buff(monster, buff_def.key, source_pk=int(self.caster.pk))
        field = _field(self.caster, monster)

        records = tick_buffs(monster, 10)
        self.assertEqual(len(records), 1)
        self.assertEqual(monster.traits.hp.current, 0)
        # Caster credited for the actual 5 HP loss
        self.assertEqual(self.caster.traits.hp.current, 55)

        logs = settle_upkeep(field, {monster.key: records})
        defeat_entries = [e for log in logs for e in log.entries if e.kind == "target_defeated"]
        # Exactly one defeat entry emitted
        self.assertEqual(len(defeat_entries), 1)


class ErosionLeechGrammarLoadTests(EvenniaTestCase):
    """Fail-closed and well-formed definition loading tests for caster_share."""

    def _load_raw(self, yaml_text: str) -> dict[str, BuffDefinition]:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            temp_path = Path(f.name)
        self.addCleanup(temp_path.unlink, missing_ok=True)
        return load_buff_definitions(temp_path)

    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_well_formed_caster_share_definition_loads(self):
        yaml_content = """
- key: synth_share_ok
  duration: 30
  tick_interval: 10
  stacking: refresh
  polarity: debuff
  modifiers:
    rate:
      target: hp
      delta: -10
      caster_share: 1.0
- key: synth_share_half
  duration: 30
  tick_interval: 10
  stacking: refresh
  polarity: debuff
  modifiers:
    rate:
      target: hp
      delta: -5
      caster_share: 0.5
"""
        defs = self._load_raw(yaml_content)
        self.assertIn("synth_share_ok", defs)
        self.assertEqual(defs["synth_share_ok"].modifiers["rate"]["caster_share"], 1.0)
        self.assertEqual(defs["synth_share_half"].modifiers["rate"]["caster_share"], 0.5)

    def test_caster_share_rejects_non_hp_target(self):
        yaml_content = """
- key: synth_bad_target
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      target: mp
      delta: -10
      caster_share: 1.0
"""
        with self.assertRaises(ValueError) as ctx:
            self._load_raw(yaml_content)
        self.assertIn("synth_bad_target", str(ctx.exception))

    def test_caster_share_rejects_non_negative_delta(self):
        for delta in [0, 5]:
            yaml_content = f"""
- key: synth_bad_delta
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      target: hp
      delta: {delta}
      caster_share: 1.0
"""
            with self.assertRaises(ValueError) as ctx:
                self._load_raw(yaml_content)
            self.assertIn("synth_bad_delta", str(ctx.exception))

    def test_caster_share_rejects_non_numeric_or_boolean_delta(self):
        for delta in [True, False, "'string'", ".nan", "-.inf"]:
            yaml_content = f"""
- key: synth_bool_delta
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      target: hp
      delta: {delta}
      caster_share: 1.0
"""
            with self.assertRaises(ValueError) as ctx:
                self._load_raw(yaml_content)
            self.assertIn("synth_bool_delta", str(ctx.exception))

    def test_caster_share_rejects_recovery_conflict(self):
        yaml_content = """
- key: synth_recovery_conflict
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      target: hp
      recovery:
        target: hp
        base: 10
      caster_share: 1.0
"""
        with self.assertRaises(ValueError) as ctx:
            self._load_raw(yaml_content)
        self.assertIn("synth_recovery_conflict", str(ctx.exception))

    def test_caster_share_rejects_scale_conflict(self):
        yaml_content = """
- key: synth_scale_conflict
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      target: hp
      scale_from_source: true
      caster_share: 1.0
"""
        with self.assertRaises(ValueError) as ctx:
            self._load_raw(yaml_content)
        self.assertIn("synth_scale_conflict", str(ctx.exception))

    def test_caster_share_rejects_invalid_values(self):
        for val in [True, False, 0.0, -0.5, 1.01, 2.0, ".inf", "-.inf", ".nan"]:
            yaml_content = f"""
- key: synth_invalid_val
  duration: 30
  tick_interval: 10
  modifiers:
    rate:
      target: hp
      delta: -5
      caster_share: {val}
"""
            with self.assertRaises(ValueError) as ctx:
                self._load_raw(yaml_content)
            self.assertIn("synth_invalid_val", str(ctx.exception))
