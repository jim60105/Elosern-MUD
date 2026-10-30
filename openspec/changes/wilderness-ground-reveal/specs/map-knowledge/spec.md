## MODIFIED Requirements

### Requirement: Arrival recording happens only at existing successful-arrival seams
record_arrival SHALL remain at existing successful movement-completion seams; wilderness ground observation SHALL also update at the end of a positive committed explicit skip, never from reads, replayed/refused operations or teleport-style relocation.

#### Scenario: Grid traversal records the destination after success
- **WHEN** a `PlayerCharacter` successfully traverses a `CostedXYZExit` or an ordinary `Exit`
  (including the Limbo bridge and an instance doorway pair)
- **THEN** the knowledge record contains the destination's canonical `grid:` or `room:` node ID with a
  `last_seen_tick` equal to the current world tick

#### Scenario: Wilderness stepping records the destination coordinate after success
- **WHEN** a `PlayerCharacter` successfully enters the wilderness through `WildernessGateExit` or
  takes a successful wilderness step through `WildernessReturnExit`
- **THEN** the knowledge record contains the destination's `wild:` node ID with the current world tick

#### Scenario: A blocked or failed traversal records nothing
- **WHEN** an exit traversal fails its locks, a pre-move veto aborts it, or a movement transaction
  rolls back
- **THEN** the knowledge record is unchanged and no new or updated observation appears

#### Scenario: A quiet reclamation relocation records nothing
- **WHEN** an unowned occupant is relocated to `settings.DEFAULT_HOME` during instance reclamation
- **THEN** no map knowledge is recorded for that relocation

#### Scenario: Teleport-style moves record nothing
- **WHEN** a character is relocated via a teleport-style `move_to` call
- **THEN** no discovery is recorded

#### Scenario: Read-only operations record nothing
- **WHEN** search, map rendering, or remote inspection touches map data
- **THEN** no discovery is recorded

#### Scenario: The node is derived from the current location at recording time
- **WHEN** `record_arrival` runs for a character anywhere in the world
- **THEN** the derived node is computed from the character's current location, so grid, wilderness,
  instance, and interior each yield their canonical identity without per-seam node computation


#### Scenario: Final skip observation
- **WHEN** a positive explicit skip ends at a wilderness cell
- **THEN** that final tick/radius is recorded transactionally without another arrival call


