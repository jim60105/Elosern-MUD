"""Player character typeclasses from design section 5.2 (entity-traits)."""

from typing import Any

from evennia.typeclasses.attributes import AttributeProperty

from world.observability import log_warn

from .entities import LivingEntity


def _schedule_action_options_after_move(actor: Any) -> None:
    """Register the action-options trigger to run after the move commits.

    The room-entry trigger must never run inside the movement transaction's
    critical section: a rollback would leave suggestions derived from a room
    the player never reached. The scheduling is therefore registered through
    ``transaction.on_commit`` (the ``commands/scene.py`` precedent), so it
    runs only after the settlement transaction commits — or immediately when
    no outer transaction is active. The gate and the fire-and-forget call
    happen inside the committed callback; every synchronous failure is logged
    as a bounded diagnostic and swallowed, never altering settlement.
    """
    from django.db import transaction

    transaction.on_commit(
        lambda: _schedule_action_options_committed(actor)
    )


def _schedule_action_options_committed(actor: Any) -> None:
    """The committed relocation trigger: puppeted-player gate, then schedule.

    Only a puppeted ``PlayerCharacter`` moves through ``at_post_move`` (NPC
    and monster moves, and rollback compensations with ``move_hooks=False``,
    stay silent). The service import is function-local (the ``commands/
    scene.py`` precedent) and every synchronous failure is logged as a bounded
    diagnostic and swallowed: the trigger never alters movement and never
    raises into its caller.
    """
    if not isinstance(actor, PlayerCharacter):
        return
    if getattr(actor, "account", None) is None:
        return
    try:
        from server.option_proposal_service import schedule_action_options
        from web.webclient.presentation.watchers import watchers_for

        schedule_action_options(
            actor,
            watchers=watchers_for(actor),
        )
    except Exception as error:
        log_warn(
            "action_options_trigger_failed",
            context={"char": str(getattr(actor, "pk", "?")), "trigger": "relocation"},
            exc=error,
        )


def _schedule_nomination_on_logout(character: Any) -> None:
    """Logout rest-point trigger (title-system D4 §7.1, change G).

    ``at_post_unpuppet`` runs after the disconnect transition completed, so
    this is a committed rest point by construction. The composition-root
    import is function-local (the ``commands/scene.py`` precedent) and every
    failure is swallowed with a bounded diagnostic: logging out can never be
    broken by nomination, and the whole stage is a silent no-op offline.
    Watchers are empty by definition — the ballot survives in ``db`` and the
    next session's full snapshot renders it.
    """
    try:
        from server.title_nomination_service import schedule_epithet_nomination

        schedule_epithet_nomination(character)
    except Exception as error:
        log_warn(
            "title_nomination_trigger_failed",
            context={"char": str(getattr(character, "pk", "?")), "trigger": "logout"},
            exc=error,
        )


class PlayerCharacter(LivingEntity):
    """A player-controlled living entity with deferred progression seams."""

    age: int | None = AttributeProperty(default=None)
    apparent_age: int | None = AttributeProperty(default=None)
    creation_pending: bool = AttributeProperty(default=False)
    guild_rank: str | None = AttributeProperty(default=None)
    quest_log: list = AttributeProperty(default=list)
    wallet: int = AttributeProperty(default=0)
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

    def at_post_move(self, source_location, **kwargs) -> None:
        """Schedule fresh action options after every committed player move.

        Every successful, hooks-enabled relocation — ordinary exit traversal
        and a direct ``move_to()`` alike — lands here; the trigger registers
        through ``transaction.on_commit`` so an aborted movement publishes
        nothing, and rollback compensations (``move_hooks=False``) never reach
        this hook. NPC and monster moves never run this override.
        """
        super().at_post_move(source_location, **kwargs)
        _schedule_action_options_after_move(self)

    def at_post_unpuppet(self, account=None, session=None, **kwargs) -> None:
        """Fire the logout epithet-nomination rest point (change G)."""
        super().at_post_unpuppet(account=account, session=session, **kwargs)
        _schedule_nomination_on_logout(self)


class Character(PlayerCharacter):
    """Evennia's conventional default-character path."""
