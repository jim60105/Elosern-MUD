"""Derived church venue set (design 2026-09-22 §5.1; ``shop_key`` pattern).

Church venues are a view over the place registry: a place joins the church
venue set iff its authored kwargs carry the ``church`` kwarg, and the derived
set IS the venue authority — the accrual change's venue check and the
enrollment change's host resolution read this set, never a second authored
list. The kwarg's value is the church identity (design: one Light Church);
every flagged place must agree on it, and a conflicting value or a duplicate
flag fails closed at derivation instead of silently winning.
"""

from world.lore.settlements.places import PLACE_REGISTRY

#: The canonical church identity every ``church``-flagged place authors.
CHURCH_VENUE_KEY = "light_church"


def _derive_church_place_keys() -> tuple[str, ...]:
    """Project the church venue set from place-authored kwargs, fail-closed."""
    keys: list[str] = []
    for place in PLACE_REGISTRY.values():
        flag: str | None = None
        for key, value in place.authored_kwargs:
            if key != "church":
                continue
            if flag is not None:
                raise ValueError(
                    f"place {place.key!r} authors the church kwarg more than "
                    "once; a duplicate flag is conflicting authoring"
                )
            flag = value
        if flag is None:
            continue
        if flag != CHURCH_VENUE_KEY:
            raise ValueError(
                f"place {place.key!r} authors church kwarg {flag!r}, "
                f"expected the canonical {CHURCH_VENUE_KEY!r}"
            )
        keys.append(place.key)
    return tuple(keys)


#: The derived church venue set: place keys in PLACE_REGISTRY order.
CHURCH_PLACES: tuple[str, ...] = _derive_church_place_keys()


def resolve_church_place_keys() -> tuple[str, ...]:
    """Return the derived church venue set (re-derivation for tests)."""
    return _derive_church_place_keys()


__all__ = ["CHURCH_PLACES", "CHURCH_VENUE_KEY", "resolve_church_place_keys"]