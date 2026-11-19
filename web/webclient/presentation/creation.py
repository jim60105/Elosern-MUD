"""Exact schema-version-8 ``creation`` panel and presenter (webclient-character-creation-ui).

The presenter serializes the frozen no-mutation creation view owned by
``world.rules.creation_wizard`` and validates its own output against the exact
bounded schema (design D2) before returning it to the presentation registry.
Outside ``creation`` mode it raises :class:`PanelUnavailableError` so the
registry emits the common unavailable form; a failure confined to one preset,
profile, or the saved draft degrades only that entry while the panel stays
schema-valid. Version 2 carries the player-owned draft ``persona`` key and the
optional top-level transient concept ``proposal`` slot
(retool-concept-transient-fill); no skill, equipment, inventory, magic-level,
or import-only field is ever exposed. Version 3 widened the transient
``proposal`` slot (bump-creation-panel-proposal-v3); version 4 adds the
server-labelled ``custom.sex`` option list and the required draft ``sex``
member (namegen-creation-ui); version 5 renames the ``custom.adult``
descriptor block to ``custom.age`` and drops the advertised minimums to 0
(age-range-0-10000); version 6 adds canonical race display names; version 7
adds each preset card's canonical ``artwork`` descriptor and the custom
form's ``silhouettes`` lookup table (creation-panel-artwork); version 8 adds
the required read-only ``portrait`` state union (creation-draft-portrait-panel).

The payload shape and the exact shared bounds are mirrored by the client
validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded by a
dual-direction parity test.
"""

from typing import Any

from web.webclient.presentation.artwork import validate_artwork
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
from web.webclient.presentation.protocol_validation import (
    validate_affinity_elements,
    validate_background,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.art import descriptors
from world.art.presenter import (
    CREATION_PRESET_SUBJECT_PREFIX,
    CREATION_SILHOUETTE_SUBJECT_PREFIX,
    draft_portrait_artwork,
    preset_artwork,
    silhouette_table,
)
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.sex import SEX_VALUES
from world.rules.character_creation import (
    MAX_PERSONA_FIELD_LENGTH,
    max_affinity_elements,
)
from world.rules.creation_messages import rejection_message
from world.rules.creation_portrait import (
    PORTRAIT_EMPTY,
    PORTRAIT_FAILED,
    PORTRAIT_PENDING,
    PORTRAIT_READY,
    PORTRAIT_STATE_UNAVAILABLE,
    PORTRAIT_UNAVAILABLE,
    DraftPortraitView,
    read_draft_portrait,
)
from world.rules.creation_wizard import (
    CUSTOM_NEEDS_ALLOCATION_STAGE,
    CUSTOM_STAGE,
    PRESET_STAGE,
    AffinityElementView,
    AffinityView,
    AgeBoundsView,
    AllocationAxisView,
    CreationView,
    CustomFormView,
    PresetCardView,
    ProfileView,
    RaceAffinityBoundsView,
    RaceOptionView,
    SubraceView,
    SexOptionView,
    read_creation_view,
)

# v6 adds canonical race display_name_zh to custom.races options and requires
# preset cards to resolve to custom.races (webclient-creation-display-labels).
# v7 adds each preset card's canonical ``artwork`` descriptor and the custom
# form's ``silhouettes`` lookup table (creation-panel-artwork); the mirrored
# JS validator moves together, so a stale v6 panel is rejected by the
# exact-schema gate on both ends.
# v8 adds the required read-only ``portrait`` state union
# (creation-draft-portrait-panel); v7 and every other version are rejected.
# v9 adds every allocation axis's ``point_cap`` and ``value_at_cap`` next to its
# lore bounds, and the ``custom_needs_allocation`` draft stage that reports a
# superseded custom-elf allocation as unallocated (elf-starting-stat-budget);
# the mirrored JS validator moves together, so v8 is rejected on both ends.
CREATION_SCHEMA_VERSION = 9

# Exact shared bounds (design D2) -- must stay equal in the JS validator and to
# the creation-wizard view-builder caps (webclient-character-creation-ui D2).
MAX_PRESETS = 8
MAX_RACES = 8
MAX_SUBRACES = 16
MAX_PROFILES = 16
MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 64
AGE_MINIMUM = 0
AGE_MAXIMUM = 10000
APPARENT_AGE_MINIMUM = 0
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
# The silhouette lookup table is bounded structurally; the advertised sex
# vocabulary and the three built-in bands keep a real table well under it.
MAX_SILHOUETTES = 16
# The sex option list mirrors ``SEX_VALUES`` exactly (at most one entry per
# member); the ceiling is a structural bound that must never bind real data.
MAX_SEX_OPTIONS = 8
# The portrait ``reason`` bound: nonblank server-owned prose, in code points.
MAX_PORTRAIT_REASON_CODE_POINTS = 512
# The exact eight lore element choices and their Chinese labels. The bound
# mapping (human 2 / beastfolk 1 / elf 0) is derived from the deterministic
# ``max_affinity_elements`` so the panel cannot drift from custom creation.
AFFINITY_ELEMENT_KEYS = tuple(ELEMENT_REGISTRY)
MAX_AFFINITY_CHOICES = 8
MAX_AFFINITY_ELEMENTS = 8

ALLOCATABLE_AXES = ("hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power")

# The exact wire persona block keys (the three prose fields).
PERSONA_WIRE_KEYS = ("personality", "life_story", "habit")
# The proposal transient-fill display-name bound (mirror of the generative
# layer's MAX_DISPLAY_NAME_CODE_POINTS and the custom-form name cap; distinct
# from the preset-card MAX_DISPLAY_NAME_CODE_POINTS above).
MAX_PROPOSAL_NAME_CODE_POINTS = 64


class CreationPanelError(ProtocolValidationError):
    """The available creation payload violates its exact bounded schema."""


def _validate_key(value: Any, field: str, maximum: int) -> str:
    validated = _validate_identifier(value, field)
    if len(validated) > maximum:
        raise ProtocolValidationError(f"{field} exceeds its bound")
    return validated


def _validate_preview_artwork_semantics(artwork: dict[str, Any], field: str) -> None:
    """Enforce a preview descriptor's closed non-generation facts.

    A creation preview is not a generated subject and carries no backend
    retention authorization, so both claims stay explicitly empty. The
    terminal is the built-in alpha mask, never a scene image.
    """
    if (
        artwork["generation_subject"] is not None
        or artwork["generation_state"] is not None
    ):
        raise ProtocolValidationError(f"{field} must claim no generation")
    if artwork["retention_sources"]:
        raise ProtocolValidationError(f"{field} must carry no retention")
    terminal = artwork["terminal"]
    if terminal is None or terminal["kind"] != descriptors.TERMINAL_ALPHA_MASK:
        raise ProtocolValidationError(f"{field} must carry an alpha terminal")
    resource = terminal["resource"]
    if (
        resource["origin"] != descriptors.ORIGIN_SILHOUETTE
        or not resource["url"].startswith("/art/defaults/")
    ):
        raise ProtocolValidationError(
            f"{field} terminal must name the built-in silhouette route"
        )


def _validate_preset_artwork(value: Any, preset_key: str) -> dict[str, Any]:
    """Validate one preset card's canonical artwork descriptor.

    Exactly the canonical seven-key descriptor whose stable subject id names
    the card it belongs to, carrying at most the card's own catalog default as
    an ``official`` image attempt and never a fault: an unadmitted preview
    default is normal absence, not a broken source.
    """
    artwork = validate_artwork(value)
    if artwork["subject_id"] != f"{CREATION_PRESET_SUBJECT_PREFIX}{preset_key}":
        raise ProtocolValidationError("preset artwork subject_id does not match the card")
    _validate_preview_artwork_semantics(artwork, "preset artwork")
    images = [attempt for attempt in artwork["attempts"] if attempt["type"] == "image"]
    if len(images) != len(artwork["attempts"]) or len(images) > 1:
        raise ProtocolValidationError(
            "preset artwork must carry at most one image attempt and no fault"
        )
    if images:
        resource = images[0]["resource"]
        if resource["origin"] != descriptors.ORIGIN_OFFICIAL:
            raise ProtocolValidationError("preset artwork attempt must be official")
        if not resource["url"].startswith("/art/official/"):
            raise ProtocolValidationError(
                "preset artwork attempt must name the official art route"
            )
    return artwork


def _validate_preset_card(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "preset card",
        {
            "key",
            "display_name",
            "race",
            "race_description",
            "subrace",
            "emphasis",
            "background",
            "artwork",
        },
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
    artwork = _validate_preset_artwork(value["artwork"], key)
    return {
        "key": key,
        "display_name": display_name,
        "race": race,
        "race_description": race_description,
        "subrace": subrace,
        "emphasis": emphasis,
        "background": background,
        "artwork": artwork,
    }


def _validate_name(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "name bounds", {"min_length", "max_length"}, {})
    minimum = _require_int(value, "min_length", minimum=1, maximum=MAX_SAFE_INTEGER)
    maximum = _require_int(value, "max_length", minimum=1, maximum=MAX_SAFE_INTEGER)
    if minimum != MIN_NAME_LENGTH or maximum != MAX_NAME_LENGTH:
        raise ProtocolValidationError("name bounds do not match the advertised contract")
    return {"min_length": minimum, "max_length": maximum}


def _validate_age(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "age bounds",
        {"age_minimum", "age_maximum", "apparent_age_minimum", "apparent_age_maximum"},
        {},
    )
    age_minimum = _require_int(value, "age_minimum", minimum=0, maximum=MAX_SAFE_INTEGER)
    age_maximum = _require_int(value, "age_maximum", minimum=0, maximum=MAX_SAFE_INTEGER)
    apparent_minimum = _require_int(
        value, "apparent_age_minimum", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    apparent_maximum = _require_int(
        value, "apparent_age_maximum", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    if (
        age_minimum != AGE_MINIMUM
        or age_maximum != AGE_MAXIMUM
        or apparent_minimum != APPARENT_AGE_MINIMUM
        or apparent_maximum != APPARENT_AGE_MAXIMUM
    ):
        raise ProtocolValidationError("age bounds do not match the advertised contract")
    if age_minimum > age_maximum or apparent_minimum > apparent_maximum:
        raise ProtocolValidationError("age bounds minimum must not exceed maximum")
    return {
        "age_minimum": age_minimum,
        "age_maximum": age_maximum,
        "apparent_age_minimum": apparent_minimum,
        "apparent_age_maximum": apparent_maximum,
    }


def _validate_race_option(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value, "race option", {"key", "display_name_zh", "description", "subraces"}, {}
    )
    display_name_zh = _require_str(
        value, "display_name_zh", maximum=MAX_DISPLAY_NAME_CODE_POINTS
    )
    if not display_name_zh.strip():
        raise ProtocolValidationError("race display_name_zh must be non-empty")
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
    return {
        "key": key,
        "display_name_zh": display_name_zh,
        "description": description,
        "subraces": subraces,
    }


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
        {
            "axis",
            "label",
            "explanation",
            "minimum",
            "maximum",
            "point_cap",
            "value_at_cap",
        },
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
    point_cap = _require_int(value, "point_cap", minimum=0, maximum=MAX_SAFE_INTEGER)
    value_at_cap = _require_int(
        value, "value_at_cap", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    # Point bounds are independent of the lore bounds the axis advertises: a
    # fixed gauge admits no points and stays at its floor, while an
    # interpolated axis (the custom elf's magic power) reaches ``value_at_cap``
    # somewhere inside its lore band.
    if not minimum <= value_at_cap <= maximum:
        raise ProtocolValidationError("axis value_at_cap must lie within its lore bounds")
    if point_cap == 0 and value_at_cap != minimum:
        raise ProtocolValidationError("axis value_at_cap must equal minimum for a zero cap")
    return {
        "axis": axis,
        "label": label,
        "explanation": explanation,
        "minimum": minimum,
        "maximum": maximum,
        "point_cap": point_cap,
        "value_at_cap": value_at_cap,
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


def _validate_silhouette_artwork(
    value: Any, sex: str, minimum: int, maximum: int
) -> dict[str, Any]:
    """Validate one silhouette entry's canonical alpha-only descriptor.

    Its stable subject id names the pending character position and the entry's
    own sex/interval, and the descriptor carries no attempt, no generation and
    no retention: the built-in alpha terminal is the only artwork it names.
    The actor segment is position-stable but not bound here: the panel payload
    carries no actor identity, so only its non-emptiness is checkable on the
    wire (the presenter computes it from the pending actor's pk).
    """
    artwork = validate_artwork(value)
    prefix = CREATION_SILHOUETTE_SUBJECT_PREFIX
    suffix = f":{sex}:{minimum}:{maximum}"
    subject_id = artwork["subject_id"]
    if not subject_id.startswith(prefix) or not subject_id.endswith(suffix):
        raise ProtocolValidationError(
            "silhouette artwork subject_id does not match the entry"
        )
    if not subject_id[len(prefix) : -len(suffix)]:
        raise ProtocolValidationError("silhouette artwork subject_id is empty")
    _validate_preview_artwork_semantics(artwork, "silhouette artwork")
    if artwork["attempts"]:
        raise ProtocolValidationError("silhouette artwork must carry no attempt")
    return artwork


def _validate_silhouettes(
    value: Any, sex_keys: list[str], age: dict[str, Any]
) -> list[dict[str, Any]]:
    """Validate the custom form's silhouette lookup table exactly.

    Every advertised sex carries a complete, gap-free partition of the
    advertised apparent-age range; an unknown sex, a gap, an overlap, an
    out-of-range or non-integer endpoint, and a malformed descriptor all
    reject the whole panel. Entries are returned grouped in the advertised sex
    order (each sex ordered by its interval) so the payload is deterministic.
    """
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SILHOUETTES:
        raise ProtocolValidationError(
            f"silhouettes must be a non-empty list of at most {MAX_SILHOUETTES} entries"
        )
    advertised = set(sex_keys)
    apparent_minimum = age["apparent_age_minimum"]
    apparent_maximum = age["apparent_age_maximum"]
    by_sex: dict[str, list[tuple[int, int, dict[str, Any]]]] = {}
    for entry in value:
        _require_exact_fields(
            entry,
            "silhouette entry",
            {"sex", "apparent_age_minimum", "apparent_age_maximum", "artwork"},
            {},
        )
        sex = _validate_key(entry["sex"], "silhouette sex", MAX_SUBRACE_KEY_CODE_POINTS)
        if sex not in advertised:
            raise ProtocolValidationError(
                f"silhouette sex {sex!r} is not an advertised sex option"
            )
        minimum = _require_int(
            entry,
            "apparent_age_minimum",
            minimum=apparent_minimum,
            maximum=apparent_maximum,
        )
        maximum = _require_int(
            entry,
            "apparent_age_maximum",
            minimum=apparent_minimum,
            maximum=apparent_maximum,
        )
        if minimum > maximum:
            raise ProtocolValidationError(
                "silhouette interval minimum must not exceed maximum"
            )
        artwork = _validate_silhouette_artwork(entry["artwork"], sex, minimum, maximum)
        by_sex.setdefault(sex, []).append((minimum, maximum, artwork))
    if set(by_sex) != advertised:
        raise ProtocolValidationError(
            "silhouettes must cover every advertised sex exactly once"
        )
    normalized: list[dict[str, Any]] = []
    for sex in sex_keys:
        intervals = sorted(by_sex[sex], key=lambda item: item[0])
        expected = apparent_minimum
        for minimum, maximum, artwork in intervals:
            if minimum != expected:
                raise ProtocolValidationError(
                    "silhouette intervals must be contiguous without gaps or overlaps"
                )
            expected = maximum + 1
            normalized.append(
                {
                    "sex": sex,
                    "apparent_age_minimum": minimum,
                    "apparent_age_maximum": maximum,
                    "artwork": artwork,
                }
            )
        if expected != apparent_maximum + 1:
            raise ProtocolValidationError(
                "silhouette intervals must cover the advertised apparent-age range"
            )
    return normalized


def _validate_custom(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "custom",
        {
            "name",
            "age",
            "races",
            "subraces",
            "profiles",
            "affinity",
            "sex",
            "silhouettes",
        },
        {},
    )
    name = _validate_name(value["name"])
    age = _validate_age(value["age"])
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
    sex = _validate_sex_options(value["sex"])
    silhouettes = _validate_silhouettes(
        value["silhouettes"], [option["key"] for option in sex], age
    )
    return {
        "name": name,
        "age": age,
        "races": races,
        "subraces": subraces,
        "profiles": profiles,
        "affinity": affinity,
        "sex": sex,
        "silhouettes": silhouettes,
    }


def _validate_sex_options(value: Any) -> list[dict[str, Any]]:
    """Validate the server-labelled sex option list (namegen-creation-ui D4).

    The list mirrors ``SEX_VALUES`` exactly -- one entry per member, registry
    order, each carrying exactly ``{key, label}`` with a non-empty label. The
    labels are server-owned Traditional Chinese prose; the browser renders
    them verbatim.
    """
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SEX_OPTIONS:
        raise ProtocolValidationError(
            f"sex must be a non-empty list of at most {MAX_SEX_OPTIONS} options"
        )
    options = []
    for entry in value:
        _require_exact_fields(entry, "sex option", {"key", "label"}, {})
        key = _validate_key(entry["key"], "sex key", MAX_SUBRACE_KEY_CODE_POINTS)
        label = _require_str(entry, "label", maximum=MAX_LABEL_CODE_POINTS)
        if not label.strip():
            raise ProtocolValidationError("sex label must be non-empty")
        options.append({"key": key, "label": label})
    if [option["key"] for option in options] != list(SEX_VALUES):
        raise ProtocolValidationError(
            "sex options must be exactly the sex vocabulary in registry order"
        )
    return options


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
    return validate_affinity_elements(
        value,
        race_key,
        ProtocolValidationError,
        empty_as_none=False,
        global_bound=MAX_AFFINITY_ELEMENTS,
    )


def _validate_background(value: Any) -> str | None:
    """Validate one nullable bounded background text field.

    A missing or blank value normalizes to ``None``; a non-string or
    over-bound value rejects. The bound mirrors ``MAX_PERSONA_FIELD_LENGTH`` so
    a validated draft always fits the persona-field contract.
    """
    return validate_background(
        value, ProtocolValidationError, MAX_PERSONA_FIELD_LENGTH
    )


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
            {"mode", "stage", "display_name", "age", "apparent_age", "race", "subrace", "allocations", "background", "affinity_elements", "persona", "sex"},
            {},
        )
        stage = value["stage"]
        if stage not in (CUSTOM_STAGE, CUSTOM_NEEDS_ALLOCATION_STAGE):
            raise ProtocolValidationError("unsupported custom draft stage")
        # The stage and the allocation slot are one exact pair: only a draft
        # whose policy was superseded reports no allocation, and such a draft
        # never carries points the browser could confirm.
        allocations = value["allocations"]
        if (stage == CUSTOM_NEEDS_ALLOCATION_STAGE) != (allocations is None):
            raise ProtocolValidationError(
                "custom draft stage and allocations do not pair"
            )
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
        # The draft stores the concrete normalized member (namegen-creation-
        # ui D2/D3): mirror the wizard normalizer's vocabulary gate so a
        # tampered stored sex value degrades the draft slot, not the panel.
        sex = value["sex"]
        if sex not in SEX_VALUES:
            raise ProtocolValidationError("draft sex is not a vocabulary member")
        return {
            "mode": "custom",
            "stage": stage,
            "display_name": display_name,
            "age": age,
            "apparent_age": apparent_age,
            "race": race,
            "subrace": subrace,
            "allocations": (
                None
                if allocations is None
                else _validate_allocations(value, "custom draft")
            ),
            "background": background,
            "affinity_elements": affinity_elements,
            "persona": persona,
            "sex": sex,
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
    the three-field persona block (retool-concept-transient-fill D1), plus
    five optional transient-fill keys present only when the validated
    generative proposal carried a value (bump-creation-panel-proposal-v3 D1):
    ``display_name`` (1..64 code points), ``age``/``apparent_age`` (integers
    in the advertised band — the generative layer clamps, so a bound violation on
    the wire is a bug-level structural rejection), ``background`` (1..600
    code points), and ``affinity_elements`` (a list of at most
    ``MAX_AFFINITY_ELEMENTS`` distinct registered element keys; the race bound
    is the generative layer's authority, the wire accepts the structural
    ceiling). An absent optional key is expressed as the key not existing —
    a null value is never legal.
    """
    _require_exact_fields(
        value,
        "proposal",
        {"revision", "race", "subrace", "allocations", "persona"},
        {
            "display_name": "optional",
            "age": "optional",
            "apparent_age": "optional",
            "background": "optional",
            "affinity_elements": "optional",
        },
    )
    revision = _require_int(value, "revision", minimum=1, maximum=MAX_SAFE_INTEGER)
    race = _validate_key(value["race"], "proposal race", MAX_RACE_KEY_CODE_POINTS)
    subrace = value["subrace"]
    if subrace is not None:
        subrace = _validate_key(subrace, "proposal subrace", MAX_SUBRACE_KEY_CODE_POINTS)
    persona = _validate_persona(value["persona"])
    if persona is None:
        raise ProtocolValidationError("proposal persona must be a block")
    checked: dict[str, Any] = {
        "revision": revision,
        "race": race,
        "subrace": subrace,
        "allocations": _validate_allocations(value, "proposal"),
        "persona": persona,
    }
    for key, maximum in (
        ("display_name", MAX_PROPOSAL_NAME_CODE_POINTS),
        ("background", MAX_PERSONA_FIELD_LENGTH),
    ):
        if key in value:
            text = value[key]
            if not isinstance(text, str) or not text:
                raise ProtocolValidationError(f"proposal {key} must be non-empty text")
            if sum(1 for _ in text) > maximum:
                raise ProtocolValidationError(f"proposal {key} exceeds its bound")
            checked[key] = text
    for key in ("age", "apparent_age"):
        if key in value:
            checked[key] = _require_int(
                value, key, minimum=AGE_MINIMUM, maximum=AGE_MAXIMUM
            )
    if "affinity_elements" in value:
        elements = value["affinity_elements"]
        if not isinstance(elements, list) or len(elements) > MAX_AFFINITY_ELEMENTS:
            raise ProtocolValidationError(
                f"proposal affinity_elements must be a list of at most "
                f"{MAX_AFFINITY_ELEMENTS} element keys"
            )
        seen: set[str] = set()
        for element in elements:
            if element not in AFFINITY_ELEMENT_KEYS:
                raise ProtocolValidationError(
                    f"proposal affinity_elements has unknown element {element!r}"
                )
            if element in seen:
                raise ProtocolValidationError(
                    f"proposal affinity_elements duplicates element {element!r}"
                )
            seen.add(element)
        checked["affinity_elements"] = list(elements)
    return checked


# The exact closed portrait union: each status's required keys (``status`` is
# always required; nothing else is ever optional or nullable).
_PORTRAIT_FIELDS = {
    PORTRAIT_EMPTY: {"status"},
    PORTRAIT_PENDING: {"status"},
    PORTRAIT_READY: {"status", "artwork"},
    PORTRAIT_FAILED: {"status", "reason"},
    PORTRAIT_UNAVAILABLE: {"status", "reason"},
}


def _validate_portrait(value: Any) -> dict[str, Any]:
    """Validate the required read-only portrait state union exactly.

    ``empty``/``pending`` carry only ``status``; ``ready`` carries exactly a
    canonical ``artwork`` descriptor; ``failed``/``unavailable`` carry exactly
    a nonblank ``reason`` of at most ``MAX_PORTRAIT_REASON_CODE_POINTS`` code
    points. A missing/null value, an unknown status, an extra or missing key
    and a null artwork or reason all reject the whole panel.
    """
    if not isinstance(value, dict):
        raise ProtocolValidationError("portrait must be an object")
    status = value.get("status")
    if not isinstance(status, str) or status not in _PORTRAIT_FIELDS:
        raise ProtocolValidationError("portrait status is not a known state")
    _require_exact_fields(value, "portrait", _PORTRAIT_FIELDS[status], {})
    if status == PORTRAIT_READY:
        return {"status": status, "artwork": validate_artwork(value["artwork"])}
    if status in (PORTRAIT_FAILED, PORTRAIT_UNAVAILABLE):
        reason = _require_str(value, "reason", maximum=MAX_PORTRAIT_REASON_CODE_POINTS)
        if not reason.strip():
            raise ProtocolValidationError("portrait reason must be non-empty")
        return {"status": status, "reason": reason}
    return {"status": status}


def validate_creation(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``creation`` payload.

    Returns a normalized payload or raises :class:`CreationPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "creation panel",
        {"schema_version", "available", "kind", "draft", "presets", "custom", "portrait"},
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
    race_keys = {race["key"] for race in custom["races"]}
    for card in presets:
        if card["race"] not in race_keys:
            raise CreationPanelError(
                f"preset {card['key']} references non-existent race {card['race']}"
            )

    portrait = _validate_portrait(payload["portrait"])

    result: dict[str, Any] = {
        "schema_version": CREATION_SCHEMA_VERSION,
        "available": True,
        "kind": "creation",
        "draft": draft,
        "presets": presets,
        "custom": custom,
        "portrait": portrait,
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
        "artwork": preset_artwork(card.key),
    }


def _serialize_name(name: Any) -> dict[str, Any]:
    return {"min_length": name.min_length, "max_length": name.max_length}


def _serialize_age(age: AgeBoundsView) -> dict[str, Any]:
    return {
        "age_minimum": age.age_minimum,
        "age_maximum": age.age_maximum,
        "apparent_age_minimum": age.apparent_age_minimum,
        "apparent_age_maximum": age.apparent_age_maximum,
    }


def _serialize_race_option(race: RaceOptionView) -> dict[str, Any]:
    return {
        "key": race.key,
        "display_name_zh": race.display_name_zh,
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
        "point_cap": axis.point_cap,
        "value_at_cap": axis.value_at_cap,
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


def _serialize_sex_option(option: SexOptionView) -> dict[str, Any]:
    return {"key": option.key, "label": option.label}


def _serialize_custom(custom: CustomFormView, actor_identity: str) -> dict[str, Any]:
    return {
        "name": _serialize_name(custom.name),
        "age": _serialize_age(custom.age),
        "races": [_serialize_race_option(race) for race in custom.races],
        "subraces": _serialize_subraces(custom.subraces),
        "profiles": [_serialize_profile(profile) for profile in custom.profiles],
        "affinity": _serialize_affinity(custom.affinity),
        "sex": [_serialize_sex_option(option) for option in custom.sex],
        "silhouettes": silhouette_table(
            actor_identity,
            tuple(option.key for option in custom.sex),
            custom.age.apparent_age_minimum,
            custom.age.apparent_age_maximum,
        ),
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
        "stage": draft["stage"],
        "display_name": draft["display_name"],
        "age": draft["age"],
        "apparent_age": draft["apparent_age"],
        "race": draft["race"],
        "subrace": draft["subrace"],
        # A draft whose allocation policy was superseded reports no points:
        # the browser resumes at the allocation step and cannot confirm them.
        "allocations": (
            None if draft["allocations"] is None else dict(draft["allocations"])
        ),
        "background": draft.get("background"),
        "affinity_elements": list(draft.get("affinity_elements") or []),
        # The wizard normalizer guarantees a concrete member on every v3
        # custom draft it accepts; serialize it verbatim for restore.
        "sex": draft["sex"],
        # The persona block is player-owned data (retool-concept-transient-
        # fill): the saved draft renders it so a reconnect resumes with the
        # player's own prose visible and editable.
        "persona": dict(draft["persona"]) if draft.get("persona") is not None else None,
    }


def _serialize_proposal(proposal: ProposalSnapshot | None) -> dict[str, Any] | None:
    if proposal is None:
        return None
    return proposal.as_dict()


def _serialize_portrait(portrait: DraftPortraitView) -> dict[str, Any]:
    """Project the immutable portrait read onto its exact wire state.

    ``ready`` builds the exact-card descriptor through the art presenter; a
    card that stopped being presentable between the read and the build (a
    vanished file) degrades to the safe ``unavailable`` state rather than an
    invented image or a silent empty slot.
    """
    if portrait.status == PORTRAIT_READY:
        artwork = None
        if portrait.subject is not None and portrait.card is not None:
            artwork = draft_portrait_artwork(
                portrait.subject, dict(portrait.card), portrait.fallback_key
            )
        if artwork is None:
            return {
                "status": PORTRAIT_UNAVAILABLE,
                "reason": rejection_message(PORTRAIT_STATE_UNAVAILABLE),
            }
        return {"status": PORTRAIT_READY, "artwork": artwork}
    if portrait.status in (PORTRAIT_FAILED, PORTRAIT_UNAVAILABLE):
        return {"status": portrait.status, "reason": portrait.reason}
    return {"status": portrait.status}


def _serialize(
    view: CreationView,
    proposal: ProposalSnapshot | None = None,
    *,
    actor_identity: str,
    portrait: DraftPortraitView,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": CREATION_SCHEMA_VERSION,
        "available": True,
        "kind": "creation",
        "draft": _serialize_draft(view.draft),
        "presets": [_serialize_preset_card(card) for card in view.presets],
        "custom": _serialize_custom(view.custom, actor_identity),
        "portrait": _serialize_portrait(portrait),
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
    return validate_creation(
        _serialize(
            view,
            context.proposal,
            actor_identity=str(actor.pk),
            portrait=read_draft_portrait(actor),
        )
    )


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
    "MAX_PORTRAIT_REASON_CODE_POINTS",
    "MAX_PRESETS",
    "MAX_PROFILES",
    "MAX_PROPOSAL_NAME_CODE_POINTS",
    "MAX_RACES",
    "MAX_RACE_KEY_CODE_POINTS",
    "MAX_SEX_OPTIONS",
    "MAX_SPECIALTY_CODE_POINTS",
    "MAX_SILHOUETTES",
    "MAX_SUBRACES",
    "MAX_SUBRACE_KEY_CODE_POINTS",
    "MIN_NAME_LENGTH",
    "PERSONA_WIRE_KEYS",
    "creation_presenter",
    "validate_creation",
]
