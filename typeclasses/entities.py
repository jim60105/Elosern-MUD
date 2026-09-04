"""Shared living-entity typeclass from design section 5.2 (entity-traits)."""

from copy import deepcopy
from typing import Any

from evennia.contrib.base_systems.components import ComponentHolderMixin
from evennia.contrib.rpg.buffs import BuffHandler
from evennia.contrib.rpg.traits import TraitHandler
from evennia.objects.objects import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import lazy_property

from world.lore.sex import DEFAULT_SEX
from world.skills.equipment import EquipmentHandler
from world.skills.handler import SkillHandler
from world.rules.affinity import RelationHandler
from world.rules.persona import PersonaStore
from world.rules.sexual_state import SexualState

from .objects import ObjectParent


class LivingEntity(ComponentHolderMixin, ObjectParent, DefaultCharacter):
    """Base typeclass shared by player characters, NPCs, and monsters."""

    race: str | None = AttributeProperty(default=None)
    subrace: str | None = AttributeProperty(default=None)
    sex: str = AttributeProperty(default=DEFAULT_SEX)

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
    def relations(self) -> RelationHandler:
        """Persistent per-player affinity store (hidden values)."""
        return RelationHandler(self)

    @lazy_property
    def persona(self) -> PersonaStore:
        """Read-only verbatim persona-record handler.

        Persona records are written only by the import loader, the
        ``world/rules`` deterministic services, or the scene-builder
        characterization seam.
        """
        return PersonaStore(self)

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

    def get_display_desc(self, looker=None, **kwargs) -> str:
        """Append the displayed-stats block and the persona block to the desc.

        The blocks are rendered by the shared appearance layer (the same frame
        the text 看 command, the ``at_look`` hook, and the webclient
        explore-look action use). The displayed-stats block appears when the
        entity has at least one valid displayed row; the flattened persona
        block (including 背景 when present) appears when the entity's persona
        record has content. Entities without a persona (e.g. monsters) render
        no persona block (the blocks are part of the appearance, never
        gating any behavior).
        The composed full title (title-system D6) adds one ``稱號：…`` line
        between the stats block and the persona block whenever the entity
        occupies a title slot; an untitled entity — or one whose title state
        is malformed — renders exactly the pre-change description.
        """
        desc = super().get_display_desc(looker, **kwargs)
        from world.rules.displayed_stats import display_stat_block

        block = display_stat_block(self, looker=looker)
        if block:
            desc = f"{desc}\n{block}"
        from world.rules.titles import safe_full_title

        full_title = safe_full_title(self)
        if full_title:
            desc = f"{desc}\n稱號：{full_title}"
        persona_block = self.persona.flatten(
            ("personality", "life_story", "habit", "background")
        )
        if persona_block:
            desc = f"{desc}\n\n{persona_block}"
        return desc
