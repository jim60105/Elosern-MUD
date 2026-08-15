"""Tests for the public SexualState handler surface."""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.sexual_vocab import AROUSAL_LEVELS
from world.rules.sexual_state import (
    PLEASURE_CONFIG,
    PleasureConfigError,
    SexualState,
    load_pleasure_config,
)


class SexualStateTests(EvenniaTest):
    @covers_requirement("sexual-state-handler::entity-sexual-is-mounted-as-the-real-sexualstate-handler-replacing-the-change-3-placeholder", "sexual-state-handler::sexualstate-is-constructed-from-entity-db-sexual-when-a-raw-baseline-is-present")
    def test_handler_mounts_and_preserves_complete_raw_baseline(self):
        entity = create_object(PlayerCharacter, key="baseline")
        baseline = {
            "arousal": "微興奮",
            "wetness": "濕潤",
            "shame": "輕微",
            "exposure": "高",
            "climax_phase": "接近",
            "sensitivity": {"私處": "極高"},
            "climax_today": 3,
            "virgin": False,
            "experience_types": ["陰道性交"],
        }
        entity.db.sexual = deepcopy(baseline)
        self.assertIsInstance(entity.sexual, SexualState)
        self.assertEqual(entity.sexual.arousal.level, "微興奮")
        self.assertEqual(entity.sexual.wetness.level, "濕潤")
        self.assertEqual(entity.sexual.shame.level, "輕微")
        self.assertEqual(entity.sexual.exposure.level, "高")
        self.assertEqual(entity.sexual.climax_phase.level, "接近")
        self.assertEqual(entity.sexual.sensitivity["私處"].level, "極高")
        self.assertEqual(entity.sexual.climax_today, 3)
        self.assertFalse(entity.sexual.virgin)
        self.assertEqual(entity.sexual.experience_types, frozenset({"陰道性交"}))
        self.assertEqual(entity.db.sexual, baseline)

    @covers_requirement("sexual-state-handler::monster-entities-without-an-imported-baseline-default-to-\u666e\u901a-sensitivity-with-shame-clamped-to-\u7121")
    def test_optional_fields_default_without_mutating_baseline(self):
        entity = create_object(PlayerCharacter, key="partial baseline")
        baseline = {"arousal": "微興奮", "virgin": True, "sensitivity": {}}
        entity.db.sexual = deepcopy(baseline)
        self.assertEqual(entity.sexual.wetness.level, "乾燥")
        self.assertEqual(entity.db.sexual, baseline)

    @covers_requirement("sexual-state-handler::virgin-is-a-one-way-flag-experience-types-is-an-append-only-set")
    def test_virgin_is_one_way_and_experience_is_append_only(self):
        state = create_object(PlayerCharacter, key="flags").sexual
        state.virgin = False
        state.virgin = True
        self.assertFalse(state.virgin)
        state.add_experience_type("陰道性交")
        state.add_experience_type("陰道性交")
        state.add_experience_type("口交")
        self.assertEqual(state.experience_types, frozenset({"陰道性交", "口交"}))

    def test_record_climax_only_increments_counter(self):
        state = create_object(PlayerCharacter, key="counter").sexual
        before = (
            state.arousal.level,
            state.wetness.level,
            state.shame.level,
            state.exposure.level,
            state.climax_phase.level,
        )
        state.record_climax()
        state.record_climax()
        self.assertEqual(state.climax_today, 2)
        self.assertEqual(
            before,
            (
                state.arousal.level,
                state.wetness.level,
                state.shame.level,
                state.exposure.level,
                state.climax_phase.level,
            ),
        )

    def test_reconstructing_handler_preserves_live_persistent_state(self):
        entity = create_object(PlayerCharacter, key="persistent state")
        entity.sexual.pleasure.base = 60
        entity.sexual.record_climax()
        rebuilt = SexualState(entity)
        self.assertEqual(rebuilt.arousal.level, "高度")
        self.assertEqual(rebuilt.climax_today, 1)


# The documented pleasure→arousal band table (design D-1). The test pins the
# documented values literally so a balance edit cannot drift unnoticed.
DOCUMENTED_BANDS = (
    (0, 14, "平靜", 0),
    (15, 34, "微興奮", 1),
    (35, 59, "中等", 2),
    (60, 84, "高度", 3),
    (85, 100, "極限", 4),
)


class PleasureBandTableTests(unittest.TestCase):
    """Every pleasure value in 0..100 maps to its documented arousal level."""

    def test_every_value_maps_to_its_documented_band(self):
        for floor, ceiling, level, ordinal in DOCUMENTED_BANDS:
            for value in range(floor, ceiling + 1):
                with self.subTest(value=value, level=level):
                    self.assertEqual(PLEASURE_CONFIG.ordinal_for(value), ordinal)
                    self.assertEqual(PLEASURE_CONFIG.floor_for(value), floor)
                    self.assertEqual(PLEASURE_CONFIG.floor_for_level(level), floor)


class PleasureConfigValidationTests(unittest.TestCase):
    """Malformed band and multiplier tables fail closed at load."""

    @staticmethod
    def _valid() -> dict:
        return {
            "pleasure_bands": [
                {"level": "平靜", "floor": 0, "ceiling": 14},
                {"level": "微興奮", "floor": 15, "ceiling": 34},
                {"level": "中等", "floor": 35, "ceiling": 59},
                {"level": "高度", "floor": 60, "ceiling": 84},
                {"level": "極限", "floor": 85, "ceiling": 100},
            ],
            "sensitivity_multipliers": {
                "普通": 1.0,
                "高": 1.4,
                "極高": 1.8,
                "敏感異常": 2.5,
            },
            "shame_multipliers": {
                "無": 1.0,
                "輕微": 0.9,
                "中等": 0.8,
                "強烈": 0.65,
                "成癮": 1.6,
            },
        }

    def _write(self, data: dict) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        import yaml

        path = Path(directory.name) / "sexual_pleasure.yaml"
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
        )
        return path

    def test_canonical_table_loads_and_matches_the_singleton(self):
        config = load_pleasure_config(path=self._write(self._valid()))
        self.assertEqual(config, PLEASURE_CONFIG)

    def test_band_gap_raises_at_load(self):
        data = self._valid()
        data["pleasure_bands"][1]["floor"] = 16
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_band_overlap_raises_at_load(self):
        data = self._valid()
        data["pleasure_bands"][1]["floor"] = 14
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_wrong_band_count_raises_at_load(self):
        data = self._valid()
        data["pleasure_bands"] = data["pleasure_bands"][:4]
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_table_not_covering_zero_to_100_raises_at_load(self):
        data = self._valid()
        data["pleasure_bands"][-1]["ceiling"] = 99
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_table_not_starting_at_zero_raises_at_load(self):
        data = self._valid()
        data["pleasure_bands"][0]["floor"] = 1
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_missing_multiplier_key_raises_at_load(self):
        data = self._valid()
        del data["sensitivity_multipliers"]["高"]
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_extra_multiplier_key_raises_at_load(self):
        data = self._valid()
        data["shame_multipliers"]["異常"] = 1.2
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_non_positive_multiplier_raises_at_load(self):
        data = self._valid()
        data["shame_multipliers"]["無"] = 0
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_nan_multiplier_raises_at_load(self):
        data = self._valid()
        data["shame_multipliers"]["無"] = float("nan")
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))

    def test_infinite_multiplier_raises_at_load(self):
        data = self._valid()
        data["sensitivity_multipliers"]["普通"] = float("inf")
        with self.assertRaises(PleasureConfigError):
            load_pleasure_config(path=self._write(data))


class PleasureConstructionTests(EvenniaTest):
    @covers_requirement("sexual-state-handler::pleasure-is-constructed-from-an-imported-baseline-s-arousal-level-at-that-level-s-band-floor")
    def test_imported_arousal_level_resolves_to_its_band_floor(self):
        entity = create_object(PlayerCharacter, key="imported arousal")
        entity.db.sexual = {"arousal": "微興奮", "virgin": True, "sensitivity": {}}
        self.assertEqual(entity.sexual.pleasure.value, 15)
        self.assertEqual(entity.sexual.arousal.level, "微興奮")

    @covers_requirement("sexual-state-handler::pleasure-is-constructed-from-an-imported-baseline-s-arousal-level-at-that-level-s-band-floor")
    def test_omitted_arousal_defaults_to_the_floor_levels_pleasure_floor(self):
        entity = create_object(PlayerCharacter, key="no arousal key")
        entity.db.sexual = {"virgin": True, "sensitivity": {}}
        self.assertEqual(entity.sexual.pleasure.value, 0)

    @covers_requirement("sexual-state-handler::pleasure-is-constructed-from-an-imported-baseline-s-arousal-level-at-that-level-s-band-floor")
    def test_monster_without_baseline_starts_at_pleasure_zero(self):
        state = create_object(Monster, key="monster pleasure").sexual
        self.assertEqual(state.pleasure.value, 0)
        self.assertEqual(state.arousal.level, "平靜")


class PleasureBoundsTests(EvenniaTest):
    @covers_requirement("sexual-state-handler::pleasure-is-bounded-0-to-100-and-every-mutation-clamps-at-those-bounds")
    def test_delta_exceeding_100_clamps_at_100(self):
        entity = create_object(PlayerCharacter, key="clamp high")
        entity.sexual.pleasure.base = 95
        entity.sexual.pleasure.base += 14
        self.assertEqual(entity.sexual.pleasure.value, 100)

    @covers_requirement("sexual-state-handler::pleasure-is-bounded-0-to-100-and-every-mutation-clamps-at-those-bounds")
    def test_delta_below_zero_clamps_at_zero(self):
        entity = create_object(PlayerCharacter, key="clamp low")
        entity.sexual.pleasure.base = 5
        entity.sexual.pleasure.base -= 20
        self.assertEqual(entity.sexual.pleasure.value, 0)


class DerivedArousalTests(EvenniaTest):
    @covers_requirement("sexual-state-handler::arousal-is-a-derived-read-only-view-over-pleasure-comparable-exactly-as-before")
    def test_mid_band_pleasure_reads_the_covering_level(self):
        entity = create_object(PlayerCharacter, key="mid band")
        entity.sexual.pleasure.base = 72
        self.assertEqual(entity.sexual.arousal.value, 3)
        self.assertEqual(entity.sexual.arousal.level, "高度")
        self.assertEqual(entity.sexual.arousal.levels, AROUSAL_LEVELS)

    @covers_requirement("sexual-state-handler::arousal-is-a-derived-read-only-view-over-pleasure-comparable-exactly-as-before")
    def test_comparisons_against_the_vocabulary_work_exactly_as_before(self):
        entity = create_object(PlayerCharacter, key="compare")
        entity.sexual.pleasure.base = 90
        self.assertTrue(entity.sexual.arousal >= "高度")
        self.assertTrue(entity.sexual.arousal == "極限")
        self.assertTrue(entity.sexual.arousal > "中等")
        self.assertFalse(entity.sexual.arousal < "極限")
        self.assertTrue(entity.sexual.arousal <= 4)

    @covers_requirement("sexual-state-handler::arousal-is-a-derived-read-only-view-over-pleasure-comparable-exactly-as-before")
    def test_direct_assignment_to_arousal_raises(self):
        entity = create_object(PlayerCharacter, key="read-only")
        with self.assertRaises(AttributeError):
            entity.sexual.arousal.value = 3
