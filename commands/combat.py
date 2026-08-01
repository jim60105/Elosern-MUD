"""Player-facing combat engagement, forfeit, and guild-examination commands."""

from evennia import Command

from typeclasses.components import GuildExaminer
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    forfeit,
    is_in_active_session,
)
from world.rules.guild_exams import (
    ExamReason,
    GuildExamError,
    start_guild_exam,
)
from world.rules.event_log import render_plain_text


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
        except CombatSessionError:
            self.caller.msg("目前沒有進行中的戰鬥。")
            return
        self.caller.msg(
            {
                "defeat": "你投降了，戰鬥以失敗告終。",
                "exam_failed": "你放棄了考核。",
            }.get(result["outcome"], "戰鬥結束。")
        )


class CmdGuildExam(Command):
    """Request the guild examination for your next rank."""

    key = "guild exam"
    aliases = ("guild 考核", "公會考核")
    locks = "cmd:all()"
    help_category = "Guild"

    def _resolve_examiner(self):
        try:
            from world.rules.guild import resolve_local_service_host

            return resolve_local_service_host(self.caller, GuildExaminer)
        except Exception:
            self.caller.msg("這裡沒有考核官。")
            return None

    def func(self) -> None:
        examiner = self._resolve_examiner()
        if examiner is None:
            return
        target_rank = self.args.strip().partition(" ")[0] or "E"
        try:
            record = start_guild_exam(
                self.caller,
                examiner,
                target_rank,
                requested_by="command",
            )
        except GuildExamError as error:
            reason = error.args[0]
            message = {
                ExamReason.UNREGISTERED: "你尚未註冊為冒險者。",
                ExamReason.WRONG_BRANCH: "考核官與你的公會不符。",
                ExamReason.NOT_NEXT_RANK: "你只能接受下一個階級的考核。",
                ExamReason.BELOW_THRESHOLD: "你的功績尚未達到考核門檻。",
                ExamReason.ACTIVE_COMBAT: "你已經在戰鬥中。",
                ExamReason.DUPLICATE_ACTIVE: "你已經有一場進行中的考核。",
                ExamReason.ALREADY_SETTLED: "你已經通過這個階級的考核。",
            }.get(reason, "無法開始考核。")
            self.caller.msg(message)
            return
        self.caller.msg(
            f"你開始了 {record.target_rank} 階的考核。請選擇你的行動（cast <技能>[=<目標>]）。"
        )