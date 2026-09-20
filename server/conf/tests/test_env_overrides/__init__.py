"""Subprocess black-box tests for the environment-variable settings overrides.

Package split of the original flat module; each slice module groups the
shipped classes by concern (defaults/coercion/fail-closed, the never-env
seam/precedence/derived-knob/sanitization surface, and the inventory + shard
ownership guards). The subprocess harness, path anchors, and the env-backed
inventory live in ``_support`` (not a collected test module).
"""
