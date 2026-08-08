"""Player-facing ``leave`` command: dismiss a companion (party-core).

Resolves a local NPC like ``talk`` and dismisses it through the party
membership module's ``leave_party(..., reason="dismissed")``. Dismissal never
changes affinity in either direction.
"""

from evennia import Command

from commands.talk import _resolve_npc
from world.rules.party import (
    LEAVE_DISMISSED_MESSAGE,
    NOT_COMPANION_MESSAGE,
    is_companion,
    leave_party,
)

_MISSING_TARGET = "你想解散誰？請指定一個目標（leave <npc>）。"
_AMBIGUOUS_TARGET = "這裡有好幾個目標，請說得更明確一些。"
_NOT_NPC = "那不是你的同伴。"


class CmdLeave(Command):
    """Dismiss a bound companion from your party."""

    key = "leave"
    aliases = ("解散",)
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
            self.caller.msg(NOT_COMPANION_MESSAGE)
            return
        leave_party(npc, self.caller, reason="dismissed")
        self.caller.msg(LEAVE_DISMISSED_MESSAGE)
