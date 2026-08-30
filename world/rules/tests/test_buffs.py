"""Integration tests for rulebook-backed Evennia buffs."""

from tools.spec_traceability import covers_requirement

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evennia.contrib.rpg.buffs import BuffHandler
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    RulebookBuff,
    _add_buff,
    _apply_rate_modifier,
    active_buff_keys_from_storage,
    blocks_action,
    entity_active_buffs,
    grant_conferred_growth_rate,
    growth_rate_multiplier,
    load_buff_definitions,
    tick_buffs,
)


def _write_yaml(content: str) -> Path:
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    handle.write(content)
    handle.close()
    return Path(handle.name)


class BuffDefinitionValidationTests(unittest.TestCase):
    def test_non_list_root_is_rejected(self):
        path = _write_yaml("key: value\n")
        with self.assertRaises(ValueError):
            load_buff_definitions(path)

    def test_entry_without_key_is_rejected(self):
        path = _write_yaml("- duration: 10\n")
        with self.assertRaises(ValueError):
            load_buff_definitions(path)

    def test_duplicate_key_is_rejected(self):
        path = _write_yaml("- key: a\n- key: a\n")
        with self.assertRaises(ValueError):
            load_buff_definitions(path)

    def test_invalid_modifier_shape_is_rejected(self):
        path = _write_yaml("- key: a\n  modifiers: {bogus: 1}\n")
        with self.assertRaises(ValueError):
            load_buff_definitions(path)

    def test_unsupported_stacking_is_rejected(self):
        path = _write_yaml("- key: a\n  stacking: wrong\n")
        with self.assertRaises(ValueError):
            load_buff_definitions(path)

    def test_polarity_defaults_to_buff(self):
        path = _write_yaml("- key: a\n")
        self.assertEqual(load_buff_definitions(path)["a"].polarity, "buff")

    def test_polarity_debuff_is_accepted(self):
        path = _write_yaml("- key: a\n  polarity: debuff\n")
        self.assertEqual(load_buff_definitions(path)["a"].polarity, "debuff")

    def test_unsupported_polarity_is_rejected(self):
        path = _write_yaml("- key: a\n  polarity: wrong\n")
        with self.assertRaises(ValueError):
            load_buff_definitions(path)

    def test_noop_rate_target_tick_does_nothing(self):
        entity = SimpleNamespace(traits=SimpleNamespace())
        _apply_rate_modifier(entity, {"target": "skill_practice", "delta": 1})

    def test_unknown_rate_target_is_rejected(self):
        entity = SimpleNamespace(traits=SimpleNamespace())
        with self.assertRaises(NotImplementedError):
            _apply_rate_modifier(entity, {"target": "bogus", "delta": 1})

    def test_unique_per_source_requires_source_key(self):
        entity = SimpleNamespace(buffs=SimpleNamespace(add=lambda *a, **k: None))
        with self.assertRaises(ValueError):
            _add_buff(entity, "conferred_growth_rate")

    def test_storage_accessor_tolerates_missing_and_malformed_cache(self):
        empty = SimpleNamespace(attributes=SimpleNamespace(get=lambda *a, **k: None))
        self.assertEqual(active_buff_keys_from_storage(empty), set())
        bad_root = SimpleNamespace(attributes=SimpleNamespace(get=lambda *a, **k: "nope"))
        with self.assertRaises(TypeError):
            active_buff_keys_from_storage(bad_root)
        bad_entry = SimpleNamespace(
            attributes=SimpleNamespace(get=lambda *a, **k: {"b": "nope"})
        )
        with self.assertRaises(TypeError):
            active_buff_keys_from_storage(bad_entry)

    def test_storage_accessor_skips_paused_and_zero_stack_buffs(self):
        entity = SimpleNamespace(
            attributes=SimpleNamespace(
                get=lambda *a, **k: {
                    "poisoned": {"definition_key": "poisoned", "paused": True},
                    "fear": {"definition_key": "fear", "stacks": 0},
                }
            )
        )
        self.assertEqual(active_buff_keys_from_storage(entity), set())


class BuffIntegrationTests(EvenniaTestCase):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="buff target")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.traits.hp.rate = 0
        return entity

    @covers_requirement("buff-handler-integration::buff-tick-is-exposed-as-a-plain-callable-with-no-settlement-order-invented")
    def test_buff_poisoned(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        before = entity.traits.hp.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, before - 5)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-火-element-spell-set")
    def test_buff_fire_scorch(self):
        definition = BUFF_DEFINITIONS["fire_scorch"]
        self.assertEqual(definition.duration, 300)
        self.assertEqual(definition.tick_interval, 10)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(definition.modifiers, {"rate": {"target": "hp", "delta": -5}})

        entity = self._entity()
        _add_buff(entity, "fire_scorch")
        before = entity.traits.hp.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, before - 5)
        self.assertEqual(entity.buffs.all["fire_scorch"].tick_interval, 10)
        self.assertIn("fire_scorch", entity_active_buffs(entity))

    def test_buff_fire_scorch_expires_by_explicit_game_seconds(self):
        entity = self._entity()
        _add_buff(entity, "fire_scorch")
        tick_buffs(entity, 290)
        self.assertIn("fire_scorch", entity_active_buffs(entity))
        tick_buffs(entity, 10)
        self.assertNotIn("fire_scorch", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-水-element-spell-set")
    def test_buff_water_shield(self):
        definition = BUFF_DEFINITIONS["water_shield"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "defense", "ceiling": 5}}
        )

        entity = self._entity()
        _add_buff(entity, "water_shield")
        self.assertIn("water_shield", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-水-element-spell-set")
    def test_buff_water_bind(self):
        definition = BUFF_DEFINITIONS["water_bind"]
        self.assertEqual(definition.duration, 30)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(definition.modifiers, {})

        entity = self._entity()
        _add_buff(entity, "water_bind")
        self.assertIn("water_bind", entity_active_buffs(entity))
        self.assertFalse(blocks_action(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_buff_earth_hardened_skin(self):
        definition = BUFF_DEFINITIONS["earth_hardened_skin"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "defense", "ceiling": 3}}
        )

        entity = self._entity()
        _add_buff(entity, "earth_hardened_skin")
        self.assertIn("earth_hardened_skin", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_buff_earth_stone_armor(self):
        definition = BUFF_DEFINITIONS["earth_stone_armor"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "defense", "ceiling": 5}}
        )

        entity = self._entity()
        _add_buff(entity, "earth_stone_armor")
        self.assertIn("earth_stone_armor", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_buff_earth_dust_veil(self):
        definition = BUFF_DEFINITIONS["earth_dust_veil"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "accuracy", "ceiling": -5}}
        )

        entity = self._entity()
        _add_buff(entity, "earth_dust_veil")
        self.assertIn("earth_dust_veil", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_buff_earth_root(self):
        definition = BUFF_DEFINITIONS["earth_root"]
        self.assertEqual(definition.duration, 30)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(definition.modifiers, {})

        entity = self._entity()
        _add_buff(entity, "earth_root")
        self.assertIn("earth_root", entity_active_buffs(entity))
        self.assertFalse(blocks_action(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_buff_earth_ward(self):
        definition = BUFF_DEFINITIONS["earth_ward"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "defense", "ceiling": 5}}
        )

        entity = self._entity()
        _add_buff(entity, "earth_ward")
        self.assertIn("earth_ward", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-風-element-spell-set")
    def test_buff_wind_haste(self):
        definition = BUFF_DEFINITIONS["wind_haste"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "agility", "ceiling": 3}}
        )

        entity = self._entity()
        _add_buff(entity, "wind_haste")
        self.assertIn("wind_haste", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-風-element-spell-set")
    def test_buff_wind_haste_domain(self):
        definition = BUFF_DEFINITIONS["wind_haste_domain"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "agility", "ceiling": 5}}
        )

        entity = self._entity()
        _add_buff(entity, "wind_haste_domain")
        self.assertIn("wind_haste_domain", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-雷-element-spell-set")
    def test_buff_lightning_static_ward(self):
        definition = BUFF_DEFINITIONS["lightning_static_ward"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "defense", "ceiling": 3}}
        )

        entity = self._entity()
        _add_buff(entity, "lightning_static_ward")
        self.assertIn("lightning_static_ward", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-雷-element-spell-set")
    def test_buff_lightning_extra_action(self):
        definition = BUFF_DEFINITIONS["lightning_extra_action"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers,
            {"bounds": {"target": "actions_per_turn", "ceiling": 1}},
        )

        entity = self._entity()
        _add_buff(entity, "lightning_extra_action")
        self.assertIn("lightning_extra_action", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_buff_ice_slow(self):
        definition = BUFF_DEFINITIONS["ice_slow"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "agility", "ceiling": -3}}
        )

        entity = self._entity()
        _add_buff(entity, "ice_slow")
        self.assertIn("ice_slow", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_buff_ice_wall(self):
        definition = BUFF_DEFINITIONS["ice_wall"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "defense", "ceiling": 5}}
        )

        entity = self._entity()
        _add_buff(entity, "ice_wall")
        self.assertIn("ice_wall", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_buff_ice_freeze(self):
        definition = BUFF_DEFINITIONS["ice_freeze"]
        self.assertEqual(definition.duration, 30)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(definition.modifiers, {})

        entity = self._entity()
        _add_buff(entity, "ice_freeze")
        self.assertIn("ice_freeze", entity_active_buffs(entity))
        self.assertFalse(blocks_action(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_buff_ice_prison(self):
        definition = BUFF_DEFINITIONS["ice_prison"]
        self.assertEqual(definition.duration, 30)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(definition.modifiers, {})

        entity = self._entity()
        _add_buff(entity, "ice_prison")
        self.assertIn("ice_prison", entity_active_buffs(entity))
        self.assertFalse(blocks_action(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-光-element-spell-set")
    def test_buff_light_holy_shield(self):
        definition = BUFF_DEFINITIONS["light_holy_shield"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "defense", "ceiling": 5}}
        )

        entity = self._entity()
        _add_buff(entity, "light_holy_shield")
        self.assertIn("light_holy_shield", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-光-element-spell-set")
    def test_buff_light_blessing(self):
        definition = BUFF_DEFINITIONS["light_blessing"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "buff")
        self.assertEqual(
            definition.modifiers, {"bounds": {"target": "defense", "ceiling": 3}}
        )

        entity = self._entity()
        _add_buff(entity, "light_blessing")
        self.assertIn("light_blessing", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-暗-element-spell-set")
    def test_buff_dark_atk_down(self):
        definition = BUFF_DEFINITIONS["dark_atk_down"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers,
            {
                "bounds": [
                    {"target": "atk_phys", "ceiling": -5},
                    {"target": "magic_power", "ceiling": -5},
                ]
            },
        )

        entity = self._entity()
        _add_buff(entity, "dark_atk_down")
        self.assertIn("dark_atk_down", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-暗-element-spell-set")
    def test_buff_dark_curse(self):
        definition = BUFF_DEFINITIONS["dark_curse"]
        self.assertEqual(definition.duration, 60)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers,
            {
                "bounds": [
                    {"target": "atk_phys", "ceiling": -10},
                    {"target": "magic_power", "ceiling": -10},
                    {"target": "agility", "ceiling": -10},
                ]
            },
        )

        entity = self._entity()
        _add_buff(entity, "dark_curse")
        self.assertIn("dark_curse", entity_active_buffs(entity))

    @covers_requirement("skill-registry::skill-registry-contains-the-full-暗-element-spell-set")
    def test_buff_dark_corrosion(self):
        definition = BUFF_DEFINITIONS["dark_corrosion"]
        self.assertEqual(definition.duration, 300)
        self.assertEqual(definition.tick_interval, 10)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers, {"rate": {"target": "hp", "delta": -5}}
        )

        entity = self._entity()
        _add_buff(entity, "dark_corrosion")
        before = entity.traits.hp.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, before - 5)
        self.assertEqual(entity.buffs.all["dark_corrosion"].tick_interval, 10)
        self.assertIn("dark_corrosion", entity_active_buffs(entity))

    def test_buff_tick_on_full_gauge_stores_integer(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        stored = entity.attributes.get("traits", category="traits")["hp"]
        self.assertNotIn("current", stored)
        tick_buffs(entity)
        stored = entity.attributes.get("traits", category="traits")["hp"]
        self.assertEqual(stored["current"], stored["base"] - 5)
        self.assertIsInstance(stored["current"], int)

    @covers_requirement("buff-handler-integration::buff-tick-is-exposed-as-a-plain-callable-with-no-settlement-order-invented")
    def test_damaging_ticks_return_ordered_records(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        _add_buff(entity, "fire_scorch")
        before = entity.traits.hp.current
        records = tick_buffs(entity, 10)
        self.assertEqual(
            [record.definition_key for record in records],
            ["poisoned", "fire_scorch"],
        )
        self.assertEqual(records[0].delta, -5)
        self.assertEqual(records[0].hp_before, float(before))
        self.assertEqual(records[1].hp_before, float(before - 5))
        self.assertEqual(entity.traits.hp.current, before - 10)

    @covers_requirement("buff-handler-integration::buff-tick-is-exposed-as-a-plain-callable-with-no-settlement-order-invented")
    def test_non_damaging_ticks_return_no_records(self):
        entity = self._entity()
        _add_buff(entity, "paralysis")
        _add_buff(entity, "fear")
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        records = tick_buffs(entity, 10)
        self.assertEqual(records, ())

    @covers_requirement("buff-handler-integration::damaging-rate-buffs-persist-a-validated-effect-source-identity-in-the-buff-cache")
    def test_damaging_tick_record_carries_cached_source_pk(self):
        entity = self._entity()
        _add_buff(entity, "poisoned", source_pk=42)
        (record,) = tick_buffs(entity)
        self.assertEqual(record.source_pk, 42)

    @covers_requirement("buff-handler-integration::buff-tick-is-exposed-as-a-plain-callable-with-no-settlement-order-invented")
    def test_ignoring_tick_records_keeps_hp_behavior_unchanged(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        before = entity.traits.hp.current
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.current, before - 5)

    @covers_requirement("buff-handler-integration::a-declared-unbuilt-seam-exists-for-buff-forbidden-actions")
    def test_buff_paralysis(self):
        entity = self._entity()
        _add_buff(entity, "paralysis")
        self.assertIn("paralysis", entity_active_buffs(entity))
        self.assertTrue(blocks_action(entity))

    def test_buff_fear(self):
        entity = self._entity()
        _add_buff(entity, "fear")
        self.assertIn("fear", entity_active_buffs(entity))
        self.assertFalse(blocks_action(entity))

    def test_buff_focus(self):
        entity = self._entity()
        _add_buff(entity, "focus")
        self.assertIn("focus", entity_active_buffs(entity))
        self.assertFalse(blocks_action(entity))

    @covers_requirement("buff-handler-integration::growth-rate-multiplier-is-a-pure-query-folding-every-active-conferred-growth-rate")
    @covers_requirement("buff-handler-integration::a-rate-of-change-modifier-can-be-conferred-from-one-entity-to-another-as-a-buff")
    def test_buff_conferred_growth_rate(self):
        entity = self._entity()
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        buff = entity.buffs.all["conferred_growth_rate:elosia"]
        self.assertEqual((buff.source_key, buff.scale), ("elosia", 0.5))
        self.assertEqual(growth_rate_multiplier(entity), 0.5)

    def test_buff_item_regen_light(self):
        definition = BUFF_DEFINITIONS["item_regen_light"]
        self.assertIsNone(definition.duration)
        self.assertEqual(definition.tick_interval, 10)
        self.assertEqual(definition.stacking, "unique_per_source")
        self.assertEqual(definition.polarity, "buff")
        entity = self._entity()
        _add_buff(
            entity,
            "item_regen_light",
            instance_key="item_regen_light:apothecary_beads",
            source_key="apothecary_beads",
        )
        self.assertIn("item_regen_light:apothecary_beads", entity.buffs.all)
        entity.traits.hp.current = entity.traits.hp.value - 10
        before = entity.traits.hp.value
        self.assertEqual(tick_buffs(entity), ())
        self.assertEqual(entity.traits.hp.value, before + 3)
        entity.traits.hp.current = entity.traits.hp.max
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, entity.traits.hp.max)

    @covers_requirement("buff-handler-integration::the-conferred-growth-rate-buff-s-tick-is-a-documented-no-op-consumed-by-pull-rather")
    def test_conferred_growth_rate_tick_is_a_no_op(self):
        entity = self._entity()
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        before = entity.traits.magic_power.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.magic_power.value, before)

    @covers_requirement("cleanse-effect-handler::buffs-yaml-entries-declare-a-polarity-defaulting-to-buff")
    def test_rulebook_polarity_classification(self):
        for key in ("poisoned", "paralysis", "fear"):
            self.assertEqual(BUFF_DEFINITIONS[key].polarity, "debuff")
        for key in ("focus", "conferred_growth_rate"):
            self.assertEqual(BUFF_DEFINITIONS[key].polarity, "buff")

    def test_handler_mount_is_read_only(self):
        entity = self._entity()
        self.assertIsInstance(entity.buffs, BuffHandler)
        with self.assertRaises(AttributeError):
            entity.buffs = {}

    @covers_requirement("buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate")
    def test_no_multiplier_shaped_buff_modifier(self):
        forbidden = {"atk_phys_multiplier", "agility_multiplier", "defense_multiplier"}
        for definition in BUFF_DEFINITIONS.values():
            self.assertFalse(set(definition.modifiers) & forbidden)

    def test_growth_query_identity_unknown_source_and_multiple_sources(self):
        entity = self._entity()
        self.assertEqual(growth_rate_multiplier(entity), 1.0)
        grant_conferred_growth_rate(entity, "unknown", 0.5)
        grant_conferred_growth_rate(entity, "other", 0.25)
        self.assertEqual(growth_rate_multiplier(entity), 0.125)

    def test_refresh_replaces_same_key_and_preserves_distinct_sources(self):
        entity = self._entity()
        _add_buff(entity, "fear")
        first_start = entity.buffs.all["fear"].start
        _add_buff(entity, "fear")
        self.assertGreaterEqual(entity.buffs.all["fear"].start, first_start)
        grant_conferred_growth_rate(entity, "one", 0.5)
        grant_conferred_growth_rate(entity, "two", 0.25)
        self.assertIn("conferred_growth_rate:one", entity.buffs.all)
        self.assertIn("conferred_growth_rate:two", entity.buffs.all)

    def test_expired_buffs_are_not_active_queried_or_ticked(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        _add_buff(entity, "paralysis")
        grant_conferred_growth_rate(entity, "temporary", 0.5)
        for key in ("poisoned", "paralysis"):
            entity.buffs.all[key].remaining_seconds = 0
        hp = entity.traits.hp.value
        self.assertEqual(entity_active_buffs(entity), {"conferred_growth_rate"})
        self.assertFalse(blocks_action(entity))
        self.assertEqual(growth_rate_multiplier(entity), 0.5)
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, hp)

    def test_buff_expiry_uses_explicit_game_seconds(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        self.assertEqual(entity.buffs.all["poisoned"].duration, -1)
        tick_buffs(entity, 290)
        self.assertIn("poisoned", entity_active_buffs(entity))
        tick_buffs(entity, 10)
        self.assertNotIn("poisoned", entity_active_buffs(entity))

    def test_yaml_tick_interval_is_persisted_as_clock_metadata(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        self.assertEqual(entity.buffs.all["poisoned"].tick_interval, 10)

    def test_every_buff_uses_the_single_generic_class(self):
        entity = self._entity()
        for key in ("poisoned", "paralysis", "fear"):
            _add_buff(entity, key)
        self.assertTrue(
            all(isinstance(buff, RulebookBuff) for buff in entity.buffs.all.values())
        )
