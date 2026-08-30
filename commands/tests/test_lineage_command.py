"""Command-level tests for the ``lineage`` Telnet ledger command.

Drives ``lineage`` end to end on a real puppet: the printed tree equals the
pure view (chains registry order, topological nodes, 見頂 marks, prerequisite
lines), the stored state is untouched, and a malformed record prints the fixed
unavailable line.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.lineage import CmdLineage
from world.rules.lineage_query import LineageView, build_lineage_view
from world.rules.progression import SKILL_PROFICIENCY_XP_PER_LEVEL

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


class LineageCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.skills = {"active": list(FIRE_KEYS), "passive": []}
        self.char1.db.skill_proficiency = {
            key: SKILL_PROFICIENCY_XP_PER_LEVEL * 10 for key in FIRE_KEYS
        }
        # fire_ball at level 2 + 23 XP: locked children and a live meter.
        self.char1.db.skill_proficiency["fire_ball"] = (
            SKILL_PROFICIENCY_XP_PER_LEVEL * 2 + 23
        )
        self.before = dict(self.char1.db.skill_proficiency)

    def test_printed_tree_mirrors_the_view(self):
        view = build_lineage_view(self.char1)
        output = self.call(CmdLineage(), "")
        self.assertIn(
            f"已完成 {view.completed_count} / {view.total_count} 樹", output
        )
        chain = next(c for c in view.chains if c.root_skill_key == "fire_arrow")
        positions = [output.index(node.display_name_zh) for node in chain.nodes]
        self.assertEqual(positions, sorted(positions))
        tip = next(n for n in chain.nodes if n.skill_key == "phoenix_eternal_flame")
        self.assertIn(f"{tip.display_name_zh} Lv.{tip.level}（見頂）", output)
        locked = next(n for n in chain.nodes if n.skill_key == "firestorm")
        locked = next(n for n in chain.nodes if n.skill_key == "scorching_wave")
        self.assertFalse(locked.usable)
        self.assertIn(locked.prereq_text_zh, output)
        mid = next(n for n in chain.nodes if n.skill_key == "fire_ball")
        self.assertFalse(mid.capped)
        self.assertIn("本階 23/50", output)

    def test_malformed_record_prints_the_fixed_line_and_writes_nothing(self):
        self.char1.db.skill_proficiency["fire_ball"] = "junk"
        output = self.call(CmdLineage(), "")
        self.assertEqual(output, "你的技能系譜暫時無法閱讀。")
        # The corrupt value is still stored untouched: the command repaired nothing.
        self.assertEqual(self.char1.db.skill_proficiency["fire_ball"], "junk")

    def test_arguments_are_rejected_with_usage(self):
        output = self.call(CmdLineage(), "extra")
        self.assertEqual(output, "語法：lineage")

    def test_state_unchanged_after_print(self):
        self.call(CmdLineage(), "")
        self.assertEqual(self.char1.db.skill_proficiency, self.before)
        self.assertEqual(
            self.char1.db.skills, {"active": list(FIRE_KEYS), "passive": []}
        )

    def test_empty_ledger_prints_the_empty_line(self):
        # A registry without any consumed root has no chains at all.
        with patch(
            "commands.lineage.build_lineage_view",
            return_value=LineageView(chains=(), completed_count=0, total_count=0),
        ):
            output = self.call(CmdLineage(), "")
        self.assertEqual(output, "目前尚無可追蹤的技能系譜。")

    def test_command_is_available_in_and_out_of_combat(self):
        from commands.default_cmdsets import CharacterCmdSet

        keys = {command.key for command in CharacterCmdSet().commands}
        self.assertIn("lineage", keys)
