"""Player-facing command for out-of-combat and active-session skill use."""

from typing import Any

from commands.command import Command

from world.rules.action import RejectReason
from world.rules.combat import BattlefieldActionContext
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.event_log import render_plain_text
from world.rules.field_cast import cast_in_field
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
    aliases = ("施法", "c")
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

        ``flee`` is not a personal action inside a session (§6): the allied
        escape is the confirmed party retreat, so this route only returns the
        party-scoped confirmation prompt and selects nothing.
        """
        from world.rules.combat_session import (
            CombatSessionError,
            parse_session_targets,
            submit_player_action,
        )

        if skill_key == FLEE_SKILL_KEY:
            self._request_party_flee(session)
            return
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

    def _request_party_flee(self, session) -> None:
        """Return the party-scope retreat prompt for an in-session ``flee``.

        No draft entry is selected, no round resolves and no time advances
        until the player confirms with the returned token; enemy
        disengagement keeps its own mechanism and never comes through here.
        """
        from world.rules.combat_session import (
            PARTY_EXIT_RETREAT,
            CombatSessionError,
            request_party_exit,
        )
        from world.rules.player_messages import party_exit_prompt_lines

        try:
            prompt = request_party_exit(
                self.caller,
                session.session_id,
                session.round_revision,
                PARTY_EXIT_RETREAT,
            )
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return
        for line in party_exit_prompt_lines(
            prompt["operation"],
            scope_count=len(prompt["party_scope"]),
            session_id=prompt["session_id"],
            round_number=session.rounds_elapsed + 1,
            confirmation_token=prompt["confirmation_token"],
            # The party's escape is its own confirmed operation, so the prompt
            # names the retreat entry point (party-combat-text-commands).
            confirm_command="combat retreat",
        ):
            self.caller.msg(line)

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
        # Field routing lives in ONE deterministic entry shared with the
        # WebClient ``explore.cast`` adapter (field-combat-initiation D-1/D-6,
        # skillbook-authoritative-casting D3): a living co-located hostile
        # Monster target opens combat with this skill as the opening action,
        # whatever the skill does; a damaging skill aimed at anything else
        # (or at nothing) is refused before any resource, roll, session, or
        # clock access; everything else keeps the settlement route. Only the
        # trusted context selection below stays with the command.
        active_context = self.caller.ndb.action_context
        if active_context is not None:
            context = active_context
        else:
            context = RoomActionContext(self.caller.location, {})
        if (
            skill_key == FLEE_SKILL_KEY
            and isinstance(context, BattlefieldActionContext)
        ):
            context = BattlefieldActionContext(context.battlefield)
        outcome = cast_in_field(
            self.caller,
            skill_key,
            targets=targets,
            scale=scale,
            context=context,
        )
        if outcome.route == "rejected":
            self.caller.msg(rejection_message(outcome.reason))
            return
        if outcome.route == "initiation":
            from world.rules.combat_result import settle_to_messages

            lines, message = settle_to_messages(outcome.combat_result)
            for line in lines:
                self.caller.msg(line)
            self.caller.msg(message)
            return
        settlement = outcome.settlement
        if settlement.result.outcome == "success":
            self.caller.msg(render_plain_text(settlement.result.event_log))
            for line in settlement.notifications:
                self.caller.msg(line)
        else:
            self.caller.msg(rejection_message(settlement.result.reason))
