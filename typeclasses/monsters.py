"""Monster typeclass from design section 5.2 (entity-traits)."""

from typing import Any

from evennia.typeclasses.attributes import AttributeProperty

from world.rules.monster_individual import (
    MonsterIdentityError,
    guard_individual_tier_write,
    individual_danger_grade,
    resolve_individual_tier,
)

from .entities import LivingEntity


class _VariantResolvedThreatTier(AttributeProperty):
    """``threat_tier`` for a ``Monster`` (monster-data-model design section 4).

    A tier-only individual keeps the plain stored attribute it always had; a
    species-backed individual resolves its tier from the variant record on every
    read, and an assignment is rejected by the deterministic owner rather than
    stored as a copy that could drift once the registry changes.

    ``autocreate=False`` is deliberate: Evennia's object-creation path fetches
    every ``AttributeProperty`` and swallows whatever it raises, so an
    autocreating ``at_set`` (which runs there with the ``None`` default) could
    silently leave the attribute missing. Without autocreation the default read
    goes through ``at_get``, which resolves deterministically and stores nothing.
    """

    def at_get(self, value: str | None, obj: Any) -> str | None:
        return resolve_individual_tier(obj, value)

    def at_set(self, value: str | None, obj: Any) -> str | None:
        guard_individual_tier_write(obj, value)
        return value


class Monster(LivingEntity):
    """A tier-scaled monster with deferred loot and behaviour seams.

    ``species_key``/``variant_key`` are the persistent identity of a
    species-backed individual, set only by the deterministic construction entry
    point (``world.rules.monster_individual.construct_species_individual``);
    a display name never carries identity. For such an individual the threat
    tier and danger grade are derived reads of the variant record, so no stored
    field is left holding truth that could contradict the registry.
    """

    species_key: str | None = AttributeProperty(default=None, autocreate=False)
    variant_key: str | None = AttributeProperty(default=None, autocreate=False)
    threat_tier: str | None = _VariantResolvedThreatTier(
        default=None, autocreate=False
    )
    loot_table: list = AttributeProperty(default=list)
    behaviour_tree: Any | None = AttributeProperty(default=None)

    @property
    def danger_grade(self) -> str | None:
        """The individual's danger grade, resolved from its variant record.

        A tier-only individual resolves ``None``: the tier registry documents no
        per-tier grade, and nothing stores one that could disagree.
        """
        return individual_danger_grade(self)

    def apply_monster_tier(self, position: str = "floor") -> None:
        """Populate traits from the named threat tier (the tier-only path).

        A species-backed individual's configuration comes from the construction
        entry point; re-applying a tier band over it would silently discard an
        approved profile, so this path refuses identity-bearing individuals.
        """
        if self.species_key is not None:
            raise MonsterIdentityError(
                "a species-backed monster's traits come from its construction "
                "entry point, not the tier band"
            )
        if self.threat_tier is None:
            raise ValueError("threat_tier must be set before applying a monster tier")

        from world.rules.traits import initial_trait_config_for_monster_tier

        self._apply_trait_config(
            initial_trait_config_for_monster_tier(self.threat_tier, position)
        )
