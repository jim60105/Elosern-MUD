"""Shared living-entity typeclass from design section 5.2 (entity-traits)."""

from copy import deepcopy
from typing import Any

from evennia.contrib.base_systems.components import ComponentHolderMixin
from evennia.contrib.rpg.buffs import BuffHandler
from evennia.contrib.rpg.traits import TraitHandler
from evennia.objects.objects import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import lazy_property

from world.skills.equipment import EquipmentHandler
from world.skills.handler import SkillHandler
from world.rules.sexual_state import SexualState

from .objects import ObjectParent


class LivingEntity(ComponentHolderMixin, ObjectParent, DefaultCharacter):
    """Base typeclass shared by player characters, NPCs, and monsters."""

    race: str | None = AttributeProperty(default=None)
    subrace: str | None = AttributeProperty(default=None)

    # Declared handler seams; their owning changes replace these placeholders.
    relations: Any | None = AttributeProperty(default=None)  # unassigned
    persona: Any | None = AttributeProperty(default=None)  # import-contract candidate

    @lazy_property
    def traits(self) -> TraitHandler:
        """Persistent deterministic trait storage."""
        return TraitHandler(self)

    @lazy_property
    def buffs(self) -> BuffHandler:
        """Persistent status-effect handler."""
        return BuffHandler(self)

    @lazy_property
    def sexual(self) -> SexualState:
        """Persistent deterministic sexual-state handler."""
        return SexualState(self)

    @lazy_property
    def equipment(self) -> EquipmentHandler:
        """Persistent equipment-slot handler."""
        return EquipmentHandler(self)

    @lazy_property
    def skills(self) -> SkillHandler:
        """Imported skill ownership and effective-value handler."""
        return SkillHandler(self)

    def at_object_creation(self) -> None:
        """Initialize storage without guessing a race or threat tier."""
        super().at_object_creation()
        self.db.disguised_stats = None
        # Materialize the handler; traits are populated explicitly once identity is known.
        self.traits

    def _apply_trait_config(self, config: dict[str, dict[str, Any]]) -> None:
        """Replace this entity's trait set from validated construction config."""
        previous = deepcopy(dict(self.traits.trait_data))
        try:
            self.traits.clear()
            for trait_key, properties in config.items():
                self.traits.add(trait_key, **properties)
        except Exception:
            self.traits.clear()
            self.traits.trait_data.update(previous)
            self.traits._cache.clear()
            raise

    def apply_race_baseline(self, tier: str | None = None) -> None:
        """Populate traits after a caller has assigned ``race`` and ``subrace``."""
        if self.race is None:
            raise ValueError("race must be set before applying a race baseline")

        from world.rules.traits import initial_trait_config

        self._apply_trait_config(initial_trait_config(self.race, self.subrace, tier))
