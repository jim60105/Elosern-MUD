"""Pure tests for the lineage read model (skill-lineage-panel §1).

``unittest.TestCase``-pure: stub entities are ``SimpleNamespace`` shapes over
a kit-shaped synthetic prerequisite tree (shared ``synth_lineage_tree`` rows
inside a ``skills`` scope); injected graphs mutate the scoped registry only.
Zero-write assertions compare a full deep-copied snapshot of the stub store
before and after every build.
"""

import copy
import dataclasses
import unittest
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement


from world.rules.lineage_query import (
    MAX_LINEAGE_POSITION_ROWS,
    LineageQueryError,
    build_lineage_view,
    lineage_position_for,
    proficiency_progress_for_keys,
)
from world.rules.progression import (
    PROFICIENCY_TIP_CAP,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    proficiency_cap,
)
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillEligibility,
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
    @covers_requirement(
        "skill-identity-eligibility::player-catalogs-and-lineage-use-identity-filtering"
    )
    @covers_requirement(
        "skill-lineage-panel::lineage-filtering-preserves-racial-discovery-without-exposing-monster-chains"
    )
    def test_identity_ineligible_tree_has_no_nodes_or_counts(self):
        from dataclasses import replace
        from world.skills.registry import SkillEligibility

        registry = live_skill_registry()
        for key in TREE:
            registry[key] = replace(
                registry[key], eligibility=SkillEligibility(allowed_actor_kinds=("monster",)),
            )
        view = build_lineage_view(_entity(TREE_CLOSURE))
        self.assertFalse(any(
            graph.graph_id == "t_tree_root" for graph in view.graphs
        ))
        self.assertEqual(view.total_count, len(view.graphs))

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_tree_is_one_graph_in_topological_order(self):
        view = build_lineage_view(_entity(TREE_CLOSURE))
        fire = next(
            graph for graph in view.graphs if graph.graph_id == "t_tree_root"
        )
        keys = [node.skill_key for node in fire.nodes]
        self.assertEqual(set(keys), set(TREE_CLOSURE))
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(fire.root_keys, ("t_tree_root",))
        # Prerequisite edges always point backwards in the emitted order.
        positions = {key: index for index, key in enumerate(keys)}
        for key in keys:
            for prereq in TREE[key].prerequisites:
                if prereq.skill_key in positions:
                    self.assertLess(positions[prereq.skill_key], positions[key])
        self.assertEqual(
            fire.group_label_zh,
            TREE["t_tree_root"].element.display_name_zh,
        )
        self.assertEqual(fire.total_count, len(TREE_CLOSURE))
        self.assertEqual(fire.owned_count, len(TREE_CLOSURE))
        self.assertEqual(
            {(edge.from_key, edge.to_key, edge.min_level) for edge in fire.edges},
            {
                ("t_tree_root", "t_tree_sprout", 3),
                ("t_tree_sprout", "t_tree_branch", 3),
                ("t_tree_branch", "t_tree_bloom", 5),
                ("t_tree_bloom", "t_tree_canopy", 8),
                ("t_tree_canopy", "t_tree_heartwood", 8),
                ("t_tree_heartwood", "t_tree_crownfire", 8),
                ("t_tree_branch", "t_tree_mossback", 3),
                ("t_tree_bloom", "t_tree_burrow", 5),
                ("t_tree_burrow", "t_tree_fallen", 5),
            },
        )
        by_key = {node.skill_key: node for node in fire.nodes}
        self.assertEqual(by_key["t_tree_root"].depth, 0)
        self.assertEqual(by_key["t_tree_branch"].depth, 2)
        self.assertEqual(by_key["t_tree_crownfire"].depth, 6)
        self.assertEqual(by_key["t_tree_mossback"].depth, 3)
        self.assertEqual(by_key["t_tree_fallen"].depth, 5)

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    def test_unowned_isolated_skill_is_absent_but_an_owned_one_is_a_graph(self):
        # An injected no-prereq skill that nobody consumes is no graph until
        # the member owns it; ownership makes it a one-node graph.
        registry = live_skill_registry()
        registry["t_tree_lonely"] = _fake_skill("t_tree_lonely")
        _revalidate_live()
        view = build_lineage_view(_entity())
        self.assertNotIn(
            "t_tree_lonely", {graph.graph_id for graph in view.graphs}
        )
        for graph in view.graphs:
            self.assertNotIn("t_tree_lonely", [node.skill_key for node in graph.nodes])
        owned_view = build_lineage_view(_entity(("t_tree_lonely",)))
        lonely = next(
            graph for graph in owned_view.graphs if graph.graph_id == "t_tree_lonely"
        )
        self.assertEqual(lonely.root_keys, ("t_tree_lonely",))
        self.assertEqual(lonely.edges, ())
        self.assertEqual(lonely.owned_count, 1)
        self.assertEqual(lonely.total_count, 1)
        self.assertTrue(lonely.nodes[0].owned)

    def test_counts_match_emitted_graphs_and_consumed_flags(self):
        view = build_lineage_view(_entity(TREE_CHAIN))
        self.assertEqual(view.total_count, len(view.graphs))
        self.assertEqual(
            view.completed_count, sum(1 for graph in view.graphs if graph.consumed)
        )


class NodeStateTests(_TreeScopeMixin, unittest.TestCase):
    def _view_for(self, proficiency, owned=TREE_CLOSURE):
        return build_lineage_view(_entity(owned, proficiency))

    def _node(self, view, key):
        graph = next(g for g in view.graphs if g.graph_id == "t_tree_root")
        return next(n for n in graph.nodes if n.skill_key == key)

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
        graph = next(g for g in view.graphs if g.graph_id == "t_tree_root")
        for node in graph.nodes:
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
        graph = next(g for g in view.graphs if g.graph_id == "t_tree_root")
        node = next(n for n in graph.nodes if n.skill_key == "t_tree_bloom")
        self.assertFalse(node.usable)
        self.assertIn(BRANCH_LABEL, node.prereq_text_zh)

    def test_xp_into_level_and_to_next_split_the_current_band(self):
        view = self._view_for({"t_tree_root": _level_xp(1, 23.0)})
        node = self._node(view, "t_tree_root")
        # Capped at 3: at level 1 the band still has room.
        self.assertFalse(node.capped)
        self.assertEqual(node.xp_into_level, 23.0)
        self.assertEqual(node.xp_to_next_level, SKILL_PROFICIENCY_XP_PER_LEVEL - 23.0)


class ReadyAndConsumedTests(_TreeScopeMixin, unittest.TestCase):
    def _fire(self, proficiency, owned=TREE_CHAIN):
        view = build_lineage_view(_entity(owned, proficiency))
        return next(g for g in view.graphs if g.graph_id == "t_tree_root")

    def _node(self, graph, key):
        return next(node for node in graph.nodes if node.skill_key == key)

    def test_ready_marks_an_unowned_node_whose_edges_are_met(self):
        # bloom requires branch Lv.5; owning the chain up to branch at Lv.5
        # makes the unowned bloom ready, while the deeper canopy is not.
        graph = self._fire(
            {"t_tree_branch": _level_xp(5)},
            owned=("t_tree_root", "t_tree_sprout", "t_tree_branch"),
        )
        bloom = self._node(graph, "t_tree_bloom")
        self.assertFalse(bloom.owned)
        self.assertTrue(bloom.ready)
        self.assertEqual(bloom.prereq_text_zh, "")
        canopy = self._node(graph, "t_tree_canopy")
        self.assertFalse(canopy.owned)
        self.assertFalse(canopy.ready)
        self.assertIn(TREE["t_tree_bloom"].label, canopy.prereq_text_zh)

    def test_owned_node_is_never_ready(self):
        graph = self._fire(
            {key: _level_xp(10) for key in TREE_CLOSURE}, owned=TREE_CLOSURE
        )
        for node in graph.nodes:
            self.assertTrue(node.owned)
            self.assertFalse(node.ready)

    def test_consumed_requires_every_node_capped(self):
        partial = self._fire({"t_tree_root": _level_xp(3)})
        self.assertFalse(partial.consumed)
        full = self._fire({key: _level_xp(10) for key in TREE_CLOSURE})
        self.assertTrue(full.consumed)
        view = build_lineage_view(
            _entity(TREE_CLOSURE, {key: _level_xp(10) for key in TREE_CLOSURE})
        )
        self.assertEqual(view.completed_count, 1)


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
        graph = next(g for g in view.graphs if g.graph_id == "t_tree_root")
        tip = next(n for n in graph.nodes if n.skill_key == "t_tree_crownfire")
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
        graph = next(
            graph for graph in view.graphs if graph.graph_id == "duck_root"
        )
        child = next(n for n in graph.nodes if n.skill_key == "duck_child")
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
        graph = next(
            graph for graph in view.graphs if graph.graph_id == "duck_root"
        )
        child = next(n for n in graph.nodes if n.skill_key == "duck_child")
        self.assertLessEqual(len(child.prereq_text_zh), LINEAGE_TEXT_WIRE_MAX)


class InjectedGraphTests(_TreeScopeMixin, unittest.TestCase):
    """Merging topologies: one graph, one merge node, one edge per parent."""

    def test_two_root_merge_is_one_graph_with_explicit_edges_and_depth(self):
        # a -> d <- b, d -> e: a and b are the roots, d merges both parents.
        registry_extras = {
            "duck_a": _fake_skill("duck_a"),
            "duck_b": _fake_skill("duck_b"),
            "duck_d": _fake_skill(
                "duck_d",
                (SkillPrerequisite("duck_a", 1), SkillPrerequisite("duck_b", 4)),
            ),
            "duck_e": _fake_skill("duck_e", (SkillPrerequisite("duck_d", 2),)),
        }
        live_skill_registry().update(registry_extras)
        _revalidate_live()
        view = build_lineage_view(_entity(tuple(registry_extras)))
        graph = next(g for g in view.graphs if g.graph_id == "duck_a")
        self.assertEqual(graph.root_keys, ("duck_a", "duck_b"))
        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(
            [node.skill_key for node in graph.nodes].count("duck_d"), 1
        )
        self.assertEqual(
            [(edge.from_key, edge.to_key, edge.min_level) for edge in graph.edges],
            [
                ("duck_a", "duck_d", 1),
                ("duck_b", "duck_d", 4),
                ("duck_d", "duck_e", 2),
            ],
        )
        depths = {node.skill_key: node.depth for node in graph.nodes}
        self.assertEqual(depths["duck_a"], 0)
        self.assertEqual(depths["duck_b"], 0)
        self.assertEqual(depths["duck_d"], 1)
        self.assertEqual(depths["duck_e"], 2)


class LineagePositionTests(_TreeScopeMixin, unittest.TestCase):
    """The selected skill's prerequisite and next-unlock position."""

    def _merge_registry(self):
        """a -> c <- b, with c's thresholds distinct so order is observable."""
        extras = {
            "duck_a": _fake_skill("duck_a"),
            "duck_b": _fake_skill("duck_b"),
            "duck_c": _fake_skill(
                "duck_c",
                (SkillPrerequisite("duck_a", 1), SkillPrerequisite("duck_b", 4)),
            ),
        }
        live_skill_registry().update(extras)
        _revalidate_live()
        return extras

    @covers_requirement("webclient-exploration-menu::the-selected-skill-carries-lineage-position-and-the-freeform-ladder")
    def test_merge_node_reports_both_prerequisites_and_no_next_unlock(self):
        extras = self._merge_registry()
        position = lineage_position_for(_entity(), "duck_c")
        self.assertEqual(
            [(edge.skill_key, edge.display_name_zh, edge.level) for edge in position.prerequisites],
            [
                ("duck_a", extras["duck_a"].label, 1),
                ("duck_b", extras["duck_b"].label, 4),
            ],
        )
        self.assertEqual(position.next, ())

    @covers_requirement("webclient-exploration-menu::the-selected-skill-carries-lineage-position-and-the-freeform-ladder")
    def test_root_reports_its_consumers_as_next_unlocks(self):
        extras = self._merge_registry()
        position = lineage_position_for(_entity(), "duck_a")
        self.assertEqual(position.prerequisites, ())
        self.assertEqual(
            [(edge.skill_key, edge.display_name_zh, edge.level) for edge in position.next],
            [("duck_c", extras["duck_c"].label, 1)],
        )

    @covers_requirement("webclient-exploration-menu::the-selected-skill-carries-lineage-position-and-the-freeform-ladder")
    def test_identity_ineligible_consumers_are_not_advertised(self):
        registry_extras = {
            "duck_a": _fake_skill("duck_a"),
            "duck_monster": dataclasses.replace(
                _fake_skill("duck_monster", (SkillPrerequisite("duck_a", 2),)),
                eligibility=SkillEligibility(allowed_actor_kinds=("monster",)),
            ),
        }
        live_skill_registry().update(registry_extras)
        _revalidate_live()
        # The stub entity has no actor kind, so a monster-only row is unownable
        # and never appears as a next unlock.
        self.assertEqual(lineage_position_for(_entity(), "duck_a").next, ())

    @covers_requirement("webclient-exploration-menu::the-selected-skill-carries-lineage-position-and-the-freeform-ladder")
    def test_each_side_is_bounded_to_the_position_rows(self):
        extras = {"duck_a": _fake_skill("duck_a")}
        for index in range(MAX_LINEAGE_POSITION_ROWS + 2):
            extras[f"duck_fan_{index}"] = _fake_skill(
                f"duck_fan_{index}", (SkillPrerequisite("duck_a", index + 1),)
            )
        live_skill_registry().update(extras)
        _revalidate_live()
        position = lineage_position_for(_entity(), "duck_a")
        self.assertEqual(len(position.next), MAX_LINEAGE_POSITION_ROWS)
        # Ascending thresholds: the first rows are the reachable low ones.
        self.assertEqual([edge.level for edge in position.next], list(range(1, 9)))

    def test_unknown_key_fails_closed(self):
        with self.assertRaises(LineageQueryError):
            lineage_position_for(_entity(), "no_such_lineage_skill")

    def test_progress_matches_the_lineage_node_band(self):
        proficiency = {"t_tree_branch": _level_xp(4, 23.0)}
        progress = proficiency_progress_for_keys(
            _entity(TREE_CLOSURE, proficiency), ["t_tree_branch"]
        )
        node = next(
            node
            for graph in build_lineage_view(_entity(TREE_CLOSURE, proficiency)).graphs
            for node in graph.nodes
            if node.skill_key == "t_tree_branch"
        )
        row = progress["t_tree_branch"]
        self.assertEqual(
            (row.level, row.xp_into_level, row.xp_to_next_level, row.capped),
            (node.level, node.xp_into_level, node.xp_to_next_level, node.capped),
        )
        # A registry-unresolvable key has no proficiency band at all.
        self.assertNotIn(
            "no_such_lineage_skill",
            proficiency_progress_for_keys(_entity(), ["no_such_lineage_skill"]),
        )
