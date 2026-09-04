# Delta: action-options-trigger-hooks

## MODIFIED Requirements

### Requirement: Room entry triggers a proposal on deterministic movement success

The room-entry trigger SHALL fire only from the deterministic movement-success boundary shared by every project exit lineage — the end of `after_successful_movement` in `typeclasses/exits.py` — and only for a puppeted `PlayerCharacter`. The trigger SHALL register its scheduling through `transaction.on_commit`, so the fire-and-forget call to the proposal service (with the watchers resolved from `watchers_for(actor)`) runs only after the movement transaction commits; it SHALL NOT fire on failed or compensated movements, on non-player traversers, on an unpuppeted player, on a rolled-back outer transaction, or from any hook inside `world/ai/`.

#### Scenario: A successful plain-exit traversal schedules a generation

- **WHEN** a puppeted `PlayerCharacter` successfully traverses a plain `MovementCostMixin` exit (settlement commits)
- **THEN** the proposal service receives exactly one fire-and-forget call with the puppeted actor and the watcher registry's live sessions for that actor, and the traversal's own settlement result is unchanged

#### Scenario: A failed movement schedules nothing

- **WHEN** the movement settlement raises (for example the clock charge fails) and compensation restores the player to the source location
- **THEN** no proposal generation is scheduled from the room-entry trigger

#### Scenario: NPC traversal schedules nothing

- **WHEN** an `NPC` traverses the same exit lineage
- **THEN** the room-entry trigger remains silent because the traverser is not a puppeted `PlayerCharacter`
