# battlefield-commit-surface — delta for implement-holy-rite-cast-rail

## MODIFIED Requirements

### Requirement: SNAPSHOTTED_SURFACES gains a battlefield surface, covering Battlefield.fled
`world/rules/action.py`'s `SNAPSHOTTED_SURFACES` SHALL include `"battlefield"` alongside its existing
`"traits"`, `"sexual"`, `"buffs"`, and `"skill_grants"` entries. A `PendingEffect` declaring
`surfaces=frozenset({"battlefield"})` SHALL be accepted by `register_effect_handler()` without raising
`UnsnapshottedSurfaceError`. The set SHALL additionally include `"church"`, the character ledger
attribute the holy-rite effect handlers stage against: adding a surface extends the snapshot
inventory the commit point covers, and the commit mechanism itself is unchanged. A `PendingEffect`
declaring `surfaces=frozenset({"church"})` SHALL be accepted by `register_effect_handler()` under the
same rule, and the commit-time snapshot/restore dispatcher SHALL grow its own `"church"` branch in
the same shape as the `"wallet"` and `"inventory"` branches — an attribute-keyed surface with an
explicit branch in `_snapshot_touched`/`_restore_touched`
(`world/rules/action/transaction.py`), not an entity-aggregate key — so a staged ledger write is
restored byte-identically when a later pending effect fails mid-commit. Membership in the surface
set alone is not the guarantee; the branch is.

#### Scenario: Registering the disengage handler succeeds
- **WHEN** `register_effect_handler("disengage", handler, surfaces=frozenset({"battlefield"}))` is
  called
- **THEN** it completes without raising `UnsnapshottedSurfaceError`

#### Scenario: An unrelated, still-unsupported surface is still rejected
- **WHEN** `register_effect_handler()` is called with a surface value outside `{"traits", "sexual",
  "buffs", "skill_grants", "battlefield", …}` (the shipped set plus exactly this change's
  addition; e.g. `"church_ledger_v2"`)
- **THEN** it still raises `UnsnapshottedSurfaceError`, proving this change widens the supported set
  by exactly one entry rather than disabling the gate

#### Scenario: A church-surface write rolls back mid-commit like a wallet-surface write
- **WHEN** a skill stages a `church`-surface `PendingEffect` followed by a second pending effect
  whose `apply()` raises
- **THEN** `resolve()` rejects with `COMMIT_FAILED` and the actor's `db.church` ledger equals its
  exact pre-commit contents (merit, daily block, and any `blessing_last_tick` stamp included),
  restored by the dispatcher's `church` branch

#### Scenario: Registering a church-surface handler succeeds
- **WHEN** `register_effect_handler("rite_blessing", handler, surfaces=frozenset({"church",
  "buffs"}))` is called
- **THEN** it completes without raising `UnsnapshottedSurfaceError`
