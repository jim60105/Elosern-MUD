"""Integration tests for roster-driven service content sync (tasks 3.x, 4.2).

Package split of the original flat module; each slice module groups the
shipped classes by concern (content sync, host identity and service
anchors, roster authority and binding convergence, quest-issuer
anchoring, and the ciaran-village commerce pair). Registry resolvers,
roster-row accessors, and the isolation base live in ``_support``
(not a collected test module).
"""
