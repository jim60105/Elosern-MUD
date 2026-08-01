## 1. Confirm landed contracts

- [x] 1.1 Confirm `PlayerCharacter.quest_log` remains an unused list attribute and no quest runtime
  module exists beyond the package stub.
- [x] 1.2 Confirm `quest_deadlines` remains before `instance_reclamation` and has no registered source.
- [x] 1.3 Confirm `ActionResolver`, combat, and `CmdCast` still match design D-4's composition assumptions.
- [x] 1.4 Reconfirm the installed wilderness traversal bypasses `move_to()` before excluding TerrainRoom.

## 2. Deterministic definitions and catalog

- [x] 2.1 Implement the closed enums and deeply immutable `RoomLocator`, `QuestObjective`, `QuestStage`,
  and `QuestDefinition` dataclasses in `world/quests/definitions.py`.
- [x] 2.2 Implement `QuestDefinitionError`, `QUEST_DEFINITION_REGISTRY`, and sole-writer
  `register_quest_definition()` with every structural and objective-specific validation from the spec.
- [x] 2.3 Add the hand-written introductory hunt to `world/quests/catalog.py` using permanent content only.
- [x] 2.4 Test explicit stage indices, every valid objective shape, every invalid field combination,
  equal/conflicting duplicate registration, immutable nested data, static locators, and the single
  `None` deadline meaning.
- [x] 2.5 Test that raw mapping/AI-shaped input cannot enter the deterministic registry.
- [x] 2.6 Test that an anchor present in lore but absent from `ANCHOR_PLACEMENT_REGISTRY` is rejected,
  while a placed anchor resolves to its synced `AnchorRoom`.

## 3. Persisted quest records and lifecycle

- [x] 3.1 Implement `QuestState`, frozen `QuestRecord`, JSON-safe serialization, and strict parsing in
  `world/quests/runtime.py`.
- [x] 3.2 Implement named data/transition/not-found/already-active errors and validate all touched records
  before replacing a quest log.
- [x] 3.3 Implement deterministic acceptance IDs, active-duplicate rejection, terminal retry, and explicit
  deadline conversion in `accept_quest()`.
- [x] 3.4 Implement `abandon_quest()` with idempotent terminal handling and binding release.
- [x] 3.5 Test JSON round-trip, malformed records, missing definitions, first acceptance, duplicate active
  acceptance, retry history, deadline/no-deadline arithmetic, unknown IDs, and repeated abandonment.

## 4. Runtime instance and entity binding

- [x] 4.1 Implement preflight/snapshot/restore helpers for quest-log and instance-pin transitions.
- [x] 4.2 Implement `bind_stage_runtime()` with distinct objective/protected IDs, stable dbrefs,
  disjoint-set validation, type/liveness checks, exact pin reason, identical-call idempotence, and
  conflicting-rebind rejection.
- [x] 4.3 Implement centralized stage-exit binding release that tolerates an already-deleted bound room.
- [x] 4.4 Fault-inject pin and quest-log writes to prove database rollback and Evennia attribute-cache
  restoration in both write orders.
- [x] 4.5 Test that overlapping objective/protected inputs and persisted overlap fail before mutation,
  and that valid objective targets never enter protected-entity failure matching.

## 5. Stable action events and planner seam

- [x] 5.1 Extend step 7 damage entry construction to track projected HP per target in pending order and
  emit one `target_defeated` entry with integer dbref and tier on the positive-to-non-positive crossing.
- [x] 5.2 Implement idempotent-by-name `register_event_effect_planner()` and invoke planners after EventLog
  construction but before time-cost validation and commit.
- [x] 5.3 Add surface-specific `quest_log`/`instance_pin` snapshot handlers, aggregate declared surfaces
  per touched object, and restore player/room objects outside the original request without applying the
  LivingEntity snapshot shape to rooms.
- [x] 5.4 Test lethal/nonlethal/miss cases, two damage effects against one target, same-key different-dbref
  targets, malformed planner output, repeated registration, planner staging, unsupported surfaces, and
  rollback across multiple out-of-request player/room effects.
- [x] 5.5 Run all existing action, combat, overwhelm, disengage, progression, and command tests unchanged.

## 6. Action-driven quest progress and failure

- [x] 6.1 Implement the quest event-effect planner for player-owned DEFEAT progress using bound dbrefs or
  monster tiers and no display-key identity.
- [x] 6.2 Implement exact protected-entity defeat failure across active player records without granting
  ordinary kill credit to NPCs, companions, or other player characters.
- [x] 6.3 Implement stage-progress capping, one-stage-per-event advancement, final completion, terminal
  no-op behavior, AREA-entry aggregation with surplus discard, and binding release through shared
  transition computation.
- [x] 6.4 Test player and non-player kill credit, bound and tier matching, duplicate display keys,
  protected death, AREA multi-kill aggregation, and action/quest/pin rollback on every injected commit
  failure.

## 7. Room-driven quest progress

- [x] 7.1 Add `QuestObservableRoomMixin` and adopt it on `GridRoom` and `InstanceRoom`, preserving
  `AnchorRoom` inheritance and `InstanceRoom.interacted` behavior.
- [x] 7.2 Implement REACH matching for anchor key, exact XYZ, and bound instance dbref.
- [x] 7.3 Implement ESCORT completion requiring every protected entity alive and present.
- [x] 7.4 Test anchor, grid, and instance arrival; missing/dead escort entities; multiple matching quests;
  one transition per hook; and terminal no-op behavior.
- [x] 7.5 Test `TerrainRoom` MRO and real wilderness entry/step paths to prove they do not invoke quest
  arrival observation.
- [x] 7.6 Run all existing room, grid, movement, wilderness, and instance tests unchanged.

## 8. Deadline settlement and startup

- [x] 8.1 Implement `settle_quest_deadlines()` with per-character atomic replacement, pin release,
  terminal/no-deadline filtering, malformed-character isolation, diagnostics, and JSON-safe events.
- [x] 8.2 Implement `sync_quest_runtime()` to register catalog content, the action planner, and the clock
  source idempotently.
- [x] 8.3 Update `server/conf/at_server_startstop.py` to call quest sync after map sync; do not add a
  maps-to-quests import.
- [x] 8.4 Test normal/repeated startup, due/not-due/no-deadline records, malformed-character isolation,
  exact scheduled payloads, and unchanged `_STAGE_ORDER`.
- [x] 8.5 Reproduce the deadline-before-reclamation existence test with a bound quest room due in one
  clock advance.

## 9. Offline runtime path and future Phase-4 seams

- [x] 9.1 Add an API-level no-AI integration test that syncs the catalog, accepts the introductory hunt,
  resolves a lethal player action, and reaches `COMPLETED` without manually invoking quest progress;
  document that it is not a player-command acceptance test.
- [x] 9.2 Add an integration test proving direct resolver, `CmdCast`, combat round, and overwhelm paths all
  execute the registered planner exactly once.
- [x] 9.3 Add a contract test showing change 16 can read a completed record without this change paying a
  reward; record the change-16 obligation to supply player-facing accept, combat entry, and turn-in before
  claiming the Phase-4 playable milestone.
- [x] 9.4 Add contract tests showing change 21 can bind an already-created instance and entities without
  this change spawning them.
- [x] 9.5 Add a dependency/source scan proving `world/quests/` imports no `world/ai/`, invokes no LLM, and
  contains no prototype-spawn call.
- [x] 9.6 Add a source/API guard proving change 15 defines no ACQUIRE progress entry point; change 16 must
  add acquisition at its inventory-owning transaction boundary.

## 10. Verification

- [x] 10.1 Map every delta-spec scenario to at least one deterministic test.
- [x] 10.2 Run focused quest, action, combat, clock, map, room, command, and server-start tests.
- [x] 10.3 Run `uv run --locked evennia test --settings settings.py .`.
- [x] 10.4 Run `uv run --locked python -m compileall -q world typeclasses commands server`.
- [x] 10.5 Run `openspec validate quest-runtime --strict` and `openspec validate --all --strict`.
- [x] 10.6 Run `git diff --check` and confirm only planning artifacts are changed by this proposal rewrite.