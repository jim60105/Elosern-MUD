"""Player-facing command for out-of-combat and active-session skill use."""

from typing import Any

from commands.command import Command

from world.rules.action import (
    ActionRequest,
    RejectReason,
)
from world.rules.cast_settlement import settle_out_of_combat_cast
from world.rules.combat import BattlefieldActionContext
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.event_log import render_plain_text
from world.rules.player_messages import (
    CONTINUE_COMBAT_MESSAGE,
    rejection_message,
    session_reason_message,
    terminal_outcome_message,
)
from world.rules.progression import scale_for_label
from world.rules.targeting import RoomActionContext


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
        raw_skill, separator, target_key = self.args.partition("=")
        skill_key, at, scale_token = raw_skill.strip().partition("@")
        if not skill_key:
            self.caller.msg("用法：cast <skill_key>[@<scale>][=<target_key>]")
            return
        scale = 1.0
        if at:
            scale = scale_for_label(scale_token)
            if scale is None:
                # A non-label token is a usage-level rejection with the stable
                # freeform message; nothing is cast and no clock advances.
                self.caller.msg(
                    rejection_message(RejectReason.SCALED_CAST_FORBIDDEN)
                )
                return
        session = self._active_session()
        if session is not None:
            self._cast_in_session(session, skill_key, target_key, scale)
            return
        self._cast_out_of_combat(skill_key, target_key, scale)

    def _cast_in_session(
        self,
        session,
        skill_key: str,
        target_key: str,
        scale: float = 1.0,
    ) -> None:
        """Delegate an active-session cast to combat-session orchestration.

        Combat time accumulates in the session and settles exactly once at the
        terminal result; this command never advances command time. The target
        value is parsed into an explicit participant list or one approved AREA
        shorthand, matching the combat-session facade contract. ``scale`` is
        the optional freeform magnitude modifier; a scale the deterministic
        gate forbids rejects before initiative with the stable message.
        """
        from world.rules.combat_session import (
            CombatSessionError,
            parse_session_targets,
            submit_player_action,
        )

        try:
            targets = parse_session_targets(
                self.caller,
                target_key,
                search=lambda name: self._resolve_target(name),
            )
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return
        try:
            result = submit_player_action(
                self.caller,
                skill_key,
                targets,
                scale=scale,
            )
        except CombatSessionError as error:
            reason = error.args[0]
            self.caller.msg(session_reason_message(str(reason)))
            return
        from world.rules.combat_result import settle_to_messages

        lines, message = settle_to_messages(result)
        for line in lines:
            self.caller.msg(line)
        self.caller.msg(message)

    def _cast_out_of_combat(
        self,
        skill_key: str,
        target_key: str,
        scale: float = 1.0,
    ) -> None:
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
        settlement = settle_out_of_combat_cast(
            ActionRequest(
                actor=self.caller,
                skill_key=skill_key,
                targets=targets,
                context=context,
                scale=scale,
            )
        )
        if settlement.result.outcome == "success":
            self.caller.msg(render_plain_text(settlement.result.event_log))
            for line in settlement.notifications:
                self.caller.msg(line)
        else:
            self.caller.msg(rejection_message(settlement.result.reason))
