## 1. Durable generated-quest store

- [ ] 1.1 Create `world/quests/generated_quest_store.py` with a `GeneratedQuestStore(DefaultScript)` (key `generated_quest_store`) exposing `list_payloads()`, `append_payload(payload)`, and `clear()` helpers
- [ ] 1.2 Add serialization/deserialization helpers for the compiled definition, offer, and requirements payloads (single reconstruction path mirroring `register_generated_quest`)

## 2. Registration persistence

- [ ] 2.1 In `world/quests/compile.py::register_generated_quest`, append the compiled payload to the durable store FIRST (idempotent by key); on store failure abort registration with no in-memory entries
- [ ] 2.2 Register into the three registries only after the durable append succeeds; startup restore reconciles store → registries on a mid-crash
- [ ] 2.3 Fault-injection tests: store write failure leaves no registry entries; termination between append and registration is healed by startup restore

## 3. Startup restore

- [ ] 3.1 In `world/quests/bootstrap.py` (or the new store module), add `restore_generated_quests()` that repopulates `QUEST_DEFINITION_REGISTRY`, `GUILD_OFFER_REGISTRY`, and `SCENE_REQUIREMENT_REGISTRY` from the store before any quest-log read
- [ ] 3.2 Wire `restore_generated_quests()` into `sync_quest_runtime` ahead of catalog registration and quest-log reads; keep the call idempotent across restarts

## 4. Tests and verification

- [ ] 4.1 Unit test: registering a generated quest persists the payload and re-registration is idempotent
- [ ] 4.2 Integration test: accept a generated quest, simulate restart (fresh registries + restore), then read the log, abandon, and complete the quest
- [ ] 4.3 Run `world/quests`, `world/rules` (guild), and repository traceability checks
