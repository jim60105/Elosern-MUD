"""Player-facing ``invite`` command: AI-judged party invitations (party-core).

Resolves a local NPC like ``talk``, preflights the deterministic gate (an
eligible free-form dialogue surface, no existing binding, party not full),
then runs a structured dialogue exchange through the guarded seam with the
NPC's affinity context. On the degraded terminal the fixed invite threshold
decides; otherwise the reply's speech is shown and its verified
``party_invite`` intent is applied through the deterministic applier. The AI
is never bound by the threshold -- only the degraded terminal consults it.
"""

from evennia import Command

from commands.talk import _resolve_npc
from typeclasses.npcs import LLMNPC
from world.rules.party import (
    ALREADY_COMPANION_MESSAGE,
    DEGRADED_ACCEPT_MESSAGE,
    DEGRADED_REJECT_MESSAGE,
    JOINED_MESSAGE,
    JOIN_REJECTION_MESSAGES,
    NOT_DIALOGUE_MESSAGE,
    PARTY_FULL_MESSAGE,
    PARTY_MAX_COMPANIONS,
    REFUSED_MESSAGE,
    PartyJoinError,
    is_companion,
    join_party,
    party_size,
)

_MISSING_TARGET = "你想邀請誰？請指定一個目標（invite <npc> [訊息]）。"
_AMBIGUOUS_TARGET = "這裡有好幾個目標，請說得更明確一些。"
_NOT_NPC = "那不是你可以邀請的對象。"
_FAILURE = "邀請失敗，請稍後再試。"


class CmdInvite(Command):
    """Invite a local NPC into your party through the guarded dialogue seam."""

    key = "invite"
    aliases = ("邀請", "組隊")
    help_category = "General"

    def func(self) -> None:
        parts = self.args.strip().split(maxsplit=1)
        raw_target = parts[0] if parts else ""
        message = parts[1].strip() if len(parts) > 1 else ""
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

        if not isinstance(npc, LLMNPC):
            self.caller.msg(NOT_DIALOGUE_MESSAGE)
            return
        if is_companion(npc, self.caller):
            self.caller.msg(ALREADY_COMPANION_MESSAGE)
            return
        if party_size(self.caller) >= PARTY_MAX_COMPANIONS:
            self.caller.msg(PARTY_FULL_MESSAGE)
            return

        from web.webclient.actions.dialogue_composition import build_dialogue_client

        client = build_dialogue_client()
        deferred = npc.run_npc_exchange(message, self.caller, client)
        deferred.addCallback(self._render_outcome, npc)
        deferred.addErrback(self._render_failure)
        return deferred

    def _render_outcome(self, result, npc: LLMNPC) -> None:
        """Render one structured exchange: the threshold or the reply+intent."""
        caller = self.caller
        if result.degraded:
            self._render_degraded(npc)
            return
        caller.msg(f"{npc.key}說：{result.reply.speech}")
        self._render_intent(npc, result.reply.intent)

    def _render_degraded(self, npc: LLMNPC) -> None:
        """Apply the fixed threshold decision on the degraded terminal only."""
        from world.rules.affinity_config import get_config

        caller = self.caller
        affinity = npc.relations.affinity_for(caller)
        if affinity < get_config().invite_threshold:
            caller.msg(f"{npc.key}說：{DEGRADED_REJECT_MESSAGE}")
            return
        try:
            join_party(npc, caller)
        except PartyJoinError as error:
            caller.msg(JOIN_REJECTION_MESSAGES.get(error.reason, REFUSED_MESSAGE))
            return
        caller.msg(f"{npc.key}說：{DEGRADED_ACCEPT_MESSAGE}")
        caller.msg(JOINED_MESSAGE)

    def _render_intent(self, npc: LLMNPC, intent) -> None:
        """Apply the verified intent and render the join/refusal feedback."""
        from world.rules.npc_intents import apply_npc_intent

        caller = self.caller
        outcome = apply_npc_intent(npc, caller, intent)
        if not (isinstance(intent, dict) and intent.get("kind") == "party_invite"):
            return
        if intent.get("accept") is True:
            if outcome.applied:
                caller.msg(JOINED_MESSAGE)
            else:
                caller.msg(
                    JOIN_REJECTION_MESSAGES.get(outcome.reason or "", REFUSED_MESSAGE)
                )
        else:
            caller.msg(REFUSED_MESSAGE)

    def _render_failure(self, failure) -> None:
        failure.trap(Exception)
        self.caller.msg(_FAILURE)
