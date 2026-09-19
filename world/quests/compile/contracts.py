"""Closed compile-boundary contracts and the spawn-requirement registry.

This submodule owns the exception, the frozen value types, and the
process-local ``SCENE_REQUIREMENT_REGISTRY`` that the rest of the
``world.quests.compile`` package shares: the translation helpers
(:mod:`world.quests.compile.compiler`), the durable payload codec
(:mod:`world.quests.compile.payload`), and the registration publishers
(:mod:`world.quests.compile.registration`). The registry lives with the
exception and values because the package -- the compile boundary -- is the
only sanctioned writer.
"""

from dataclasses import dataclass
import re

from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestType,
    RoomLocator,
)
from world.rules.guild_offers import QuestReward
from world.rules.quest_issuance import Settlement


class QuestCompileError(ValueError):
    """A validated proposal payload violates the compile contract."""


_QUEST_TYPE_BY_VALUE = {quest_type.value: quest_type for quest_type in QuestType}
_OBJECTIVE_KIND_BY_VALUE = {
    "reach_location": ObjectiveKind.REACH,
    "defeat": ObjectiveKind.DEFEAT,
    "escort": ObjectiveKind.ESCORT,
    "acquire": ObjectiveKind.ACQUIRE,
}
_DESTINATION_KIND_BY_VALUE = {
    "anchor": DestinationKind.ANCHOR,
    "grid": DestinationKind.GRID,
    "instance": DestinationKind.BOUND_INSTANCE,
}


@dataclass(frozen=True)
class StageNpcCharacterization:
    """Optional frozen characterization of one spawned occupant.

    Carries the validated per-occupant characterization fields in deterministic
    order (design D5): the required authored ``display_name``/``title``, paired
    ``age``/``apparent_age``, the named portrait ``stable_key``, and the
    optional authored persona/background flavor block. The structural layer
    keeps ``str | None`` (npc-title-authored-identities D5): the shared helper
    enforces requiredness, so a ``None`` identity here means only that a
    pre-change stored payload predates the field.
    """

    display_name: str | None = None
    title: str | None = None
    age: int | None = None
    apparent_age: int | None = None
    portrait_stable_key: str | None = None
    background: str | None = None
    persona: tuple[tuple[str, str], ...] = ()
    combat_traits: tuple[str, ...] = ()


@dataclass(frozen=True)
class StageSpawnRequirement:
    """One stage's preserved spawn requirements for change 21's SceneBuilder.

    Plain validated data carrying the objective kind, the destination locator,
    the scene requirement (archetype, anchor hint, sentence), and the NPC role
    requirements, so the SceneBuilder can consume them without importing the
    generative package. ``characterizations`` is aligned by position with
    ``npc_reqs``: each entry holds the optional validated characterization of
    that occupant, or ``None`` when the blueprint declared none (existing
    consumers unpack ``npc_reqs`` unchanged).
    """

    index: int
    objective_kind: ObjectiveKind
    location: RoomLocator | None
    archetype: str | None
    anchor_near: str | None
    scene_sentence: str | None
    npc_reqs: tuple[tuple[str, str, str | None], ...]
    characterizations: tuple[StageNpcCharacterization | None, ...] = ()

    def __post_init__(self) -> None:
        # Characterization entries are aligned by position with ``npc_reqs``;
        # reject any meaningful mismatch so a future consumer can never attach
        # a characterization to the wrong occupant. The empty ``()`` default
        # means "every occupant is field-less" and stays backward compatible.
        if self.characterizations and len(self.characterizations) != len(self.npc_reqs):
            raise ValueError(
                "characterizations must be aligned with npc_reqs "
                f"({len(self.characterizations)} != {len(self.npc_reqs)})"
            )


# Process-local spawn-requirement registry, keyed by definition key (D4). It
# lives here -- the compile boundary -- because it is the only place the
# transient ``CompiledQuest.stage_requirements`` is registered atomically with
# the definition and issuance. Like ``QUEST_DEFINITION_REGISTRY`` and
# ``GUILD_OFFER_REGISTRY``, it does not survive a server restart.
SCENE_REQUIREMENT_REGISTRY: dict[str, tuple[StageSpawnRequirement, ...]] = {}


@dataclass(frozen=True)
class IssuanceDescriptor:
    """The issuer binding one compiled quest is published under.

    ``issuer_key`` is always namespaced (``guild:<branch key>`` for a guild
    offer, ``npc:<content key>`` or ``npc:#<pk>`` for a private commission)
    and ``settlement`` is the closed settlement mode the issuance resolves
    to. Guild issuances always settle by counter; private commissions settle
    automatically (quest-issuer-model design §4.1).
    """

    issuer_key: str
    settlement: Settlement


@dataclass(frozen=True)
class CompiledQuest:
    """The closed immutable runtime translation of one validated proposal."""

    definition: QuestDefinition
    reward: QuestReward
    issuance: IssuanceDescriptor
    stage_requirements: tuple[StageSpawnRequirement, ...]


def _reject(message: str) -> None:
    raise QuestCompileError(message)


_CJK_START = "\u4e00"
_CJK_END = "\u9fff"
_TEMPLATE_PLACEHOLDER_RE = re.compile(r"\{actor\}|\{target\}|\{data\[[^\]]*\]\}")


def _has_cjk(text: str) -> bool:
    return any(_CJK_START <= ch <= _CJK_END for ch in text)
