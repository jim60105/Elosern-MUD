"""Tests for the public SexualState handler surface."""

from copy import deepcopy

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.sexual_state import SexualState


class SexualStateTests(EvenniaTest):
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

    def test_optional_fields_default_without_mutating_baseline(self):
        entity = create_object(PlayerCharacter, key="partial baseline")
        baseline = {"arousal": "微興奮", "virgin": True, "sensitivity": {}}
        entity.db.sexual = deepcopy(baseline)
        self.assertEqual(entity.sexual.wetness.level, "乾燥")
        self.assertEqual(entity.db.sexual, baseline)

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
        entity.sexual.arousal.value = "高度"
        entity.sexual.record_climax()
        rebuilt = SexualState(entity)
        self.assertEqual(rebuilt.arousal.level, "高度")
        self.assertEqual(rebuilt.climax_today, 1)
