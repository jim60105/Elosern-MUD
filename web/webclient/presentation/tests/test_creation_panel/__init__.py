"""Exact ``creation`` schema, presenter, and isolation tests.

Covers the D2 shared bounds, the version-3 payload validation (player-owned
draft persona plus the optional transient proposal slot with its five
transient-fill keys), deterministic
preset/profile ordering, the draft shape for both stages, the worst-case
envelope size, the all-ceilings byte gate, and the isolation of a corrupt
draft and non-creation modes.

Package split of the original flat module; each slice module groups
the shipped classes by panel concern. Shared module-level helpers
live in ``_support`` (not a collected test module).
"""
