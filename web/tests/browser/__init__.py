"""Isolated browser acceptance harness for the Elosern WebClient.

This package owns the browser-test-only Evennia settings, the deterministic
account/character seed, the managed Evennia subprocess harness, and the
Playwright acceptance tests. Everything here runs against temporary SQLite
databases, log/media/static roots, and dynamic loopback ports; it never reads
or writes the developer database and never assumes port 4001.
"""
