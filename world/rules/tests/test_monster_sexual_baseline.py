"""Tests for monster and generic sexual-state defaults."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.entities import LivingEntity
from typeclasses.monsters import Monster
from world.rules.sexual_state import SexualState


class MonsterSexualBaselineTests(EvenniaTest):
    def test_monster_uses_floors_lazy_sensitivity_and_shame_clamp(self):
        state = create_object(Monster, key="monster baseline").sexual
        self.assertEqual(
            (
                state.arousal.level,
                state.wetness.level,
                state.shame.level,
                state.exposure.level,
                state.climax_phase.level,
            ),
            ("平靜", "乾燥", "無", "極低", "未達"),
        )
        self.assertEqual(state.sensitivity["尾巴"].level, "普通")
        state.shame.value = "強烈"
        self.assertEqual(state.shame.level, "無")
        state.arousal.value = "高度"
        self.assertEqual(state.arousal.level, "高度")

    def test_monster_shame_clamp_survives_handler_reconstruction(self):
        entity = create_object(Monster, key="persistent monster clamp")
        self.assertEqual(entity.sexual.shame.max, 0)
        rebuilt = SexualState(entity)
        self.assertEqual(rebuilt.shame.max, 0)
        rebuilt.shame.value = "強烈"
        self.assertEqual(rebuilt.shame.level, "無")

    def test_generic_default_does_not_clamp_shame(self):
        state = create_object(LivingEntity, key="generic baseline").sexual
        state.shame.value = "強烈"
        self.assertEqual(state.shame.level, "強烈")
