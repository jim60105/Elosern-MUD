"""Skill-progression tests (skill-progression): the practice-cost ladder and
lineage unlocks exercised on a fully synthetic skill tree.

Package split of the original flat module; each slice module groups the
shipped classes by concern (the core progression ladder split across cost/
tier and preset/policy slices, element-affinity and practice-pipeline
integration, and the derived/cross-lineage unlock wiring). Shared synthetic
tree fixtures and helpers live in ``_support`` (not a collected test
module).
"""
