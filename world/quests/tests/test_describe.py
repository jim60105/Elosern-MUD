"""Pure unit tests for the quest-detail rendering layer (task 1.4).

These are read-only ``unittest.TestCase`` tests: ``describe.py`` must import no
writers and never read the world clock (the tick is injected), so every display
rule is a fixed-input pure function.
"""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.anchors import ANCHOR_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
)
from world.quests.describe import (
    QuestDescribeError,
    describe_destination,
    describe_objective,
    describe_quest_detail,
)
from world.quests.runtime import QuestRecord, QuestState
from world.rules.guild_offers import (
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
)
from world.rules.clock import CLOCK_YAML

from ._fixtures import (
    anchor_locator,
    bound_instance_locator,
    defeat,
    grid_locator,
    quest,
)

_HOUR = CLOCK_YAML["seconds_per_hour"]


def _record(
    definition_key: str = "introductory_hunt",
    *,
    state: QuestState = QuestState.IN_PROGRESS,
    stage_index: int = 0,
    stage_progress: int = 0,
    deadline_tick: int | None = None,
    failure_reason: str | None = None,
) -> QuestRecord:
    return QuestRecord(
        quest_id=f"{definition_key}:1",
        definition_key=definition_key,
        state=state,
        stage_index=stage_index,
        stage_progress=stage_progress,
        deadline_tick=deadline_tick,
        accepted_tick=0,
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
        failure_reason=failure_reason,
    )


def _offer() -> GuildQuestOffer:
    return GuildQuestOffer(
        definition_key="introductory_hunt",
        issuer_branch_key="guild_branch_altoria",
        reward=QuestReward(
            copper=50,
            items=(ItemQuantity("healing_potion", 2),),
            merit=25,
        ),
    )


class DescribeObjectiveTests(unittest.TestCase):
    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_defeat_tier_renders_tier_and_quantity(self):
        tier = MONSTER_TIER_REGISTRY["low"]
        self.assertEqual(
            describe_objective(defeat(tier="low", quantity=1)),
            f"討伐 1 隻{tier.display_name_zh}魔物",
        )

    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_defeat_bound_targets_renders_binding(self):
        self.assertEqual(
            describe_objective(defeat(bound=True, quantity=3)),
            "討伐綁定的目標 3 個",
        )

    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_reach_anchor_renders_anchor_display_name(self):
        anchor = ANCHOR_REGISTRY["capital_altoria"]
        objective = QuestObjective(
            kind=ObjectiveKind.REACH,
            destination=anchor_locator(),
        )
        self.assertEqual(
            describe_objective(objective),
            f"抵達{anchor.display_name_zh}",
        )

    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_reach_grid_renders_exact_coordinates(self):
        objective = QuestObjective(
            kind=ObjectiveKind.REACH,
            destination=grid_locator(2, 1),
        )
        self.assertEqual(describe_objective(objective), "抵達座標 (2, 1)")

    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_reach_bound_instance_renders_generic_destination(self):
        objective = QuestObjective(
            kind=ObjectiveKind.REACH,
            destination=bound_instance_locator(),
        )
        self.assertEqual(describe_objective(objective), "抵達指定的地點")

    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_escort_renders_protected_entity_requirement(self):
        objective = QuestObjective(
            kind=ObjectiveKind.ESCORT,
            destination=anchor_locator(),
        )
        self.assertIn("護送", describe_objective(objective))
        self.assertIn("保護", describe_objective(objective))

    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_acquire_renders_item_and_count(self):
        item = ITEM_REGISTRY["healing_potion"]
        objective = QuestObjective(
            kind=ObjectiveKind.ACQUIRE,
            quantity=2,
            item_key="healing_potion",
        )
        self.assertEqual(
            describe_objective(objective),
            f"收集 2 個{item.display_name_zh}",
        )

    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_unknown_objective_kind_raises(self):
        objective = QuestObjective(
            kind=ObjectiveKind.DEFEAT,
            monster_tier="low",
        )
        object.__setattr__(objective, "kind", "bogus")
        with self.assertRaises(QuestDescribeError):
            describe_objective(objective)


class DescribeDestinationTests(unittest.TestCase):
    def test_anchor_uses_registry_display_name(self):
        self.assertEqual(
            describe_destination(anchor_locator()),
            ANCHOR_REGISTRY["capital_altoria"].display_name_zh,
        )

    def test_grid_uses_exact_coordinates(self):
        self.assertEqual(
            describe_destination(grid_locator(3, 1)),
            "座標 (3, 1)",
        )

    def test_bound_instance_is_generic(self):
        self.assertEqual(
            describe_destination(bound_instance_locator()),
            "指定的地點",
        )

    def test_unknown_destination_kind_raises(self):
        locator = RoomLocator(DestinationKind.ANCHOR, anchor_key="capital_altoria")
        object.__setattr__(locator, "kind", "bogus")
        with self.assertRaises(QuestDescribeError):
            describe_destination(locator)


class DescribeQuestDetailTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.definition = quest("introductory_hunt")

    def test_full_detail_assembles_name_state_stage_progress(self):
        text = describe_quest_detail(
            _record(stage_progress=1),
            self.definition,
            None,
            0,
        )
        self.assertIn(self.definition.display_name, text)
        self.assertIn("進行中", text)
        self.assertIn("階段：1", text)
        self.assertIn("進度：1 / 1", text)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_reward_section_rendered_when_offer_present(self):
        text = describe_quest_detail(
            _record(),
            self.definition,
            _offer(),
            0,
        )
        self.assertIn("獎勵：銅 50", text)
        self.assertIn("功績 25", text)
        self.assertIn("治療藥水", text)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_reward_section_omitted_when_offer_absent(self):
        text = describe_quest_detail(_record(), self.definition, None, 0)
        self.assertNotIn("獎勵", text)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_deadline_renders_remaining_hours_when_future(self):
        text = describe_quest_detail(
            _record(deadline_tick=5 * _HOUR),
            self.definition,
            None,
            0,
        )
        self.assertIn("剩餘 5 小時", text)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_deadline_renders_under_one_hour_when_positive(self):
        text = describe_quest_detail(
            _record(deadline_tick=30 * 60),
            self.definition,
            None,
            0,
        )
        self.assertIn("不足 1 小時", text)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_deadline_renders_expired_when_non_positive(self):
        text = describe_quest_detail(
            _record(deadline_tick=_HOUR),
            self.definition,
            None,
            _HOUR,
        )
        self.assertIn("已逾期", text)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_deadline_omitted_when_none(self):
        text = describe_quest_detail(_record(), self.definition, None, 0)
        self.assertNotIn("期限", text)

    def test_terminal_state_label_is_rendered(self):
        text = describe_quest_detail(
            _record(state=QuestState.COMPLETED, stage_progress=1),
            self.definition,
            None,
            0,
        )
        self.assertIn("已完成", text)

    def test_failed_state_label_is_rendered(self):
        text = describe_quest_detail(
            _record(state=QuestState.FAILED, failure_reason="abandoned"),
            self.definition,
            None,
            0,
        )
        self.assertIn("已失敗", text)


if __name__ == "__main__":
    unittest.main()
