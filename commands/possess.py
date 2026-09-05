"""Player-facing possession commands: ``possess`` (附身) and ``unpossess`` (歸位).

Possession changes control, not ownership: the account temporarily drives its
own bound NPC companion while the party model, affinity records, and quest
credit survive untouched.

The puppet-transfer and cmdset-mount transitions are documented seams in
``world/rules/possession.py`` and land with ``companion-possession-transition``.
"""

from commands.command import Command
from commands.talk import _resolve_npc
from world.rules.party import is_companion
from world.rules.possession import (
    POSSESSION_REJECTION_MESSAGES,
    REASON_NOT_BOUND,
    UNPOSSESS_RELEASED_MESSAGE,
    PossessionGateError,
    PossessionWriteError,
    current_possession,
    enter_possession,
    release_possession,
)

_MISSING_TARGET = "你想附身誰？請指定一個同伴（possess <npc>）。"
_AMBIGUOUS_TARGET = "這裡有好幾個目標，請說得更明確一些。"
_NOT_NPC = "那不是你的同伴。"


class CmdPossess(Command):
    """Possess a bound companion in the same room."""

    key = "possess"
    aliases = ("附身",)
    help_category = "General"

    def func(self) -> None:
        parts = self.args.strip().split(maxsplit=1)
        raw_target = parts[0] if parts else ""
        resolved = _resolve_npc(
            self.caller,
            raw_target,
            missing=_MISSING_TARGET,
            ambiguous=_AMBIGUOUS_TARGET,
            not_npc=_NOT_NPC,
        )
        if isinstance(resolved, str):
            self.caller.msg(resolved)
            return

        npc = resolved
        if not is_companion(npc, self.caller):
            self.caller.msg(POSSESSION_REJECTION_MESSAGES[REASON_NOT_BOUND])
            return

        try:
            enter_possession(self.caller, npc)
        except PossessionGateError as error:
            msg = POSSESSION_REJECTION_MESSAGES.get(error.reason, "無法附身。")
            self.caller.msg(msg)
            return
        except PossessionWriteError:
            self.caller.msg("附身操作失敗，請稍後再試。")
            return

        self.caller.msg(f"你附身到了{npc.key}身上。")


class CmdUnpossess(Command):
    """Release current companion possession and return to your own body."""

    key = "unpossess"
    aliases = ("歸位",)
    help_category = "General"

    def func(self) -> None:
        current = current_possession(self.caller)
        if current is None:
            self.caller.msg("你目前並未附身在任何同伴身上。")
            return

        try:
            release_possession(self.caller, reason="handback")
        except PossessionWriteError:
            self.caller.msg("歸位操作失敗，請稍後再試。")
            return
        self.caller.msg(UNPOSSESS_RELEASED_MESSAGE)
