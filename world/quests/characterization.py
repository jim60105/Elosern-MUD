"""Shared deterministic bound helper for quest-blueprint characterization.

Change 22's mirror-validation rule source: both the scenario-director guardrail
(``world/ai``) and the deterministic compile boundary (``world/quests``)
validate the per-occupant characterization fields -- the required authored
``display_name``/``title``, paired ``age``/``apparent_age``, the named
``portrait.stable_key``, and the required compact ``persona`` card -- through
this one module, so the two layers cannot
drift. The module never mutates state, and its only world.rules dependency is
the single shared identity validator in ``world/rules/npc_identity.py``
(npc-title-authored-identities D3: the name and title character rules delegate
to that one module through function-local deferred imports, so this helper
never inlines or duplicates the character-set rules; the bound constant is a
plain immutable read). ``world/ai`` imports it read-only, the same direction it
already uses for ``world/lore`` registries; ``world/quests`` imports it
directly. No state-changing API is reachable from here.
"""

from collections.abc import Mapping
import unicodedata
from typing import Any

from world.art.subjects import (
    FORBIDDEN_SUBJECT_KEY_CHARACTERS,
    MAX_SUBJECT_KEY_BYTES,
    MAX_SUBJECT_KEY_LENGTH,
    is_reserved_player_stable_key,
)
# The occupant card obeys the single pure compact-card contract
# (npc-persona-generated-quest-cards D2): required, normalized, and bounded by
# ``world.lore.npc_card`` -- a registry-only lore module with no Evennia,
# Django, or ``world.rules`` dependency, so the helper stays pure.
from world.lore.npc_card import NpcCardError, normalize_card

# Bounded text/key caps for the characterization fields. The authored-name cap
# is the shared NPC name bound itself (npc-title-authored-identities D3): the
# name/title character rules live in exactly one module. ``stable_key`` obeys
# the single shared art-side subject-key contract (fix-art-pipeline-contracts
# D1): non-empty, no reserved separators, no control characters, at most 64
# code points and at most 200 UTF-8 bytes -- exactly what
# ``world/art/subjects.py`` enforces for every producer, so a compiled quest
# key can never be rejected later at the queue or exceed the worker output
# filename bound.
from world.rules.npc_identity import MAX_NPC_NAME_CODE_POINTS

MAX_DISPLAY_NAME_LENGTH = MAX_NPC_NAME_CODE_POINTS
MAX_STABLE_KEY_LENGTH = MAX_SUBJECT_KEY_LENGTH

# The lower bound of a reasonable declared age: no age below zero is
# meaningful, and the upper bound is the declared race's lifespan ceiling.
AGE_FLOOR = 0

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
    """Validate one ``npc_req`` entry's characterization fields.

    Returns a list of human-readable problems (empty when valid). The rules
    mirror design D2/D3/D4 and the art-side subject-key contract:

    - ``display_name`` and ``title`` are REQUIRED authored identity fields
      (npc-title-authored-identities D5): missing or empty rejects, never
      defaulted, and the character rules delegate to the single shared
      validators in ``world/rules/npc_identity.py``.
    - ``age``/``apparent_age``, when declared, are paired and each satisfies
      ``type(value) is int`` (so booleans, floats, and ``None`` reject) with
      ``AGE_FLOOR <= value <= lifespan_upper_bound``. A key present with a
      ``None`` value is not an absence and rejects.
    - ``portrait``, when declared, is a mapping with exactly one ``stable_key``
      field whose value obeys the shared subject-key contract (bounded
      non-empty text, no reserved separators, no control characters) and is
      not digit-only -- the digit-only region of the character-portrait
      keyspace is reserved for player characters (whose stable keys are
      ``str(pk)``), so a blueprint can never claim a player's portrait subject
      (fix-portrait-stable-key-collision D2).
    - ``persona`` is the REQUIRED complete compact card validated through the
      card contract (npc-persona-generated-quest-cards D2); a top-level
      ``background`` key is rejected because the card replaced it.
    """
    errors: list[str] = []

    from world.rules.npc_identity import (
        NPCNameError,
        NPCTitleError,
        validate_npc_name,
        validate_npc_title,
    )

    for field, validator_error in (
        ("display_name", (NPCNameError, validate_npc_name)),
        ("title", (NPCTitleError, validate_npc_title)),
    ):
        error_type, validator = validator_error
        if field not in entry:
            errors.append(
                f"{field} is required (authored identity is never defaulted)"
            )
            continue
        value = entry[field]
        if value is None or not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be non-empty text")
            continue
        try:
            validator(value)
        except error_type as error:
            errors.append(f"{field} is not a valid authored {field}: {error}")

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
        if value < AGE_FLOOR:
            errors.append(f"{field} {value} is negative")
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
                elif is_reserved_player_stable_key(stable_key):
                    errors.append(
                        "portrait.stable_key is digit-only: the digit-only "
                        "region of the character-portrait keyspace is reserved "
                        "for player characters"
                    )

    if "persona" not in entry:
        errors.append(
            "persona is required (every occupant carries a complete compact card)"
        )
    else:
        error = card_error(entry["persona"])
        if error is not None:
            errors.append(error)
    if "background" in entry:
        # The optional flavor ``background`` was replaced end to end by the
        # complete card (npc-persona-generated-quest-cards D1); a stray key is
        # a shape violation, never silently dropped.
        errors.append(
            "background is not part of the occupant shape; the persona card "
            "carries all characterization prose"
        )
    return errors


def card_error(raw: Any) -> str | None:
    """Return the named card-contract violation of one occupant card, if any.

    Delegates to ``world.lore.npc_card.normalize_card`` (design D2) and maps an
    ``NpcCardError`` onto ``persona.<leaf>: <code>`` (or ``persona: <code>``
    for a whole-card failure such as the rendered total bound).
    """
    try:
        normalize_card(raw)
    except NpcCardError as error:
        if error.field:
            return f"persona.{error.field}: {error.code}"
        return f"persona: {error.code}"
    return None


def _comparable_card(raw: Any) -> Any:
    """Return the normalized card record, or the raw value when invalid."""
    try:
        return normalize_card(raw).to_record()
    except NpcCardError:
        return raw


def duplicate_stable_key_errors(entries: list[Mapping[str, Any]]) -> list[str]:
    """Return errors when shared portrait ``stable_key`` entries disagree.

    Two ``npc_req`` entries sharing a ``stable_key`` in one blueprint SHALL
    declare the same ``display_name``, ages, normalized persona card, and
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
            _comparable_card(entry.get("persona")),
        )
        if stable_key in seen and seen[stable_key] != identity:
            errors.append(
                f"conflicting characterization under shared stable_key {stable_key!r}"
            )
        seen.setdefault(stable_key, identity)
    return errors


def duplicate_display_name_errors(entries: list[Mapping[str, Any]]) -> list[str]:
    """Return errors when two ``npc_req`` entries share one authored name.

    Every authored ``display_name`` is world-unique (design §3.2): two entries
    in ONE blueprint -- same stage or across stages -- declaring the same name
    reject (design D4). A shared portrait ``stable_key`` is the sanctioned way
    to say "the same face appears twice"; it never licenses two live NPCs under
    one key, because every materialization spawns fresh occupants with no
    cross-stage reuse path. Entries without a usable name string are ignored --
    ``characterize_errors`` reports them.
    """
    counts: dict[str, int] = {}
    for entry in entries:
        value = entry.get("display_name")
        if not isinstance(value, str) or not value.strip():
            continue
        name = value.strip()
        counts[name] = counts.get(name, 0) + 1
    return [
        f"display_name {name!r} is declared {count} times in this blueprint; "
        "authored names are unique across the whole blueprint"
        for name, count in counts.items()
        if count > 1
    ]
