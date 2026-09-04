"""Player-facing ``talk`` command for deterministic NPC dialogue (D5/D4).

On a ``guild_staff`` dialogue host the keyword ``回報`` is an action keyword:
``talk <npc> 回報`` lists reportable quests (read-only), while
``talk <npc> 回報 <quest_id>`` turns that quest in through the deterministic
``dialogue_turn_in`` service. Every other keyword resolves exactly as before.
"""

from commands.command import Command

from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from world.rules.affinity import AFFINITY_DAILY_CAP_HINT
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    dialogue_key_for,
    greeting_for,
    is_dialogue_host,
    run_scripted_talk,
)
from world.rules.guild import (
    GuildDataError,
    GuildServiceError,
    RewardClaimError,
    dialogue_turn_in,
)
from world.rules.npc_schedules import interaction_reason

_MISSING_TARGET = "你想跟誰說話？請指定一個目標（talk <npc>）。"
_AMBIGUOUS_TARGET = "這裡有好幾個目標，請說得更明確一些。"
_NOT_NPC = "那不是你可以交談的對象。"
_NO_RESPONSE = "對方沒有理會你。"
_USAGE = "用法：talk <npc> 或 talk <npc> <keyword>"


def _resolve_npc(
    caller,
    raw_target: str,
    *,
    missing: str = _MISSING_TARGET,
    ambiguous: str = _AMBIGUOUS_TARGET,
    not_npc: str = _NOT_NPC,
) -> NPC | None | str:
    """Resolve a talk target to an NPC, or a reason string on failure.

    Returns the NPC on success; ``missing``, ``ambiguous``, or ``not_npc`` on
    a resolution failure. The message overrides let sibling commands
    (``invite``/``leave``) reuse the exact resolution rules with their own
    target wording; the defaults keep ``talk``'s behavior unchanged.
    """
    if not raw_target:
        return missing
    location = caller.location
    if location is None:
        return not_npc
    matches = [
        obj
        for obj in location.contents
        if isinstance(obj, NPC)
        and (
            raw_target.lower() in (obj.key.lower(), *(alias.lower() for alias in obj.aliases.all()))
        )
    ]
    if not matches:
        return not_npc
    if len(matches) > 1:
        return ambiguous
    return matches[0]


class CmdsTalk(Command):
    """Talk to an NPC, with an optional keyword on dialogue-capable hosts."""

    key = "talk"
    aliases = ("交談", "對話", "t")
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

        reason = interaction_reason(npc, "talk")
        if reason is not None:
            self.caller.msg(reason)
            return

        if keyword:
            kw_parts = keyword.split(maxsplit=1)
            action_keyword = kw_parts[0]
            quest_id = kw_parts[1] if len(kw_parts) > 1 else ""
            if (
                action_keyword == GUILD_STAFF_TURNIN_KEYWORD
                and dialogue_key_for(npc) == GUILD_STAFF_DIALOGUE_KEY
                and getattr(npc, "components", None) is not None
                and npc.components.has(GuildStaff.name)
                and quest_id
            ):
                self._turn_in_quest(npc, quest_id)
                return
            try:
                result = run_scripted_talk(npc, self.caller, keyword)
            except (RewardClaimError, GuildDataError) as error:
                self.caller.msg(f"無法回報任務：{error}")
                return
            if result is None:
                self.caller.msg(_NO_RESPONSE)
                return
            hint = f"\n{AFFINITY_DAILY_CAP_HINT}" if result.budget_capped else ""
            self.caller.msg(f"{npc.key}說：{result.response}{hint}")
            return

        if is_dialogue_host(npc):
            greeting = greeting_for(npc)
            if greeting is not None:
                self.caller.msg(f"{npc.key}說：{greeting}\n{_USAGE}")
                return
            self.caller.msg(_NO_RESPONSE)
            return

        self.caller.msg(_NO_RESPONSE)

    def _turn_in_quest(self, npc: NPC, quest_id: str) -> None:
        """Turn in one quest through the local guild-staff dialogue host."""
        try:
            result = dialogue_turn_in(self.caller, npc, quest_id)
        except GuildServiceError:
            self.caller.msg("這裡沒有公會服務人員。")
            return
        except (RewardClaimError, GuildDataError) as error:
            self.caller.msg(f"無法回報任務：{error}")
            return
        self.caller.msg(
            f"你回報了任務 {result['quest_id']}，獲得 {result['copper']} 銅、"
            f"功績 {result['merit']} 與道具 {result['items']}。"
        )
        for line in result.get("title_notifications", ()):
            self.caller.msg(line)
