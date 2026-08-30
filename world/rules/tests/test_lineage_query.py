"""Pure tests for the lineage read model (skill-lineage-panel §1).

``unittest.TestCase``-pure: stub entities are ``SimpleNamespace`` shapes over
the canonical ``SKILL_REGISTRY`` fire lineage; injected graphs restore the
canonical caches in ``tearDown``. Zero-write assertions compare a full
deep-copied snapshot of the stub store before and after every build.
"""

import copy
import unittest
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement


from world.rules.lineage_query import (
    LineageQueryError,
    build_lineage_view,
)
from world.rules.progression import (
    PROFICIENCY_TIP_CAP,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    proficiency_cap,
)
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    validate_prerequisite_graph,
)


def _fake_skill(key: str, prerequisites: tuple[SkillPrerequisite, ...] = ()) -> SkillDef:
    return SkillDef(
        key=key,
        label=f"測試技能{key}",
        description=f"injected lineage fixture {key}",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.NONE,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=[],
        category=SkillCategory.UTILITY,
        prerequisites=prerequisites,
    )


def _entity(owned: tuple[str, ...] = (), proficiency: dict[str, float] | None = None):
    return SimpleNamespace(
        race=None,
        pk=None,
        key="stub",
        skills=SimpleNamespace(owned_keys=lambda: set(owned)),
        db=SimpleNamespace(skill_proficiency=dict(proficiency or {})),
    )


def _level_xp(level: int, into: float = 0.0) -> float:
    return level * SKILL_PROFICIENCY_XP_PER_LEVEL + into


FIRE_TREE = (
    "fire_arrow",
    "fire_ball",
    "scorching_wave",
    "firestorm",
    "lava_burst",
    "dragon_flame",
    "phoenix_eternal_flame",
)

# Every skill in fire_arrow's reverse-edge closure (the fire chain's full
# node set, sisters included).
FIRE_CLOSURE = FIRE_TREE + ("infernal_wrap", "hellfire", "world_ending_blaze")


class LineageViewShapeTests(unittest.TestCase):
    def setUp(self):
        validate_prerequisite_graph(SKILL_REGISTRY)

    def tearDown(self):
        validate_prerequisite_graph(SKILL_REGISTRY)

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_fire_tree_is_one_chain_in_topological_order(self):
        view = build_lineage_view(_entity(FIRE_CLOSURE))
        fire = next(
            chain for chain in view.chains if chain.root_skill_key == "fire_arrow"
        )
        keys = [node.skill_key for node in fire.nodes]
        self.assertEqual(set(keys), set(FIRE_CLOSURE))
        # Prerequisite edges always point backwards in the emitted order.
        positions = {key: index for index, key in enumerate(keys)}
        for key in keys:
            for prereq in SKILL_REGISTRY[key].prerequisites:
                if prereq.skill_key in positions:
                    self.assertLess(positions[prereq.skill_key], positions[key])
        self.assertEqual(
            fire.element_or_style_zh,
            SKILL_REGISTRY["fire_arrow"].element.display_name_zh,
        )

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_prereq_less_uncconsumed_skill_starts_no_chain(self):
        # basic_attack declares no prerequisites and nobody consumes it.
        view = build_lineage_view(_entity(("basic_attack",)))
        self.assertNotIn(
            "basic_attack", {chain.root_skill_key for chain in view.chains}
        )
        for chain in view.chains:
            self.assertNotIn("basic_attack", [node.skill_key for node in chain.nodes])

    def test_counts_match_emitted_chains_and_consumed_flags(self):
        view = build_lineage_view(_entity(FIRE_TREE))
        self.assertEqual(view.total_count, len(view.chains))
        self.assertEqual(
            view.completed_count, sum(1 for chain in view.chains if chain.consumed)
        )


class NodeStateTests(unittest.TestCase):
    def _view_for(self, proficiency, owned=FIRE_CLOSURE):
        return build_lineage_view(_entity(owned, proficiency))

    def _node(self, view, key):
        chain = next(c for c in view.chains if c.root_skill_key == "fire_arrow")
        return next(n for n in chain.nodes if n.skill_key == key)

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_capped_mid_tree_node_reports_saturation(self):
        # fire_arrow is consumed up to level 3; 3 levels + band XP saturates it.
        view = self._view_for({"fire_arrow": _level_xp(3, 23.0)})
        node = self._node(view, "fire_arrow")
        self.assertTrue(node.capped)
        self.assertEqual(node.xp_to_next_level, 0.0)
        self.assertEqual(node.level, 3)
        self.assertTrue(node.usable)  # root, owned, nothing gates it

    def test_root_and_unlocked_nodes_carry_empty_prereq_text(self):
        # Level 10 everywhere satisfies every edge (max edge is Lv.8).
        seeded = {key: _level_xp(10) for key in FIRE_CLOSURE}
        view = self._view_for(seeded)
        chain = next(c for c in view.chains if c.root_skill_key == "fire_arrow")
        for node in chain.nodes:
            self.assertEqual(node.prereq_text_zh, "")
            self.assertTrue(node.usable)

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_locked_node_names_its_missing_edge(self):
        # firestorm requires scorching_wave Lv.3; level 2 locks it.
        view = self._view_for({"scorching_wave": _level_xp(2)})
        node = self._node(view, "firestorm")
        self.assertFalse(node.usable)
        self.assertIn("灼熱波動", node.prereq_text_zh)
        self.assertIn("Lv.3", node.prereq_text_zh)

    def test_unmet_ownership_edge_reports_the_same_text(self):
        # Own firestorm + fire_tree minus scorching_wave ownership.
        owned = tuple(key for key in FIRE_TREE if key != "scorching_wave")
        view = build_lineage_view(_entity(owned, {"fire_ball": _level_xp(3)}))
        chain = next(c for c in view.chains if c.root_skill_key == "fire_arrow")
        node = next(n for n in chain.nodes if n.skill_key == "firestorm")
        self.assertFalse(node.usable)
        self.assertIn("灼熱波動", node.prereq_text_zh)

    def test_xp_into_level_and_to_next_split_the_current_band(self):
        view = self._view_for({"fire_arrow": _level_xp(1, 23.0)})
        node = self._node(view, "fire_arrow")
        # Capped at 3: at level 1 the band still has room.
        self.assertFalse(node.capped)
        self.assertEqual(node.xp_into_level, 23.0)
        self.assertEqual(node.xp_to_next_level, SKILL_PROFICIENCY_XP_PER_LEVEL - 23.0)


class MeterTests(unittest.TestCase):
    def _fire(self, proficiency):
        view = build_lineage_view(_entity(FIRE_TREE, proficiency))
        return next(c for c in view.chains if c.root_skill_key == "fire_arrow")

    def test_empty_progress_is_zero(self):
        self.assertEqual(self._fire({}).meter, 0.0)

    def test_shallowest_uncapped_node_drives_the_meter(self):
        # First node capped (3 = fire_arrow cap), second node half banded.
        chain = self._fire(
            {
                "fire_arrow": _level_xp(3),
                "fire_ball": _level_xp(1, SKILL_PROFICIENCY_XP_PER_LEVEL / 2),
            }
        )
        # fire_arrow capped contributes 1 step; fire_ball half of one step.
        self.assertAlmostEqual(chain.meter, (1 + 0.5) / len(chain.nodes))

    def test_full_consumption_reads_one(self):
        chain = self._fire({key: _level_xp(10) for key in FIRE_CLOSURE})
        self.assertTrue(chain.consumed)
        self.assertEqual(chain.meter, 1.0)

    def test_capped_but_unsatisfied_band_never_shares_a_deeper_step(self):
        # fire_arrow saturated (contributes 1), fire_ball 0 XP.
        chain = self._fire({"fire_arrow": _level_xp(3)})
        self.assertAlmostEqual(chain.meter, 1 / len(chain.nodes))


class PurityTests(unittest.TestCase):
    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_double_build_is_equal_and_writes_nothing(self):
        entity = _entity(FIRE_TREE, {"fire_arrow": _level_xp(2, 12.5)})
        before = copy.deepcopy(entity.db.__dict__)
        first = build_lineage_view(entity)
        second = build_lineage_view(entity)
        self.assertEqual(first, second)
        self.assertEqual(entity.db.__dict__, before)

    def test_tip_cap_default_matches_rulebook(self):
        view = build_lineage_view(_entity(FIRE_TREE, {"phoenix_eternal_flame": _level_xp(PROFICIENCY_TIP_CAP - 1)}))
        chain = next(c for c in view.chains if c.root_skill_key == "fire_arrow")
        tip = next(n for n in chain.nodes if n.skill_key == "phoenix_eternal_flame")
        self.assertFalse(tip.capped)
        self.assertEqual(proficiency_cap("phoenix_eternal_flame"), PROFICIENCY_TIP_CAP)


class FailClosedTests(unittest.TestCase):
    def _expect_error(self, proficiency):
        with self.assertRaises(LineageQueryError):
            build_lineage_view(_entity(FIRE_TREE, proficiency))

    def test_non_numeric_entry_fails_closed(self):
        self._expect_error({"fire_arrow": "lots"})

    def test_boolean_entry_fails_closed(self):
        self._expect_error({"fire_arrow": True})

    def test_negative_entry_fails_closed(self):
        self._expect_error({"fire_arrow": -1.0})

    def test_infinite_entry_fails_closed(self):
        self._expect_error({"fire_arrow": float("inf")})

    def test_non_mapping_record_fails_closed(self):
        entity = _entity(FIRE_TREE)
        entity.db.skill_proficiency = ["fire_arrow"]
        with self.assertRaises(LineageQueryError):
            build_lineage_view(entity)

    def test_unknown_key_entries_are_ignored_not_fatal(self):
        # A stored key outside the registry renders nothing and cannot poison
        # the view; registry keys are the only renderable surface.
        view = build_lineage_view(_entity(FIRE_TREE, {"not_a_skill": "junk"}))
        self.assertGreater(view.total_count, 0)


class WireTextBoundTests(unittest.TestCase):
    """Legal maximum-length labels clamp, never break, the wire bound."""

    def setUp(self):
        self.canonical = dict(SKILL_REGISTRY)

    def tearDown(self):
        SKILL_REGISTRY.clear()
        SKILL_REGISTRY.update(self.canonical)
        validate_prerequisite_graph(SKILL_REGISTRY)

    def test_max_length_prerequisite_label_clamps_to_the_wire_bound(self):
        import dataclasses

        from world.rules.lineage_query import LINEAGE_TEXT_WIRE_MAX

        # root label consumes LABEL_MAX (128) legally; the rendered
        # 「需「label Lv.3」」 wrapper would overshoot without the clamp.
        from world.skills.registry import LABEL_MAX

        SKILL_REGISTRY["duck_root"] = _fake_skill("duck_root")
        SKILL_REGISTRY["duck_root"] = dataclasses.replace(
            SKILL_REGISTRY["duck_root"], label="測" * LABEL_MAX
        )
        SKILL_REGISTRY["duck_child"] = _fake_skill(
            "duck_child", (SkillPrerequisite("duck_root", 3),)
        )
        validate_prerequisite_graph(SKILL_REGISTRY)
        # Child owned at level 0 with the prereq unmet: the edge renders.
        view = build_lineage_view(
            _entity(("duck_root", "duck_child"), {"duck_root": 1.0})
        )
        chain = next(
            chain for chain in view.chains if chain.root_skill_key == "duck_root"
        )
        child = next(n for n in chain.nodes if n.skill_key == "duck_child")
        self.assertLessEqual(len(child.prereq_text_zh), LINEAGE_TEXT_WIRE_MAX)
        self.assertTrue(child.prereq_text_zh.startswith("需「"))
        self.assertTrue(child.prereq_text_zh.endswith("Lv.3」"))
        self.assertIn("…", child.prereq_text_zh)
        # Determinism: the clamp is a pure function of the registry data.
        second = build_lineage_view(
            _entity(("duck_root", "duck_child"), {"duck_root": 1.0})
        )
        self.assertEqual(view, second)

    def test_oversized_threshold_also_clamps_to_the_wire_bound(self):
        # Totality (rubber-duck RD3): a legal int threshold whose digits
        # alone overshoot the budget must not break the bound.
        import dataclasses

        from world.rules.lineage_query import LINEAGE_TEXT_WIRE_MAX
        from world.skills.registry import LABEL_MAX

        SKILL_REGISTRY["duck_root"] = _fake_skill("duck_root")
        SKILL_REGISTRY["duck_root"] = dataclasses.replace(
            SKILL_REGISTRY["duck_root"], label="測" * LABEL_MAX
        )
        SKILL_REGISTRY["duck_child"] = _fake_skill(
            "duck_child", (SkillPrerequisite("duck_root", 10**130),)
        )
        validate_prerequisite_graph(SKILL_REGISTRY)
        view = build_lineage_view(
            _entity(("duck_root", "duck_child"), {"duck_root": 1.0})
        )
        chain = next(
            chain for chain in view.chains if chain.root_skill_key == "duck_root"
        )
        child = next(n for n in chain.nodes if n.skill_key == "duck_child")
        self.assertLessEqual(len(child.prereq_text_zh), LINEAGE_TEXT_WIRE_MAX)


class InjectedGraphTests(unittest.TestCase):
    """Merging topologies: the contract is degree-independent."""

    def setUp(self):
        self.canonical = dict(SKILL_REGISTRY)

    def tearDown(self):
        SKILL_REGISTRY.clear()
        SKILL_REGISTRY.update(self.canonical)
        validate_prerequisite_graph(SKILL_REGISTRY)

    def test_merge_node_appears_in_both_root_closures(self):
        # a -> c <- b: c is consumed by nothing, merges two chains.
        registry_extras = {
            "duck_a": _fake_skill("duck_a"),
            "duck_b": _fake_skill("duck_b"),
            "duck_c": _fake_skill(
                "duck_c",
                (SkillPrerequisite("duck_a", 1), SkillPrerequisite("duck_b", 1)),
            ),
        }
        SKILL_REGISTRY.update(registry_extras)
        validate_prerequisite_graph(SKILL_REGISTRY)
        view = build_lineage_view(_entity(("duck_a", "duck_b", "duck_c")))
        by_root = {chain.root_skill_key: chain for chain in view.chains}
        self.assertIn("duck_a", by_root)
        self.assertIn("duck_b", by_root)
        self.assertEqual(by_root["duck_a"].nodes[-1].skill_key, "duck_c")
        self.assertEqual(by_root["duck_b"].nodes[-1].skill_key, "duck_c")
