"""Integration tests for rulebook-backed Evennia buffs."""

from tools.spec_traceability import covers_requirement

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evennia.contrib.rpg.buffs import BuffHandler
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

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

    def test_noop_rate_target_tick_does_nothing(self):
        entity = SimpleNamespace(traits=SimpleNamespace())
        _apply_rate_modifier(entity, {"target": "magic_level_growth", "delta": 1})

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


class BuffIntegrationTests(EvenniaTest):
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

    def test_buff_tick_on_full_gauge_stores_integer(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        stored = entity.attributes.get("traits", category="traits")["hp"]
        self.assertNotIn("current", stored)
        tick_buffs(entity)
        stored = entity.attributes.get("traits", category="traits")["hp"]
        self.assertEqual(stored["current"], stored["base"] - 5)
        self.assertIsInstance(stored["current"], int)

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

    @covers_requirement("buff-handler-integration::the-conferred-growth-rate-buff-s-tick-is-a-documented-no-op-consumed-by-pull-rather")
    def test_conferred_growth_rate_tick_is_a_no_op(self):
        entity = self._entity()
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        before = entity.traits.magic_level.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.magic_level.value, before)

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
