"""Boundary tests for the ``lineage`` panel contract (skill-lineage-panel §2.4).

Every wire cap is pinned here on the Python mirror: schema/kind fields, one-
over rejections, the declared truncation order, full-view header counts under
truncation, and the byte-budget fail-closed. Presenter-side malformed-input
behavior rides the registry's common unavailable form.
"""

import dataclasses
import unittest
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement


from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.lineage import (
    LINEAGE_SCHEMA_VERSION,
    MAX_CHAINS,
    MAX_NODES_PER_CHAIN,
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
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    validate_prerequisite_graph,
)

# The canonical fire chain plus its sister spells (full root closure).
FIRE_KEYS = (
    "fire_arrow",
    "fire_ball",
    "scorching_wave",
    "firestorm",
    "lava_burst",
    "dragon_flame",
    "phoenix_eternal_flame",
    "infernal_wrap",
    "hellfire",
    "world_ending_blaze",
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
        pk=None,
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
        "level": 1,
        "xp_into_level": 23.0,
        "xp_to_next_level": SKILL_PROFICIENCY_XP_PER_LEVEL - 23.0,
        "capped": False,
        "prereq_text_zh": "",
    }
    node.update(overrides)
    return node


def _chain(root, nodes=None, node_count=2, **overrides):
    if nodes is None:
        nodes = (
            [_node(root)]
            + [_node(f"{root}_n{index}") for index in range(1, node_count)]
            if node_count >= 1
            else []
        )
    chain = {
        "root_skill_key": root,
        "element_or_style_zh": "測試風格",
        "consumed": False,
        "meter": 0.5,
        "nodes": nodes,
    }
    chain.update(overrides)
    return chain


def _payload(chains, completed=0, total=None):
    return {
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "available": True,
        "kind": "lineage",
        "completed_count": completed,
        "total_count": len(chains) if total is None else total,
        "chains": chains,
    }


class ValidatorFieldTests(unittest.TestCase):
    """Exact fields, kind, and one-over boundary rejections."""

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_valid_minimal_payload_normalizes(self):
        payload = _payload([_chain("root_a")])
        normalized = validate_lineage(payload)
        self.assertEqual(normalized["kind"], "lineage")
        self.assertEqual(normalized["schema_version"], 1)
        self.assertEqual(normalized["chains"][0]["root_skill_key"], "root_a")

    def test_kind_must_be_lineage(self):
        payload = _payload([_chain("root_a")])
        payload["kind"] = "character"
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    def test_wrong_schema_version_rejected(self):
        payload = _payload([_chain("root_a")])
        payload["schema_version"] = 2
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    def test_unknown_field_rejected(self):
        payload = _payload([_chain("root_a")])
        payload["extra"] = True
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    def test_completed_count_must_not_exceed_total(self):
        payload = _payload([_chain("root_a")], completed=2, total=1)
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_chain_count_caps(self):
        at_cap = _payload([_chain(f"root_{index}", node_count=1) for index in range(MAX_CHAINS)])
        # 16 one-node chains serialize under the envelope and pass.
        self.assertLessEqual(json_byte_size(at_cap), MAX_CANONICAL_JSON_BYTES)
        validate_lineage(at_cap)
        over = _payload(
            [_chain(f"root_{index}", node_count=1) for index in range(MAX_CHAINS + 1)]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(over)

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_node_count_caps(self):
        at_cap = _payload([_chain("root_a", node_count=MAX_NODES_PER_CHAIN)])
        validate_lineage(at_cap)
        over = _payload([_chain("root_a", node_count=MAX_NODES_PER_CHAIN + 1)])
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(over)

    def test_empty_chain_rejected(self):
        payload = _payload([_chain("root_a", node_count=0)])
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_text_caps(self):
        long_text = "測" * (MAX_TEXT_CODE_POINTS + 1)
        for mutate in (
            lambda chain: chain["nodes"][0].__setitem__("display_name_zh", long_text),
            lambda chain: chain["nodes"][0].__setitem__("prereq_text_zh", long_text),
            lambda chain: chain.__setitem__("element_or_style_zh", long_text),
        ):
            chain = _chain("root_a")
            mutate(chain)
            with self.assertRaises(ProtocolValidationError):
                validate_lineage(_payload([chain]))

    def test_meter_bounds(self):
        for meter in (-0.1, 1.1):
            with self.assertRaises(ProtocolValidationError):
                validate_lineage(_payload([_chain("root_a", meter=meter)]))

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_head_truncation_keeps_the_root(self):
        # Truncated chains keep their head: nodes[0] must remain the root.
        chain = _chain("root_a")
        chain["nodes"] = chain["nodes"][1:]
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(_payload([chain]))

    def test_byte_budget_fails_closed_on_the_theoretical_worst_case(self):
        # Per-field ceilings are bounds, not a guarantee any combination fits:
        # 16 chains x 32 nodes at the text cap exceeds the envelope and the
        # validator fails it closed (the presenter truncates instead).
        chains = []
        for index in range(MAX_CHAINS):
            root = f"root_{index}"
            nodes = [
                _node(
                    f"root_{index}" if node_index == 0 else f"n{index}_{node_index}",
                    display_name_zh="測" * MAX_TEXT_CODE_POINTS,
                )
                for node_index in range(MAX_NODES_PER_CHAIN)
            ]
            chains.append(_chain(root, nodes=nodes))
        payload = _payload(chains)
        self.assertGreater(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        with self.assertRaises(ProtocolValidationError):
            validate_lineage(payload)


class InjectedRegistryMixin(unittest.TestCase):
    def setUp(self):
        self.canonical = dict(SKILL_REGISTRY)

    def tearDown(self):
        SKILL_REGISTRY.clear()
        SKILL_REGISTRY.update(self.canonical)
        validate_prerequisite_graph(SKILL_REGISTRY)


class PresenterTests(InjectedRegistryMixin):
    """Truncation order, full-view counts, and unavailable fail-closed.

    The canonical fire chain is present in every injected view (chains come
    from the registry, not ownership) and sits FIRST in registry order, so
    expectations below add it to the injected ladder count.
    """

    def _inject_ladder_chains(self, count: int, depth: int, fat_text: int = 0):
        """Inject ``count`` linear chains of ``depth`` skills each."""
        registry_extras: dict[str, SkillDef] = {}
        for chain_index in range(count):
            root = f"lr{chain_index}_0"
            registry_extras[root] = _fake_skill(root)
            for depth_index in range(1, depth):
                key = f"lr{chain_index}_{depth_index}"
                registry_extras[key] = _fake_skill(
                    key, prereq=f"lr{chain_index}_{depth_index - 1}"
                )
        SKILL_REGISTRY.update(registry_extras)
        validate_prerequisite_graph(SKILL_REGISTRY)
        if fat_text:
            for key in registry_extras:
                skill = SKILL_REGISTRY[key]
                SKILL_REGISTRY[key] = dataclasses.replace(
                    skill, label="測" * fat_text
                )
        return tuple(registry_extras)

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_malformed_proficiency_fails_closed_as_unavailable(self):
        registry = build_production_registry()
        context = _context(_entity(FIRE_KEYS, {"fire_arrow": "junk"}))
        payload = registry.render("lineage", context)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "lineage_unavailable")

    @covers_requirement("skill-lineage-panel::the-lineage-panel-ships-as-one-bounded-versioned-oob-contract")
    def test_chain_cap_truncates_trailing_chains_with_full_view_counts(self):
        keys = self._inject_ladder_chains(MAX_CHAINS + 4, 2)
        # Fully saturate one ladder (both nodes) so completed_count is 1.
        proficiency = {
            "lr0_0": 10 * SKILL_PROFICIENCY_XP_PER_LEVEL,
            "lr0_1": 10 * SKILL_PROFICIENCY_XP_PER_LEVEL,
        }
        payload = lineage_presenter(_context(_entity(keys, proficiency)))
        self.assertEqual(len(payload["chains"]), MAX_CHAINS)
        # Full view = injected ladders + the canonical fire chain.
        self.assertEqual(payload["total_count"], MAX_CHAINS + 4 + 1)
        self.assertEqual(payload["completed_count"], 1)

    def test_node_cap_truncates_trailing_nodes(self):
        keys = self._inject_ladder_chains(1, MAX_NODES_PER_CHAIN + 8)
        payload = lineage_presenter(_context(_entity(keys)))
        chain = next(
            item for item in payload["chains"] if item["root_skill_key"] == "lr0_0"
        )
        self.assertEqual(len(chain["nodes"]), MAX_NODES_PER_CHAIN)
        self.assertEqual(chain["nodes"][0]["skill_key"], "lr0_0")
        # The meter/consumed still describe the FULL chain, not the truncated
        # node list: an all-level-0 chain has meter 0 regardless.
        self.assertEqual(chain["meter"], 0.0)
        self.assertFalse(chain["consumed"])

    def test_max_length_labels_keep_the_panel_available(self):
        # Rubber-duck R2-1: a legal 128-code-point registry label renders a
        # prerequisite gate LONGER than the bound unless the read model clamps
        # it. The panel must stay available with every text in bound.
        self._inject_ladder_chains(
            1, 3, fat_text=MAX_TEXT_CODE_POINTS
        )
        # duck-style ladder with an unmet edge: level 0 everywhere locks the
        # non-root nodes, so their 「需「label Lv.1」」 text renders.
        payload = lineage_presenter(_context(_entity(())))
        self.assertTrue(payload["available"])
        validate_lineage(payload)
        for chain in payload["chains"]:
            self.assertLessEqual(
                len(chain["element_or_style_zh"]), MAX_TEXT_CODE_POINTS
            )
            for node in chain["nodes"]:
                self.assertLessEqual(len(node["display_name_zh"]), MAX_TEXT_CODE_POINTS)
                self.assertLessEqual(len(node["prereq_text_zh"]), MAX_TEXT_CODE_POINTS)

    def test_byte_budget_drops_further_trailing_chains(self):
        # Text-capped labels force stage three: even at the chain and node
        # caps the payload exceeds the envelope, so trailing chains drop.
        # Labels sit 8 code points under the text cap so the derived prereq
        # line (需「label Lv.1」 = 7 chars + label) also fits; node count and
        # chain count do the byte pressure.
        keys = self._inject_ladder_chains(
            MAX_CHAINS, MAX_NODES_PER_CHAIN, fat_text=MAX_TEXT_CODE_POINTS - 8
        )
        payload = lineage_presenter(_context(_entity(keys)))
        self.assertLess(len(payload["chains"]), MAX_CHAINS)
        self.assertEqual(payload["total_count"], MAX_CHAINS + 1)
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        validate_lineage(payload)

    def test_real_registry_payload_is_small(self):
        payload = lineage_presenter(_context(_entity()))
        self.assertLess(json_byte_size(payload), 48 * 1024)
