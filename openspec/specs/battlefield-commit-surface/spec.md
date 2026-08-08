## Purpose

Define atomic ActionResolver support for battlefield-level mutations.

## Requirements

### Requirement: SNAPSHOTTED_SURFACES gains a battlefield surface, covering Battlefield.fled
`world/rules/action.py`'s `SNAPSHOTTED_SURFACES` SHALL include `"battlefield"` alongside its existing
`"traits"`, `"sexual"`, `"buffs"`, and `"skill_grants"` entries. A `PendingEffect` declaring
`surfaces=frozenset({"battlefield"})` SHALL be accepted by `register_effect_handler()` without raising
`UnsnapshottedSurfaceError`.

#### Scenario: Registering the disengage handler succeeds
- **WHEN** `register_effect_handler("disengage", handler, surfaces=frozenset({"battlefield"}))` is
  called
- **THEN** it completes without raising `UnsnapshottedSurfaceError`

#### Scenario: An unrelated, still-unsupported surface is still rejected
- **WHEN** `register_effect_handler()` is called with a surface value outside `{"traits", "sexual",
  "buffs", "skill_grants", "battlefield"}` (e.g. `"inventory"`)
- **THEN** it still raises `UnsnapshottedSurfaceError`, proving this change's addition widens the
  supported set by exactly one entry rather than disabling the gate

### Requirement: A Battlefield-shaped object is snapshotted and restored by shape, not by explicit
declaration from the caller
`world/rules/action.py`'s commit-time snapshot/restore dispatch SHALL detect a `Battlefield`-shaped
object (duck-typed: an object exposing both a `fled` and a `roster` attribute) and snapshot/restore
exactly its `fled` and `knocked_out` sets, falling back to the existing per-entity snapshot/restore
path for any object that is not battlefield-shaped. `world/rules/action.py` SHALL NOT import
`world.rules.combat.Battlefield` to make this determination.

#### Scenario: A Battlefield object is snapshotted by its fled and knocked_out sets
- **WHEN** a `PendingEffect` whose `entity` field is a `Battlefield`-shaped object is staged for commit
- **THEN** the commit mechanism's snapshot of that object captures the exact contents of its `fled`
  and `knocked_out` sets before any effect in the same commit applies

#### Scenario: A LivingEntity is still snapshotted by the pre-existing per-entity path
- **WHEN** a `PendingEffect` whose `entity` field is an ordinary `LivingEntity` is staged for commit,
  alongside a `PendingEffect` whose `entity` field is a `Battlefield`-shaped object, in the same commit
- **THEN** the `LivingEntity`'s `traits`/`sexual`/`buffs`/`skill_grants` are snapshotted via the
  existing, unmodified per-entity mechanism, and the `Battlefield`'s `fled` and `knocked_out` sets are
  snapshotted via the new battlefield-shaped path — both within the same `_commit()` call

#### Scenario: No isinstance check against Battlefield exists in action.py
- **WHEN** `world/rules/action.py`'s source is inspected
- **THEN** it contains no `isinstance(..., Battlefield)` check and no import of
  `world.rules.combat.Battlefield`; the battlefield-shaped dispatch is duck-typed only

### Requirement: A commit failure rolls back a battlefield mutation exactly as it rolls back an entity
mutation
When one `PendingEffect`'s `apply()` raises mid-commit, any `Battlefield.fled` or
`Battlefield.knocked_out` mutation already applied by an earlier `PendingEffect` in the same commit
SHALL be reversed, restoring both sets to their exact pre-commit contents, using the same
all-or-nothing guarantee action-resolver's existing entity-state rollback already provides.

#### Scenario: A battlefield mutation is rolled back when a later effect in the same commit fails
- **WHEN** a commit stages a successful knockout effect (adding a key to `battlefield.knocked_out`)
  followed by a second, synthetic `PendingEffect` whose `apply()` raises
- **THEN** `resolve()` returns `ActionResult(outcome="rejected", reason=RejectReason.COMMIT_FAILED)`,
  and the knocked-out key is absent from `battlefield.knocked_out` after the call — the earlier
  effect's own already-applied mutation was reversed

#### Scenario: The existing entity-rollback tests still pass unmodified
- **WHEN** action-resolver's own pre-existing atomicity test suite (fault injection at each of the eight
  steps, the three-effects-second-raises commit test) is run against `world/rules/action.py` after this
  change's additions land
- **THEN** every pre-existing test in that suite still passes with no modification to its own assertions

### Requirement: The no-combat-branching tripwire remains unaffected by the battlefield-surface addition
Action-resolver's existing source-scan and signature-scan tripwire tests, and its positive
polymorphism proof (identical `ActionRequest`s, different `ActionContext`, different outcome), SHALL
continue to pass unmodified after this change's additions to `world/rules/action.py`.

#### Scenario: The forbidden-token scan finds nothing new
- **WHEN** `world/rules/action.py` is scanned for the tokens `in_combat`, `is_combat`, `combat_state`,
  and `isinstance(context, Battlefield` after this change's edits land
- **THEN** none of these tokens appear anywhere in the file

#### Scenario: The positive polymorphism proof still holds
- **WHEN** action-resolver's own test calling `ActionResolver.resolve()` twice with identical requests
  differing only in which `ActionContext` is supplied is run after this change's edits land
- **THEN** it still passes with no modification to its own assertions — this change's additions live
  entirely inside `_commit()`'s internal snapshot/restore dispatch, never inside `resolve()`'s eight
  steps or `targeting.py`'s validations
