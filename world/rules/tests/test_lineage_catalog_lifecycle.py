"""Catalog/index lifecycle regressions for the lineage read model.

The live ``SKILL_REGISTRY`` is mutated in place by the synthetic-data kit
(scoped patch and process install) and extended by the browser harness's
innate-skill graft. Its reverse-edge caches are built by the load-time
validator, so every mutation boundary must rebuild them: a stale reverse map
leaves a valid installed graph with undrained indegrees and the topological
sort reports a cycle the validator never saw.

These tests pin the corrected boundary. They install the real kit contents
through the process-scope entry point, graft the production innate rows,
uninstall, and install again; they also exercise an independently authored
branching/two-parent merge graph through the scoped kit. Contract: the index is
rebuilt once at each mutation and never repaired per read, and a genuinely
malformed graph still fails closed through the existing validator.
"""

import unittest
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement

from world.rules.lineage_query import LineageQueryError, build_lineage_view
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillPrerequisite,
    declared_prerequisites,
    prerequisite_consumers,
    validate_prerequisite_graph,
)
from world.tests.synthetic_data import (
    install_synthetic_catalogs,
    make_skill,
    synthetic_registries,
    uninstall_synthetic_catalogs,
)


def _entity(owned=(), proficiency=None):
    """A stub entity the lineage read model accepts (no Evennia handlers)."""
    return SimpleNamespace(
        race=None,
        pk=None,
        key="stub",
        skills=SimpleNamespace(owned_keys=lambda: set(owned)),
        db=SimpleNamespace(skill_proficiency=dict(proficiency or {})),
    )


def _consumer_snapshot(registry):
    """The exact reverse-edge index keyed by every live registry row."""
    return {key: prerequisite_consumers(key) for key in registry}


class InstalledCatalogLineageTests(unittest.TestCase):
    """Process-scope install, graft, uninstall and reinstall rebuild the index."""

    def setUp(self):
        self.registry = SKILL_REGISTRY
        self.shipped_rows = dict(self.registry)
        self.shipped_index = _consumer_snapshot(self.registry)
        self.addCleanup(self._restore)

    def _restore(self):
        uninstall_synthetic_catalogs()
        # A test that fails before uninstall still leaves the process usable.
        validate_prerequisite_graph(self.registry)

    @covers_requirement(
    "skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-"
    "side-effect-free"
)
    def test_install_without_the_boundary_rebuild_reproduces_the_false_cycle(self):
        """The corrected mechanism is what makes the installed graph readable.

        With the boundary rebuild suppressed the install is exactly the
        pre-fix state: live rows carry the burst -> comet edge while the
        reverse index still describes the shipped rows, so the topological
        sort drains one node too few and reports the observed false cycle.
        """
        from unittest.mock import patch

        with patch(
            "world.tests.synthetic_data.install._revalidate_skill_lineage",
            lambda: None,
        ):
            self.assertTrue(install_synthetic_catalogs(("skills",)))
            self.assertEqual(prerequisite_consumers("t_ember_burst"), ())
            with self.assertRaises(LineageQueryError) as caught:
                build_lineage_view(_entity())
            self.assertIn("cycle", str(caught.exception))
        self.assertTrue(uninstall_synthetic_catalogs())
        self.assertEqual(_consumer_snapshot(self.registry), self.shipped_index)

    @covers_requirement(
    "skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-"
    "side-effect-free"
)
    def test_install_graft_uninstall_and_reinstall_rebuild_the_reverse_index(self):
        self.assertNotIn("t_ember_burst", self.registry)

        self.assertTrue(install_synthetic_catalogs(("skills",)))
        # The installed catalog's reverse edges are live immediately: the
        # shallow burst consumes the deep comet row, one edge at Lv.3.
        self.assertEqual(
            prerequisite_consumers("t_ember_burst"),
            (("t_ember_comet", 3),),
        )
        self.assertEqual(
            [edge.skill_key for edge in declared_prerequisites("t_ember_comet")],
            ["t_ember_burst"],
        )

        view = build_lineage_view(_entity())
        graph = next(
            item for item in view.graphs if item.graph_id == "t_ember_burst"
        )
        self.assertEqual(
            [node.skill_key for node in graph.nodes],
            ["t_ember_burst", "t_ember_comet"],
        )
        self.assertEqual(
            len(graph.nodes), len({node.skill_key for node in graph.nodes})
        )
        self.assertEqual(graph.root_keys, ("t_ember_burst",))
        self.assertEqual(
            [(edge.from_key, edge.to_key, edge.min_level) for edge in graph.edges],
            [("t_ember_burst", "t_ember_comet", 3)],
        )
        self.assertEqual((graph.owned_count, graph.total_count), (0, 2))

        # The browser harness grafts the production innate seam rows after the
        # install; the index stays consistent for the extended catalog.
        from web.browser_support.browser_fixtures_data import (
            graft_synth_innate_skills,
        )

        graft_synth_innate_skills()
        self.assertIn("basic_attack", self.registry)
        self.assertEqual(prerequisite_consumers("basic_attack"), ())
        self.assertEqual(
            [node.skill_key for node in build_lineage_view(_entity()).graphs[0].nodes],
            ["t_ember_burst", "t_ember_comet"],
        )

        # Uninstall restores both the shipped rows and the index over them.
        self.assertTrue(uninstall_synthetic_catalogs())
        self.assertEqual(dict(self.registry), self.shipped_rows)
        self.assertEqual(_consumer_snapshot(self.registry), self.shipped_index)

        # A reinstall rebuilds from the installed rows, never from the cache
        # left behind by the previous install.
        self.assertTrue(install_synthetic_catalogs(("skills",)))
        self.assertEqual(
            prerequisite_consumers("t_ember_burst"),
            (("t_ember_comet", 3),),
        )
        self.assertEqual(
            [node.skill_key for node in build_lineage_view(_entity()).graphs[0].nodes],
            ["t_ember_burst", "t_ember_comet"],
        )


class ScopedGraphLineageTests(unittest.TestCase):
    """Independent branch-and-merge DAG plus fail-closed source validation."""

    # a -> side, a -> merge, b -> merge, merge -> sink. The merge node has two
    # parents; the emitted order is deterministic by registry order.
    DAG = {
        "t_dag_a": make_skill("t_dag_a", label="測試根系甲"),
        "t_dag_b": make_skill("t_dag_b", label="測試根系乙"),
        "t_dag_side": make_skill(
            "t_dag_side",
            label="測試支流",
            prerequisites=(SkillPrerequisite("t_dag_a", 1),),
        ),
        "t_dag_merge": make_skill(
            "t_dag_merge",
            label="測試合流",
            prerequisites=(
                SkillPrerequisite("t_dag_a", 2),
                SkillPrerequisite("t_dag_b", 3),
            ),
        ),
        "t_dag_sink": make_skill(
            "t_dag_sink",
            label="測試末梢",
            prerequisites=(SkillPrerequisite("t_dag_merge", 4),),
        ),
    }

    def setUp(self):
        self.shipped_index = _consumer_snapshot(SKILL_REGISTRY)
        self.addCleanup(
            lambda: self.assertEqual(
                _consumer_snapshot(SKILL_REGISTRY), self.shipped_index
            )
        )

    @covers_requirement(
    "skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-"
    "side-effect-free"
)
    def test_branch_and_two_parent_merge_keep_one_ordered_node_each(self):
        with synthetic_registries("skills", extra={"skills": self.DAG}):
            self.assertEqual(
                prerequisite_consumers("t_dag_a"),
                (("t_dag_side", 1), ("t_dag_merge", 2)),
            )
            self.assertEqual(
                prerequisite_consumers("t_dag_b"),
                (("t_dag_merge", 3),),
            )
            view = build_lineage_view(_entity())
            graph = next(
                item for item in view.graphs if item.graph_id == "t_dag_a"
            )
            # Registry order is the kit rows first, then this scope's extras.
            self.assertEqual(
                [node.skill_key for node in graph.nodes],
                ["t_dag_a", "t_dag_b", "t_dag_side", "t_dag_merge", "t_dag_sink"],
            )
            self.assertEqual(len(graph.nodes), len({n.skill_key for n in graph.nodes}))
            self.assertEqual(graph.root_keys, ("t_dag_a", "t_dag_b"))
            self.assertEqual(
                {(edge.from_key, edge.to_key, edge.min_level) for edge in graph.edges},
                {
                    ("t_dag_a", "t_dag_side", 1),
                    ("t_dag_a", "t_dag_merge", 2),
                    ("t_dag_b", "t_dag_merge", 3),
                    ("t_dag_merge", "t_dag_sink", 4),
                },
            )
            depths = {node.skill_key: node.depth for node in graph.nodes}
            self.assertEqual(
                depths,
                {
                    "t_dag_a": 0,
                    "t_dag_b": 0,
                    "t_dag_side": 1,
                    "t_dag_merge": 1,
                    "t_dag_sink": 2,
                },
            )
            # Deterministic across builds and no query-time repair.
            self.assertEqual(view, build_lineage_view(_entity()))

    @covers_requirement(
    "skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-"
    "side-effect-free"
)
    def test_cycle_still_fails_closed_without_disturbing_live_caches(self):
        before = _consumer_snapshot(SKILL_REGISTRY)
        cyclic = {
            "t_cycle_a": make_skill(
                "t_cycle_a",
                prerequisites=(SkillPrerequisite("t_cycle_b", 1),),
            ),
            "t_cycle_b": make_skill(
                "t_cycle_b",
                prerequisites=(SkillPrerequisite("t_cycle_a", 1),),
            ),
        }
        with self.assertRaises(ValueError) as caught:
            validate_prerequisite_graph(cyclic)
        self.assertIn("cyclic", str(caught.exception))
        # The refusal happens before the cache swap: the live index still
        # describes the live registry, with no fabricated rows.
        self.assertEqual(_consumer_snapshot(SKILL_REGISTRY), before)

    @covers_requirement(
    "skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-"
    "side-effect-free"
)
    def test_malformed_proficiency_still_fails_closed(self):
        with synthetic_registries("skills", extra={"skills": self.DAG}):
            entity = _entity(proficiency={"t_dag_a": "not-a-number"})
            with self.assertRaises(LineageQueryError):
                build_lineage_view(entity)
            self.assertEqual(
                entity.db.skill_proficiency, {"t_dag_a": "not-a-number"}
            )
