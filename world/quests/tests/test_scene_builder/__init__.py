"""Tests for the deterministic SceneBuilder materialization layer (scene-builder).

Covers the occupant prototype whitelist, the requirements->prototype->spawn
rules (anti-hallucination by construction), atomic and idempotent instance
materialization, permanent-layer located-only behavior, DEFEAT/ESCORT binding
sets, rollback and re-entry, and the lore-backed stat derivation. Package
split of the original flat module: the shipped suites live in the materialization,
characterization and portrait-pipeline slices; the shared bases
(``SceneBuilderTestBase``, ``SceneBuilderIsolation``), the module-level payload
helpers and the synthetic scope live in ``_support`` (not a collected test
module), imported by the offline, flavor and boundary sibling modules.
"""
