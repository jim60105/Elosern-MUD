"""Species-backed monster individual construction (monster-data-model design section 4).

One deterministic entry point turns a validated species/variant pair into a
persistent ``Monster``: it validates both registry references and their
membership *before* anything is persisted, then applies the approved combat
configuration through the existing trait path. ``world.lore`` stays read-only;
this module is the mutation owner of the individual layer, so every spawn path
(placement, quest provisioning) calls :func:`construct_species_individual`.

Two boundaries are pinned here:

* **Identity is never inferred** (requirement R1). A display name, an object key,
  a threat tier, a quest role, or generative output never produces species
  identity: only the two validated registry keys do.
* **Derived truth is not editable** (requirement R2). ``threat_tier`` and
  ``danger_grade`` resolve from the variant record on every read, so nothing
  stores a copy that could drift away from the registry; a tier assignment on a
  species-backed individual is rejected instead.

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
from world.observability import log_info, log_warn
from world.rules.traits import initial_trait_config_for_variant


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


def resolve_variant(species_key: object, variant_key: object) -> MonsterVariant:
    """Return the registered variant this identity names, validated as a pair.

    Both keys must resolve in the shipped registries and the variant must belong
    to the supplied species; anything else raises the named identity error, so no
    caller can build (or read) an individual whose identity is half-resolved.
    """
    if not isinstance(species_key, str) or not species_key:
        raise MonsterIdentityError("species-backed monster has no species key")
    if not isinstance(variant_key, str) or not variant_key:
        raise MonsterIdentityError("species-backed monster has no variant key")
    if species_key not in MONSTER_SPECIES_REGISTRY:
        raise MonsterIdentityError(f"unknown monster species {species_key!r}")
    variant = MONSTER_VARIANT_REGISTRY.get(variant_key)
    if variant is None:
        raise MonsterIdentityError(f"unknown monster variant {variant_key!r}")
    if variant.species_key != species_key:
        raise MonsterIdentityError(
            f"monster variant {variant_key!r} belongs to species "
            f"{variant.species_key!r}, not {species_key!r}"
        )
    return variant


def resolve_individual_tier(individual: Any, stored_tier: object) -> Any:
    """Return a monster's threat tier: derived for species-backed, stored otherwise.

    A tier-only individual (no species identity) keeps the plain attribute, so
    wilderness and scene-materialization callers are untouched; a species-backed
    individual reads its variant's declared tier instead of any stored copy.
    """
    if getattr(individual, "species_key", None) is None:
        return stored_tier
    return resolve_variant(individual.species_key, individual.variant_key).threat_tier


def guard_individual_tier_write(individual: Any, value: object) -> None:
    """Reject a threat-tier assignment on a species-backed individual.

    The assignment is rejected outright — not stored when it happens to agree —
    because a stored copy is exactly the drift requirement R2 forbids once the
    variant's registered tier changes. Tier-only individuals are not guarded.
    """
    if getattr(individual, "species_key", None) is None:
        return
    variant = resolve_variant(individual.species_key, individual.variant_key)
    raise MonsterTierConflictError(
        f"monster tier {value!r} cannot be assigned: variant {variant.key!r} "
        f"derives tier {variant.threat_tier!r} and stores no copy"
    )


def individual_danger_grade(individual: Any) -> str | None:
    """Return the individual's danger grade, resolved from its variant record.

    A tier-only individual carries no grade: the tier registry documents none,
    and nothing stores one that could disagree with the registry.
    """
    if getattr(individual, "species_key", None) is None:
        return None
    return resolve_variant(individual.species_key, individual.variant_key).danger_grade


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
    source) completes before anything is persisted, so a rejected construction
    leaves no partially built individual behind. Call this inside the caller's
    ``transaction.atomic()`` — that transaction is the real rollback boundary;
    a failure after the row is written compensates by deleting it.
    """
    try:
        variant = resolve_variant(species_key, variant_key)
        config, numeric_source = initial_trait_config_for_variant(variant, position)
    except Exception as error:
        raise MonsterConstructionError(
            f"cannot construct variant {variant_key!r} of species {species_key!r}"
        ) from error

    from evennia.utils.create import create_object
    from typeclasses.monsters import Monster

    individual = create_object(
        Monster, key=key if key is not None else variant.display_name_zh
    )
    try:
        individual.species_key = species_key
        individual.variant_key = variant_key
        individual._apply_trait_config(config)
    except Exception as error:
        _discard_individual(individual, species_key, variant_key)
        raise MonsterConstructionError(
            f"failed to apply the combat configuration for variant {variant_key!r}"
        ) from error
    _schedule_construction_event(individual.pk, species_key, variant_key, numeric_source)
    return individual


def _discard_individual(
    individual: Any, species_key: str, variant_key: str
) -> None:
    """Compensate a failed construction by deleting the freshly created row.

    Deletion can itself fail (a vetoing delete hook, a concurrent removal); that
    must never mask the construction failure, so it is reported through the
    facade and contained here — the caller's transaction remains the rollback
    boundary for any residue.
    """
    try:
        individual.delete()
    except Exception as error:  # noqa: BLE001 - contained compensate step, logged below
        log_warn(
            "monster_individual_discard_failed",
            exc=error,
            context={
                "individual": getattr(individual, "pk", None),
                "species": species_key,
                "variant": variant_key,
            },
        )


def _schedule_construction_event(
    individual_pk: int | None,
    species_key: str,
    variant_key: str,
    numeric_source: str,
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
            },
        )
    )
