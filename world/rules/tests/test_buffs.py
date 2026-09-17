"""Data-contract test: buff rulebook content contract
Integration and behavior tests for buff mechanics: rate-of-change, bounds,
duration, expiry, immunity, and stacking policies. The shipped polarity and
modifier-shape scans bind the catalogue-wide claims in buff-handler-integration and
cleanse-effect-handler."""

from tools.spec_traceability import covers_requirement

import ast
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from dataclasses import replace as _dc_replace

from evennia.contrib.rpg.buffs import BuffHandler
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    RulebookBuff,
    apply_buff,
    _apply_rate_modifier,
    active_buff_keys_from_storage,
    blocks_action,
    cleanse_debuffs,
    entity_active_buffs,
    grant_conferred_growth_rate,
    growth_rate_multiplier,
    load_buff_definitions,
    remove_by_selector,
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

    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_marker_clause_validation(self):
        path = _write_yaml("- key: a\n  marker: ground\n")
        self.assertEqual(load_buff_definitions(path)["a"].marker, "ground")

        path = _write_yaml("- key: a\n")
        self.assertIsNone(load_buff_definitions(path)["a"].marker)

        for bad_marker in ("fire", "true", "3", "null"):
            with self.subTest(bad_marker=bad_marker):
                path = _write_yaml(f"- key: offending_buff\n  marker: {bad_marker}\n")
                with self.assertRaises(ValueError) as ctx:
                    load_buff_definitions(path)
                self.assertIn("offending_buff", str(ctx.exception))
                self.assertIn("invalid marker", str(ctx.exception))

    def test_selector_word_definition_key_is_rejected(self):
        """A buffs.yaml key may never collide with a remove_by_selector word."""
        for selector in ("all", "positive", "negative"):
            with self.subTest(selector=selector):
                path = _write_yaml(f"- key: {selector}\n")
                with self.assertRaises(ValueError):
                    load_buff_definitions(path)

    def test_noop_rate_target_tick_does_nothing(self):
        entity = SimpleNamespace(traits=SimpleNamespace())
        _apply_rate_modifier(entity, {"target": "skill_practice", "delta": 1})

    def test_unknown_rate_target_is_rejected(self):
        entity = SimpleNamespace(traits=SimpleNamespace())
        with self.assertRaises(NotImplementedError):
            _apply_rate_modifier(entity, {"target": "bogus", "delta": 1})

    @covers_requirement("buff-handler-integration::buff-application-has-one-public-entry-point-carrying-both-grant-time-guards")
    def test_unique_per_source_requires_source_key(self):
        entity = SimpleNamespace(buffs=SimpleNamespace(add=lambda *a, **k: None))
        with self.assertRaises(ValueError):
            apply_buff(entity, "conferred_growth_rate")

    @covers_requirement("buff-handler-integration::buff-application-has-one-public-entry-point-carrying-both-grant-time-guards")
    def test_immune_debuff_is_refused_without_writing(self):
        """The delta's first scenario, reached through the public name: the
        worn-equipment immunity gate inside apply_buff refuses the write."""
        written: list[tuple] = []
        entity = SimpleNamespace(
            buffs=SimpleNamespace(add=lambda *args, **kw: written.append((args, kw)))
        )
        with patch(
            "world.rules.equipment_effects.equipment_immune_buff_keys",
            return_value={"poisoned"},
        ):
            apply_buff(entity, "poisoned")
        self.assertEqual(written, [])
        # The same gate must not swallow a buff-polarity grant.
        apply_buff(entity, "focus")
        self.assertEqual(len(written), 1)

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


class _BuffFixtureMixin(EvenniaTestCase):
    """Synthetic-definition and entity fixtures shared by the buff suites."""

    def _synth_buff(self, **overrides):
        """A synthetic BUFF_DEFINITIONS row shaped by the assertion under
        test, registered for the duration of the test.

        The correspondence contract (every buffs.yaml key has exactly one
        ``test_buff_<key>`` handler-behavior test) stays intact; the shipped
        rows' field values are registry content, not integration behavior.
        """
        definition = _dc_replace(
            BUFF_DEFINITIONS["focus"], key=overrides.pop("key", "t_probe_buff"), **overrides
        )
        original = BUFF_DEFINITIONS.get(definition.key)
        BUFF_DEFINITIONS[definition.key] = definition
        self.addCleanup(
            lambda: BUFF_DEFINITIONS.__setitem__(definition.key, original)
            if original is not None
            else BUFF_DEFINITIONS.pop(definition.key)
        )
        return definition

    def _entity(self):
        entity = create_object(PlayerCharacter, key="buff target")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.traits.hp.rate = 0
        return entity


class BuffIntegrationTests(_BuffFixtureMixin, EvenniaTestCase):
    @covers_requirement("buff-handler-integration::buff-tick-is-exposed-as-a-plain-callable-with-no-settlement-order-invented")
    def test_buff_poisoned(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        before = entity.traits.hp.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, before - 5)

    def test_buff_fire_scorch(self):
        self.assertIn("fire_scorch", BUFF_DEFINITIONS)
        entity = self._entity()
        apply_buff(entity, "fire_scorch")
        before = entity.traits.hp.value
        records = tick_buffs(entity)
        self.assertLess(entity.traits.hp.value, before)
        self.assertTrue(
            any(record.definition_key == "fire_scorch" for record in records)
        )
        self.assertIn("fire_scorch", entity_active_buffs(entity))

    def test_buff_fire_scorch_expires_by_explicit_game_seconds(self):
        entity = self._entity()
        apply_buff(entity, "fire_scorch")
        duration = BUFF_DEFINITIONS["fire_scorch"].duration
        tick_buffs(entity, duration - 10)
        self.assertIn("fire_scorch", entity_active_buffs(entity))
        tick_buffs(entity, 10)
        self.assertNotIn("fire_scorch", entity_active_buffs(entity))

    def test_buff_water_film_divert_shape(self):
        definition = self._synth_buff(
            key="t_divert_shape",
            duration=60,
            stacking="refresh",
            polarity="buff",
            modifiers={"divert": {"target": "mp", "fraction": 0.3, "cap": 30}},
        )
        entity = self._entity()
        apply_buff(entity, definition.key)
        self.assertIn(definition.key, entity_active_buffs(entity))

    def test_buff_water_bind(self):
        definition = BUFF_DEFINITIONS["water_bind"]
        self.assertEqual(definition.duration, 30)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(definition.modifiers, {})

        entity = self._entity()
        apply_buff(entity, "water_bind")
        self.assertIn("water_bind", entity_active_buffs(entity))
        self.assertFalse(blocks_action(entity))

    # Earth rulebook rows carry lore-catalog numbers; per the earth wave's
    # ratified verification contract these stay load/apply/presence checks —
    # pinning durations, ceilings and modifier shapes here would re-mirror
    # shipped catalog data (row-mirror assertions are prohibited).
    def _assert_buff_loads_applies_and_shows(self, key: str) -> None:
        self.assertIn(key, BUFF_DEFINITIONS)
        entity = self._entity()
        apply_buff(entity, key)
        self.assertIn(key, entity_active_buffs(entity))

    def test_buff_earth_hardened_skin(self):
        self._assert_buff_loads_applies_and_shows("earth_hardened_skin")

    def test_buff_earth_stone_armor(self):
        self._assert_buff_loads_applies_and_shows("earth_stone_armor")

    def test_buff_earth_dust_veil(self):
        self._assert_buff_loads_applies_and_shows("earth_dust_veil")

    def test_buff_earth_ward(self):
        self._assert_buff_loads_applies_and_shows("earth_ward")

    def test_buff_earth_bedrock(self):
        self._assert_buff_loads_applies_and_shows("earth_bedrock")

    def test_buff_earth_carapace(self):
        self._assert_buff_loads_applies_and_shows("earth_carapace")

    def test_buff_earth_fissure(self):
        self._assert_buff_loads_applies_and_shows("earth_fissure")

    def test_buff_earth_fissure_quake(self):
        self._assert_buff_loads_applies_and_shows("earth_fissure_quake")

    def test_buff_earth_fissure_apex(self):
        self._assert_buff_loads_applies_and_shows("earth_fissure_apex")

    def test_buff_gale_step_haste(self):
        self._assert_buff_loads_applies_and_shows("gale_step_haste")

    def test_buff_gale_chain_step_haste(self):
        self._assert_buff_loads_applies_and_shows("gale_chain_step_haste")

    def test_buff_afterimage_step_haste(self):
        self._assert_buff_loads_applies_and_shows("afterimage_step_haste")

    def test_buff_haste_domain_haste(self):
        self._assert_buff_loads_applies_and_shows("haste_domain_haste")

    def test_buff_displaced(self):
        self._assert_buff_loads_applies_and_shows("displaced")

    def test_buff_displaced_tempest(self):
        self._assert_buff_loads_applies_and_shows("displaced_tempest")

    def test_buff_displaced_apotheosis(self):
        self._assert_buff_loads_applies_and_shows("displaced_apotheosis")

    def test_buff_lightning_static_ward(self):
        self._assert_buff_loads_applies_and_shows("lightning_static_ward")

    def test_buff_lightning_extra_action(self):
        self._assert_buff_loads_applies_and_shows("lightning_extra_action")

    # Ice rulebook rows carry lore-catalog numbers; per the ratified verification
    # discipline these stay load/apply/presence checks.
    def test_buff_ice_slow(self):
        self._assert_buff_loads_applies_and_shows("ice_slow")

    def test_buff_ice_freeze(self):
        self._assert_buff_loads_applies_and_shows("ice_freeze")

    def test_buff_ice_prison(self):
        self._assert_buff_loads_applies_and_shows("ice_prison")

    def test_buff_dark_weaken(self):
        definition = BUFF_DEFINITIONS["dark_weaken"]
        self.assertEqual(definition.duration, 15)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers,
            {
                "bounds": [
                    {"target": "atk_phys", "ceiling": -3},
                ]
            },
        )

        entity = self._entity()
        apply_buff(entity, "dark_weaken")
        self.assertIn("dark_weaken", entity_active_buffs(entity))

    def test_buff_dark_curse(self):
        definition = BUFF_DEFINITIONS["dark_curse"]
        self.assertEqual(definition.duration, 20)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers,
            {
                "bounds": [
                    {"target": "atk_phys", "ceiling": -5},
                    {"target": "defense", "ceiling": -5},
                    {"target": "agility", "ceiling": -5},
                ]
            },
        )

        entity = self._entity()
        apply_buff(entity, "dark_curse")
        self.assertIn("dark_curse", entity_active_buffs(entity))

    def test_buff_defeat_weak(self):
        definition = BUFF_DEFINITIONS["defeat_weak"]
        self.assertEqual(definition.duration, 300)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers,
            {
                "bounds": [
                    {"target": "atk_phys", "ceiling": -5},
                    {"target": "agility", "ceiling": -5},
                    {"target": "defense", "ceiling": -5},
                ]
            },
        )

        entity = self._entity()
        apply_buff(entity, "defeat_weak")
        self.assertIn("defeat_weak", entity_active_buffs(entity))

    def test_buff_aftermath_residue(self):
        definition = BUFF_DEFINITIONS["aftermath_residue"]
        self.assertEqual(definition.duration, 900)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers,
            {"bounds": [{"target": "agility", "ceiling": -2}]},
        )

        entity = self._entity()
        apply_buff(entity, "aftermath_residue")
        self.assertIn("aftermath_residue", entity_active_buffs(entity))

    def test_buff_aftermath_humiliated(self):
        definition = BUFF_DEFINITIONS["aftermath_humiliated"]
        self.assertEqual(definition.duration, 600)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers,
            {"bounds": [{"target": "accuracy", "ceiling": -3}]},
        )

        entity = self._entity()
        apply_buff(entity, "aftermath_humiliated")
        self.assertIn("aftermath_humiliated", entity_active_buffs(entity))

    def test_buff_dark_corrosion(self):
        definition = BUFF_DEFINITIONS["dark_corrosion"]
        self.assertEqual(definition.duration, 300)
        self.assertEqual(definition.tick_interval, 10)
        self.assertEqual(definition.stacking, "refresh")
        self.assertEqual(definition.polarity, "debuff")
        self.assertEqual(
            definition.modifiers,
            {"rate": {"target": "hp", "delta": -12, "caster_share": 1.0}},
        )

        entity = self._entity()
        apply_buff(entity, "dark_corrosion")
        before = entity.traits.hp.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, before - 12)
        self.assertEqual(entity.buffs.all["dark_corrosion"].tick_interval, 10)
        self.assertIn("dark_corrosion", entity_active_buffs(entity))

    def test_buff_tick_on_full_gauge_stores_integer(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        stored = entity.attributes.get("traits", category="traits")["hp"]
        self.assertNotIn("current", stored)
        tick_buffs(entity)
        stored = entity.attributes.get("traits", category="traits")["hp"]
        self.assertEqual(stored["current"], stored["base"] - 5)
        self.assertIsInstance(stored["current"], int)

    @covers_requirement("buff-handler-integration::buff-tick-is-exposed-as-a-plain-callable-with-no-settlement-order-invented")
    def test_damaging_ticks_return_ordered_records(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        apply_buff(entity, "fire_scorch")
        before = entity.traits.hp.current
        records = tick_buffs(entity, 10)
        self.assertEqual(
            [record.definition_key for record in records],
            ["poisoned", "fire_scorch"],
        )
        self.assertEqual(records[0].delta, -5)
        self.assertEqual(records[0].hp_before, float(before))
        self.assertEqual(records[1].hp_before, float(before - 5))

    @covers_requirement("buff-handler-integration::buff-tick-is-exposed-as-a-plain-callable-with-no-settlement-order-invented")
    def test_non_damaging_ticks_return_no_records(self):
        entity = self._entity()
        apply_buff(entity, "paralysis")
        apply_buff(entity, "fear")
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        records = tick_buffs(entity, 10)
        self.assertEqual(records, ())

    @covers_requirement("buff-handler-integration::damaging-rate-buffs-persist-a-validated-effect-source-identity-in-the-buff-cache")
    def test_damaging_tick_record_carries_cached_source_pk(self):
        entity = self._entity()
        apply_buff(entity, "poisoned", source_pk=42)
        (record,) = tick_buffs(entity)
        self.assertEqual(record.source_pk, 42)

    @covers_requirement("buff-handler-integration::buff-tick-is-exposed-as-a-plain-callable-with-no-settlement-order-invented")
    def test_ignoring_tick_records_keeps_hp_behavior_unchanged(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        before = entity.traits.hp.current
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.current, before - 5)

    @covers_requirement("buff-handler-integration::a-declared-unbuilt-seam-exists-for-buff-forbidden-actions")
    def test_buff_paralysis(self):
        entity = self._entity()
        apply_buff(entity, "paralysis")
        self.assertIn("paralysis", entity_active_buffs(entity))
        self.assertTrue(blocks_action(entity))

    def test_buff_fear(self):
        entity = self._entity()
        apply_buff(entity, "fear")
        self.assertIn("fear", entity_active_buffs(entity))
        self.assertFalse(blocks_action(entity))

    def test_buff_focus(self):
        entity = self._entity()
        apply_buff(entity, "focus")
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
        # Duration-less rate buff: every tick heals, and stacking keeps one
        # instance per source key.
        definition = self._synth_buff(
            key="item_regen_light",
            duration=None,
            tick_interval=10,
            stacking="unique_per_source",
            polarity="buff",
            modifiers={"rate": {"target": "hp", "delta": 3}},
        )
        entity = self._entity()
        apply_buff(
            entity,
            definition.key,
            instance_key=f"{definition.key}:t_bead_of_tides",
            source_key="t_bead_of_tides",
        )
        self.assertIn(f"{definition.key}:t_bead_of_tides", entity.buffs.all)
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
        apply_buff(entity, "fear")
        first_start = entity.buffs.all["fear"].start
        apply_buff(entity, "fear")
        self.assertGreaterEqual(entity.buffs.all["fear"].start, first_start)
        grant_conferred_growth_rate(entity, "one", 0.5)
        grant_conferred_growth_rate(entity, "two", 0.25)
        self.assertIn("conferred_growth_rate:one", entity.buffs.all)
        self.assertIn("conferred_growth_rate:two", entity.buffs.all)

    def test_expired_buffs_are_not_active_queried_or_ticked(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        apply_buff(entity, "paralysis")
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
        apply_buff(entity, "poisoned")
        self.assertEqual(entity.buffs.all["poisoned"].duration, -1)
        tick_buffs(entity, 290)
        self.assertIn("poisoned", entity_active_buffs(entity))
        tick_buffs(entity, 10)
        self.assertNotIn("poisoned", entity_active_buffs(entity))

    def test_yaml_tick_interval_is_persisted_as_clock_metadata(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        self.assertEqual(entity.buffs.all["poisoned"].tick_interval, 10)

    def test_every_buff_uses_the_single_generic_class(self):
        entity = self._entity()
        for key in ("poisoned", "paralysis", "fear"):
            apply_buff(entity, key)
        self.assertTrue(
            all(isinstance(buff, RulebookBuff) for buff in entity.buffs.all.values())
        )


class RemoveBySelectorTests(_BuffFixtureMixin, EvenniaTestCase):
    """The selector-driven removal (item-effect-model design §5.6, D3)."""

    def _polarities(self, entity):
        return {
            buff.definition_key
            for buff in entity.buffs.all.values()
            if buff.stacks > 0
        }

    @covers_requirement("cleanse-effect-handler::status-removal-is-expressed-as-one-selector-driven-operation-returning-a-count")
    def test_negative_removes_every_debuff_and_nothing_else(self):
        entity = self._entity()
        debuff_one = self._synth_buff(key="t_neg_one", polarity="debuff")
        debuff_two = self._synth_buff(key="t_neg_two", polarity="debuff")
        apply_buff(entity, debuff_one.key)
        apply_buff(entity, debuff_two.key)
        apply_buff(entity, "focus")
        self.assertEqual(remove_by_selector(entity, "negative"), 2)
        self.assertEqual(self._polarities(entity), {"focus"})

    def test_positive_removes_beneficial_buffs_only(self):
        entity = self._entity()
        debuff = self._synth_buff(key="t_pos_debuff", polarity="debuff")
        apply_buff(entity, debuff.key)
        apply_buff(entity, "focus")
        self.assertEqual(remove_by_selector(entity, "positive"), 1)
        self.assertEqual(self._polarities(entity), {debuff.key})

    def test_all_removes_both_polarities(self):
        entity = self._entity()
        debuff = self._synth_buff(key="t_all_debuff", polarity="debuff")
        apply_buff(entity, debuff.key)
        apply_buff(entity, "focus")
        self.assertEqual(remove_by_selector(entity, "all"), 2)
        self.assertEqual(self._polarities(entity), set())

    def test_concrete_key_removes_every_live_instance_of_the_definition(self):
        entity = self._entity()
        definition = self._synth_buff(key="t_multi", polarity="debuff")
        apply_buff(entity, definition.key, instance_key="t_multi:first")
        apply_buff(entity, definition.key, instance_key="t_multi:second")
        apply_buff(entity, "focus")
        self.assertEqual(remove_by_selector(entity, definition.key), 2)
        self.assertEqual(self._polarities(entity), {"focus"})

    def test_selector_matching_nothing_writes_nothing_and_returns_zero(self):
        entity = self._entity()
        apply_buff(entity, "focus")
        before = set(entity.buffs.all)
        self.assertEqual(remove_by_selector(entity, "negative"), 0)
        self.assertEqual(set(entity.buffs.all), before)

    def test_paused_and_expired_instances_are_not_removed(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        apply_buff(entity, "paralysis")
        entity.buffs.all["poisoned"].paused = True
        entity.buffs.all["paralysis"].remaining_seconds = 0
        self.assertEqual(remove_by_selector(entity, "negative"), 0)
        self.assertIn("poisoned", entity.buffs.all)
        self.assertIn("paralysis", entity.buffs.all)

    def test_unrecognized_selector_fails_closed(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        with self.assertRaises(ValueError):
            remove_by_selector(entity, "everything")
        self.assertIn("poisoned", self._polarities(entity))

    def test_cleanse_debuffs_is_the_negative_alias(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        apply_buff(entity, "focus")
        self.assertEqual(cleanse_debuffs(entity), 1)
        self.assertEqual(self._polarities(entity), {"focus"})


class BuffEntryPointStructuralTests(unittest.TestCase):
    """The buff-application entry point's structural contract (D1)."""

    _ROOT = Path(__file__).resolve().parents[3]

    @covers_requirement("buff-handler-integration::buff-application-has-one-public-entry-point-carrying-both-grant-time-guards")
    def test_no_module_outside_buffs_calls_the_handler_directly(self):
        """No deterministic module outside world/rules/buffs.py reaches
        ``entity.buffs.add(...)``; every buff grant goes through
        ``apply_buff``."""
        offenders = []
        for directory in ("commands", "server", "tests", "tools", "typeclasses", "web", "world"):
            base = self._ROOT / directory
            for path in sorted(base.rglob("*.py")):
                if "__pycache__" in path.parts or "node_modules" in path.parts:
                    continue
                relative = path.relative_to(self._ROOT).as_posix()
                if relative == "world/rules/buffs.py":
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "add"
                        and ast.unparse(node.func.value).endswith(".buffs")
                    ):
                        offenders.append(f"{relative}:{node.lineno}")
        self.assertEqual(offenders, [])
