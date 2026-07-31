"""Percentile-die wrapper for the native linear combat rules."""

from evennia.contrib.rpg.dice import roll as _evennia_roll


def roll_d100() -> int:
    """Return one d100 result using Evennia's supported dice contrib."""
    return int(_evennia_roll(1, 100))
