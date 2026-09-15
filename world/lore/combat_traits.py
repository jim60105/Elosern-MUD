"""Closed combat-trait vocabulary (light-conditional-damage).

Single source for the combat-trait keys an import record or a DamagePolicy
predicate may declare. ``world/rules/traits.py`` re-exports this value and
owns the validation/accessor rules that read it; the vocabulary itself is
static world data, so it lives here beside the other closed vocabularies.
"""

COMBAT_TRAITS_VOCABULARY: frozenset[str] = frozenset({"undead"})

__all__ = ["COMBAT_TRAITS_VOCABULARY"]
