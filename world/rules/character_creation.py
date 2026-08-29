"""Deterministic validation and activation for account-owned player shells."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import random
import unicodedata
from typing import Any

from django.db import transaction

from world.imports.schema import MAX_ENTITY_KEY_LENGTH
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY, StatModifiers
from world.lore.starting_kits import SUBRACE_STARTING_KIT_REGISTRY
from world.rules.surfaces import (
    restore_attributes,
    restore_traits,
    snapshot_attributes,
    snapshot_traits,
)
from world.rules.traits import GAUGE_KEYS, STATIC_KEYS, trait_config_for_values

ALLOCATABLE_AXES = GAUGE_KEYS + STATIC_KEYS
_CREATION_ATTRIBUTE_KEYS = (
    "age", "apparent_age", "race", "subrace", "creation_pending",
    "magic_xp", "skill_proficiency", "skills", "skill_grants", "equipment",
    "inventory", "wallet", "quest_log", "guild_rank", "persona",
    "portrait_policy", "affinity_elements",
)

# The single deterministic race-bound mapping every identity channel and the
# WebClient descriptor derive their affinity numbers from (D3): a human may
# pick up to 2 elements, a beastfolk up to 1, and an elf picks none (its set
# is seeded from the chosen subrace).
_AFFINITY_INPUT_BOUNDS: dict[str, int] = {
    "human": 2,
    "beastfolk": 1,
    "elf": 0,
}


def max_affinity_elements(race_key: str) -> int:
    """Return the player-input affinity-element bound for one race key.

    The single deterministic mapping (``human`` 2, ``beastfolk`` 1, ``elf`` 0)
    from which custom-creation validation, import validation, and the
    WebClient custom-form descriptor all derive their numbers so the layers
    cannot drift.
    """
    if race_key not in _AFFINITY_INPUT_BOUNDS:
        raise CharacterCreationError(f"unknown race {race_key!r}")
    return _AFFINITY_INPUT_BOUNDS[race_key]


def validate_affinity_seed(
    seed: Any, label: str = "subrace affinity seed"
) -> tuple[str, ...]:
    """Validate one affinity seed: registry membership and uniqueness only.

    Subrace seeds are the sole source of an elf's affinity and may exceed the
    player-input bound (eolas seeds all eight), so the bound is deliberately
    NOT applied here -- only that every key exists in ``ELEMENT_REGISTRY`` and
    no key repeats. An invalid seed raises, so it can never be persisted.
    """
    if isinstance(seed, (str, bytes)) or not isinstance(seed, Sequence):
        raise CharacterCreationError(
            f"{label} must be a sequence of element keys"
        )
    seen: set[str] = set()
    checked: list[str] = []
    for entry in seed:
        if not isinstance(entry, str) or entry not in ELEMENT_REGISTRY:
            raise CharacterCreationError(
                f"{label} contains unknown element {entry!r}"
            )
        if entry in seen:
            raise CharacterCreationError(
                f"{label} contains duplicate element {entry!r}"
            )
        seen.add(entry)
        checked.append(entry)
    return tuple(checked)


def validate_affinity_elements(
    elements: Any, race_key: str
) -> tuple[str, ...]:
    """Validate one player- or import-supplied affinity set against the race bound.

    Every key must exist in ``ELEMENT_REGISTRY`` with no duplicates, and the
    count must respect ``max_affinity_elements(race_key)``. An elf-supplied set
    is rejected entirely (an elf's affinity is subrace-seeded). ``None`` and
    an empty set normalize to ``()`` (neutral).
    """
    if elements is None:
        return ()
    checked = validate_affinity_seed(elements, "affinity_elements")
    if not checked:
        return ()
    if race_key == "elf":
        raise CharacterCreationError(
            "affinity_elements must be empty for an elf; "
            "its affinity is seeded from the subrace"
        )
    bound = max_affinity_elements(race_key)
    if len(checked) > bound:
        raise CharacterCreationError(
            f"affinity_elements exceeds the {race_key} bound of {bound} elements"
        )
    return checked


def _resolved_affinity_elements(validated: "_ValidatedCreation") -> tuple[str, ...]:
    """Resolve the single affinity source at activation time.

    An elf's set is always seeded from ``SUBRACE_REGISTRY[subrace]`` (validated
    so an invalid seed can never be persisted); every other race uses the
    validated player/preset-supplied set.
    """
    if validated.race == "elf":
        subrace = SUBRACE_REGISTRY[validated.subrace]
        return validate_affinity_seed(
            subrace.affinity_elements, "subrace affinity seed"
        )
    return validated.affinity_elements

# The persona draft's exact prose field set (creation-persona-persistence D3).
# Mirrors the generative layer's ``PERSONA_FIELDS``; a parity test keeps the
# two in lock step.
PERSONA_PROSE_KEYS = ("personality", "life_story", "habit")
# The import-card persona record shape (world.imports loader contract): the
# block fills the three prose fields and the remaining keys are stored as
# empty containers, so every future PersonaStore consumer sees the documented
# six-key contract.
PERSONA_IMPORT_CARD_KEYS = (
    "identity", "personality", "life_story", "habit", "appearance",
    "social_connection",
)
# Hard cap on one persona prose field (design D2); matches the generative
# layer's prompt-side cap so a validated draft always fits the read-only
# persona contract. A parity test keeps the two in lock step.
MAX_PERSONA_FIELD_LENGTH = 600


class CharacterCreationError(ValueError):
    """Raised when a creation request is invalid or cannot commit."""


@dataclass(frozen=True)
class StartingProfile:
    """Raw allocation bounds plus post-allocation static modifiers."""

    race: str
    subrace: str | None
    bounds: tuple[tuple[str, tuple[int, int]], ...]
    static_modifiers: StatModifiers
    budget: int

    def bounds_dict(self) -> dict[str, tuple[int, int]]:
        return dict(self.bounds)


@dataclass(frozen=True)
class CharacterCreationRequest:
    """Fully specified custom or preset activation input."""

    mode: str
    display_name: str | None = None
    age: int | None = None
    apparent_age: int | None = None
    race: str | None = None
    subrace: str | None = None
    allocations: Mapping[str, int] | None = None
    preset_key: str | None = None
    background: str | None = None
    affinity_elements: tuple[str, ...] | None = None


@dataclass(frozen=True)
class CharacterCreationResult:
    """Persisted identity and sampled starting magic level."""

    display_name: str
    race: str
    subrace: str | None
    magic_level: int


@dataclass(frozen=True)
class _ValidatedCreation:
    display_name: str
    age: int
    apparent_age: int
    race: str
    subrace: str | None
    values: dict[str, int]
    background: str | None = None
    affinity_elements: tuple[str, ...] = ()


def resolve_starting_profile(race_key: str, subrace_key: str | None = None) -> StartingProfile:
    """Resolve player allocation bounds entirely from immutable lore."""
    race = RACE_REGISTRY.get(race_key)
    if race is None:
        raise CharacterCreationError(f"unknown race {race_key!r}")
    subrace = None
    if subrace_key:
        subrace = SUBRACE_REGISTRY.get(subrace_key)
        if subrace is None:
            raise CharacterCreationError(f"unknown subrace {subrace_key!r}")
        if subrace.race_key != race_key:
            raise CharacterCreationError(
                f"subrace {subrace_key!r} does not belong to race {race_key!r}"
            )

    bounds = {key: getattr(race.vital_baseline, key) for key in GAUGE_KEYS}
    bounds.update({key: getattr(race.static_baseline, key) for key in STATIC_KEYS})
    if subrace and subrace.vital_overrides:
        bounds.update(subrace.vital_overrides)
    modifiers = subrace.static_modifiers if subrace else StatModifiers()
    budget = sum(upper - lower for lower, upper in bounds.values()) // 2
    return StartingProfile(
        race_key, subrace_key, tuple((key, bounds[key]) for key in ALLOCATABLE_AXES),
        modifiers, budget,
    )


def _validate_name(value: Any) -> str:
    if not isinstance(value, str):
        raise CharacterCreationError("display name must be text")
    name = value.strip()
    if not 1 <= len(name) <= MAX_ENTITY_KEY_LENGTH:
        raise CharacterCreationError(
            f"display name must contain 1 to {MAX_ENTITY_KEY_LENGTH} characters"
        )
    if any(not char.isprintable() or unicodedata.category(char).startswith("C") for char in name):
        raise CharacterCreationError("display name contains a control character")
    if any(char in name for char in "|{}"):
        raise CharacterCreationError("display name contains an Evennia markup delimiter")
    if any(char in name for char in "/:"):
        raise CharacterCreationError("display name contains a reserved separator")
    return name


def _validate_adult(value: Any, field: str) -> int:
    if type(value) is not int or value < 18:
        raise CharacterCreationError(f"{field} must be an integer of at least 18")
    return value


def _validate_allocations(profile: StartingProfile, allocations: Any) -> dict[str, int]:
    if not isinstance(allocations, Mapping) or set(allocations) != set(ALLOCATABLE_AXES):
        raise CharacterCreationError("allocations must contain exactly the six starting axes")
    bounds = profile.bounds_dict()
    checked: dict[str, int] = {}
    for key in ALLOCATABLE_AXES:
        value = allocations[key]
        span = bounds[key][1] - bounds[key][0]
        if type(value) is not int or not 0 <= value <= span:
            raise CharacterCreationError(f"allocation for {key} must be an integer from 0 to {span}")
        checked[key] = value
    if sum(checked.values()) != profile.budget:
        raise CharacterCreationError(f"allocations must sum exactly to {profile.budget}")
    return checked


def _validate_background(value: Any) -> str | None:
    """Validate one optional player-authored background (flavor) text field.

    A blank or missing value is accepted and becomes ``None`` (the persona
    record simply omits the key); a non-string or over-bound value rejects.
    The bound mirrors ``MAX_PERSONA_FIELD_LENGTH`` so the validated draft
    always fits the read-only persona contract.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise CharacterCreationError("background must be text")
    text = value.strip()
    if not text:
        return None
    if len(text) > MAX_PERSONA_FIELD_LENGTH:
        raise CharacterCreationError(
            f"background exceeds the {MAX_PERSONA_FIELD_LENGTH}-character length cap"
        )
    return text


def _validate_persona_block(value: Any) -> dict[str, str]:
    """Validate one deterministic persona block: exactly the three prose fields.

    The block is the server-owned persona draft carried by the concept draft
    (creation-persona-persistence D1/D3). Contents are never inspected -- only
    the exact field set, text type, and length cap are checked -- so the
    generative layer's whole-proposal validation stays the content authority
    and the activation write stays deterministic.
    """
    if not isinstance(value, Mapping) or set(value) != set(PERSONA_PROSE_KEYS):
        raise CharacterCreationError(
            "persona must contain exactly personality, life_story, and habit"
        )
    checked: dict[str, str] = {}
    for field in PERSONA_PROSE_KEYS:
        text = value[field]
        if not isinstance(text, str) or not text.strip():
            raise CharacterCreationError(f"persona.{field} must be a non-empty text field")
        if len(text) > MAX_PERSONA_FIELD_LENGTH:
            raise CharacterCreationError(
                f"persona.{field} exceeds the {MAX_PERSONA_FIELD_LENGTH}-character length cap"
            )
        checked[field] = text
    return checked


def _owned_character(account: Any, character: Any) -> bool:
    return character in account.characters


def preflight_character_creation(
    account: Any, character: Any, request: CharacterCreationRequest
) -> _ValidatedCreation:
    """Validate every input and compute final values without sampling or writing."""
    if account is None or not _owned_character(account, character):
        raise CharacterCreationError("character is not owned by this account")
    if not character.creation_pending:
        raise CharacterCreationError("character creation is already complete")

    if request.mode == "preset":
        preset = PLAYER_PRESET_REGISTRY.get(request.preset_key or "")
        if preset is None:
            raise CharacterCreationError("unknown player preset")
        name, age, apparent_age = preset.display_name, preset.age, preset.apparent_age
        race, subrace, allocations = preset.race, preset.subrace, preset.allocation_dict()
        affinity_elements = preset.affinity_elements
    elif request.mode == "custom":
        name, age, apparent_age = request.display_name, request.age, request.apparent_age
        race, subrace, allocations = request.race, request.subrace, request.allocations
        affinity_elements = request.affinity_elements
    else:
        raise CharacterCreationError("creation mode must be 'preset' or 'custom'")

    valid_name = _validate_name(name)
    valid_age = _validate_adult(age, "age")
    valid_apparent_age = _validate_adult(apparent_age, "apparent_age")
    if not isinstance(race, str):
        raise CharacterCreationError("race must be a registry key")
    if request.mode == "custom":
        # Every race has at least one registered subrace, so custom creation
        # never offers "none": a missing, blank, literal "none", or non-string
        # subrace is rejected here with a stable message before the profile
        # resolves.
        if (
            not isinstance(subrace, str)
            or not subrace.strip()
            or subrace.strip().lower() == "none"
        ):
            raise CharacterCreationError("custom creation requires a registered subrace")
    elif subrace is not None and not isinstance(subrace, str):
        raise CharacterCreationError("subrace must be a registry key or omitted")
    profile = resolve_starting_profile(race, subrace)
    checked = _validate_allocations(profile, allocations)
    bounds = profile.bounds_dict()
    values = {key: bounds[key][0] + checked[key] for key in ALLOCATABLE_AXES}
    for key in STATIC_KEYS:
        values[key] = round(values[key] * (1 + getattr(profile.static_modifiers, key)))
    values["guild_merit"] = 0
    if request.mode == "custom":
        # Custom-mode affinity is race-bounded player input (D4): an elf
        # rejects any player-supplied set, and the race-dependent bound
        # (human 2 / beastfolk 1 / elf 0) is enforced here.
        checked_affinity = validate_affinity_elements(affinity_elements, race)
    else:
        # Preset-mode affinity is the preset's own declared set (already
        # validated at registry load); the elf's set is resolved from the
        # subrace at activation.
        checked_affinity = tuple(affinity_elements or ())
    background = (
        _validate_background(request.background)
        if request.mode == "custom"
        else None
    )
    return _ValidatedCreation(
        valid_name, valid_age, valid_apparent_age, race, subrace, values,
        background, checked_affinity,
    )


def starting_magic_interval(race_key: str) -> tuple[int, int]:
    race = RACE_REGISTRY[race_key]
    average = race.starting_magic_level
    low = (average * 9 + 9) // 10
    high = average * 11 // 10
    if low < 0 or high < low or high > race.magic_cap:
        raise CharacterCreationError("race has an invalid starting magic interval")
    return low, high


def finalize_player_portrait(character: Any) -> None:
    """Establish the named portrait policy and schedule the post-commit ensure.

    The explicit named policy (``{"mode": "named", "stable_key": str(pk)}``)
    is the art lifecycle's eligibility marker; ``schedule_portrait_ensure``
    registers the exception-safe post-commit ensure. Must be called INSIDE the
    activation transaction (fix-creation-finalization-safety D3): a rollback
    removes the policy attribute and the registered on-commit job never fires,
    so no rolled-back creation can leave portrait state behind.
    """
    character.db.portrait_policy = {
        "mode": "named",
        "stable_key": str(character.pk),
    }
    from world.art.service import schedule_portrait_ensure

    schedule_portrait_ensure(character)


def activate_player_character(
    account: Any,
    character: Any,
    request: CharacterCreationRequest,
    *,
    sampler: Callable[[int, int], int] = random.randint,
    write_observer: Callable[[str], None] | None = None,
    persona: Mapping[str, Any] | None = None,
) -> CharacterCreationResult:
    """Atomically initialize one existing account-owned pending shell.

    ``persona`` carries the server-owned persona block from the staging draft
    (creation-persona-persistence D3): when present it is validated
    deterministically and persisted as the six-key import-card record inside
    the same all-or-nothing transaction; when absent nothing is written.
    """
    validated = preflight_character_creation(account, character, request)
    low, high = starting_magic_interval(validated.race)
    magic_level = sampler(low, high)
    if type(magic_level) is not int or not low <= magic_level <= high:
        raise CharacterCreationError("magic sampler returned a value outside its integer band")
    race = RACE_REGISTRY[validated.race]
    if not 0 <= magic_level <= race.magic_cap:
        raise CharacterCreationError("magic sampler returned a value outside the race cap")

    values = {**validated.values, "magic_level": magic_level}
    trait_config = trait_config_for_values(values, race.magic_cap)
    skills_value = (
        PLAYER_PRESET_REGISTRY[request.preset_key].skill_lists()
        if request.mode == "preset"
        else {"active": [], "passive": []}
    )
    if request.mode == "preset":
        inventory_value = PLAYER_PRESET_REGISTRY[request.preset_key].inventory_list()
    else:
        # Custom mode hands out the chosen subrace's basic starting kit
        # (add-subrace-starting-kits D2). Load-time coverage guarantees the
        # lookup succeeds; the guarded get keeps even a future registry bug
        # failing pre-persistence like every other activation error.
        kit = SUBRACE_STARTING_KIT_REGISTRY.get(validated.subrace)
        if kit is None:
            raise CharacterCreationError("subrace has no registered starting kit")
        inventory_value = kit.inventory_list()
    attribute_values = {
        "age": validated.age,
        "apparent_age": validated.apparent_age,
        "race": validated.race,
        "subrace": validated.subrace,
        "magic_xp": 0,
        "skill_proficiency": {},
        "skills": skills_value,
        "skill_grants": [],
        "equipment": {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []},
        "inventory": inventory_value,
        "wallet": 0,
        "quest_log": [],
        "guild_rank": None,
        "creation_pending": False,
        "affinity_elements": list(_resolved_affinity_elements(validated)),
    }
    persona_record = None
    if persona is not None:
        checked_persona = _validate_persona_block(persona)
        persona_record = {
            "identity": {},
            "personality": checked_persona["personality"],
            "life_story": checked_persona["life_story"],
            "habit": checked_persona["habit"],
            "appearance": {},
            "social_connection": {},
        }
        if validated.background is not None:
            persona_record["background"] = validated.background
    elif validated.background is not None:
        # A custom draft with a background but no concept persona block still
        # persists an import-card-shaped record so the owner can inspect and
        # update the flavor text (creation-persona-persistence D4).
        persona_record = {
            "identity": {},
            "personality": "",
            "life_story": "",
            "habit": "",
            "appearance": {},
            "social_connection": {},
            "background": validated.background,
        }
    old_key = character.key
    attribute_snapshots = snapshot_attributes(character, _CREATION_ATTRIBUTE_KEYS)
    trait_snapshot = snapshot_traits(character)
    try:
        with transaction.atomic():
            character.key = validated.display_name
            character.save(update_fields=["db_key"])
            if write_observer:
                write_observer("identity")
            character._apply_trait_config(trait_config)
            if write_observer:
                write_observer("traits")
            for key, value in attribute_values.items():
                character.attributes.add(key, value)
                if write_observer:
                    write_observer(key)
            # The persona write is part of the same all-or-nothing transaction:
            # a failure here rolls back the whole activation, so a crash or a
            # rejected write can never leave a persona-less active character
            # behind (creation-persona-persistence D3).
            if persona_record is not None:
                character.attributes.add("persona", persona_record)
                if write_observer:
                    write_observer("persona")
            # Every activation path (Telnet command, WebClient ``activate_draft``)
            # clears the staging creation draft in the SAME atomic transaction, so
            # a completed character never retains a draft (webclient-character-
            # creation-ui D3). This is the single documented finalization write
            # to ``creation_draft`` outside the wizard's save path.
            if character.attributes.has("creation_draft"):
                if write_observer:
                    write_observer("creation_draft")
                character.attributes.remove("creation_draft")
            # Every player-activation path (Telnet command, WebClient
            # ``activate_draft``) establishes the named portrait policy and
            # schedules the post-commit portrait ensure INSIDE this activation
            # transaction (fix-creation-finalization-safety D3): a rollback
            # removes the policy attribute and the on-commit job never fires.
            finalize_player_portrait(character)
            if write_observer:
                write_observer("portrait_policy")
    except Exception:
        character.key = old_key
        restore_traits(character, trait_snapshot)
        restore_attributes(character, attribute_snapshots)
        raise
    return CharacterCreationResult(
        validated.display_name, validated.race, validated.subrace, magic_level
    )
