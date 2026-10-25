"""Pure reader and sole writer for entity social identities.

Stores sorted unique canonical keys in ``entity.db.social_identities``.
Corrupted or missing state fails closed (returns an empty frozenset).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from world.lore.social_identities import (
    MAX_SOCIAL_IDENTITIES,
    SOCIAL_IDENTITY_REGISTRY,
)

SOCIAL_IDENTITIES_ATTRIBUTE = "social_identities"


class SocialIdentityError(ValueError):
    """Raised when an invalid social identity key or container is passed."""


def read_social_identities(entity: Any) -> frozenset[str]:
    """Return the set of assigned social identities for an entity.

    Pure reader that never creates or mutates storage. Missing, unreadable, or
    corrupted stored state fails closed to an empty frozenset (unknown is
    never commoner by default, and corrupted state never implies membership).
    """
    if entity is None:
        return frozenset()

    # Evennia entities have an attributes handler; autocreate is avoided by
    # checking ``has`` first or reading safely.
    attributes = getattr(entity, "attributes", None)
    if attributes is None or not hasattr(attributes, "has"):
        # Fallback to .db if attributes handler is missing
        db = getattr(entity, "db", None)
        if db is None:
            return frozenset()
        raw = getattr(db, SOCIAL_IDENTITIES_ATTRIBUTE, None)
    else:
        if not attributes.has(SOCIAL_IDENTITIES_ATTRIBUTE):
            return frozenset()
        raw = attributes.get(SOCIAL_IDENTITIES_ATTRIBUTE)

    # Fail closed on non-collection, strings, bytes, mappings
    if isinstance(raw, (str, bytes, dict)) or not isinstance(raw, (list, tuple, set, frozenset)):
        return frozenset()

    valid_keys = set()
    for item in raw:
        if not isinstance(item, str) or isinstance(item, bool):
            # Corrupted element: whole corrupted state fails closed
            return frozenset()
        if item not in SOCIAL_IDENTITY_REGISTRY:
            # Unknown key: fails closed
            return frozenset()
        valid_keys.add(item)

    return frozenset(valid_keys)


def set_social_identities(entity: Any, keys: Iterable[str]) -> frozenset[str]:
    """Validate, sort, deduplicate, and store social identity keys on an entity.

    Sole writer for social identities.
    Accepts any iterable of strings (tuples, lists, sets, frozensets). Rejects
    strings/bytes directly, non-iterables, bools, unknown keys, or exceeding
    MAX_SOCIAL_IDENTITIES. Stores sorted unique keys as a tuple on
    ``entity.db.social_identities`` and returns the resulting frozenset.

    The committed identity write refreshes the changed actor's dialogue
    availability (authored-dialogue-refresh-physical) because authored topics
    qualify on these structured keys only. Construction on a body with no
    lawful dialogue owner is a no-op: the owner helper returns nothing and no
    callback is registered. Persona prose is deliberately not a source.
    """
    if entity is None:
        raise SocialIdentityError("Cannot set social identities on None")

    if isinstance(keys, (str, bytes, dict)) or not isinstance(keys, Iterable):
        raise SocialIdentityError(f"Social identities must be an iterable of strings, got {type(keys).__name__}")

    unique_keys = set()
    for k in keys:
        if not isinstance(k, str) or isinstance(k, bool):
            raise SocialIdentityError(f"Social identity keys must be strings, got {k!r}")
        if k not in SOCIAL_IDENTITY_REGISTRY:
            raise SocialIdentityError(f"Unknown social identity key: {k!r}")
        unique_keys.add(k)

    if len(unique_keys) > MAX_SOCIAL_IDENTITIES:
        raise SocialIdentityError(
            f"Social identities count {len(unique_keys)} exceeds maximum {MAX_SOCIAL_IDENTITIES}"
        )

    sorted_keys = tuple(sorted(unique_keys))

    # Write to entity.db.social_identities or entity.attributes.add
    attributes = getattr(entity, "attributes", None)
    if attributes is not None and hasattr(attributes, "add"):
        attributes.add(SOCIAL_IDENTITIES_ATTRIBUTE, sorted_keys)
    elif hasattr(entity, "db"):
        setattr(entity.db, SOCIAL_IDENTITIES_ATTRIBUTE, sorted_keys)
    else:
        raise SocialIdentityError("Entity does not support attribute storage")

    from world.rules.dialogue_availability import (
        affected_dialogue_owners,
        queue_dialogue_refresh,
    )

    queue_dialogue_refresh(
        affected_dialogue_owners(entity), cause="social_identity"
    )
    return frozenset(sorted_keys)
