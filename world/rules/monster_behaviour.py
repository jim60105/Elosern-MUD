"""Deterministic, rulebook-driven monster combat decisions.

Startup loads and validates one AI tuning rulebook and publishes three things:
the immutable resolved tuning (:data:`MONSTER_AI_TUNING`) with its reproducible
fingerprint, the typed per-monster resolution (:func:`resolve_monster_ai`) that
honours the *actual* stored ``behaviour_tree`` and the registered
species/variant pair, and the legacy decision body
(:func:`monster_behaviour_policy`).

Intelligence is authored per registered variant and never inferred (design
section 5/6): no tier, species, danger grade, rank, stat or archetype supplies
one. Every production variant is authored ``legacy``, and the utility selector
is delivered by the later ``monster-ai-attack-selection`` change, so the legacy
body below still returns exactly the action it returned before.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from json import dumps
from math import isfinite
from numbers import Real
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable

import yaml

from world.lore.monster_species import (
    MONSTER_SPECIES_REGISTRY,
    MONSTER_VARIANT_REGISTRY,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.rules import combat, dice
from world.rules.action import ActionRequest, _stored_trait_value
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_individual import _registered_variant
from world.rules.progression import can_use_skill
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillDef,
    SkillKind,
    TargetSpec,
)


class MonsterBehaviourConfigError(ValueError):
    """Raised when monster behaviour tuning violates its rulebook contract."""


def _configuration_error(detail: str) -> MonsterBehaviourConfigError:
    return MonsterBehaviourConfigError(
        f"invalid monster behaviour rulebook: {detail}"
    )


def _load_rulebook(path: Path) -> Any:
    """Load YAML while preserving the stable rulebook-error contract."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise _configuration_error("could not parse YAML") from error


MONSTER_BEHAVIOUR_YAML = _load_rulebook(
    Path(__file__).parent / "rulebook" / "monster_behaviour.yaml"
)

#: The decision-algorithm version a fingerprint covers. Bump it whenever a
#: selection change alters what an identical resolved tuning decides.
AI_ALGORITHM_VERSION = 1

#: The authored candidate-budget bounds (attack design section 4).
MIN_CANDIDATE_BUDGET = 1
MAX_CANDIDATE_BUDGET = 4096


class DecisionMode(StrEnum):
    """One monster's effective decision mode (design section 5).

    ``LEGACY`` is a permanent product mode, not a compatibility shim: its
    target order, skill order, flee priority and dice sequence are the retained
    contract.
    """

    LEGACY = "legacy"
    UTILITY = "utility"


#: The complete named utility-weight schema (attack design section 6). A
#: supplied ``utility_weights`` mapping declares exactly these names, so a
#: partially tuned archetype cannot enter the rulebook.
UTILITY_WEIGHT_NAMES: tuple[str, ...] = (
    "damage",
    "kill",
    "heal",
    "control",
    "focus",
    "cost",
    "waste",
    "preference",
)


@dataclass(frozen=True, slots=True)
class UtilityWeights:
    """The authored, finite, non-negative weights of one archetype."""

    damage: float
    kill: float
    heal: float
    control: float
    focus: float
    cost: float
    waste: float
    preference: float

    def as_payload(self) -> dict[str, float]:
        """Return the canonical-named weight mapping for fingerprinting."""
        return {name: getattr(self, name) for name in UTILITY_WEIGHT_NAMES}


class InvalidDecisionReason(StrEnum):
    """Why a monster's AI tuning could not produce a usable decision."""

    #: The actual stored binding names no archetype this process knows, so no
    #: profile -- and therefore no mode -- can be established at all.
    INVALID_BINDING = "invalid_binding"
    #: Utility was requested without a registered species/variant pair.
    INVALID_IDENTITY = "invalid_identity"
    #: Utility was requested for a variant that authors no intelligence.
    MISSING_INTELLIGENCE = "missing_intelligence"


@dataclass(frozen=True, slots=True)
class MonsterAIDecision:
    """One monster's resolved AI tuning, recorded for its session.

    Every field is an immutable scalar or enum, so a recorded resolution can
    never be edited through one of its own containers. ``invalid_reason`` is
    ``None`` exactly when the resolution is usable.
    """

    mode: DecisionMode | None
    intelligence: int | None
    archetype_key: str | None
    variant_key: str | None
    invalid_reason: InvalidDecisionReason | None
    tuning_fingerprint: str


@dataclass(frozen=True, slots=True)
class MonsterAITuning:
    """The immutable, fingerprinted AI tuning this process loaded at startup.

    ``behaviour_profiles``, ``tier_defaults``, ``variant_intelligence``,
    ``variant_decision_mode`` and ``variant_bindings`` are read-only views over
    private mappings the loader builds and then discards, so no caller can
    mutate the recorded tuning. ``variant_bindings`` carries the authored
    decision-relevant binding (threat tier, archetype reference) of every
    variant the two tuning maps name.
    """

    algorithm_version: int
    candidate_budget: int
    behaviour_profiles: Mapping[str, "BehaviourProfile"]
    tier_defaults: Mapping[str, str]
    variant_intelligence: Mapping[str, int]
    variant_decision_mode: Mapping[str, DecisionMode]
    variant_bindings: Mapping[str, tuple[str, str | None]]
    fingerprint: str


@dataclass(frozen=True)
class BehaviourProfile:
    """Tunable leaves for the shared monster decision tree."""

    target_strategy: str
    skill_choice: str
    prefer_area_when_multiple_enemies: bool
    flee_hp_fraction: float | None
    decision_mode: DecisionMode
    utility_weights: UtilityWeights | None


_MANDATORY_PROFILE_FIELDS = frozenset(
    {
        "target_strategy",
        "skill_choice",
        "prefer_area_when_multiple_enemies",
        "flee_hp_fraction",
    }
)
_OPTIONAL_PROFILE_FIELDS = frozenset({"decision_mode", "utility_weights"})
_TOP_LEVEL_FIELDS = frozenset(
    {
        "tier_default_archetype",
        "archetypes",
        "variant_intelligence",
        "variant_decision_mode",
        "candidate_budget",
    }
)
#: An archetype that declares no mode is legacy, and one that declares no
#: weights is simply not scored yet (design section 5; attack design section 2
#: makes both fields additive).
_DEFAULT_DECISION_MODE = DecisionMode.LEGACY
_TARGET_STRATEGIES = frozenset({"lowest_hp", "highest_effective_power"})
_SKILL_CHOICES = frozenset({"first_owned", "highest_expected_damage"})


def _format_keys(keys: Any) -> str:
    """Format authored keys for a diagnostic without comparing mixed types."""
    return repr(sorted(keys, key=repr))


def _finite_real(value: Any) -> bool:
    """Return whether ``value`` is a finite real number, never a boolean."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def _validated_mode(value: Any, where: str) -> DecisionMode:
    """Return the authored decision mode, rejecting anything else."""
    if isinstance(value, str):
        try:
            return DecisionMode(value)
        except ValueError:
            pass
    raise _configuration_error(f"{where} has unrecognized decision_mode {value!r}")


def _validated_weights(value: Any, where: str) -> UtilityWeights | None:
    """Return the complete named weight schema, or ``None`` when unauthored.

    The field is additive: an archetype may stop at the four mandatory legacy
    fields, and a supplied mapping must then declare exactly the named schema.
    """
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise _configuration_error(
            f"{where} must declare a utility_weights mapping"
        )
    if set(value) != set(UTILITY_WEIGHT_NAMES):
        raise _configuration_error(
            f"{where} must declare exactly "
            f"{_format_keys(UTILITY_WEIGHT_NAMES)} utility weights"
        )
    resolved: dict[str, float] = {}
    for name in UTILITY_WEIGHT_NAMES:
        weight = value[name]
        if not _finite_real(weight):
            raise _configuration_error(
                f"{where} has non-finite or non-numeric {name} weight {weight!r}"
            )
        if weight < 0:
            raise _configuration_error(f"{where} has a negative {name} weight")
        resolved[name] = float(weight)
    return UtilityWeights(**resolved)


def _load_behaviour_profiles(
    rulebook: Any,
    *,
    tiers: Any = None,
) -> dict[str, BehaviourProfile]:
    """Validate rulebook tuning and build immutable behaviour profiles."""
    if not isinstance(rulebook, Mapping):
        raise _configuration_error("rulebook must be a mapping")
    archetypes = rulebook.get("archetypes")
    defaults = rulebook.get("tier_default_archetype")
    if not isinstance(archetypes, Mapping):
        raise _configuration_error("archetypes must be a mapping")
    if not isinstance(defaults, Mapping):
        raise _configuration_error("tier_default_archetype must be a mapping")
    tier_keys = set(MONSTER_TIER_REGISTRY if tiers is None else tiers)

    profiles: dict[str, BehaviourProfile] = {}
    for key, values in archetypes.items():
        if not isinstance(key, str) or not isinstance(values, Mapping):
            raise _configuration_error("each archetype must be a named mapping")
        declared = set(values)
        if not declared >= _MANDATORY_PROFILE_FIELDS:
            raise _configuration_error(
                f"archetype {key!r} must declare "
                f"{_format_keys(_MANDATORY_PROFILE_FIELDS)}"
            )
        unknown = declared - _MANDATORY_PROFILE_FIELDS - _OPTIONAL_PROFILE_FIELDS
        if unknown:
            raise _configuration_error(
                f"archetype {key!r} declares unknown fields {_format_keys(unknown)}"
            )
        target_strategy = values["target_strategy"]
        if (
            not isinstance(target_strategy, str)
            or target_strategy not in _TARGET_STRATEGIES
        ):
            raise _configuration_error(
                f"archetype {key!r} has unknown target_strategy {target_strategy!r}"
            )
        skill_choice = values["skill_choice"]
        if (
            not isinstance(skill_choice, str)
            or skill_choice not in _SKILL_CHOICES
        ):
            raise _configuration_error(
                f"archetype {key!r} has unknown skill_choice {skill_choice!r}"
            )
        prefer_area = values["prefer_area_when_multiple_enemies"]
        if type(prefer_area) is not bool:
            raise _configuration_error(
                f"archetype {key!r} has non-boolean area preference"
            )
        flee_fraction = values["flee_hp_fraction"]
        if flee_fraction is not None and (
            isinstance(flee_fraction, bool)
            or not isinstance(flee_fraction, Real)
            or not 0 <= flee_fraction <= 1
        ):
            raise _configuration_error(
                f"archetype {key!r} has invalid flee_hp_fraction"
            )
        profiles[key] = BehaviourProfile(
            target_strategy=target_strategy,
            skill_choice=skill_choice,
            prefer_area_when_multiple_enemies=prefer_area,
            flee_hp_fraction=(
                None if flee_fraction is None else float(flee_fraction)
            ),
            decision_mode=_validated_mode(
                values.get("decision_mode", _DEFAULT_DECISION_MODE),
                f"archetype {key!r}",
            ),
            utility_weights=_validated_weights(
                values.get("utility_weights"), f"archetype {key!r}"
            ),
        )

    if set(defaults) != tier_keys:
        raise _configuration_error(
            f"tier_default_archetype must map exactly {_format_keys(tier_keys)}"
        )
    for tier, archetype_key in defaults.items():
        if not isinstance(archetype_key, str) or archetype_key not in profiles:
            raise _configuration_error(
                f"tier default {tier!r} references unknown archetype {archetype_key!r}"
            )
    return profiles


BEHAVIOUR_PROFILES = _load_behaviour_profiles(MONSTER_BEHAVIOUR_YAML)


def _validated_budget(value: Any) -> int:
    """Return the authored candidate budget, rejecting anything else."""
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not MIN_CANDIDATE_BUDGET <= value <= MAX_CANDIDATE_BUDGET
    ):
        raise _configuration_error(
            f"candidate_budget must be an integer "
            f"{MIN_CANDIDATE_BUDGET}..{MAX_CANDIDATE_BUDGET}, got {value!r}"
        )
    return value


def _validated_variant_keys(
    value: Any,
    where: str,
    species: Any,
    variants: Any,
) -> Mapping[str, Any]:
    """Return a variant-keyed tuning mapping whose every key resolves as a pair."""
    if not isinstance(value, Mapping):
        raise _configuration_error(f"{where} must be a mapping")
    for key in value:
        if not isinstance(key, str):
            raise _configuration_error(f"{where} keys must be variant keys")
        variant = variants.get(key)
        if variant is None:
            raise _configuration_error(f"{where} names unregistered variant {key!r}")
        if variant.species_key not in species:
            raise _configuration_error(
                f"{where} variant {key!r} has no registered species relationship"
            )
    return value


def _validated_intelligence(
    value: Any,
    species: Any,
    variants: Any,
) -> dict[str, int]:
    """Return validated per-variant intelligence, inactive legacy entries included."""
    declared = _validated_variant_keys(
        value, "variant_intelligence", species, variants
    )
    resolved: dict[str, int] = {}
    for key, raw in declared.items():
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= 100:
            raise _configuration_error(
                f"variant_intelligence {key!r} must be an integer 0..100, got {raw!r}"
            )
        resolved[key] = raw
    return resolved


def _validated_variant_modes(
    value: Any,
    species: Any,
    variants: Any,
) -> dict[str, DecisionMode]:
    """Return the validated per-variant mode overrides."""
    declared = _validated_variant_keys(
        value, "variant_decision_mode", species, variants
    )
    return {
        key: _validated_mode(raw, f"variant_decision_mode {key!r}")
        for key, raw in declared.items()
    }


def _validate_utility_coverage(
    profiles: Mapping[str, BehaviourProfile],
    defaults: Mapping[str, str],
    variants: Any,
    intelligence: Mapping[str, int],
    modes: Mapping[str, DecisionMode],
) -> None:
    """Require every effective utility variant to author its intelligence.

    The authored binding is used here (the variant's own archetype reference,
    else its tier default), because startup can only validate authored data;
    runtime repair is re-validated per decision by :func:`resolve_monster_ai`.
    """
    for key, variant in variants.items():
        reference = variant.behaviour_profile_key
        archetype_key = (
            reference if reference is not None else defaults.get(variant.threat_tier)
        )
        profile = profiles.get(archetype_key)
        if profile is None:
            raise _configuration_error(
                f"variant {key!r} references unknown archetype {archetype_key!r}"
            )
        if modes.get(key, profile.decision_mode) is DecisionMode.UTILITY:
            if key not in intelligence:
                raise _configuration_error(
                    f"utility variant {key!r} declares no intelligence"
                )
            if profile.utility_weights is None:
                raise _configuration_error(
                    f"utility variant {key!r} binds an archetype with no "
                    f"utility weights"
                )


def _tuning_fingerprint(
    *,
    candidate_budget: int,
    defaults: Mapping[str, str],
    profiles: Mapping[str, BehaviourProfile],
    intelligence: Mapping[str, int],
    modes: Mapping[str, DecisionMode],
    bindings: Mapping[str, tuple[str, str | None]],
) -> str:
    """Fingerprint the canonical decision-relevant projection of one tuning.

    The projection carries stable identifiers, authored numbers and authored
    rulebook leaves only -- never a display name, object address or entity
    representation -- so identical tuning always fingerprints identically and
    a change to the algorithm, a mode, a weight, the budget, an intelligence
    value, a tier default, a behaviour leaf or a referenced variant's binding
    always changes it. It is the complete set of decision-relevant rulebook
    inputs this process consumes today (design section 5): the archetype
    decision leaves, the tier defaults and the referenced variant bindings.
    Estimator-side inputs join the same projection when the estimator itself
    lands.
    """
    payload = {
        "algorithm_version": AI_ALGORITHM_VERSION,
        "candidate_budget": candidate_budget,
        "tier_default_archetype": dict(sorted(defaults.items())),
        "archetypes": {
            key: {
                "target_strategy": profile.target_strategy,
                "skill_choice": profile.skill_choice,
                "prefer_area_when_multiple_enemies": (
                    profile.prefer_area_when_multiple_enemies
                ),
                "flee_hp_fraction": profile.flee_hp_fraction,
                "decision_mode": profile.decision_mode.value,
                "utility_weights": (
                    None
                    if profile.utility_weights is None
                    else profile.utility_weights.as_payload()
                ),
            }
            for key, profile in sorted(profiles.items())
        },
        "variant_intelligence": dict(sorted(intelligence.items())),
        "variant_decision_mode": {
            key: mode.value for key, mode in sorted(modes.items())
        },
        "variant_bindings": {
            key: [tier, reference]
            for key, (tier, reference) in sorted(bindings.items())
        },
    }
    encoded = dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _load_ai_tuning(
    rulebook: Any,
    *,
    profiles: Mapping[str, BehaviourProfile] | None = None,
    species: Any = None,
    variants: Any = None,
) -> MonsterAITuning:
    """Validate the whole AI tuning rulebook and fingerprint its resolved form.

    References, primitive types, numeric bounds, the complete named weight
    schema and utility activation coverage are all checked once at startup;
    the published record is immutable. The registries are injectable so a
    synthetic rulebook can be validated without naming shipped content.
    """
    if not isinstance(rulebook, Mapping):
        raise _configuration_error("rulebook must be a mapping")
    unknown = set(rulebook) - _TOP_LEVEL_FIELDS
    if unknown:
        raise _configuration_error(
            f"unknown top-level fields {_format_keys(unknown)}"
        )
    missing = _TOP_LEVEL_FIELDS - set(rulebook)
    if missing:
        raise _configuration_error(
            f"missing top-level fields {_format_keys(missing)}"
        )
    resolved_profiles = BEHAVIOUR_PROFILES if profiles is None else profiles
    species_rows = MONSTER_SPECIES_REGISTRY if species is None else species
    variant_rows = MONSTER_VARIANT_REGISTRY if variants is None else variants
    defaults = rulebook["tier_default_archetype"]
    budget = _validated_budget(rulebook["candidate_budget"])
    intelligence = _validated_intelligence(
        rulebook["variant_intelligence"], species_rows, variant_rows
    )
    modes = _validated_variant_modes(
        rulebook["variant_decision_mode"], species_rows, variant_rows
    )
    bindings = {
        key: (
            variant_rows[key].threat_tier,
            variant_rows[key].behaviour_profile_key,
        )
        for key in sorted(set(intelligence) | set(modes))
    }
    _validate_utility_coverage(
        resolved_profiles, defaults, variant_rows, intelligence, modes
    )
    return MonsterAITuning(
        algorithm_version=AI_ALGORITHM_VERSION,
        candidate_budget=budget,
        behaviour_profiles=MappingProxyType(dict(resolved_profiles)),
        tier_defaults=MappingProxyType(dict(defaults)),
        variant_intelligence=MappingProxyType(intelligence),
        variant_decision_mode=MappingProxyType(modes),
        variant_bindings=MappingProxyType(bindings),
        fingerprint=_tuning_fingerprint(
            candidate_budget=budget,
            defaults=defaults,
            profiles=resolved_profiles,
            intelligence=intelligence,
            modes=modes,
            bindings=bindings,
        ),
    )


MONSTER_AI_TUNING = _load_ai_tuning(MONSTER_BEHAVIOUR_YAML)


def _invalid_binding(fingerprint: str) -> MonsterAIDecision:
    """The typed state of a monster whose actual stored binding is unusable."""
    return MonsterAIDecision(
        mode=None,
        intelligence=None,
        archetype_key=None,
        variant_key=None,
        invalid_reason=InvalidDecisionReason.INVALID_BINDING,
        tuning_fingerprint=fingerprint,
    )


def resolve_monster_ai(
    monster: Any,
    *,
    tuning: MonsterAITuning | None = None,
) -> MonsterAIDecision | None:
    """Resolve one monster's effective mode and intelligence, or why it cannot.

    The resolution reads the monster's *actual* stored ``behaviour_tree`` and
    validates the species/variant pair against the registries, so a repaired
    binding or identity is honoured rather than a remembered one, and a
    variant string alone is never trusted: its override applies only once the
    pair resolves. An unset placeholder (no stored value, or the empty string)
    selects the tier default, while a stored value no archetype key can be
    read from -- an unknown key or a repaired non-string -- is reported as an
    unusable binding instead of being silently replaced by that default.
    ``None`` means the entity carries no ``threat_tier`` and is therefore not
    a registered-monster decision target; the delegated policy owns it.
    """
    if not hasattr(monster, "threat_tier"):
        return None
    resolved = MONSTER_AI_TUNING if tuning is None else tuning
    stored = _stored_binding(monster)
    tier = getattr(monster, "threat_tier", None)
    if stored is None or stored == "":
        archetype_key = resolved.tier_defaults.get(
            tier if isinstance(tier, str) else None
        )
    elif isinstance(stored, str):
        archetype_key = stored
    else:
        return _invalid_binding(resolved.fingerprint)
    profile = resolved.behaviour_profiles.get(archetype_key)
    if profile is None:
        return _invalid_binding(resolved.fingerprint)
    variant = _registered_variant(
        getattr(monster, "species_key", None),
        getattr(monster, "variant_key", None),
    )
    variant_key = None if variant is None else variant.key
    mode = resolved.variant_decision_mode.get(variant_key, profile.decision_mode)
    intelligence = (
        None
        if variant_key is None
        else resolved.variant_intelligence.get(variant_key)
    )
    reason = None
    if mode is DecisionMode.UTILITY:
        if variant_key is None:
            reason = InvalidDecisionReason.INVALID_IDENTITY
        elif intelligence is None:
            reason = InvalidDecisionReason.MISSING_INTELLIGENCE
    return MonsterAIDecision(
        mode=mode,
        intelligence=None if reason is not None else intelligence,
        archetype_key=archetype_key,
        variant_key=variant_key,
        invalid_reason=reason,
        tuning_fingerprint=resolved.fingerprint,
    )


def _profile_for(archetype_key: Any, tier: Callable[[], Any]) -> BehaviourProfile:
    """Resolve one archetype key, falling back to the tier default."""
    if not archetype_key:
        archetype_key = MONSTER_BEHAVIOUR_YAML["tier_default_archetype"][tier()]
    return BEHAVIOUR_PROFILES[archetype_key]


def resolve_behaviour_profile(monster: Any) -> BehaviourProfile:
    """Resolve an instance override or its threat tier's default profile."""
    return _profile_for(
        getattr(monster, "behaviour_tree", None), lambda: monster.threat_tier
    )


def read_behaviour_profile(monster: Any) -> BehaviourProfile:
    """Resolve the same profile without provisioning anything.

    ``resolve_behaviour_profile`` reads the autocreating ``behaviour_tree``
    descriptor; this read-only twin reads the stored Attribute instead, so a
    GM inspection (gm-portal-s3-runtime-state §2) never materializes it. The
    resolution itself is shared, so the two can never drift.
    """
    return _profile_for(_stored_binding(monster), lambda: monster.threat_tier)


def _stored_binding(monster: Any) -> Any:
    """Read ``behaviour_tree`` without materializing the Attribute.

    ``resolve_behaviour_profile`` reads the autocreating descriptor; a
    read-only consumer must not create anything, so the GM inspection and the
    AI resolution share this one stored read (a plain value object without an
    attribute handler exposes the binding as a plain attribute).
    """
    attributes = getattr(monster, "attributes", None)
    if attributes is None:
        return getattr(monster, "behaviour_tree", None)
    return attributes.get("behaviour_tree", default=None)


def _owned_damage_skills(entity: Any) -> list[SkillDef]:
    """Return affordable active damage skills in owned-key order."""
    return [
        SKILL_REGISTRY[key]
        for key in entity.skills.owned_keys()
        if key in SKILL_REGISTRY
        and SKILL_REGISTRY[key].kind is SkillKind.ACTIVE
        and can_use_skill(entity, SKILL_REGISTRY[key])
        and any(
            effect.startswith("damage:")
            for effect in SKILL_REGISTRY[key].effects
        )
        and all(
            _stored_trait_value(getattr(entity.traits, resource)) >= amount
            for resource, amount in SKILL_REGISTRY[key].cost.items()
        )
    ]


def _damage_school(skill: SkillDef) -> str:
    """Return the physical or magic school from a damage effect."""
    effect = next(
        effect for effect in skill.effects if effect.startswith("damage:")
    )
    school = combat._parse_damage_effect(effect).school
    return school


def _living_enemies(
    battlefield: Battlefield,
    actor: Any,
) -> list[Any]:
    """Return living, non-fled members of the opposing team.

    Knocked-out members are excluded through the shared predicate, so opposing
    combatants never select a knocked-out companion (party-combat D-2).
    """
    actor_team = battlefield.team_of(str(actor.key))
    enemy_keys = next(
        (
            members
            for team, members in battlefield.teams.items()
            if team != actor_team
        ),
        frozenset(),
    )
    return [
        battlefield.roster[key]
        for key in enemy_keys
        if key in battlefield.roster
        and key not in battlefield.fled
        and not battlefield.is_knocked_out(key)
        and combat._stored_hp(battlefield.roster[key]) > 0
    ]


def _should_flee(entity: Any, profile: BehaviourProfile) -> bool:
    """Return whether stored true HP has reached this profile's flee boundary."""
    threshold = profile.flee_hp_fraction
    maximum = combat._max_hp(entity)
    return (
        threshold is not None
        and maximum > 0
        and combat._stored_hp(entity) / maximum <= threshold
    )


def _choose_target(
    entity: Any,
    enemies: list[Any],
    strategy: str,
) -> Any:
    """Choose one enemy by the configured metric and seeded tie-break."""
    del entity
    if strategy == "lowest_hp":
        metric = lambda enemy: combat._stored_hp(enemy)
        best = min(metric(enemy) for enemy in enemies)
    elif strategy == "highest_effective_power":
        metric = combat.effective_power
        best = max(metric(enemy) for enemy in enemies)
    else:
        raise ValueError(f"unknown target_strategy: {strategy!r}")
    tied = sorted(
        (enemy for enemy in enemies if metric(enemy) == best),
        key=lambda enemy: str(enemy.key),
    )
    if len(tied) == 1:
        return tied[0]
    return tied[dice.roll_d100() % len(tied)]


def _choose_skill(
    entity: Any,
    candidates: list[SkillDef],
    strategy: str,
    target: Any | None,
) -> SkillDef:
    """Choose an eligible skill without consuming resolution dice."""
    if strategy == "first_owned":
        return candidates[0]
    if strategy != "highest_expected_damage":
        raise ValueError(f"unknown skill_choice: {strategy!r}")
    defender_defense = (
        combat._adjusted_defense(target) if target is not None else 0.0
    )

    def expected_damage(skill: SkillDef) -> float:
        attack_key = (
            "atk_phys"
            if _damage_school(skill) == "physical"
            else "magic_power"
        )
        return combat._adjusted_attack(entity, attack_key) - defender_defense

    best = max(expected_damage(skill) for skill in candidates)
    tied = [
        skill for skill in candidates if expected_damage(skill) == best
    ]
    if len(tied) == 1:
        return tied[0]
    return tied[dice.roll_d100() % len(tied)]


def monster_behaviour_policy(
    entity: Any,
    battlefield: Battlefield,
) -> ActionRequest | None:
    """Return one resolver-ready monster action for the current turn."""
    if not hasattr(entity, "threat_tier"):
        return combat.default_attack_policy(entity, battlefield)

    enemies = _living_enemies(battlefield, entity)
    if not enemies:
        return None
    profile = resolve_behaviour_profile(entity)
    if _should_flee(entity, profile):
        return ActionRequest(
            actor=entity,
            skill_key=FLEE_SKILL_KEY,
            targets=[entity],
            context=BattlefieldActionContext(
                battlefield,
                event_context={"battlefield": battlefield},
            ),
        )
    damage_skills = _owned_damage_skills(entity)
    single_skills = [
        skill
        for skill in damage_skills
        if skill.target_spec is TargetSpec.SINGLE
    ]
    area_skills = [
        skill
        for skill in damage_skills
        if skill.target_spec is TargetSpec.AREA
    ]
    use_area = (
        profile.prefer_area_when_multiple_enemies
        and len(enemies) > 1
        and bool(area_skills)
    ) or (not single_skills and bool(area_skills))
    context = BattlefieldActionContext(battlefield)
    if use_area:
        skill = _choose_skill(
            entity,
            area_skills,
            profile.skill_choice,
            target=None,
        )
        return ActionRequest(entity, skill.key, "all-enemies", context)
    if not single_skills:
        return None

    from world.rules.buffs import entity_active_buffs, has_positional_marker
    from world.rules.spell_conditions import is_strike_class

    # Lamb-seal narrowing (church design §5.7): BEFORE target-strategy
    # evaluation, if any living enemy carries lamb_seal the single-target
    # candidate base narrows to the seal-bearers in canonical order (player
    # first, then ascending pk). With no seal anywhere the base stays exactly
    # the living enemies, so every no-seal decision is byte-identical. AREA
    # paths already returned above; the positional-marker exclusion below
    # remains an orthogonal filter and is never substituted by the seal.
    sealed = [
        enemy for enemy in enemies if "lamb_seal" in entity_active_buffs(enemy)
    ]
    if sealed:
        from typeclasses.characters import PlayerCharacter

        sealed.sort(
            key=lambda enemy: (
                0 if isinstance(enemy, PlayerCharacter) else 1,
                int(getattr(enemy, "pk", 0) or 0),
            )
        )
        base = sealed
    else:
        base = enemies
    # Selection hygiene (design D6): a SINGLE-target kit that is exclusively
    # strike-class excludes displaced candidates; a monster owning magic-
    # school SINGLE damage keeps the full set and, against a displaced
    # target, selects only its gate-allowed (non-strike) skills. State-only
    # and dice-free; resolution-time gating stays the single authority.
    has_magic_single = any(not is_strike_class(skill) for skill in single_skills)
    if not has_magic_single:
        candidates = [enemy for enemy in base if not has_positional_marker(enemy)]
        if not candidates:
            return None
    else:
        candidates = base
    if sealed:
        # Multi-seal canonical order IS the target resolution: the first
        # seal-bearer is chosen without strategy-metric evaluation or
        # tie-break dice (the preference overrides the metric, design §5.7).
        target = candidates[0]
    else:
        target = _choose_target(entity, candidates, profile.target_strategy)
    if has_positional_marker(target):
        eligible_skills = [skill for skill in single_skills if not is_strike_class(skill)]
        if not eligible_skills:
            return None
    else:
        eligible_skills = single_skills
    skill = _choose_skill(entity, eligible_skills, profile.skill_choice, target)
    return ActionRequest(entity, skill.key, [target], context)
