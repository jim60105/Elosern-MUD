## Why

The onboarding corridor-skip observer is invoked only from `GridRoom.at_object_receive`; leaving the guided corridor into a plain `Room` (e.g. Limbo) or an `InstanceRoom` never marks the guide skipped, so arrival scenes can replay and the guard keeps prompting (audit finding F20).

## What Changes

- The onboarding room-entry observer runs from the shared movement-completion boundary for every room type (plain `Room`, `GridRoom`, `TerrainRoom`, `InstanceRoom`), so any successful player arrival outside the guided corridor marks the guide skipped.
- The `GridRoom`-only hook is removed in favor of the shared boundary to avoid double observation.
- Wilderness special traversal also flows through the same notification.

## Capabilities

### Modified Capabilities

- `onboarding-guide`: deviation detection applies to every room type via the shared movement boundary.

## Impact

- `typeclasses/rooms.py` (remove GridRoom-only hook), `typeclasses/exits.py` / shared movement-completion path (call observer), `world/rules/onboarding.py` (idempotent observer), tests.
