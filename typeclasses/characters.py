"""Player character typeclasses from design section 5.2 (entity-traits)."""

from evennia.typeclasses.attributes import AttributeProperty

from .entities import LivingEntity


class PlayerCharacter(LivingEntity):
    """A player-controlled living entity with deferred progression seams."""

    guild_rank: str | None = AttributeProperty(default=None)
    quest_log: list = AttributeProperty(default=list)
    wallet: int = AttributeProperty(default=0)

    def at_pre_move(self, destination, move_type="move", **kwargs) -> bool:
        """Block every traversal while an active combat session is running."""
        from world.rules.combat_session import is_in_active_session

        if is_in_active_session(self):
            return False
        return super().at_pre_move(destination, move_type=move_type, **kwargs)


class Character(PlayerCharacter):
    """Evennia's conventional default-character path."""
