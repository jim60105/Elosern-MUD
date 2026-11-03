# Spec Delta

## MODIFIED Requirements

### Requirement: engage_group opens one session against several co-located hostile targets
`world/rules/combat_session.py` SHALL provide `engage_group(actor, targets)`, applying every
validation, companion collection, record construction, battlefield reconstruction, persistence, skip
safety registration, and dialogue-session clearing that single-target engagement performs, with
`enemy_ids` holding one dbref per supplied target in deterministic order.

#### Scenario: A two-enemy session reconstructs, persists, resolves, and settles
- **WHEN** `engage_group()` is called with two living hostile monsters in the actor's room, and the
  player then submits one preflight-valid action
- **THEN** the persisted `enemy_ids` contains both dbrefs, the reconstructed battlefield places both
  on the opposing team, the round resolves, and terminal settlement behaves as it does for a
  single-enemy session

#### Scenario: engage is unchanged for its callers
- **WHEN** `engage(actor, target)` is called
- **THEN** it returns the same shape it returned before this change, persists every living co-located Monster ID in sorted persistent-ID order, and keeps its existing result shape

#### Scenario: One invalid target rejects the whole group
- **WHEN** `engage_group()` is called with one valid monster and one target that is dead, in another
  room, or not a `Monster`
- **THEN** the request is rejected, no session is persisted, no battlefield is registered, and no
  world time changes

#### Scenario: engage delegates to engage_group unchanged
- **WHEN** `engage(actor, target)` is called
- **THEN** it validates the anchor target, then delegates with all living co-located Monster IDs in persistent-ID order; explicitly staged engage_group callers keep their declared roster

#### Scenario: Any invalid precondition rejects the whole request
- **WHEN** the actor is not a `PlayerCharacter`, already has an active session, or any supplied
  target is not a living hostile `Monster` in the actor's room
- **THEN** `engage_group()` rejects the whole request — persisting no session

### Requirement: engage creates one persistent local combat session
Ordinary engagement SHALL require a player, a living local anchor target and no active session, persist every living co-located monster as enemies, include eligible local companions, and store only JSON-safe session values and persistent participant IDs.

#### Scenario: Present monster can be engaged
- **WHEN** a player invokes `engage` on a living hostile Monster in the current room
- **THEN** one hostile-mode session is persisted and registered with skip safety

#### Scenario: Co-located living companions join the session's allied team
- **WHEN** a player with co-located living bound companions engages a hostile target
- **THEN** the persisted `player_ids` contains the player and each such companion, and the session
  reconstructs them as the allied team

#### Scenario: Knocked-out companions are excluded from a new engagement
- **WHEN** a player whose bound companion is marked knocked out (HP at the nonlethal floor)
  engages a hostile target
- **THEN** the companion is absent from the session's allied team

#### Scenario: Remote or dead target is rejected
- **WHEN** the named target is in another room or has zero HP
- **THEN** no session or world-time change occurs

#### Scenario: Active session blocks another engagement
- **WHEN** a player already has a valid active session
- **THEN** a second `engage` request is rejected without replacing it

#### Scenario: Whole-cell ordinary membership
- **WHEN** ordinary engagement selects one monster among mixed ambient, site and quest-owned living monsters
- **THEN** all local living monsters join in persistent-ID order; designated examination and explicitly staged encounters retain their declared participants

