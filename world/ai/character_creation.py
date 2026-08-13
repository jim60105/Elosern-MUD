"""Character creation layer: guarded concept-to-proposal generation.

The ``character_creation`` layer maps a player's free-form character concept to
a validated frozen ``CharacterProposal`` through the shared
validation-retry-degrade guardrail (design §7.5). The proposal carries only
existing registry keys (race/subrace/skill) plus the six allocation values and
a three-field persona draft; it never carries an age or any other mechanical
number, so the deterministic adult gate stays the only age authority. When the
layer is disabled, the transport fails, the prompt key is unavailable, or the
validation retries are exhausted, ``generate_character_proposal`` resolves to
``None`` -- the single public degraded marker -- so the command can return the
stable offline message and the deterministic creation wizard remains fully
usable.

Boundary contract (``tests/test_ai_transport_contract.py``): this module imports
no state writer, no typeclass, no live transport, and no socket. It reads only
the immutable ``world.lore`` and ``world.skills`` registries and consumes the
client through the injected protocol exactly like ``npc_dialogue.py``. The
allocation-band derivation mirrors
``world/rules/character_creation.resolve_starting_profile`` against the same
lore registries; the deterministic preflight at activation remains the final
authority over every proposal value.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from twisted.internet import defer

from world.ai import guardrail
from world.ai.guardrail import (
    GuardrailRegistrationError,
    guarded_call,
    register_degrade_fallback,
    register_semantic_validator,
)
from world.ai.schemas import ChatRequestDescriptor
from world.ai.schemas.registry import (
    DuplicateSchemaError,
    _OUTPUT_SCHEMAS,
    register_output_schema,
)
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.prompts.loader import PromptUnavailableError, render_prompt
from world.skills.registry import SKILL_REGISTRY

# The six allocatable starting axes (design D2). Mirrors
# ``world/rules/traits.GAUGE_KEYS + STATIC_KEYS``; the tuple is duplicated here
# only because ``world/ai`` must not import ``world.rules`` (transport-boundary
# contract), and the activation preflight remains the authoritative checker.
ALLOCATABLE_AXES = ("hp", "mp", "sp", "atk_phys", "agility", "defense")

# Hard prompt bounds (design D2): the concept input is capped before it enters
# any prompt, the race catalog is bounded with an explicit truncation marker,
# and the persona fields are capped to the PersonaStore field limit so a
# validated draft always fits the read-only persona contract.
MAX_CONCEPT_LENGTH = 500
MAX_CATALOG_LENGTH = 2000
MAX_PERSONA_FIELD_LENGTH = 600
MAX_SUGGESTED_SKILLS = 8

# The persona draft's exact field set; a proposal with any other shape fails
# the whole proposal (design D2).
PERSONA_FIELDS = ("personality", "life_story", "habit")

_TRUNCATION_MARKER = "…"


class CharacterCreationClientRequiredError(TypeError):
    """Raised when a proposal call is made with an explicit ``None`` client."""


class CharacterCreationNotRegisteredError(RuntimeError):
    """Raised when the character_creation layer's hooks are not installed."""


@dataclass(frozen=True)
class CharacterProposal:
    """A validated frozen concept-to-proposal mapping.

    Every key is a real registry key or an in-band allocation value; the
    persona draft is the only free-form text. The proposal carries no age and
    no number outside ``allocations``.
    """

    race_key: str
    subrace_key: str | None
    allocations: Mapping[str, int]
    suggested_skills: tuple[str, ...]
    persona: Mapping[str, str]


CHARACTER_CREATION_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["race_key", "subrace_key", "allocations", "suggested_skills", "persona"],
    "properties": {
        "race_key": {"type": "string"},
        "subrace_key": {"type": ["string", "null"]},
        "allocations": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        },
        "suggested_skills": {"type": "array", "items": {"type": "string"}},
        "persona": {
            "type": "object",
            "required": ["personality", "life_story", "habit"],
            "properties": {
                "personality": {"type": "string"},
                "life_story": {"type": "string"},
                "habit": {"type": "string"},
            },
        },
    },
}

_CHARACTER_CREATION_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the public ``None``."""
    return _CHARACTER_CREATION_DEGRADED


def _validate_shape(parsed: Any) -> list[str]:
    if not isinstance(parsed, Mapping):
        return ["character proposal must be a JSON object"]
    extra = sorted(set(parsed) - {"race_key", "subrace_key", "allocations", "suggested_skills", "persona"})
    if extra:
        return [
            "character proposal carries unexpected field(s) "
            + ", ".join(repr(name) for name in extra)
            + "; only race_key, subrace_key, allocations, suggested_skills, "
            "and persona are allowed (no age, no other numbers)"
        ]
    return []


def _validate_race(parsed: Any) -> list[str]:
    race_key = parsed.get("race_key") if isinstance(parsed, Mapping) else None
    if not isinstance(race_key, str) or race_key not in RACE_REGISTRY:
        return [f"race_key {race_key!r} is not a registered race"]
    return []


def _validate_subrace(parsed: Any) -> list[str]:
    if not isinstance(parsed, Mapping):
        return []
    race_key = parsed.get("race_key")
    subrace_key = parsed.get("subrace_key")
    if subrace_key is None:
        return []
    if not isinstance(subrace_key, str) or subrace_key not in SUBRACE_REGISTRY:
        return [f"subrace_key {subrace_key!r} is not a registered subrace"]
    if SUBRACE_REGISTRY[subrace_key].race_key != race_key:
        return [
            f"subrace {subrace_key!r} does not belong to race {race_key!r}"
        ]
    return []


def _race_bands(race_key: str, subrace_key: str | None) -> dict[str, tuple[int, int]]:
    """Return the allocatable band per axis, mirroring ``resolve_starting_profile``.

    Reads only the immutable race/subrace registries: the race's vital and
    static baselines, overridden per-axis by the subrace's vital overrides.
    """
    race = RACE_REGISTRY[race_key]
    bounds: dict[str, tuple[int, int]] = {
        "hp": race.vital_baseline.hp,
        "mp": race.vital_baseline.mp,
        "sp": race.vital_baseline.sp,
        "atk_phys": race.static_baseline.atk_phys,
        "agility": race.static_baseline.agility,
        "defense": race.static_baseline.defense,
    }
    if subrace_key is not None:
        subrace = SUBRACE_REGISTRY[subrace_key]
        if subrace.vital_overrides:
            bounds.update(subrace.vital_overrides)
    return bounds


def _allocation_budget(race_key: str, subrace_key: str | None) -> int:
    spans = [
        upper - lower
        for lower, upper in _race_bands(race_key, subrace_key).values()
    ]
    return sum(spans) // 2


def _validate_allocations(parsed: Any) -> list[str]:
    if not isinstance(parsed, Mapping):
        return []
    race_key = parsed.get("race_key")
    subrace_key = parsed.get("subrace_key")
    if not isinstance(race_key, str) or race_key not in RACE_REGISTRY:
        return []
    if subrace_key is not None and (
        not isinstance(subrace_key, str) or subrace_key not in SUBRACE_REGISTRY
    ):
        # The subrace validator reports the unknown key; bands cannot be
        # derived for it, so this validator stays silent.
        return []
    allocations = parsed.get("allocations")
    if not isinstance(allocations, Mapping) or set(allocations) != set(ALLOCATABLE_AXES):
        return ["allocations must contain exactly the six starting axes"]
    bands = _race_bands(race_key, subrace_key)
    for axis in ALLOCATABLE_AXES:
        value = allocations.get(axis)
        lower, upper = bands[axis]
        span = upper - lower
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= span:
            return [f"allocation for {axis} must be an integer from 0 to {span}"]
    if sum(allocations[axis] for axis in ALLOCATABLE_AXES) != _allocation_budget(race_key, subrace_key):
        return ["allocations must sum exactly to the race's allocation budget"]
    return []


def _validate_suggested_skills(parsed: Any) -> list[str]:
    skills = parsed.get("suggested_skills") if isinstance(parsed, Mapping) else None
    if not isinstance(skills, list) or len(skills) > MAX_SUGGESTED_SKILLS:
        return [
            f"suggested_skills must be a list of at most {MAX_SUGGESTED_SKILLS} keys"
        ]
    seen: set[str] = set()
    for key in skills:
        if not isinstance(key, str) or key not in SKILL_REGISTRY:
            return [f"suggested skill {key!r} is not a registered skill"]
        if key in seen:
            return [f"suggested skill {key!r} repeats"]
        seen.add(key)
    return []


def _validate_persona(parsed: Any) -> list[str]:
    persona = parsed.get("persona") if isinstance(parsed, Mapping) else None
    if not isinstance(persona, Mapping) or set(persona) != set(PERSONA_FIELDS):
        return ["persona must contain exactly personality, life_story, and habit"]
    for field in PERSONA_FIELDS:
        value = persona.get(field)
        if not isinstance(value, str) or not value.strip():
            return [f"persona.{field} must be a non-empty text field"]
        if len(value) > MAX_PERSONA_FIELD_LENGTH:
            return [
                f"persona.{field} exceeds the {MAX_PERSONA_FIELD_LENGTH}-character length cap"
            ]
    return []


_VALIDATORS: dict[str, Any] = {
    "proposal_shape": _validate_shape,
    "race_registry": _validate_race,
    "subrace_compatibility": _validate_subrace,
    "allocations_in_bands": _validate_allocations,
    "suggested_skills_registry": _validate_suggested_skills,
    "persona_exact_shape": _validate_persona,
}


def _cap_string(value: str) -> str:
    if len(value) <= MAX_CONCEPT_LENGTH:
        return value
    return value[: MAX_CONCEPT_LENGTH - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def build_race_catalog() -> str:
    """Render a bounded registry-derived race/subrace/skill brief for the prompt.

    Deterministic: identical registries always produce byte-identical output,
    and the brief carries no numbers (the LLM must not infer bands or budgets).
    The catalog is hard-bounded with an explicit truncation marker; the
    deterministic proposal validation is unaffected by a truncated catalog.
    """
    race_entries = "、".join(
        f"{key}（{race.description}）" for key, race in RACE_REGISTRY.items()
    )
    subrace_entries = "、".join(
        f"{key}（{subrace.display_name_zh}，所屬種族 {subrace.race_key}）"
        for key, subrace in SUBRACE_REGISTRY.items()
    )
    skill_entries = "、".join(SKILL_REGISTRY)
    catalog = (
        f"種族：{race_entries}\n子種族：{subrace_entries}\n"
        f"可建議技能鍵值：{skill_entries}"
    )
    if len(catalog) <= MAX_CATALOG_LENGTH:
        return catalog
    budget = MAX_CATALOG_LENGTH - len(_TRUNCATION_MARKER)
    cut = catalog.rfind("、", 0, budget)
    if cut == -1:
        return catalog[:budget] + _TRUNCATION_MARKER
    return catalog[:cut] + _TRUNCATION_MARKER


def build_character_creation_prompt(concept: str) -> tuple[dict[str, str], dict[str, str]]:
    """Build a deterministic (system, user) message pair for one proposal call.

    The system message fixes the 正體中文 role, the registry-fidelity rule, the
    no-numbers/no-age rule, and the exact JSON output contract, substituting
    the bounded race catalog into ``{race_catalog}``. The user message
    serializes the bounded concept. Identical input always produces
    byte-identical prompts with no live entity references.
    """
    system = {
        "role": "system",
        "content": render_prompt(
            "character_creation.system",
            concept=_cap_string(concept),
            race_catalog=build_race_catalog(),
        ),
    }
    user = {
        "role": "user",
        "content": json.dumps(
            {"concept": _cap_string(concept)}, sort_keys=True, ensure_ascii=False
        ),
    }
    return system, user


def _is_registered() -> bool:
    """True when the guardrail's actual registries hold every layer hook."""
    if guardrail._degrade_fallbacks.get("character_creation") is not _degrade_fallback:
        return False
    validators = guardrail._semantic_validators.get("character_creation", {})
    if not all(
        validators.get(name) is validator
        for name, validator in _VALIDATORS.items()
    ):
        return False
    return _OUTPUT_SCHEMAS.get("character_creation") is CHARACTER_CREATION_OUTPUT_SCHEMA


def _require_registered() -> None:
    if not _is_registered():
        raise CharacterCreationNotRegisteredError(
            "the character_creation layer is not registered; "
            "call register_character_creation() first"
        )


def _uninstall_fallback() -> None:
    if guardrail._degrade_fallbacks.get("character_creation") is _degrade_fallback:
        del guardrail._degrade_fallbacks["character_creation"]


def _uninstall_validator(name: str) -> None:
    validators = guardrail._semantic_validators.get("character_creation", {})
    if validators.get(name) is _VALIDATORS[name]:
        del validators[name]


def _uninstall_schema() -> None:
    if _OUTPUT_SCHEMAS.get("character_creation") is CHARACTER_CREATION_OUTPUT_SCHEMA:
        del _OUTPUT_SCHEMAS["character_creation"]


def _uninstall_all_own_hooks() -> None:
    """Remove every character_creation hook that is this module's own (by identity).

    Used for rollback so a partial-failure registration can never leave a
    half-installed layer behind. Foreign hooks with the same names are left
    untouched.
    """
    _uninstall_fallback()
    for name in _VALIDATORS:
        _uninstall_validator(name)
    _uninstall_schema()


def register_character_creation() -> None:
    """Install the character_creation layer's guardrail hooks atomically and idempotently.

    Registers the sentinel degrade fallback, every semantic validator, and the
    output jsonschema. On a partial failure every hook belonging to this module
    (by identity) is removed before the error propagates, so the layer is never
    left half-registered. A second call is a no-op that keeps the first
    registration and swallows only this module's own duplicate registration,
    never an incompatible one.
    """
    if _is_registered():
        return
    try:
        if guardrail._degrade_fallbacks.get("character_creation") is not _degrade_fallback:
            register_degrade_fallback("character_creation", _degrade_fallback)
        for name, validator in _VALIDATORS.items():
            validators = guardrail._semantic_validators.get("character_creation", {})
            if validators.get(name) is validator:
                continue
            register_semantic_validator("character_creation", name, validator)
        if _OUTPUT_SCHEMAS.get("character_creation") is not CHARACTER_CREATION_OUTPUT_SCHEMA:
            register_output_schema("character_creation", CHARACTER_CREATION_OUTPUT_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _uninstall_all_own_hooks()
        raise


@defer.inlineCallbacks
def generate_character_proposal(client: Any, *, concept: str):
    """Run the character_creation layer's guarded pipeline for one proposal.

    Args:
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); never imported directly here. An explicit
            ``None`` is rejected with ``CharacterCreationClientRequiredError``
            before any prompt construction or transport interaction.
        concept: The player's free-form character idea; bounded before it
            enters any prompt.

    Returns:
        A Deferred resolving to a frozen ``CharacterProposal`` on success, or
        to ``None`` -- the single public degraded marker -- when the layer is
        disabled, the prompt key is unavailable, the transport fails, or the
        retry budget is exhausted. The layer never writes state and never
        yields a partial proposal.
    """
    if client is None:
        raise CharacterCreationClientRequiredError(
            "generate_character_proposal requires an injected client; got None"
        )
    _require_registered()
    try:
        system, user = build_character_creation_prompt(concept)
    except PromptUnavailableError:
        return None
    descriptor = ChatRequestDescriptor(
        messages=(system, user),
        schema_id="character_creation",
    )
    text = yield guarded_call("character_creation", client, descriptor)
    if text is _CHARACTER_CREATION_DEGRADED:
        return None
    parsed = json.loads(text)
    return CharacterProposal(
        race_key=parsed["race_key"],
        subrace_key=parsed["subrace_key"],
        allocations={axis: parsed["allocations"][axis] for axis in ALLOCATABLE_AXES},
        suggested_skills=tuple(parsed["suggested_skills"]),
        persona={field: parsed["persona"][field] for field in PERSONA_FIELDS},
    )
