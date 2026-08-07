"""NPC typeclasses from design section 5.2 (entity-traits) and §7.4 (npc-dialogue)."""

from typing import Any

from evennia.typeclasses.attributes import AttributeProperty
from twisted.internet import defer

from .entities import LivingEntity


class NPC(LivingEntity):
    """A non-player living entity with deferred dialogue and schedule seams."""

    dialogue_memory: Any | None = AttributeProperty(default=None)
    schedule: Any | None = AttributeProperty(default=None)


def _swallow_cancelled(failure):
    """Trap a timer cancellation so no CancelledError leaks to the speaker."""
    from twisted.internet.defer import CancelledError

    failure.trap(CancelledError)


class LLMNPC(NPC):
    """A generative-dialogue NPC (design §7.4 amendment).

    Ports the Evennia ``LLMNPC`` contrib's per-character chat memory and
    thinking-state feedback as project code rather than subclassing the contrib
    (the project ``NPC`` is ``LivingEntity``-based, which cannot merge with the
    contrib's ``DefaultCharacter`` sibling, and the generative package may not
    import the contrib). ``__applabel__`` keeps this proxy model registered
    under the installed ``evennia.typeclasses`` app so its class name cannot
    collide with the contrib's same-named Django model when
    ``world.ai.client`` is imported in the same process. The client is a
    required injected argument and is never constructed lazily here. Imports of
    the generative reply layer and the deterministic applier are deliberately
    deferred to the server-ready call path so importing this module cannot bind
    the guardrail's import-time logger or create an import cycle.
    """

    __applabel__ = "typeclasses"

    chat_memory: dict = AttributeProperty(default=dict)
    max_chat_memory_size: int = AttributeProperty(default=12)
    thinking_timeout: float = AttributeProperty(default=2.0)
    # Per-entity thinking feedback override; unset falls back to the prompt
    # library's npc.thinking key.
    thinking_messages: tuple | None = AttributeProperty(default=None)

    def _memory_key(self, character: Any) -> str:
        """Return the stable per-character memory partition key.

        Uses the persistent primary key (serialized) rather than the display
        name: two characters may share a key, but never an id, so one
        character's private conversation history cannot be read or overwritten
        by another same-named character.
        """
        return str(character.pk)

    def _append_memory(self, character: Any, speaker: Any, speech: str) -> None:
        """Append one speech line to the per-character memory window (oldest dropped)."""
        memory = dict(self.db.chat_memory or {})
        lines = list(memory.get(self._memory_key(character), []))
        lines.append(f"{speaker.key}: {speech}")
        window = max(int(self.max_chat_memory_size), 1)
        del lines[:-window]
        memory[self._memory_key(character)] = lines
        self.db.chat_memory = memory

    def _chat_lines(self, character: Any) -> list[str]:
        """Return the bounded memory window lines for one character."""
        memory = self.db.chat_memory or {}
        return list(memory.get(self._memory_key(character), []))

    def _npc_context(self) -> dict[str, str]:
        """Build the plain-data NPC identity for the prompt builder."""
        return {
            "name": self.key or "",
            "desc": self.db.desc or "",
            "location": self.location.key if self.location else "",
        }

    def _player_context(self, character: Any) -> dict[str, Any]:
        """Build the plain-data player identity plus what the NPC perceives."""
        return {
            "name": character.key or "",
            "disguised_stats": dict(character.db.disguised_stats or {}),
        }

    def _thinking_text(self) -> str:
        """Render the thinking feedback shown to the speaker.

        A per-entity ``thinking_messages`` override tuple wins when set (each
        template may use ``{name}``); otherwise the text falls back to the
        prompt library's ``npc.thinking`` key. An unavailable library key
        degrades to an empty string (no echo), never an exception.
        """
        messages = self.db.thinking_messages
        if messages:
            return str(messages[0]).format(name=self.key)
        from world.prompts.loader import PromptUnavailableError, render_prompt

        try:
            return render_prompt("npc.thinking", name=self.key)
        except PromptUnavailableError:
            return ""

    @defer.inlineCallbacks
    def at_talked_to(self, speech: str, character: Any, client: Any, *, reactor=None):
        """Handle a player addressing this NPC through the guarded dialogue seam.

        Args:
            speech: The player's line.
            character: The speaking player character.
            client: The injected client protocol; an explicit ``None`` errbacks
                with ``NPCDialogueClientRequiredError`` before any prompt
                construction or transport work.
            reactor: Optional Twisted reactor for the thinking timer; tests
                inject ``twisted.internet.task.Clock`` for determinism and the
                global reactor is used when omitted.

        Returns:
            A Deferred resolving after the reply is presented (or the degraded
            greeting/silence is rendered) and a verified intent is applied.
        """
        from twisted.internet import task as twisted_task
        from world.ai.npc_dialogue import (
            NPCDialogueClientRequiredError,
            generate_npc_reply,
        )
        from world.rules.npc_intents import apply_npc_intent

        if client is None:
            raise NPCDialogueClientRequiredError(
                "at_talked_to requires an injected client; got None"
            )

        if reactor is None:
            from twisted.internet import reactor as global_reactor

            reactor = global_reactor

        def _echo_thinking():
            character.msg(self._thinking_text())

        thinking_defer = twisted_task.deferLater(
            reactor, float(self.thinking_timeout), _echo_thinking
        )
        thinking_defer.addErrback(_swallow_cancelled)

        self._append_memory(character, character, speech)

        try:
            reply = yield generate_npc_reply(
                client,
                npc_context=self._npc_context(),
                player_context=self._player_context(character),
                memory=self._chat_lines(character),
            )
        finally:
            if thinking_defer is not None and not thinking_defer.called:
                thinking_defer.cancel()

        if reply is None:
            from world.rules.dialogue import greeting_for

            greeting = greeting_for(self)
            if greeting is not None:
                character.msg(f"{self.key}說：{greeting}")
            return

        character.msg(f"{self.key}說：{reply.speech}")
        self._append_memory(character, self, reply.speech)
        apply_npc_intent(self, character, reply.intent)
