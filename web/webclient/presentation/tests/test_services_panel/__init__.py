"""Exact ``services`` schema, presenter, and surface-isolation tests.

Covers the D4 shared bounds, the version-2 payload validation, deterministic
row ordering, pagination totals, host identity/display-name limits,
action-descriptor shapes, the worst-case envelope size, and the isolation of a
corrupt quest log, malformed merchant stock, and non-exploration modes.

Package split of the original flat module; each slice module groups
the shipped classes by panel concern. Shared module-level helpers
live in ``_support`` (not a collected test module).
"""
