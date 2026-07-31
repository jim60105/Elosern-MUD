"""Player-facing command for out-of-combat skill use."""

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

    def func(self) -> None:
        skill_key, separator, target_key = self.args.partition("=")
        skill_key = skill_key.strip()
        if not skill_key:
            self.caller.msg("用法：cast <skill_key>[=<target_key>]")
            return
        targets = []
        if separator and target_key.strip():
            target = self.caller.search(target_key.strip())
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
