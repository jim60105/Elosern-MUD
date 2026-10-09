"""Species-backed monster individual construction (monster-data-model design section 4).

One deterministic entry point turns a validated species/variant pair into a
persistent ``Monster``: it validates both registry references and their
membership *before* anything is persisted, then applies the approved combat
configuration through the existing trait path. ``world.lore`` stays read-only;
this module is the mutation owner of the individual layer, so every spawn path
(placement, quest provisioning) calls :func:`construct_species_individual`.

Three boundaries are pinned here:

* **Identity is never inferred and never half-assigned** (requirement R1). Only
  the two validated registry keys carry species identity, and they are written
  through guarded attributes that accept one registered species/variant pair
  (variant first), so a display name, an object key, a tier, a quest role, or
  generative output can never produce identity, and no writer can leave an
  individual with an identity no read could resolve.
* **Derived truth is not editable** (requirement R2). ``threat_tier`` and
  ``danger_grade`` resolve from the variant record on every read, so nothing
  stores a copy that could drift away from the registry; a tier assignment on a
  species-backed individual is rejected instead.
* **Reads never raise** — every consumer reads the tier as optional
  (``getattr(entity, "threat_tier", None)``), so an identity that no longer
  resolves (a retired variant record) degrades to the same optional value
  instead of breaking rendering or combat for an unrelated surface.

Construction emits one ``monster_individual_constructed`` boundary info event
through the ``world.observability`` facade, naming the individual, species,
variant and the ``numeric_source`` that built it (``approved_profile`` or the
documented ``interim_tier_band``). The event fires only on a durable commit
(``transaction.on_commit``), so a rolled-back construction leaves no trace.
"""

from typing import Any

from world.lore.monster_species import (
    MONSTER_SPECIES_REGISTRY,
    MONSTER_VARIANT_REGISTRY,
    MonsterVariant,
)
from world.observability import log_info
from world.rules.traits import initial_trait_config_for_variant
from world.skills.registry import SKILL_REGISTRY, SkillKind
from world.skills.eligibility import record_identity_eligible


def _validate_variant_kit_and_behaviour(variant: MonsterVariant, species_key: str) -> None:
    """Validate full kit, skill references, kinds, eligibility, effects and behaviour profile."""
    from world.rules.monster_behaviour import MONSTER_BEHAVIOUR_YAML
    from world.rules.action.contracts import _EFFECT_HANDLERS, _effect_prefix

    for skill_key in variant.active_skill_keys:
        if skill_key not in SKILL_REGISTRY:
            raise MonsterConstructionError(f"unknown active skill {skill_key!r}")
        skill = SKILL_REGISTRY[skill_key]
        if skill.kind is not SkillKind.ACTIVE:
            raise MonsterConstructionError(f"active skill {skill_key!r} is not ACTIVE")
        if not record_identity_eligible(
            skill.eligibility, "monster", species_key=species_key, variant_key=variant.key
        ):
            raise MonsterConstructionError(f"monster not eligible for skill {skill_key!r}")
        for eff in skill.effects:
            if _effect_prefix(eff) not in _EFFECT_HANDLERS:
                raise MonsterConstructionError(f"unsupported effect {eff!r}")
        for prereq in skill.prerequisites:
            if prereq.skill_key not in variant.active_skill_keys and prereq.skill_key not in variant.passive_skill_keys:
                raise MonsterConstructionError(f"unusable prerequisite {prereq.skill_key!r}")

    for skill_key in variant.passive_skill_keys:
        if skill_key not in SKILL_REGISTRY:
            raise MonsterConstructionError(f"unknown passive skill {skill_key!r}")
        skill = SKILL_REGISTRY[skill_key]
        if skill.kind is not SkillKind.PASSIVE:
            raise MonsterConstructionError(f"passive skill {skill_key!r} is not PASSIVE")
        if not record_identity_eligible(
            skill.eligibility, "monster", species_key=species_key, variant_key=variant.key
        ):
            raise MonsterConstructionError(f"monster not eligible for skill {skill_key!r}")
        for eff in skill.effects:
            if _effect_prefix(eff) not in _EFFECT_HANDLERS:
                raise MonsterConstructionError(f"unsupported effect {eff!r}")

    if variant.behaviour_profile_key is not None:
        archetypes = MONSTER_BEHAVIOUR_YAML.get("archetypes", {})
        if variant.behaviour_profile_key not in archetypes:
            raise MonsterConstructionError(f"unknown behaviour profile {variant.behaviour_profile_key!r}")


class MonsterIdentityError(ValueError):
    """An individual's species/variant identity, or the truth derived from it, was violated."""


class MonsterConstructionError(MonsterIdentityError):
    """A species-backed individual could not be constructed."""


class MonsterTierConflictError(MonsterIdentityError):
    """A write attempted to assign a species-backed individual's derived threat tier.

    The tier is not independently editable truth for such an individual: it
    resolves from the variant record on every read, and a contradicting stored
    value is exactly the drift this rejects.
    """


def _registered_variant(species_key: object, variant_key: object) -> MonsterVariant | None:
    """The variant these keys name when the pair resolves, else ``None``.

    The lenient half of the module's validation: the read path and the write
    guards use it so an unresolvable identity can be reported or degraded
    without raising from inside an ``at_get``.
    """
    if not isinstance(species_key, str) or not species_key:
        return None
    if not isinstance(variant_key, str) or not variant_key:
        return None
    if species_key not in MONSTER_SPECIES_REGISTRY:
        return None
    variant = MONSTER_VARIANT_REGISTRY.get(variant_key)
    if variant is None or variant.species_key != species_key:
        return None
    return variant


def resolve_variant(species_key: object, variant_key: object) -> MonsterVariant:
    """Return the registered variant this identity names, validated as a pair.

    Both keys must resolve in the shipped registries and the variant must belong
    to the supplied species. The strict half of the module's validation: the
    construction entry point uses it, so anything else raises the named identity
    error and no individual is built from a half-resolved identity.
    """
    variant = _registered_variant(species_key, variant_key)
    if variant is not None:
        return variant
    if not isinstance(species_key, str) or not species_key:
        raise MonsterIdentityError("species-backed monster has no species key")
    if species_key not in MONSTER_SPECIES_REGISTRY:
        raise MonsterIdentityError(f"unknown monster species {species_key!r}")
    if not isinstance(variant_key, str) or not variant_key:
        raise MonsterIdentityError("species-backed monster has no variant key")
    known = MONSTER_VARIANT_REGISTRY.get(variant_key)
    if known is None:
        raise MonsterIdentityError(f"unknown monster variant {variant_key!r}")
    raise MonsterIdentityError(
        f"monster variant {variant_key!r} belongs to species "
        f"{known.species_key!r}, not {species_key!r}"
    )


def resolve_individual_tier(individual: Any, stored_tier: object) -> Any:
    """Return a monster's threat tier: derived for species-backed, stored otherwise.

    A tier-only individual (no species identity) keeps the plain attribute, so
    wilderness and scene-materialization callers are untouched; a species-backed
    individual reads its variant's declared tier instead of any stored copy.

    A read never raises. When the identity cannot resolve — a registry edit
    retired the variant record, or a raw ``.db`` write left a pair this module
    would not accept — the stored value is returned (``None`` for an
    identity-bearing individual, which stores no tier), because every consumer
    reads this attribute as optional and an unrelated surface must not break.
    """
    species_key = getattr(individual, "species_key", None)
    if species_key is None:
        return stored_tier
    variant = _registered_variant(
        species_key, getattr(individual, "variant_key", None)
    )
    return stored_tier if variant is None else variant.threat_tier


def guard_individual_tier_write(individual: Any, value: object) -> None:
    """Reject a threat-tier assignment on a species-backed individual.

    The assignment is rejected outright — not stored when it happens to agree —
    because a stored copy is exactly the drift requirement R2 forbids once the
    variant's registered tier changes. Tier-only individuals are not guarded.
    """
    if getattr(individual, "species_key", None) is None:
        return
    variant = _registered_variant(
        individual.species_key, getattr(individual, "variant_key", None)
    )
    derived = "its variant record" if variant is None else f"variant {variant.key!r}"
    raise MonsterTierConflictError(
        f"monster tier {value!r} cannot be assigned: {derived} derives this "
        "individual's tier and stores no copy"
    )


def guard_individual_species_key_write(individual: Any, value: object) -> None:
    """Reject a species key that cannot form one registered identity pair.

    Identity is written variant-first (the construction entry point assigns
    ``variant_key`` and then ``species_key``), so a species key is accepted only
    when the individual already carries a variant of exactly that species: a
    species key alone would be an identity no read could resolve.
    """
    if value is None:
        return
    if not isinstance(value, str) or value not in MONSTER_SPECIES_REGISTRY:
        raise MonsterIdentityError(f"unknown monster species {value!r}")
    variant_key = getattr(individual, "variant_key", None)
    variant = MONSTER_VARIANT_REGISTRY.get(variant_key)
    if variant is None or variant.species_key != value:
        raise MonsterIdentityError(
            f"species key {value!r} cannot pair with variant {variant_key!r}: "
            "identity is written variant-first and must be one registered pair"
        )


def guard_individual_variant_key_write(individual: Any, value: object) -> None:
    """Reject a variant key that does not resolve, or that contradicts the species key."""
    if value is None:
        return
    if not isinstance(value, str) or value not in MONSTER_VARIANT_REGISTRY:
        raise MonsterIdentityError(f"unknown monster variant {value!r}")
    species_key = getattr(individual, "species_key", None)
    if species_key is None:
        return
    variant = MONSTER_VARIANT_REGISTRY[value]
    if variant.species_key != species_key:
        raise MonsterIdentityError(
            f"monster variant {value!r} belongs to species "
            f"{variant.species_key!r}, not {species_key!r}"
        )


def individual_danger_grade(individual: Any) -> str | None:
    """Return the individual's danger grade, resolved from its variant record.

    A tier-only individual carries no grade — the tier registry documents none,
    and nothing stores one that could disagree — and an identity that no longer
    resolves degrades to ``None`` for the same no-raising reason as the tier.
    """
    species_key = getattr(individual, "species_key", None)
    if species_key is None:
        return None
    variant = _registered_variant(
        species_key, getattr(individual, "variant_key", None)
    )
    return None if variant is None else variant.danger_grade


def construct_species_individual(
    species_key: str,
    variant_key: str,
    *,
    key: str | None = None,
    position: str = "floor",
) -> Any:
    """Create one species-backed ``Monster`` and return it.

    ``key`` is the object's display label only (defaulting to the variant's
    approved display text); identity is carried by the two registry keys and is
    never derived from a display name. The signature accepts no player, level,
    clock, or progression input at all, so no scaling can be threaded through
    this surface, and ``position`` only selects a documented point inside the
    declared tier band.

    Validation (species/variant keys, their membership, and the resolved numeric
    source) completes before anything is persisted, and the create/assign/apply
    sequence runs inside its own ``transaction.atomic()`` block, so a failure at
    any point — including inside Evennia's own creation hooks — leaves no
    partially built individual behind and surfaces as the named construction
    error. A caller wrapping this in a larger transaction still governs the final
    commit; the boundary event is scheduled on that commit.
    """
    try:
        variant = resolve_variant(species_key, variant_key)
        config, numeric_source = initial_trait_config_for_variant(variant, position)
        _validate_variant_kit_and_behaviour(variant, species_key)
    except Exception as error:
        raise MonsterConstructionError(
            f"cannot construct variant {variant_key!r} of species {species_key!r}"
        ) from error

    from django.db import transaction
    from evennia.utils.create import create_object
    from typeclasses.monsters import Monster

    try:
        with transaction.atomic():
            individual = create_object(
                Monster, key=key if key is not None else variant.display_name_zh
            )
            individual.variant_key = variant_key
            individual.species_key = species_key
            individual._apply_trait_config(config)
            if variant.active_skill_keys or variant.passive_skill_keys:
                individual.db.skills = {
                    "active": list(variant.active_skill_keys),
                    "passive": list(variant.passive_skill_keys),
                }
            individual.db.behaviour_tree = variant.behaviour_profile_key
    except Exception as error:
        raise MonsterConstructionError(
            f"failed to build variant {variant_key!r} of species {species_key!r}"
        ) from error
    _schedule_construction_event(
        individual.pk, species_key, variant_key, numeric_source,
        kit=(*variant.active_skill_keys, *variant.passive_skill_keys),
        profile=variant.behaviour_profile_key,
    )
    return individual


def _schedule_construction_event(
    individual_pk: int | None,
    species_key: str,
    variant_key: str,
    numeric_source: str,
    kit: tuple[str, ...] = (),
    profile: str | None = None,
) -> None:
    """Record the construction boundary on durable commit.

    Same commit contract as the other rules boundary events: a construction that
    rolls back with its caller's transaction must not leave a log line for an
    individual that never existed.
    """
    from django.db import transaction

    transaction.on_commit(
        lambda: log_info(
            "monster_individual_constructed",
            context={
                "individual": individual_pk,
                "species": species_key,
                "variant": variant_key,
                "numeric_source": numeric_source,
                "kit": kit,
                "profile": profile,
            },
        )
    )
