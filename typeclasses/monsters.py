"""Monster typeclass from design section 5.2 (entity-traits)."""

from typing import Any

from evennia.typeclasses.attributes import AttributeProperty

from .entities import LivingEntity


class Monster(LivingEntity):
    """A tier-scaled monster with deferred loot and behaviour seams."""

    threat_tier: str | None = AttributeProperty(default=None)
    loot_table: list = AttributeProperty(default=list)
    behaviour_tree: Any | None = AttributeProperty(default=None)

    def apply_monster_tier(self, position: str = "floor") -> None:
        """Populate traits after a caller has assigned ``threat_tier``."""
        if self.threat_tier is None:
            raise ValueError("threat_tier must be set before applying a monster tier")

        from world.rules.traits import initial_trait_config_for_monster_tier

        self._apply_trait_config(
            initial_trait_config_for_monster_tier(self.threat_tier, position)
        )
