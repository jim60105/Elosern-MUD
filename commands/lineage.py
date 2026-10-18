"""Player-facing ``lineage`` / ``系譜`` command: the skill graphs in text.

Prints the exact ``world.rules.lineage_query`` view the WebClient panel
renders for the named party member (default: the commander): connected graphs
in registry order with their roots and owned/total counts, nodes in
topological order with their prerequisite edges and minimum levels, 見頂
markers on saturated nodes, 可解鎖 on ready nodes, and the 「需「X Lv.N」」
line on locked nodes. The command is available in and out of combat and
mutates nothing — building the view is a pure read, and malformed stored
proficiency prints one fixed unavailable line.
"""

from commands.command import Command

from world.rules.lineage_query import LineageQueryError, build_lineage_view
from world.rules.party_scope import (
    PartyScopeError,
    resolve_commander,
    resolve_member_token,
)

_USAGE = "語法：lineage [<成員>]"
_UNAVAILABLE = "你的技能系譜暫時無法閱讀。"
_TIP_MARK = "（見頂）"
_READY_MARK = "（可解鎖）"
_EMPTY = "目前尚無可追蹤的技能系譜。"


class CmdLineage(Command):
    """Print the skill graphs: roots, nodes, edges, and unlock gates."""

    key = "lineage"
    aliases = ("系譜",)
    help_category = "General"

    def func(self) -> None:
        token = self.args.strip()
        try:
            member = (
                resolve_member_token(self.caller, token)
                if token
                else resolve_commander(self.caller)
            )
        except PartyScopeError as error:
            self.caller.msg(error.message)
            return
        try:
            view = build_lineage_view(member)
        except LineageQueryError:
            self.caller.msg(_UNAVAILABLE)
            return
        if not view.graphs:
            self.caller.msg(_EMPTY)
            return
        lines = [f"技能系譜：已完成 {view.completed_count} / {view.total_count} 樹"]
        for graph in view.graphs:
            names = {node.skill_key: node.display_name_zh for node in graph.nodes}
            roots = "‧".join(names[root] for root in graph.root_keys)
            lines.append(
                f"── {graph.group_label_zh}"
                f"（{graph.owned_count}/{graph.total_count}）根：{roots}"
            )
            for node in graph.nodes:
                row = f"  {node.display_name_zh} Lv.{node.level}"
                if node.capped:
                    row += _TIP_MARK
                elif node.owned:
                    row += f"（本階 {node.xp_into_level:g}/{node.xp_into_level + node.xp_to_next_level:g}）"
                elif node.ready:
                    row += _READY_MARK
                parents = [
                    edge
                    for edge in graph.edges
                    if edge.to_key == node.skill_key
                ]
                if parents:
                    row += "　" + " ‧ ".join(
                        f"← {names[edge.from_key]} Lv.{edge.min_level}"
                        for edge in parents
                    )
                if node.prereq_text_zh:
                    row += f"　{node.prereq_text_zh}"
                lines.append(row)
        self.caller.msg("\n".join(lines))
