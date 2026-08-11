"""NPC typeclasses from design section 5.2 (entity-traits) and §7.4 (npc-dialogue)."""

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any

from evennia.typeclasses.attributes import AttributeProperty
from twisted.internet import defer

from .entities import LivingEntity

# Trait keys whose true current values become no-leak secrets when the NPC
# carries an active disguise (persona-dialogue-injection D2). ``hp`` binds its
# current gauge value, never the maximum.
_DISGUISE_SECRET_KEYS = ("atk_phys", "agility", "defense", "magic_level", "hp")

# Canonical adult age baseline for procedurally spawned or synced NPCs
# (fix-npc-adult-identity D1); every character must be an adult.
NPC_ADULT_BASELINE = 18


def ensure_npc_adult_identity(npc: Any) -> None:
    """Ensure an NPC persists canonical adult age attributes (set-if-absent).

    Sets ``age`` to 18 when missing and ``apparent_age`` to 18 when missing,
    independently: an existing value is never overwritten, and a missing field
    is never filled merely because the other field is absent. No-op for NPCs
    whose identity already carries both values (import/characterization
    paths), so it can run unconditionally on every spawn/sync site.
    """
    for key in ("age", "apparent_age"):
        if npc.attributes.get(key) is None:
            npc.attributes.add(key, NPC_ADULT_BASELINE)


@dataclass(frozen=True)
class DialogueExchangeResult:
    """One structured dialogue exchange: the degraded terminal or a reply.

    ``degraded=True`` means the guarded layer resolved to its public ``None``
    marker and ``reply`` is ``None``; the caller decides the fallback behavior
    (the authored greeting or the party-invite threshold). A degraded outcome
    is never silently treated as a declined intent. ``reply`` is typed loosely
    so this module needs no module-scope generative import.
    """

    degraded: bool
    reply: Any | None


class NPC(LivingEntity):
    """A non-player living entity with dialogue and schedule seams.

    ``schedule`` (``AttributeProperty``) carries the NPC's deterministic
    schedule: ``None`` (no schedule), a validated template reference, or a
    full custom entry list -- see ``world.rules.npc_schedules`` for the
    storage contract. It is written only through ``set_npc_schedule``, which
    also records the assignment tick and the persistent ``schedule`` tag. The
    runtime-state attribute ``schedule_state`` is declared there (current
    state value or ``None``) and written only by the schedule-runtime change.
    """

    dialogue_memory: Any | None = AttributeProperty(default=None)
    schedule: Any | None = AttributeProperty(default=None)

    def at_object_delete(self) -> bool:
        """Free every party binding this NPC holds before the object is removed.

        Runs the party module's purge API (party-core D-6) so instance
        reclamation, scene teardown, and ordinary deletes never leave a stale
        dbid consuming a player's companion slot. Returns ``True`` so the
        delete proceeds (Evennia aborts when this hook is falsy).
        """
        from world.rules.party import purge_npc_memberships

        purge_npc_memberships(self)
        return True

    def get_display_desc(self, looker=None, **kwargs) -> str:
        """Append the affinity stage line to the ordinary zh-tw description.

        The stage line is rendered by the shared appearance layer (the same
        frame the text 看 command, the ``at_look`` hook, and the webclient
        explore-look action use); entities without an affinity record for the
        looker render no line and the read never persists.
        """
        desc = super().get_display_desc(looker, **kwargs)
        from world.rules.affinity import affinity_stage_line

        line = affinity_stage_line(self, looker)
        return f"{desc}\n{line}" if line else desc


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

    def _affinity_context(self, character: Any) -> dict[str, Any] | None:
        """The NPC's own affinity context for ``character``, read-only.

        Gated on ``has_record`` so a recordless player yields ``None`` (the
        prompt block is omitted). Only read APIs are used -- this never
        creates, persists, or mutates an affinity record, and a corrupted
        stored record degrades through the tolerant parser instead of
        crashing the talk.
        """
        handler = self.relations
        if not handler.has_record(character):
            return None
        return {
            "value": handler.affinity_for(character),
            "cap": handler.cap_for(character),
            "stage": handler.stage_for(character).name,
        }

    def _persona_block(self, character: Any) -> tuple[str | None, str | None]:
        """Read-only persona blocks for the NPC and the speaking player.

        Both come from ``PersonaStore.flatten()`` (already bounded by the
        handler's contract); ``None`` when the record is absent or
        content-free. This never creates, persists, or mutates a persona
        record on either entity.
        """
        return self.persona.flatten(), character.persona.flatten()

    def _no_leak_secrets(self, character: Any) -> frozenset[str]:
        """Build the per-call no-leak secret set as plain decimal strings.

        The set holds the NPC's affinity value and cap toward ``character``
        when a record exists, plus the NPC's own true trait values for
        ``_DISGUISE_SECRET_KEYS`` when the NPC carries a ``disguised_stats``
        record whose value for that key differs from the true trait value
        (``hp`` at its current gauge value, never the maximum). An NPC
        without the trait, without a disguise, or without a record
        contributes nothing; the set may be empty and the caller installs no
        validator in that case. Reads only; never mutates state.
        """
        secrets: set[str] = set()
        context = self._affinity_context(character)
        if context is not None:
            secrets.add(str(context["value"]))
            secrets.add(str(context["cap"]))
        disguised = self.db.disguised_stats or {}
        if isinstance(disguised, Mapping):
            traits = self.traits
            for key in _DISGUISE_SECRET_KEYS:
                trait = getattr(traits, key)
                if trait is None or key not in disguised:
                    continue
                try:
                    displayed = int(disguised[key])
                    true_value = int(trait.value)
                except (TypeError, ValueError):
                    continue
                if displayed != true_value:
                    secrets.add(str(true_value))
        return frozenset(secrets)

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
    def run_npc_exchange(self, speech: str, character: Any, client: Any, *, reactor=None):
        """Run one guarded dialogue exchange without applying anything.

        Performs the same steps ``at_talked_to`` used to: rejects an explicit
        ``None`` client, appends the speaker's line to the per-character chat
        memory, arms and cancels the thinking timer, and resolves the reply
        through the guarded dialogue layer -- supplying the NPC's and the
        speaking player's persona blocks and the per-call no-leak secret set
        (all read-only, mirroring the affinity context). The NPC's reply
        speech is appended to memory when one exists. Nothing is applied:
        intent application and degrade fallbacks are the caller's decision,
        which is what lets the ``invite`` adapter apply the fixed threshold
        only on the degraded terminal.

        Args:
            speech: The speaker's line.
            character: The speaking player character.
            client: The injected client protocol; an explicit ``None`` errbacks
                with ``NPCDialogueClientRequiredError`` before any prompt
                construction or transport work.
            reactor: Optional Twisted reactor for the thinking timer; tests
                inject ``twisted.internet.task.Clock`` for determinism.

        Returns:
            A Deferred resolving to a frozen :class:`DialogueExchangeResult`
            carrying ``degraded=True`` and ``reply=None`` when the guarded
            layer degraded, or ``degraded=False`` with the validated reply.
        """
        from twisted.internet import task as twisted_task
        from world.ai.npc_dialogue import (
            NPCDialogueClientRequiredError,
            generate_npc_reply,
        )

        if client is None:
            raise NPCDialogueClientRequiredError(
                "run_npc_exchange requires an injected client; got None"
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

        npc_persona, player_persona = self._persona_block(character)

        try:
            reply = yield generate_npc_reply(
                client,
                npc_context=self._npc_context(),
                player_context=self._player_context(character),
                memory=self._chat_lines(character),
                affinity_context=self._affinity_context(character),
                npc_persona=npc_persona,
                player_persona=player_persona,
                no_leak_secrets=self._no_leak_secrets(character),
            )
        finally:
            if thinking_defer is not None and not thinking_defer.called:
                thinking_defer.cancel()

        if reply is None:
            return DialogueExchangeResult(degraded=True, reply=None)
        self._append_memory(character, self, reply.speech)
        return DialogueExchangeResult(degraded=False, reply=reply)

    @defer.inlineCallbacks
    def at_talked_to(self, speech: str, character: Any, client: Any, *, reactor=None):
        """Handle a player addressing this NPC through the guarded dialogue seam.

        Before any prompt construction or transport work, the seam consults
        the schedule gate (``world.rules.npc_schedules.interaction_reason``);
        a blocked NPC presents the stable rejection line and runs nothing.
        The prompt carries the NPC's own affinity context for the speaker
        (read-only; a recordless player gets no block), the guarded pipeline
        resolves the reply, the degraded outcome maps to the authored greeting
        or silence, and a verified intent is applied deterministically. This
        is a thin composition of :meth:`run_npc_exchange` plus presentation
        and intent application.

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
            The resolution value is the applied :class:`IntentOutcome` when a
            reply was presented -- including the completion gate's stale
            marker when the exchange settled after the pair separated or the
            NPC stopped allowing talk -- and ``None`` on a blocked or degraded
            seam.
        """
        from world.ai.npc_dialogue import NPCDialogueClientRequiredError
        from world.rules.npc_intents import (
            STALE_CONTEXT_NOTE,
            apply_npc_intent,
            intent_context_ok,
            is_stale_context,
        )
        from world.rules.npc_schedules import interaction_reason

        reason = interaction_reason(self, "talk")
        if reason is not None:
            # A schedule-blocked NPC never builds a prompt, runs a pipeline,
            # appends memory, or applies an intent (npc-schedule-runtime D4/D5).
            character.msg(reason)
            return

        if client is None:
            raise NPCDialogueClientRequiredError(
                "at_talked_to requires an injected client; got None"
            )

        result = yield self.run_npc_exchange(speech, character, client, reactor=reactor)
        if result.degraded:
            from world.rules.dialogue import greeting_for

            greeting = greeting_for(self)
            if greeting is not None:
                character.msg(f"{self.key}說：{greeting}")
            return

        character.msg(f"{self.key}說：{result.reply.speech}")
        outcome = apply_npc_intent(
            self, character, result.reply.intent, context_ok=intent_context_ok
        )
        if is_stale_context(outcome):
            # The exchange settled after the pair separated or the NPC left
            # the talkable state (completion gate, audit F22): keep the
            # speech, skip the intent, and tell the player why.
            character.msg(STALE_CONTEXT_NOTE)
        return outcome
