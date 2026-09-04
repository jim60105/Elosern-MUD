# Delta: map-knowledge

## MODIFIED Requirements

### Requirement: Arrival recording happens only at existing successful-arrival seams
`world/rules/map_knowledge.py`'s `record_arrival` SHALL be invoked only from the project's existing
successful-arrival seams: the shared movement-completion helper
`typeclasses.exits.after_successful_movement` — which the `MovementCostMixin.at_post_traverse`, the
success branch of `WildernessGateExit.at_traverse`, and both success branches of
`WildernessReturnExit.at_traverse` all call after `charge_movement`. Failed traversal, locked exits, vetoed
`at_pre_move`, rolled-back movement, teleport-style `move_to` calls, quiet reclamation relocations,
search, map rendering, and remote inspection SHALL NOT record discovery. The derived node SHALL be
computed from the character's current location at recording time, so grid, wilderness, instance, and
interior each yield their canonical identity without per-seam node computation.

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
