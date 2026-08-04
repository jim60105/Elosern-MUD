"""Deterministic creation-wizard draft service (webclient-character-creation-ui D3).

This module is the sole writer of a pending character's ``creation_draft``
staging attribute. It exposes a frozen no-mutation read model
(:func:`read_creation_view`), draft saves validated through the existing public
``preflight_character_creation``, an idempotent reset (:func:`clear_draft`),
and :func:`activate_draft`, which re-validates the stored draft, re-checks
ownership and pending state against committed data, and clears the draft inside
one deterministic ``transaction.atomic()`` block together with the existing
all-or-nothing ``activate_player_character`` write.

The staging draft is not canonical identity: writing it never sets ``age``,
``apparent_age``, ``race``, ``subrace``, the object key, traits, or
``creation_pending``. A rejected or cancelled save leaves the canonical
identity attributes, the trait set, and any previously validated staging draft
unchanged.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    _CREATION_ATTRIBUTE_KEYS,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    preflight_character_creation,
    resolve_starting_profile,
)
from world.rules.surfaces import (
    restore_attributes,
    restore_traits,
    snapshot_attributes,
    snapshot_traits,
)

# Storage format of the staging draft attribute. Bounded and versioned so a
# future draft shape can be rejected cleanly rather than misread.
DRAFT_VERSION = 1
PRESET_STAGE = "preset_selected"
CUSTOM_STAGE = "custom_filled"

# Presentation bounds shared with the wire presenter (web.webclient.
# presentation.creation) and the JS validator; the registries today are far
# smaller, so these are structural ceilings that must never bind real data.
MAX_PRESETS = 8
MAX_RACES = 8
MAX_SUBRACES = 16
MAX_PROFILES = 16

# Custom-form bounds (design D2): identical to the command wizard's name rules
# and the deterministic adult gate.
NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 80
AGE_MINIMUM = 18
AGE_MAXIMUM = 10000
APPARENT_AGE_MINIMUM = 18
APPARENT_AGE_MAXIMUM = 10000
ALLOCATION_MAXIMUM = 10000

# Stable Traditional Chinese axis labels and player-facing explanations for the
# six allocatable starting axes. Presentation text only; the numeric authority
# lives in ``resolve_starting_profile``.
ALLOCATION_AXIS_LABELS: dict[str, str] = {
    "hp": "生命值",
    "mp": "魔力值",
    "sp": "體力值",
    "atk_phys": "物理攻擊",
    "agility": "敏捷",
    "defense": "防禦",
}
ALLOCATION_AXIS_EXPLANATIONS: dict[str, str] = {
    "hp": "生命值，決定你能承受多少傷害",
    "mp": "魔力值，驅動法術的消耗",
    "sp": "體力值，支撐行動與攻擊",
    "atk_phys": "物理攻擊，影響造成的傷害",
    "agility": "敏捷，影響命中與迴避",
    "defense": "防禦，減免受到的傷害",
}


@dataclass(frozen=True)
class PresetCardView:
    """One preset card derived entirely from immutable registry data."""

    key: str
    display_name: str
    race: str
    race_description: str
    subrace: str | None
    emphasis: str
    background: str


@dataclass(frozen=True)
class NameBoundsView:
    """The server-advertised display-name length bounds."""

    min_length: int
    max_length: int


@dataclass(frozen=True)
class AdultBoundsView:
    """The server-advertised adult age bounds for both age fields."""

    age_minimum: int
    age_maximum: int
    apparent_age_minimum: int
    apparent_age_maximum: int


@dataclass(frozen=True)
class RaceOptionView:
    """One custom-form race option with its registry description.

    ``subraces`` is ``None`` when the race has no subraces, otherwise a tuple
    of the race's subrace registry keys in registry order.
    """

    key: str
    description: str
    subraces: tuple[str, ...] | None


@dataclass(frozen=True)
class SubraceView:
    """One custom-form subrace preview derived from the immutable registry."""

    display_name_zh: str
    common_name_zh: str
    specialty: str


@dataclass(frozen=True)
class AllocationAxisView:
    """One allocatable starting axis with its exact bounds and explanation."""

    axis: str
    label: str
    explanation: str
    minimum: int
    maximum: int


@dataclass(frozen=True)
class ProfileView:
    """One (race, subrace) starting profile with budget and allocation axes."""

    race: str
    subrace: str | None
    budget: int
    axes: tuple[AllocationAxisView, ...]


@dataclass(frozen=True)
class CustomFormView:
    """The complete custom-form descriptor built from immutable registries."""

    name: NameBoundsView
    adult: AdultBoundsView
    races: tuple[RaceOptionView, ...]
    subraces: dict[str, SubraceView]
    profiles: tuple[ProfileView, ...]


@dataclass(frozen=True)
class CreationView:
    """The complete frozen read-only creation view for a pending character.

    ``draft`` is the normalized current staging draft (``None`` when absent or
    unreadable); a corrupt draft never fabricates a value and degrades only the
    draft slot.
    """

    presets: tuple[PresetCardView, ...]
    custom: CustomFormView
    draft: dict[str, Any] | None


def _axis_views(race_key: str, subrace_key: str | None) -> tuple[AllocationAxisView, ...]:
    profile = resolve_starting_profile(race_key, subrace_key)
    views: list[AllocationAxisView] = []
    for axis, (lower, upper) in profile.bounds:
        views.append(
            AllocationAxisView(
                axis=axis,
                label=ALLOCATION_AXIS_LABELS.get(axis, axis),
                explanation=ALLOCATION_AXIS_EXPLANATIONS.get(axis, ""),
                minimum=0,
                maximum=upper - lower,
            )
        )
    return tuple(views)


def build_preset_cards() -> tuple[PresetCardView, ...]:
    """Compose preset cards from the immutable preset and race registries."""
    cards: list[PresetCardView] = []
    for key in PLAYER_PRESET_REGISTRY:
        preset = PLAYER_PRESET_REGISTRY[key]
        race = RACE_REGISTRY[preset.race]
        cards.append(
            PresetCardView(
                key=preset.key,
                display_name=preset.display_name,
                race=preset.race,
                race_description=race.description,
                subrace=preset.subrace,
                emphasis=preset.emphasis,
                background=preset.background,
            )
        )
        if len(cards) >= MAX_PRESETS:
            break
    return tuple(cards)


def _race_option(race_key: str) -> RaceOptionView:
    race = RACE_REGISTRY[race_key]
    subrace_keys = tuple(
        key for key, subrace in SUBRACE_REGISTRY.items() if subrace.race_key == race_key
    )
    return RaceOptionView(
        key=race.key,
        description=race.description,
        subraces=subrace_keys if subrace_keys else None,
    )


def _profiles() -> tuple[ProfileView, ...]:
    profiles: list[ProfileView] = []
    for race_key in RACE_REGISTRY:
        subrace_keys = tuple(
            key for key, subrace in SUBRACE_REGISTRY.items() if subrace.race_key == race_key
        )
        for subrace_key in (None,) + subrace_keys:
            profile = resolve_starting_profile(race_key, subrace_key)
            profiles.append(
                ProfileView(
                    race=race_key,
                    subrace=subrace_key,
                    budget=profile.budget,
                    axes=_axis_views(race_key, subrace_key),
                )
            )
            if len(profiles) >= MAX_PROFILES:
                return tuple(profiles)
    return tuple(profiles)


def build_custom_form() -> CustomFormView:
    """Compose the custom-form descriptor entirely from immutable registries."""
    races: list[RaceOptionView] = []
    subraces: dict[str, SubraceView] = {}
    for race_key in RACE_REGISTRY:
        races.append(_race_option(race_key))
        if len(races) >= MAX_RACES:
            break
    for key in SUBRACE_REGISTRY:
        subrace = SUBRACE_REGISTRY[key]
        subraces[key] = SubraceView(
            display_name_zh=subrace.display_name_zh,
            common_name_zh=subrace.common_name_zh,
            specialty=subrace.specialty,
        )
        if len(subraces) >= MAX_SUBRACES:
            break
    return CustomFormView(
        name=NameBoundsView(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH),
        adult=AdultBoundsView(
            age_minimum=AGE_MINIMUM,
            age_maximum=AGE_MAXIMUM,
            apparent_age_minimum=APPARENT_AGE_MINIMUM,
            apparent_age_maximum=APPARENT_AGE_MAXIMUM,
        ),
        races=tuple(races),
        subraces=subraces,
        profiles=_profiles(),
    )


def read_creation_view(character: Any) -> CreationView:
    """Build the frozen no-mutation creation view for a pending character.

    The builder performs no writes, never materializes a lazy trait handler,
    never reads ``disguised_stats`` or persona, and never advances the world
    clock. A corrupt draft degrades only the draft slot.
    """
    return CreationView(
        presets=build_preset_cards(),
        custom=build_custom_form(),
        draft=read_draft(character),
    )


def _normalize_draft(storage: Any) -> dict[str, Any] | None:
    """Return a structurally and semantically valid normalized draft or ``None``.

    Accepts any Mapping (Evennia returns lazy ``_SaverDict`` wrappers from the
    attribute store, not plain ``dict`` instances). A draft that fails its
    structural shape OR its semantic bounds (unknown preset, underage, unknown
    or incompatible race/subrace, malformed allocations) is treated as corrupt
    and degrades only the draft slot so the creation panel stays schema-valid.
    """
    if not isinstance(storage, Mapping) or storage.get("version") != DRAFT_VERSION:
        return None
    mode = storage.get("mode")
    if mode == "preset":
        stage = storage.get("stage")
        preset_key = storage.get("preset_key")
        if stage != PRESET_STAGE or not isinstance(preset_key, str) or not preset_key:
            return None
        if preset_key not in PLAYER_PRESET_REGISTRY:
            return None
        return {"mode": "preset", "stage": stage, "preset_key": preset_key}
    if mode == "custom":
        stage = storage.get("stage")
        display_name = storage.get("display_name")
        age = storage.get("age")
        apparent_age = storage.get("apparent_age")
        race = storage.get("race")
        subrace = storage.get("subrace")
        allocations = storage.get("allocations")
        if (
            stage != CUSTOM_STAGE
            or not isinstance(display_name, str)
            or isinstance(age, bool)
            or not isinstance(age, int)
            or isinstance(apparent_age, bool)
            or not isinstance(apparent_age, int)
            or not isinstance(race, str)
            or not (subrace is None or isinstance(subrace, str))
            or not isinstance(allocations, Mapping)
        ):
            return None
        if age < AGE_MINIMUM or age > AGE_MAXIMUM:
            return None
        if apparent_age < APPARENT_AGE_MINIMUM or apparent_age > APPARENT_AGE_MAXIMUM:
            return None
        if race not in RACE_REGISTRY:
            return None
        if subrace is not None:
            entry = SUBRACE_REGISTRY.get(subrace)
            if entry is None or entry.race_key != race:
                return None
        if set(allocations) != set(ALLOCATABLE_AXES):
            return None
        checked_allocations: dict[str, int] = {}
        for axis in ALLOCATABLE_AXES:
            value = allocations.get(axis)
            if isinstance(value, bool) or not isinstance(value, int):
                return None
            if not 0 <= value <= ALLOCATION_MAXIMUM:
                return None
            checked_allocations[axis] = value
        return {
            "mode": "custom",
            "stage": stage,
            "display_name": display_name,
            "age": age,
            "apparent_age": apparent_age,
            "race": race,
            "subrace": subrace,
            "allocations": checked_allocations,
        }
    return None


def read_draft(character: Any) -> dict[str, Any] | None:
    """Return the normalized staging draft for ``character`` or ``None``.

    Read-only: never mutates the character. A missing or corrupt draft returns
    ``None`` so the read model stays schema-valid.
    """
    storage = getattr(character, "creation_draft", None)
    return _normalize_draft(storage)


def _write_draft(character: Any, storage: dict[str, Any]) -> None:
    character.db.creation_draft = storage


def _request_from_draft(draft: dict[str, Any]) -> CharacterCreationRequest:
    if draft["mode"] == "preset":
        return CharacterCreationRequest(mode="preset", preset_key=draft["preset_key"])
    return CharacterCreationRequest(
        mode="custom",
        display_name=draft["display_name"],
        age=draft["age"],
        apparent_age=draft["apparent_age"],
        race=draft["race"],
        subrace=draft["subrace"],
        allocations=dict(draft["allocations"]),
    )


def save_preset_draft(account: Any, character: Any, preset_key: str) -> dict[str, Any]:
    """Validate and persist the ``preset_selected`` staging draft.

    Re-runs the existing public ``preflight_character_creation`` for the preset
    so the adult gate, registry membership, name rules, and allocation bounds
    are authoritative before any value is persisted. The character remains
    pending and no canonical identity or trait value changes.
    """
    request = CharacterCreationRequest(mode="preset", preset_key=preset_key)
    preflight_character_creation(account, character, request)
    _write_draft(
        character,
        {"version": DRAFT_VERSION, "mode": "preset", "stage": PRESET_STAGE, "preset_key": preset_key},
    )
    return read_draft(character)


def save_custom_draft(
    account: Any, character: Any, request: CharacterCreationRequest
) -> dict[str, Any]:
    """Validate the complete custom request and persist the ``custom_filled`` draft.

    The request must already be ``mode="custom"``; the existing public
    ``preflight_character_creation`` validates ownership, pending state, the
    adult gate, registry membership, name rules, allocation bounds, and budget
    before the draft is written. The trimmed server-accepted display name is
    persisted; no canonical identity or trait value changes.
    """
    if request.mode != "custom":
        raise CharacterCreationError("creation mode must be 'preset' or 'custom'")
    validated = preflight_character_creation(account, character, request)
    _write_draft(
        character,
        {
            "version": DRAFT_VERSION,
            "mode": "custom",
            "stage": CUSTOM_STAGE,
            "display_name": validated.display_name,
            "age": validated.age,
            "apparent_age": validated.apparent_age,
            "race": validated.race,
            "subrace": validated.subrace,
            "allocations": dict(request.allocations),
        },
    )
    return read_draft(character)


def clear_draft(character: Any) -> None:
    """Idempotently clear the staging draft; the character stays pending."""
    if character.attributes.has("creation_draft"):
        character.attributes.remove("creation_draft")


def activate_draft(
    account: Any,
    character: Any,
    *,
    sampler: Callable[[int, int], int] | None = None,
    write_observer: Callable[[str], None] | None = None,
):
    """Atomically activate the stored draft and clear it in one transaction.

    One deterministic ``transaction.atomic()`` block: the stored draft is
    re-read and re-validated through the existing ``preflight_character_creation``
    (which re-checks ownership and ``creation_pending`` against committed
    state), ``activate_player_character`` writes the all-or-nothing activation
    and clears the draft in the same transaction, and the block commits only
    when both succeed. An injected write failure (``write_observer`` stage
    ``creation_draft``) rolls the whole transaction back, leaving the shell
    pending with its prior draft and trait state. Evennia's in-process
    attribute/trait caches are snapshotted up front and restored on any
    exception so no caller serves a stale read after a rollback. Returns the
    :class:`world.rules.character_creation.CharacterCreationResult`.

    Concurrency is bounded exactly-once by Evennia's single-threaded Twisted
    reactor, the dispatcher's one-in-flight-per-session rule, and the pending
    re-check inside the transaction: the first commit flips ``creation_pending``
    to false and clears the draft, and any later admission for the same shell
    fails its pending re-check rather than double-applying.
    """
    old_key = character.key
    attribute_snapshots = snapshot_attributes(
        character, _CREATION_ATTRIBUTE_KEYS + ("creation_draft",)
    )
    trait_snapshot = snapshot_traits(character)
    try:
        with transaction.atomic():
            if not bool(getattr(character, "creation_pending", False)):
                # A character activated between render and submit is rejected as
                # already complete regardless of whether a stale draft remains.
                raise CharacterCreationError("character creation is already complete")
            draft = read_draft(character)
            if draft is None:
                raise CharacterCreationError("no creation draft saved")
            request = _request_from_draft(draft)
            preflight_character_creation(account, character, request)
            if sampler is None:
                result = activate_player_character(
                    account, character, request, write_observer=write_observer
                )
            else:
                result = activate_player_character(
                    account, character, request,
                    sampler=sampler, write_observer=write_observer,
                )
    except Exception:
        character.key = old_key
        restore_traits(character, trait_snapshot)
        restore_attributes(character, attribute_snapshots)
        raise
    return result


__all__ = [
    "AGE_MAXIMUM",
    "AGE_MINIMUM",
    "ALLOCATION_MAXIMUM",
    "ALLOCATION_AXIS_EXPLANATIONS",
    "ALLOCATION_AXIS_LABELS",
    "APPARENT_AGE_MAXIMUM",
    "APPARENT_AGE_MINIMUM",
    "AdultBoundsView",
    "AllocationAxisView",
    "CreationView",
    "CustomFormView",
    "CUSTOM_STAGE",
    "DRAFT_VERSION",
    "MAX_PRESETS",
    "MAX_PROFILES",
    "MAX_RACES",
    "MAX_SUBRACES",
    "NAME_MAX_LENGTH",
    "NAME_MIN_LENGTH",
    "PRESET_STAGE",
    "PresetCardView",
    "ProfileView",
    "RaceOptionView",
    "SubraceView",
    "activate_draft",
    "build_custom_form",
    "build_preset_cards",
    "clear_draft",
    "read_creation_view",
    "read_draft",
    "save_custom_draft",
    "save_preset_draft",
]
