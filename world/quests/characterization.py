"""Shared deterministic bound helper for quest-blueprint characterization.

Change 22's mirror-validation rule source: both the scenario-director guardrail
(``world/ai``) and the deterministic compile boundary (``world/quests``)
validate the optional per-occupant characterization fields -- ``display_name``,
paired ``age``/``apparent_age``, and the named ``portrait.stable_key`` --
through this one module, so the two layers cannot drift. The module is pure: it
imports only the immutable lore registries and the adult floor constant, and it
never mutates state. ``world/ai`` imports it read-only, the same direction it
already uses for ``world/lore`` registries; ``world/quests`` imports it
directly. No state-changing API is reachable from here.
"""

from collections.abc import Mapping
import unicodedata
from typing import Any

from world.art.adult import ADULT_MINIMUM
from world.art.subjects import (
    FORBIDDEN_SUBJECT_KEY_CHARACTERS,
    MAX_SUBJECT_KEY_BYTES,
    MAX_SUBJECT_KEY_LENGTH,
)

# Bounded text/key caps for the characterization fields. ``stable_key`` obeys
# the single shared art-side subject-key contract (fix-art-pipeline-contracts
# D1): non-empty, no reserved separators, no control characters, at most 64
# code points and at most 200 UTF-8 bytes -- exactly what
# ``world/art/subjects.py`` enforces for every producer, so a compiled quest
# key can never be rejected later at the queue or exceed the worker output
# filename bound.
MAX_DISPLAY_NAME_LENGTH = 64
MAX_STABLE_KEY_LENGTH = MAX_SUBJECT_KEY_LENGTH

# The optional authored persona/background flavor fields share the persona
# field bound (fix-custom-creation-information-and-background D7): a generated
# NPC's flavor text must always fit the read-only ``PersonaStore`` contract so
# the look appearance path can render it unchanged. The value mirrors
# ``world.rules.character_creation.MAX_PERSONA_FIELD_LENGTH``; this module
# cannot import ``world.rules`` (the shared-helper purity contract), so a
# parity contract pins the two numbers together.
MAX_PERSONA_FIELD_LENGTH = 600
PERSONA_PROSE_KEYS = ("personality", "life_story", "habit")

_AGE_FIELDS = ("age", "apparent_age")


def race_lifespan_upper_bound(tier_key: str) -> int:
    """Resolve one NPC tier's race lifespan upper bound from the registries.

    The upper bound is the ``RaceProfile.lifespan`` ceiling of the tier's race,
    reached through ``NPC_TIER_REGISTRY[tier].race_key`` -- never a copied
    constant, so a lore edit propagates to both validation layers on next
    import (design D4).
    """
    from world.lore.npc_tiers import NPC_TIER_REGISTRY
    from world.lore.races import RACE_REGISTRY

    tier = NPC_TIER_REGISTRY[tier_key]
    return RACE_REGISTRY[tier.race_key].lifespan[1]


def characterize_errors(
    entry: Mapping[str, Any],
    *,
    lifespan_upper_bound: int,
) -> list[str]:
    """Validate one ``npc_req`` entry's optional characterization fields.

    Returns a list of human-readable problems (empty when valid). The rules
    mirror design D2/D3/D4 and the art-side subject-key contract:

    - ``display_name``, when declared, is bounded non-empty text.
    - ``age``/``apparent_age``, when declared, are paired and each satisfies
      ``type(value) is int`` (so booleans, floats, and ``None`` reject) with
      ``ADULT_MINIMUM <= value <= lifespan_upper_bound``. A key present with a
      ``None`` value is not an absence and rejects.
    - ``portrait``, when declared, is a mapping with exactly one ``stable_key``
      field whose value obeys the shared subject-key contract (bounded
      non-empty text, no reserved separators, no control characters).
    """
    errors: list[str] = []

    if "display_name" in entry:
        value = entry["display_name"]
        if value is None or not isinstance(value, str) or not value.strip():
            errors.append("display_name must be non-empty text")
        elif len(value) > MAX_DISPLAY_NAME_LENGTH:
            errors.append(
                f"display_name exceeds the {MAX_DISPLAY_NAME_LENGTH}-character cap"
            )

    age_present = "age" in entry
    apparent_present = "apparent_age" in entry
    if age_present != apparent_present:
        errors.append("age and apparent_age must be declared together")
    for field in _AGE_FIELDS:
        if field not in entry:
            continue
        value = entry[field]
        if value is None or type(value) is not int:
            errors.append(
                f"{field} must be an integer (booleans and None reject)"
            )
            continue
        if value < ADULT_MINIMUM:
            errors.append(f"{field} {value} is below the adult floor {ADULT_MINIMUM}")
        if value > lifespan_upper_bound:
            errors.append(
                f"{field} {value} exceeds the race lifespan upper bound "
                f"{lifespan_upper_bound}"
            )

    if "portrait" in entry:
        portrait = entry["portrait"]
        if portrait is None or not isinstance(portrait, Mapping):
            errors.append("portrait must be an object with exactly one stable_key field")
        else:
            if set(portrait.keys()) != {"stable_key"}:
                errors.append("portrait must carry exactly one stable_key field")
            else:
                stable_key = portrait["stable_key"]
                if stable_key is None or not isinstance(stable_key, str) or not stable_key:
                    errors.append("portrait.stable_key must be non-empty text")
                elif any(
                    char in FORBIDDEN_SUBJECT_KEY_CHARACTERS for char in stable_key
                ):
                    errors.append(
                        "portrait.stable_key must not contain '|', '/', ':', "
                        "'{', or '}'"
                    )
                elif any(
                    not char.isprintable()
                    or unicodedata.category(char).startswith("C")
                    for char in stable_key
                ):
                    errors.append(
                        "portrait.stable_key must not contain control characters"
                    )
                elif len(stable_key.encode("utf-8")) > MAX_SUBJECT_KEY_BYTES:
                    errors.append(
                        f"portrait.stable_key exceeds the "
                        f"{MAX_SUBJECT_KEY_BYTES}-byte UTF-8 bound"
                    )
                elif len(stable_key) > MAX_STABLE_KEY_LENGTH:
                    errors.append(
                        f"portrait.stable_key exceeds the "
                        f"{MAX_STABLE_KEY_LENGTH}-character cap"
                    )

    if "persona" in entry:
        persona = entry["persona"]
        if persona is None or not isinstance(persona, Mapping):
            errors.append("persona must be an object with optional prose fields")
        else:
            extra = sorted(set(persona) - set(PERSONA_PROSE_KEYS))
            if extra:
                # The persona block is exactly the three prose fields; a nested
                # ``background`` (or any other key) is not part of the authored
                # contract and would be silently dropped at compile, so it is
                # rejected here. Background flavor belongs at the top level
                # (fix-custom-creation-information-and-background D7).
                errors.append(
                    "persona may only carry personality, life_story, and habit"
                )
            for field in PERSONA_PROSE_KEYS:
                if field not in persona:
                    continue
                value = persona[field]
                if value is None or not isinstance(value, str) or not value.strip():
                    errors.append(f"persona.{field} must be non-empty text")
                elif len(value) > MAX_PERSONA_FIELD_LENGTH:
                    errors.append(
                        f"persona.{field} exceeds the "
                        f"{MAX_PERSONA_FIELD_LENGTH}-character cap"
                    )
    if "background" in entry:
        # The top-level ``background`` is the canonical authored flavor surface
        # for a characterization entry, validated independently of whether a
        # ``persona`` object is also present.
        value = entry["background"]
        if value is None or not isinstance(value, str):
            errors.append("background must be text")
        elif value.strip() and len(value) > MAX_PERSONA_FIELD_LENGTH:
            errors.append(
                f"background exceeds the "
                f"{MAX_PERSONA_FIELD_LENGTH}-character cap"
            )
    return errors


def duplicate_stable_key_errors(entries: list[Mapping[str, Any]]) -> list[str]:
    """Return errors when shared portrait ``stable_key`` entries disagree.

    Two ``npc_req`` entries sharing a ``stable_key`` in one blueprint SHALL
    declare the same ``display_name``, ages, persona/background flavor, and
    portrait key; conflicting characterization under the same key is a
    blueprint error and rejects (design D6). Entries without a well-formed
    portrait key are ignored -- ``characterize_errors`` reports them.
    """
    seen: dict[str, tuple[Any, ...]] = {}
    errors: list[str] = []
    for entry in entries:
        portrait = entry.get("portrait")
        if not isinstance(portrait, Mapping) or "stable_key" not in portrait:
            continue
        stable_key = portrait["stable_key"]
        if not isinstance(stable_key, str) or not stable_key:
            continue
        identity = (
            entry.get("display_name"),
            entry.get("age"),
            entry.get("apparent_age"),
            entry.get("persona"),
            entry.get("background"),
        )
        if stable_key in seen and seen[stable_key] != identity:
            errors.append(
                f"conflicting characterization under shared stable_key {stable_key!r}"
            )
        seen.setdefault(stable_key, identity)
    return errors
