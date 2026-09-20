"""
Evennia-backed tests for deterministic player activation.

Runs entirely on the synthetic kit: race, subrace, static-tier, preset,
skill, item, price, starting-kit, element, and buff catalogs are replaced for
every preflight/activation path, so no shipped catalog identifier appears in
the mechanics under test. Two deliberate production-literal fixtures remain:
the affinity bound map (patched, not a kit target) and the ``elf`` race key,
which the elf subrace-seed rule matches by literal. Shipped-content claims
this suite used to carry (the human budget value, foxkin band facts, the
every-shipped-preset activation sweeps) now live in the registered
data-contract suites ``world/lore/tests/test_races.py`` and
``world/lore/tests/test_player_presets.py``.

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level fixtures, helpers,
and bases live in ``_support`` (not a collected test module).
"""
