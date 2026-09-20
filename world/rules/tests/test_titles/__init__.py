"""
Deterministic title state, predicates, planner, and guild-pairing tests.

Covers the title-system storage contract (D1/D4/D5/D8): the strict fail-closed
reader, the compose matrix, dedupe/idempotent banking with D8 auto-equip, the
swap-only equip surface with leak-free stable rejections, the seven predicate
families, the event-effect planner's commit-window grant (a notification only
survives when the outer settlement commits), and the guild pairing (starter
pair on registration, rank title on promotion) with rollback that can neither
lose nor double-grant. Also pins the structural invariant that no
delete/unequip mutator exists anywhere in the module or its command.

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level fixtures, helpers,
and bases live in ``_support`` (not a collected test module).
"""
