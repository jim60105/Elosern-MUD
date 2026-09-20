"""The authored dialogue shape: the two frozen dataclasses every row carries.

The shape of authored data is authored data: these dataclasses moved out of
``world/rules/dialogue.py`` with the rows they describe so the lore package
owns its own vocabulary and never imports the rules layer. ``dialogue.py``
re-imports them, so every existing ``world.rules.dialogue`` import path keeps
working unchanged.
"""

from dataclasses import dataclass


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
