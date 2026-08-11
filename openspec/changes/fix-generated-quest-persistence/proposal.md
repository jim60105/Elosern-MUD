## Why

An accepted AI-generated quest (`ai_<digest>`) persists only its `QuestRecord`; the definition, guild offer, and stage spawn requirements live in three process-local registries that are empty after a restart. Every quest-log read then raises `QuestDataError` for the first `ai_*` record, poisoning the entire quest log (audit finding F01, `REPORT.md`).

## What Changes

- Persist the compiled payload (definition, offer, spawn requirements) of every generated quest at registration time in a durable Evennia Script.
- Restore all generated quests into the three registries at startup, before any quest-log read.
- Guarantee that an accepted generated quest remains readable, abandonable, and continuable (for stages whose runtime bindings survive) across a server restart.
- Add regression coverage for the restart-then-read flow.

## Capabilities

### Modified Capabilities

- `quest-lifecycle`: generated `QuestRecord` entries must resolve their definition after a restart instead of raising.
- `guild-quest-board`: generated offers are re-registered on startup so the board and acceptance keep working.
- `scene-builder`: compiled generated content is durably mirrored at registration time.

## Impact

- `world/quests/compile.py` (registration site), `world/quests/runtime.py` (read path), `world/quests/bootstrap.py` (startup), `server/conf/at_server_startstop.py` (sync order).
- New module under `world/quests/` owning the durable store; no schema change to `QuestRecord`; no user-facing command changes.
