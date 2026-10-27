"""Localized zh-tw wrappers of the XYZGrid contrib commands (localize-limbo-zhtw D-5).

The project-owned ``ProjectXYZGridCmdSet`` keeps the native builder commands
``@teleport``/``@open`` and replaces ``goto``/``map`` with the zh-tw wrappers,
so no English-keyed variant coexists with them in the merged player set.
"""

from collections import namedtuple

from evennia.contrib.grid.xyzgrid.commands import (
    CmdGoto as _CmdGoto,
    CmdMap as _CmdMap,
    CmdXYZOpen,
    CmdXYZTeleport,
    XYZGridCmdSet,
)
from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid
from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.utils import ansi, list_to_string
from evennia.utils.utils import delay

from world.maps.map_data import SETTLEMENT_GRAPHS, settlement_graph
from world.maps.xymap_graph import graph_from_xymap

PathData = namedtuple("PathData", ("target", "graph", "directions", "legs", "task"))


def _route_graph(z_map_key):
    """Return the declared sparse graph, else adapt the live contrib map.

    Synthetic/builder maps still arrive through the xyzgrid contrib; the
    transient adapter gives them the same route contract without making the
    ASCII lattice the routing authority for declared settlements.
    """

    graph = settlement_graph(z_map_key)
    if graph is not None:
        return graph
    return graph_from_xymap(get_xyzgrid().get_map(z_map_key))


class CmdGoto(_CmdGoto):
    """前往此區域中指定名稱的地點（最短路徑）

    用法：
      path <地點> - 找出到目標地點的最短路徑（不移動）
      前往 <地點> - 沿最短路徑自動移動到目標地點
      path        - 顯示目前目標地點與最短路徑
      前往        - 中止目前的自動移動，否則顯示目前路徑
      path clear  - 清除目前路徑

    找出目前區域內到指定地點的最短路線，並可自動帶你走過去。建造者可以
    指定特定座標（X,Y）。
    """

    key = "前往"
    aliases = ["goto", "path"]
    help_category = "General"

    def func(self):
        """執行前往（上游邏輯，zh-tw 訊息）。"""
        caller = self.caller
        goto_mode = self.cmdname in ("前往", "goto")

        path_data = caller.ndb.xy_path_data

        if not self.args:
            if path_data:
                target_name = path_data.target.get_display_name(caller)
                task = path_data.task
                if goto_mode:
                    if task and task.active():
                        task.cancel()
                        caller.msg(f"已中止前往 {target_name} 的自動移動。")
                        return
                current_path = list_to_string([f"|w{step}|n" for step in path_data.directions])
                moving = "(移動中)" if task and task.active() else ""
                caller.msg(f"前往 {target_name}{moving} 的路徑：{current_path}")
            else:
                caller.msg("用法：前往|path [<地點>]")
            return

        if not goto_mode and self.args == "clear" and path_data:
            caller.ndb.xy_path_data = None
            caller.msg("已清除前往路徑。")
            return

        try:
            xyz_start = caller.location.xyz
        except AttributeError:
            self.caller.msg("目前位置不在網格上，無法計算路徑。")
            return

        allow_xyz_query = caller.locks.check_lockstring(caller, "perm(Builder)")
        if allow_xyz_query and all(char in self.args for char in ("(", ")", ",")):
            target = self._search_by_xyz(self.args, xyz_start)
            if not target:
                return
        else:
            target = self._search_by_key_and_alias(self.args, xyz_start)
            if not target:
                return
        try:
            xyz_end = target.xyz
        except AttributeError:
            self.caller.msg("目標地點不在網格上，無法自動移動過去。")
            return

        graph = _route_graph(xyz_start[2])
        if graph is None:
            self.caller.msg("目前位置不在已宣告的聚落圖上，無法計算路徑。")
            return
        xy_start = xyz_start[:2]
        xy_end = xyz_end[:2]
        legs = list(graph.plan_between_coordinates(xy_start, xy_end))
        directions = [leg.direction for leg in legs]

        caller.msg(
            f"前往 {target.get_display_name(caller)} 共有 {len(directions)} 步："
            f" |w{list_to_string(directions, endsep='|n，最後|w')}|n"
        )

        self._auto_step(
            caller,
            self.session,
            target=target,
            graph=graph,
            directions=directions,
            legs=legs,
            step=goto_mode,
        )

    def _auto_step(
        self,
        caller,
        session,
        target=None,
        graph=None,
        directions=None,
        legs=None,
        step=True,
    ):
        """上游自動移動（zh-tw 訊息；配合「前往」/「goto」/「path」語意）。"""
        path_data = caller.ndb.xy_path_data

        if target:
            if path_data and path_data.task and path_data.task.active():
                path_data.task.cancel()
            path_data = caller.ndb.xy_path_data = PathData(
                target=target,
                graph=graph,
                directions=directions,
                legs=legs,
                task=None,
            )

        if step and path_data:
            legs = path_data.legs
            graph = path_data.graph

            try:
                leg = legs.pop(0)
                path_data.directions.pop(0)
            except IndexError:
                caller.msg("已到達目標。", session=session)
                caller.ndb.xy_path_data = None
                return

            expected_xyz = (leg.source.x, leg.source.y, graph.map_id)
            location = caller.location
            try:
                xyz_start = location.xyz
            except AttributeError:
                caller.ndb.xy_path_data = None
                caller.msg("前往已中止——已離開該區域。", session=session)
                return

            if xyz_start != expected_xyz:
                caller.msg("路徑已改變——重新計算（輸入「前往」中止）", session=session)

                try:
                    xyz_end = path_data.target.xyz
                except AttributeError:
                    caller.ndb.xy_path_data = None
                    caller.msg("前往已中止——目標在區域外。", session=session)
                    return

                if xyz_start[2] != xyz_end[2]:
                    caller.ndb.xy_path_data = None
                    caller.msg("前往已中止——目標在區域外。", session=session)
                    return

                xy_start = xyz_start[:2]
                xy_end = xyz_end[:2]
                legs = list(graph.plan_between_coordinates(xy_start, xy_end))
                directions = [step.direction for step in legs]

                try:
                    leg = legs.pop(0)
                    directions.pop(0)
                except IndexError:
                    caller.msg("已到達目標。", session=session)
                    caller.ndb.xy_path_data = None
                    return

                path_data = caller.ndb.xy_path_data = PathData(
                    target=path_data.target,
                    graph=graph,
                    directions=directions,
                    legs=legs,
                    task=None,
                )

            exit_name = leg.exit_key
            exit_obj = caller.search(exit_name)
            if not exit_obj:
                caller.msg(f"目前位置找不到出口 '{exit_name}'。前往已中止。")
                caller.ndb.xy_path_data = None
                return

            caller.execute_cmd(exit_name, session=session)

            caller.ndb.xy_path_data = PathData(
                target=path_data.target,
                graph=path_data.graph,
                directions=path_data.directions,
                legs=path_data.legs,
                task=delay(self.auto_step_delay, self._auto_step, caller, session),
            )

    def _search_by_xyz(self, inp, xyz_start):
        """上游座標搜尋（zh-tw 訊息）。"""
        inp = inp.strip("()")
        X, Y = inp.split(",", 2)
        Z = xyz_start[2]
        X, Y, Z = str(X).strip(), str(Y).strip(), str(Z).strip()
        try:
            return XYZRoom.objects.get_xyz(xyz=(X, Y, Z))
        except XYZRoom.DoesNotExist:
            self.caller.msg(f"找不到 ({X},{Y})（Z={Z}）的房間。")
            return None


class CmdMap(_CmdMap):
    """顯示一個區域的地圖

    用法：
      地圖 [Z 座標]
      地圖 list

    建造者指令。
    """

    key = "地圖"
    aliases = ["map"]
    locks = "cmd:perm(Builders)"

    def func(self):
        """執行地圖顯示（上游邏輯，zh-tw 訊息）。"""
        xyzgrid = get_xyzgrid()
        Z = None

        if not self.args:
            location = self.caller.location
            try:
                xyz = location.xyz
            except AttributeError:
                self.caller.msg("你目前的位置不在網格上。")
                return
            Z = xyz[2]

        elif self.args.strip().lower() == "list":
            entries = [
                f"{graph.map_id} ({len(graph.nodes)} 個地點)"
                for graph in SETTLEMENT_GRAPHS.values()
            ]
            entries.extend(
                repr(xymap)
                for xymap in xyzgrid.all_maps()
                if xymap.Z not in SETTLEMENT_GRAPHS
            )
            xymaps = "\n ".join(entries)
            self.caller.msg(f"網格上的地圖（Z 座標）：\n |w{xymaps}")
            return

        else:
            Z = self.args

        xymap = xyzgrid.get_map(Z)
        if not xymap:
            graph = settlement_graph(Z)
            if graph is not None:
                self.caller.msg(ansi.raw(_sparse_map_listing(graph)))
                return
            self.caller.msg(
                f"找不到 XYMap '{Z}'。輸入「地圖 list」查看可用的地圖與 Z 座標。"
            )
            return

        self.caller.msg(ansi.raw(xymap.mapstring))


def _sparse_map_listing(graph) -> str:
    """Render one declared settlement as a deterministic node/exit listing.

    The meter scale has no ASCII lattice; the builder-facing map view lists
    each authored location with its physical coordinate and outgoing compass
    exits instead.
    """

    lines = [f"{graph.map_id}（{len(graph.nodes)} 個地點，單位：公尺）"]
    for node in sorted(graph.nodes.values(), key=lambda item: (item.y, item.x)):
        exits = [
            f"{edge.direction}→{edge.destination.key}"
            for edge in graph.edges
            if edge.source.node_id == node.node_id
        ]
        lines.append(
            f" {node.key} ({node.x}, {node.y})："
            + ("、".join(sorted(exits)) if exits else "無")
        )
    return "\n".join(lines)


class ProjectXYZGridCmdSet(XYZGridCmdSet):
    """The project's mounted XYZGrid set: native builder commands plus zh-tw
    wrappers replacing ``goto``/``map`` (localize-limbo-zhtw D-5)."""

    key = "xyzgrid_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdXYZTeleport())
        self.add(CmdXYZOpen())
        self.add(CmdGoto())
        self.add(CmdMap())
