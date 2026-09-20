"""Exact ``character`` schema, presenter, and parity tests.

Covers the D10 shared bounds, the version-3 payload validation (category-
grouped ``actives``/``passives``), true-vs-disguised values, the empty
displayed list when undisguised, read-only guarantees, and the
status-vs-character parity proving both panels share the same canonical trait
source.
Version 5 (expose-stat-breakdown-read-model) adds the breakdown trait rows
(``base``/``effective``/``layers``) and the equipment ``adjustment`` summary;
render-equipment-breakdown-webclient closed the transitional tolerance
window: version 5 is the only accepted schema version, and v4 payloads
reject.

Package split of the original flat module; each slice module groups
the shipped classes by panel concern. Shared module-level helpers
live in ``_support`` (not a collected test module).
"""
