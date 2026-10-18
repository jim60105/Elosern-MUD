"""Player-facing command for out-of-combat and active-session skill use."""

import re
from typing import Any

from commands.command import Command

from world.rules.action import RejectReason
from world.rules.combat import BattlefieldActionContext
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.event_log import render_plain_text
from world.rules.field_cast import cast_as_member, cast_in_field
from world.rules.party_scope import PartyScopeError, resolve_member_token
from world.rules.player_messages import (
    CONTINUE_COMBAT_MESSAGE,
    rejection_message,
    session_reason_message,
    terminal_outcome_message,
)
from world.rules.progression import scale_for_label
from world.rules.targeting import RoomActionContext
from world.rules.unlock_notices import deliver_unlocks

#: The final ``由 <成員>`` pair names the caster. The greedy prefix makes the
#: LAST eligible pair win, so a ``由`` inside an earlier target name is kept
#: as part of the ordinary argument.
_MEMBER_SUFFIX = re.compile(r"^(?P<argument>.*)\s+由\s+(?P<member>\S.*)$")


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
        """Return ``(commander, session)`` for the caller's active session.

        A possessed puppet owns no session: the party's encounter is persisted
        under the commander it operates, so the commander keys every in-session
        submission while the caller keeps receiving the messages.
        """
        from world.rules.combat_session import read_session, session_owner

        try:
            commander = session_owner(self.caller)
            return commander, read_session(commander)
        except Exception:
            return self.caller, None

    def _split_member_suffix(self, args: str) -> tuple[str, str | None]:
        """Split the final ``由 <成員>`` pair off one cast argument string.

        The suffix is reserved syntax, so the greedy prefix keeps any earlier
        ``由`` text (for example inside a target name) in the ordinary
        argument. A trailing bare ``由`` is not a suffix and falls through to
        the ordinary parse, which rejects it as an unknown skill or target.
        """
        match = _MEMBER_SUFFIX.match(args)
        if match is None:
            return args, None
        return match.group("argument"), match.group("member").strip()

    def func(self) -> None:
        argument, member_token = self._split_member_suffix(self.args)
        raw_skill, separator, target_key = argument.partition("=")
        skill_key, at, scale_token = raw_skill.strip().partition("@")
        if not skill_key:
            self.caller.msg(
                "用法：cast <skill_key>[@<scale>][=<target_key>] [由 <成員>]"
            )
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
        member = None
        if member_token is not None:
            try:
                member = resolve_member_token(self.caller, member_token)
            except PartyScopeError as error:
                self.caller.msg(error.message)
                return
        commander, session = self._active_session()
        if session is not None:
            self._cast_in_session(
                commander, session, skill_key, target_key, scale, member
            )
            return
        self._cast_out_of_combat(skill_key, target_key, scale, member)

    def _cast_in_session(
        self,
        commander: Any,
        session,
        skill_key: str,
        target_key: str,
        scale: float = 1.0,
        member: Any = None,
    ) -> None:
        """Delegate an active-session cast to combat-session orchestration.

        ``commander`` owns the session (the caller itself, or the commander a
        possessed caller operates); every submission and token parse is keyed
        on it, while all feedback goes to the caller.

        Combat time accumulates in the session and settles exactly once at the
        terminal result; this command never advances command time. The target
        value is parsed into an explicit participant list or one approved AREA
        shorthand, matching the combat-session facade contract. ``scale`` is
        the optional freeform magnitude modifier; a scale the deterministic
        gate forbids rejects before initiative with the stable message.

        ``flee`` is not a personal action inside a session (§6): the allied
        escape is the confirmed party retreat, so this route only returns the
        party-scoped confirmation prompt and selects nothing.

        A ``由 <成員>`` suffix selects for that member exactly what ``combat
        command <actor-token> skill ...`` selects for it: the same internal
        draft command through the same admission facade, replacing any earlier
        entry and resolving the round only when the final required member
        confirms. It never casts for the caller and never advances time.
        """
        from world.rules.combat_session import (
            CombatSessionError,
            parse_session_targets,
            submit_player_action,
        )

        if member is not None:
            from commands.combat import build_skill_command, submit_actor_command

            command = build_skill_command(
                self.caller,
                skill_key,
                scale,
                target_key,
                commander=commander,
            )
            if command is None:
                return
            submit_actor_command(
                self.caller, session, member, command, commander=commander
            )
            return
        if skill_key == FLEE_SKILL_KEY:
            self._request_party_flee(commander, session)
            return
        try:
            targets = parse_session_targets(
                commander,
                target_key,
                search=lambda name: self._resolve_target(name),
            )
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return
        try:
            result = submit_player_action(
                commander,
                skill_key,
                targets,
                scale=scale,
                # The caller is the caster: a possessed puppet acts for itself
                # inside its commander's encounter, exactly as the commander
                # acts for itself.
                commanded_actor=self.caller,
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

    def _request_party_flee(self, commander: Any, session) -> None:
        """Return the party-scope retreat prompt for an in-session ``flee``.

        ``commander`` owns the session; the prompt is keyed on it and rendered
        to the caller.

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
                commander,
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
        member: Any = None,
    ) -> None:
        targets = []
        if target_key.strip():
            target = self._resolve_target(target_key)
            if target is None:
                return
            targets.append(target)
        if member is not None:
            from world.rules.combat_session import CombatSessionError

            try:
                outcome = cast_as_member(
                    self.caller,
                    int(member.pk),
                    skill_key,
                    targets=targets,
                    scale=scale,
                )
            except PartyScopeError as error:
                self.caller.msg(error.message)
                return
            except CombatSessionError as error:
                # A member's monster target opens the commander's encounter
                # (the member is the caster, the commander the session owner);
                # an engagement refusal still reports its stable session
                # reason and leaves nothing behind.
                reason = error.args[0] if error.args else "malformed_session"
                self.caller.msg(session_reason_message(str(reason)))
                return
            self._render_field_outcome(outcome)
            return
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
        self._render_field_outcome(outcome)

    def _render_field_outcome(self, outcome) -> None:
        """Render one routed field cast through the shared message surfaces."""
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
            # The rendered unlock line is already among the notifications
            # above; this records the session unread marks for the same
            # committed grant without repeating the line.
            deliver_unlocks(self.caller, settlement.unlock_notices, announce=False)
        else:
            self.caller.msg(rejection_message(settlement.result.reason))
