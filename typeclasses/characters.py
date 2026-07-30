"""Player character typeclasses from design section 5.2 (entity-traits)."""

from evennia.typeclasses.attributes import AttributeProperty

from .entities import LivingEntity


class PlayerCharacter(LivingEntity):
    """A player-controlled living entity with deferred progression seams."""

    guild_rank: str | None = AttributeProperty(default=None)
    quest_log: list = AttributeProperty(default=list)
    wallet: int = AttributeProperty(default=0)


class Character(PlayerCharacter):
    """Evennia's conventional default-character path."""
