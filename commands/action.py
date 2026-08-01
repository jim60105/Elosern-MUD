"""Player-facing command for out-of-combat and active-session skill use."""

from evennia import Command

from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
)
from world.rules.combat import BattlefieldActionContext
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.event_log import render_plain_text
from world.rules.targeting import RoomActionContext


REJECTION_MESSAGES = {
    reason: {
        RejectReason.UNKNOWN_SKILL: "你不會使用這項技能。",
        RejectReason.SKILL_NOT_ACTIVE: "被動技能不能主動施展。",
        RejectReason.INSUFFICIENT_RESOURCE: "你的資源不足。",
        RejectReason.TARGET_NOT_PRESENT: "目標不在這裡。",
        RejectReason.TARGET_DEAD: "目標已失去行動能力。",
        RejectReason.TARGET_OUT_OF_RANGE: "目標超出範圍。",
        RejectReason.TARGET_FACTION_FORBIDDEN: "這項技能不能指定該目標。",
        RejectReason.ACTION_FORBIDDEN: "你目前無法行動。",
    }.get(reason, "這項行動無法完成。")
    for reason in RejectReason
}


class CmdCast(Command):
    """Cast a skill through the deterministic action resolver."""

    key = "cast"
    aliases = ("施法",)
    locks = "cmd:all()"
    help_category = "General"

    def _resolve_target(self, target_key: str):
        target = self.caller.search(target_key.strip())
        return target

    def _active_session(self):
        from world.rules.combat_session import read_session

        try:
            return read_session(self.caller)
        except Exception:
            return None

    def func(self) -> None:
        skill_key, separator, target_key = self.args.partition("=")
        skill_key = skill_key.strip()
        if not skill_key:
            self.caller.msg("用法：cast <skill_key>[=<target_key>]")
            return
        session = self._active_session()
        if session is not None:
            self._cast_in_session(session, skill_key, target_key)
            return
        self._cast_out_of_combat(skill_key, target_key)

    def _cast_in_session(self, session, skill_key: str, target_key: str) -> None:
        """Delegate an active-session cast to combat-session orchestration.

        Combat time accumulates in the session and settles exactly once at the
        terminal result; this command never advances command time.
        """
        from world.rules.combat_session import (
            CombatSessionError,
            SessionReason,
            submit_player_action,
        )

        target = self._resolve_target(target_key) if target_key.strip() else None
        if target_key.strip() and target is None:
            return
        try:
            result = submit_player_action(self.caller, skill_key, target)
        except CombatSessionError as error:
            reason = error.args[0]
            if reason is SessionReason.NO_ACTIVE_SESSION:
                self.caller.msg("目前沒有進行中的戰鬥。")
            elif reason is SessionReason.INVALID_RECOVERY:
                self.caller.msg("你已經無法行動，戰鬥結束了。")
            else:
                self.caller.msg("這項行動無法完成。")
            return
        if result["outcome"] == "rejected":
            self.caller.msg(
                REJECTION_MESSAGES.get(result["reason"], "這項行動無法完成。")
            )
            return
        for event_log in result["logs"]:
            self.caller.msg(render_plain_text(event_log))
        if result["outcome"] in ("victory", "defeat", "fled", "exam_passed", "exam_failed", "cap"):
            self.caller.msg(
                {
                    "victory": "戰鬥結束，你取得了勝利。",
                    "defeat": "你被擊敗了。",
                    "fled": "你脫離了戰鬥。",
                    "exam_passed": "你通過了公會考核。",
                    "exam_failed": "你未能通過公會考核。",
                    "cap": "戰鬥超出了回合上限，回合結束。",
                }[result["outcome"]]
            )
        else:
            self.caller.msg("繼續戰鬥。")

    def _cast_out_of_combat(self, skill_key: str, target_key: str) -> None:
        targets = []
        if target_key.strip():
            target = self._resolve_target(target_key)
            if target is None:
                return
            targets.append(target)
        active_context = self.caller.ndb.action_context
        if active_context is not None:
            context = active_context
        else:
            context = RoomActionContext(
                self.caller.location,
                {
                    "disguise": dict(
                        self.caller.db.disguised_stats or {}
                    )
                }
                if skill_key == "status_disguise"
                else {},
            )
        if (
            skill_key == FLEE_SKILL_KEY
            and isinstance(context, BattlefieldActionContext)
        ):
            context = BattlefieldActionContext(context.battlefield)
        result = ActionResolver.resolve(
            ActionRequest(
                actor=self.caller,
                skill_key=skill_key,
                targets=targets,
                context=context,
            )
        )
        if result.outcome == "success":
            get_world_clock().advance(
                result.time_cost_seconds,
                AdvanceSource.COMMAND,
                [self.caller],
            )
            self.caller.msg(render_plain_text(result.event_log))
        else:
            self.caller.msg(REJECTION_MESSAGES.get(result.reason, "這項行動無法完成。"))
