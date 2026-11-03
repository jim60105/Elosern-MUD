"""Stable individual combat identity (dependency-free).

Persisted actors are identified by ``dbref:<positive int pk>``; nonpersistent
pure actors must carry an explicit non-empty ``combat_identity`` and are
identified by ``fixture:<identity>``. Display labels are never identities.
"""

from typing import Any

DBREF_PREFIX = "dbref:"
FIXTURE_PREFIX = "fixture:"


class CombatIdentityError(ValueError):
    """A combatant cannot supply a stable individual identity."""


def stable_actor_id(entity: Any) -> str:
    """Return one combatant's stable individual identity."""
    dbref = getattr(entity, "pk", None)
    if dbref is not None:
        if isinstance(dbref, bool) or not isinstance(dbref, int) or dbref <= 0:
            raise CombatIdentityError(
                f"persisted combatant has a malformed primary key {dbref!r}"
            )
        return f"{DBREF_PREFIX}{dbref}"
    identity = getattr(entity, "combat_identity", None)
    if (
        isinstance(identity, bool)
        or not isinstance(identity, str)
        or not identity
        or identity != identity.strip()
        or any(character.isspace() for character in identity)
        or any(ord(character) < 32 for character in identity)
    ):
        raise CombatIdentityError(
            "a nonpersistent combatant requires an explicit non-empty "
            f"combat_identity; got {identity!r}"
        )
    return f"{FIXTURE_PREFIX}{identity}"
