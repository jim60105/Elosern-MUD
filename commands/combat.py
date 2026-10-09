"""Player-facing combat engagement, forfeit, and guild-examination commands."""

from commands.command import Command

from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    forfeit,
    is_in_active_session,
)
from world.rules.combat_view import (
    CombatViewError,
    build_combat_view,
    group_skill_views,
)
from world.rules.guild_exam_request import (
    OUTCOME_SCHEDULE,
    next_exam_rank,
    request_guild_exam,
)
from world.rules.guild_exams import GuildExamError
from world.rules.event_log import render_plain_text
from world.rules.player_messages import session_reason_message
from world.rules.service_messages import (
    exam_schedule_message,
    exam_started_message,
    rejection_message,
)


class CmdEngage(Command):
    """Engage a present hostile monster in combat."""

    key = "engage"
    aliases = ("攻擊", "戰鬥")
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self) -> None:
        if is_in_active_session(self.caller):
            self.caller.msg("你已經在戰鬥中了。")
            return
        target_name = self.args.strip().partition(" ")[0]
        if not target_name:
            self.caller.msg("用法：engage <target>")
            return
        target = self.caller.search(target_name)
        if target is None:
            return
        try:
            result = engage(self.caller, target)
        except CombatSessionError as error:
            reason = error.args[0]
            message = {
                SessionReason.NOT_HOSTILE: "這個目標不是敵對魔物。",
                SessionReason.NOT_PRESENT: "目標不在這裡。",
                SessionReason.TARGET_DEAD: "目標已經無法行動。",
                SessionReason.ALREADY_IN_COMBAT: "你已經在戰鬥中了。",
            }.get(reason, "無法開始戰鬥。")
            self.caller.msg(message)
            return
        self.caller.msg("戰鬥開始！請選擇你的行動（cast <技能>[=<目標>]）。")


class CmdCombatForfeit(Command):
    """Forfeit the active combat session."""

    key = "combat forfeit"
    aliases = ("combat 投降", "投降")

    def func(self) -> None:
        try:
            result = forfeit(self.caller)
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return
        self.caller.msg(
            {
                "defeat": "你投降了，戰鬥以失敗告終。",
                "exam_failed": "你放棄了考核。",
            }.get(result["outcome"], "戰鬥結束。")
        )


class CmdCombatActions(Command):
    """List active skills and session participant tokens during combat."""

    key = "combat actions"
    aliases = ("combat 動作", "戰鬥動作")
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self) -> None:
        if not is_in_active_session(self.caller):
            self.caller.msg("目前沒有進行中的戰鬥。")
            return
        try:
            view = build_combat_view(self.caller)
        except CombatViewError:
            self.caller.msg("目前無法顯示戰鬥動作。")
            return
        if view.recovery:
            self.caller.msg("戰鬥紀錄異常，無法列出動作。可使用「投降」結束戰鬥。")
            return
        lines = ["可用技能與目標代號："]
        for category in group_skill_views(view.skills):
            lines.append(f"◆ {category.label}")
            for sub_group in category.groups:
                if sub_group.label is not None:
                    lines.append(f"  {sub_group.label}")
                for skill in sub_group.skills:
                    target_tokens = [
                        p.token
                        for p in view.participants
                        if p.identity in skill.valid_target_ids
                    ]
                    if target_tokens:
                        targets = "可指定：" + "、".join(target_tokens)
                    elif skill.target_spec == "none":
                        targets = "無需目標"
                    elif skill.target_spec == "self":
                        targets = "指定自己"
                    else:
                        targets = "目前無有效目標"
                    status = "可用" if skill.enabled else skill.reason_message or "無法使用"
                    lines.append(f"  {skill.key}（{skill.label}）：{status}｜{targets}")
        lines.append("目標代號：")
        lines.append(
            "  " + "、".join(f"{p.token}＝{p.display_name}" for p in view.participants)
        )
        lines.append(
            "輸入 cast <技能>=<代號>、cast <技能>=<代號1,代號2>，"
            "或 cast <技能>=all-enemies／all-allies／all。"
        )
        self.caller.msg("\n".join(lines))


class CmdGuildExam(Command):
    """Ask the guild counter to arrange your next promotion examination.

    With the qualified examiner present this starts the simulated-battle
    examination; with the examiner away the counter answers the examiner's
    next planned attendance at the guild. Nothing is reserved either way.
    """

    key = "guild exam"
    aliases = ("guild 考核", "公會考核")
    locks = "cmd:all()"
    help_category = "Guild"

    def func(self) -> None:
        target_rank = self.args.strip().partition(" ")[0] or next_exam_rank(self.caller)
        if target_rank is None:
            self.caller.msg(rejection_message("top_rank"))
            return
        try:
            outcome = request_guild_exam(self.caller, target_rank, requested_by="command")
        except GuildExamError as error:
            self.caller.msg(rejection_message(error))
            return
        if outcome.kind == OUTCOME_SCHEDULE:
            self.caller.msg(exam_schedule_message(
                outcome.host_name, outcome.target_rank,
                outcome.interval.start_tick, outcome.interval.end_tick,
            ))
            return
        self.caller.msg(
            exam_started_message(outcome.target_rank)
            + "請選擇你的行動（cast <技能>[=<目標>]）。"
        )
