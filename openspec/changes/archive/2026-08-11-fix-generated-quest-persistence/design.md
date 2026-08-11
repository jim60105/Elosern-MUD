## Context

`register_generated_quest` (`world/quests/compile.py:757-810`) publishes a compiled definition into `QUEST_DEFINITION_REGISTRY` (`world/quests/definitions.py:242`), a guild offer into `GUILD_OFFER_REGISTRY` (`world/rules/guild_offers.py:55`), and spawn requirements into `SCENE_REQUIREMENT_REGISTRY` (`world/quests/compile.py:130`). All three are module-level dicts that the code comment itself states "do not survive a server restart" (`compile.py:125-129`). `accept_quest` persists only `definition_key` (`world/quests/runtime.py:296-331`); after a restart `read_records → validate_record_runtime → definition_for` raises `QuestDataError` (`runtime.py:160-181, 280-288`), making the whole log unreadable. Hand-written catalog quests survive because `register_catalog` re-registers them idempotently at every startup; generated content has no equivalent mirror.

## Goals / Non-Goals

**Goals:**
- Accepted generated quests survive restarts: readable, abandonable, and continuable for stages whose runtime bindings still exist.
- Registration is durable-first: no registered-but-unpersisted or persisted-but-unregistered generated quest can survive a restart.
- Startup restores generated content before any player quest-log read.

**Non-Goals:**
- Quest progress/instance scene persistence for in-progress quest stages (separate concern).
- Cleanup/GC of completed generated quests from the durable store.
- Changing the `QuestRecord` schema.

## Decisions

**D1 — A single `GeneratedQuestStore` Evennia Script as the durable mirror.** One `DefaultScript` (key `generated_quest_store`) holding a list of serialized payloads `{definition: {...}, offer: {...}, requirements: {...}}`. Rationale: matches the project's existing Script-as-record pattern (`LoreRecord`, `ArtAssetRecord`), survives restarts, and gives one write point. The server is a single game process, so store access is never concurrent; a duplicate store Script is a split-brain hazard and fails loudly at lookup instead of silently picking one.

**D2 — Durable-first registration.** `register_generated_quest` appends the payload to the durable store BEFORE touching the three in-memory registries; a store write failure aborts registration entirely (no in-memory entries). The append is idempotent by definition key **with content verification**: an already-stored equal payload is a no-op, while a divergent payload for the same key (possible only in a mid-crash divergence window) is rejected before any registry write, so the store can never silently regress an offer or reward after a restart. A crash between the durable append and the registry registration is self-healed by startup restore (D3), which reconciles store → registries, so no registered-but-unpersisted or persisted-but-unregistered state can survive a restart.

**D3 — Startup restore in `sync_quest_runtime` before any quest-log read.** Load the store and repopulate the three registries; equal content already present is skipped idempotently, while conflicting content raises. Every reconstructed payload is re-validated for self-consistency (the offer must bind its own definition; each spawn requirement must sit at its own position with the objective kind of the definition stage it describes) so a corrupt or schema-drifted payload fails loudly at startup — exactly the current contract's behavior — instead of registering a mismatched offer or leaving the SceneBuilder to fail mid-game. No cleanup or compatibility logic is needed for legacy/orphaned records: the project is pre-release with no users, so a record whose definition cannot be restored fails loudly exactly as the current contract requires.

**D4 — Reuse the existing serialization helpers.** The compiled definition/offer/requirements are dataclasses; serialize via `dataclasses.asdict` (or existing JSON helpers in `world/quests/compile.py` if present) and reconstruct with the same constructor `register_generated_quest` uses, keeping one deserialization path.

## Risks / Trade-offs

- **Stale store growth**: completed quests stay in the store; acceptable for single-player scale, cleanup left as non-goal (pre-release, no migration concerns).
- **Schema drift**: payloads serialized by an older build could fail to reconstruct; a failed restore surfaces as the existing loud `QuestDataError` behavior — no compatibility layer is added for pre-release saves.
