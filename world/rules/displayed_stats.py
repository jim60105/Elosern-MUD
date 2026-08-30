"""Displayed-stats block for the shared target-appearance path (displayed-stats-view).

D2's appearance-rendering consumer: the player reads any present living
target's displayed combat values directly from ``look <target>``. The block
renders exactly the displayed combat five, every value through the sanctioned
disguise accessor, and is presentation-only: it never writes attributes,
mutates traits, advances the clock, or records map knowledge.

Version 5 (expose-stat-breakdown-read-model D5): a SELF-look (``looker`` is
the observed entity) renders the full breakdown rows instead — the same
single read-model assembly the character panel serializes, spelled out with
named source segments. Every third-party observation renders the five-row
block byte-identically to before.
"""

from typing import Any

from world.rules.status_query import TRAIT_LABELS
from world.rules.traits import get_display_value

# The displayed combat five in fixed presentation order (displayed-stats-view
# A2); ``hp`` renders the gauge's current value, never the maximum.
DISPLAYED_KEYS = ("atk_phys", "agility", "defense", "magic_power", "hp")


def _self_breakdown_block(entity: Any) -> str | None:
    """Render the self-view breakdown, or ``None`` when it is unavailable.

    Shares the character panel's single assembly (``build_character_read_model``
    → ``status_text.breakdown_text``); a fail-closed breakdown
    (or any read-model failure) degrades to the five-row block instead of
    raising, so appearance rendering never becomes fatal.
    """
    from world.rules.status_query import build_character_read_model
    from world.rules.status_text import breakdown_text

    try:
        model = build_character_read_model(entity)
    except Exception:
        return None
    return breakdown_text(model)


def display_stat_block(entity: Any, looker: Any = None) -> str | None:
    """Render the displayed combat values for ``look <target>``.

    Reads every key through ``get_display_value()``; returns ``None`` for
    non-living targets so ``look`` appends nothing. A missing or malformed
    trait row is omitted, never fatal, and an entity without a single valid
    row yields ``None`` too. Read-only: never writes attributes, mutates
    traits, advances the clock, or records map knowledge.

    When ``looker`` is the observed entity itself the block instead shows
    the full true-value breakdown from the same builder feeding the
    character panel (displayed-stats-view, amended by
    expose-stat-breakdown-read-model); every other observation keeps the
    five-row third-party block byte-identical.
    """
    if not hasattr(entity, "traits"):
        return None
    if looker is not None and looker is entity:
        breakdown = _self_breakdown_block(entity)
        if breakdown is not None:
            return breakdown
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
