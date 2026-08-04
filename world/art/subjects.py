"""Namespaced art-subject identity and deterministic adult-safe descriptions.

Art subjects are the immutable identities the deterministic art backend keys
its records and jobs on. Three namespaces exist: ``scene:<archetype>``,
``portrait:character:<stable-key>``, and ``portrait:monster:<archetype>``.
Every access path -- queue, store, worker, command, presenter -- goes through a
parsed ``ArtSubject``; no raw full-key string is ever accepted.

Named-character portrait eligibility is explicit metadata (``portrait_policy``
on the character), never inferred from display-name uniqueness, quest role,
database key shape, or LLM authorship (design D2, focused design §3.3).
"""

from dataclasses import dataclass
from enum import StrEnum
import unicodedata

from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.races import SUBRACE_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

# The approved visual style is fixed so every description is stable across
# reloads and the store's source-description hash is meaningful.
_APPROVED_STYLE = "approved visual style"


class ArtSubjectError(ValueError):
    """Raised when an art subject is malformed or unresolvable."""


class ArtSubjectKind(StrEnum):
    """The three namespaced subject kinds (serialized prefix is the value)."""

    SCENE = "scene"
    CHARACTER = "portrait:character"
    MONSTER = "portrait:monster"


@dataclass(frozen=True)
class ArtSubject:
    """One typed, un-prefixed subject identity."""

    kind: ArtSubjectKind
    key: str

    def full(self) -> str:
        """The serialized full subject key, e.g. ``scene:forest_path``."""
        return f"{self.kind.value}:{self.key}"


def _validate_subject_key(key: str) -> None:
    if not isinstance(key, str) or not key:
        raise ArtSubjectError("an art subject key must be non-empty text")
    if ":" in key:
        raise ArtSubjectError("an art subject key must not contain ':'")
    if any(
        not char.isprintable() or unicodedata.category(char).startswith("C")
        for char in key
    ):
        raise ArtSubjectError("an art subject key must not contain control characters")


def parse_subject(full_key: str) -> ArtSubject:
    """Parse a serialized full subject key into a typed ``ArtSubject``."""
    if not isinstance(full_key, str):
        raise ArtSubjectError("a full art subject key must be text")
    for kind in ArtSubjectKind:
        prefix = f"{kind.value}:"
        if full_key.startswith(prefix):
            key = full_key[len(prefix):]
            _validate_subject_key(key)
            return ArtSubject(kind, key)
    raise ArtSubjectError(f"unknown art subject prefix in {full_key!r}")


def scene_subject_for(archetype: str) -> ArtSubject:
    """Resolve and re-validate one scene subject from the immutable registry."""
    if archetype not in SCENE_ARCHETYPE_REGISTRY:
        raise ArtSubjectError(f"unknown scene archetype {archetype!r}")
    _validate_subject_key(archetype)
    return ArtSubject(ArtSubjectKind.SCENE, archetype)


def monster_subject_for(archetype: str) -> ArtSubject:
    """Resolve and re-validate one generic-monster subject from the bestiary."""
    if archetype not in MONSTER_TIER_REGISTRY:
        raise ArtSubjectError(f"unknown monster archetype {archetype!r}")
    _validate_subject_key(archetype)
    return ArtSubject(ArtSubjectKind.MONSTER, archetype)


def character_subject_for(entity) -> ArtSubject | None:
    """Derive a portrait subject only from an explicit named ``portrait_policy``.

    ``None`` and ``{"mode": "generic"}`` produce no unique portrait. Eligibility
    is never inferred from the display name, quest role, key shape, or LLM
    authorship.
    """
    policy = entity.db.portrait_policy if hasattr(entity, "db") else None
    if policy is None:
        return None
    if isinstance(policy, dict):
        policy = dict(policy)
    elif not hasattr(policy, "get"):
        raise ArtSubjectError("portrait_policy must be a mapping or None")
    mode = policy.get("mode")
    if mode == "generic":
        return None
    if mode == "named":
        stable_key = policy.get("stable_key")
        if not isinstance(stable_key, str):
            raise ArtSubjectError("a named portrait policy needs a text stable_key")
        _validate_subject_key(stable_key)
        return ArtSubject(ArtSubjectKind.CHARACTER, stable_key)
    raise ArtSubjectError(f"unknown portrait policy mode {mode!r}")


def _race_label(entity) -> str:
    subrace_key = entity.db.subrace
    if subrace_key:
        subrace = SUBRACE_REGISTRY.get(subrace_key)
        if subrace is not None:
            return subrace.display_name_zh
    return str(entity.db.race or "unknown race")


def character_description(entity, age: int) -> str:
    """One deterministic adult-safe description for a character portrait.

    The template covers only stable, validated identity: the display name,
    race/subrace label, and the adult age. Persona text, secret state, mutable
    combat resources, and disguised stats are never included (design D6).
    """
    display_name = entity.db.display_name or entity.key or "<unknown>"
    return (
        f"A {_race_label(entity)} adult named {display_name} "
        f"({age}) in the {_APPROVED_STYLE}."
    )


def scene_description(subject: ArtSubject) -> str:
    """The immutable one-sentence registry description for a scene subject."""
    archetype = SCENE_ARCHETYPE_REGISTRY[subject.key]
    return archetype.scene_sentence


def monster_description(subject: ArtSubject) -> str:
    """The deterministic bestiary description for a generic-monster subject."""
    tier = MONSTER_TIER_REGISTRY[subject.key]
    examples = "、".join(tier.example_monsters_zh)
    return f"{tier.description} ({tier.display_name_zh}；例如：{examples})"


def description_for(subject: ArtSubject, *, entity=None, age=None) -> str:
    """Return the canonical deterministic description for a subject."""
    if subject.kind is ArtSubjectKind.SCENE:
        return scene_description(subject)
    if subject.kind is ArtSubjectKind.MONSTER:
        return monster_description(subject)
    if entity is None or age is None:
        raise ArtSubjectError(
            "a character description requires the entity and adult age"
        )
    return character_description(entity, age)
