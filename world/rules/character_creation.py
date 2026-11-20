"""Deterministic validation and activation for account-owned player shells."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import unicodedata
from typing import Any

from django.db import transaction

from world.imports.schema import MAX_ENTITY_KEY_LENGTH
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY, PlayerPreset
from world.lore.races import SUBRACE_REGISTRY
from world.lore.sex import DEFAULT_SEX
from world.lore.starting_kits import SUBRACE_STARTING_KIT_REGISTRY
from world.observability import log_info, log_warn
from world.rules import start_location
from world.rules.creation_identity import (
    CharacterCreationError,
    validate_age,
    validate_sex,
)
from world.rules.equipment import toggle_equipment
from world.rules.progression import (
    lineage_ownership_closure,
    seed_lineage_proficiency,
)
from world.rules.surfaces import (
    restore_attributes,
    restore_traits,
    snapshot_attributes,
    snapshot_traits,
)
from world.rules.starting_policy import (
    ALLOCATABLE_AXES,
    PHYSICAL_AXES,
    StartingProfile,
    resolve_starting_profile,
)
from world.rules.traits import trait_config_for_values
_CREATION_ATTRIBUTE_KEYS = (
    "age", "apparent_age", "race", "subrace", "creation_pending",
    "skill_proficiency", "skills", "skill_grants", "equipment",
    "inventory", "wallet", "quest_log", "guild_rank", "persona",
    "portrait_policy", "affinity_elements", "sex", "nation", "buffs",
    # Preset activation may seed both (preset-disguise-and-sexual-baseline);
    # the idmapper cache is not transaction-aware, so both join the
    # rollback snapshot.
    "disguised_stats", "sexual",
    # Preset activation binds declared starting companions through
    # ``join_party`` (preset-companion-activation); a failed companion step
    # must restore the player-side membership cache alongside every other
    # in-process surface this snapshot covers.
    "party",
    # Preset activation records its provenance preset key so the built-in
    # gallery fallback can find the preset's declared fallback key through
    # a subject keyed by the entity pk (gallery-builtin-fallbacks).
    "creation_preset_key",
    # Social identities snapshot for atomic rollback (authored-dialogue-social-identity).
    "social_identities",
    # Activation records the start-room arrival (subrace-start-settlements
    # D4); a rolled-back activation must leave no map-knowledge record.
    "map_knowledge",
    # Activation drops the draft portrait receipt (custom) or discards the
    # creation output with it (preset, creation-draft-portrait-cleanup); a
    # rolled-back activation keeps the previously committed receipt.
    "creation_portrait",
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
    sex: str | None = None
    nation: str | None = None
    skip_portrait: bool = False


@dataclass(frozen=True)
class CharacterCreationResult:
    """Persisted identity and allocated starting magic power."""

    display_name: str
    race: str
    subrace: str | None
    magic_power: int


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
    sex: str = DEFAULT_SEX
    nation: str | None = None


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


def _validate_allocations(profile: StartingProfile, allocations: Any) -> dict[str, int]:
    if not isinstance(allocations, Mapping) or set(allocations) != set(ALLOCATABLE_AXES):
        raise CharacterCreationError("allocations must contain exactly the seven starting axes")
    axes = profile.axes_dict()
    checked: dict[str, int] = {}
    for key in ALLOCATABLE_AXES:
        value = allocations[key]
        point_cap = axes[key].point_cap
        if type(value) is not int or not 0 <= value <= point_cap:
            raise CharacterCreationError(
                f"allocation for {key} must be an integer from 0 to {point_cap}"
            )
        checked[key] = value
    if sum(checked.values()) != profile.budget:
        raise CharacterCreationError(f"allocations must sum exactly to {profile.budget}")
    return checked


def _resolve_values(profile: StartingProfile, allocations: Any) -> dict[str, int]:
    """Compute final trait values from one profile plus one allocation map.

    The single points-to-values-plus-modifier implementation every consumer
    shares: the profile's own per-axis conversion (raw increment, or the custom
    elf's magic interpolation), then the subrace static modifiers, then the
    pinned guild counter. Allocation validation is part of the computation
    because the preset registry's cap/budget guarantees live in a CI test, not
    an import-time validator.
    """
    checked = _validate_allocations(profile, allocations)
    axes = profile.axes_dict()
    values = {key: axes[key].value_for(checked[key]) for key in ALLOCATABLE_AXES}
    for key in PHYSICAL_AXES:
        # Subrace static modifiers cover the three physical axes only; the
        # fourth axis (magic_power) is allocable but modifier-free (D-A5).
        values[key] = round(
            values[key] * (1 + getattr(profile.static_modifiers, key, 0.0))
        )
    values["guild_merit"] = 0
    return values


def resolve_preset_values(preset: PlayerPreset) -> dict[str, int]:
    """Resolve one preset card's final trait values. Pure and read-only.

    The single definition of "what this card is worth" shared by player
    activation preflight and every later non-player consumer of the same card
    (the companion builder is the first), so their numbers cannot drift. Takes
    only a preset: no account, no character, no database or world-clock read,
    and no write. The returned mapping is a fresh caller-owned dict per call.
    """
    return _resolve_values(
        resolve_starting_profile(preset.race, preset.subrace),
        preset.allocation_dict(),
    )


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

    The block is the player-owned persona block carried by the custom draft
    (retool-concept-transient-fill D2). Contents are never inspected -- only
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
        # The preset's allocations are consumed inside resolve_preset_values
        # below, so this branch reads only the identity channels directly.
        race, subrace = preset.race, preset.subrace
        affinity_elements = preset.affinity_elements
        # The preset registry is the source of truth for the sex channel
        # (preset-sex-field): the value was validated against SEX_VALUES at
        # load, and a preset-mode request never falls back to DEFAULT_SEX.
        sex = preset.sex
    elif request.mode == "custom":
        name, age, apparent_age = request.display_name, request.age, request.apparent_age
        race, subrace, allocations = request.race, request.subrace, request.allocations
        affinity_elements = request.affinity_elements
        sex = request.sex
    else:
        raise CharacterCreationError("creation mode must be 'preset' or 'custom'")

    valid_name = _validate_name(name)
    valid_age = validate_age(age, "age")
    valid_apparent_age = validate_age(apparent_age, "apparent_age")
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
    if request.mode == "preset":
        # The preset branch delegates the whole computation to the shared pure
        # resolver (preset-value-resolver); the custom branch resolves its own
        # player inputs through the same single arithmetic helper.
        values = resolve_preset_values(preset)
    else:
        values = _resolve_values(
            resolve_starting_profile(race, subrace), allocations
        )
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
    checked_sex = validate_sex(sex, race)
    nation = request.nation
    if nation is None:
        nation = getattr(character, "nation", None)
        if nation is None and hasattr(character, "db"):
            nation = getattr(character.db, "nation", None)
    return _ValidatedCreation(
        valid_name, valid_age, valid_apparent_age, race, subrace, values,
        background, checked_affinity, checked_sex, nation,
    )


def ensure_player_portrait_policy(character: Any) -> dict[str, Any]:
    """Establish or reuse exactly the character's own named portrait policy.

    The explicit named policy (``{"mode": "named", "stable_key": str(pk)}``)
    is the art lifecycle's eligibility marker. Two writers share this one
    helper: activation (``finalize_player_portrait``) and the pending-character
    draft portrait request, so a portrait requested during creation and one
    requested after activation name the SAME subject — the image never has to
    move. An already-matching named policy is reused verbatim; a named policy
    naming a different stable key is a deterministic rejection (a character can
    never own two named portrait subjects). A generic policy is replaced by the
    named one, because a pending shell's profile carries no unique portrait.

    The helper schedules nothing and writes nothing else; the caller owns its
    transaction, so a rollback leaves no policy behind.
    """
    named = {"mode": "named", "stable_key": str(character.pk)}
    existing = character.db.portrait_policy if hasattr(character, "db") else None
    if existing is not None:
        if not hasattr(existing, "get"):
            raise CharacterCreationError("portrait_policy must be a mapping or None")
        policy = dict(existing)
        mode = policy.get("mode")
        if mode == "named":
            if policy.get("stable_key") != named["stable_key"]:
                raise CharacterCreationError(
                    "the character already carries a different named portrait policy"
                )
            return named
        if mode != "generic":
            raise CharacterCreationError(
                f"unknown portrait policy mode {mode!r}"
            )
    character.db.portrait_policy = named
    return named


def finalize_player_portrait(character: Any, *, skip_portrait: bool = False) -> None:
    """Establish the named portrait policy and schedule the post-commit ensure.

    The named policy is established through ``ensure_player_portrait_policy``,
    the one helper the draft portrait request also uses: a character that
    already requested a portrait while pending therefore keeps exactly the
    policy that request established (activation never re-keys it), while a
    character that never requested one gains its policy here.
    ``schedule_portrait_ensure`` registers the exception-safe post-commit
    ensure. Must be called INSIDE the activation transaction
    (fix-creation-finalization-safety D3): a rollback removes any policy THIS
    activation added and the registered commit callback never fires, so a
    rolled-back activation adds no portrait state. State committed BEFORE the
    activation — a draft portrait request's policy, receipt, cards and jobs —
    is not the activation's and survives its rollback unchanged
    (creation-draft-portrait-cleanup).

    ``skip_portrait`` (default False: generate) is the explicit player-created
    skip flag (change ``gallery-autogen-retrofit``): the named policy is still
    established on the skipped path — the character stays eligible for a later
    request — but nothing is scheduled. Skipping means "schedule no automatic
    request"; it never deletes an already generated draft card, so a skipped
    custom activation keeps it, while an artless one resolves through the
    standard chain's fallback seam. A draft card or in-flight creation job on
    the same named subject satisfies the shared automatic-generation guard,
    so the default path never queues a duplicate for it. Like every other
    finalization write, the flag is read inside the activation transaction.
    """
    ensure_player_portrait_policy(character)
    if skip_portrait:
        return
    from world.art.service import schedule_portrait_ensure

    schedule_portrait_ensure(character)


def _persona_record_for(
    validated: _ValidatedCreation,
    request: CharacterCreationRequest,
    persona: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Build the persona record this activation writes, or ``None`` for no write.

    The single shared record builder (preset-persona-activation): both
    creation modes converge here, and ``activate_player_character`` stays the
    sole creation-time persona writer.

    Preset mode returns the registry's validated persona expanded through
    ``PresetPersona.to_record()``, which always carries the six
    ``PERSONA_IMPORT_CARD_KEYS`` and adds ``background`` only when authored;
    the prose length bound was already swept at module import, so no
    re-validation runs here. ``persona`` is custom-mode only: no caller ever
    supplies it for a preset request, and the preset branch takes precedence.

    Custom mode keeps its two historical branches byte-identical: the
    validated draft persona block fills the three prose fields of the six-key
    import-card record (empty containers for the rest), and a draft with only
    a bounded background still persists an import-card-shaped record so the
    owner can inspect and update the flavor text
    (creation-persona-persistence D4). A draft with neither writes nothing.
    """
    if request.mode == "preset":
        return PLAYER_PRESET_REGISTRY[request.preset_key].persona.to_record()
    if persona is not None:
        checked_persona = _validate_persona_block(persona)
        persona_record: dict[str, Any] = {
            "identity": {},
            "personality": checked_persona["personality"],
            "life_story": checked_persona["life_story"],
            "habit": checked_persona["habit"],
            "appearance": {},
            "social_connection": {},
        }
        if validated.background is not None:
            persona_record["background"] = validated.background
        return persona_record
    if validated.background is not None:
        # A custom draft with a background but a null persona block still
        # persists an import-card-shaped record so the owner can inspect and
        # update the flavor text (creation-persona-persistence D4).
        return {
            "identity": {},
            "personality": "",
            "life_story": "",
            "habit": "",
            "appearance": {},
            "social_connection": {},
            "background": validated.background,
        }
    return None


def _preset_lineage_state(
    preset: PlayerPreset,
) -> tuple[dict[str, list[str]], dict[str, float]]:
    """Return the closed ``(skills, skill_proficiency)`` state one preset activates with.

    The third shared caller of the lineage auto-seed (preset-lineage-and-
    proficiency): composes ``lineage_ownership_closure`` and
    ``seed_lineage_proficiency`` directly over the preset's declared keys --
    the same two helpers the import loader and the scene builder share, not
    the import-record wrapper ``normalize_lineage_record``. The declared keys
    keep their declared order and closure-added keys follow them per list;
    the seed satisfies every unsatisfied prerequisite edge to exactly its
    required value, with the preset's declared ``skill_proficiency`` entries
    winning over a seeded value even when one leaves an edge unmet -- the
    same precedence an explicit import-record entry has.
    """
    declared_active = list(preset.active_skills)
    declared_passive = list(preset.passive_skills)
    add_active, add_passive = lineage_ownership_closure(
        [*declared_active, *declared_passive]
    )
    closed = [*declared_active, *add_active, *declared_passive, *add_passive]
    skills_value = {
        "active": [*declared_active, *add_active],
        "passive": [*declared_passive, *add_passive],
    }
    proficiency_value = seed_lineage_proficiency(
        closed, dict(preset.skill_proficiency)
    )
    return skills_value, proficiency_value


def activate_player_character(
    account: Any,
    character: Any,
    request: CharacterCreationRequest,
    *,
    write_observer: Callable[[str], None] | None = None,
    persona: Mapping[str, Any] | None = None,
) -> CharacterCreationResult:
    """Atomically initialize one existing account-owned pending shell.

    ``persona`` carries the player-owned persona block from the custom draft
    (retool-concept-transient-fill D4): when present it is validated
    deterministically and persisted as the six-key import-card record inside
    the same all-or-nothing transaction; when absent nothing is written.
    The parameter is custom-mode only -- preset mode always builds its record
    from the registry's validated persona (preset-persona-activation).

    The retired magic sampler is gone (D-A5): ``magic_power`` arrives as the
    seventh allocated static axis, so activation writes exactly what the
    profile resolved -- no injected randomness.

    The character is moved into its subrace's start room and homed there
    inside the same transaction (subrace-start-settlements); a failure returns
    it to where it stood.

    Draft portrait disposition (creation-draft-portrait-cleanup): the whole
    activation runs inside the pending character's serialized draft portrait
    unit (``world.rules.creation_portrait.draft_portrait_mutation``), entered
    before the preflight, snapshots and transaction; ``activate_draft``'s
    outer entry is reused. A custom activation keeps the named subject, its
    cards and any in-flight creation job and drops only the staging
    ``creation_portrait`` receipt, so the shared automatic-generation guard
    sees the existing work and queues no duplicate. A preset activation
    discards the creation-owned cards/jobs (``clear_draft_portrait``) BEFORE
    the shared portrait finalization, so the preset's normal official/
    fallback/automatic sources decide its portrait. Either disposition rolls
    back with the activation; removed files are unlinked only after commit.
    """
    from world.rules.creation_portrait import draft_portrait_mutation

    with draft_portrait_mutation(character) as unit:
        return _activate_player_character_locked(
            account,
            character,
            request,
            unit,
            write_observer=write_observer,
            persona=persona,
        )


def _activate_player_character_locked(
    account: Any,
    character: Any,
    request: CharacterCreationRequest,
    unit: Any,
    *,
    write_observer: Callable[[str], None] | None,
    persona: Mapping[str, Any] | None,
) -> CharacterCreationResult:
    """The activation body, run inside the character's serialized unit."""
    from world.rules.creation_portrait import (
        CREATION_PORTRAIT_ATTRIBUTE,
        clear_draft_portrait,
        restore_draft_portrait_state,
        snapshot_draft_portrait_state,
    )
    from world.rules.presentation_events import on_publication_commit

    validated = preflight_character_creation(account, character, request)
    try:
        start_room = start_location.resolve_start_room(validated.subrace)
    except start_location.StartLocationError as error:
        raise CharacterCreationError(str(error)) from error
    origin = character.location

    values = validated.values
    trait_config = trait_config_for_values(values)
    # Custom mode grants no skills, so its closure and seed are the empty
    # state; preset mode closes the declared kit over its prerequisite chain
    # and seeds the resulting edges (preset-lineage-and-proficiency).
    if request.mode == "preset":
        preset = PLAYER_PRESET_REGISTRY[request.preset_key]
        inventory_value = preset.inventory_list()
        starting_equipment = preset.starting_equipment
        skills_value, proficiency_value = _preset_lineage_state(
            preset
        )
    else:
        skills_value, proficiency_value = {"active": [], "passive": []}, {}
        # Custom mode hands out the chosen subrace's basic starting kit
        # (add-subrace-starting-kits D2). Load-time coverage guarantees the
        # lookup succeeds; the guarded get keeps even a future registry bug
        # failing pre-persistence like every other activation error.
        kit = SUBRACE_STARTING_KIT_REGISTRY.get(validated.subrace)
        if kit is None:
            raise CharacterCreationError("subrace has no registered starting kit")
        inventory_value = kit.inventory_list()
        # Every kit item is worn at activation (custom-kit-worn-at-activation
        # D2): the derived starting_equipment is the kit's own keys, so the
        # shared toggle loop below wears them exactly like a preset loadout —
        # same position, same all-or-nothing transaction, same buff and
        # gauge-ceiling machinery. The guarded lookup above fired first, so
        # the derivation only sees a resolved kit, and both still precede
        # every write. Load-time kit validation guarantees the set is fully
        # wearable (no singleton collision, no accessory overflow).
        starting_equipment = tuple(key for key, _ in kit.items)
    attribute_values = {
        "age": validated.age,
        "apparent_age": validated.apparent_age,
        "race": validated.race,
        "subrace": validated.subrace,
        "skill_proficiency": proficiency_value,
        "skills": skills_value,
        "skill_grants": [],
        "equipment": {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []},
        "inventory": inventory_value,
        "wallet": 0,
        "quest_log": [],
        "guild_rank": None,
        "creation_pending": False,
        "affinity_elements": list(_resolved_affinity_elements(validated)),
        # Creation and the character importer converge on one concrete
        # ``SEX_VALUES`` member here (namegen-creation-ui D2); the wizard
        # draft is normalized through the same validator before it is stored.
        "sex": validated.sex,
        "nation": validated.nation,
    }
    if request.mode == "preset":
        # The disguise layer and sexual baseline are preset-only writes
        # (custom mode declares neither and writes neither key, preserving
        # today's behavior). ``disguised_stats`` normalizes an empty
        # declaration to ``None`` exactly like the import loader's
        # ``record["disguised_stats"] or None``; ``sexual`` is written ONLY
        # when the preset declares a baseline, so an undeclared card keeps
        # the lazy ``_generic_default_baseline()`` construction. Inserted
        # after ``nation`` so the ``creation_pending=False`` write always
        # precedes them in the shared write loop.
        attribute_values["disguised_stats"] = dict(preset.disguised_stats) or None
        if preset.sexual_baseline is not None:
            attribute_values["sexual"] = preset.sexual_baseline.to_record()
        # Registry provenance (gallery-builtin-fallbacks): the portrait
        # subject of a preset-born character is keyed by pk, not preset key,
        # so the activation itself carries the preset key for the fallback
        # resolver's declaration rung.
        attribute_values["creation_preset_key"] = preset.key
    persona_record = _persona_record_for(validated, request, persona)
    # Social identity: custom mode defaults empty; preset mode seeds preset's explicit tags.
    preset_social_identities = preset.social_identities if request.mode == "preset" else ()
    attribute_values["social_identities"] = tuple(sorted(set(preset_social_identities)))

    old_key = character.key
    attribute_snapshots = snapshot_attributes(character, _CREATION_ATTRIBUTE_KEYS)
    trait_snapshot = snapshot_traits(character)
    portrait_snapshot = snapshot_draft_portrait_state(character)
    # Companions built during THIS activation attempt, kept for the except
    # branch below (preset-companion-activation).
    built_companions: list[Any] = []
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
            # Declared starting equipment is applied through the sole
            # equipment writer (preset-starting-equipment D1/D2), LAST among
            # the mechanical writes: the toggle preflight requires canonical
            # inventory ownership (so the ``inventory`` attribute write above
            # must have landed) and ``sync_equipment_gauge_limits``
            # recomputes ceilings on the already-applied trait config. A
            # rejected toggle is a hard failure (D3): the registry validators
            # make one a genuine bug, and silently skipping it would ship a
            # character contradicting its own card. ``buffs`` joins the
            # activation snapshot (D5) because the toggle writes it and the
            # idmapper cache is not transaction-aware.
            if starting_equipment:
                for equipment_key in starting_equipment:
                    toggle_result = toggle_equipment(character, equipment_key)
                    if toggle_result.outcome == "rejected":
                        raise CharacterCreationError(
                            f"preset starting equipment {equipment_key!r} was "
                            f"rejected: {toggle_result.reason}"
                        )
                # The stage fires only when toggles actually ran, so an
                # observed stage always means a real write attempt.
                if write_observer:
                    write_observer("starting_equipment")
            # Every activation path (Telnet command, WebClient ``activate_draft``)
            # clears the staging creation draft in the SAME atomic transaction, so
            # a completed character never retains a draft (webclient-character-
            # creation-ui D3). This is the single documented finalization write
            # to ``creation_draft`` outside the wizard's save path.
            if character.attributes.has("creation_draft"):
                if write_observer:
                    write_observer("creation_draft")
                character.attributes.remove("creation_draft")
            # Start-location placement (subrace-start-settlements D4): the
            # character moves into its subrace's start room, is homed there and
            # records the arrival, BEFORE companions are built at its location.
            # The move is hook-free so the transaction holds only durable,
            # snapshot-covered writes; arrival effects run after commit.
            if not character.move_to(start_room, quiet=True, move_hooks=False):
                raise CharacterCreationError("start room refused the character")
            character.home = start_room
            from world.rules.map_knowledge import record_arrival

            record_arrival(character)
            # Registered through the publication commit seam so the effects
            # (which may take the art queue lock) run only after the commit
            # AND after the serialized draft portrait unit released it.
            on_publication_commit(
                lambda: _run_start_arrival_effects(character, start_room, origin)
            )
            if write_observer:
                write_observer("start_location")
            # Declared starting companions are built, seeded, and bound LAST
            # among the player-side writes, before portrait finalization
            # (preset-companion-activation): the builder places each NPC at
            # ``player.location`` and ``join_party`` requires a persisted
            # player key and co-location, so both only hold after the
            # identity/attribute writes above. The binding owns its failure
            # path (delete built NPCs, restore surfaces, surface as
            # ``CharacterCreationError``); this branch then rolls the whole
            # activation back through the except below. The lazy import keeps
            # the module-cycle-free: ``starting_companions`` imports this
            # module at top level, so this side must not import it there.
            if request.mode == "preset" and preset.starting_companions:
                from world.rules.starting_companions import (
                    _discard_built_companions,
                    bind_starting_companions,
                )

                built_companions = bind_starting_companions(character, preset)
                # The stage fires only when a binding actually ran, so an
                # observed stage always means a real companion-write attempt.
                if write_observer:
                    write_observer("starting_companions")
            # Every player-activation path (Telnet command, WebClient
            # ``activate_draft``) establishes the named portrait policy and
            # schedules the post-commit portrait ensure INSIDE this activation
            # transaction (fix-creation-finalization-safety D3): a rollback
            # removes the policy attribute and the on-commit job never fires.
            # The request's explicit ``skip_portrait`` flag (default False)
            # still establishes the policy but schedules nothing
            # (gallery-autogen-retrofit).
            # Draft portrait disposition (creation-draft-portrait-cleanup),
            # BEFORE the finalizer registers its guarded ensure: a preset
            # discards the creation-owned cards/jobs and the receipt so it
            # never inherits a custom image; a custom activation keeps the
            # subject, cards and in-flight job and drops only the staging
            # receipt. The stage fires only when a receipt existed.
            if character.attributes.has(CREATION_PORTRAIT_ATTRIBUTE):
                if request.mode == "preset":
                    clear_draft_portrait(character, unit)
                else:
                    character.attributes.remove(CREATION_PORTRAIT_ATTRIBUTE)
                if write_observer:
                    write_observer("draft_portrait")
            finalize_player_portrait(character, skip_portrait=request.skip_portrait)
            if write_observer:
                write_observer("portrait_policy")
    except Exception:
        # A failure AFTER a completed bind (the write observer, portrait
        # finalization): the rollback removed the companion rows but the
        # idmapper and the departure room's contents cache still hold them.
        # Evict them BEFORE the attribute restore below: the eviction's
        # ``at_object_delete`` purge rewrites ``player.db.party`` (binding
        # removal), and the snapshot restore must run last so the purged
        # surface cannot outlive the restore. Best-effort, never raises, so
        # no phantom companion survives the failed activation in-process.
        if built_companions:
            _discard_built_companions(built_companions)
        # After the companion discard (it evicts from the start room's
        # contents) and before the attribute restore.
        restore_activation_placement(character, origin)
        character.key = old_key
        restore_traits(character, trait_snapshot)
        restore_draft_portrait_state(portrait_snapshot)
        restore_attributes(character, attribute_snapshots)
        raise
    log_info(
        "character_start_placed",
        context={
            "char": character.key,
            "char_dbref": character.dbref,
            "subrace": validated.subrace,
            "room": start_room.key,
            "room_dbref": start_room.dbref,
        },
    )
    from world.rules.lore_knowledge import reveal_lore_best_effort

    if validated.race:
        reveal_lore_best_effort(character, "race", validated.race)
    if validated.nation:
        reveal_lore_best_effort(character, "nation", validated.nation)
    return CharacterCreationResult(
        validated.display_name, validated.race, validated.subrace, validated.values["magic_power"]
    )


def restore_activation_placement(character: Any, origin: Any) -> None:
    """Undo a rolled-back activation placement in-process; never raises.

    The rollback reverted the durable location and home rows, but the idmapper
    object and both rooms' contents caches still hold the moved state. A
    hook-free ``move_to`` (the mirror of the hook-free forward move) returns the
    character even into a room whose entry hook refuses character arrivals (the
    虛境 birth room); ``home`` is re-read from the rolled-back row and applied
    in memory only.
    """
    from evennia.objects.models import ObjectDB

    if character.location is not origin:
        try:
            if origin is None:
                character.location = None
            elif not character.move_to(origin, quiet=True, move_hooks=False):
                raise RuntimeError("origin refused the returning character")
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "activation_placement",
                    "char": character.key,
                    "key": "location",
                },
            )
    try:
        row_home = (
            ObjectDB.objects.filter(id=character.id)
            .values_list("db_home_id", flat=True)
            .first()
        )
        if character.db_home_id != row_home:
            character.db_home_id = row_home
    except Exception as error:
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={
                "stage": "activation_placement",
                "char": character.key,
                "key": "home",
            },
        )


def _run_start_arrival_effects(character: Any, room: Any, origin: Any) -> None:
    """Run the arrival effects of a committed start-room placement.

    They are the effects a hooks-enabled move would have run: the room's
    receive hook (scene entry and art ensure), arrival lore, encounter
    dispatch and the auto look. Each step is best-effort: activation has
    already committed, so a failure is logged and never raised.
    """

    def _receive() -> None:
        room.at_object_receive(character, origin, move_type="teleport")

    def _lore() -> None:
        from world.quests.room_observation import observe_arrival_lore

        observe_arrival_lore(character, room)

    def _encounters() -> None:
        from world.quests.encounter_dispatch import activate_for_move

        activate_for_move(character)

    def _look() -> None:
        character.msg(text=(character.at_look(room), {"type": "look"}))

    for step, effect in (
        ("receive", _receive),
        ("lore", _lore),
        ("encounters", _encounters),
        ("look", _look),
    ):
        try:
            effect()
        except Exception as error:
            log_warn(
                "character_start_arrival_effect_failed",
                exc=error,
                context={"char": getattr(character, "key", None), "step": step},
            )


def _validate_preset_persona_lengths(registry: Mapping[str, PlayerPreset]) -> None:
    """Sweep every registered preset persona's prose against the field-length cap.

    ``world/lore/`` must not import ``world/rules/``, so the lore-side persona
    validator cannot see ``MAX_PERSONA_FIELD_LENGTH`` (field-parity design
    3.1): this module — the constant's owner — runs the length bound over
    every preset persona's ``to_record()`` at import instead, so an over-long
    field fails the server start exactly as an invalid skill kit does. The
    walk covers every string the record can carry: top-level prose, the
    identity layers, the appearance sub-keys, and both sides of every
    ``social_connection`` pair (``PersonaStore`` renders connection keys
    verbatim, so they are prose too).
    """
    for preset in registry.values():
        for field, value in preset.persona.to_record().items():
            texts: list[tuple[str, str]] = []
            if isinstance(value, str):
                texts.append((f"persona.{field}", value))
            elif isinstance(value, Mapping):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_key, str):
                        texts.append((f"persona.{field} key {sub_key!r}", sub_key))
                    if isinstance(sub_value, str):
                        texts.append((f"persona.{field}.{sub_key}", sub_value))
            for label, text in texts:
                if len(text) > MAX_PERSONA_FIELD_LENGTH:
                    raise CharacterCreationError(
                        f"preset {preset.key!r} {label} exceeds the "
                        f"{MAX_PERSONA_FIELD_LENGTH}-character length cap"
                    )


_validate_preset_persona_lengths(PLAYER_PRESET_REGISTRY)
