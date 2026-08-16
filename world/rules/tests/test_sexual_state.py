"""Tests for the public SexualState handler surface."""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.sexual_vocab import AROUSAL_LEVELS
from world.rules.sexual_state import (
    PLEASURE_CONFIG,
    PleasureConfigError,
    SexualState,
    _LIFETIME_COUNTER_KEYS,
    load_pleasure_config,
    reset_daily_counters,
)


class SexualStateTests(EvenniaTestCase):
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


class PleasureConstructionTests(EvenniaTestCase):
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


class PleasureBoundsTests(EvenniaTestCase):
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


class DerivedArousalTests(EvenniaTestCase):
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


# The delta spec's eleven (field, mutator) pairs, pinned literally so the
# implementation cannot drift from the documented table without a test failing.
LIFETIME_COUNTER_PAIRS = (
    ("masturbation_count", "record_masturbation"),
    ("toy_use_count", "record_toy_use"),
    ("exposure_act_count", "record_exposure_act"),
    ("watched_count", "record_watched"),
    ("duo_act_count", "record_duo_act"),
    ("group_act_count", "record_group_act"),
    ("hostile_act_count", "record_hostile_act"),
    ("restraint_count", "record_restraint"),
    ("interspecies_act_count", "record_interspecies_act"),
    ("climax_count", "record_climax_count"),
    ("climax_extension_count", "record_climax_extension"),
)

LIFETIME_COUNTER_FIELDS = tuple(field for field, _ in LIFETIME_COUNTER_PAIRS)


class LifetimeCounterTests(EvenniaTestCase):
    """The eleven lifetime behaviour counters per the delta spec scenarios."""

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_every_counter_starts_at_zero_regardless_of_baseline(self):
        fresh = create_object(PlayerCharacter, key="fresh counters")
        imported = create_object(PlayerCharacter, key="imported counters")
        imported.db.sexual = {"arousal": "微興奮", "virgin": True, "sensitivity": {}}
        monster = create_object(Monster, key="monster counters")
        for label, entity in (
            ("fresh", fresh),
            ("imported", imported),
            ("monster", monster),
        ):
            for field in LIFETIME_COUNTER_FIELDS:
                with self.subTest(entity=label, field=field):
                    self.assertEqual(getattr(entity.sexual, field), 0)

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_mutator_increments_only_its_own_counter_by_exactly_one(self):
        state = create_object(PlayerCharacter, key="single mutator").sexual
        state.record_masturbation()
        self.assertEqual(state.masturbation_count, 1)
        for field in LIFETIME_COUNTER_FIELDS:
            if field != "masturbation_count":
                self.assertEqual(getattr(state, field), 0)

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_repeated_calls_accumulate_linearly(self):
        state = create_object(PlayerCharacter, key="linear accumulation").sexual
        for _ in range(5):
            state.record_hostile_act()
        self.assertEqual(state.hostile_act_count, 5)
        for field in LIFETIME_COUNTER_FIELDS:
            if field != "hostile_act_count":
                self.assertEqual(getattr(state, field), 0)

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_no_counter_is_reset_by_daily_reset(self):
        entity = create_object(PlayerCharacter, key="daily reset keeps lifetime")
        for field, mutator in LIFETIME_COUNTER_PAIRS:
            getattr(entity.sexual, mutator)()
        for _ in range(2):
            entity.sexual.record_climax_count()
        for _ in range(6):
            entity.sexual.record_restraint()
        entity.sexual.record_climax()
        before = {
            field: getattr(entity.sexual, field) for field in LIFETIME_COUNTER_FIELDS
        }
        reset_daily_counters(entity)
        self.assertEqual(entity.sexual.climax_today, 0)
        self.assertEqual(entity.sexual.climax_count, 3)
        self.assertEqual(entity.sexual.restraint_count, 7)
        for field in LIFETIME_COUNTER_FIELDS:
            self.assertEqual(getattr(entity.sexual, field), before[field])

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_every_counter_is_unbounded_with_floor_zero(self):
        entity = create_object(PlayerCharacter, key="unbounded counters")
        entity.sexual
        stored = entity.attributes.get("sexual_traits", category="traits")
        for field in LIFETIME_COUNTER_FIELDS:
            with self.subTest(field=field):
                config = stored[field]
                self.assertEqual(config["min"], 0)
                self.assertIsNone(config["max"])

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_climax_count_is_independent_of_climax_today(self):
        state = create_object(PlayerCharacter, key="independent climax counters").sexual
        state.record_climax()
        state.record_climax()
        self.assertEqual(state.climax_today, 2)
        self.assertEqual(state.climax_count, 0)
        state.record_climax_count()
        self.assertEqual(state.climax_today, 2)
        self.assertEqual(state.climax_count, 1)

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_each_mutator_moves_only_its_own_counter(self):
        self.assertEqual(
            _LIFETIME_COUNTER_KEYS,
            LIFETIME_COUNTER_FIELDS,
            "the module constant must match the delta spec table exactly",
        )
        state = create_object(PlayerCharacter, key="table driven counters").sexual
        for field, mutator in LIFETIME_COUNTER_PAIRS:
            with self.subTest(field=field, mutator=mutator):
                before = {
                    other_field: getattr(state, other_field)
                    for other_field in LIFETIME_COUNTER_FIELDS
                }
                getattr(state, mutator)()
                for other_field in LIFETIME_COUNTER_FIELDS:
                    if other_field == field:
                        self.assertEqual(
                            getattr(state, other_field), before[other_field] + 1
                        )
                    else:
                        self.assertEqual(
                            getattr(state, other_field), before[other_field]
                        )

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_reconstruction_preserves_lifetime_counters(self):
        entity = create_object(PlayerCharacter, key="persistent lifetime counters")
        entity.sexual.record_climax_count()
        rebuilt = SexualState(entity)
        self.assertEqual(rebuilt.climax_count, 1)
        self.assertEqual(rebuilt.climax_today, 0)


class LifetimeCounterStructureTests(unittest.TestCase):
    """Counters are reachable only through their named property or mutator."""

    @covers_requirement("sexual-state-handler::sexualstate-exposes-eleven-independent-unbounded-lifetime-behaviour-counters-each-with-exactly-one-sanctioned-mutator")
    def test_no_module_reaches_the_counters_through_private_traits(self):
        root = Path(__file__).parents[3]
        offenders = []
        for directory in (
            root / "world",
            root / "commands",
            root / "typeclasses",
            root / "web",
            root / "server",
            root / "tools",
        ):
            for path in sorted(directory.rglob("*.py")):
                relative = path.relative_to(root).as_posix()
                if "/tests/" in relative or path.name.startswith("test_"):
                    continue
                if relative == "world/rules/sexual_state.py":
                    continue
                source = path.read_text(encoding="utf-8")
                for field in LIFETIME_COUNTER_FIELDS:
                    if f"._traits.{field}" in source:
                        offenders.append(f"{relative} references ._traits.{field}")
        self.assertEqual([], offenders)
