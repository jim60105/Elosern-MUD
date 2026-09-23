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
same rule, and any surface outside the resulting set still raises.

#### Scenario: Registering the disengage handler succeeds
- **WHEN** `register_effect_handler("disengage", handler, surfaces=frozenset({"battlefield"}))` is
  called
- **THEN** it completes without raising `UnsnapshottedSurfaceError`

#### Scenario: An unrelated, still-unsupported surface is still rejected
- **WHEN** `register_effect_handler()` is called with a surface value outside `{"traits", "sexual",
  "buffs", "skill_grants", "battlefield", "church"}` (e.g. `"room_flags"`)
- **THEN** it still raises `UnsnapshottedSurfaceError`, proving the additions widen the supported
  set entry by entry rather than disabling the gate

#### Scenario: Registering a church-surface handler succeeds
- **WHEN** `register_effect_handler("rite_blessing", handler, surfaces=frozenset({"church",
  "buffs"}))` is called
- **THEN** it completes without raising `UnsnapshottedSurfaceError`
