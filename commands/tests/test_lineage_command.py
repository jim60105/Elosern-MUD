"""Command-level tests for the ``lineage`` / ``系譜`` Telnet graph command.

Drives ``lineage`` end to end on a real puppet over the kit's synthetic
prerequisite tree (test-data-independence): the printed graphs equal the pure
view (registry order, roots and counts, topological nodes, explicit edges,
見頂/可解鎖 marks, prerequisite lines), the named party member is honoured,
the stored state is untouched, and a malformed record prints the fixed
unavailable line.
"""

import dataclasses
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from tools.spec_traceability import covers_requirement


from commands.default_cmdsets import CharacterCmdSet
from commands.lineage import CmdLineage
from typeclasses.npcs import NPC
from world.rules.lineage_query import LineageView, build_lineage_view
from world.rules.party import join_party
from world.rules.party_scope import PARTY_SCOPE_MESSAGES, REASON_NOT_PARTY_MEMBER
from world.rules.progression import (
    PROFICIENCY_TIP_CAP,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    proficiency_cap,
)
from world.rules.tests._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
    synth_lineage_tree,
)
from world.skills.registry import SkillPrerequisite, validate_prerequisite_graph

# The kit's seven-node chain plus sister leaves, swapped in for the skills
# scope; the load-time reverse-edge caches are rebuilt against the scoped
# registry on entry and back against the live registry on exit (cleanups are
# LIFO, so the re-validation registers before opening the scope).
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
TREE_CLOSURE = TREE_CHAIN + ("t_tree_mossback", "t_tree_burrow", "t_tree_fallen")
_MID_KEY = "t_tree_branch"
_TIP_KEY = "t_tree_crownfire"


def _revalidate_live() -> None:
    validate_prerequisite_graph(live_skill_registry())


class LineageCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        self.addCleanup(_revalidate_live)
        open_synthetic_scope(self, "skills", extra=TREE_EXTRA)
        _revalidate_live()
        super().setUp()
        self.char1.db.skills = {"active": list(TREE_CLOSURE), "passive": []}
        self.char1.db.skill_proficiency = {
            key: SKILL_PROFICIENCY_XP_PER_LEVEL * PROFICIENCY_TIP_CAP
            for key in TREE_CLOSURE
        }
        # The tip needs at least its own (canopy) cap to read as 見頂.
        self.char1.db.skill_proficiency[_TIP_KEY] = (
            SKILL_PROFICIENCY_XP_PER_LEVEL * proficiency_cap(_TIP_KEY)
        )
        # The mid node at level 2 + 23 XP: below its consuming edge, so its
        # child stays locked and the live XP band shows.
        self.char1.db.skill_proficiency[_MID_KEY] = (
            SKILL_PROFICIENCY_XP_PER_LEVEL * 2 + 23
        )
        self.before = dict(self.char1.db.skill_proficiency)
        self.companion = create_object(
            NPC, key="艾拉", location=self.room1, home=self.room1
        )
        join_party(self.companion, self.char1)
        self.companion.db.skills = {"active": [TREE_CHAIN[0]], "passive": []}
        self.companion.db.skill_proficiency = {TREE_CHAIN[0]: 0.0}

    @covers_requirement("skill-lineage-panel::the-lineage-telnet-command-mirrors-the-panel-surface")
    def test_printed_tree_mirrors_the_view(self):
        view = build_lineage_view(self.char1)
        output = self.call(CmdLineage(), "")
        self.assertIn(
            f"已完成 {view.completed_count} / {view.total_count} 樹", output
        )
        graph = next(g for g in view.graphs if g.graph_id == "t_tree_root")
        self.assertIn(
            f"── {graph.group_label_zh}"
            f"（{graph.owned_count}/{graph.total_count}）根："
            f"{TREE['t_tree_root'].label}",
            output,
        )
        positions = [output.index(node.display_name_zh) for node in graph.nodes]
        self.assertEqual(positions, sorted(positions))
        tip = next(n for n in graph.nodes if n.skill_key == _TIP_KEY)
        self.assertTrue(tip.capped)
        self.assertIn(f"{tip.display_name_zh} Lv.{tip.level}（見頂）", output)
        locked = next(n for n in graph.nodes if n.skill_key == "t_tree_bloom")
        self.assertFalse(locked.usable)
        self.assertIn(locked.prereq_text_zh, output)
        edge = next(
            edge for edge in graph.edges if edge.to_key == "t_tree_bloom"
        )
        self.assertIn(
            f"← {TREE[edge.from_key].label} Lv.{edge.min_level}", output
        )
        mid = next(n for n in graph.nodes if n.skill_key == _MID_KEY)
        self.assertFalse(mid.capped)
        self.assertIn("本階 23/50", output)

    @covers_requirement("skill-lineage-panel::the-lineage-telnet-command-mirrors-the-panel-surface")
    def test_malformed_record_prints_the_fixed_line_and_writes_nothing(self):
        self.char1.db.skill_proficiency[_MID_KEY] = "junk"
        output = self.call(CmdLineage(), "")
        self.assertEqual(output, "你的技能系譜暫時無法閱讀。")
        # The corrupt value is still stored untouched: the command repaired nothing.
        self.assertEqual(self.char1.db.skill_proficiency[_MID_KEY], "junk")

    def test_a_non_member_token_is_refused_with_the_shared_message(self):
        output = self.call(CmdLineage(), "不存在的人")
        self.assertEqual(
            output, PARTY_SCOPE_MESSAGES[REASON_NOT_PARTY_MEMBER]
        )

    @covers_requirement("skill-lineage-panel::the-lineage-telnet-command-mirrors-the-panel-surface")
    def test_named_member_prints_that_members_graphs(self):
        output = self.call(CmdLineage(), "艾拉")
        view = build_lineage_view(self.companion)
        self.assertIn(
            f"已完成 {view.completed_count} / {view.total_count} 樹", output
        )
        graph = next(g for g in view.graphs if g.graph_id == "t_tree_root")
        self.assertIn(
            f"（{graph.owned_count}/{graph.total_count}）根：", output
        )
        self.assertIn("（1/10）根：", output)

    @covers_requirement("skill-lineage-panel::the-lineage-telnet-command-mirrors-the-panel-surface")
    def test_ready_marker_prints_for_an_unowned_node(self):
        self.char1.db.skills = {
            "active": ["t_tree_root", "t_tree_sprout", _MID_KEY],
            "passive": [],
        }
        self.char1.db.skill_proficiency = {
            _MID_KEY: SKILL_PROFICIENCY_XP_PER_LEVEL * 5
        }
        output = self.call(CmdLineage(), "")
        self.assertIn(f"{TREE['t_tree_bloom'].label} Lv.0（可解鎖）", output)

    @covers_requirement("skill-lineage-panel::the-lineage-telnet-command-mirrors-the-panel-surface")
    def test_capped_ready_node_prints_both_markers(self):
        # Saturation and readiness are independent: an unowned node whose
        # stored band is already at its cap still carries 可解鎖.
        bloom_cap = proficiency_cap("t_tree_bloom")
        self.char1.db.skills = {
            "active": ["t_tree_root", "t_tree_sprout", _MID_KEY],
            "passive": [],
        }
        self.char1.db.skill_proficiency = {
            _MID_KEY: SKILL_PROFICIENCY_XP_PER_LEVEL * 5,
            "t_tree_bloom": SKILL_PROFICIENCY_XP_PER_LEVEL * bloom_cap,
        }
        output = self.call(CmdLineage(), "")
        self.assertIn(
            f"{TREE['t_tree_bloom'].label} Lv.{bloom_cap}（見頂）（可解鎖）",
            output,
        )

    @covers_requirement("skill-lineage-panel::the-lineage-telnet-command-mirrors-the-panel-surface")
    def test_printed_graphs_match_the_bounded_panel_view(self):
        # The command renders the same bounded view the panel serializes:
        # trailing graphs drop under the cap while the full-view counts stay.
        from web.webclient.presentation.context import PresentationContext
        from web.webclient.presentation.lineage import lineage_presenter

        baseline = build_lineage_view(self.char1).total_count
        registry = live_skill_registry()
        registry["cmd_extra"] = dataclasses.replace(
            TREE["t_tree_root"], key="cmd_extra", prerequisites=(), label="指令測試根"
        )
        registry["cmd_extra_child"] = dataclasses.replace(
            TREE["t_tree_sprout"],
            key="cmd_extra_child",
            prerequisites=(SkillPrerequisite("cmd_extra", 1),),
            label="指令測試葉",
        )
        _revalidate_live()
        with patch("web.webclient.presentation.lineage.MAX_GRAPHS", 1):
            payload = lineage_presenter(
                PresentationContext(actor=self.char1, protocol_version=1)
            )
            output = self.call(CmdLineage(), "")
        self.assertEqual(len(payload["graphs"]), 1)
        self.assertEqual(payload["total_count"], baseline + 1)
        self.assertEqual(output.count("── "), 1)
        self.assertIn(
            f"已完成 {payload['completed_count']} / {payload['total_count']} 樹",
            output,
        )
        self.assertIn(payload["graphs"][0]["group_label_zh"], output)

    @covers_requirement("skill-lineage-panel::the-lineage-telnet-command-mirrors-the-panel-surface")
    def test_state_unchanged_after_print(self):
        self.call(CmdLineage(), "")
        self.assertEqual(self.char1.db.skill_proficiency, self.before)
        self.assertEqual(
            self.char1.db.skills, {"active": list(TREE_CLOSURE), "passive": []}
        )

    def test_empty_ledger_prints_the_empty_line(self):
        # A registry without any graph has nothing to print.
        with patch(
            "commands.lineage.build_lineage_view",
            return_value=LineageView(graphs=(), completed_count=0, total_count=0),
        ):
            output = self.call(CmdLineage(), "")
        self.assertEqual(output, "目前尚無可追蹤的技能系譜。")

    @covers_requirement("skill-lineage-panel::the-lineage-telnet-command-mirrors-the-panel-surface")
    def test_command_is_available_in_and_out_of_combat(self):
        cmdset = CharacterCmdSet()
        keys = {command.key for command in cmdset.commands}
        self.assertIn("lineage", keys)
        command = next(c for c in cmdset.commands if c.key == "lineage")
        self.assertIsInstance(command, CmdLineage)
        self.assertIn("系譜", command.aliases)
