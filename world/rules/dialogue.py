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
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from typeclasses.components import ScriptedDialogue

GUILD_STAFF_DIALOGUE_KEY = "guild_staff"
GUILD_STAFF_TURNIN_KEYWORD = "回報"

NO_UNDERSTANDING_LINE = "對方皺起眉頭：「我不太明白你的意思。」"


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
