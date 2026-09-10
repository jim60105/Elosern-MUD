"""Pure tests for the lineage read model (skill-lineage-panel §1).

``unittest.TestCase``-pure: stub entities are ``SimpleNamespace`` shapes over
a kit-shaped synthetic prerequisite tree (shared ``synth_lineage_tree`` rows
inside a ``skills`` scope); injected graphs mutate the scoped registry only.
Zero-write assertions compare a full deep-copied snapshot of the stub store
before and after every build.
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
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    validate_prerequisite_graph,
)

from ._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
    synth_lineage_tree,
)

# The synthetic lineage tree: a seven-node chain (root -> ... -> crownfire)
# with 3/3/5/8/8/8 thresholds and three sister leaves (mossback off branch,
# burrow off bloom, fallen off burrow). Registry keys and labels are kit
# synthetic values; the topology mirrors the shape the read model must
# handle (chain + sister leaves, strict canopy on top).
TREE = synth_lineage_tree()
TREE_EXTRA = {"skills": TREE}

TREE_CHAIN = (
    "t_tree_root",
    "t_tree_sprout",
    "t_tree_branch",
    "t_tree_bloom",
    "t_tree_canopy",
    "t_tree_heartwood",
    "t_tree_crownfire",
)

# Every skill in the root's reverse-edge closure (the tree's full node set,
# sisters included).
TREE_CLOSURE = TREE_CHAIN + ("t_tree_mossback", "t_tree_burrow", "t_tree_fallen")

ROOT_LABEL = TREE["t_tree_root"].label
BRANCH_LABEL = TREE["t_tree_branch"].label


def _revalidate_live() -> None:
    """Rebuild the load-time caches against whichever registry is live.

    The kit replaces the registry mapping for the scope's duration; the
    reverse-edge caches are keyed to the contents, so every scope entry and
    exit re-validates through the live accessor (the shipped symbol is never
    named). Cleanups are LIFO: register this BEFORE opening the scope so it
    runs after the scope exits.
    """
    validate_prerequisite_graph(live_skill_registry())


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


class _TreeScopeMixin:
    """Every test runs against the synthetic tree; caches rebuilt both ways."""

    def setUp(self):
        self.addCleanup(_revalidate_live)
        open_synthetic_scope(self, "skills", extra=TREE_EXTRA)
        _revalidate_live()


class LineageViewShapeTests(_TreeScopeMixin, unittest.TestCase):
    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_tree_chain_is_one_chain_in_topological_order(self):
        view = build_lineage_view(_entity(TREE_CLOSURE))
        fire = next(
            chain for chain in view.chains if chain.root_skill_key == "t_tree_root"
        )
        keys = [node.skill_key for node in fire.nodes]
        self.assertEqual(set(keys), set(TREE_CLOSURE))
        # Prerequisite edges always point backwards in the emitted order.
        positions = {key: index for index, key in enumerate(keys)}
        for key in keys:
            for prereq in TREE[key].prerequisites:
                if prereq.skill_key in positions:
                    self.assertLess(positions[prereq.skill_key], positions[key])
        self.assertEqual(
            fire.element_or_style_zh,
            TREE["t_tree_root"].element.display_name_zh,
        )

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_prereq_less_uncconsumed_skill_starts_no_chain(self):
        # An injected no-prereq skill that nobody consumes starts nothing.
        registry = live_skill_registry()
        registry["t_tree_lonely"] = _fake_skill("t_tree_lonely")
        _revalidate_live()
        view = build_lineage_view(_entity(("t_tree_lonely",)))
        self.assertNotIn(
            "t_tree_lonely", {chain.root_skill_key for chain in view.chains}
        )
        for chain in view.chains:
            self.assertNotIn("t_tree_lonely", [node.skill_key for node in chain.nodes])

    def test_counts_match_emitted_chains_and_consumed_flags(self):
        view = build_lineage_view(_entity(TREE_CHAIN))
        self.assertEqual(view.total_count, len(view.chains))
        self.assertEqual(
            view.completed_count, sum(1 for chain in view.chains if chain.consumed)
        )


class NodeStateTests(_TreeScopeMixin, unittest.TestCase):
    def _view_for(self, proficiency, owned=TREE_CLOSURE):
        return build_lineage_view(_entity(owned, proficiency))

    def _node(self, view, key):
        chain = next(c for c in view.chains if c.root_skill_key == "t_tree_root")
        return next(n for n in chain.nodes if n.skill_key == key)

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_capped_mid_tree_node_reports_saturation(self):
        # The root is consumed up to level 3; 3 levels + band XP saturates it.
        view = self._view_for({"t_tree_root": _level_xp(3, 23.0)})
        node = self._node(view, "t_tree_root")
        self.assertTrue(node.capped)
        self.assertEqual(node.xp_to_next_level, 0.0)
        self.assertEqual(node.level, 3)
        self.assertTrue(node.usable)  # root, owned, nothing gates it

    def test_root_and_unlocked_nodes_carry_empty_prereq_text(self):
        # Level 10 everywhere satisfies every edge (max edge is Lv.8).
        seeded = {key: _level_xp(10) for key in TREE_CLOSURE}
        view = self._view_for(seeded)
        chain = next(c for c in view.chains if c.root_skill_key == "t_tree_root")
        for node in chain.nodes:
            self.assertEqual(node.prereq_text_zh, "")
            self.assertTrue(node.usable)

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_locked_node_names_its_missing_edge(self):
        # bloom requires branch Lv.5; level 4 locks it.
        view = self._view_for({"t_tree_branch": _level_xp(4)})
        node = self._node(view, "t_tree_bloom")
        self.assertFalse(node.usable)
        self.assertIn(BRANCH_LABEL, node.prereq_text_zh)
        self.assertIn("Lv.5", node.prereq_text_zh)

    def test_unmet_ownership_edge_reports_the_same_text(self):
        # Own bloom + chain minus branch ownership.
        owned = tuple(key for key in TREE_CHAIN if key != "t_tree_branch")
        view = build_lineage_view(_entity(owned, {"t_tree_sprout": _level_xp(3)}))
        chain = next(c for c in view.chains if c.root_skill_key == "t_tree_root")
        node = next(n for n in chain.nodes if n.skill_key == "t_tree_bloom")
        self.assertFalse(node.usable)
        self.assertIn(BRANCH_LABEL, node.prereq_text_zh)

    def test_xp_into_level_and_to_next_split_the_current_band(self):
        view = self._view_for({"t_tree_root": _level_xp(1, 23.0)})
        node = self._node(view, "t_tree_root")
        # Capped at 3: at level 1 the band still has room.
        self.assertFalse(node.capped)
        self.assertEqual(node.xp_into_level, 23.0)
        self.assertEqual(node.xp_to_next_level, SKILL_PROFICIENCY_XP_PER_LEVEL - 23.0)


class MeterTests(_TreeScopeMixin, unittest.TestCase):
    def _fire(self, proficiency):
        view = build_lineage_view(_entity(TREE_CHAIN, proficiency))
        return next(c for c in view.chains if c.root_skill_key == "t_tree_root")

    def test_empty_progress_is_zero(self):
        self.assertEqual(self._fire({}).meter, 0.0)

    def test_shallowest_uncapped_node_drives_the_meter(self):
        # First node capped (3 = root's consuming-edge cap), second node half
        # banded.
        chain = self._fire(
            {
                "t_tree_root": _level_xp(3),
                "t_tree_sprout": _level_xp(1, SKILL_PROFICIENCY_XP_PER_LEVEL / 2),
            }
        )
        # The capped root contributes 1 step; sprout half of one step.
        self.assertAlmostEqual(chain.meter, (1 + 0.5) / len(chain.nodes))

    def test_full_consumption_reads_one(self):
        chain = self._fire({key: _level_xp(10) for key in TREE_CLOSURE})
        self.assertTrue(chain.consumed)
        self.assertEqual(chain.meter, 1.0)

    def test_capped_but_unsatisfied_band_never_shares_a_deeper_step(self):
        # Root saturated (contributes 1), sprout 0 XP.
        chain = self._fire({"t_tree_root": _level_xp(3)})
        self.assertAlmostEqual(chain.meter, 1 / len(chain.nodes))


class PurityTests(_TreeScopeMixin, unittest.TestCase):
    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_double_build_is_equal_and_writes_nothing(self):
        entity = _entity(TREE_CHAIN, {"t_tree_root": _level_xp(2, 12.5)})
        before = copy.deepcopy(entity.db.__dict__)
        first = build_lineage_view(entity)
        second = build_lineage_view(entity)
        self.assertEqual(first, second)
        self.assertEqual(entity.db.__dict__, before)

    def test_tip_cap_default_matches_rulebook(self):
        view = build_lineage_view(
            _entity(
                TREE_CHAIN,
                {"t_tree_crownfire": _level_xp(PROFICIENCY_TIP_CAP - 1)},
            )
        )
        chain = next(c for c in view.chains if c.root_skill_key == "t_tree_root")
        tip = next(n for n in chain.nodes if n.skill_key == "t_tree_crownfire")
        self.assertFalse(tip.capped)
        self.assertEqual(proficiency_cap("t_tree_crownfire"), PROFICIENCY_TIP_CAP)


class FailClosedTests(_TreeScopeMixin, unittest.TestCase):
    def _expect_error(self, proficiency):
        with self.assertRaises(LineageQueryError):
            build_lineage_view(_entity(TREE_CHAIN, proficiency))

    def test_non_numeric_entry_fails_closed(self):
        self._expect_error({"t_tree_root": "lots"})

    def test_boolean_entry_fails_closed(self):
        self._expect_error({"t_tree_root": True})

    def test_negative_entry_fails_closed(self):
        self._expect_error({"t_tree_root": -1.0})

    def test_infinite_entry_fails_closed(self):
        self._expect_error({"t_tree_root": float("inf")})

    def test_non_mapping_record_fails_closed(self):
        entity = _entity(TREE_CHAIN)
        entity.db.skill_proficiency = ["t_tree_root"]
        with self.assertRaises(LineageQueryError):
            build_lineage_view(entity)

    def test_unknown_key_entries_are_ignored_not_fatal(self):
        # A stored key outside the registry renders nothing and cannot poison
        # the view; registry keys are the only renderable surface.
        view = build_lineage_view(_entity(TREE_CHAIN, {"not_a_skill": "junk"}))
        self.assertGreater(view.total_count, 0)


class WireTextBoundTests(_TreeScopeMixin, unittest.TestCase):
    """Legal maximum-length labels clamp, never break, the wire bound."""

    def test_max_length_prerequisite_label_clamps_to_the_wire_bound(self):
        import dataclasses

        from world.rules.lineage_query import LINEAGE_TEXT_WIRE_MAX

        # root label consumes LABEL_MAX (128) legally; the rendered
        # 「需「label Lv.3」」 wrapper would overshoot without the clamp.
        from world.skills.registry import LABEL_MAX

        registry = live_skill_registry()
        registry["duck_root"] = dataclasses.replace(
            _fake_skill("duck_root"), label="測" * LABEL_MAX
        )
        registry["duck_child"] = _fake_skill(
            "duck_child", (SkillPrerequisite("duck_root", 3),)
        )
        _revalidate_live()
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

        registry = live_skill_registry()
        registry["duck_root"] = dataclasses.replace(
            _fake_skill("duck_root"), label="測" * LABEL_MAX
        )
        registry["duck_child"] = _fake_skill(
            "duck_child", (SkillPrerequisite("duck_root", 10**130),)
        )
        _revalidate_live()
        view = build_lineage_view(
            _entity(("duck_root", "duck_child"), {"duck_root": 1.0})
        )
        chain = next(
            chain for chain in view.chains if chain.root_skill_key == "duck_root"
        )
        child = next(n for n in chain.nodes if n.skill_key == "duck_child")
        self.assertLessEqual(len(child.prereq_text_zh), LINEAGE_TEXT_WIRE_MAX)


class InjectedGraphTests(_TreeScopeMixin, unittest.TestCase):
    """Merging topologies: the contract is degree-independent."""

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
        live_skill_registry().update(registry_extras)
        _revalidate_live()
        view = build_lineage_view(_entity(("duck_a", "duck_b", "duck_c")))
        by_root = {chain.root_skill_key: chain for chain in view.chains}
        self.assertIn("duck_a", by_root)
        self.assertIn("duck_b", by_root)
        self.assertEqual(by_root["duck_a"].nodes[-1].skill_key, "duck_c")
        self.assertEqual(by_root["duck_b"].nodes[-1].skill_key, "duck_c")
