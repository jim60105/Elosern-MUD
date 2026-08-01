"""Player-facing character creation command and pending command gate."""

from evennia import CmdSet, Command, default_cmds
from evennia.commands.cmdhandler import CMD_NOMATCH

from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    resolve_starting_profile,
)


def _integer(response: str, field: str) -> int:
    if response.strip().lower() == "cancel":
        raise CharacterCreationError("角色建立已取消")
    try:
        return int(response.strip())
    except ValueError as error:
        raise CharacterCreationError(f"{field} 必須是整數。") from error


class CmdCharacter(Command):
    """建立角色。用法：character、character preset <key>、character create"""

    key = "character"
    aliases = ("角色",)

    def _activate(self, request: CharacterCreationRequest) -> None:
        try:
            result = activate_player_character(self.account, self.caller, request)
        except CharacterCreationError as error:
            self.caller.msg(f"角色建立失敗：{error}")
            return
        self.caller.msg(
            f"角色 {result.display_name} 已建立，初始魔法等級為 {result.magic_level}。"
        )

    def func(self):
        args = self.args.strip().split()
        if not args:
            presets = "、".join(PLAYER_PRESET_REGISTRY)
            self.caller.msg(
                "請選擇角色建立方式。\n"
                f"預設角色：character preset <key>（{presets}）\n"
                "自訂角色：character create"
            )
            return
        if args[0].lower() == "preset":
            if len(args) != 2:
                self.caller.msg("用法：character preset <key>")
                return
            self._activate(CharacterCreationRequest(mode="preset", preset_key=args[1]))
            return
        if args != ["create"]:
            self.caller.msg("用法：character preset <key> 或 character create")
            return

        try:
            name = yield "角色姓名（輸入 cancel 取消）："
            if name.strip().lower() == "cancel":
                self.caller.msg("已取消角色建立。")
                return
            age = _integer((yield "實際年齡（至少 18，可輸入 cancel 取消）："), "實際年齡")
            apparent_age = _integer((yield "外表年齡（至少 18，可輸入 cancel 取消）："), "外表年齡")
            race = (yield f"種族（{'、'.join(RACE_REGISTRY)}，可輸入 cancel 取消）：").strip()
            if race.lower() == "cancel":
                self.caller.msg("已取消角色建立。")
                return
            available = [key for key, value in SUBRACE_REGISTRY.items() if value.race_key == race]
            prompt = "子種族（可留空或輸入 none）"
            if available:
                prompt += f"（{'、'.join(available)}）"
            subrace = (yield prompt + "：").strip() or None
            if subrace and subrace.lower() == "none":
                subrace = None
            if subrace and subrace.lower() == "cancel":
                self.caller.msg("已取消角色建立。")
                return
            profile = resolve_starting_profile(race, subrace)
            allocations: dict[str, int] = {}
            for axis, (lower, upper) in profile.bounds:
                span = upper - lower
                allocations[axis] = _integer(
                    (yield f"{axis} 配點（0–{span}）："), axis
                )
            summary = (
                f"姓名 {name.strip()}，年齡 {age}/{apparent_age}，種族 {race}，"
                f"子種族 {subrace or '無'}，配點總和 {sum(allocations.values())}/"
                f"{profile.budget}。輸入 yes 確認，或 cancel 取消："
            )
            confirmation = (yield summary).strip().lower()
            if confirmation != "yes":
                self.caller.msg("已取消角色建立。")
                return
            self._activate(CharacterCreationRequest(
                mode="custom", display_name=name, age=age,
                apparent_age=apparent_age, race=race, subrace=subrace,
                allocations=allocations,
            ))
        except CharacterCreationError as error:
            if str(error) == "角色建立已取消":
                self.caller.msg("已取消角色建立。")
            else:
                self.caller.msg(f"輸入無效：{error} 請重新執行 character create。")


class CmdCreationRequired(Command):
    """Explain why an ordinary command is unavailable during creation."""

    key = CMD_NOMATCH

    def func(self) -> None:
        self.caller.msg("你必須先完成角色建立。請輸入 character 查看建立方式。")


class CharacterCreationCmdSet(CmdSet):
    """High-priority replacement set for an uninitialized player shell."""

    key = "CharacterCreation"
    priority = 200
    mergetype = "Replace"
    no_exits = True
    no_objs = True

    def at_cmdset_creation(self) -> None:
        self.add(CmdCharacter)
        self.add(CmdCreationRequired)
        self.add(default_cmds.CmdHelp)
        self.add(default_cmds.CmdQuit)
