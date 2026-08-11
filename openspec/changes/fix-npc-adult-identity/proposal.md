## Why

Two NPC spawn paths violate the mandatory-adult invariant (audit finding F03): `_sync_service_host` (`world/rules/guild_economy.py:38-56`) creates the guild master and merchant without `age`/`apparent_age`, and `_spawn_opponent` (`world/rules/guild_exams.py:189-219`) does the same for exam opponents. Every other NPC path carries canonical adult ages; the portrait adult gate then rejects these NPCs deterministically (`world/art/adult.py:26-42`).

## What Changes

- Introduce a shared adult-identity initializer for synced/spawned NPCs that persists `age = apparent_age = 18` when absent.
- Call it from `_sync_service_host` and `_spawn_opponent` so both NPC classes carry canonical adult identities from creation.
- Keep the existing repair/baseline behavior of the onboarding guard and scene occupants unchanged.

## Capabilities

### New Capabilities

- `npc-adult-identity`: canonical adult age attributes for procedurally spawned and synced NPCs.

### Modified Capabilities

- `sample-city-altoria`: guild service hosts carry adult age attributes.
- `guild-rank-exams`: exam opponents carry adult age attributes.

## Impact

- `world/rules/guild_economy.py`, `world/rules/guild_exams.py`, new helper (likely in `typeclasses/npcs.py` or `world/rules/`), tests for both spawn paths.
