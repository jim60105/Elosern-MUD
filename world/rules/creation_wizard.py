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
import json
from typing import Any

from django.db import transaction

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    _CREATION_ATTRIBUTE_KEYS,
    _owned_character,
    MAX_PERSONA_FIELD_LENGTH,
    PERSONA_PROSE_KEYS,
    CharacterCreationError,
    CharacterCreationRequest,
    _validate_allocations,
    _validate_persona_block,
    activate_player_character,
    max_affinity_elements,
    preflight_character_creation,
    resolve_starting_profile,
    validate_affinity_elements,
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
CONCEPT_STAGE = "concept_filled"


class ConceptDraftStaleError(CharacterCreationError):
    """The draft fingerprint changed while the concept proposal was in flight.

    Raised by :func:`apply_concept_proposal` when the fingerprint captured
    before the generative call no longer matches the stored draft, so a late
    generative response can never overwrite a draft changed by another session
    or entry (creation-persona-persistence D2).
    """

# Presentation bounds shared with the wire presenter (web.webclient.
# presentation.creation) and the JS validator; the registries today are far
# smaller, so these are structural ceilings that must never bind real data.
MAX_PRESETS = 8
MAX_RACES = 8
MAX_SUBRACES = 16
MAX_PROFILES = 16

# Custom-form bounds (design D2): identical to the command wizard's name rules
# and the deterministic adult gate. The display-name bound mirrors the shared
# entity-key contract (fix-import-key-validity D3) so the panel's advertised
# maximum never exceeds what `_validate_name` accepts.
NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 64
AGE_MINIMUM = 18
AGE_MAXIMUM = 10000
APPARENT_AGE_MINIMUM = 18
APPARENT_AGE_MAXIMUM = 10000
ALLOCATION_MAXIMUM = 10000
# Stable Traditional Chinese axis labels and player-facing explanations for the
# seven allocatable starting axes. Presentation text only; the numeric authority
# lives in ``resolve_starting_profile``.
ALLOCATION_AXIS_LABELS: dict[str, str] = {
    "hp": "生命值",
    "mp": "魔力值",
    "sp": "體力值",
    "atk_phys": "物理攻擊",
    "agility": "敏捷",
    "defense": "防禦",
    "magic_power": "魔力",
}
ALLOCATION_AXIS_EXPLANATIONS: dict[str, str] = {
    "hp": "生命值，決定你能承受多少傷害",
    "mp": "魔力值，驅動魔法的消耗",
    "sp": "體力值，支撐行動與攻擊",
    "atk_phys": "物理攻擊，影響造成的傷害",
    "agility": "敏捷，影響命中與迴避",
    "defense": "防禦，減免受到的傷害",
    "magic_power": "魔力，決定魔法傷害與治療強度",
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
class AffinityElementView:
    """One element choice in the affinity picker."""

    key: str
    label: str


@dataclass(frozen=True)
class RaceAffinityBoundsView:
    """The player-input affinity bound for one race (D3/D4)."""

    maximum: int
    elements: tuple[AffinityElementView, ...]


@dataclass(frozen=True)
class AffinityView:
    """The affinity picker descriptor derived from the race bound mapping.

    Maps each race key (``human``, ``beastfolk``, ``elf``) to exactly
    ``max_affinity_elements(race_key)`` (2/1/0) and the eight lore element
    choices from ``ELEMENT_REGISTRY``.
    """

    bounds: dict[str, RaceAffinityBoundsView]


@dataclass(frozen=True)
class CustomFormView:
    """The complete custom-form descriptor built from immutable registries."""

    name: NameBoundsView
    adult: AdultBoundsView
    races: tuple[RaceOptionView, ...]
    subraces: dict[str, SubraceView]
    profiles: tuple[ProfileView, ...]
    affinity: AffinityView


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
        for subrace_key in subrace_keys:
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


def _affinity_view() -> AffinityView:
    """Compose the affinity picker descriptor from the race bound mapping."""
    element_choices = tuple(
        AffinityElementView(
            key=element.key, label=element.display_name_zh
        )
        for element in ELEMENT_REGISTRY.values()
    )
    bounds = {
        race_key: RaceAffinityBoundsView(
            maximum=max_affinity_elements(race_key),
            elements=element_choices,
        )
        for race_key in RACE_REGISTRY
    }
    return AffinityView(bounds)


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
        affinity=_affinity_view(),
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


def _normalize_allocations(allocations: Any) -> dict[str, int] | None:
    """Return the structurally checked allocation dict or ``None``."""
    if not isinstance(allocations, Mapping) or set(allocations) != set(ALLOCATABLE_AXES):
        return None
    checked_allocations: dict[str, int] = {}
    for axis in ALLOCATABLE_AXES:
        value = allocations.get(axis)
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        if not 0 <= value <= ALLOCATION_MAXIMUM:
            return None
        checked_allocations[axis] = value
    return checked_allocations


def _normalize_persona(persona: Any) -> dict[str, str] | None:
    """Return the validated persona block or ``None`` when malformed."""
    try:
        return _validate_persona_block(persona)
    except CharacterCreationError:
        return None


def _normalize_background(background: Any) -> str | None:
    """Return the bounded trimmed background text or ``None`` when malformed.

    A blank value normalizes to ``None`` (the key is simply omitted); a
    non-string or over-bound value is malformed and degrades the draft.
    """
    if background is None:
        return None
    if not isinstance(background, str):
        return None
    text = background.strip()
    if not text:
        return None
    if len(text) > MAX_PERSONA_FIELD_LENGTH:
        return None
    return text


def _normalize_affinity(affinity: Any, race_key: str) -> list[str] | None:
    """Return the validated affinity-element list or ``None`` when malformed.

    A missing value normalizes to an empty list; an unknown element, duplicate,
    or race-bound violation (human 2 / beastfolk 1 / elf none) degrades the
    draft so an invalid set can never be persisted.
    """
    if affinity is None:
        return []
    try:
        return list(validate_affinity_elements(affinity, race_key))
    except CharacterCreationError:
        return None


def _normalize_identity_choices(race: Any, subrace: Any) -> bool:
    """True when the stored race/subrace pair is registered and compatible.

    Subrace is required on every creation path now that every race has at
    least one registered subrace; a custom/concept draft without one is
    corrupt.
    """
    if not isinstance(race, str) or not isinstance(subrace, str):
        return False
    if race not in RACE_REGISTRY:
        return False
    entry = SUBRACE_REGISTRY.get(subrace)
    if entry is None or entry.race_key != race:
        return False
    return True


def _normalize_draft(storage: Any) -> dict[str, Any] | None:
    """Return a structurally and semantically valid normalized draft or ``None``.

    Accepts any Mapping (Evennia returns lazy ``_SaverDict`` wrappers from the
    attribute store, not plain ``dict`` instances). A draft that fails its
    structural shape OR its semantic bounds (unknown preset, underage, unknown
    or incompatible race/subrace, malformed allocations, malformed persona
    block) is treated as corrupt and degrades only the draft slot so the
    creation panel stays schema-valid.
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
        if (
            stage != CUSTOM_STAGE
            or not isinstance(display_name, str)
            or isinstance(age, bool)
            or not isinstance(age, int)
            or isinstance(apparent_age, bool)
            or not isinstance(apparent_age, int)
        ):
            return None
        if age < AGE_MINIMUM or age > AGE_MAXIMUM:
            return None
        if apparent_age < APPARENT_AGE_MINIMUM or apparent_age > APPARENT_AGE_MAXIMUM:
            return None
        if not _normalize_identity_choices(storage.get("race"), storage.get("subrace")):
            return None
        checked_allocations = _normalize_allocations(storage.get("allocations"))
        if checked_allocations is None:
            return None
        affinity_elements = _normalize_affinity(
            storage.get("affinity_elements"), storage["race"]
        )
        if affinity_elements is None:
            return None
        normalized: dict[str, Any] = {
            "mode": "custom",
            "stage": stage,
            "display_name": display_name,
            "age": age,
            "apparent_age": apparent_age,
            "race": storage["race"],
            "subrace": storage["subrace"],
            "allocations": checked_allocations,
        }
        if affinity_elements:
            normalized["affinity_elements"] = affinity_elements
        if "background" in storage:
            background = _normalize_background(storage["background"])
            if background is None:
                return None
            normalized["background"] = background
        if "persona" in storage:
            persona = _normalize_persona(storage["persona"])
            if persona is None:
                return None
            normalized["persona"] = persona
        return normalized
    if mode == "concept":
        stage = storage.get("stage")
        if stage != CONCEPT_STAGE:
            return None
        if not _normalize_identity_choices(storage.get("race"), storage.get("subrace")):
            return None
        checked_allocations = _normalize_allocations(storage.get("allocations"))
        if checked_allocations is None:
            return None
        normalized = {
            "mode": "concept",
            "stage": stage,
            "race": storage["race"],
            "subrace": storage.get("subrace"),
            "allocations": checked_allocations,
        }
        if "background" in storage:
            background = _normalize_background(storage["background"])
            if background is None:
                return None
            normalized["background"] = background
        if "persona" in storage:
            persona = _normalize_persona(storage["persona"])
            if persona is None:
                return None
            normalized["persona"] = persona
        return normalized
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


def draft_fingerprint(character: Any) -> str:
    """Return a deterministic fingerprint of the character's current draft.

    Built from the normalized draft so two drafts with the same accepted
    values always share one fingerprint and any change (save, clear, or
    persona-preserving custom save) produces a different one. The fingerprint
    is captured before a generative call and compared inside
    :func:`apply_concept_proposal`'s transaction (creation-persona-persistence
    D2); ``"absent"`` is the stable marker for a missing draft.
    """
    draft = read_draft(character)
    if draft is None:
        return "absent"
    return json.dumps(draft, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def apply_concept_proposal(
    account: Any,
    character: Any,
    proposal: Mapping[str, Any],
    *,
    expected_fingerprint: str,
) -> dict[str, Any]:
    """Validate a concept proposal and save the ``concept_filled`` draft.

    The proposal is a plain-data mapping with exactly ``race_key``,
    ``subrace_key``, ``allocations``, and ``persona`` (the validated persona
    block; may be omitted for a draft without persona). The proposal is
    re-validated deterministically -- race/subrace registry membership and
    compatibility plus in-band allocations through the same preflight checks,
    and the persona block's exact three-field bounded shape -- before anything
    is written. The draft is saved inside one ``transaction.atomic()`` block
    that compares ``draft_fingerprint(character)`` to the fingerprint captured
    before the generative call; a mismatch raises
    :class:`ConceptDraftStaleError` and writes nothing, so a late response can
    never clobber a draft changed by another session or entry while the call
    was in flight. Returns the normalized saved draft.
    """
    if not isinstance(proposal, Mapping) or set(proposal) != {
        "race_key", "subrace_key", "allocations", "persona",
    }:
        raise CharacterCreationError("concept proposal carries unexpected fields")
    if account is None or not _owned_character(account, character):
        raise CharacterCreationError("character is not owned by this account")
    if not bool(getattr(character, "creation_pending", False)):
        raise CharacterCreationError("character creation is already complete")
    race_key = proposal["race_key"]
    subrace_key = proposal["subrace_key"]
    if not isinstance(race_key, str) or not race_key:
        raise CharacterCreationError("race must be a registry key")
    if not isinstance(subrace_key, str) or not subrace_key:
        raise CharacterCreationError("subrace must be a registered registry key")
    profile = resolve_starting_profile(race_key, subrace_key)
    checked_allocations = _validate_allocations(profile, proposal["allocations"])
    persona_block = None
    if proposal["persona"] is not None:
        persona_block = _validate_persona_block(proposal["persona"])
    storage: dict[str, Any] = {
        "version": DRAFT_VERSION,
        "mode": "concept",
        "stage": CONCEPT_STAGE,
        "race": race_key,
        "subrace": subrace_key,
        "allocations": checked_allocations,
    }
    if persona_block is not None:
        storage["persona"] = persona_block
    with transaction.atomic():
        if draft_fingerprint(character) != expected_fingerprint:
            raise ConceptDraftStaleError("concept draft fingerprint changed")
        # The concept-apply service never overwrites a player-authored
        # background: a custom draft's accepted background survives the apply
        # so the journey (background, then concept, then custom save, then
        # activation) keeps the text at every step
        # (creation-persona-persistence D4).
        previous = _normalize_draft(getattr(character, "creation_draft", None))
        if (
            previous is not None
            and previous.get("mode") == "custom"
            and previous.get("background") is not None
        ):
            storage["background"] = previous["background"]
        _write_draft(character, storage)
    return read_draft(character)


def _request_from_draft(draft: dict[str, Any]) -> CharacterCreationRequest:
    if draft["mode"] == "preset":
        return CharacterCreationRequest(mode="preset", preset_key=draft["preset_key"])
    if draft["mode"] != "custom":
        # A concept stage never carries the display name and both ages the
        # activation preflight requires; it can only be completed through a
        # custom save, never activated directly (creation-persona-persistence
        # D1).
        raise CharacterCreationError("creation draft is incomplete")
    return CharacterCreationRequest(
        mode="custom",
        display_name=draft["display_name"],
        age=draft["age"],
        apparent_age=draft["apparent_age"],
        race=draft["race"],
        subrace=draft["subrace"],
        allocations=dict(draft["allocations"]),
        background=draft.get("background"),
        affinity_elements=tuple(draft.get("affinity_elements") or ()),
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

    A custom save preserves the concept draft's server-owned persona block only
    when the submitted race equals the concept draft's race -- the generated
    background still fits -- and clears it otherwise
    (creation-persona-persistence D1).
    """
    if request.mode != "custom":
        raise CharacterCreationError("creation mode must be 'preset' or 'custom'")
    validated = preflight_character_creation(account, character, request)
    persona_block = None
    previous = read_draft(character)
    if previous is not None and previous.get("mode") == "concept":
        if previous.get("race") == validated.race:
            persona_block = previous.get("persona")
    storage: dict[str, Any] = {
        "version": DRAFT_VERSION,
        "mode": "custom",
        "stage": CUSTOM_STAGE,
        "display_name": validated.display_name,
        "age": validated.age,
        "apparent_age": validated.apparent_age,
        "race": validated.race,
        "subrace": validated.subrace,
        "allocations": dict(request.allocations),
    }
    if validated.affinity_elements:
        storage["affinity_elements"] = list(validated.affinity_elements)
    if validated.background is not None:
        storage["background"] = validated.background
    if persona_block is not None:
        storage["persona"] = persona_block
    _write_draft(character, storage)
    return read_draft(character)


def clear_draft(character: Any) -> None:
    """Idempotently clear the staging draft; the character stays pending."""
    if character.attributes.has("creation_draft"):
        character.attributes.remove("creation_draft")


def activate_draft(
    account: Any,
    character: Any,
    *,
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
            persona = draft.get("persona")
            result = activate_player_character(
                account, character, request,
                persona=persona, write_observer=write_observer,
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
    "AffinityElementView",
    "AffinityView",
    "AllocationAxisView",
    "CONCEPT_STAGE",
    "ConceptDraftStaleError",
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
    "RaceAffinityBoundsView",
    "RaceOptionView",
    "SubraceView",
    "activate_draft",
    "apply_concept_proposal",
    "build_custom_form",
    "build_preset_cards",
    "clear_draft",
    "draft_fingerprint",
    "read_creation_view",
    "read_draft",
    "save_custom_draft",
    "save_preset_draft",
]
