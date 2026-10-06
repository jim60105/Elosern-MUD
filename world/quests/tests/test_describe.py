"""Pure unit tests for the quest-detail rendering layer (task 1.4).

These are read-only ``unittest.TestCase`` tests: ``describe.py`` must import no
writers and never read the world clock (the tick is injected), so every display
rule is a fixed-input pure function.
"""

from tools.spec_traceability import covers_requirement

import importlib
import unittest

from world.tests.synthetic_data import (
    SYNTH_ANCHORS,
    SYNTH_ITEMS,
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    SYNTH_REGIONS,
    synthetic_registries,
)
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
    TEST_ISSUER_KEY,
    anchor_locator,
    bound_instance_locator,
    defeat,
    grid_locator,
    quest,
)

_HOUR = CLOCK_YAML["seconds_per_hour"]

# Rendering runs entirely against the kit's synthetic rows; the scope keeps
# the tier/anchor/item registries synthetic for the describe lookups.
_T_TIER = SYNTH_MONSTER_TIERS["t_faint"].key
_T_ITEM = SYNTH_ITEMS["t_ember_spray"].key
_T_ANCHOR = SYNTH_ANCHORS["t_hollow_tarn"].key


#: Pure rendering input: a private definition key consistent across the
#: record and its definition.
_DEFINITION_KEY = "t_describe_fixture"


def _record(
    definition_key: str = _DEFINITION_KEY,
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
        issuer_key=TEST_ISSUER_KEY,
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
        definition_key=_DEFINITION_KEY,
        issuer_branch_key="t_mossgate_branch",
        reward=QuestReward(
            copper=50,
            items=(ItemQuantity(_T_ITEM, 2),),
            merit=25,
        ),
    )


@synthetic_registries("monster_tiers", "anchors", "anchor_placements", "items")
class DescribeObjectiveTests(unittest.TestCase):
    @covers_requirement("quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive")
    def test_defeat_tier_renders_tier_and_quantity(self):
        tier = SYNTH_MONSTER_TIERS[_T_TIER]
        self.assertEqual(
            describe_objective(defeat(tier=_T_TIER, quantity=1)),
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
        anchor = SYNTH_ANCHORS[_T_ANCHOR]
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
        item = SYNTH_ITEMS[_T_ITEM]
        objective = QuestObjective(
            kind=ObjectiveKind.ACQUIRE,
            quantity=2,
            item_key=_T_ITEM,
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


@synthetic_registries("anchors", "anchor_placements")
class DescribeDestinationTests(unittest.TestCase):
    def test_anchor_uses_registry_display_name(self):
        self.assertEqual(
            describe_destination(anchor_locator()),
            SYNTH_ANCHORS[_T_ANCHOR].display_name_zh,
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
        locator = RoomLocator(DestinationKind.ANCHOR, anchor_key=_T_ANCHOR)
        object.__setattr__(locator, "kind", "bogus")
        with self.assertRaises(QuestDescribeError):
            describe_destination(locator)


@synthetic_registries("items")
class DescribeQuestDetailTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.definition = quest(_DEFINITION_KEY)

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
        self.assertIn(SYNTH_ITEMS[_T_ITEM].display_name_zh, text)

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


# ---------------------------------------------------------------------------
# The species-hunt selector and the authored prose sections (task 3.2). Every
# key below is a kit row or an invented one; the hunt's region, species, and
# variant display names come from the same registries the renderer reads.
# ---------------------------------------------------------------------------
_HUNT_SPECIES = next(iter(SYNTH_MONSTER_SPECIES))
_HUNT_VARIANTS = tuple(
    key
    for key, row in SYNTH_MONSTER_VARIANTS.items()
    if row.species_key == _HUNT_SPECIES
)
_HUNT_ORDINARY = next(
    key for key in _HUNT_VARIANTS if SYNTH_MONSTER_VARIANTS[key].ordinary_variant
)
_HUNT_STRONGER = next(
    key for key in _HUNT_VARIANTS if not SYNTH_MONSTER_VARIANTS[key].ordinary_variant
)
_HUNT_REGION = next(iter(SYNTH_REGIONS))
_RATIONALE = "合成評價理由：合成強勢型成群時壓制力極高，獨行者風險偏高。"
_FLAVOR = "合成背景：合成議會急需合成鬃毛，合成草原因此喧鬧。"

_HUNT_SCOPE = synthetic_registries("regions", "monster_species", "monster_variants")


def _hunt_objective(
    countable: tuple[str, ...] = (_HUNT_ORDINARY, _HUNT_STRONGER),
    *,
    quantity: int = 2,
) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.DEFEAT,
        quantity=quantity,
        region_key=_HUNT_REGION,
        species_key=_HUNT_SPECIES,
        countable_variant_keys=countable,
    )


def _grade_text(definition: QuestDefinition) -> str:
    """The grade line the renderer must show for one definition.

    Read from the CURRENT guild-rank registry (through the shared probe seam)
    rather than pinned as a literal, so the expectation stays a registry fact.
    """
    from world.rules.tests._guild_service_probes import live_guild_rank_registry

    rank = live_guild_rank_registry().get(definition.rank)
    return definition.rank if rank is None else rank.display_name_zh


@_HUNT_SCOPE
class SpeciesHuntDescribeTests(unittest.TestCase):
    """The hunt's requirement line is registry-resolved and deterministic."""

    @covers_requirement(
        "quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive"
    )
    def test_a_hunt_renders_region_species_count_and_variants(self):
        text = describe_objective(_hunt_objective())
        region = SYNTH_REGIONS[_HUNT_REGION]
        species = SYNTH_MONSTER_SPECIES[_HUNT_SPECIES]
        self.assertIn(region.display_name_zh, text)
        self.assertIn(species.display_name_zh, text)
        self.assertIn("2", text)
        for variant_key in (_HUNT_ORDINARY, _HUNT_STRONGER):
            self.assertIn(SYNTH_MONSTER_VARIANTS[variant_key].display_name_zh, text)
        # Display names only: no authored key leaks into player prose.
        for key in (_HUNT_REGION, _HUNT_SPECIES, _HUNT_ORDINARY, _HUNT_STRONGER):
            self.assertNotIn(key, text)

    @covers_requirement(
        "quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive"
    )
    def test_the_variant_order_is_stable_and_key_sorted(self):
        reversed_order = describe_objective(
            _hunt_objective((_HUNT_STRONGER, _HUNT_ORDINARY))
        )
        self.assertEqual(
            reversed_order, describe_objective(_hunt_objective())
        )
        first = min(_HUNT_ORDINARY, _HUNT_STRONGER)
        second = max(_HUNT_ORDINARY, _HUNT_STRONGER)
        self.assertLess(
            reversed_order.index(SYNTH_MONSTER_VARIANTS[first].display_name_zh),
            reversed_order.index(SYNTH_MONSTER_VARIANTS[second].display_name_zh),
        )

    @covers_requirement(
        "quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive"
    )
    def test_unknown_hunt_references_raise(self):
        unknown = (
            ("region", {"countable": (_HUNT_ORDINARY,), "region_key": "t_absent_region"}),
            ("species", {"species_key": "t_absent_species"}),
            ("variant", {"countable": (_HUNT_ORDINARY, "t_absent_variant")}),
        )
        for name, overrides in unknown:
            with self.subTest(reference=name):
                objective = _hunt_objective()
                mutated = QuestObjective(
                    kind=objective.kind,
                    quantity=objective.quantity,
                    region_key=overrides.get("region_key", objective.region_key),
                    species_key=overrides.get("species_key", objective.species_key),
                    countable_variant_keys=overrides.get(
                        "countable", objective.countable_variant_keys
                    ),
                )
                with self.assertRaises(QuestDescribeError):
                    describe_objective(mutated)

    @covers_requirement(
        "quest-detail-view::objective-descriptions-are-deterministic-and-exhaustive"
    )
    def test_rendering_a_hunt_writes_no_lifecycle_state(self):
        objective = _hunt_objective()
        definition = quest(
            "t_describe_hunt",
            stages=(QuestStage(0, objective),),
            rating_rationale_zh=_RATIONALE,
            background_flavor_zh=_FLAVOR,
        )
        before = (definition, objective)
        first = describe_quest_detail(_record("t_describe_hunt"), definition, None, 0)
        second = describe_quest_detail(_record("t_describe_hunt"), definition, None, 0)
        self.assertEqual(first, second)
        self.assertEqual((definition, objective), before)
        module = importlib.import_module(".".join(("world", "quests", "describe")))
        for writer in (
            "apply_quest_log_replacement",
            "apply_quest_log_delta",
            "accept_quest",
            "abandon_quest",
            "fulfill_record",
            "set_quest_tracked",
            "write_reward_claims",
        ):
            with self.subTest(writer=writer):
                self.assertFalse(hasattr(module, writer))


@_HUNT_SCOPE
class AuthoredProseDescribeTests(unittest.TestCase):
    """Grade, rating rationale, and background flavor render as three fields."""

    def _definition(self, **overrides: object) -> QuestDefinition:
        return quest(
            _DEFINITION_KEY,
            stages=(QuestStage(0, _hunt_objective(quantity=1)),),
            **overrides,
        )

    @covers_requirement(
        "quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail"
    )
    def test_grade_rationale_and_flavor_render_as_three_sections(self):
        definition = self._definition(
            rating_rationale_zh=_RATIONALE, background_flavor_zh=_FLAVOR
        )
        text = describe_quest_detail(_record(), definition, None, 0)
        grade = _grade_text(definition)
        self.assertIn(f"階級：{grade}", text)
        self.assertIn(f"評價理由：{_RATIONALE}", text)
        self.assertIn(f"背景：{_FLAVOR}", text)
        # None of them replaces the objective description or the progress line.
        self.assertIn("目標：", text)
        self.assertIn("進度：0 / 1", text)
        self.assertNotIn("已完成", text)

    @covers_requirement(
        "quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail"
    )
    def test_absent_prose_is_omitted_not_fabricated(self):
        text = describe_quest_detail(_record(), self._definition(), None, 0)
        self.assertIn("階級：", text)
        self.assertNotIn("評價理由", text)
        self.assertNotIn("背景", text)

    @covers_requirement(
        "quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail"
    )
    def test_the_targeted_variants_danger_grade_never_becomes_the_grade(self):
        stronger = SYNTH_MONSTER_VARIANTS[_HUNT_STRONGER]
        self.assertIsNotNone(stronger.danger_grade)
        definition = self._definition(
            rating_rationale_zh=_RATIONALE, background_flavor_zh=_FLAVOR
        )
        text = describe_quest_detail(_record(), definition, None, 0)
        self.assertEqual(definition.rank, "F")
        self.assertNotEqual(stronger.danger_grade, definition.rank)
        self.assertIn(f"階級：{_grade_text(definition)}", text)
        self.assertNotIn(stronger.danger_grade, text)

    @covers_requirement(
        "quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail"
    )
    def test_an_authored_rank_without_a_registry_row_still_renders(self):
        definition = self._definition(rank="t_absent_rank")
        text = describe_quest_detail(_record(), definition, None, 0)
        self.assertIn("階級：t_absent_rank", text)


if __name__ == "__main__":
    unittest.main()
