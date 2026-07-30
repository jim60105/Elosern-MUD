"""NPC typeclass from design section 5.2 (entity-traits)."""

from typing import Any

from evennia.typeclasses.attributes import AttributeProperty

from .entities import LivingEntity


class NPC(LivingEntity):
    """A non-player living entity with deferred dialogue and schedule seams."""

    dialogue_memory: Any | None = AttributeProperty(default=None)
    schedule: Any | None = AttributeProperty(default=None)
