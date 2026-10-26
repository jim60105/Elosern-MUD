# Spec Delta

## MODIFIED Requirements

### Requirement: sync_grid() is idempotent across repeated calls and server starts
Repeated grid synchronization SHALL reuse stable declared rooms/exits and converge to the loaded settlement topology without duplicate objects.

#### Scenario: Running sync_grid twice creates no duplicate rooms
- **WHEN** `sync_grid()` is called, and then called a second time with no map data changed
- **THEN** the total count of `GridRoom`/`AnchorRoom` instances after the second call equals the
  count after the first call, and the total count of `XYZExit` instances is likewise unchanged

#### Scenario: A room's Attributes are updated in place, not duplicated, when its prototype changes
- **WHEN** `content/maps/settlements/capital_altoria.yaml`'s prototype for one coordinate changes (for example, its
  `desc`) and `sync_grid()` is called again
- **THEN** the existing room at that coordinate is updated to the new `desc`, and no second room is
  created at the same coordinate

