"""Pure tests for the skill-lineage gate, caps, ladder, dedupe, and seeding.

Every case here is ``unittest.TestCase``-pure: stub entities are
``SimpleNamespace`` shapes, the real ``SKILL_REGISTRY`` graph is read, and
injected-graph cases restore the canonical caches through
``validate_prerequisite_graph(SKILL_REGISTRY)`` in ``tearDown``.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.lore.elements import ELEMENT_REGISTRY
from world.rules import progression
from world.rules.progression import (
    FREEFORM_SCALE_LADDER,
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
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    declared_prerequisites,
    prerequisite_consumers,
    validate_prerequisite_graph,
)


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
    """Injected-graph fail-closed validation; canonical caches restored."""

    def setUp(self):
        reset_practice_dedupe()

    def tearDown(self):
        # Restore the canonical caches any injected graph overwrote.
        validate_prerequisite_graph(SKILL_REGISTRY)

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
            SkillPrerequisite("fire_arrow", 0)

    @covers_requirement("skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed")
    def test_non_integer_and_bool_thresholds_fail_at_construction(self):
        for bad in (1.5, "3", True, False, None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    SkillPrerequisite("fire_arrow", bad)

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
        first = validate_prerequisite_graph(SKILL_REGISTRY)
        second = validate_prerequisite_graph(SKILL_REGISTRY)
        self.assertEqual(first, second)
        self.assertEqual(prerequisite_consumers("fire_arrow"), first["fire_arrow"])

    @covers_requirement("skill-lineage::the-fire-lineage-ships-as-the-first-round-linear-tree")
    def test_fire_tree_edges_are_as_designed(self):
        expected = {
            "fire_ball": ("fire_arrow", 3),
            "scorching_wave": ("fire_ball", 3),
            "firestorm": ("scorching_wave", 3),
            "infernal_wrap": ("scorching_wave", 3),
            "lava_burst": ("firestorm", 5),
            "hellfire": ("firestorm", 5),
            "world_ending_blaze": ("hellfire", 5),
            "dragon_flame": ("lava_burst", 8),
            "phoenix_eternal_flame": ("dragon_flame", 8),
        }
        for key, (prereq_key, minimum) in expected.items():
            with self.subTest(key=key):
                self.assertEqual(
                    declared_prerequisites(key),
                    (SkillPrerequisite(prereq_key, minimum),),
                )
        self.assertEqual(declared_prerequisites("fire_arrow"), ())
        # Topological canopy: phoenix is the strict last node.
        self.assertEqual(prerequisite_consumers("phoenix_eternal_flame"), ())

    @covers_requirement("skill-lineage::the-fire-lineage-ships-as-the-first-round-linear-tree")
    def test_mastery_passives_stay_out_of_the_graph(self):
        for element_key in ELEMENT_REGISTRY:
            mastery_key = f"{element_key}_mastery"
            with self.subTest(mastery_key=mastery_key):
                self.assertEqual(prerequisite_consumers(mastery_key), ())
                self.assertEqual(declared_prerequisites(mastery_key), ())


class CanUseSkillTests(unittest.TestCase):
    """The ONE gate matrix on the real fire graph."""

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_root_skill_is_usable_on_ownership_alone(self):
        entity = _entity(("fire_arrow",))
        self.assertTrue(can_use_skill(entity, SKILL_REGISTRY["fire_arrow"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_unowned_skill_is_denied(self):
        entity = _entity(("fire_arrow",))
        self.assertFalse(can_use_skill(entity, SKILL_REGISTRY["fire_ball"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_missing_prerequisite_ownership_denies_even_at_high_level(self):
        # Owns fire_ball at level 5 but NOT fire_arrow: the edge fails on
        # ownership regardless of the skill's own level.
        entity = _entity(("fire_ball",), {"fire_ball": 250.0})
        self.assertFalse(can_use_skill(entity, SKILL_REGISTRY["fire_ball"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_sub_threshold_level_denies_and_exact_threshold_passes(self):
        entity = _entity(("fire_arrow", "fire_ball"), {"fire_arrow": 2.0 * 50 + 49})
        self.assertFalse(can_use_skill(entity, SKILL_REGISTRY["fire_ball"]))
        entity.db.skill_proficiency["fire_arrow"] = 3.0 * 50
        self.assertTrue(can_use_skill(entity, SKILL_REGISTRY["fire_ball"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_missing_prerequisite_names_the_first_unmet_edge(self):
        entity = _entity(("fire_ball",), {})
        unmet = missing_prerequisite(entity, SKILL_REGISTRY["fire_ball"])
        self.assertIsNotNone(unmet)
        self.assertEqual(unmet.skill_key, "fire_arrow")
        self.assertEqual(unmet.min_proficiency, 3)
        self.assertIsNone(missing_prerequisite(entity, SKILL_REGISTRY["fire_arrow"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_gate_is_school_agnostic_on_the_same_path(self):
        # No school branch exists: the identical predicate path answers for
        # any ACTIVE skill, proven by opening/closing only the proficiency
        # factor while everything else (element, affinity, race) stays fixed.
        entity = _entity(("fire_ball", "fire_arrow"), {"fire_arrow": 100.0})
        self.assertFalse(can_use_skill(entity, SKILL_REGISTRY["fire_ball"]))
        entity.db.skill_proficiency["fire_arrow"] = 150.0
        self.assertTrue(can_use_skill(entity, SKILL_REGISTRY["fire_ball"]))

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_transitive_chain_requires_every_edge(self):
        entity = _entity(
            ("fire_arrow", "fire_ball", "scorching_wave", "firestorm"),
            {"fire_arrow": 150.0, "fire_ball": 100.0},
        )
        # scorching_wave needs fire_ball >= 3; at level 2 the chain blocks.
        self.assertFalse(can_use_skill(entity, SKILL_REGISTRY["scorching_wave"]))
        entity.db.skill_proficiency["fire_ball"] = 150.0
        self.assertTrue(can_use_skill(entity, SKILL_REGISTRY["scorching_wave"]))
        self.assertFalse(can_use_skill(entity, SKILL_REGISTRY["firestorm"]))


class TipCapTests(unittest.TestCase):
    """cap(S) = max consuming edge, else the yaml canopy default."""

    def tearDown(self):
        validate_prerequisite_graph(SKILL_REGISTRY)

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_real_graph_caps(self):
        self.assertEqual(proficiency_cap("fire_arrow"), 3)
        self.assertEqual(proficiency_cap("scorching_wave"), 3)
        self.assertEqual(proficiency_cap("firestorm"), 5)
        self.assertEqual(proficiency_cap("hellfire"), 5)
        self.assertEqual(proficiency_cap("lava_burst"), 8)
        self.assertEqual(proficiency_cap("dragon_flame"), 8)
        self.assertEqual(proficiency_cap("phoenix_eternal_flame"), PROFICIENCY_TIP_CAP)

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
            award_practice_xp(entity, "fire_arrow", 40.0)
        self.assertEqual(
            entity.db.skill_proficiency["fire_arrow"],
            3 * SKILL_PROFICIENCY_XP_PER_LEVEL,
        )
        self.assertEqual(skill_proficiency_level(entity, "fire_arrow"), 3)

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_canopy_default_caps_the_unconsumed_node(self):
        entity = _entity()
        for _ in range(60):
            award_practice_xp(entity, "phoenix_eternal_flame", 40.0)
        self.assertEqual(
            entity.db.skill_proficiency["phoenix_eternal_flame"],
            PROFICIENCY_TIP_CAP * SKILL_PROFICIENCY_XP_PER_LEVEL,
        )

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_award_fails_closed_on_invalid_amounts(self):
        entity = _entity()
        for bad in (float("nan"), float("inf"), -1.0, True, "1"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    award_practice_xp(entity, "fire_arrow", bad)
        self.assertEqual(entity.db.skill_proficiency, {})

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_saturation_still_unlocks_the_child_edge(self):
        entity = _entity(
            ("scorching_wave", "firestorm"), {"scorching_wave": 150.0}
        )
        award_practice_xp(entity, "scorching_wave", 100.0)  # capped at 150
        self.assertTrue(can_use_skill(entity, SKILL_REGISTRY["firestorm"]))


class FreeformLadderTests(unittest.TestCase):
    """Skill-anchored ladder over the cast skill's own proficiency."""

    # wind_blade caps at Lv.10, so its ladder spans every rung.
    WIND = "wind_blade"

    def _master(self, level_xp: float):
        return _entity(("wind_blade", "wind_mastery"), {"wind_blade": level_xp})

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_ladder_constants(self):
        self.assertEqual(
            FREEFORM_SCALE_LADDER,
            ((0.25, 0), (0.5, 1), (1.0, 3), (2.0, 6), (4.0, 10)),
        )

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_entitled_levels_unlock_rungs(self):
        skill = SKILL_REGISTRY[self.WIND]
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
        entity = _entity(("wind_blade",), {"wind_blade": 500.0})
        self.assertEqual(freeform_scales_for(entity, SKILL_REGISTRY[self.WIND]), ())

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_ladder_is_skill_anchored_not_element_max(self):
        # High proficiency in a SIBLING wind skill must not raise wind_blade's
        # own rung set: the ladder reads the CAST skill's level only.
        entity = _entity(
            ("wind_blade", "wind_mastery", "tornado_blade"),
            {"wind_blade": 0.0, "tornado_blade": 500.0},
        )
        self.assertEqual(
            freeform_scales_for(entity, SKILL_REGISTRY[self.WIND]), (0.25,)
        )

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_unknown_element_entitlement_fails_closed(self):
        with self.assertRaises(ValueError):
            progression.freeform_mastery_entitled(_entity(), "not_an_element")

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_capped_skill_ladder_is_bounded_by_its_tip_cap(self):
        # firestorm caps at Lv.5; the 2.0 rung needs Lv.6, so the ladder
        # provably stops at 1.0 even on inflated XP — a mid-tree spell never
        # advertises a rung it cannot practise to.
        entity = _entity(("firestorm", "fire_mastery"), {"firestorm": 500.0})
        self.assertEqual(
            freeform_scales_for(entity, SKILL_REGISTRY["firestorm"]),
            (0.25, 0.5, 1.0),
        )

    @covers_requirement("skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency")
    def test_scale_entries_follow_the_ladder_with_scaled_costs(self):
        entity = self._master(150.0)
        entries = freeform_scale_entries_for(entity, SKILL_REGISTRY[self.WIND])
        self.assertEqual([entry[0] for entry in entries], [0.25, 0.5, 1.0])
        self.assertTrue(all(entry[2] >= 1 for entry in entries))
        self.assertEqual(entries[-1][1], "1")


class PracticeFormulaTests(unittest.TestCase):
    """Closed-form amount: base x race x affinity x growth."""

    def setUp(self):
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        patcher.start()
        self.addCleanup(patcher.stop)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_physical_skill_takes_neutral_affinity_even_for_element_affinity(self):
        # basic_attack is element=fire with a PHYSICAL damage school.
        entity = _entity(("basic_attack",), race="human", affinity=("fire",))
        amount = practice_xp_amount(entity, SKILL_REGISTRY["basic_attack"])
        self.assertEqual(amount, SKILL_PRACTICE_XP_PER_USE * 1.0)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_elemental_magic_carries_the_affinity_factor(self):
        favored = _entity(("fire_ball",), race="human", affinity=("fire",))
        unfavored = _entity(("fire_ball",), race="human", affinity=("water",))
        self.assertEqual(
            practice_xp_amount(favored, SKILL_REGISTRY["fire_ball"]),
            SKILL_PRACTICE_XP_PER_USE * 1.1,
        )
        self.assertEqual(
            practice_xp_amount(unfavored, SKILL_REGISTRY["fire_ball"]),
            SKILL_PRACTICE_XP_PER_USE * 0.9,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_race_multiplier_participates(self):
        elf = _entity(("basic_attack",), race="elf")
        self.assertEqual(
            practice_xp_amount(elf, SKILL_REGISTRY["basic_attack"]),
            SKILL_PRACTICE_XP_PER_USE * 10.0,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_growth_multiplier_participates(self):
        with patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.5):
            entity = _entity(("basic_attack",), race="human")
            self.assertEqual(
                practice_xp_amount(entity, SKILL_REGISTRY["basic_attack"]),
                SKILL_PRACTICE_XP_PER_USE * 1.5,
            )


class PracticeDedupeTests(unittest.TestCase):
    """One accrual per (actor, skill, target) per tick; explicit release."""

    def setUp(self):
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tick = {"value": 7}
        tick_patch = patch.object(progression, "_current_tick", lambda: self.tick["value"])
        tick_patch.start()
        self.addCleanup(tick_patch.stop)

    def test_same_triple_twice_in_one_tick_accrues_once(self):
        actor = _entity(("basic_attack",), race="human")
        target = SimpleNamespace(pk=101, key="t1")
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, "basic_attack", target)
        )
        self.assertFalse(
            progression.grant_skill_practice_xp(actor, "basic_attack", target)
        )
        self.assertEqual(
            actor.db.skill_proficiency["basic_attack"], SKILL_PRACTICE_XP_PER_USE
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_distinct_targets_each_accrue(self):
        actor = _entity(("basic_attack",), race="human")
        for index in range(3):
            target = SimpleNamespace(pk=200 + index, key=f"t{index}")
            self.assertTrue(
                progression.grant_skill_practice_xp(actor, "basic_attack", target)
            )
        self.assertEqual(
            actor.db.skill_proficiency["basic_attack"],
            3 * SKILL_PRACTICE_XP_PER_USE,
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_no_target_skills_dedupe_on_none(self):
        actor = _entity(("basic_attack",), race="human")
        self.assertTrue(progression.grant_skill_practice_xp(actor, "basic_attack"))
        self.assertFalse(progression.grant_skill_practice_xp(actor, "basic_attack"))

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_tick_change_clears_the_claims(self):
        actor = _entity(("basic_attack",), race="human")
        self.assertTrue(progression.grant_skill_practice_xp(actor, "basic_attack"))
        self.tick["value"] = 8
        self.assertTrue(progression.grant_skill_practice_xp(actor, "basic_attack"))
        self.assertEqual(
            actor.db.skill_proficiency["basic_attack"],
            2 * SKILL_PRACTICE_XP_PER_USE,
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_release_lets_a_same_tick_retry_accrue(self):
        actor = _entity(("basic_attack",), race="human")
        self.assertTrue(progression.grant_skill_practice_xp(actor, "basic_attack"))
        claim = practice_claim_key(actor, "basic_attack", None)
        self.assertIn(
            claim, progression.practice_claims_for(actor, "basic_attack")
        )
        release_practice_claims([claim])
        self.assertTrue(progression.grant_skill_practice_xp(actor, "basic_attack"))

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_passive_unknown_and_simulated_grant_nothing(self):
        actor = _entity(("basic_attack", "body_enhancement"), race="human")
        self.assertFalse(
            progression.grant_skill_practice_xp(actor, "body_enhancement")
        )
        self.assertFalse(progression.grant_skill_practice_xp(actor, "not_a_skill"))
        self.assertFalse(
            progression.grant_skill_practice_xp(
                actor, "basic_attack", nonlethal=True
            )
        )
        self.assertEqual(actor.db.skill_proficiency, {})

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_saturated_skill_accrues_nothing_new(self):
        actor = _entity(
            ("basic_attack",), race="human", proficiency={"basic_attack": 500.0}
        )
        progression.grant_skill_practice_xp(actor, "basic_attack")
        self.assertEqual(actor.db.skill_proficiency["basic_attack"], 500.0)


class LineageSeedTests(unittest.TestCase):
    """Fixed-point seeding, ownership closure, and record normalization."""

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_full_chain_cascade_seeds_exact_edge_values(self):
        closure_active, closure_passive = lineage_ownership_closure(["firestorm"])
        self.assertEqual(
            closure_active, ["fire_arrow", "fire_ball", "scorching_wave"]
        )
        self.assertEqual(closure_passive, [])
        seeded = seed_lineage_proficiency(["firestorm", *closure_active], None)
        self.assertEqual(
            seeded,
            {"scorching_wave": 150.0, "fire_ball": 150.0, "fire_arrow": 150.0},
        )

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_deep_seed_cascades_to_the_root(self):
        active, _ = lineage_ownership_closure(["phoenix_eternal_flame"])
        seeded = seed_lineage_proficiency(
            ["phoenix_eternal_flame", *active], None
        )
        self.assertEqual(
            seeded,
            {
                # Each ancestor is seeded to the TIGHTEST edge that names it
                # (max over edges): lava_burst is consumed by dragon_flame@8,
                # firestorm by lava_burst@5, the lower chain by their @3 edges.
                "dragon_flame": 400.0,
                "lava_burst": 400.0,
                "firestorm": 250.0,
                "scorching_wave": 150.0,
                "fire_ball": 150.0,
                "fire_arrow": 150.0,
            },
        )
        entity = _entity(["phoenix_eternal_flame", *active], seeded)
        for key in ("fire_ball", "firestorm", "phoenix_eternal_flame"):
            with self.subTest(key=key):
                self.assertTrue(can_use_skill(entity, SKILL_REGISTRY[key]))

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_explicit_below_edge_wins_and_is_never_overwritten(self):
        seeded = seed_lineage_proficiency(
            [
                "firestorm",
                "scorching_wave",
                "fire_ball",
                "fire_arrow",
            ],
            {"scorching_wave": 120.0},
        )
        self.assertEqual(seeded["scorching_wave"], 120.0)
        # fire_arrow (edge under scorching_wave) still seeds normally.
        self.assertEqual(seeded["fire_arrow"], 150.0)

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_seed_is_idempotent(self):
        once = seed_lineage_proficiency(["firestorm"], None)
        twice = seed_lineage_proficiency(["firestorm"], once)
        self.assertEqual(once, twice)

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_normalize_record_closes_and_seeds(self):
        record = {"skills": ["firestorm"], "passives": []}
        normalized = normalize_lineage_record(record)
        self.assertEqual(
            sorted(normalized["skills"]),
            ["fire_arrow", "fire_ball", "firestorm", "scorching_wave"],
        )
        self.assertEqual(normalized["passives"], [])
        self.assertEqual(
            normalized["skill_proficiency"],
            {"scorching_wave": 150.0, "fire_ball": 150.0, "fire_arrow": 150.0},
        )
        # Idempotent + input untouched.
        again = normalize_lineage_record(normalized)
        self.assertEqual(again["skills"], normalized["skills"])
        self.assertEqual(
            again["skill_proficiency"], normalized["skill_proficiency"]
        )
        self.assertEqual(record["skills"], ["firestorm"])

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_normalize_keeps_unknown_keys_for_the_semantic_check(self):
        record = {"skills": ["not_a_skill"], "passives": []}
        normalized = normalize_lineage_record(record)
        self.assertEqual(normalized["skills"], ["not_a_skill"])
        self.assertNotIn("skill_proficiency", normalized)


class ProficiencyCapTableTests(unittest.TestCase):
    """The yaml canopy default is a real bound, not a placeholder."""

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_canopy_default_is_ten(self):
        self.assertEqual(PROFICIENCY_TIP_CAP, 10)

    @covers_requirement("skill-lineage::practice-saturates-at-the-derived-tip-cap")
    def test_no_edge_is_above_its_prerequisites_cap(self):
        for key, skill in SKILL_REGISTRY.items():
            for prereq in skill.prerequisites:
                self.assertGreaterEqual(
                    proficiency_cap(prereq.skill_key),
                    prereq.min_proficiency,
                    f"{key} edge exceeds cap({prereq.skill_key})",
                )
class DerivedUnlockSinkTests(unittest.TestCase):
    """``unlocks_out`` appends exactly one derived line per false->true flip."""

    def setUp(self):
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tick = {"value": 11}
        tick_patch = patch.object(progression, "_current_tick", lambda: self.tick["value"])
        tick_patch.start()
        self.addCleanup(tick_patch.stop)

    def _near_edge(self):
        """Owner with fire_ball at level 2: scorching_wave not yet usable."""
        return _entity(
            ("fire_arrow", "fire_ball", "scorching_wave"),
            {
                "fire_arrow": SKILL_PROFICIENCY_XP_PER_LEVEL * 10,
                "fire_ball": SKILL_PROFICIENCY_XP_PER_LEVEL * 2 + 49,
            },
            race="human",
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp",
        "skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification")
    def test_crossing_an_edge_appends_exactly_one_line(self):
        actor = self._near_edge()
        sink: list[str] = []
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, "fire_ball", unlocks_out=sink)
        )
        self.assertEqual(sink, ["新法術可用：灼熱波動"])

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp",
        "skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification")
    def test_a_second_award_after_the_flip_appends_nothing(self):
        actor = self._near_edge()
        sink: list[str] = []
        progression.grant_skill_practice_xp(actor, "fire_ball", unlocks_out=sink)
        self.assertEqual(len(sink), 1)
        # Same tick: the dedupe claim suppresses the award itself.
        self.assertFalse(
            progression.grant_skill_practice_xp(actor, "fire_ball", unlocks_out=sink)
        )
        self.assertEqual(len(sink), 1)
        # New tick: the award runs again but the child is already usable.
        self.tick["value"] = 12
        self.assertTrue(
            progression.grant_skill_practice_xp(actor, "fire_ball", unlocks_out=sink)
        )
        self.assertEqual(len(sink), 1)

    def test_nonlethal_and_deduped_awards_touch_the_sink_not_at_all(self):
        actor = self._near_edge()
        sink: list[str] = []
        self.assertFalse(
            progression.grant_skill_practice_xp(
                actor, "fire_ball", nonlethal=True, unlocks_out=sink
            )
        )
        self.assertEqual(sink, [])
        self.assertEqual(
            actor.db.skill_proficiency["fire_ball"],
            SKILL_PROFICIENCY_XP_PER_LEVEL * 2 + 49,
        )

    def test_sink_is_optional_for_existing_callers(self):
        actor = self._near_edge()
        self.assertTrue(progression.grant_skill_practice_xp(actor, "fire_ball"))

    def test_wording_splits_on_skill_category(self):
        spell = SKILL_REGISTRY["firestorm"]
        physical = SKILL_REGISTRY["basic_attack"]
        self.assertEqual(progression.unlock_line(spell), "新法術可用：火焰風暴")
        self.assertEqual(
            progression.unlock_line(physical), f"新技能可用：{physical.label}"
        )

    def test_unlock_candidates_are_the_reverse_edge_consumers(self):
        keys = [skill.key for skill in progression.unlock_candidates_for("fire_ball")]
        self.assertEqual(keys, ["scorching_wave"])

    @covers_requirement("skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification")
    def test_seeded_lineage_crosses_edges_silently(self):
        # Seeding writes proficiency directly (no grant, no sink): the
        # notification surface belongs to live awards only.
        actor = _entity(("fire_arrow", "fire_ball", "scorching_wave"), race="human")
        actor.db.skill_proficiency = seed_lineage_proficiency(
            ("fire_arrow", "fire_ball", "scorching_wave"), {}
        )
        self.assertTrue(
            can_use_skill(actor, SKILL_REGISTRY["scorching_wave"])
        )


class StudyPracticeGrantTests(unittest.TestCase):
    """Closed-form booked-study grants (declared-practice-skip D7)."""

    def setUp(self):
        reset_practice_dedupe()
        patcher = patch("world.rules.buffs.growth_rate_multiplier", lambda e: 1.0)
        self.addCleanup(patcher.stop)
        patcher.start()

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_hourly_grant_is_the_shared_composite_times_whole_hours(self):
        entity = _entity(owned=("fire_arrow",), race="human")
        self.assertTrue(
            progression.grant_study_practice_xp(entity, "fire_arrow", 8)
        )
        per_use = practice_xp_amount(entity, SKILL_REGISTRY["fire_arrow"])
        # One formula, two entry points: 8 booked hours award 8 ×
        # PRACTICE_XP_PER_STUDY_HOUR / SKILL_PRACTICE_XP_PER_USE = 80 uses.
        self.assertAlmostEqual(
            entity.db.skill_proficiency["fire_arrow"], 80.0 * per_use
        )

    def test_growth_buff_and_learning_scale_the_hourly_grant(self):
        entity = _entity(owned=("fire_arrow",), race="human")
        with patch("world.rules.buffs.growth_rate_multiplier", lambda e: 2.0):
            self.assertTrue(
                progression.grant_study_practice_xp(entity, "fire_arrow", 1)
            )
        # 1h x 10.0 x growth 2.0 = 20 below the derived ceiling: the buff
        # composite is the one the per-use path shares, not a re-derived copy.
        self.assertAlmostEqual(
            entity.db.skill_proficiency["fire_arrow"],
            progression.PRACTICE_XP_PER_STUDY_HOUR * 2.0,
        )
        elf = _entity(owned=("fire_arrow",), race="elf")
        progression.grant_study_practice_xp(elf, "fire_arrow", 1)
        # 1h x 10.0 x learning 10.0 = 100 for the elf (still under 150).
        self.assertAlmostEqual(
            elf.db.skill_proficiency["fire_arrow"],
            progression.PRACTICE_XP_PER_STUDY_HOUR * 10.0,
        )

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_booked_award_saturates_identically_to_per_use_award(self):
        cap = proficiency_cap("fire_arrow")
        ceiling = cap * SKILL_PROFICIENCY_XP_PER_LEVEL
        studied = _entity(owned=("fire_arrow",), proficiency={"fire_arrow": ceiling - 10.0})
        self.assertTrue(
            progression.grant_study_practice_xp(studied, "fire_arrow", 8)
        )
        self.assertEqual(studied.db.skill_proficiency["fire_arrow"], ceiling)
        used = _entity(
            owned=("fire_arrow",), proficiency={"fire_arrow": ceiling - 10.0}
        )
        award_practice_xp(used, "fire_arrow", 10.0 * cap)
        self.assertEqual(
            studied.db.skill_proficiency["fire_arrow"],
            used.db.skill_proficiency["fire_arrow"],
        )
        # Beyond the ceiling the booked grant writes nothing further.
        self.assertTrue(
            progression.grant_study_practice_xp(studied, "fire_arrow", 8)
        )
        self.assertEqual(studied.db.skill_proficiency["fire_arrow"], ceiling)

    def test_nonpositive_hours_are_no_op_and_bad_types_raise(self):
        entity = _entity(owned=("fire_arrow",), race="human")
        self.assertFalse(
            progression.grant_study_practice_xp(entity, "fire_arrow", 0)
        )
        self.assertFalse(
            progression.grant_study_practice_xp(entity, "fire_arrow", -3)
        )
        self.assertEqual(entity.db.skill_proficiency, {})
        with self.assertRaises(ValueError):
            progression.grant_study_practice_xp(entity, "fire_arrow", True)
        with self.assertRaises(ValueError):
            progression.grant_study_practice_xp(entity, "fire_arrow", 1.5)
        self.assertEqual(entity.db.skill_proficiency, {})

    def test_unknown_and_passive_skills_grant_nothing(self):
        entity = _entity(
            owned=("fire_arrow", "fire_mastery"), race="human"
        )
        self.assertFalse(
            progression.grant_study_practice_xp(entity, "not_a_skill", 4)
        )
        self.assertFalse(
            progression.grant_study_practice_xp(entity, "fire_mastery", 4)
        )
        self.assertEqual(entity.db.skill_proficiency, {})
