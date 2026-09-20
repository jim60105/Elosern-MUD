"""Unit and integration behavior tests for the effect-audience authoring,
the pure planner, and the full routing pipeline.

Package split of the original flat module; each slice module groups the
shipped classes by concern (authoring/pure planner, and the integration
pipeline split across two same-named sibling classes with byte-identical
setUp, preserving the shipped (class, method) set). MockContext and the
other shared pieces live in ``_support`` (not a collected test module).
"""
