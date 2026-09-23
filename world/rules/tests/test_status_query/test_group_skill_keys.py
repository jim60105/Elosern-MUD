"""Data-contract test: holy_rite grouping order is asserted over shipped SKILL_REGISTRY rows

Slice of ``test_status_query``: the skill-key grouping rules and the
level-reference comparison.
"""
from collections.abc import Mapping, Sequence
from dataclasses import replace
import unittest
from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.buffs import apply_buff
from world.rules.combat_session import engage
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.rules.status_query import (
    StatusQueryError,
    build_character_read_model,
    build_status_read_model,
    group_skill_keys,
)
from world.skills.handler import INNATE_SKILL_ORDER
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries
from .._combat_session_helpers import (
    _live_registry,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
# ``flee`` is injected into ``SKILL_REGISTRY`` at import time by
# ``world.rules.disengage`` (the ``universal-action-ownership`` dependency
# direction), so the grouping and split tests import it explicitly to keep
# ``flee`` in scope.
import world.rules.disengage  # noqa: F401  (registers flee)


from ._support import (
    _LOCAL_SKILLS,
    _T_EL_A,
    _T_EL_B,
    _T_EL_C,
    _T_MART_A,
    _T_MART_B,
    _T_MART_C,
    _T_REST,
    _T_SEX_A,
    _T_SEX_B,
    _T_RITE_A,
    _T_RITE_B,
    _element_rows,
)


class GroupSkillKeysTests(unittest.TestCase):
    """Pure grouping tests for the out-of-combat skill taxonomy.

    ``group_skill_keys`` reads only the module-level registries, so these
    tests run without an entity or database; the skill catalogue is scoped to
    this file's local rows while the element vocabulary stays the live shipped
    registry (the ordering contract IS that registry's declaration order).
    """

    def setUp(self):
        self.element_keys, self.element_labels, element_rows = _element_rows()
        patcher = synthetic_registries(
            "skills",
            extra={
                "skills": {
                    **_LOCAL_SKILLS,
                    **element_rows,
                    "rite_lamb_mark": SKILL_REGISTRY["rite_lamb_mark"],
                    "rite_anointing_touch": SKILL_REGISTRY["rite_anointing_touch"],
                    "poverty_vow": SKILL_REGISTRY["poverty_vow"],
                }
            },
        )
        patcher.__enter__()
        self.addCleanup(patcher.__exit__, None, None, None)

    def _flatten(self, views):
        return [
            (category.label, [(group.label, [row.key for row in group.skills])
                              for group in category.groups])
            for category in views
        ]

    @covers_requirement(
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel"
    )
    def test_category_order_follows_skillcategory_declaration_order(self):
        views = group_skill_keys([_T_EL_A, _T_MART_A, _T_REST[0]])
        self.assertEqual(
            [view.category for view in views],
            ["elemental_magic", "martial_arts", "enhancement"],
        )

    @covers_requirement(
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel"
    )
    def test_elemental_sub_groups_follow_element_registry_order(self):
        # The three element rows bind to the first three shipped element keys
        # in declaration order; the grouping must emit them in registry order
        # regardless of the input order, with the registry's own labels.
        views = group_skill_keys([_T_EL_C, _T_EL_A, _T_EL_B])
        self.assertEqual(
            [[group.group for group in view.groups] for view in views],
            [list(self.element_keys)],
        )
        self.assertEqual(
            [group.label for group in views[0].groups],
            list(self.element_labels),
        )

    def test_empty_category_is_omitted(self):
        views = group_skill_keys([_T_EL_A])
        self.assertEqual(
            [view.category for view in views], ["elemental_magic"]
        )
        self.assertNotIn(
            "sexual_act",
            [view.category for view in views],
            "an entity owning no sexual-act skill must see no sexual_act category",
        )

    @covers_requirement(
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel"
    )
    def test_enhancement_sub_groups_follow_tag_order(self):
        # Enhancement sub-groups follow fixed order: None -> 天賦 -> 身法
        # Local fixture keys passed in reverse order:
        # _T_REST[2] ("身法"), _T_REST[1] ("天賦"), _T_REST[0] (None).
        views = group_skill_keys([_T_REST[2], _T_REST[1], _T_REST[0]])
        self.assertEqual([view.category for view in views], ["enhancement"])
        self.assertEqual(
            [group.group for group in views[0].groups],
            [None, "天賦", "身法"],
        )
        self.assertEqual(
            [group.label for group in views[0].groups],
            [None, "天賦", "身法"],
        )
        self.assertEqual(
            [row.key for group in views[0].groups for row in group.skills],
            [_T_REST[0], _T_REST[1], _T_REST[2]],
        )

    @covers_requirement(
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel"
    )
    def test_holy_rite_sub_groups_follow_tag_order(self):
        # Holy rite sub-groups follow fixed order: None -> 聖禮
        # Pass in reverse order: _T_RITE_B ("聖禮"), _T_RITE_A (None).
        views = group_skill_keys([_T_RITE_B, _T_RITE_A])
        self.assertEqual([view.category for view in views], ["holy_rite"])
        self.assertEqual(
            [group.group for group in views[0].groups],
            [None, "聖禮"],
        )
        self.assertEqual(
            [group.label for group in views[0].groups],
            [None, "聖禮"],
        )
        self.assertEqual(
            [row.key for group in views[0].groups for row in group.skills],
            [_T_RITE_A, _T_RITE_B],
        )

    @covers_requirement(
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel"
    )
    def test_owned_holy_rite_rows_list_in_seventh_group_and_passives_stay_enhancement(self):
        # Scenario: Owned holy-rite rows list in the seventh group under the client bound
        # Actives end with holy_rite group (null then 聖禮), poverty_vow stays enhancement
        actives = group_skill_keys(["rite_anointing_touch", "rite_lamb_mark"])
        self.assertEqual(actives[-1].category, "holy_rite")
        self.assertEqual(actives[-1].label, "神聖聖儀")
        self.assertEqual(
            [group.group for group in actives[-1].groups],
            [None, "聖禮"],
        )
        self.assertEqual(
            [row.key for group in actives[-1].groups for row in group.skills],
            ["rite_lamb_mark", "rite_anointing_touch"],
        )
        passives = group_skill_keys(["poverty_vow"])
        self.assertEqual([view.category for view in passives], ["enhancement"])
        self.assertNotIn("holy_rite", [view.category for view in passives])

    @covers_requirement(
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel"
    )
    def test_ungrouped_category_emits_exactly_one_null_keyed_sub_group(self):
        views = group_skill_keys([_T_MART_A, _T_MART_B])
        self.assertEqual([view.category for view in views], ["martial_arts"])
        self.assertEqual(len(views[0].groups), 1)
        group = views[0].groups[0]
        self.assertIsNone(group.group)
        self.assertIsNone(group.label)
        self.assertEqual(
            [row.key for row in group.skills], [_T_MART_A, _T_MART_B]
        )

    def test_row_order_matches_owned_keys_order_without_alphabetizing(self):
        views = group_skill_keys([_T_MART_C, _T_MART_A, _T_MART_B])
        self.assertEqual(
            [row.key for row in views[0].groups[0].skills],
            [_T_MART_C, _T_MART_A, _T_MART_B],
        )

    def test_sexual_act_sub_groups_follow_first_seen_group_order(self):
        views = group_skill_keys([_T_SEX_A, _T_SEX_B, _T_SEX_A])
        self.assertEqual([view.category for view in views], ["sexual_act"])
        self.assertEqual(
            [group.group for group in views[0].groups],
            ["t_sexp_a", "t_sexp_b"],
        )

    @covers_requirement(
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel"
    )
    def test_unknown_key_lands_in_a_synthetic_bucket_after_every_real_category(self):
        views = group_skill_keys([_T_EL_A, "no_such_skill", "also_missing"])
        self.assertEqual(
            [view.category for view in views],
            ["elemental_magic", "unknown"],
        )
        fallback = views[-1]
        self.assertEqual(fallback.label, "未知技能")
        self.assertEqual(len(fallback.groups), 1)
        self.assertIsNone(fallback.groups[0].group)
        self.assertEqual(
            [(row.key, row.label) for row in fallback.groups[0].skills],
            [("no_such_skill", "no_such_skill"), ("also_missing", "also_missing")],
        )

    def test_category_labels_are_the_canonical_traditional_chinese_forms(self):
        views = group_skill_keys(
            [_T_EL_A, _T_MART_A, _T_REST[0], _T_REST[3], _T_REST[4], _T_SEX_A, _T_RITE_A]
        )
        self.assertEqual(
            [view.label for view in views],
            ["元素魔法", "武技", "強化", "神之秘法", "特殊", "性愛行為", "神聖聖儀"],
        )

    def test_group_skill_keys_is_empty_for_no_keys(self):
        self.assertEqual(group_skill_keys([]), ())


class LevelRefComparisonTests(unittest.TestCase):
    def test_ordinal_comparisons_accept_levelref_str_and_int(self):
        from world.rules.status_query import _LevelRef

        levels = ("a", "b", "c")
        ref = _LevelRef(1, levels)
        self.assertEqual(ref, _LevelRef(1, levels))
        self.assertEqual(ref, "b")
        self.assertEqual(ref == 1, True)
        self.assertTrue(ref >= 0)
        self.assertTrue(ref <= "c")
        self.assertTrue(ref < 2)
        self.assertTrue(ref > 0)
