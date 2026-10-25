"""Runtime provider for source-neutral authored and generated dialogue definitions.

Dispatches from trusted host context to an immutable ResolvedDialogueSource,
spanning static YAML-backed snapshots and future generated packages.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from world.lore.dialogue.codec import (
    GeneratedDialogueIdentity,
    StaticDialogueIdentity,
    make_generated_host_key,
    make_static_host_key,
)
from world.lore.dialogue.shape import (
    AuthoredDialogue,
    AuthoredTopic,
    MAX_TOPICS_PER_DIALOGUE,
    DialogueDefinition,
    SceneVariant,
)
from world.lore.dialogue import DIALOGUE_SNAPSHOT, canonical_dialogue_bindings
from world.lore.scenes import Scene, Speech


@dataclass(frozen=True)
class ResolvedDialogueSource:
    """An immutable resolved dialogue source: identity, host_key, definition, and effects."""

    identity: StaticDialogueIdentity | GeneratedDialogueIdentity
    host_key: str
    dialogue: AuthoredDialogue
    phase_revision: int | str | None = None
    effects: Mapping[str, Any] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.identity, (StaticDialogueIdentity, GeneratedDialogueIdentity)
        ):
            raise TypeError(
                "identity must be StaticDialogueIdentity or GeneratedDialogueIdentity"
            )
        if not isinstance(self.host_key, str) or not self.host_key:
            raise ValueError("host_key must be a nonempty string")
        if not isinstance(self.dialogue, AuthoredDialogue):
            raise TypeError("dialogue must be an AuthoredDialogue instance")


def to_authored_dialogue(
    defn: DialogueDefinition | AuthoredDialogue, dialogue_key: str = "t_synth"
) -> AuthoredDialogue:
    """Adapt a legacy DialogueDefinition to AuthoredDialogue if needed."""
    if isinstance(defn, AuthoredDialogue):
        return defn
    topics = []
    for i, resp in enumerate(defn.responses, 1):
        topic_id = f"{dialogue_key}.topic_{i:02d}"
        scene = Scene(
            scene_id=f"{dialogue_key}.topic_{i:02d}_scene",
            revision="r1",
            lines=(
                Speech(speaker="actor", text=resp.keyword),
                Speech(speaker="host", text=resp.response),
            ),
        )
        topics.append(
            AuthoredTopic(
                topic_id=topic_id,
                keyword=resp.keyword,
                label=resp.keyword,
                fallback=scene,
            )
        )
    return AuthoredDialogue(greeting=defn.greeting, topics=tuple(topics[:MAX_TOPICS_PER_DIALOGUE]))


def resolve_dialogue_source(context: Any) -> ResolvedDialogueSource | None:
    """Resolve the dialogue source for a DialogueContext.

    Dispatches from trusted context.source_identity and host binding.
    """
    if context is None or getattr(context, "source_identity", None) is None:
        return None

    from world.rules.dialogue import DIALOGUE_TABLE

    source_id = context.source_identity

    if isinstance(source_id, StaticDialogueIdentity):
        dialogue_key = source_id.dialogue_key
        raw_defn = DIALOGUE_TABLE.get(dialogue_key)
        if raw_defn is None:
            return None
        dialogue = to_authored_dialogue(raw_defn, dialogue_key)
        return ResolvedDialogueSource(
            identity=source_id,
            host_key=context.host_key,
            dialogue=dialogue,
            phase_revision=None,
            effects={},
        )

    if isinstance(source_id, GeneratedDialogueIdentity):
        # Prepared seam: generated-packages implements DB package cutover.
        return None

    return None


__all__ = [
    "ResolvedDialogueSource",
    "canonical_dialogue_bindings",
    "resolve_dialogue_source",
    "to_authored_dialogue",
]
