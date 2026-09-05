"""Deterministic account roster read model (webclient-character-roster).

Builds the frozen account-level roster read model disclosing an account's owned
characters, their identity, display name, live-puppet status, and pending creation
flag, plus account capacity and combat switch-lock facts.

Strictly read-only: never writes canonical state, never constructs lazy handlers,
and never reads disguised stats or persona.
"""

from dataclasses import dataclass
from typing import Any

from django.conf import settings

from world.rules.combat_session import is_in_active_session

# Presenter-owned row ceiling, independent of the configured capacity knob.
MAX_ROSTER_ROWS = 10

# Shared display-name code-point bound.
MAX_DISPLAY_NAME_CODE_POINTS = 128

# Stable lock reason in Traditional Chinese emitted when switching is blocked.
ROSTER_LOCK_REASON = "戰鬥中無法切換角色"


@dataclass(frozen=True)
class RosterCharacterView:
    """One character row in the account roster view.

    Attributes:
        identity: Stable integer database ID of the character.
        name: The character's current object key (bounded).
        current: True if this character is the session's live puppet.
        pending: True if character creation is still pending.
    """

    identity: int
    name: str
    current: bool
    pending: bool


@dataclass(frozen=True)
class AccountRosterView:
    """The complete frozen read model for an account's character roster.

    Attributes:
        characters: Deterministically ordered (ascending identity) character rows.
        max_characters: Configured maximum character slots for the account.
        can_create: True if the account owns fewer characters than max_characters.
        switch_locked: True if character switching is currently blocked (e.g. combat).
        lock_reason: Stable Traditional Chinese reason when switch_locked is True, else None.
    """

    characters: tuple[RosterCharacterView, ...]
    max_characters: int
    can_create: bool
    switch_locked: bool
    lock_reason: str | None


class AccountRosterError(RuntimeError):
    """Raised when an account roster cannot be read without mutation."""


def build_account_roster(actor: Any) -> AccountRosterView:
    """Build the deterministic account roster read model for ``actor``.

    Args:
        actor: The puppeted character entity currently rendering presentation.

    Returns:
        A frozen :class:`AccountRosterView` containing bounded character rows and
        account-level capacity/lock facts.

    Raises:
        AccountRosterError: If the actor is absent, has no owning account, the
            characters collection cannot be read, or the actor is not uniquely
            represented in the roster.
    """
    if actor is None:
        raise AccountRosterError("actor is None")

    account = getattr(actor, "account", None)
    if account is None:
        raise AccountRosterError("actor has no resolvable owning account")

    # Materialize once inside a strict try block to avoid inconsistent reads.
    try:
        characters_handler = getattr(account, "characters", None)
        if characters_handler is None:
            raise AccountRosterError("account has no characters attribute")
        raw_characters = list(characters_handler)
    except AccountRosterError:
        raise
    except Exception as exc:
        raise AccountRosterError(
            f"failed to read characters from account: {exc}"
        ) from exc

    try:
        sorted_characters = sorted(raw_characters, key=lambda c: int(c.pk))
    except Exception as exc:
        raise AccountRosterError(
            f"failed to sort characters by identity: {exc}"
        ) from exc

    # Verify that the rendered actor is legitimately owned by this account
    # before applying any row truncation.
    actor_pk = getattr(actor, "pk", None)
    actor_matches = [
        c
        for c in sorted_characters
        if (c == actor) or (actor_pk is not None and getattr(c, "pk", None) == actor_pk)
    ]
    if len(actor_matches) != 1:
        raise AccountRosterError(
            f"roster must have exactly one current character, found {len(actor_matches)}"
        )
    owned_actor = actor_matches[0]

    # Enforce presenter-owned row bound.
    if len(sorted_characters) <= MAX_ROSTER_ROWS:
        bounded_characters = sorted_characters
    else:
        initial_slice = sorted_characters[:MAX_ROSTER_ROWS]
        if owned_actor in initial_slice:
            bounded_characters = initial_slice
        else:
            # Guarantee the owned live puppet is preserved within the bounded set
            # by taking the first MAX_ROSTER_ROWS - 1 entries plus owned_actor,
            # re-sorting by numeric identity.
            bounded_characters = sorted(
                sorted_characters[: MAX_ROSTER_ROWS - 1] + [owned_actor],
                key=lambda c: int(c.pk),
            )

    rows: list[RosterCharacterView] = []
    for char in bounded_characters:
        is_current = (char == owned_actor)
        name = str(getattr(char, "key", "?"))[:MAX_DISPLAY_NAME_CODE_POINTS]
        pending = bool(getattr(char, "creation_pending", False))
        rows.append(
            RosterCharacterView(
                identity=int(char.pk),
                name=name,
                current=is_current,
                pending=pending,
            )
        )

    # Capacity facts: read MAX_NR_CHARACTERS dynamically at call time.
    max_characters = int(getattr(settings, "MAX_NR_CHARACTERS", 5))
    can_create = len(raw_characters) < max_characters

    # Lock facts: switching is locked exactly when the live puppet is in combat.
    switch_locked = is_in_active_session(actor)
    lock_reason = ROSTER_LOCK_REASON if switch_locked else None

    return AccountRosterView(
        characters=tuple(rows),
        max_characters=max_characters,
        can_create=can_create,
        switch_locked=switch_locked,
        lock_reason=lock_reason,
    )


__all__ = [
    "AccountRosterError",
    "AccountRosterView",
    "MAX_DISPLAY_NAME_CODE_POINTS",
    "MAX_ROSTER_ROWS",
    "ROSTER_LOCK_REASON",
    "RosterCharacterView",
    "build_account_roster",
]
