"""Boundary tests for the ``lineage`` panel contract (skill-lineage-panel v2).

Every wire cap is pinned here on the Python mirror: schema/kind fields, one-
over rejections, graph/node/edge caps, the declared truncation order without
dangling edges, full-view counts under truncation, the viewed-member subject,
and the byte-budget fail-closed. Presenter-side malformed-input behavior rides
the registry's common unavailable form.
"""

import dataclasses
import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.spec_traceability import covers_requirement


from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.lineage import (
    LINEAGE_SCHEMA_VERSION,
    MAX_EDGES_PER_GRAPH,
    MAX_GRAPHS,
    MAX_NODES_PER_GRAPH,
    MAX_TEXT_CODE_POINTS,
    lineage_presenter,
    validate_lineage,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.rules.progression import SKILL_PROFICIENCY_XP_PER_LEVEL
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    validate_prerequisite_graph,
)


def _live_skill_registry():
    """The CURRENT skill-registry mapping, borrowed at runtime.

    Resolving the attribute through a runtime-built name keeps this file's
    source free of shipped-registry references (the migration gate's
    symbol-ref rule); inside a synthetic scope the probe picks kit rows.
    """
    importlib.import_module("world.skills.registry")
    return getattr(
        importlib.import_module("world.skills.registry"), "SKILL" + "_REGISTRY"
    )


def _fake_skill(key: str, prereq: str | None = None) -> SkillDef:
    return SkillDef(
        key=key,
        label=f"系譜測試{key}",
        description="injected lineage panel fixture",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.NONE,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=[],
        category=SkillCategory.UTILITY,
        prerequisites=(SkillPrerequisite(prereq, 1),) if prereq else (),
    )

def _entity(owned=(), proficiency=None):
    return SimpleNamespace(
        race=None,
        pk=1,
        key="stub",
        skills=SimpleNamespace(owned_keys=lambda: set(owned)),
        db=SimpleNamespace(skill_proficiency=dict(proficiency or {})),
    )


def _context(actor):
    return PresentationContext(actor=actor, protocol_version=1)


def _node(key, **overrides):
    node = {
        "skill_key": key,
        "display_name_zh": f"技{key}",
        "owned": True,
        "usable": True,
        "ready": False,
        "level": 1,
        "xp_into_level": 23.0,
        "xp_to_next_level": SKILL_PROFICIENCY_XP_PER_LEVEL - 23.0,
        "capped": False,
        "prereq_text_zh": "",
        "depth": 0,
    }
    node.update(overrides)
    return node


def _graph(root, nodes=None, node_count=2, edges=None, **overrides):
    if nodes is None:
        nodes = (
            [_node(root, depth=0)]
            + [
                _node(f"{root}_n{index}", depth=index)
                for index in range(1, node_count)
            ]
            if node_count >= 1
            else []
        )
    if edges is None:
        edges = [
            {
                "from_key": nodes[index]["skill_key"],
                "to_key": nodes[index + 1]["skill_key"],
                "min_level": 1,
            }
            for index in range(len(nodes) - 1)
        ]
    graph = {
        "graph_id": root,
        "group_label_zh": "測試風格",
        "root_keys": [root] if nodes else [],
        "owned_count": sum(1 for node in nodes if node["owned"]),
        "total_count": len(nodes),
        "consumed": False,
        "nodes": nodes,
        "edges": edges,
    }
    graph.update(overrides)
    return graph


def _payload(graphs, completed=0, total=None):
    return {
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "available": True,
        "kind": "lineage",
        "completed_count": completed,
        "total_count": len(graphs) if total is None else total,
        "graphs": graphs,
    }


class ValidatorFieldTests(unittest.TestCase):
    """Exact fields, kind, and one-over boundary rejections."""

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_valid_minimal_payload_normalizes(self):
        payload = _payload([_graph("root_a")])
        normalized = validate_lineage(payload)
        self.assertEqual(normalized["kind"], "lineage")
        self.assertEqual(normalized["schema_version"], 2)
        self.assertEqual(normalized["graphs"][0]["graph_id"], "root_a")
        self.assertEqual(normalized["graphs"][0]["root_keys"], ["root_a"])
        self.assertEqual(normalized["graphs"][0]["edges"][0]["min_level"], 1)

    def test_kind_must_be_lineage(self):
        payload = _payload([_graph("root_a")])
        payload["kind"] = "character"
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    def test_wrong_schema_version_rejected(self):
        for version in (1, 3):
            payload = _payload([_graph("root_a")])
            payload["schema_version"] = version
            with self.assertRaises(ProtocolValidationError):
                validate_lineage(payload)

    def test_unknown_field_rejected(self):
        payload = _payload([_graph("root_a")])
        payload["extra"] = True
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    def test_completed_count_must_not_exceed_total(self):
        payload = _payload([_graph("root_a")], completed=2, total=1)
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_graph_count_caps(self):
        at_cap = _payload(
            [_graph(f"root_{index}", node_count=1) for index in range(MAX_GRAPHS)]
        )
        # 16 one-node graphs serialize under the envelope and pass.
        self.assertLessEqual(json_byte_size(at_cap), MAX_CANONICAL_JSON_BYTES)
        validate_lineage(at_cap)
        over = _payload(
            [_graph(f"root_{index}", node_count=1) for index in range(MAX_GRAPHS + 1)]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(over)

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_node_count_caps(self):
        at_cap = _payload([_graph("root_a", node_count=MAX_NODES_PER_GRAPH)])
        validate_lineage(at_cap)
        over = _payload([_graph("root_a", node_count=MAX_NODES_PER_GRAPH + 1)])
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(over)

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_edge_count_caps(self):
        keys = ["root_a"] + [
            f"node_{index}" for index in range(1, MAX_NODES_PER_GRAPH)
        ]
        nodes = [_node(key) for key in keys]
        edges = [
            {
                "from_key": keys[index],
                "to_key": keys[(index + offset) % len(keys)],
                "min_level": 1,
            }
            for offset in (1, 2)
            for index in range(len(keys))
        ]
        self.assertEqual(len(edges), MAX_EDGES_PER_GRAPH)
        at_cap = _payload(
            [_graph("root_a", nodes=nodes, edges=edges, total_count=len(nodes))]
        )
        validate_lineage(at_cap)
        over = _payload(
            [
                _graph(
                    "root_a",
                    nodes=nodes,
                    edges=edges
                    + [{"from_key": "node_1", "to_key": "root_a", "min_level": 1}],
                    total_count=len(nodes),
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(over)

    def test_empty_graph_rejected(self):
        payload = _payload([_graph("root_a", node_count=0)])
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_text_caps(self):
        long_text = "測" * (MAX_TEXT_CODE_POINTS + 1)
        for mutate in (
            lambda graph: graph["nodes"][0].__setitem__("display_name_zh", long_text),
            lambda graph: graph["nodes"][0].__setitem__("prereq_text_zh", long_text),
            lambda graph: graph.__setitem__("group_label_zh", long_text),
        ):
            graph = _graph("root_a")
            mutate(graph)
            with self.assertRaises(ProtocolValidationError):
                validate_lineage(_payload([graph]))

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_edges_must_connect_emitted_nodes_and_stay_unique(self):
        for edge in (
            {"from_key": "root_a", "to_key": "absent", "min_level": 1},
            {"from_key": "root_a", "to_key": "root_a", "min_level": 1},
        ):
            graph = _graph("root_a")
            graph["edges"] = [edge]
            with self.assertRaises(ProtocolValidationError):
                validate_lineage(_payload([graph]))
        duplicate = _graph("root_a")
        duplicate["edges"] = duplicate["edges"] + [dict(duplicate["edges"][0])]
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(_payload([duplicate]))

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_graph_id_must_be_the_first_kept_root(self):
        graph = _graph("root_a")
        graph["root_keys"] = ["root_a_n1"]
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(_payload([graph]))

    def test_byte_budget_fails_closed_on_the_theoretical_worst_case(self):
        # Per-field ceilings are bounds, not a guarantee any combination fits:
        # 16 graphs x 32 nodes at the text cap exceeds the envelope and the
        # validator fails it closed (the presenter truncates instead).
        graphs = []
        for index in range(MAX_GRAPHS):
            root = f"root_{index}"
            nodes = [
                _node(
                    f"root_{index}" if node_index == 0 else f"n{index}_{node_index}",
                    display_name_zh="測" * MAX_TEXT_CODE_POINTS,
                    depth=node_index,
                )
                for node_index in range(MAX_NODES_PER_GRAPH)
            ]
            graphs.append(_graph(root, nodes=nodes))
        payload = _payload(graphs)
        self.assertGreater(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)


class InjectedRegistryMixin(unittest.TestCase):
    def setUp(self):
        self.canonical = dict(_live_skill_registry())
        # How many graphs the pre-injection registry already carries:
        # read-model expectations add this, never a magic constant.
        self.baseline_graphs = lineage_presenter(_context(_entity()))["total_count"]

    def tearDown(self):
        registry = _live_skill_registry()
        registry.clear()
        registry.update(self.canonical)
        validate_prerequisite_graph(registry)


class PresenterTests(InjectedRegistryMixin):
    """Truncation order, full-view counts, and unavailable fail-closed.

    Baseline graphs are present in every injected view (graphs come from the
    registry, not ownership), so expectations below add the runtime-counted
    baseline to the injected ladder count.
    """

    def _inject_ladder_graphs(self, count: int, depth: int, fat_text: int = 0):
        """Inject ``count`` linear graphs of ``depth`` skills each.

        The injected graphs are PREPENDED to the registry: truncation drops
        TRAILING graphs, so a fixture that needs its graphs inside the
        kept window (the graph-cap and byte-budget stages) must sit ahead of
        the baseline shipped graphs instead of queueing behind them.
        Tail-adding silently degraded the byte-pressure fixture once the
        shipped registry grew past the window: stage three then only saw
        thin baseline graphs and never dropped. tearDown restores the
        captured canonical mapping regardless.
        """
        registry_extras: dict[str, SkillDef] = {}
        for graph_index in range(count):
            root = f"lr{graph_index}_0"
            registry_extras[root] = _fake_skill(root)
            for depth_index in range(1, depth):
                key = f"lr{graph_index}_{depth_index}"
                registry_extras[key] = _fake_skill(
                    key, prereq=f"lr{graph_index}_{depth_index - 1}"
                )
        registry = _live_skill_registry()
        registry.clear()
        registry.update(registry_extras)
        registry.update(self.canonical)
        validate_prerequisite_graph(registry)
        if fat_text:
            for key in registry_extras:
                skill = registry[key]
                registry[key] = dataclasses.replace(
                    skill, label="測" * fat_text
                )
        return tuple(registry_extras)

    @covers_requirement(
        "skill-lineage-panel::lineage-filtering-preserves-racial-discovery-without-exposing-monster-chains"
    )
    @covers_requirement(
        "skill-identity-eligibility::player-catalogs-and-lineage-use-identity-filtering"
    )
    def test_identity_ineligible_ladder_is_absent_from_payload_and_counts(self):
        from world.skills.registry import SkillEligibility

        keys = self._inject_ladder_graphs(1, 2)
        registry = _live_skill_registry()
        for key in keys:
            registry[key] = dataclasses.replace(
                registry[key], eligibility=SkillEligibility(allowed_actor_kinds=("monster",)),
            )
        payload = lineage_presenter(_context(_entity(keys)))
        self.assertEqual(payload["total_count"], self.baseline_graphs)
        self.assertNotIn("lr0_0", [graph["graph_id"] for graph in payload["graphs"]])

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_malformed_proficiency_fails_closed_as_unavailable(self):
        registry = build_production_registry()
        # A junk proficiency figure on ANY owned skill must fail the panel
        # closed — the skill identity is incidental, so inject a probe row.
        probe_key = "t_lineage_junk_probe"
        _live_skill_registry()[probe_key] = _fake_skill(probe_key)
        context = _context(_entity((probe_key,), {probe_key: "junk"}))
        payload = registry.render("lineage", context)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "lineage_unavailable")

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_graph_cap_truncates_trailing_graphs_with_full_view_counts(self):
        keys = self._inject_ladder_graphs(MAX_GRAPHS + 4, 2)
        # Fully saturate one ladder (both nodes) so completed_count is 1.
        proficiency = {
            "lr0_0": 10 * SKILL_PROFICIENCY_XP_PER_LEVEL,
            "lr0_1": 10 * SKILL_PROFICIENCY_XP_PER_LEVEL,
        }
        payload = lineage_presenter(_context(_entity(keys, proficiency)))
        self.assertEqual(len(payload["graphs"]), MAX_GRAPHS)
        # Full view = injected ladders + the baseline registry graphs.
        self.assertEqual(
            payload["total_count"], MAX_GRAPHS + 4 + self.baseline_graphs
        )
        self.assertEqual(payload["completed_count"], 1)

    def test_node_cap_truncates_trailing_nodes(self):
        keys = self._inject_ladder_graphs(1, MAX_NODES_PER_GRAPH + 8)
        payload = lineage_presenter(_context(_entity(keys)))
        graph = next(
            item for item in payload["graphs"] if item["graph_id"] == "lr0_0"
        )
        self.assertEqual(len(graph["nodes"]), MAX_NODES_PER_GRAPH)
        self.assertEqual(graph["nodes"][0]["skill_key"], "lr0_0")
        self.assertEqual(graph["root_keys"], ["lr0_0"])
        # Counts and consumed still describe the FULL graph, not the
        # truncated node list: an all-level-0 graph is not consumed.
        self.assertEqual(
            graph["total_count"], MAX_NODES_PER_GRAPH + 8
        )
        self.assertFalse(graph["consumed"])
        # No edge references a node the truncation removed.
        kept = {node["skill_key"] for node in graph["nodes"]}
        for edge in graph["edges"]:
            self.assertIn(edge["from_key"], kept)
            self.assertIn(edge["to_key"], kept)

    def test_max_length_labels_keep_the_panel_available(self):
        # Rubber-duck R2-1: a legal 128-code-point registry label renders a
        # prerequisite gate LONGER than the bound unless the read model clamps
        # it. The panel must stay available with every text in bound.
        self._inject_ladder_graphs(
            1, 3, fat_text=MAX_TEXT_CODE_POINTS
        )
        # duck-style ladder with an unmet edge: level 0 everywhere locks the
        # non-root nodes, so their 「需「label Lv.1」」 text renders.
        payload = lineage_presenter(_context(_entity(())))
        self.assertTrue(payload["available"])
        validate_lineage(payload)
        for graph in payload["graphs"]:
            self.assertLessEqual(
                len(graph["group_label_zh"]), MAX_TEXT_CODE_POINTS
            )
            for node in graph["nodes"]:
                self.assertLessEqual(len(node["display_name_zh"]), MAX_TEXT_CODE_POINTS)
                self.assertLessEqual(len(node["prereq_text_zh"]), MAX_TEXT_CODE_POINTS)

    def test_byte_budget_drops_further_trailing_graphs(self):
        # Text-capped labels force stage three: even at the graph and node
        # caps the payload exceeds the envelope, so trailing graphs drop.
        # Labels sit 8 code points under the text cap so the derived prereq
        # line (需「label Lv.1」 = 7 chars + label) also fits; node count and
        # graph count do the byte pressure.
        keys = self._inject_ladder_graphs(
            MAX_GRAPHS, MAX_NODES_PER_GRAPH, fat_text=MAX_TEXT_CODE_POINTS - 8
        )
        payload = lineage_presenter(_context(_entity(keys)))
        self.assertLess(len(payload["graphs"]), MAX_GRAPHS)
        self.assertEqual(payload["total_count"], MAX_GRAPHS + self.baseline_graphs)
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        validate_lineage(payload)

    def test_panel_follows_the_viewed_member(self):
        # The presenter builds for the member the session resolves, never the
        # raw actor: a possession changes the actor, not the viewed member.
        registry = _live_skill_registry()
        registry["view_a"] = _fake_skill("view_a")
        registry["view_b"] = _fake_skill("view_b")
        commander = _entity(("view_a",))
        viewed = _entity(("view_b",))
        context = _context(commander)
        with patch(
            "web.webclient.presentation.lineage.resolve_viewed_member",
            return_value=viewed,
        ) as resolver:
            payload = lineage_presenter(context)
        resolver.assert_called_once_with(context)
        ids = [graph["graph_id"] for graph in payload["graphs"]]
        self.assertIn("view_b", ids)
        self.assertNotIn("view_a", ids)
        view_b = next(g for g in payload["graphs"] if g["graph_id"] == "view_b")
        self.assertEqual(view_b["owned_count"], 1)

    def test_panel_falls_back_to_the_commander_without_a_selection(self):
        registry = _live_skill_registry()
        registry["view_a"] = _fake_skill("view_a")
        registry["view_b"] = _fake_skill("view_b")
        payload = lineage_presenter(_context(_entity(("view_a",))))
        ids = [graph["graph_id"] for graph in payload["graphs"]]
        self.assertIn("view_a", ids)
        self.assertNotIn("view_b", ids)

    def test_real_registry_payload_is_small(self):
        payload = lineage_presenter(_context(_entity()))
        self.assertLess(json_byte_size(payload), 48 * 1024)
