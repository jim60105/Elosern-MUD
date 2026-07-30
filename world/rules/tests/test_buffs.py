"""Integration tests for rulebook-backed Evennia buffs."""

from evennia.contrib.rpg.buffs import BuffHandler
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    RulebookBuff,
    _add_buff,
    blocks_action,
    entity_active_buffs,
    grant_conferred_growth_rate,
    growth_rate_multiplier,
    tick_buffs,
)


class BuffIntegrationTests(EvenniaTest):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="buff target")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.traits.hp.rate = 0
        return entity

    def test_buff_poisoned(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        before = entity.traits.hp.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, before - 5)

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

    def test_buff_conferred_growth_rate(self):
        entity = self._entity()
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        buff = entity.buffs.all["conferred_growth_rate:elosia"]
        self.assertEqual((buff.source_key, buff.scale), ("elosia", 0.5))
        self.assertEqual(growth_rate_multiplier(entity), 0.5)

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
        for buff in entity.buffs.all.values():
            buff.duration = 1
            buff.start -= 2
        hp = entity.traits.hp.value
        self.assertEqual(entity_active_buffs(entity), set())
        self.assertFalse(blocks_action(entity))
        self.assertEqual(growth_rate_multiplier(entity), 1.0)
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, hp)

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
