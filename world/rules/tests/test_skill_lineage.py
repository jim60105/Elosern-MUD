"""Pure tests for the skill-lineage gate, caps, ladder, dedupe, and seeding.

Every case here is ``unittest.TestCase``-pure: stub entities are
``SimpleNamespace`` shapes, the shared kit-shaped synthetic lineage tree
(``synth_lineage_tree``) is the live graph inside a ``skills`` scope, and
injected-graph cases rebuild the load-time caches through
``validate_prerequisite_graph(live_skill_registry())``. The shipped fire
lineage's content contract is owned by the registered skill-catalog
data-contract files, not by this behavior suite.
"""

import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.rules import progression
from world.rules.progression import (
    AFFINITY_ELEMENT_MULTIPLIER,
    FREEFORM_SCALE_LADDER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    PROFICIENCY_TIP_CAP,
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    award_practice_xp,
    can_use_skill,
    freeform_scale_entries_for,
    freeform_scales_for,
    lineage_ownership_closure,
    missing_prerequisite,
    normalize_lineage_record,
    practice_claim_key,
    practice_xp_amount,
    proficiency_cap,
    release_practice_claims,
    reset_practice_dedupe,
    seed_lineage_proficiency,
    skill_proficiency_level,
)
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    declared_prerequisites,
    prerequisite_consumers,
    validate_prerequisite_graph,
)
from world.tests.synthetic_data import (
    SYNTH_RACES,
    SYNTH_SKILLS,
    make_race,
)

from ._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
    synth_lineage_tree,
    synth_lineage_tree_magic,
)

# --- synthetic graph under test ---------------------------------------------

TREE = synth_lineage_tree()
MAGIC_TREE = synth_lineage_tree_magic()

# The tree's element (kit template's borrowed element row) and the runtime
# mastery key production derives for it (P06 freeform idiom: production
# hardcodes ``f"{element}_mastery"``; the row is built under that runtime key).
_TREE_ELEMENT = TREE["t_tree_root"].element.key
_MASTERY_KEY = f"{_TREE_ELEMENT}_mastery"
_MASTERY_ROW = replace(
    SYNTH_SKILLS["t_steady_stride"],
    key=_MASTERY_KEY,
    label="合成元素精通",
    description="對該元素達到最高造詣的合成被動。",
    effects=["passive_trait:element_mastery"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    group=_TREE_ELEMENT,
)

# Elemental-magic damage row on the tree's element: the affinity-factor
# fixture (parsed magic damage of its own element).
_MAGIC_SPELL = replace(
    SYNTH_SKILLS["t_ember_burst"],
    key="t_tree_spell",
    label="木影術",
    description="以元素的共鳴灼烧單一的目標。",
    effects=[f"damage:{_TREE_ELEMENT}:magic"],
)

# A fast-learning race for the learning-multiplier fixture (the kit race's
# own multiplier is 1.0).
_QUICKSTUDY = make_race("t_quickstudy", learning_multiplier=2.0)

# The magic variant is disjoint (prefixed keys/edges), so publishing both
# trees in one registry never changes the martial graph's derived caps.
_ALL_ROWS = {
    **TREE,
    **MAGIC_TREE,
    _MASTERY_KEY: _MASTERY_ROW,
    _MAGIC_SPELL.key: _MAGIC_SPELL,
}


def _fake_skill(
    key: str,
    prerequisites: tuple[SkillPrerequisite, ...] = (),
    kind: SkillKind = SkillKind.ACTIVE,
) -> SkillDef:
    """Build one minimal valid registry-shaped skill for injected graphs."""
    return SkillDef(
        key=key,
        label=f"測試技能{key}",
        description=f"injected lineage fixture {key}",
        kind=kind,
        target_spec=TargetSpec.NONE,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=[],
        category=SkillCategory.UTILITY,
        prerequisites=prerequisites,
    )


def _entity(
    owned: tuple[str, ...] = (),
    proficiency: dict[str, float] | None = None,
    race: str | None = None,
    affinity: tuple[str, ...] = (),
):
    """Build a pure stub entity the progression queries accept."""
    return SimpleNamespace(
        race=race,
        pk=None,
        key="stub",
        skills=SimpleNamespace(owned_keys=lambda: set(owned)),
        db=SimpleNamespace(
            skill_proficiency=dict(proficiency or {}),
            affinity_elements=list(affinity),
            skills={"active": list(owned), "passive": []},
        ),
    )


class PrerequisiteGraphValidationTests(unittest.TestCase):
    """Injected-graph fail-closed validation on locally built registries."""

    def setUp(self):
        reset_practice_dedupe()
        # Injected local registries overwrite the load-time caches; rebuild
        # them for whatever registry is live when the next cache reader runs.
        self.addCleanup(validate_prerequisite_graph, live_skill_registry())

    @covers_requirement("skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed")
    def test_dangling_prerequisite_names_entry_and_key(self):
        registry = {"a": _fake_skill("a", (SkillPrerequisite("not_a_skill", 3),))}
        with self.assertRaises(ValueError) as caught:
            validate_prerequisite_graph(registry)
        message = str(caught.exception)
        self.assertIn("'a'", message)
        self.assertIn("not_a_skill", message)

    @covers_requirement("skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed")
    def test_cycle_is_named_by_the_topological_sort(self):
        registry = {
            "a": _fake_skill("a", (SkillPrerequisite("b", 1),)),
            "b": _fake_skill("b", (SkillPrerequisite("a", 1),)),
            "clean": _fake_skill("clean"),
        }
        with self.assertRaises(ValueError) as caught:
            validate_prerequisite_graph(registry)
        message = str(caught.exception)
        self.assertIn("cyclic", message)
        self.assertIn("'a'", message)
        self.assertIn("'b'", message)
        self.assertNotIn("clean", message)

    @covers_requirement("skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed")
    def test_zero_threshold_fails_at_construction(self):
        with self.assertRaises(ValueError):
            SkillPrerequisite("t_any_skill", 0)

    @covers_requirement("skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed")
    def test_non_integer_and_bool_thresholds_fail_at_construction(self):
        for bad in (1.5, "3", True, False, None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    SkillPrerequisite("t_any_skill", bad)

    @covers_requirement("skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed")
    def test_branching_reverse_map_reports_both_edges(self):
        registry = {
            "root": _fake_skill("root"),
            "mid": _fake_skill("mid", (SkillPrerequisite("root", 3),)),
            "tip": _fake_skill("tip", (SkillPrerequisite("mid", 2),)),
            "branch": _fake_skill("branch", (SkillPrerequisite("root", 5),)),
        }
        reverse = validate_prerequisite_graph(registry)
        self.assertEqual(reverse["root"], (("mid", 3), ("branch", 5)))
        self.assertEqual(reverse["mid"], (("tip", 2),))
        self.assertNotIn("tip", reverse)

    @covers_requirement("skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed")
    def test_merging_skill_declares_several_prerequisites(self):
        registry = {
            "a": _fake_skill("a"),
            "b": _fake_skill("b"),
            "merged": _fake_skill(
                "merged", (SkillPrerequisite("a", 2), SkillPrerequisite("b", 4))
            ),
        }
        reverse = validate_prerequisite_graph(registry)
        self.assertEqual(reverse["a"], (("merged", 2),))
        self.assertEqual(reverse["b"], (("merged", 4),))

    @covers_requirement("skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed")
    def test_validation_is_idempotent(self):
        first = validate_prerequisite_graph(_ALL_ROWS)
        second = validate_prerequisite_graph(_ALL_ROWS)
        self.assertEqual(first, second)
        self.assertEqual(prerequisite_consumers("t_tree_root"), first["t_tree_root"])


class _Scoped(unittest.TestCase):
    """Scoped base: open the kit rows around the whole lifecycle, then
    rebuild the load-time caches against them.

    The kit scope swaps registry contents but never re-validates the
    reverse-edge caches the progression layer captured at import; one
    revalidation per test (inside the scope, which ``setUp`` itself opens)
    binds the caches to the live rows.
    """

    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "races",
            "elements",
            extra={
                "skills": _ALL_ROWS,
                "races": {_QUICKSTUDY.key: _QUICKSTUDY},
            },
        )
        validate_prerequisite_graph(live_skill_registry())


class CanUseSkillTests(_Scoped):
    """The ONE gate matrix on the synthetic tree graph."""

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_root_skill_is_usable_on_ownership_alone(self):
        entity = _entity(("t_tree_root",))
        self.assertTrue(can_use_skill(entity, TREE["t_tree_root"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_unowned_skill_is_denied(self):
        entity = _entity(("t_tree_root",))
        self.assertFalse(can_use_skill(entity, TREE["t_tree_sprout"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_missing_prerequisite_ownership_denies_even_at_high_level(self):
        # Owns sprout at level 5 but NOT root: the edge fails on ownership
        # regardless of the skill's own level.
        entity = _entity(("t_tree_sprout",), {"t_tree_sprout": 250.0})
        self.assertFalse(can_use_skill(entity, TREE["t_tree_sprout"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_sub_threshold_level_denies_and_exact_threshold_passes(self):
        entity = _entity(
            ("t_tree_root", "t_tree_sprout"),
            {"t_tree_root": 2.0 * SKILL_PROFICIENCY_XP_PER_LEVEL + 49},
        )
        self.assertFalse(can_use_skill(entity, TREE["t_tree_sprout"]))
        entity.db.skill_proficiency["t_tree_root"] = 3.0 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(entity, TREE["t_tree_sprout"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_missing_prerequisite_names_the_first_unmet_edge(self):
        entity = _entity(("t_tree_sprout",), {})
        unmet = missing_prerequisite(entity, TREE["t_tree_sprout"])
        self.assertIsNotNone(unmet)
        self.assertEqual(unmet.skill_key, "t_tree_root")
        self.assertEqual(unmet.min_proficiency, 3)
        self.assertIsNone(missing_prerequisite(entity, TREE["t_tree_root"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_gate_is_school_agnostic_on_the_same_path(self):
        # No school branch exists: the identical predicate path answers for
        # any ACTIVE skill, proven by opening/closing only the proficiency
        # factor while everything else (element, affinity, race) stays fixed.
        entity = _entity(
            ("t_tree_sprout", "t_tree_root"),
            {"t_tree_root": 2.0 * SKILL_PROFICIENCY_XP_PER_LEVEL},
        )
        self.assertFalse(can_use_skill(entity, TREE["t_tree_sprout"]))
        entity.db.skill_proficiency["t_tree_root"] = 3.0 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(entity, TREE["t_tree_sprout"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_transitive_chain_requires_every_edge(self):
        entity = _entity(
            ("t_tree_root", "t_tree_sprout", "t_tree_branch", "t_tree_bloom"),
            {
                "t_tree_root": 3.0 * SKILL_PROFICIENCY_XP_PER_LEVEL,
                "t_tree_sprout": 2.0 * SKILL_PROFICIENCY_XP_PER_LEVEL,
            },
        )
        # bloom requires branch >= 5; at level 2 the chain blocks branch's
        # own edge too — open sprout fully and branch unlocks, bloom stays.
        self.assertFalse(can_use_skill(entity, TREE["t_tree_branch"]))
        entity.db.skill_proficiency["t_tree_sprout"] = 3.0 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(entity, TREE["t_tree_branch"]))
        self.assertFalse(can_use_skill(entity, TREE["t_tree_bloom"]))


class TipCapTests(_Scoped):
    """cap(S) = max consuming edge, else the yaml canopy default."""

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_tree_graph_caps(self):
        self.assertEqual(proficiency_cap("t_tree_root"), 3)
        self.assertEqual(proficiency_cap("t_tree_sprout"), 3)
        self.assertEqual(proficiency_cap("t_tree_branch"), 5)
        self.assertEqual(proficiency_cap("t_tree_burrow"), 5)
        self.assertEqual(proficiency_cap("t_tree_bloom"), 8)
        self.assertEqual(proficiency_cap("t_tree_canopy"), 8)
        self.assertEqual(proficiency_cap("t_tree_crownfire"), PROFICIENCY_TIP_CAP)

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_branch_takes_the_maximum_edge(self):
        registry = {
            "root": _fake_skill("root"),
            "a": _fake_skill("a", (SkillPrerequisite("root", 2),)),
            "b": _fake_skill("b", (SkillPrerequisite("root", 6),)),
        }
        validate_prerequisite_graph(registry)
        self.assertEqual(proficiency_cap("root"), 6)

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_award_saturates_at_cap_and_clamps_storage(self):
        entity = _entity()
        for _ in range(10):
            award_practice_xp(entity, "t_tree_root", 40.0)
        self.assertEqual(
            entity.db.skill_proficiency["t_tree_root"],
            3 * SKILL_PROFICIENCY_XP_PER_LEVEL,
        )
        self.assertEqual(skill_proficiency_level(entity, "t_tree_root"), 3)

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_canopy_default_caps_the_unconsumed_node(self):
        entity = _entity()
        for _ in range(60):
            award_practice_xp(entity, "t_tree_crownfire", 40.0)
        self.assertEqual(
            entity.db.skill_proficiency["t_tree_crownfire"],
            PROFICIENCY_TIP_CAP * SKILL_PROFICIENCY_XP_PER_LEVEL,
        )

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_award_fails_closed_on_invalid_amounts(self):
        entity = _entity()
        for bad in (float("nan"), float("inf"), -1.0, True, "1"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    award_practice_xp(entity, "t_tree_root", bad)
        self.assertEqual(entity.db.skill_proficiency, {})

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_saturation_still_unlocks_the_child_edge(self):
        # bloom caps at 8 (canopy edge); award past the ceiling keeps the
        # stored value at the ceiling while the child stays usable.
        entity = _entity(
            ("t_tree_bloom", "t_tree_canopy"),
            {"t_tree_bloom": 8 * SKILL_PROFICIENCY_XP_PER_LEVEL},
        )
        award_practice_xp(entity, "t_tree_bloom", 100.0)  # capped at 8
        self.assertTrue(can_use_skill(entity, TREE["t_tree_canopy"]))


class FreeformLadderTests(_Scoped):
    """Skill-anchored ladder over the cast skill's own proficiency."""

    # The canopy node is unconsumed, so it caps at Lv.10 and its ladder
    # spans every rung.
    CANOPY = "t_tree_crownfire"

    def _master(self, level_xp: float):
        return _entity(
            (self.CANOPY, _MASTERY_KEY), {self.CANOPY: level_xp}
        )

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_ladder_constants(self):
        self.assertEqual(
            FREEFORM_SCALE_LADDER,
            ((0.25, 0), (0.5, 1), (1.0, 3), (2.0, 6), (4.0, 10)),
        )

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_entitled_levels_unlock_rungs(self):
        skill = TREE[self.CANOPY]
        for xp, expected in (
            (0.0, (0.25,)),
            (50.0, (0.25, 0.5)),
            (150.0, (0.25, 0.5, 1.0)),
            (300.0, (0.25, 0.5, 1.0, 2.0)),
            (500.0, (0.25, 0.5, 1.0, 2.0, 4.0)),
        ):
            with self.subTest(xp=xp):
                self.assertEqual(freeform_scales_for(self._master(xp), skill), expected)

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_no_mastery_means_no_ladder(self):
        entity = _entity((self.CANOPY,), {self.CANOPY: 500.0})
        self.assertEqual(freeform_scales_for(entity, TREE[self.CANOPY]), ())

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_ladder_is_skill_anchored_not_element_max(self):
        # High proficiency in a SIBLING node must not raise the canopy's own
        # rung set: the ladder reads the CAST skill's level only.
        entity = _entity(
            (self.CANOPY, _MASTERY_KEY, "t_tree_heartwood"),
            {self.CANOPY: 0.0, "t_tree_heartwood": 500.0},
        )
        self.assertEqual(freeform_scales_for(entity, TREE[self.CANOPY]), (0.25,))

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_unknown_element_entitlement_fails_closed(self):
        with self.assertRaises(ValueError):
            progression.freeform_mastery_entitled(_entity(), "not_an_element")

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_capped_skill_ladder_is_bounded_by_its_tip_cap(self):
        # The root caps at Lv.3; the 1.0 rung needs Lv.3 (passes) and the
        # 2.0 rung needs Lv.6, so the ladder provably stops at 1.0 even on
        # inflated XP — a mid-tree spell never advertises a rung it cannot
        # practise to.
        entity = _entity(("t_tree_root", _MASTERY_KEY), {"t_tree_root": 500.0})
        self.assertEqual(
            freeform_scales_for(entity, TREE["t_tree_root"]),
            (0.25, 0.5, 1.0),
        )

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_scale_entries_follow_the_ladder_with_scaled_costs(self):
        # Entries need an mp-cost spell shape: cast the tree-element spell,
        # whose ladder anchors on its OWN proficiency.
        entity = _entity(
            (_MAGIC_SPELL.key, _MASTERY_KEY),
            {_MAGIC_SPELL.key: 150.0},
        )
        entries = freeform_scale_entries_for(entity, _MAGIC_SPELL)
        self.assertEqual([entry[0] for entry in entries], [0.25, 0.5, 1.0])
        self.assertTrue(all(entry[2] >= 1 for entry in entries))
        self.assertEqual(entries[-1][1], "1")


class PracticeFormulaTests(_Scoped):
    """Closed-form amount: base x race x affinity x growth."""

    def setUp(self):
        super().setUp()
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        patcher.start()
        self.addCleanup(patcher.stop)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_physical_skill_takes_neutral_affinity_even_for_element_affinity(self):
        # The martial tree row carries the element field without a magic
        # damage of its own element: affinity never scales its accrual.
        entity = _entity(("t_tree_root",), race="t_duskmari", affinity=(_TREE_ELEMENT,))
        amount = practice_xp_amount(entity, TREE["t_tree_root"])
        self.assertEqual(amount, SKILL_PRACTICE_XP_PER_USE * 1.0)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_elemental_magic_carries_the_affinity_factor(self):
        favored = _entity(
            (_MAGIC_SPELL.key,), race="t_duskmari", affinity=(_TREE_ELEMENT,)
        )
        unfavored = _entity(
            (_MAGIC_SPELL.key,), race="t_duskmari", affinity=("t_glowmire",)
        )
        self.assertEqual(
            practice_xp_amount(favored, _MAGIC_SPELL),
            SKILL_PRACTICE_XP_PER_USE * AFFINITY_ELEMENT_MULTIPLIER,
        )
        self.assertEqual(
            practice_xp_amount(unfavored, _MAGIC_SPELL),
            SKILL_PRACTICE_XP_PER_USE * NON_AFFINITY_ELEMENT_MULTIPLIER,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_race_multiplier_participates(self):
        quickstudy = _entity(("t_tree_root",), race=_QUICKSTUDY.key)
        baseline = _entity(("t_tree_root",), race="t_duskmari")
        self.assertEqual(
            practice_xp_amount(quickstudy, TREE["t_tree_root"]),
            SKILL_PRACTICE_XP_PER_USE * _QUICKSTUDY.learning_multiplier,
        )
        self.assertEqual(
            practice_xp_amount(baseline, TREE["t_tree_root"]),
            SKILL_PRACTICE_XP_PER_USE * SYNTH_RACES["t_duskmari"].learning_multiplier,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_growth_multiplier_participates(self):
        with patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.5):
            entity = _entity(("t_tree_root",), race="t_duskmari")
            self.assertEqual(
                practice_xp_amount(entity, TREE["t_tree_root"]),
                SKILL_PRACTICE_XP_PER_USE * 1.5,
            )


class PracticeDedupeTests(_Scoped):
    """One accrual per (actor, skill, target) per tick; explicit release."""

    STRIKE = "t_tree_root"

    def setUp(self):
        super().setUp()
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tick = {"value": 7}
        tick_patch = patch.object(progression, "_current_tick", lambda: self.tick["value"])
        tick_patch.start()
        self.addCleanup(tick_patch.stop)

    def test_same_triple_twice_in_one_tick_accrues_once(self):
        actor = _entity((self.STRIKE,), race="t_duskmari")
        target = SimpleNamespace(pk=101, key="t1")
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, self.STRIKE, target)
        )
        self.assertFalse(
            progression.grant_skill_practice_xp(actor, self.STRIKE, target)
        )
        self.assertEqual(
            actor.db.skill_proficiency[self.STRIKE], SKILL_PRACTICE_XP_PER_USE
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_distinct_targets_each_accrue(self):
        actor = _entity((self.STRIKE,), race="t_duskmari")
        for index in range(3):
            target = SimpleNamespace(pk=200 + index, key=f"t{index}")
            self.assertTrue(
                progression.grant_skill_practice_xp(actor, self.STRIKE, target)
            )
        self.assertEqual(
            actor.db.skill_proficiency[self.STRIKE],
            3 * SKILL_PRACTICE_XP_PER_USE,
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_no_target_skills_dedupe_on_none(self):
        actor = _entity((self.STRIKE,), race="t_duskmari")
        self.assertTrue(progression.grant_skill_practice_xp(actor, self.STRIKE))
        self.assertFalse(progression.grant_skill_practice_xp(actor, self.STRIKE))

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_tick_change_clears_the_claims(self):
        actor = _entity((self.STRIKE,), race="t_duskmari")
        self.assertTrue(progression.grant_skill_practice_xp(actor, self.STRIKE))
        self.tick["value"] = 8
        self.assertTrue(progression.grant_skill_practice_xp(actor, self.STRIKE))
        self.assertEqual(
            actor.db.skill_proficiency[self.STRIKE],
            2 * SKILL_PRACTICE_XP_PER_USE,
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_release_lets_a_same_tick_retry_accrue(self):
        actor = _entity((self.STRIKE,), race="t_duskmari")
        self.assertTrue(progression.grant_skill_practice_xp(actor, self.STRIKE))
        claim = practice_claim_key(actor, self.STRIKE, None)
        self.assertIn(
            claim, progression.practice_claims_for(actor, self.STRIKE)
        )
        release_practice_claims([claim])
        self.assertTrue(progression.grant_skill_practice_xp(actor, self.STRIKE))

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_passive_unknown_and_simulated_grant_nothing(self):
        actor = _entity(
            (self.STRIKE, SYNTH_SKILLS["t_steady_stride"].key), race="t_duskmari"
        )
        self.assertFalse(
            progression.grant_skill_practice_xp(
                actor, SYNTH_SKILLS["t_steady_stride"].key
            )
        )
        self.assertFalse(progression.grant_skill_practice_xp(actor, "not_a_skill"))
        self.assertFalse(
            progression.grant_skill_practice_xp(
                actor, self.STRIKE, nonlethal=True
            )
        )
        self.assertEqual(actor.db.skill_proficiency, {})

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_saturated_skill_accrues_nothing_new(self):
        ceiling = proficiency_cap(self.STRIKE) * SKILL_PROFICIENCY_XP_PER_LEVEL
        actor = _entity(
            (self.STRIKE,),
            race="t_duskmari",
            proficiency={self.STRIKE: ceiling},
        )
        progression.grant_skill_practice_xp(actor, self.STRIKE)
        self.assertEqual(actor.db.skill_proficiency[self.STRIKE], ceiling)


class LineageSeedTests(_Scoped):
    """Fixed-point seeding, ownership closure, and record normalization."""

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_full_chain_cascade_seeds_exact_edge_values(self):
        closure_active, closure_passive = lineage_ownership_closure(["t_tree_bloom"])
        self.assertEqual(
            closure_active, ["t_tree_branch", "t_tree_root", "t_tree_sprout"]
        )
        self.assertEqual(closure_passive, [])
        seeded = seed_lineage_proficiency(["t_tree_bloom", *closure_active], None)
        self.assertEqual(
            seeded,
            {
                "t_tree_branch": 250.0,
                "t_tree_sprout": 150.0,
                "t_tree_root": 150.0,
            },
        )

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_deep_seed_cascades_to_the_root(self):
        active, _ = lineage_ownership_closure(["t_tree_crownfire"])
        seeded = seed_lineage_proficiency(["t_tree_crownfire", *active], None)
        self.assertEqual(
            seeded,
            {
                # Each ancestor is seeded to the TIGHTEST edge that names it
                # (max over edges): only the chain consumes these nodes —
                # the sister leaves are not owned here.
                "t_tree_heartwood": 400.0,
                "t_tree_canopy": 400.0,
                "t_tree_bloom": 400.0,
                "t_tree_branch": 250.0,
                "t_tree_sprout": 150.0,
                "t_tree_root": 150.0,
            },
        )
        entity = _entity(("t_tree_crownfire", *active), seeded)
        for key in ("t_tree_sprout", "t_tree_bloom", "t_tree_crownfire"):
            with self.subTest(key=key):
                self.assertTrue(can_use_skill(entity, TREE[key]))

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_explicit_below_edge_wins_and_is_never_overwritten(self):
        seeded = seed_lineage_proficiency(
            ["t_tree_bloom", "t_tree_branch", "t_tree_sprout", "t_tree_root"],
            {"t_tree_branch": 120.0},
        )
        self.assertEqual(seeded["t_tree_branch"], 120.0)
        # root (edge under sprout) still seeds normally.
        self.assertEqual(seeded["t_tree_root"], 150.0)

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_seed_is_idempotent(self):
        once = seed_lineage_proficiency(["t_tree_bloom"], None)
        twice = seed_lineage_proficiency(["t_tree_bloom"], once)
        self.assertEqual(once, twice)

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_normalize_record_closes_and_seeds(self):
        record = {"skills": ["t_tree_bloom"], "passives": []}
        normalized = normalize_lineage_record(record)
        self.assertEqual(
            sorted(normalized["skills"]),
            ["t_tree_bloom", "t_tree_branch", "t_tree_root", "t_tree_sprout"],
        )
        self.assertEqual(normalized["passives"], [])
        self.assertEqual(
            normalized["skill_proficiency"],
            {"t_tree_branch": 250.0, "t_tree_sprout": 150.0, "t_tree_root": 150.0},
        )
        # Idempotent + input untouched.
        again = normalize_lineage_record(normalized)
        self.assertEqual(again["skills"], normalized["skills"])
        self.assertEqual(
            again["skill_proficiency"], normalized["skill_proficiency"]
        )
        self.assertEqual(record["skills"], ["t_tree_bloom"])

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_normalize_keeps_unknown_keys_for_the_semantic_check(self):
        record = {"skills": ["not_a_skill"], "passives": []}
        normalized = normalize_lineage_record(record)
        self.assertEqual(normalized["skills"], ["not_a_skill"])
        self.assertNotIn("skill_proficiency", normalized)


class ProficiencyCapTableTests(_Scoped):
    """The yaml canopy default is a real bound, not a placeholder."""

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_canopy_default_is_a_positive_bound(self):
        self.assertGreaterEqual(PROFICIENCY_TIP_CAP, 1)
        # The rulebook key is a YAML quantity (PROFICIENCY_TIP_CAP derives
        # from it); the ladder's top rung is practised only by unconsumed
        # nodes, so the canopy must reach it.
        self.assertGreaterEqual(PROFICIENCY_TIP_CAP, FREEFORM_SCALE_LADDER[-1][1])

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_no_edge_is_above_its_prerequisites_cap(self):
        for key, skill in live_skill_registry().items():
            for prereq in skill.prerequisites:
                self.assertGreaterEqual(
                    proficiency_cap(prereq.skill_key),
                    prereq.min_proficiency,
                    f"{key} edge exceeds cap({prereq.skill_key})",
                )


class DerivedUnlockSinkTests(_Scoped):
    """``unlocks_out`` appends exactly one derived line per false->true flip."""

    def setUp(self):
        super().setUp()
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tick = {"value": 11}
        tick_patch = patch.object(progression, "_current_tick", lambda: self.tick["value"])
        tick_patch.start()
        self.addCleanup(tick_patch.stop)

    def _near_edge(self):
        """Owner with sprout at level 2: branch not yet usable."""
        return _entity(
            ("t_tree_root", "t_tree_sprout", "t_tree_branch"),
            {
                "t_tree_root": SKILL_PROFICIENCY_XP_PER_LEVEL * 10,
                "t_tree_sprout": SKILL_PROFICIENCY_XP_PER_LEVEL * 2 + 49,
            },
            race="t_duskmari",
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp",
        "skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification")
    def test_crossing_an_edge_appends_exactly_one_line(self):
        actor = self._near_edge()
        sink: list[str] = []
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, "t_tree_sprout", unlocks_out=sink)
        )
        self.assertEqual(sink, [f"新技能可用：{TREE['t_tree_branch'].label}"])

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp",
        "skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification")
    def test_a_second_award_after_the_flip_appends_nothing(self):
        actor = self._near_edge()
        sink: list[str] = []
        progression.grant_skill_practice_xp(actor, "t_tree_sprout", unlocks_out=sink)
        self.assertEqual(len(sink), 1)
        # Same tick: the dedupe claim suppresses the award itself.
        self.assertFalse(
            progression.grant_skill_practice_xp(actor, "t_tree_sprout", unlocks_out=sink)
        )
        self.assertEqual(len(sink), 1)
        # New tick: the award runs again but the child is already usable.
        self.tick["value"] = 12
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, "t_tree_sprout", unlocks_out=sink)
        )
        self.assertEqual(len(sink), 1)

    def test_nonlethal_and_deduped_awards_touch_the_sink_not_at_all(self):
        actor = self._near_edge()
        sink: list[str] = []
        self.assertFalse(
            progression.grant_skill_practice_xp(
                actor, "t_tree_sprout", nonlethal=True, unlocks_out=sink
            )
        )
        self.assertEqual(sink, [])
        self.assertEqual(
            actor.db.skill_proficiency["t_tree_sprout"],
            SKILL_PROFICIENCY_XP_PER_LEVEL * 2 + 49,
        )

    def test_sink_is_optional_for_existing_callers(self):
        actor = self._near_edge()
        self.assertTrue(progression.grant_skill_practice_xp(actor, "t_tree_sprout"))

    def test_wording_splits_on_skill_category(self):
        spell = MAGIC_TREE["magic_t_tree_bloom"]
        physical = TREE["t_tree_bloom"]
        self.assertEqual(
            progression.unlock_line(spell), f"新法術可用：{spell.label}"
        )
        self.assertEqual(
            progression.unlock_line(physical), f"新技能可用：{physical.label}"
        )

    def test_unlock_candidates_are_the_reverse_edge_consumers(self):
        keys = [
            skill.key for skill in progression.unlock_candidates_for("t_tree_sprout")
        ]
        # Disjoint trees: only the martial branch consumes the sprout.
        self.assertEqual(keys, ["t_tree_branch"])

    @covers_requirement("skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification")
    def test_seeded_lineage_crosses_edges_silently(self):
        # Seeding writes proficiency directly (no grant, no sink): the
        # notification surface belongs to live awards only.
        actor = _entity(
            ("t_tree_root", "t_tree_sprout", "t_tree_branch"), race="t_duskmari"
        )
        actor.db.skill_proficiency = seed_lineage_proficiency(
            ("t_tree_root", "t_tree_sprout", "t_tree_branch"), {}
        )
        self.assertTrue(can_use_skill(actor, TREE["t_tree_branch"]))


class StudyPracticeGrantTests(_Scoped):
    """Closed-form booked-study grants (declared-practice-skip D7)."""

    def setUp(self):
        super().setUp()
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        self.addCleanup(patcher.stop)
        patcher.start()

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_hourly_grant_is_the_shared_composite_times_whole_hours(self):
        entity = _entity(owned=("t_tree_root",), race="t_duskmari")
        self.assertTrue(
            progression.grant_study_practice_xp(entity, "t_tree_root", 8)
        )
        per_use = practice_xp_amount(entity, TREE["t_tree_root"])
        # One formula, two entry points: 8 booked hours award 8 ×
        # PRACTICE_XP_PER_STUDY_HOUR / SKILL_PRACTICE_XP_PER_USE = 80 uses.
        self.assertAlmostEqual(
            entity.db.skill_proficiency["t_tree_root"], 80.0 * per_use
        )

    def test_growth_buff_and_learning_scale_the_hourly_grant(self):
        entity = _entity(owned=("t_tree_root",), race="t_duskmari")
        with patch("world.rules.buffs.growth_rate_multiplier", lambda e: 2.0):
            self.assertTrue(
                progression.grant_study_practice_xp(entity, "t_tree_root", 1)
            )
        # 1h x composite growth 2.0 stays under the derived ceiling: the buff
        # composite is the one the per-use path shares, not a re-derived copy.
        self.assertAlmostEqual(
            entity.db.skill_proficiency["t_tree_root"],
            progression.PRACTICE_XP_PER_STUDY_HOUR * 2.0,
        )
        quickstudy = _entity(owned=("t_tree_root",), race=_QUICKSTUDY.key)
        progression.grant_study_practice_xp(quickstudy, "t_tree_root", 1)
        # 1h x learning 2.0 for the quick-study race.
        self.assertAlmostEqual(
            quickstudy.db.skill_proficiency["t_tree_root"],
            progression.PRACTICE_XP_PER_STUDY_HOUR * _QUICKSTUDY.learning_multiplier,
        )

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_booked_award_saturates_identically_to_per_use_award(self):
        cap = proficiency_cap("t_tree_root")
        ceiling = cap * SKILL_PROFICIENCY_XP_PER_LEVEL
        studied = _entity(
            owned=("t_tree_root",), proficiency={"t_tree_root": ceiling - 10.0}
        )
        self.assertTrue(
            progression.grant_study_practice_xp(studied, "t_tree_root", 8)
        )
        self.assertEqual(studied.db.skill_proficiency["t_tree_root"], ceiling)
        used = _entity(
            owned=("t_tree_root",), proficiency={"t_tree_root": ceiling - 10.0}
        )
        award_practice_xp(used, "t_tree_root", 10.0 * cap)
        self.assertEqual(
            studied.db.skill_proficiency["t_tree_root"],
            used.db.skill_proficiency["t_tree_root"],
        )
        # Beyond the ceiling the booked grant writes nothing further.
        self.assertTrue(
            progression.grant_study_practice_xp(studied, "t_tree_root", 8)
        )
        self.assertEqual(studied.db.skill_proficiency["t_tree_root"], ceiling)

    def test_nonpositive_hours_are_no_op_and_bad_types_raise(self):
        entity = _entity(owned=("t_tree_root",), race="t_duskmari")
        self.assertFalse(
            progression.grant_study_practice_xp(entity, "t_tree_root", 0)
        )
        self.assertFalse(
            progression.grant_study_practice_xp(entity, "t_tree_root", -3)
        )
        self.assertEqual(entity.db.skill_proficiency, {})
        with self.assertRaises(ValueError):
            progression.grant_study_practice_xp(entity, "t_tree_root", True)
        with self.assertRaises(ValueError):
            progression.grant_study_practice_xp(entity, "t_tree_root", 1.5)
        self.assertEqual(entity.db.skill_proficiency, {})

    def test_unknown_and_passive_skills_grant_nothing(self):
        entity = _entity(
            owned=("t_tree_root", SYNTH_SKILLS["t_steady_stride"].key),
            race="t_duskmari",
        )
        self.assertFalse(
            progression.grant_study_practice_xp(entity, "not_a_skill", 4)
        )
        self.assertFalse(
            progression.grant_study_practice_xp(
                entity, SYNTH_SKILLS["t_steady_stride"].key, 4
            )
        )
        self.assertEqual(entity.db.skill_proficiency, {})
