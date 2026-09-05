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
_DISGUISE_SECRET_KEYS = ("atk_phys", "agility", "defense", "magic_power", "hp")

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

    ``npc_title`` carries the single-line plain-text title (design
    2026-09-03-npc-identity-titles §3): authored once by a creation path
    (import loader, blueprint materialization, registry-backed host or
    examiner), each of which validates through
    ``world.rules.npc_identity.validate_npc_title`` before assigning, and
    immutable afterwards. There is deliberately no title-specific runtime
    write surface (no setter, no helper, no command, no dialogue path);
    Evennia's generic ``.db`` access is framework infrastructure outside
    that guarantee, so malformed stored state can only come from it and the
    composer degrades it to the plain name. ``autocreate=False`` keeps a
    read of an absent title from persisting a row (Evennia materializes an
    autocreated property on first read), preserving the composer's
    pure-read contract.
    """

    dialogue_memory: Any | None = AttributeProperty(default=None)
    schedule: Any | None = AttributeProperty(default=None)
    npc_title: str = AttributeProperty(default="", autocreate=False)

    def at_object_delete(self) -> bool:
        """Free every party binding this NPC holds before the object is removed.

        Runs the party module's purge API (party-core D-6) so instance
        reclamation, scene teardown, and ordinary deletes never leave a stale
        dbid consuming a player's companion slot. Returns ``True`` so the
        delete proceeds (Evennia aborts when this hook is falsy). After the
        purge commits, the owning player's connected webclient sessions get an
        epoch-guarded ``party`` panel push (webclient-align-04) so a dismissed
        companion never lingers in committed presentation until the next
        unrelated sync; the fan-out is deferred through
        ``transaction.on_commit`` (the established side-effect seam) so a
        rolled-back deletion never burns a presentation revision or shows a
        removal that was undone, and never fails the delete.
        """
        from django.db import transaction

        from world.rules.party import bound_owner_of, purge_npc_memberships

        owner = bound_owner_of(self)
        purge_npc_memberships(self)
        if owner is not None:
            from web.webclient.presentation.party_push import push_party_update

            transaction.on_commit(lambda: push_party_update(owner))
        departure_room = self.location
        if departure_room is not None:
            # Same deferral as the post-move seam: the deletion commits with
            # the surrounding transaction, and a rolled-back deletion must not
            # have burned anyone's session. The dbid is captured now — the
            # object's pk is gone by the time the callback fires.
            departed_id = int(self.pk)
            transaction.on_commit(
                lambda: self._clear_dialogue_sessions_naming_me(
                    departure_room, npc_id=departed_id
                )
            )
        return True

    def at_post_move(self, source_location, **kwargs):
        """Retire dialogue sessions held by players the NPC just left behind.

        Any move counts as departing the room for the dialogue-session seam
        (webclient-align-07): schedule-driven moves, dismissals that walk the
        NPC away, and manual ``move_to`` all run through Evennia's post-move
        hook, so every leave-room path clears without each caller wiring it.
        Only sessions naming THIS NPC clear — another host's session in the
        same room is untouched. The fan-out rides ``transaction.on_commit``
        (the established side-effect seam, mirroring the party push): a
        companion's follow-move runs INSIDE the player's movement-settlement
        transaction, whose rollback compensation cannot restore the attribute
        cache — a later failed step would otherwise clear a bystander's live
        session for a departure that never committed. Outside any transaction
        the callback runs immediately.
        """
        super().at_post_move(source_location, **kwargs)
        from typeclasses.characters import _schedule_action_options_after_move

        _schedule_action_options_after_move(self)
        if source_location is None:
            return
        from django.db import transaction

        room = source_location
        transaction.on_commit(lambda: self._clear_dialogue_sessions_naming_me(room))

    def _clear_dialogue_sessions_naming_me(self, room, npc_id: int | None = None) -> None:
        """Clear every character session in ``room`` that names this NPC.

        The scan is the cleanup seam; the deterministic-core helper applies the
        conditional clear (no-op unless the stored session names this object).
        A missing room degrades to a no-op. ``npc_id`` overrides the host
        identity for post-deletion callbacks, whose object has lost its pk.
        Every session the conditional clear actually retired fans the
        ``dialogue`` panel out to that character's live watchers
        (webclient-align-10): this callback runs with no session context, and
        without the push a connected explorer keeps the departed host's
        available panel and dialogue mode until an unrelated snapshot. The
        push is fire-and-forget (party_push contract), so it can never raise
        back into the on-commit chain.
        """
        if room is None:
            return
        from typeclasses.characters import PlayerCharacter
        from world.rules.dialogue import clear_dialogue_session
        from web.webclient.presentation.dialogue_push import push_dialogue_update

        host = self.pk if npc_id is None else npc_id
        for obj in room.contents:
            if isinstance(obj, PlayerCharacter):
                if clear_dialogue_session(obj, npc=host):
                    push_dialogue_update(obj)

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

    def get_display_name(self, looker=None, *, full_identity=False, **kwargs) -> str:
        """Render the plain name, or 「姓名　稱號」 when the caller opts in.

        ``full_identity`` is an explicit, per-surface decision (design D3):
        only the room character listing and the look header pass it. With the
        flag false this returns the inherited rendering byte-identically —
        echoes, combat text, and every other caller never see a title.
        """
        if not full_identity:
            return super().get_display_name(looker, **kwargs)
        from world.rules.npc_identity import npc_display_name

        return npc_display_name(self)

    def return_appearance(self, looker, **kwargs) -> str:
        """Look header carries the full identity by default (design D4).

        Evennia fills the appearance template's ``{name}`` slot from
        ``self.get_display_name(looker, **kwargs)``, so this is the only
        injection point that leaves the template itself untouched.
        ``setdefault`` keeps the caller in charge: an explicit
        ``full_identity=False`` renders the plain header. The text 看 command,
        the ``at_look`` seam, and the webclient ``explore.look`` action share
        this framework, so all three headers stay identical (the
        localized-appearance contract).
        """
        kwargs.setdefault("full_identity", True)
        return super().return_appearance(looker, **kwargs)


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
        from world.rules.npc_identity import npc_title_value

        return {
            "name": self.key or "",
            "desc": self.db.desc or "",
            "location": self.location.key if self.location else "",
            # Read-only seam (design D7): the renderer does not consume
            # ``title`` until a later prompt change adds a {title} slot, so
            # every rendered prompt stays byte-identical while authored
            # titles exist.
            "title": npc_title_value(self),
        }

    def _player_context(self, character: Any, *, identity_detail: bool = False) -> dict[str, Any]:
        """Build the plain-data player identity plus what the NPC perceives.

        The composed full title (title-system D6) rides as the named
        ``epithet`` section whenever a slot is occupied; an empty title
        omits the section entirely (never a placeholder). ``identity_detail``
        additionally attaches up to five banked epithets with their basis
        quotes for exchanges where the NPC is being told who the player is.
        Malformed title state degrades to no section rather than breaking
        the talk.
        """
        from world.rules.titles import safe_full_title, safe_title_context_entries

        context: dict[str, Any] = {
            "name": character.key or "",
            "disguised_stats": dict(character.db.disguised_stats or {}),
        }
        full_title = safe_full_title(character)
        if full_title:
            context["epithet"] = full_title
        if identity_detail:
            entries = safe_title_context_entries(character)
            if entries:
                context["identity_entries"] = list(entries)
        return context

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

        The NPC block flattens the full depth field set so the character sees
        its own hidden identity; the player block is flattened from
        ``PersonaStore.public_view()`` over exactly the public depth fields,
        so the player's hidden identity layer, prose fields, and background
        are excluded by construction (persona-depth-dialogue-injection D2/D3).
        Both use the policy constants owned by ``world.ai.npc_dialogue`` and
        are already bounded by the handler's contract; ``None`` when the
        record is absent or content-free. This never creates, persists, or
        mutates a persona record on either entity.
        """
        from world.ai.npc_dialogue import NPC_PERSONA_FIELDS, PLAYER_PERSONA_FIELDS

        return (
            self.persona.flatten(NPC_PERSONA_FIELDS),
            character.persona.public_view().flatten(PLAYER_PERSONA_FIELDS),
        )

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
    def run_npc_exchange(
        self, speech: str, character: Any, client: Any, *, reactor=None, identity_detail: bool = False
    ):
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
            identity_detail: When ``True`` the prompt also carries up to five
                banked epithets with their basis quotes; the composed full
                title (``epithet``) is always included when a slot is occupied.

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
                player_context=self._player_context(character, identity_detail=identity_detail),
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
    def at_talked_to(self, speech: str, character: Any, client: Any, *, reactor=None, settled_line=None):
        """Handle a player addressing this NPC through the guarded dialogue seam.

        Before any prompt construction or transport work, the seam consults
        the schedule gate (``world.rules.npc_schedules.interaction_reason``);
        a blocked NPC presents the stable rejection line and runs nothing.
        The prompt carries the NPC's own affinity context for the speaker
        (read-only; a recordless player gets no block), the guarded pipeline
        resolves the reply, the degraded outcome maps to the authored greeting
        or silence, and a verified intent is applied deterministically. This
        is a thin composition of :meth:`run_npc_exchange` plus presentation
        and intent application. Being addressed face to face is the identity
        detail case: the NPC is told who the speaker is, so the banked
        epithets ride along.

        Args:
            speech: The player's line.
            character: The speaking player character.
            client: The injected client protocol; an explicit ``None`` errbacks
                with ``NPCDialogueClientRequiredError`` before any prompt
                construction or transport work.
            reactor: Optional Twisted reactor for the thinking timer; tests
                inject ``twisted.internet.task.Clock`` for determinism and the
                global reactor is used when omitted.
            settled_line: Optional observer called with the line that was
                actually presented (a reply's speech, or the authored degrade
                greeting) once the completion gate still passes. Used by the
                webclient-align-07 dialogue-session seam to record the
                exchange through the deterministic-core writer. A mid-flight
                stale settlement and a silent degrade invoke it never.

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

        if getattr(getattr(self, "db", None), "possessed_by", None) is not None:
            character.msg("他現在無法回應你。")
            return

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

        result = yield self.run_npc_exchange(
            speech, character, client, reactor=reactor, identity_detail=True
        )
        if result.degraded:
            from world.rules.dialogue import greeting_for

            greeting = greeting_for(self)
            if greeting is not None:
                character.msg(f"{self.key}說：{greeting}")
                # The authored degrade line is still a presented exchange: the
                # session observer records it, but only while the completion
                # gate still passes (the pair is together and talk-allowed).
                if settled_line is not None and intent_context_ok(self, character):
                    settled_line(greeting)
            return

        character.msg(f"{self.key}說：{result.reply.speech}")
        # Record the exchange iff it settled while the pair is still together
        # and talk-allowed — the same gate the intent applier uses, so a
        # mid-flight-stale settlement records nothing (webclient-align-07).
        if settled_line is not None and intent_context_ok(self, character):
            settled_line(result.reply.speech)
        outcome = apply_npc_intent(
            self, character, result.reply.intent, context_ok=intent_context_ok
        )
        if is_stale_context(outcome):
            # The exchange settled after the pair separated or the NPC left
            # the talkable state (completion gate, audit F22): keep the
            # speech, skip the intent, and tell the player why.
            character.msg(STALE_CONTEXT_NOTE)
        return outcome
