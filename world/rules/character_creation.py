"""Deterministic validation and activation for account-owned player shells."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import random
import unicodedata
from typing import Any

from django.db import transaction

from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY, StatModifiers
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
    "inventory", "wallet", "quest_log", "guild_rank",
)


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
    if not 1 <= len(name) <= 80:
        raise CharacterCreationError("display name must contain 1 to 80 characters")
    if any(not char.isprintable() or unicodedata.category(char).startswith("C") for char in name):
        raise CharacterCreationError("display name contains a control character")
    if "|" in name or "{" in name:
        raise CharacterCreationError("display name contains an Evennia markup delimiter")
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
    elif request.mode == "custom":
        name, age, apparent_age = request.display_name, request.age, request.apparent_age
        race, subrace, allocations = request.race, request.subrace, request.allocations
    else:
        raise CharacterCreationError("creation mode must be 'preset' or 'custom'")

    valid_name = _validate_name(name)
    valid_age = _validate_adult(age, "age")
    valid_apparent_age = _validate_adult(apparent_age, "apparent_age")
    if not isinstance(race, str):
        raise CharacterCreationError("race must be a registry key")
    if subrace is not None and not isinstance(subrace, str):
        raise CharacterCreationError("subrace must be a registry key or omitted")
    profile = resolve_starting_profile(race, subrace)
    checked = _validate_allocations(profile, allocations)
    bounds = profile.bounds_dict()
    values = {key: bounds[key][0] + checked[key] for key in ALLOCATABLE_AXES}
    for key in STATIC_KEYS:
        values[key] = round(values[key] * (1 + getattr(profile.static_modifiers, key)))
    values["guild_merit"] = 0
    return _ValidatedCreation(
        valid_name, valid_age, valid_apparent_age, race, subrace, values
    )


def starting_magic_interval(race_key: str) -> tuple[int, int]:
    race = RACE_REGISTRY[race_key]
    average = race.starting_magic_level
    low = (average * 9 + 9) // 10
    high = average * 11 // 10
    if low < 0 or high < low or high > race.magic_cap:
        raise CharacterCreationError("race has an invalid starting magic interval")
    return low, high


def activate_player_character(
    account: Any,
    character: Any,
    request: CharacterCreationRequest,
    *,
    sampler: Callable[[int, int], int] = random.randint,
    write_observer: Callable[[str], None] | None = None,
) -> CharacterCreationResult:
    """Atomically initialize one existing account-owned pending shell."""
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
    attribute_values = {
        "age": validated.age,
        "apparent_age": validated.apparent_age,
        "race": validated.race,
        "subrace": validated.subrace,
        "magic_xp": 0,
        "skill_proficiency": {},
        "skills": {"active": [], "passive": []},
        "skill_grants": [],
        "equipment": {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []},
        "inventory": [],
        "wallet": 0,
        "quest_log": [],
        "guild_rank": None,
        "creation_pending": False,
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
            # Every activation path (Telnet command, WebClient ``activate_draft``)
            # clears the staging creation draft in the SAME atomic transaction, so
            # a completed character never retains a draft (webclient-character-
            # creation-ui D3). This is the single documented finalization write
            # to ``creation_draft`` outside the wizard's save path.
            if character.attributes.has("creation_draft"):
                if write_observer:
                    write_observer("creation_draft")
                character.attributes.remove("creation_draft")
    except Exception:
        character.key = old_key
        restore_traits(character, trait_snapshot)
        restore_attributes(character, attribute_snapshots)
        raise
    return CharacterCreationResult(
        validated.display_name, validated.race, validated.subrace, magic_level
    )
