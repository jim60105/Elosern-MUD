"""Per-skill narration for the enhancement family: the body answering itself.

The register is the body answering its own training: breath drawn in, weight
settled, a movement already known by the muscles. ``ROWS`` follows the skill
registry's own in-order block; order is authoring order, not a behavioural
input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "concentration",
        action=(
            "{actor} 收束呼吸，把心神歸到一點。",
            "{actor} 讓身體記起訓練過千百次的節奏。",
        ),
    ),
)

__all__ = ["ROWS"]
