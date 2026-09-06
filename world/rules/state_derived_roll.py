"""State-derived deterministic dice for the defeat violation sequence (DA4 D-V4).

``CombatSessionRecord`` persists no RNG seed or cursor and ``roll_d100`` is a
stateless Evennia dice wrapper, so a seeded per-session stream cannot exist.
Every d100 the defeat aftermath needs is instead a pure function of durable
record state: the session id, the violator identity, the victim identity, the
per-violator attempt index, and a purpose tag that lets one key space serve
both resist contests and future target-selection rolls.

A settlement that rolls back (the existing recovery fallback re-runs it once)
re-derives byte-identical rolls for free, because every input is durable
state — there is no replay bookkeeping to persist. The derivation is a keyed
BLAKE2b digest folded into ``1..100``; it is deliberately not cryptographic
randomness, only uniformity across the key space (design D-V4 risk note).
"""

import hashlib

_DIGEST_SIZE = 8
_DIE_SIDES = 100
_FIELD_SEPARATOR = "|"


def derived_roll(
    session_id: str,
    violator_key: str,
    victim_key: str,
    attempt_index: int,
    purpose: str,
) -> int:
    """Return one deterministic d100 (``1..100``) derived from durable state.

    All five arguments participate in the digest, so changing any one of them
    (session, violator, victim, attempt, or purpose) changes the roll. The
    function is pure: no module state, no RNG object, no clock read.
    String arguments may not contain the ``|`` field separator: an escaped or
    length-prefixed encoding would obscure the constraint, and the separator
    cannot appear in any durable identifier this helper's callers key on.
    """
    if not isinstance(session_id, str) or not session_id:
        raise ValueError("session_id must be a non-empty string")
    if not isinstance(violator_key, str) or not violator_key:
        raise ValueError("violator_key must be a non-empty string")
    if not isinstance(victim_key, str) or not victim_key:
        raise ValueError("victim_key must be a non-empty string")
    if isinstance(attempt_index, bool) or not isinstance(attempt_index, int):
        raise ValueError("attempt_index must be an integer")
    if attempt_index < 0:
        raise ValueError("attempt_index must be non-negative")
    if not isinstance(purpose, str) or not purpose:
        raise ValueError("purpose must be a non-empty string")
    for name, value in (
        ("session_id", session_id),
        ("violator_key", violator_key),
        ("victim_key", victim_key),
        ("purpose", purpose),
    ):
        if _FIELD_SEPARATOR in value:
            raise ValueError(
                f"{name} may not contain the {_FIELD_SEPARATOR!r} separator"
            )

    payload = _FIELD_SEPARATOR.join(
        (
            session_id,
            violator_key,
            victim_key,
            str(attempt_index),
            purpose,
        )
    ).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=_DIGEST_SIZE).digest()
    return int.from_bytes(digest, "big") % _DIE_SIDES + 1


__all__ = ["derived_roll"]
