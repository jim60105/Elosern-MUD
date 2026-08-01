"""Player character typeclasses from design section 5.2 (entity-traits)."""

from evennia.typeclasses.attributes import AttributeProperty

from .entities import LivingEntity


class PlayerCharacter(LivingEntity):
    """A player-controlled living entity with deferred progression seams."""

    age: int | None = AttributeProperty(default=None)
    apparent_age: int | None = AttributeProperty(default=None)
    creation_pending: bool = AttributeProperty(default=False)
    guild_rank: str | None = AttributeProperty(default=None)
    quest_log: list = AttributeProperty(default=list)
    wallet: int = AttributeProperty(default=0)

    def at_cmdset_get(self, **kwargs) -> None:
        """Derive the creation gate from persistent state for every merge."""
        gate = "commands.character_creation.CharacterCreationCmdSet"
        if self.creation_pending and not self.cmdset.has(gate):
            self.cmdset.add(gate, persistent=False)
        elif not self.creation_pending and self.cmdset.has(gate):
            self.cmdset.remove(gate)
        return super().at_cmdset_get(**kwargs)

    def at_pre_move(self, destination, move_type="move", **kwargs) -> bool:
        """Block every traversal while an active combat session is running."""
        from world.rules.combat_session import is_in_active_session

        if is_in_active_session(self):
            return False
        return super().at_pre_move(destination, move_type=move_type, **kwargs)


class Character(PlayerCharacter):
    """Evennia's conventional default-character path."""
