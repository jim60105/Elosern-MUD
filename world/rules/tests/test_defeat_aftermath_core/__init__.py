"""
Defeat-aftermath core tests (defeat-aftermath-core).

Covers the hostile-defeat settlement contract: the HP-1 nonlethal floor,
the violator departure (population despawn, quest-bound retain with
precedence, foreign untouched), the weak debuff mount and ordinary decay,
the recovery advance (exact-target wake, capped degenerate case, clock
side-effect window, rollback boundaries, retained-winner smoke), the
EventLog kinds with the observability boundary event, the guarded violation
hook, the per-section rulebook loader, and the zero-uncaused-write battery.

Annotation note: the ``covers_requirement`` annotations reference the
canonical main-spec requirement IDs synced into ``openspec/specs/`` (the
``defeat-aftermath-recovery`` capability plus the amended
``defeat-aftermath-core`` expectations).

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level fixtures, helpers,
and bases live in ``_support`` (not a collected test module).
"""
