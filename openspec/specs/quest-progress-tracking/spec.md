# quest-progress-tracking Specification

## Purpose
Automatic quest progress driven by committed player actions (DEFEAT) and room arrival (REACH/ESCORT),
with stable dbref identity, one transition per event, and instance-pin release on every stage exit.

## Requirements
### Requirement: DEFEAT progress is planned automatically from committed player action events
The quest event-effect planner SHALL inspect `target_defeated` entries produced by an
`ActionResolver` request. It SHALL advance only active DEFEAT stages owned by the request actor when the
actor is a `PlayerCharacter`, and SHALL additionally advance the owner's matching stage when the request
actor is a bound companion of the owner (per the party binding) and is not knocked out; a companion's
entries SHALL follow the same aggregation, cap, and one-transition rules as the owner's own. A
bound-target objective SHALL match `data["target_id"]` against the record's `objective_target_ids`; an
unbound objective SHALL match its declared `monster_tier`. Display
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

#### Scenario: A bound companion's kill advances the owner's objective
- **WHEN** a bound, non-knocked-out companion defeats a monster matching the owner's active DEFEAT stage
- **THEN** the owner's quest progress advances in the same action transaction with the same cap and
  one-transition rules

#### Scenario: A knocked-out companion's kill grants no credit
- **WHEN** a knocked-out companion defeats a matching-tier monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: Another character's action grants no ordinary kill credit
- **WHEN** an NPC that is not a bound companion, a different `PlayerCharacter`, or a monster defeats a matching-tier monster
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
flag behavior. REACH SHALL match an anchor key, exact XYZ tuple, or bound instance dbref. Arrival
observation SHALL advance when the player is the arriving object and at least one bound companion
is present in the destination room — already there or arriving with the player — and SHALL be
re-run once after companion follow moves complete so first-arrival co-presence is visible, with
the one-transition rule making the repeated observation idempotent. ESCORT SHALL
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

#### Scenario: Companion co-presence satisfies arrival
- **WHEN** the player arrives at a matching destination and at least one bound companion is
  present there after the follow moves complete
- **THEN** the REACH or ESCORT stage advances exactly once, and the repeated post-follow
  observation advances nothing a second time

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

### Requirement: Arrival observation advances at most one per event and never exceeds quantity

REACH/ESCORT arrival observation SHALL increment stage progress by at most one per matching arrival event and SHALL cap progress at the objective quantity, so even a non-1 quantity (should one slip through) can never jump to full completion in a single arrival. The post-follow re-observation (party-follow D-2) SHALL NOT re-count the same arrival event: when a companion was already present in the destination, the re-run is skipped because the first observation has already advanced every matching stage for that event.

#### Scenario: First arrival with quantity one completes the stage

- **WHEN** the player arrives at a matching destination with companion co-presence and the stage quantity is 1
- **THEN** progress becomes 1, the stage completes exactly once, and a repeated post-follow observation advances nothing

#### Scenario: Arrival never over-fills progress

- **WHEN** a matching arrival would advance progress beyond the objective quantity
- **THEN** progress is capped at the quantity and the quest transitions at most once
