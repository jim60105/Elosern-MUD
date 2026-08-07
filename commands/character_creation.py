"""Player-facing character creation command and pending command gate."""

from evennia import CmdSet, Command
from evennia.commands.cmdhandler import CMD_NOMATCH

from commands.localized import CmdHelp, CmdQuit
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


ALLOCATION_AXIS_EXPLANATIONS: dict[str, str] = {
    "hp": "生命值，決定你能承受多少傷害",
    "mp": "魔力值，驅動法術的消耗",
    "sp": "體力值，支撐行動與攻擊",
    "atk_phys": "物理攻擊，影響造成的傷害",
    "agility": "敏捷，影響命中與迴避",
    "defense": "防禦，減免受到的傷害",
}


def creation_start_screen() -> str:
    """Render the no-argument ``character`` presentation (design.md D6).

    A world-view framing line followed by one preview line per preset drawn
    entirely from immutable registry data: the race one-liner, the allocation
    emphasis, and the background. Reused by ``CmdCharacter.func`` and by the
    ``Account.at_post_login`` login coordinator.
    """
    lines = ["你站在伊洛瑟恩大陸的門口，世界正等待你的名字。", "可選擇的預設角色："]
    for key, preset in PLAYER_PRESET_REGISTRY.items():
        race = RACE_REGISTRY[preset.race]
        lines.append(
            f"  {key}（{preset.display_name}）：{race.description} "
            f"｜配點：{preset.emphasis}｜背景：{preset.background}"
        )
    lines.append("請選擇角色建立方式。")
    lines.append(f"預設角色：character preset <key>（{'、'.join(PLAYER_PRESET_REGISTRY)}）")
    lines.append("自訂角色：character create")
    return "\n".join(lines)


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
        from world.rules.onboarding import (
            maybe_play_arrival,
            relocate_to_starting_location,
        )

        # Establish the explicit named portrait policy and schedule the
        # post-commit portrait ensure. A failed activation returns above, so a
        # rolled-back creation never writes a policy or emits a job (design D2/D7).
        self.caller.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(self.caller.pk),
        }
        from world.art.service import schedule_portrait_ensure

        schedule_portrait_ensure(self.caller)

        relocate_to_starting_location(self.caller)
        self.caller.msg(
            f"角色 {result.display_name} 已建立，初始魔法等級為 {result.magic_level}。"
        )
        maybe_play_arrival(self.caller)

    def func(self):
        args = self.args.strip().split()
        if not args:
            self.caller.msg(creation_start_screen())
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
            race_explanations = "\n".join(
                f"  {key}：{RACE_REGISTRY[key].description}" for key in RACE_REGISTRY
            )
            race = (yield (
                f"種族（{'、'.join(RACE_REGISTRY)}，可輸入 cancel 取消）：\n"
                f"{race_explanations}\n"
            )).strip()
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
                explanation = ALLOCATION_AXIS_EXPLANATIONS.get(axis, "")
                allocations[axis] = _integer(
                    (yield f"{axis} 配點（0–{span}）：{explanation}\n"), axis
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
        self.add(CmdHelp)
        self.add(CmdQuit)
