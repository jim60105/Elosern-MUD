"""
Deterministic tests for item-use preflight, settlement, and the clock facade.

Covers side-effect-free eligibility, atomic effect/consumption settlement
including contained-mirror handling and cache restoration, the stable
``item_used`` event identity, and the composed out-of-combat clock boundary.

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level fixtures, helpers,
and bases live in ``_support`` (not a collected test module).
"""
