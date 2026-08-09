## ADDED Requirements

### Requirement: Instance quest scenes schedule one post-commit flavor generation
A freshly spawned `BOUND_INSTANCE` quest scene with a scene-sentence context SHALL schedule exactly
one scene-flavor generation, registered through `transaction.on_commit` so it fires only after the
spawn transaction actually commits (a nested outer transaction that rolls back SHALL never schedule
a generation). The scheduling SHALL be fire-and-forget: it never blocks arrival, never delays
materialization, never raises to the caller — synchronous failures (unregistered layer, malformed
context, client-construction failure) included, which SHALL be logged as bounded diagnostics and
resolved to nothing — and a failure resolves to "no flavor". An already-bound stage, a permanent
destination, or a scene without a scene-sentence context SHALL schedule nothing.

#### Scenario: A fresh instance scene schedules one generation
- **WHEN** a player materializes a fresh instance scene whose requirement or archetype carries a
  scene sentence, with the `scene_builder` profile enabled
- **THEN** exactly one flavor generation is scheduled on commit, and the materialization result
  and traversal are unaffected

#### Scenario: A rolled-back outer transaction schedules nothing
- **WHEN** the enter command runs inside an outer transaction that rolls back after materialization
- **THEN** no flavor generation is scheduled or fired

#### Scenario: A synchronous scheduling failure never reaches the command
- **WHEN** the layer is not registered, the context dict is malformed, or client construction
  raises before a Deferred exists
- **THEN** the scheduling call logs a bounded diagnostic, returns normally, and the 進入 command
  completes without error

#### Scenario: An already-bound stage schedules nothing
- **WHEN** the player re-enters a stage that is already bound (no fresh spawn)
- **THEN** no flavor generation is scheduled and the existing binding is returned

#### Scenario: A scene without scene-sentence context schedules nothing
- **WHEN** a stage's requirement has neither a scene sentence nor a resolvable archetype sentence
- **THEN** the materialization carries no flavor context and nothing is scheduled

#### Scenario: Offline profile resolves to no flavor without a network request
- **WHEN** the `scene_builder` profile is disabled and a fresh scene materializes
- **THEN** the scheduled generation resolves to no flavor, no network request occurs, and the room
  is unchanged

### Requirement: The flavor write is deterministic, idempotent, and sole-writer
`room.db.scene_flavor` SHALL be written only by the deterministic SceneBuilder apply helper. The
write SHALL verify the room's database row authoritatively (a cached typeclass is not proof of
existence after reclamation) before writing, SHALL be a no-op when the room no longer exists or
already carries a flavor (never overwrites, never regenerates), SHALL catch database and
object-deletion exceptions and resolve them to the same no-op outcome, SHALL never roll back or
block the materialization transaction, and SHALL leave the room description (`room.db.desc`)
untouched.

#### Scenario: A completed flavor is written once
- **WHEN** a flavor generation completes successfully for an existing flavor-less room
- **THEN** `room.db.scene_flavor` holds the flavor text and `room.db.desc` is unchanged

#### Scenario: A vanished room receives no write
- **WHEN** the flavor completes after the instance room was reclaimed and only a stale cached
  reference remains
- **THEN** the authoritative existence check fails, no write occurs, no error escapes, and the
  outcome is "no flavor"

#### Scenario: A room with an existing flavor never regenerates
- **WHEN** a completion tries to apply a flavor to a room that already carries one
- **THEN** the existing value is kept and no regeneration occurs

### Requirement: Completed flavor is pushed to present players and rendered in look
On a successful write, the flavor SHALL be pushed as plain text to every `PlayerCharacter` whose
location is the room (absent players are not chased). The shared appearance layer SHALL render
`room.db.scene_flavor` as a paragraph after the room description and before the exit line, on the
text look command, the character's `at_look` seam, and the webclient `explore.look` action
identically. A room without flavor SHALL render exactly as today.

#### Scenario: Present players receive the flavor on completion
- **WHEN** a flavor completes while players are inside the room
- **THEN** those players receive the flavor text, and players who left receive nothing

#### Scenario: Look renders the flavor paragraph on every entry path
- **WHEN** a player looks at a flavor-bearing scene room through the text 看 command, the `at_look`
  seam, and the webclient `explore.look` action
- **THEN** all three outputs show the room description followed by the flavor paragraph, followed
  by the 「出口」 line, with no English frame string

#### Scenario: Flavor-less rooms render as today
- **WHEN** a player looks at a room with no `scene_flavor`
- **THEN** the appearance is byte-identical to the pre-change rendering
