"""Displayed-stats block for the shared target-appearance path (displayed-stats-view).

D2's appearance-rendering consumer: the player reads any present living
target's displayed combat values directly from ``look <target>``. The block
renders exactly the displayed combat five, every value through the sanctioned
disguise accessor, and is presentation-only: it never writes attributes,
mutates traits, advances the clock, or records map knowledge.
"""

from typing import Any

from world.rules.status_query import TRAIT_LABELS
from world.rules.traits import get_display_value

# The displayed combat five in fixed presentation order (displayed-stats-view
# A2); ``hp`` renders the gauge's current value, never the maximum.
DISPLAYED_KEYS = ("atk_phys", "agility", "defense", "magic_level", "hp")


def display_stat_block(entity: Any) -> str | None:
    """Render the five displayed combat values for ``look <target>``.

    Reads every key through ``get_display_value()``; returns ``None`` for
    non-living targets so ``look`` appends nothing. A missing or malformed
    trait row is omitted, never fatal, and an entity without a single valid
    row yields ``None`` too. Read-only: never writes attributes, mutates
    traits, advances the clock, or records map knowledge.
    """
    if not hasattr(entity, "traits"):
        return None
    rows: list[str] = []
    for key in DISPLAYED_KEYS:
        trait = getattr(entity.traits, key, None)
        if trait is None:
            continue
        try:
            value = int(get_display_value(entity, key))
        except (TypeError, ValueError, OverflowError, AttributeError):
            continue
        rows.append(f"{TRAIT_LABELS.get(key, key)}：{value}")
    if not rows:
        return None
    return "\n".join(rows)


__all__ = ["DISPLAYED_KEYS", "display_stat_block"]
