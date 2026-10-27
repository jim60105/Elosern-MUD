"""Player-facing ``talk`` command for deterministic NPC dialogue (D5/D4).

On a ``guild_staff`` dialogue host the keyword ``回報`` is an action keyword:
``talk <npc> 回報`` lists reportable quests (read-only), while
``talk <npc> 回報 <quest_id>`` turns that quest in through the deterministic
``dialogue_turn_in`` service. Every other keyword resolves exactly as before.

Authored scene topics are emitted complete and in order. A non-paged text
client has no per-line pager, so a COMPLETE successful emission counts as
reading: each emitted node is acknowledged through the same
``complete_dialogue_delivery`` service the browser uses, predecessor first, and
a failed/partial emission stops the chain without marking that node or any
dependent node. A public (``pure_chain``) successor is only selectable after
its predecessor's reading is saved; naming it earlier answers with the fixed
refusal line and writes nothing.
"""

import uuid
from typing import Any

from commands.command import Command

from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from world.rules.affinity import AFFINITY_DAILY_CAP_HINT
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    DialogueCompletionError,
    chain_deliveries,
    complete_dialogue_delivery,
    dialogue_key_for,
    escape_evennia_greeting,
    is_dialogue_host,
    misunderstood_line_for,
    open_or_refresh_dialogue,
    live_dialogue_session,
    select_authored_topic,
    resolve_greeting,
)
from world.rules.dialogue_context import DialogueContextError, resolve_dialogue_context
from world.rules.dialogue_sources import resolve_dialogue_source
from world.lore.scenes import Speech
from world.observability import log_warn
from world.rules.guild import (
    GuildDataError,
    GuildServiceError,
    RewardClaimError,
    dialogue_turn_in,
    reportable_quest_summary,
)
from world.rules.npc_schedules import interaction_reason

_MISSING_TARGET = "你想跟誰說話？請指定一個目標（talk <npc>）。"
_AMBIGUOUS_TARGET = "這裡有好幾個目標，請說得更明確一些。"
_NOT_NPC = "那不是你可以交談的對象。"
_NO_RESPONSE = "對方沒有理會你。"
_USAGE = "用法：talk <npc> 或 talk <npc> <keyword>"
_PURE_CHAIN_UNREAD = "對方搖了搖頭：「前面的話還沒說完呢。」"


def _emit_delivery(caller, npc: NPC, delivery) -> bool:
    """Emit one whole attributed scene in order, reporting emission success.

    A text client has no pager, so a fully emitted scene counts as read — but
    only a COMPLETE emission does. Any transport failure returns ``False`` and
    the caller must stop the chain without marking reading for this node or any
    dependent node.
    """
    try:
        for line in delivery.lines:
            if isinstance(line, Speech):
                if line.speaker == "actor":
                    caller.msg(f"你說：{line.text}")
                else:
                    caller.msg(f"{npc.key}說：{line.text}")
            else:
                caller.msg(line.text)
    except Exception as error:
        # The player never saw the whole scene, so it is not reading progress:
        # stop here and leave both this node and its dependents unmarked.
        log_warn(
            "talk_emission_failed",
            context={
                "char": str(getattr(caller, "pk", "?")),
                "npc": str(getattr(npc, "pk", "?")),
                "topic": str(getattr(delivery, "topic_id", None) or "?"),
            },
            exc=error,
        )
        return False
    return True


def _complete_delivery(caller, delivery) -> bool:
    """Record one successfully emitted formal delivery as read.

    Returns ``False`` when the server refused the acknowledgement (for example
    a superseded receipt) so the caller stops emitting dependent chain nodes
    that could no longer be marked either.
    """
    if delivery.kind != "formal" or not delivery.topic_id:
        return True
    try:
        complete_dialogue_delivery(
            caller,
            delivery_id=delivery.delivery_id,
            context_id=delivery.context_id,
            topic_id=delivery.topic_id,
            scene_revision=delivery.scene_revision,
        )
    except DialogueCompletionError:  # observability: ignore R2: the completion service already emitted dialogue_completion_rejected with identifiers
        return False
    return True


def _resolve_npc(
    caller,
    raw_target: str,
    *,
    missing: str = _MISSING_TARGET,
    ambiguous: str = _AMBIGUOUS_TARGET,
    not_npc: str = _NOT_NPC,
    candidates: Any = None,
) -> NPC | None | str:
    """Resolve a talk target to an NPC, or a reason string on failure.

    Returns the NPC on success; ``missing``, ``ambiguous``, or ``not_npc`` on
    a resolution failure. The message overrides let sibling commands
    (``invite``/``leave``) reuse the exact resolution rules with their own
    target wording; the defaults keep ``talk``'s behavior unchanged.
    ``candidates`` narrows the searched room objects (the visible-discovery
    surfaces pass the room's visibility-filtered contents).
    """
    if not raw_target:
        return missing
    if candidates is None:
        location = caller.location
        if location is None:
            return not_npc
        candidates = location.contents
    matches = [
        obj
        for obj in candidates
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


def resolve_visible_npc(
    caller,
    raw_target: str,
    *,
    missing: str,
    ambiguous: str,
    not_npc: str,
) -> NPC | None | str:
    """Resolve one visible room NPC by name/alias or exact ``#<id>``.

    Names and aliases match only the room's visibility-filtered contents, so a
    hidden occupant is neither named nor counted as an ambiguity. The exact
    ``#<id>`` form reuses the shared exploration visibility rule; nothing here
    authorizes a later operation, which each caller revalidates.
    """
    from world.rules.service_targets import visible_room_entity

    target = (raw_target or "").strip()
    if not target:
        return missing
    if target.startswith("#"):
        digits = target[1:]
        if not digits.isascii() or not digits.isdigit():
            return not_npc
        return visible_room_entity(caller, int(digits)) or not_npc
    location = getattr(caller, "location", None)
    if location is None:
        return not_npc
    visible = location.filter_visible(list(location.contents), caller)
    return _resolve_npc(
        caller,
        target,
        missing=missing,
        ambiguous=ambiguous,
        not_npc=not_npc,
        candidates=visible,
    )


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

        # A possessed companion speaks through its own body but owns nothing:
        # every authored path below routes relations and affinity to the
        # commander. A forged or stale mirror rejects before any line, session
        # or affinity write, exactly like the web dispatcher.
        from world.rules.possession import (
            POSSESSED_REFUSAL_MESSAGES,
            REASON_POSSESSED_TALK,
            is_possessed_actor,
        )

        possessed = is_possessed_actor(self.caller)
        if possessed:
            try:
                resolve_dialogue_context(self.caller, npc)
            except DialogueContextError:  # observability: ignore R2: the fixed player-facing refusal IS the command answer
                self.caller.msg(POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK])
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
                if possessed:
                    # Guild turn-in keeps its own player-only authority; a
                    # possessed body never substitutes for the commander.
                    self.caller.msg(POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK])
                    return
                self._turn_in_quest(npc, quest_id)
                return
            if (
                action_keyword == GUILD_STAFF_TURNIN_KEYWORD
                and dialogue_key_for(npc) == GUILD_STAFF_DIALOGUE_KEY
                and getattr(npc, "components", None) is not None
                and npc.components.has(GuildStaff.name)
            ):
                try:
                    summary = reportable_quest_summary(self.caller, npc)
                except (RewardClaimError, GuildDataError) as error:  # observability: ignore R2: the bounded refusal line IS the command answer
                    self.caller.msg(f"無法回報任務：{error}")
                    return
                if summary is not None:
                    self.caller.msg(f"{npc.key}說：{summary}")
                    return
            diag_key = dialogue_key_for(npc)
            if diag_key is None:
                self.caller.msg(_NO_RESPONSE)
                return

            # Authored and generated scene dialogue share this selection path.
            try:
                context = resolve_dialogue_context(self.caller, npc)
            except DialogueContextError:  # observability: ignore R2: the fixed player-facing refusal IS the command answer
                self.caller.msg(POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK])
                return
            source = resolve_dialogue_source(context)
            if source is None:
                self.caller.msg(_NO_RESPONSE)
                return

            # The text surface lists topics through the same disclosure
            # projection as the panel: hidden and locked rows are decided
            # here, never from the raw declaration.
            from world.rules.dialogue_availability import project_topics

            rows = project_topics(context, context_id=context.context_id)
            matched_row = next(
                (
                    row
                    for row in rows
                    if row.keyword == keyword or row.topic_id == keyword
                ),
                None,
            )
            if matched_row is None:
                # A public successor stays unlisted until its predecessor's
                # reading is saved. Naming it explicitly is refused without a
                # selection, a receipt or any reading write.
                pending_successor = next(
                    (
                        topic
                        for topic in source.dialogue.topics
                        if (topic.keyword == keyword or topic.topic_id == keyword)
                        and getattr(topic, "disclosure", "qualified") == "pure_chain"
                    ),
                    None,
                )
                if pending_successor is not None:
                    self.caller.msg(_PURE_CHAIN_UNREAD)
                    return
                # Unknown or hidden keyword: no session write, no state change,
                # and no formal prose through the legacy response view.
                if possessed:
                    self.caller.msg(_NO_RESPONSE)
                    return
                self.caller.msg(f"{npc.key}說：{misunderstood_line_for(npc)}")
                return

            session = live_dialogue_session(self.caller)
            expected_context_id = (
                session.context_id
                if (session is not None and session.npc_id == int(getattr(npc, "pk", 0)))
                else None
            )
            selection_id = uuid.uuid4().hex[:16]
            try:
                delivery = select_authored_topic(
                    self.caller,
                    npc,
                    matched_row.topic_id,
                    selection_id=selection_id,
                    expected_context_id=expected_context_id,
                )
            except Exception:  # observability: ignore R2: the rules boundary reported the rejection; the no-response line IS the answer
                self.caller.msg(_NO_RESPONSE)
                return

            # The text interface emits the whole attributed scene; a complete
            # emission counts as reading. Each successfully emitted node is
            # marked through the same completion service the browser uses, in
            # predecessor order, and emission stops at the first failure.
            emitted = _emit_delivery(self.caller, npc, delivery)
            if not emitted:
                return
            completed = _complete_delivery(self.caller, delivery)
            if not completed:
                return
            session = live_dialogue_session(self.caller)
            if session is not None:
                for node in chain_deliveries(session, npc, actor=self.caller):
                    if not _emit_delivery(self.caller, npc, node.delivery):
                        return
                    if not _complete_delivery(self.caller, node.delivery):
                        return
            if delivery.affinity_budget_capped:
                # The authored selection attempted the same +1 talk affinity
                # the scripted writer grants; a budget-blocked gain still owes
                # the fixed non-numeric hint (affinity-system).
                self.caller.msg(AFFINITY_DAILY_CAP_HINT)
            return

        if is_dialogue_host(npc):
            greeting = resolve_greeting(npc)
            if greeting is not None:
                speech = escape_evennia_greeting(greeting.text) if greeting.is_override else greeting.text
                self.caller.msg(f"{npc.key}說：{speech}\n{_USAGE}")
                return
            self.caller.msg(_NO_RESPONSE)
            return

        greeting = resolve_greeting(npc)
        if greeting is not None:
            speech = escape_evennia_greeting(greeting.text) if greeting.is_override else greeting.text
            self.caller.msg(f"{npc.key}說：{speech}")
            return

        self.caller.msg(_NO_RESPONSE)

    def _turn_in_quest(self, npc: NPC, quest_id: str) -> None:
        """Turn in one quest through the local guild-staff dialogue host."""
        try:
            result = dialogue_turn_in(self.caller, npc, quest_id)
        except GuildServiceError:  # observability: ignore R2: the bounded refusal line IS the command answer
            self.caller.msg("這裡沒有公會服務人員。")
            return
        except (RewardClaimError, GuildDataError) as error:  # observability: ignore R2: the bounded refusal line IS the command answer
            self.caller.msg(f"無法回報任務：{error}")
            return
        self.caller.msg(
            f"你回報了任務 {result['quest_id']}，獲得 {result['copper']} 銅、"
            f"功績 {result['merit']} 與道具 {result['items']}。"
        )
        for line in result.get("title_notifications", ()):
            self.caller.msg(line)
