## Why

Two quest-content validity defects from audit run-1: (F11) ESCORT quests can be published and accepted but no production path ever binds protected entities (the compiler forbids ESCORT `npc_req` while permanent locations are never bound), so they can never complete; (F21) REACH/ESCORT objectives accept any positive `quantity`, but the first matching arrival fulfills the whole objective at once.

## What Changes

- REACH/ESCORT objectives are restricted to `quantity: 1` at proposal and compile validation.
- ESCORT publishing is refused with a clear error until a protected-entity binding flow exists; escort requests from the guild board are refused with a player-facing message.
- Arrival observation increments progress by at most one per event (capped at quantity) instead of unconditionally fulfilling the objective.

## Capabilities

### Modified Capabilities

- `quest-blueprint`: quantity cap and ESCORT publishability rules.
- `quest-progress-tracking`: bounded per-event arrival progress.

## Impact

- `world/quests/definitions.py`, `world/quests/compile.py`, `world/ai/scenario_director.py`, `world/quests/room_observation.py`, `commands/guild.py` request path, tests; catalog quests are unaffected (quantity 1).
