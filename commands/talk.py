"""Player-facing ``talk`` command for deterministic NPC dialogue (D5)."""

from evennia import Command

from typeclasses.npcs import NPC
from world.rules.onboarding import (
    current_guide_prompt,
    is_guide_host,
    talk_response,
)

_MISSING_TARGET = "你想跟誰說話？請指定一個目標（talk <npc>）。"
_AMBIGUOUS_TARGET = "這裡有好幾個目標，請說得更明確一些。"
_NOT_NPC = "那不是你可以交談的對象。"
_NO_RESPONSE = "對方沒有理會你。"
_USAGE = "用法：talk <npc> 或 talk <npc> <keyword>"


def _resolve_npc(caller, raw_target: str) -> NPC | None | str:
    """Resolve a talk target to an NPC, or a reason string on failure.

    Returns the NPC on success; ``_MISSING_TARGET``, ``_AMBIGUOUS_TARGET``, or
    ``_NOT_NPC`` on a resolution failure.
    """
    if not raw_target:
        return _MISSING_TARGET
    location = caller.location
    if location is None:
        return _NOT_NPC
    matches = [
        obj
        for obj in location.contents
        if isinstance(obj, NPC)
        and (
            raw_target.lower() in (obj.key.lower(), *(alias.lower() for alias in obj.aliases.all()))
        )
    ]
    if not matches:
        return _NOT_NPC
    if len(matches) > 1:
        return _AMBIGUOUS_TARGET
    return matches[0]


class CmdsTalk(Command):
    """Talk to an NPC, with an optional keyword on dialogue-capable hosts."""

    key = "talk"
    aliases = ("交談", "對話")
    help_category = "General"

    def func(self) -> None:
        parts = self.args.strip().split(maxsplit=1)
        raw_target = parts[0] if parts else ""
        keyword = parts[1].strip() if len(parts) > 1 else ""
        resolved = _resolve_npc(self.caller, raw_target)
        if isinstance(resolved, str):
            self.caller.msg(resolved)
            return
        npc = resolved

        if keyword:
            response = talk_response(npc, self.caller, keyword)
            if response is None:
                self.caller.msg(_NO_RESPONSE)
                return
            self.caller.msg(f"{npc.key}說：{response}")
            return

        if not is_guide_host(npc):
            self.caller.msg(_NO_RESPONSE)
            return
        prompt = current_guide_prompt(self.caller)
        if prompt is None:
            response = talk_response(npc, self.caller, "再見")
            self.caller.msg(f"{npc.key}說：{response}\n{_USAGE}")
            return
        self.caller.msg(
            f"{npc.key}說：{prompt}\n（用 talk {npc.key} <keyword> 詢問：公會、冒險、危險、再見）"
        )
