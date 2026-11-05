"""The on-demand ``area_map`` presenter and the ``map.view`` action.

publish-area-map-panel: whole-area fog of war on grid, instance, interior and
wilderness layers, gateway metadata, adjacent-only move descriptors, quest
markers, measured bounds, read-only behaviour, and on-demand publication
(movement and text refreshes never compute or push a map).

Settlement and wilderness cases run against the shipped synced maps through
the runtime probes in ``test_local_map._support`` (no catalog literal); room
graphs and the pure fog function use synthetic fixtures.
"""

# The journeys live in one module per layer so each can own its own
# machine shard; the shared probes and fixtures are in ``_support``.
