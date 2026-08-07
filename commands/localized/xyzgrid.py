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

PathData = namedtuple("PathData", ("target", "xymap", "directions", "step_sequence", "task"))


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

        xyzgrid = get_xyzgrid()
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

        xymap = xyzgrid.get_map(xyz_start[2])
        xy_start = xyz_start[:2]
        xy_end = xyz_end[:2]
        directions, step_sequence = xymap.get_shortest_path(xy_start, xy_end)

        caller.msg(
            f"前往 {target.get_display_name(caller)} 共有 {len(directions)} 步："
            f" |w{list_to_string(directions, endsep='|n，最後|w')}|n"
        )

        self._auto_step(
            caller,
            self.session,
            target=target,
            xymap=xymap,
            directions=directions,
            step_sequence=step_sequence,
            step=goto_mode,
        )

    def _auto_step(
        self,
        caller,
        session,
        target=None,
        xymap=None,
        directions=None,
        step_sequence=None,
        step=True,
    ):
        """上游自動移動（zh-tw 訊息；配合「前往」/「goto」/「path」語意）。"""
        path_data = caller.ndb.xy_path_data

        if target:
            if path_data and path_data.task and path_data.task.active():
                path_data.task.cancel()
            path_data = caller.ndb.xy_path_data = PathData(
                target=target,
                xymap=xymap,
                directions=directions,
                step_sequence=step_sequence,
                task=None,
            )

        if step and path_data:
            step_sequence = path_data.step_sequence

            try:
                direction = path_data.directions.pop(0)
                current_node = path_data.step_sequence.pop(0)
                first_link = path_data.step_sequence.pop(0)
            except IndexError:
                caller.msg("已到達目標。", session=session)
                caller.ndb.xy_path_data = None
                return

            expected_xyz = (current_node.X, current_node.Y, current_node.Z)
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
                directions, step_sequence = path_data.xymap.get_shortest_path(xy_start, xy_end)

                try:
                    direction = directions.pop(0)
                    current_node = step_sequence.pop(0)
                    first_link = step_sequence.pop(0)
                except IndexError:
                    caller.msg("已到達目標。", session=session)
                    caller.ndb.xy_path_data = None
                    return

                path_data = caller.ndb.xy_path_data = PathData(
                    target=path_data.target,
                    xymap=path_data.xymap,
                    directions=directions,
                    step_sequence=step_sequence,
                    task=None,
                )

            interrupt_node_or_link = None

            while step_sequence:
                if not interrupt_node_or_link and step_sequence[0].interrupt_path:
                    interrupt_node_or_link = step_sequence[0]
                if hasattr(step_sequence[0], "node_index"):
                    break
                step_sequence.pop(0)

            exit_name, *_ = first_link.spawn_aliases.get(
                direction, current_node.direction_spawn_defaults.get(direction, ("unknown",))
            )

            exit_obj = caller.search(exit_name)
            if not exit_obj:
                caller.msg(f"目前位置找不到出口 '{exit_name}'。前往已中止。")
                caller.ndb.xy_path_data = None
                return

            if interrupt_node_or_link:
                if hasattr(interrupt_node_or_link, "node_index"):
                    message = exit_obj.destination.attributes.get(
                        "xyz_path_interrupt_msg", default=self.default_xyz_path_interrupt_msg
                    )
                    caller.execute_cmd(exit_name, session=session)
                else:
                    message = exit_obj.attributes.get(
                        "xyz_path_interrupt_msg", default=self.default_xyz_path_interrupt_msg
                    )
                caller.msg(message)
                return

            caller.execute_cmd(exit_name, session=session)

            caller.ndb.xy_path_data = PathData(
                target=path_data.target,
                xymap=path_data.xymap,
                directions=path_data.directions,
                step_sequence=path_data.step_sequence,
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
            xymaps = "\n ".join(str(repr(xymap)) for xymap in xyzgrid.all_maps())
            self.caller.msg(f"網格上的地圖（Z 座標）：\n |w{xymaps}")
            return

        else:
            Z = self.args

        xymap = xyzgrid.get_map(Z)
        if not xymap:
            self.caller.msg(
                f"找不到 XYMap '{Z}'。輸入「地圖 list」查看可用的地圖與 Z 座標。"
            )
            return

        self.caller.msg(ansi.raw(xymap.mapstring))


class ProjectXYZGridCmdSet(XYZGridCmdSet):
    """The project's mounted XYZGrid set: native builder commands plus zh-tw
    wrappers replacing ``goto``/``map`` (localize-limbo-zhtw D-5)."""

    key = "xyzgrid_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdXYZTeleport())
        self.add(CmdXYZOpen())
        self.add(CmdGoto())
        self.add(CmdMap())
