"""Read-only onboarding guidance data and coordination (onboarding-guide D1/D2).

This package contains the immutable arrival-scene beats, the guard keyword
dialogue table, and a pure beat coordinator. It imports nothing from
``world.rules``, ``typeclasses``, or Evennia: every state read or write is
performed by ``world.rules.onboarding``, which is the sole writer of onboarding
state. The single-writer invariant holds because the dependency direction is
``rules -> onboarding data`` only.
"""
