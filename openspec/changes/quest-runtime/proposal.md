## Why

Roadmap item 15 requires the deterministic quest runtime before guild rewards or AI-generated quest
proposals can be added. The repository already has a persistent player quest-log seam, structured
action events, a player-driven clock with a reserved `quest_deadlines` stage, permanent map locations,
and instance-room pinning, but no component turns those facilities into accept, progress, complete,
fail, or abandon behavior.

Phase 4 must end with a playable path that uses hand-written quests and no AI services. This change
builds and integration-tests the normalized deterministic consumer and one hand-written quest catalog,
but does not claim that player-facing milestone by itself. Change 16 must add guild accept/turn-in,
reward settlement, and a player-reachable composition of the already-landed combat runtime before the
Phase-4 milestone can be declared complete. Changes 20 and 21 remain responsible for AI
`QuestBlueprint` proposals and generated scene material respectively.

## What Changes

- Add immutable, registry-backed `QuestDefinition` content with explicit `QuestStage` indices, typed
  deterministic objectives, static room locators, deadline policy, and structural validation. This is
  runtime input, not the change-20 AI `QuestBlueprint` schema.
- Add persisted per-character `QuestRecord` state and deterministic APIs for acceptance, abandonment,
  stage advancement, completion, and failure. Unaccepted quests are represented by absence; terminal
  records remain as history.
- Add automatic quest progress from committed action `EventLog` entries and room arrival. Defeat
  matching uses stable entity dbrefs carried in `target_defeated` entries; reach and escort matching use
  anchor keys, XYZ coordinates, or an explicitly bound instance-room dbref.
- Extend the action pipeline with a registered event-effect planner seam. Quest progress caused by a
  successful skill is staged as a `PendingEffect` and commits atomically with damage and resource cost;
  out-of-combat casts and combat rounds need no manual `observe_event_log()` call.
- Register the room-arrival hook on `GridRoom`/`AnchorRoom` and `InstanceRoom`. Wilderness-coordinate
  objectives remain unsupported because the installed wilderness contrib bypasses `move_to()` for its
  normal traversal path.
- Register deadline settlement from the server startup composition root, using the existing
  `quest_deadlines` clock stage. Due active quests fail before instance reclamation in the same clock
  advance.
- Add an explicit instance-binding API that pins a room already created by another deterministic
  caller and releases that pin on stage exit or terminal transition. This change never invokes
  SceneBuilder and never spawns an instance; change 21 will create the room before binding it.
- Add a hand-written quest catalog and deterministic integration tests that prove an offline API-level
  accept-to-completion seam. Player-facing accept, combat entry, turn-in, and reward payout remain an
  explicit change-16 integration obligation.

## Capabilities

### New Capabilities

- `quest-blueprint`: Runtime-owned `QuestDefinition`, typed stages/objectives, static destination
  locators, immutable registration, and the boundary with change 20's future AI `QuestBlueprint`.
- `quest-lifecycle`: Persistent `QuestRecord` state and accept, abandon, complete, fail, and instance
  binding operations.
- `quest-progress-tracking`: Automatic committed-action and room-arrival progress, stable target
  identity, stage transitions, and instance pin release.
- `quest-failure-conditions`: World-clock deadline expiry and key-entity defeat failure.

### Modified Capabilities

- `action-resolution-pipeline`: Successful action events gain stable dbref identity and registered
  event-effect planners whose state changes commit atomically with the action.

## Impact

- New implementation modules under `world/quests/` for definitions, catalog, runtime, and startup.
- Additive changes to `world/rules/action.py`, `world/rules/event_log.py`, `world/rules/combat.py`,
  `typeclasses/rooms.py`, and `server/conf/at_server_startstop.py`.
- Uses the existing `PlayerCharacter.db.quest_log`, `WorldClock` event-source registry, map locators,
  and instance pin APIs. It does not modify reward, guild-rank, wallet, shop, AI, or scene-generation
  behavior. Change 15 completion is not evidence that the design document's player-playable Phase-4
  milestone has been reached; that requires change 16's command-level integration test.
- No migration or backward-compatibility work is required because the project is unreleased and has no
  external users.
