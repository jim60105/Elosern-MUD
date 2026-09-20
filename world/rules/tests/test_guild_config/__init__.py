"""Data-contract test: guild/shop config validation contract
Tests for immutable economy identities and the guild-economy catalog loader (tasks 2.1-2.5).

Package split of the original flat module; each slice module groups the
shipped classes by concern (item/offer identities, the merit/exam
rulebook sections, the assortment/shop join, price scaling, catalog
loading, and the derived service-host roster). Shared rulebook readers,
the registry-isolation base, and the synthetic price-shop harness live
in ``_support`` (not a collected test module).
"""
