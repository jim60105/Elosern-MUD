# scene-flavor-apply

## Why

`scene-flavor-layer` delivers the guarded generative flavor layer, but nothing schedules it:
quest scenes still show only the deterministic one-line scene sentence, the flavor layer has no
consumer, and players never see atmosphere prose that echoes the quest.

## What Changes

- **Deterministic flavor context on materialization.** `SceneMaterialization` gains an optional
  `flavor_context` (a plain bounded dict — never a `world.ai` import, keeping the deterministic-path
  ban green). Only a freshly spawned instance scene with a scene-sentence context carries it; an
  already-bound stage or a permanent destination carries `None`.
- **Composition root in `server/scene_flavor_service.py`** (mirrors `ai_director_service.py`):
  validates the context dict at the adapter boundary, builds the `scene_builder` profile client
  (live when enabled, non-`None` offline stub when disabled), and schedules exactly one flavor
  generation through `transaction.on_commit` — so a nested transaction rollback never fires it —
  fire-and-forget, never blocking arrival, and never raising to the caller (synchronous failures
  included).
- **Deterministic, idempotent write.** `apply_scene_flavor(room, text)` in `world/quests/
  scene_builder.py` is the sole writer of `room.db.scene_flavor`; it verifies the room row
  authoritatively before writing, never regenerates an existing value, never touches `room.db.desc`,
  and a vanished room or generation failure leaves no flavor (logged).
- **Player-visible completion.** On success the flavor is pushed to the `PlayerCharacter`s present
  in the room; a later `look` renders the flavor paragraph after the room description through the
  shared room appearance hook (`typeclasses/rooms.py::Room.get_display_desc` — text 看, `at_look`,
  and webclient `explore.look` identically).
- **No gameplay dependency.** Offline profile, transport failure, retry exhaustion, or missing
  context all resolve to "no flavor"; rooms, descriptions, and the quest flow are untouched.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities
- `scene-flavor`: New application requirements — post-commit scheduling, deterministic idempotent
  write, present-player push, and look rendering of the flavor paragraph.
- `scene-builder`: New requirements — `SceneMaterialization` carries deterministic flavor context
  for freshly spawned instance scenes, and the flavor write is deterministic, idempotent, and
  never rolls back or blocks materialization.
- `localized-appearance`: The room appearance frame gains the optional flavor paragraph, rendered
  identically on the text look command, the `at_look` seam, and the webclient `explore.look`
  action.

## Impact

- Modified: `world/quests/scene_builder.py` (context helper + `apply_scene_flavor` + result field),
  `world/quests/definitions.py` (no change), `commands/scene.py` (schedules on commit via the
  service), the shared room appearance hook (`typeclasses/rooms.py::Room.get_display_desc`) used by
  the text 看 command, the `at_look` seam, and the webclient `explore.look` path.
- New: `server/scene_flavor_service.py` and its tests under `server/conf/tests/`.
- Unchanged: `world/ai/` (the layer already landed), `world/ai/profiles.py`, room descriptions,
  quest/combat/economy mechanics.
- No new dependencies.
