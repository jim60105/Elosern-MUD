"""Sole-writer art service and deterministic seam tests.

Package split of the original flat module; each slice module groups the
shipped classes by concern (the startup/ensure service, the autogen
retrofit, the gallery request seam and prompt composition, the monster
gallery generation and startup sync, and the orphan prune). The
synthetic-scope helper, the kit vocabularies and the subject/binding
factories live in ``_support`` (not a collected test module).
"""
