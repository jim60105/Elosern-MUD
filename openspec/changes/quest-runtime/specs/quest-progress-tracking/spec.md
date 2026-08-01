## ADDED Requirements

### Requirement: DEFEAT progress is planned automatically from committed player action events
The quest event-effect planner SHALL inspect `target_defeated` entries produced by an
`ActionResolver` request. It SHALL advance only active DEFEAT stages owned by the request actor when the
actor is a `PlayerCharacter`. A bound-target objective SHALL match `data["target_id"]` against the
record's `objective_target_ids`; an unbound objective SHALL match its declared `monster_tier`. Display
keys SHALL NOT be used as entity identity. The resulting quest mutation SHALL commit in the same action
transaction as lethal damage. The planner SHALL aggregate every matching defeat entry in one EventLog
per quest, cap progress at the current objective quantity, perform at most one stage transition, and
discard surplus kills rather than applying them to the next stage.

#### Scenario: Player defeat advances a matching tier objective automatically
- **WHEN** a player action lethally damages a monster whose tier matches the player's active DEFEAT stage
- **THEN** `ActionResolver.resolve()` commits the damage and increments quest progress without any caller
  invoking a separate observer

#### Scenario: Bound objective matches exact dbref
- **WHEN** two monsters share a display key but only one dbref is in `objective_target_ids`
- **THEN** defeating the unbound monster does not advance the quest and defeating the bound monster does

#### Scenario: Another character's action grants no ordinary kill credit
- **WHEN** an NPC, companion, or different `PlayerCharacter` defeats a matching-tier monster
- **THEN** the quest owner's ordinary DEFEAT progress is unchanged

#### Scenario: Quest planner failure rejects the complete action
- **WHEN** the quest planner cannot stage a valid transition because the actor's active record is
  malformed
- **THEN** the action rejects before commit and target HP, resources, progression, quest log, and pins
  all remain unchanged

#### Scenario: AREA defeat entries aggregate without skipping stages
- **WHEN** one AREA action defeats three matching targets while the current objective needs two
- **THEN** progress reaches two, the current stage transitions exactly once, and the surplus kill is not
  applied to the next stage

### Requirement: Room arrival drives REACH and ESCORT through supported persistent room hooks
`QuestObservableRoomMixin.at_object_receive()` SHALL call its parent hook and then
`observe_room_entry(self, obj)` for a `PlayerCharacter`. `GridRoom` SHALL adopt the mixin and
`AnchorRoom` SHALL inherit it. `InstanceRoom` SHALL adopt it while preserving its existing interacted
flag behavior. REACH SHALL match an anchor key, exact XYZ tuple, or bound instance dbref. ESCORT SHALL
additionally require at least one protected entity and require every protected entity to be alive and
present in the destination room.

#### Scenario: Anchor arrival completes a matching REACH stage
- **WHEN** the player enters an `AnchorRoom` whose `anchor_key` matches the active stage locator
- **THEN** that stage advances or completes in the same room-receive hook

#### Scenario: Grid arrival uses exact XYZ identity
- **WHEN** the player enters a `GridRoom` with the active REACH stage's exact `(x, y, z)` tuple
- **THEN** the stage advances without a room dbref stored in the definition

#### Scenario: Bound instance arrival uses the accepted record
- **WHEN** the player enters the `InstanceRoom` whose dbref is stored in the current record
- **THEN** a BOUND_INSTANCE REACH stage advances

#### Scenario: Escort requires every protected entity alive and present
- **WHEN** the player reaches an ESCORT destination while one protected entity is absent or has zero HP
- **THEN** the stage remains unchanged; it advances only after all protected entities arrive alive

#### Scenario: Existing instance interaction behavior remains intact
- **WHEN** a player enters an `InstanceRoom`
- **THEN** `interacted` becomes true and quest arrival observation also runs

### Requirement: Wilderness rooms do not advertise an arrival hook that normal traversal bypasses
`TerrainRoom` SHALL NOT adopt `QuestObservableRoomMixin`, and no definition registered by this change
SHALL contain a wilderness-coordinate destination. Tests SHALL preserve the verified behavior that
normal wilderness entry and stepping do not invoke quest room observation.

#### Scenario: Wilderness traversal does not produce false quest progress
- **WHEN** a player enters the wilderness and then takes an intra-wilderness step
- **THEN** `observe_room_entry()` is not called by either traversal and no quest stage advances

### Requirement: Stage completion advances exactly once and releases obsolete runtime bindings
When progress reaches an objective's quantity, the runtime SHALL release the current stage's instance
pin, clear all current-stage runtime bindings, reset progress, and either enter the next contiguous stage
or mark the quest `COMPLETED` if the objective was final. One event or room hook SHALL transition a given
quest at most once even when its quantity exceeds the remaining amount. Terminal records SHALL ignore
later matching events.

#### Scenario: Intermediate objective enters the next stage
- **WHEN** a matching event satisfies a non-final stage
- **THEN** the record advances by one stage, resets progress to zero, clears bindings, and remains active

#### Scenario: Final objective completes the quest
- **WHEN** a matching event satisfies the final stage
- **THEN** state becomes `COMPLETED`, progress is capped at the objective quantity, and bindings are
  cleared

#### Scenario: Instance pin is released on stage exit
- **WHEN** a bound-instance stage advances or completes
- **THEN** its exact quest pin is absent before the transition returns, while room deletion and promotion
  remain exclusively owned by map-instance reclamation

### Requirement: Change 15 exposes a deterministic no-AI completion seam for Phase 4
An integration test SHALL synchronize the hand-written catalog, accept its introductory hunt, resolve a
player's lethal action against a matching monster through `ActionResolver`, and observe the quest become
completed without directly calling quest progress functions or importing `world/ai/`. This completed
record SHALL be suitable for change 16's future player-facing accept/combat-entry/turn-in and reward
settlement. This API-level test SHALL NOT be treated as proof that the player-playable Phase-4 milestone
is complete before that command-level change-16 integration exists.

#### Scenario: Hand-written hunt completes through ordinary combat resolution
- **WHEN** AI services are unavailable and an integration test accepts the catalog hunt through the
  lifecycle API and resolves its fight through `ActionResolver`
- **THEN** deterministic resolution produces a `COMPLETED` record ready for change 16, without claiming
  that change 15 alone supplied player commands or a world encounter
