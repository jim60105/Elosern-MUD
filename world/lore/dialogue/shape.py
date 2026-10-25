"""The authored dialogue shape: the frozen dataclasses every row carries.

The shape of authored data is authored data: these dataclasses moved out of
``world/rules/dialogue.py`` with the rows they describe so the lore package
owns its own vocabulary and never imports the rules layer. ``dialogue.py``
re-imports them, so every existing ``world.rules.dialogue`` import path keeps
working unchanged.

This module defines both the legacy ``KeywordResponse`` and
``DialogueDefinition`` (retained for backward compatibility until runtime
cutover) and the new Shared contract v2 immutable authored dialogue models:
``SceneVariant``, ``AuthoredTopic``, and ``AuthoredDialogue``.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from world.lore.dialogue.conditions import Condition
from world.lore.scenes import Scene

MAX_KEYWORD_CODE_POINTS = 32
MAX_LABEL_CODE_POINTS = 32
MAX_STATIC_TOPIC_ID_CHARS = 96
MAX_VARIANTS_PER_TOPIC = 8
MAX_PREDECESSORS_PER_TOPIC = 16
MAX_TOPICS_PER_DIALOGUE = 16

VARIANT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}\Z")
STATIC_SUFFIX_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}\Z")


@dataclass(frozen=True)
class KeywordResponse:
    """One authored response to a player keyword (legacy shape)."""

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


@dataclass(frozen=True)
class SceneVariant:
    """One conditional scene variant of an authored topic."""

    variant_id: str
    priority: int
    when: Condition
    scene: Scene

    def __post_init__(self) -> None:
        if not isinstance(self.variant_id, str) or not VARIANT_ID_PATTERN.match(self.variant_id):
            raise ValueError(
                f"SceneVariant variant_id must match [a-z][a-z0-9_]{{0,31}}, got {self.variant_id!r}"
            )
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError("SceneVariant priority must be an integer")
        if not isinstance(self.scene, Scene):
            raise TypeError(f"SceneVariant scene must be a Scene instance, got {type(self.scene)!r}")


@dataclass(frozen=True)
class AuthoredTopic:
    """One immutable authored topic in a dialogue definition."""

    topic_id: str
    keyword: str
    label: str
    fallback: Scene
    variants: tuple[SceneVariant, ...] = ()
    requires: Condition | None = None
    unavailable: Literal["hidden", "locked"] = "hidden"
    refusal: Scene | None = None
    predecessors: tuple[str, ...] = ()
    disclosure: Literal["qualified", "pure_chain"] = "qualified"

    def __post_init__(self) -> None:
        if not isinstance(self.topic_id, str) or not self.topic_id:
            raise ValueError("AuthoredTopic topic_id must be a nonempty string")
        if not isinstance(self.keyword, str) or not (1 <= len(self.keyword) <= MAX_KEYWORD_CODE_POINTS):
            raise ValueError(
                f"AuthoredTopic keyword must be a string of 1..{MAX_KEYWORD_CODE_POINTS} code points"
            )
        if not isinstance(self.label, str) or not (1 <= len(self.label) <= MAX_LABEL_CODE_POINTS):
            raise ValueError(
                f"AuthoredTopic label must be a string of 1..{MAX_LABEL_CODE_POINTS} code points"
            )
        if not isinstance(self.fallback, Scene):
            raise TypeError(f"AuthoredTopic fallback must be a Scene instance, got {type(self.fallback)!r}")
        if not isinstance(self.variants, tuple):
            raise TypeError("AuthoredTopic variants must be a tuple of SceneVariant")
        if len(self.variants) > MAX_VARIANTS_PER_TOPIC:
            raise ValueError(
                f"AuthoredTopic cannot exceed {MAX_VARIANTS_PER_TOPIC} variants, got {len(self.variants)}"
            )
        variant_ids = set()
        priorities = set()
        for v in self.variants:
            if not isinstance(v, SceneVariant):
                raise TypeError(f"Variant item must be SceneVariant, got {type(v)!r}")
            if v.variant_id in variant_ids:
                raise ValueError(f"Duplicate variant_id {v.variant_id!r} in topic {self.topic_id!r}")
            variant_ids.add(v.variant_id)
            if v.priority in priorities:
                raise ValueError(f"Duplicate variant priority {v.priority} in topic {self.topic_id!r}")
            priorities.add(v.priority)

        if self.unavailable not in ("hidden", "locked"):
            raise ValueError(
                f"AuthoredTopic unavailable must be 'hidden' or 'locked', got {self.unavailable!r}"
            )
        if self.unavailable == "locked" and self.refusal is None:
            raise ValueError(
                f"AuthoredTopic {self.topic_id!r} with unavailable='locked' requires a non-null refusal scene"
            )
        if self.refusal is not None and not isinstance(self.refusal, Scene):
            raise TypeError(f"AuthoredTopic refusal must be a Scene instance or None, got {type(self.refusal)!r}")

        if not isinstance(self.predecessors, tuple):
            raise TypeError("AuthoredTopic predecessors must be a tuple of str")
        if len(self.predecessors) > MAX_PREDECESSORS_PER_TOPIC:
            raise ValueError(
                f"AuthoredTopic cannot exceed {MAX_PREDECESSORS_PER_TOPIC} predecessors, got {len(self.predecessors)}"
            )
        if len(set(self.predecessors)) != len(self.predecessors):
            raise ValueError(f"AuthoredTopic {self.topic_id!r} predecessors contains duplicates")

        if self.disclosure not in ("qualified", "pure_chain"):
            raise ValueError(
                f"AuthoredTopic disclosure must be 'qualified' or 'pure_chain', got {self.disclosure!r}"
            )
        if self.disclosure == "pure_chain":
            if not self.predecessors:
                raise ValueError(
                    f"AuthoredTopic {self.topic_id!r} with disclosure='pure_chain' requires non-empty predecessors"
                )
            if self.requires is not None:
                raise ValueError(
                    f"AuthoredTopic {self.topic_id!r} with disclosure='pure_chain' cannot declare requires"
                )


@dataclass(frozen=True)
class AuthoredDialogue:
    """An immutable dialogue definition: an optional greeting plus authored topics."""

    greeting: str | None
    topics: tuple[AuthoredTopic, ...]

    def __post_init__(self) -> None:
        if self.greeting is not None and not isinstance(self.greeting, str):
            raise TypeError("AuthoredDialogue greeting must be a str or None")
        if not isinstance(self.topics, tuple):
            raise TypeError("AuthoredDialogue topics must be a tuple of AuthoredTopic")
        if len(self.topics) > MAX_TOPICS_PER_DIALOGUE:
            raise ValueError(
                f"AuthoredDialogue cannot exceed {MAX_TOPICS_PER_DIALOGUE} topics, got {len(self.topics)}"
            )
        topic_ids = set()
        for t in self.topics:
            if not isinstance(t, AuthoredTopic):
                raise TypeError(f"Topic item must be AuthoredTopic, got {type(t)!r}")
            if t.topic_id in topic_ids:
                raise ValueError(f"Duplicate topic_id {t.topic_id!r} in AuthoredDialogue")
            topic_ids.add(t.topic_id)
