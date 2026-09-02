"""Player-facing ``lineage`` command: the skill-lineage ledger in text.

Prints the exact ``world.rules.lineage_query`` view the WebClient panel
renders: chains in registry order, nodes in topological order, 見頂 markers on
saturated nodes, and the 「需「X Lv.N」」 line on locked nodes. The command is
available in and out of combat and mutates nothing — building the view is a
pure read, and malformed stored proficiency prints one fixed unavailable line.
"""

from commands.command import Command

from world.rules.lineage_query import LineageQueryError, build_lineage_view

_USAGE = "語法：lineage"
_UNAVAILABLE = "你的技能系譜暫時無法閱讀。"
_TIP_MARK = "（見頂）"
_EMPTY = "目前尚無可追蹤的技能系譜。"


class CmdLineage(Command):
    """Print the skill-lineage ledger: chains, nodes, and unlock gates."""

    key = "lineage"
    help_category = "General"

    def func(self) -> None:
        if self.args.strip():
            self.caller.msg(_USAGE)
            return
        try:
            view = build_lineage_view(self.caller)
        except LineageQueryError:
            self.caller.msg(_UNAVAILABLE)
            return
        if not view.chains:
            self.caller.msg(_EMPTY)
            return
        lines = [f"技能系譜：已完成 {view.completed_count} / {view.total_count} 樹"]
        for chain in view.chains:
            percent = int(round(chain.meter * 100))
            status = "已全數見頂" if chain.consumed else f"進度 {percent}%"
            lines.append(f"── {chain.element_or_style_zh}（{status}）")
            for node in chain.nodes:
                row = f"  {node.display_name_zh} Lv.{node.level}"
                if node.capped:
                    row += _TIP_MARK
                elif node.owned:
                    row += f"（本階 {node.xp_into_level:g}/{node.xp_into_level + node.xp_to_next_level:g}）"
                if node.prereq_text_zh:
                    row += f"　{node.prereq_text_zh}"
                lines.append(row)
        self.caller.msg("\n".join(lines))
