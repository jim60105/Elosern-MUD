"""Scripted dialogue: authored tables, read-only resolution, and the talk writer.

This module owns authored scripted dialogue end to end: the immutable keyed
tables, component resolution, the keyword lookup, and the no-keyword greeting.
The lookup surface performs no state writes, preserving the read-side
discipline of the runtime; the ``guild_staff`` action keyword is the one
authored exception: keyword ``回報`` resolves the read-only reportable-quest
listing through ``world.rules.guild`` (or falls back to the authored line),
and the keyword-less lookup never writes.

The module also hosts the deterministic scripted-talk writer
(``run_scripted_talk``), the only dialogue path that writes state: a known
keyword grants +1 talk affinity with the host through the sole-writer
affinity API (``world/rules/affinity.py``) in one transaction, restoring the
relations surface on failure. It lives here because ``world/rules/`` is the
deterministic core and this is the dialogue subsystem's own writer.

The module also owns the character-held dialogue session (webclient-align-07)
as its ONLY read/write surface: ``open_or_refresh_dialogue`` /
``clear_dialogue_session`` / ``live_dialogue_session``. Persistent
``db.dialogue_session`` on the character is the single truth of WHO the
character is speaking to and the latest server-authored LINE; no presenter,
AI layer, or client payload may open, refresh, or clear it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from typeclasses.components import ScriptedDialogue

from world.observability import log_info

GUILD_STAFF_DIALOGUE_KEY = "guild_staff"
GUILD_STAFF_TURNIN_KEYWORD = "回報"

NO_UNDERSTANDING_LINE = "對方皺起眉頭：「我不太明白你的意思。」"

# The session line bound mirrors the accepted-prose bounds the dialogue
# responses already respect (``world.ai.narrator.MAX_PROSE_LENGTH`` and
# ``world.ai.npc_dialogue.MAX_SPEECH_LENGTH``, both 2000). The parity is a
# deliberate local constant: the transport boundary forbids ``world.rules``
# from importing ``world.ai``, and a session line can never exceed the bound
# its own producer authored it under.
MAX_DIALOGUE_SESSION_LINE_CODE_POINTS = 2000


@dataclass(frozen=True)
class KeywordResponse:
    """One authored response to a player keyword."""

    keyword: str
    response: str


@dataclass(frozen=True)
class DialogueDefinition:
    """One immutable dialogue table: an optional greeting plus keyword responses.

    ``greeting`` is the no-keyword topic line shown by ``talk <npc>``. ``None``
    means the host has no authored greeting and falls back to the no-response
    line for a keyword-less talk.
    """

    greeting: str | None
    responses: tuple[KeywordResponse, ...]


GUILD_STAFF_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "註冊",
        "「先在櫃檯註冊成為冒險者（guild register），你的階級會是 F，"
        "之後就可以接取任務了。」",
    ),
    KeywordResponse(
        "任務",
        "「用 guild list 查看任務板上適合你階級的委託，用 guild accept "
        "<任務名> 接取，完成後回來對我說『回報』並指定任務編號，"
        "或直接用 guild turnin <任務編號> 交回任務。」",
    ),
    KeywordResponse(
        "公會",
        "「這裡是埃洛西恩冒險者公會的阿爾托利亞分會。公會命令有 "
        "guild register、guild list、guild accept、guild log、guild show、"
        "guild turnin、guild abandon 與 guild merit。」",
    ),
    KeywordResponse(
        "工會",
        "「你是想問冒險者公會的事吧？用 guild 相關命令可以註冊、接取"
        "任務、查看進度與回報；完成任務後對我說『回報』再指定任務編號，"
        "即可交回任務。」",
    ),
    KeywordResponse(
        "回報",
        "「想交回任務，得先成為註冊冒險者（guild register）。註冊後完成"
        "委託，對我說『回報』並指定任務編號，或直接用 guild turnin "
        "<任務編號>。」",
    ),
    KeywordResponse(
        "再見",
        "「願你的冒險順遂。需要的時候，隨時回來公會。」",
    ),
)

DIALOGUE_TABLE: MappingProxyType = MappingProxyType(
    {
        GUILD_STAFF_DIALOGUE_KEY: DialogueDefinition(
            greeting=(
                "櫃檯的公會職員抬起頭：「歡迎來到冒險者公會。想成為冒險者，"
                "就用 guild register 註冊；之後用 guild list 查看任務、"
                "guild accept 接取、guild log 與 guild show 查看進度，"
                "完成後對我說『回報』並指定任務編號（或直接用 guild "
                "turnin），還有 guild abandon 與 guild merit。」"
            ),
            responses=GUILD_STAFF_RESPONSES,
        ),
    }
)


def resolve_dialogue_component(npc: Any) -> Any | None:
    """Return the dialogue component carried by ``npc``, or ``None``.

    A host carrying the scripted dialogue component is dialogue-capable.
    """
    components = getattr(npc, "components", None)
    if components is None:
        return None
    if components.has(ScriptedDialogue.name):
        return components.get(ScriptedDialogue.get_component_slot())
    return None


def is_dialogue_host(npc: Any) -> bool:
    """Whether ``npc`` carries any dialogue component."""
    return resolve_dialogue_component(npc) is not None


def dialogue_key_for(npc: Any) -> str | None:
    """Return the host's ``dialogue_key`` or ``None`` for a non-host."""
    component = resolve_dialogue_component(npc)
    if component is None:
        return None
    return getattr(component, "dialogue_key", None)


def table_response(dialogue_key: str, keyword: str) -> str:
    """Return the authored response for one keyword, or the no-understanding line."""
    definition = DIALOGUE_TABLE.get(dialogue_key)
    if definition is None:
        return NO_UNDERSTANDING_LINE
    for entry in definition.responses:
        if entry.keyword == keyword:
            return entry.response
    return NO_UNDERSTANDING_LINE


def dialogue_has_keyword(dialogue_key: str, keyword: str) -> bool:
    """Whether ``keyword`` has an authored response in the named table."""
    definition = DIALOGUE_TABLE.get(dialogue_key)
    if definition is None:
        return False
    return any(entry.keyword == keyword for entry in definition.responses)


def dialogue_response(npc: Any, actor: Any, keyword: str) -> str | None:
    """Return the authored response for ``keyword`` on ``npc``, or ``None``.

    ``None`` means the NPC is not a dialogue host (the caller shows the
    no-response line). A host with an unknown keyword yields the
    no-understanding line. The ``guild_staff`` host answers the ``回報``
    keyword with the read-only reportable-quest listing for ``actor`` (the
    registered guild member standing with that host), falling back to the
    authored line when the actor is not a member. This function never writes
    state.
    """
    key = dialogue_key_for(npc)
    if key is None:
        return None
    if key == GUILD_STAFF_DIALOGUE_KEY and keyword == GUILD_STAFF_TURNIN_KEYWORD:
        from world.rules.guild import reportable_quest_summary

        summary = reportable_quest_summary(actor, npc)
        if summary is not None:
            return summary
    return table_response(key, keyword)


def greeting_for(npc: Any) -> str | None:
    """Return the host's authored no-keyword greeting, or ``None``.

    A missing ``dialogue_key`` or a definition with ``greeting=None`` yields
    ``None`` so the caller falls back to the no-response line.
    """
    key = dialogue_key_for(npc)
    if key is None:
        return None
    definition = DIALOGUE_TABLE.get(key)
    if definition is None:
        return None
    return definition.greeting


@dataclass(frozen=True)
class ScriptedTalkResult:
    """One applied scripted talk: the response and whether the gain was capped."""

    response: str
    budget_capped: bool


def run_scripted_talk(npc: Any, character: Any, keyword: str) -> ScriptedTalkResult | None:
    """Apply one known-keyword scripted talk atomically and return the result.

    Shared by the text ``talk`` command and the webclient
    ``explore.talk_scripted`` path. A known keyword commits the +1 ``talk``
    affinity gain with the host in one transaction, restoring the relations
    surface on failure; unknown keywords and componentless hosts return their
    line without writing anything. The ``guild_staff`` ``回報`` action keyword
    is the authored exception: it resolves its read-only listing purely and
    never grants affinity (turn-in rewards follow the guild settlement
    contract).
    """
    from world.rules.affinity import AffinitySource, apply_affinity_change
    from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

    response = dialogue_response(npc, character, keyword)
    if response is None:
        return None
    dialogue_key = dialogue_key_for(npc)
    if (
        dialogue_key == GUILD_STAFF_DIALOGUE_KEY
        and keyword == GUILD_STAFF_TURNIN_KEYWORD
    ):
        from typeclasses.components import GuildStaff

        if getattr(npc, "components", None) is not None and npc.components.has(
            GuildStaff.name
        ):
            return ScriptedTalkResult(response=response, budget_capped=False)
    if dialogue_key is None or not dialogue_has_keyword(dialogue_key, keyword):
        return ScriptedTalkResult(response=response, budget_capped=False)

    relations_snapshot = attribute_snapshot(npc, "relations_data")
    try:
        from django.db import transaction

        with transaction.atomic():
            outcome = apply_affinity_change(npc, character, AffinitySource.TALK, 1)
    except Exception:
        restore_attribute_best_effort(npc, "relations_data", relations_snapshot)
        raise
    return ScriptedTalkResult(response=response, budget_capped=outcome.budget_capped)


# ---------------------------------------------------------------------------
# Dialogue session (webclient-align-07): the ONLY writers of
# ``db.dialogue_session`` on the character.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DialogueSession:
    """One live dialogue session: the host dbid, the latest line, the tick.

    ``npc_id`` is a database identity re-resolved per read — the session never
    holds a live object reference. ``updated_tick`` is the world-clock tick at
    write time, or ``None`` when no clock singleton exists yet.
    """

    npc_id: int
    line: str
    updated_tick: int | None


def _parse_dialogue_session(raw: Any) -> DialogueSession | None:
    """Parse a stored session value, or ``None`` for absent/corrupt state.

    Read-only: a malformed value degrades to "no session" and is never repaired
    or rewritten here — the next clear seam or talk retires it. Accepts exactly
    the positive-int / str / ``int | None`` field shapes (``bool`` is rejected
    as an id/tick even though it subclasses ``int``).
    """
    # Evennia's persisted attribute value is a ``_SaverDict`` (a Mapping, not a
    # dict subclass) — the parse keys off the mapping interface.
    if not isinstance(raw, Mapping):
        return None
    npc_id = raw.get("npc_id")
    line = raw.get("line")
    updated_tick = raw.get("updated_tick")
    if not isinstance(npc_id, int) or isinstance(npc_id, bool) or npc_id <= 0:
        return None
    if not isinstance(line, str):
        return None
    # A stored line beyond the write bound or carrying unpaired surrogate code
    # points is corruption (webclient-align-10): the write path truncates and
    # never emits surrogates, so such a value can only come from damaged
    # storage. Corrupt state is "not live" here, which makes the dialogue
    # panel degrade through its REGISTERED unavailable form instead of
    # failing available-form validation as an internal presenter error.
    if len(line) > MAX_DIALOGUE_SESSION_LINE_CODE_POINTS:
        return None
    if any(0xD800 <= ord(char) <= 0xDFFF for char in line):
        return None
    if updated_tick is not None and (
        not isinstance(updated_tick, int) or isinstance(updated_tick, bool)
    ):
        return None
    return DialogueSession(npc_id=npc_id, line=line, updated_tick=updated_tick)


def _session_updated_tick() -> int | None:
    """Current world-clock tick, or ``None`` when no clock singleton exists.

    Uses the read-only ``read_world_clock`` accessor — opening a dialogue never
    materializes the clock Script.
    """
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return None if clock is None else int(clock.tick)


def open_or_refresh_dialogue(character: Any, npc: Any, line: str) -> DialogueSession:
    """Record one delivered server-authored line as the character's session.

    The ONLY opener: called from the deterministic-core success paths (the
    scripted adapter/command branches and the freeform settled observer). The
    line is truncated to ``MAX_DIALOGUE_SESSION_LINE_CODE_POINTS`` at write, so
    the stored value is always within the bound no producer can exceed it.
    Refreshing replaces the value in place (one session per character).
    """
    session = DialogueSession(
        npc_id=int(npc.pk),
        line=str(line)[:MAX_DIALOGUE_SESSION_LINE_CODE_POINTS],
        updated_tick=_session_updated_tick(),
    )
    character.db.dialogue_session = {
        "npc_id": session.npc_id,
        "line": session.line,
        "updated_tick": session.updated_tick,
    }
    log_info(
        "dialogue_session_open",
        context={"char": str(getattr(character, "pk", "?")), "npc": str(session.npc_id)},
    )
    return session


def clear_dialogue_session(character: Any, npc: Any | None = None) -> bool:
    """Retire the character's session, returning whether one was cleared.

    With ``npc`` set, only a session naming that NPC is cleared (the departure
    seams never touch another host's session); ``npc=None`` is the unconditional
    clear used by movement settlement and combat engage. An absent or corrupt
    value is a no-op ``False``. ``npc`` may be a live object or a pre-captured
    positive dbid — deletion hooks run after the object's ``pk`` is gone, and
    an unresolvable host id is a no-op (it never matches a stored session).
    """
    session = _parse_dialogue_session(character.db.dialogue_session)
    if session is None:
        if npc is None and character.db.dialogue_session is not None:
            # Unconditional clear also retires a corrupt stored value.
            character.db.dialogue_session = None
            log_info(
                "dialogue_session_clear",
                context={
                    "char": str(getattr(character, "pk", "?")),
                    "npc": "corrupt",
                    "reason": "unconditional",
                },
            )
            return True
        return False
    if npc is not None:
        host_id = npc if isinstance(npc, int) else getattr(npc, "pk", None)
        if not isinstance(host_id, int) or int(host_id) != session.npc_id:
            return False
    character.db.dialogue_session = None
    log_info(
        "dialogue_session_clear",
        context={
            "char": str(getattr(character, "pk", "?")),
            "npc": str(session.npc_id),
            "reason": "named" if npc is not None else "unconditional",
        },
    )
    return True


def live_dialogue_session(character: Any) -> DialogueSession | None:
    """The character's session iff its host still resolves as present+interactable.

    A stale dbid (deleted object, departed NPC, or a host whose schedule state
    no longer allows talk) is reported as not live — the stored value is left
    in place for the next clear seam or talk to retire, mirroring the party
    module's stale-dbid filtering. ``intent_context_ok`` is the canonical
    co-location + talk-interactability gate.
    """
    from evennia.objects.objects import ObjectDB

    from typeclasses.npcs import NPC
    from world.rules.npc_intents import intent_context_ok

    session = _parse_dialogue_session(character.db.dialogue_session)
    if session is None:
        return None
    obj = ObjectDB.objects.filter(id=session.npc_id).first()
    if obj is None or not isinstance(obj, NPC):
        return None
    if not intent_context_ok(obj, character):
        return None
    return session
