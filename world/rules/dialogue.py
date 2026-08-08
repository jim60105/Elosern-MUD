"""Single read-only dialogue resolution service (scripted-dialogue D3).

This module is the one lookup point for authored scripted dialogue on NPCs: it
owns component resolution, the keyword lookup, and the no-keyword greeting.
It performs no state writes, preserving the single-writer invariant; the guard's
stateful keyword tracking stays in ``world.rules.onboarding``, which calls back
into these same lookups after recording the seen keyword. The ``guild_staff``
action keyword is the one authored exception: keyword ``回報`` resolves the
read-only reportable-quest listing through ``world.rules.guild`` (or falls back
to the authored line), and the keyword-less lookup never writes.
"""

from typing import Any

from typeclasses.components import OnboardingGuide, ScriptedDialogue
from world.onboarding.guide import dialogue_response as _table_response
from world.onboarding.guide_dialogue import (
    DIALOGUE_TABLE,
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
)


def resolve_dialogue_component(npc: Any) -> Any | None:
    """Return the dialogue component carried by ``npc``, or ``None``.

    A host carrying either the onboarding guide component or a scripted
    dialogue component is dialogue-capable; the onboarding host wins when both
    are present so its stateful behavior stays authoritative.
    """
    components = getattr(npc, "components", None)
    if components is None:
        return None
    if components.has(OnboardingGuide.name):
        return components.get(OnboardingGuide.get_component_slot())
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
    return _table_response(key, keyword)


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
