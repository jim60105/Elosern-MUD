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
    onboarded: bool = AttributeProperty(default=False)
    onboarding_beat: str | None = AttributeProperty(default=None)
    guide_progress: dict = AttributeProperty(default=dict)
    first_arrival_seen: bool = AttributeProperty(default=False)
    # Server-owned creation-wizard staging draft (webclient-character-creation-
    # ui D3). The single-writer rule is enforced by code review: every write
    # routes through world.rules.creation_wizard, which is the sole writer.
    # It is staging state, not canonical identity; it is cleared atomically
    # with activation and never sets age/race/traits/creation_pending.
    # autocreate=False so reading the property never materializes an empty
    # staging attribute on every pending shell.
    creation_draft: dict | None = AttributeProperty(default=None, autocreate=False)

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

    def at_look(self, target, **kwargs) -> str:
        """Advance the arrival ``look`` beat after a successful look at the gate.

        The onboarding service guards on room + state, so a look elsewhere (or a
        look that fails) never advances the beat. On a successful advance the
        guard-guidance prompt is appended to the returned look text.
        """
        look_string = super().at_look(target, **kwargs)
        if not self.creation_pending:
            from world.rules.onboarding import advance_beat

            guidance = advance_beat(self)
            if guidance:
                look_string = f"{look_string}\n\n{guidance}"
        return look_string


class Character(PlayerCharacter):
    """Evennia's conventional default-character path."""
