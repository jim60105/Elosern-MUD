"""Exact schema-version-2 ``creation`` panel and presenter (webclient-character-creation-ui).

The presenter serializes the frozen no-mutation creation view owned by
``world.rules.creation_wizard`` and validates its own output against the exact
bounded schema (design D2) before returning it to the presentation registry.
Outside ``creation`` mode it raises :class:`PanelUnavailableError` so the
registry emits the common unavailable form; a failure confined to one preset,
profile, or the saved draft degrades only that entry while the panel stays
schema-valid. Version 2 carries the player-owned draft ``persona`` key and the
optional top-level transient concept ``proposal`` slot
(retool-concept-transient-fill); no skill, equipment, inventory, magic-level,
or import-only field is ever exposed.

The payload shape and the exact shared bounds are mirrored by the client
validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded by a
dual-direction parity test.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext, ProposalSnapshot
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.lore.elements import ELEMENT_REGISTRY
from world.rules.character_creation import (
    MAX_PERSONA_FIELD_LENGTH,
    max_affinity_elements,
)
from world.rules.creation_wizard import (
    CUSTOM_STAGE,
    PRESET_STAGE,
    AdultBoundsView,
    AffinityElementView,
    AffinityView,
    AllocationAxisView,
    CreationView,
    CustomFormView,
    PresetCardView,
    ProfileView,
    RaceAffinityBoundsView,
    RaceOptionView,
    SubraceView,
    read_creation_view,
)

CREATION_SCHEMA_VERSION = 2

# Exact shared bounds (design D2) -- must stay equal in the JS validator and to
# the creation-wizard view-builder caps (webclient-character-creation-ui D2).
MAX_PRESETS = 8
MAX_RACES = 8
MAX_SUBRACES = 16
MAX_PROFILES = 16
MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 64
AGE_MINIMUM = 18
AGE_MAXIMUM = 10000
APPARENT_AGE_MINIMUM = 18
APPARENT_AGE_MAXIMUM = 10000
MAX_PRESET_KEY_CODE_POINTS = 64
MAX_DISPLAY_NAME_CODE_POINTS = 128
MAX_RACE_KEY_CODE_POINTS = 64
MAX_DESCRIPTION_CODE_POINTS = 512
MAX_EMPHASIS_CODE_POINTS = 256
MAX_BACKGROUND_CODE_POINTS = 256
MAX_SUBRACE_KEY_CODE_POINTS = 64
MAX_SPECIALTY_CODE_POINTS = 256
MAX_LABEL_CODE_POINTS = 128
MAX_EXPLANATION_CODE_POINTS = 256
# The exact eight lore element choices and their Chinese labels. The bound
# mapping (human 2 / beastfolk 1 / elf 0) is derived from the deterministic
# ``max_affinity_elements`` so the panel cannot drift from custom creation.
AFFINITY_ELEMENT_KEYS = tuple(ELEMENT_REGISTRY)
MAX_AFFINITY_CHOICES = 8
MAX_AFFINITY_ELEMENTS = 8

ALLOCATABLE_AXES = ("hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power")

# The exact wire persona block keys (the three prose fields).
PERSONA_WIRE_KEYS = ("personality", "life_story", "habit")


class CreationPanelError(ProtocolValidationError):
    """The available creation payload violates its exact bounded schema."""


def _validate_key(value: Any, field: str, maximum: int) -> str:
    validated = _validate_identifier(value, field)
    if len(validated) > maximum:
        raise ProtocolValidationError(f"{field} exceeds its bound")
    return validated


def _validate_preset_card(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "preset card",
        {"key", "display_name", "race", "race_description", "subrace", "emphasis", "background"},
        {},
    )
    key = _validate_key(value["key"], "preset key", MAX_PRESET_KEY_CODE_POINTS)
    display_name = _require_str(
        value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS
    )
    if not display_name.strip():
        raise ProtocolValidationError("preset display_name must be non-empty")
    race = _validate_key(value["race"], "preset race", MAX_RACE_KEY_CODE_POINTS)
    race_description = _require_str(
        value, "race_description", maximum=MAX_DESCRIPTION_CODE_POINTS
    )
    if not race_description.strip():
        raise ProtocolValidationError("preset race_description must be non-empty")
    subrace = value["subrace"]
    if subrace is not None:
        subrace = _validate_key(subrace, "preset subrace", MAX_SUBRACE_KEY_CODE_POINTS)
    emphasis = _require_str(value, "emphasis", maximum=MAX_EMPHASIS_CODE_POINTS)
    if not emphasis.strip():
        raise ProtocolValidationError("preset emphasis must be non-empty")
    background = _require_str(value, "background", maximum=MAX_BACKGROUND_CODE_POINTS)
    if not background.strip():
        raise ProtocolValidationError("preset background must be non-empty")
    return {
        "key": key,
        "display_name": display_name,
        "race": race,
        "race_description": race_description,
        "subrace": subrace,
        "emphasis": emphasis,
        "background": background,
    }


def _validate_name(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "name bounds", {"min_length", "max_length"}, {})
    minimum = _require_int(value, "min_length", minimum=1, maximum=MAX_SAFE_INTEGER)
    maximum = _require_int(value, "max_length", minimum=1, maximum=MAX_SAFE_INTEGER)
    if minimum != MIN_NAME_LENGTH or maximum != MAX_NAME_LENGTH:
        raise ProtocolValidationError("name bounds do not match the advertised contract")
    return {"min_length": minimum, "max_length": maximum}


def _validate_adult(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "adult bounds",
        {"age_minimum", "age_maximum", "apparent_age_minimum", "apparent_age_maximum"},
        {},
    )
    age_minimum = _require_int(value, "age_minimum", minimum=1, maximum=MAX_SAFE_INTEGER)
    age_maximum = _require_int(value, "age_maximum", minimum=1, maximum=MAX_SAFE_INTEGER)
    apparent_minimum = _require_int(
        value, "apparent_age_minimum", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    apparent_maximum = _require_int(
        value, "apparent_age_maximum", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    if (
        age_minimum != AGE_MINIMUM
        or age_maximum != AGE_MAXIMUM
        or apparent_minimum != APPARENT_AGE_MINIMUM
        or apparent_maximum != APPARENT_AGE_MAXIMUM
    ):
        raise ProtocolValidationError("adult bounds do not match the advertised contract")
    if age_minimum > age_maximum or apparent_minimum > apparent_maximum:
        raise ProtocolValidationError("adult bounds minimum must not exceed maximum")
    return {
        "age_minimum": age_minimum,
        "age_maximum": age_maximum,
        "apparent_age_minimum": apparent_minimum,
        "apparent_age_maximum": apparent_maximum,
    }


def _validate_race_option(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "race option", {"key", "description", "subraces"}, {})
    key = _validate_key(value["key"], "race key", MAX_RACE_KEY_CODE_POINTS)
    description = _require_str(
        value, "description", maximum=MAX_DESCRIPTION_CODE_POINTS
    )
    if not description.strip():
        raise ProtocolValidationError("race description must be non-empty")
    subraces = value["subraces"]
    if subraces is not None:
        if not isinstance(subraces, list):
            raise ProtocolValidationError("race subraces must be a list or null")
        if len(subraces) > MAX_SUBRACES:
            raise ProtocolValidationError("race subraces exceeds its bound")
        subraces = [
            _validate_key(entry, "race subrace", MAX_SUBRACE_KEY_CODE_POINTS)
            for entry in subraces
        ]
    return {"key": key, "description": description, "subraces": subraces}


def _validate_subraces(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolValidationError("subraces must be an object")
    if len(value) > MAX_SUBRACES:
        raise ProtocolValidationError(f"subraces exceeds {MAX_SUBRACES} entries")
    normalized: dict[str, Any] = {}
    for key, entry in value.items():
        normalized_key = _validate_key(key, "subrace key", MAX_SUBRACE_KEY_CODE_POINTS)
        if not isinstance(entry, dict):
            raise ProtocolValidationError("subrace entry must be an object")
        _require_exact_fields(
            entry,
            "subrace entry",
            {"display_name_zh", "common_name_zh", "specialty"},
            {},
        )
        display_name_zh = _require_str(
            entry, "display_name_zh", maximum=MAX_SPECIALTY_CODE_POINTS
        )
        common_name_zh = _require_str(
            entry, "common_name_zh", maximum=MAX_SPECIALTY_CODE_POINTS
        )
        specialty = _require_str(entry, "specialty", maximum=MAX_SPECIALTY_CODE_POINTS)
        if not display_name_zh.strip() or not common_name_zh.strip() or not specialty.strip():
            raise ProtocolValidationError("subrace fields must be non-empty")
        normalized[normalized_key] = {
            "display_name_zh": display_name_zh,
            "common_name_zh": common_name_zh,
            "specialty": specialty,
        }
    return normalized


def _validate_axis(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "allocation axis",
        {"axis", "label", "explanation", "minimum", "maximum"},
        {},
    )
    axis = _validate_key(value["axis"], "axis", MAX_SUBRACE_KEY_CODE_POINTS)
    if axis not in ALLOCATABLE_AXES:
        raise ProtocolValidationError(f"axis {axis!r} is not an allocatable starting axis")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("axis label must be non-empty")
    explanation = _require_str(
        value, "explanation", maximum=MAX_EXPLANATION_CODE_POINTS
    )
    minimum = _require_int(value, "minimum", minimum=0, maximum=MAX_SAFE_INTEGER)
    maximum = _require_int(value, "maximum", minimum=0, maximum=MAX_SAFE_INTEGER)
    if minimum > maximum:
        raise ProtocolValidationError("axis minimum must not exceed maximum")
    return {
        "axis": axis,
        "label": label,
        "explanation": explanation,
        "minimum": minimum,
        "maximum": maximum,
    }


def _validate_profile(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "profile", {"race", "subrace", "budget", "axes"}, {})
    race = _validate_key(value["race"], "profile race", MAX_RACE_KEY_CODE_POINTS)
    subrace = value["subrace"]
    if subrace is not None:
        subrace = _validate_key(subrace, "profile subrace", MAX_SUBRACE_KEY_CODE_POINTS)
    budget = _require_int(value, "budget", minimum=0, maximum=MAX_SAFE_INTEGER)
    axes = value["axes"]
    if not isinstance(axes, list) or len(axes) != 7:
        raise ProtocolValidationError("profile axes must contain exactly seven axes")
    axis_keys = set()
    normalized_axes = []
    for entry in axes:
        normalized = _validate_axis(entry)
        axis_keys.add(normalized["axis"])
        normalized_axes.append(normalized)
    if axis_keys != set(ALLOCATABLE_AXES):
        raise ProtocolValidationError("profile axes must match the seven starting axes")
    return {"race": race, "subrace": subrace, "budget": budget, "axes": normalized_axes}


def _validate_custom(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "custom",
        {"name", "adult", "races", "subraces", "profiles", "affinity"},
        {},
    )
    name = _validate_name(value["name"])
    adult = _validate_adult(value["adult"])
    races = value["races"]
    if not isinstance(races, list) or len(races) > MAX_RACES:
        raise ProtocolValidationError(f"races must be a list of at most {MAX_RACES} options")
    races = [_validate_race_option(entry) for entry in races]
    if not races:
        raise ProtocolValidationError("races must not be empty")
    subraces = _validate_subraces(value["subraces"])
    profiles = value["profiles"]
    if not isinstance(profiles, list) or len(profiles) > MAX_PROFILES:
        raise ProtocolValidationError(
            f"profiles must be a list of at most {MAX_PROFILES} entries"
        )
    if not profiles:
        raise ProtocolValidationError("profiles must not be empty")
    profiles = [_validate_profile(entry) for entry in profiles]
    affinity = _validate_affinity(value["affinity"])
    return {
        "name": name,
        "adult": adult,
        "races": races,
        "subraces": subraces,
        "profiles": profiles,
        "affinity": affinity,
    }


def _validate_affinity_element(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "affinity element", {"key", "label"}, {})
    key = _validate_key(value["key"], "affinity key", MAX_SUBRACE_KEY_CODE_POINTS)
    if key not in AFFINITY_ELEMENT_KEYS:
        raise ProtocolValidationError(f"affinity key {key!r} is not a lore element")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("affinity element label must be non-empty")
    return {"key": key, "label": label}


def _validate_race_affinity(value: Any, race_key: str) -> dict[str, Any]:
    _require_exact_fields(value, f"affinity {race_key}", {"maximum", "elements"}, {})
    maximum = _require_int(value, "maximum", minimum=0, maximum=MAX_SAFE_INTEGER)
    if maximum != max_affinity_elements(race_key):
        raise ProtocolValidationError(
            f"affinity {race_key} maximum does not match the race bound"
        )
    elements = value["elements"]
    if not isinstance(elements, list) or not elements or len(elements) > MAX_AFFINITY_CHOICES:
        raise ProtocolValidationError("affinity elements must be a non-empty bounded list")
    element_keys = []
    normalized_elements = []
    for entry in elements:
        normalized = _validate_affinity_element(entry)
        element_keys.append(normalized["key"])
        normalized_elements.append(normalized)
    if set(element_keys) != set(AFFINITY_ELEMENT_KEYS):
        raise ProtocolValidationError(
            "affinity elements must be exactly the eight lore elements"
        )
    return {"maximum": maximum, "elements": normalized_elements}


def _validate_affinity(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolValidationError("affinity must be an object")
    if set(value) != set(("human", "beastfolk", "elf")):
        raise ProtocolValidationError("affinity must map human, beastfolk, and elf")
    normalized: dict[str, Any] = {}
    for race_key in ("human", "beastfolk", "elf"):
        normalized[race_key] = _validate_race_affinity(value[race_key], race_key)
    return normalized


def _validate_allocations(value: dict[str, Any], name: str) -> dict[str, Any]:
    allocations = value["allocations"]
    if not isinstance(allocations, dict) or set(allocations) != set(ALLOCATABLE_AXES):
        raise ProtocolValidationError(f"{name} allocations must contain exactly the seven axes")
    normalized_allocations: dict[str, int] = {}
    for axis in ALLOCATABLE_AXES:
        normalized_allocations[axis] = _require_int(
            allocations, axis, minimum=0, maximum=10000
        )
    return normalized_allocations


def _validate_affinity_elements(value: Any, race_key: str) -> list[str]:
    """Validate one draft affinity set against the race-dependent maximum.

    An absent value normalizes to ``[]``; a non-list, unknown element, or
    over-bound set degrades the draft so an invalid set never reaches the
    browser. Elf drafts always carry ``[]`` (the subrace seeds at activation).
    """
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProtocolValidationError("affinity_elements must be a list or null")
    if len(value) > MAX_AFFINITY_ELEMENTS:
        raise ProtocolValidationError("affinity_elements exceeds its bound")
    if race_key == "elf" and value:
        raise ProtocolValidationError(
            "an elf must not supply affinity_elements; the subrace is the authority"
        )
    maximum = max_affinity_elements(race_key)
    if len(value) > maximum:
        raise ProtocolValidationError(
            f"affinity_elements exceeds the {race_key} maximum of {maximum}"
        )
    checked = []
    for entry in value:
        if not isinstance(entry, str) or entry not in ELEMENT_REGISTRY:
            raise ProtocolValidationError(f"unknown affinity element {entry!r}")
        if entry in checked:
            raise ProtocolValidationError(f"duplicate affinity element {entry!r}")
        checked.append(entry)
    return checked


def _validate_background(value: Any) -> str | None:
    """Validate one nullable bounded background text field.

    A missing or blank value normalizes to ``None``; a non-string or
    over-bound value rejects. The bound mirrors ``MAX_PERSONA_FIELD_LENGTH`` so
    a validated draft always fits the persona-field contract.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProtocolValidationError("background must be text or null")
    text = value.strip()
    if not text:
        return None
    if sum(1 for _ in text) > MAX_PERSONA_FIELD_LENGTH:
        raise ProtocolValidationError("background exceeds its bound")
    return text


def _validate_draft(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ProtocolValidationError("draft must be a JSON object or null")
    mode = value.get("mode")
    if mode == "preset":
        _require_exact_fields(
            value,
            "preset draft",
            {"mode", "stage", "preset_key"},
            {},
        )
        if value["stage"] != PRESET_STAGE:
            raise ProtocolValidationError("unsupported preset draft stage")
        preset_key = _validate_key(
            value["preset_key"], "draft preset_key", MAX_PRESET_KEY_CODE_POINTS
        )
        return {"mode": "preset", "stage": PRESET_STAGE, "preset_key": preset_key}
    if mode == "custom":
        _require_exact_fields(
            value,
            "custom draft",
            {"mode", "stage", "display_name", "age", "apparent_age", "race", "subrace", "allocations", "background", "affinity_elements", "persona"},
            {},
        )
        if value["stage"] != CUSTOM_STAGE:
            raise ProtocolValidationError("unsupported custom draft stage")
        display_name = _require_str(
            value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS
        )
        if not display_name.strip():
            raise ProtocolValidationError("draft display_name must be non-empty")
        age = _require_int(value, "age", minimum=AGE_MINIMUM, maximum=AGE_MAXIMUM)
        apparent_age = _require_int(
            value, "apparent_age", minimum=APPARENT_AGE_MINIMUM, maximum=APPARENT_AGE_MAXIMUM
        )
        race = _validate_key(value["race"], "draft race", MAX_RACE_KEY_CODE_POINTS)
        subrace = _validate_key(value["subrace"], "draft subrace", MAX_SUBRACE_KEY_CODE_POINTS)
        background = _validate_background(value["background"])
        affinity_elements = _validate_affinity_elements(
            value["affinity_elements"], race
        )
        persona = _validate_persona(value["persona"])
        return {
            "mode": "custom",
            "stage": CUSTOM_STAGE,
            "display_name": display_name,
            "age": age,
            "apparent_age": apparent_age,
            "race": race,
            "subrace": subrace,
            "allocations": _validate_allocations(value, "custom draft"),
            "background": background,
            "affinity_elements": affinity_elements,
            "persona": persona,
        }
    raise ProtocolValidationError("draft has an unknown mode")


def _validate_persona(value: Any) -> dict[str, str] | None:
    """Validate one required nullable persona block on the wire.

    ``None`` is the explicit "no persona" value; any other value must carry
    exactly ``personality``, ``life_story``, and ``habit``, each a 1..600
    non-empty code-point string (retool-concept-transient-fill D2/D3).
    """
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != set(PERSONA_WIRE_KEYS):
        raise ProtocolValidationError(
            "persona must be null or carry exactly personality, life_story, and habit"
        )
    checked: dict[str, str] = {}
    for key in PERSONA_WIRE_KEYS:
        text = value[key]
        if not isinstance(text, str) or not text.strip():
            raise ProtocolValidationError(f"persona.{key} must be non-empty text")
        if sum(1 for _ in text) > MAX_PERSONA_FIELD_LENGTH:
            raise ProtocolValidationError(f"persona.{key} exceeds its bound")
        checked[key] = text
    return checked


def _validate_proposal(value: Any) -> dict[str, Any]:
    """Validate the optional top-level transient concept proposal.

    The proposal carries exactly ``revision`` (a positive transient sequence
    number), ``race``, nullable ``subrace``, the seven allocatable axes, and
    the three-field persona block (retool-concept-transient-fill D1).
    """
    _require_exact_fields(
        value, "proposal", {"revision", "race", "subrace", "allocations", "persona"}, {}
    )
    revision = _require_int(value, "revision", minimum=1, maximum=MAX_SAFE_INTEGER)
    race = _validate_key(value["race"], "proposal race", MAX_RACE_KEY_CODE_POINTS)
    subrace = value["subrace"]
    if subrace is not None:
        subrace = _validate_key(subrace, "proposal subrace", MAX_SUBRACE_KEY_CODE_POINTS)
    persona = _validate_persona(value["persona"])
    if persona is None:
        raise ProtocolValidationError("proposal persona must be a block")
    return {
        "revision": revision,
        "race": race,
        "subrace": subrace,
        "allocations": _validate_allocations(value, "proposal"),
        "persona": persona,
    }


def validate_creation(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``creation`` payload.

    Returns a normalized payload or raises :class:`CreationPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "creation panel",
        {"schema_version", "available", "kind", "draft", "presets", "custom"},
        {"proposal": "optional"},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != CREATION_SCHEMA_VERSION:
        raise CreationPanelError("unsupported creation schema_version")
    if not _require_bool(payload, "available"):
        raise CreationPanelError("available must be true for the creation form")
    if payload["kind"] != "creation":
        raise CreationPanelError("creation panel kind must be creation")

    draft = _validate_draft(payload["draft"])
    presets = payload["presets"]
    if not isinstance(presets, list) or len(presets) > MAX_PRESETS:
        raise ProtocolValidationError(f"presets must be a list of at most {MAX_PRESETS} cards")
    if not presets:
        raise ProtocolValidationError("presets must not be empty")
    presets = [_validate_preset_card(card) for card in presets]
    custom = _validate_custom(payload["custom"])

    result: dict[str, Any] = {
        "schema_version": CREATION_SCHEMA_VERSION,
        "available": True,
        "kind": "creation",
        "draft": draft,
        "presets": presets,
        "custom": custom,
    }
    if "proposal" in payload:
        # The proposal key is present only while the session slot holds a
        # proposal; a null value is never legal (the presenter omits the key).
        result["proposal"] = _validate_proposal(payload["proposal"])
    # Envelope guarantee (design D2): a conforming payload must serialize within
    # the OOB envelope limit. Per-field bounds are ceilings, not a guarantee
    # that any combination of them fits, so the validator enforces the
    # serialized size directly -- an all-ceilings payload fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise CreationPanelError("creation payload exceeds the OOB envelope limit")
    return result


# ---------------------------------------------------------------------------
# Serialization from the frozen read model.
# ---------------------------------------------------------------------------


def _serialize_preset_card(card: PresetCardView) -> dict[str, Any]:
    return {
        "key": card.key,
        "display_name": card.display_name,
        "race": card.race,
        "race_description": card.race_description,
        "subrace": card.subrace,
        "emphasis": card.emphasis,
        "background": card.background,
    }


def _serialize_name(name: Any) -> dict[str, Any]:
    return {"min_length": name.min_length, "max_length": name.max_length}


def _serialize_adult(adult: AdultBoundsView) -> dict[str, Any]:
    return {
        "age_minimum": adult.age_minimum,
        "age_maximum": adult.age_maximum,
        "apparent_age_minimum": adult.apparent_age_minimum,
        "apparent_age_maximum": adult.apparent_age_maximum,
    }


def _serialize_race_option(race: RaceOptionView) -> dict[str, Any]:
    return {
        "key": race.key,
        "description": race.description,
        "subraces": None if race.subraces is None else list(race.subraces),
    }


def _serialize_subraces(subraces: dict[str, SubraceView]) -> dict[str, Any]:
    return {
        key: {
            "display_name_zh": entry.display_name_zh,
            "common_name_zh": entry.common_name_zh,
            "specialty": entry.specialty,
        }
        for key, entry in subraces.items()
    }


def _serialize_axis(axis: AllocationAxisView) -> dict[str, Any]:
    return {
        "axis": axis.axis,
        "label": axis.label,
        "explanation": axis.explanation,
        "minimum": axis.minimum,
        "maximum": axis.maximum,
    }


def _serialize_profile(profile: ProfileView) -> dict[str, Any]:
    return {
        "race": profile.race,
        "subrace": profile.subrace,
        "budget": profile.budget,
        "axes": [_serialize_axis(axis) for axis in profile.axes],
    }


def _serialize_affinity_element(element: AffinityElementView) -> dict[str, Any]:
    return {"key": element.key, "label": element.label}


def _serialize_race_affinity(bounds: RaceAffinityBoundsView) -> dict[str, Any]:
    return {
        "maximum": bounds.maximum,
        "elements": [
            _serialize_affinity_element(element) for element in bounds.elements
        ],
    }


def _serialize_affinity(affinity: AffinityView) -> dict[str, Any]:
    return {
        race_key: _serialize_race_affinity(bounds)
        for race_key, bounds in affinity.bounds.items()
    }


def _serialize_custom(custom: CustomFormView) -> dict[str, Any]:
    return {
        "name": _serialize_name(custom.name),
        "adult": _serialize_adult(custom.adult),
        "races": [_serialize_race_option(race) for race in custom.races],
        "subraces": _serialize_subraces(custom.subraces),
        "profiles": [_serialize_profile(profile) for profile in custom.profiles],
        "affinity": _serialize_affinity(custom.affinity),
    }


def _serialize_draft(draft: dict[str, Any] | None) -> dict[str, Any] | None:
    if draft is None:
        return None
    if draft["mode"] == "preset":
        return {
            "mode": "preset",
            "stage": PRESET_STAGE,
            "preset_key": draft["preset_key"],
        }
    return {
        "mode": "custom",
        "stage": CUSTOM_STAGE,
        "display_name": draft["display_name"],
        "age": draft["age"],
        "apparent_age": draft["apparent_age"],
        "race": draft["race"],
        "subrace": draft["subrace"],
        "allocations": dict(draft["allocations"]),
        "background": draft.get("background"),
        "affinity_elements": list(draft.get("affinity_elements") or []),
        # The persona block is player-owned data (retool-concept-transient-
        # fill): the saved draft renders it so a reconnect resumes with the
        # player's own prose visible and editable.
        "persona": dict(draft["persona"]) if draft.get("persona") is not None else None,
    }


def _serialize_proposal(proposal: ProposalSnapshot | None) -> dict[str, Any] | None:
    if proposal is None:
        return None
    return proposal.as_dict()


def _serialize(
    view: CreationView, proposal: ProposalSnapshot | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": CREATION_SCHEMA_VERSION,
        "available": True,
        "kind": "creation",
        "draft": _serialize_draft(view.draft),
        "presets": [_serialize_preset_card(card) for card in view.presets],
        "custom": _serialize_custom(view.custom),
    }
    if proposal is not None:
        # The proposal key ships only while the session slot holds a snapshot
        # owned by the rendering puppet; it is never present as null
        # (retool-concept-transient-fill D1).
        payload["proposal"] = _serialize_proposal(proposal)
    return payload


def creation_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``creation`` panel for the authenticated puppet."""
    actor = context.actor
    if not bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    from world.rules.combat_session import is_in_active_session

    if is_in_active_session(actor):
        raise PanelUnavailableError
    view = read_creation_view(actor)
    return validate_creation(_serialize(view, context.proposal))


__all__ = [
    "AGE_MAXIMUM",
    "AGE_MINIMUM",
    "AFFINITY_ELEMENT_KEYS",
    "APPARENT_AGE_MAXIMUM",
    "APPARENT_AGE_MINIMUM",
    "ALLOCATABLE_AXES",
    "CREATION_SCHEMA_VERSION",
    "CreationPanelError",
    "MAX_AFFINITY_CHOICES",
    "MAX_AFFINITY_ELEMENTS",
    "MAX_BACKGROUND_CODE_POINTS",
    "MAX_DESCRIPTION_CODE_POINTS",
    "MAX_DISPLAY_NAME_CODE_POINTS",
    "MAX_EMPHASIS_CODE_POINTS",
    "MAX_EXPLANATION_CODE_POINTS",
    "MAX_LABEL_CODE_POINTS",
    "MAX_NAME_LENGTH",
    "MAX_PRESET_KEY_CODE_POINTS",
    "MAX_PRESETS",
    "MAX_PROFILES",
    "MAX_RACES",
    "MAX_RACE_KEY_CODE_POINTS",
    "MAX_SPECIALTY_CODE_POINTS",
    "MAX_SUBRACES",
    "MAX_SUBRACE_KEY_CODE_POINTS",
    "MIN_NAME_LENGTH",
    "PERSONA_WIRE_KEYS",
    "creation_presenter",
    "validate_creation",
]
