"""Derived church venue set (design 2026-09-22 §5.1; ``shop_key`` pattern).

Church venues are a view over the place registry: a place joins the church
venue set iff its authored ``church`` venue flag is set, and the derived
set IS the venue authority — the accrual change's venue check and the
enrollment change's host resolution read this set, never a second authored
list. The flag is a boolean (a place either is a church venue or is not), so
the old duplicate/conflicting-kwarg authoring is not representable; the
church identity itself (design: one Light Church) is authored once, on the
clergy host's ``church_host`` capability, and validated where that capability
is derived.
"""

from world.lore.settlements.places import PLACE_REGISTRY

#: The canonical church identity a ``church_host`` capability authors.
CHURCH_VENUE_KEY = "light_church"


def _derive_church_place_keys() -> tuple[str, ...]:
    """Project the church venue set from the authored place flag."""
    return tuple(
        place.key for place in PLACE_REGISTRY.values() if place.church
    )


#: The derived church venue set: place keys in PLACE_REGISTRY order.
CHURCH_PLACES: tuple[str, ...] = _derive_church_place_keys()


def resolve_church_place_keys() -> tuple[str, ...]:
    """Return the derived church venue set (re-derivation for tests)."""
    return _derive_church_place_keys()


__all__ = ["CHURCH_PLACES", "CHURCH_VENUE_KEY", "resolve_church_place_keys"]