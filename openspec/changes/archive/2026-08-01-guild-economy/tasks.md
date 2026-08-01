## 1. Confirm dependency contracts

- [x] 1.1 Verify change 15 is implemented and strictly validated before beginning code changes; confirm
  its QuestDefinition, ObjectiveKind, quest-record parsing, lifecycle, event planner, and startup APIs
  match the published artifacts.
- [x] 1.2 Confirm `PlayerCharacter.guild_rank`/`wallet`, `guild_merit`, flat inventory, guild/price lore,
  component holder, clock stages, and Altoria exterior keys still match design assumptions.
- [x] 1.3 Confirm the current combat, overwhelm, monster-policy, disengage, skip-safety, and command paths
  that player combat sessions will compose; add no parallel damage or flee path.
- [x] 1.4 Inspect the installed Evennia Component API and use its real field, attach, query, and persistence
  signatures in tests before authoring project components.

## 2. Immutable economy content and balance rulebook

- [x] 2.1 Add deeply immutable ItemDefinition and ShopDefinition identity/offer-key registries under
  `world/lore/`, including meal, healing-potion, and plain-sword content without tunable numeric rules.
- [x] 2.2 Load and validate YAML shop rules against lore identities, including price-table references,
  exact integer buy/sell prices, sellability, opening/restock hours, stock caps, initial quantities, and
  restock quantities.
- [x] 2.3 Add `world/rules/rulebook/guild_economy.yaml` with hand-written quest rewards, strictly
  increasing E-through-S merit thresholds, exact exam profiles, shop prices/hours, and stock/restock
  values.
- [x] 2.4 Validate E/D examiner physical stats inside `human_adventurer`, C/B inside `human_elite`, A
  inside `human_veteran`, S inside `human_swordmaster`, and every examiner skill key.
- [x] 2.5 Test immutable nested content, all invalid catalog/rulebook shapes, no floating-point money, and
  cross-registry referential integrity.

## 3. Service components and Altoria interiors

- [x] 3.1 Implement GuildStaff, Merchant, and GuildExaminer Components carrying stable branch/service
  identifiers and persistent service data without direct player-state writes.
- [x] 3.2 Extend map startup with stable-tagged permanent `altoria_guild_hall` and
  `altoria_general_store` rooms and bidirectional exits from their documented exteriors.
- [x] 3.3 Idempotently create one adult guild staff/examiner host, one adult merchant host, and exam spawn
  metadata; attach/update components by stable identity.
- [x] 3.4 Initialize merchant stock only when absent and preserve every live stock quantity on repeated
  synchronization.
- [x] 3.5 Test fresh/repeated sync, no duplicate rooms/exits/NPCs/components, permanent reachability, and
  unchanged thirteen-node/twelve-link xyzgrid topology and shortest paths.
- [x] 3.6 Add source tests proving Components delegate mutations and contain no rank, merit, wallet,
  inventory, quest-log, reward-claim, or combat-session assignments.

## 4. Guild registration and membership validation

- [x] 4.1 Implement strict JSON-safe guild-registration parsing and named membership/data/location/
  ambiguity errors in `world/rules/guild.py`.
- [x] 4.2 Implement `register_adventurer()` with local GuildStaff validation, branch derived only from
  that component, all-eight-trait `get_display_value()` snapshot, current tick metadata, universal F
  assignment, and idempotent reread behavior.
- [x] 4.3 Implement shared local service-host resolution for zero, one, and ambiguous Component hosts;
  reject remote dbref use.
- [x] 4.4 Add atomic rank/registration snapshots and restore both database and AttributeProperty caches
  on every fault-injected write order.
- [x] 4.5 Test undisguised/disguised registration, exceptional true stats still receiving F, repeat after
  disguise change, non-player/remote/ambiguous rejection, and malformed partial membership.
- [x] 4.6 Update `get_display_value()` documentation and boundary scans so registration is the sole guild
  caller and combat, reward, board, merit, exam, and promotion remain forbidden consumers.

## 5. Inventory planning and ACQUIRE progress

- [x] 5.1 Implement immutable InventoryPlan plus positive-quantity addition/removal normalization,
  known-item validation, complete-removal preflight, and before/after repeated-key lists.
- [x] 5.2 Refactor `add_item()` and `remove_item()` as standalone atomic wrappers over the planner while
  retaining import loader raw-population behavior.
- [x] 5.3 Extend quest ObjectiveKind/validation with ACQUIRE's exact known-item and positive-quantity
  shape, rejecting every unrelated objective field.
- [x] 5.4 Add quest-runtime computation of ACQUIRE replacements from positive committed plan additions,
  with multiple-quest matching, one-stage-per-plan transitions, capping, and surplus discard.
- [x] 5.5 Compose inventory and quest-log writes with an outer caller transaction without early/double
  application; provide standalone cache-consistent application.
- [x] 5.6 Test planning side-effect freedom, duplicate item quantities, insufficient removal, unknown
  items, import non-progression, no caller assertion API, removal non-reversal, and every rollback point.
- [x] 5.7 Run existing equipment, import, action, and quest tests unchanged after the inventory refactor.

## 6. Guild offers, board access, and reward settlement

- [x] 6.1 Implement frozen ItemQuantity, QuestReward, GuildQuestOffer, immutable registry, and sole-writer
  registration with quest/item/branch/rank/reward-band validation.
- [x] 6.2 Register the Altoria hand-written introductory offer idempotently with an in-band integer reward
  and known reward items.
- [x] 6.3 Implement stable local/rank-filtered board listing using canonical guild rank only.
- [x] 6.4 Implement offer acceptance and abandonment as validation adapters over change 15 lifecycle APIs,
  without constructing or mutating quest records in the guild layer.
- [x] 6.5 Implement strict JSON-safe `guild_reward_claims` parsing and `turn_in_quest()` preflight for
  completed record, exact issuer, known offer, and unclaimed deterministic quest ID.
- [x] 6.6 Implement one reward transaction covering integer wallet, repeated-item InventoryPlan,
  ACQUIRE quest-log replacement, guild-merit counter, and claims, leaving completed history unchanged.
- [x] 6.7 Fault-inject every reward write position and restore database and in-process Attribute, trait,
  inventory, quest-log, and claim surfaces.
- [x] 6.8 Test equal/conflicting offer registration, all invalid reward shapes, F/A/S band boundaries,
  board filtering, over-rank direct acceptance, first/duplicate/later-ID claims, and reward-driven ACQUIRE.

## 7. Innate basic attack and persistent combat sessions

- [x] 7.1 Add `basic_attack` to the skill registry and `INNATE_SKILL_KEYS` beside flee as zero-cost
  SINGLE/ENEMY physical damage unusable outside combat.
- [x] 7.2 Test no-skill PlayerCharacter/NPC/Monster ownership, monster-policy fallback, ordinary
  ActionResolver validation, modifier/EventLog/planner execution, and out-of-combat rejection.
- [x] 7.3 Implement strict JSON-safe CombatSessionRecord parsing, deterministic session IDs, live
  Battlefield reconstruction, and named engagement/session errors.
- [x] 7.4 Implement hostile `engage` preflight for local living hostility and no active session, persist
  participant dbrefs/initial overwhelm classification, register skip safety, and prompt without running
  any action before player input.
- [x] 7.5 Implement side-effect-free, non-random ActionResolver preflight for ownership/resource/target/
  capability/effect-handler/time metadata; reject before initiative without NPC action or upkeep.
- [x] 7.6 Implement one-use preflight-valid player action plus monster-policy provider; drive exactly one
  ordinary `run_round()`, distinguish mid-round invalidation from preflight rejection, and persist state.
- [x] 7.7 Refactor CmdCast active-combat behavior to delegate to combat-session orchestration, without
  command-default time or duplicate direct resolution; preserve out-of-combat behavior unchanged.
- [x] 7.8 After the first player request passes preflight, integrate resolver-backed overwhelm outcome;
  use that request once then deterministic lowest-HP basic attacks for compressed follow-up turns, while
  preserving per-round input pauses for undecided encounters.
- [x] 7.9 Settle accumulated rounds once on victory, defeat, flee, forfeit, exam terminal outcome, invalid
  recovery, or cap; clear action context/session/skip-safety state idempotently.
- [x] 7.10 Block every exit/location move during an active session; persist sessions across disconnect,
  resume on reconnect, and implement `combat forfeit` cleanup for ordinary and examination modes.
- [x] 7.11 Restore valid sessions on startup and diagnostically terminate malformed, moved, missing, dead,
  or duplicated participant references without blocking the player.
- [x] 7.12 Test preflight rejection versus mid-round invalidation, initiative before/after player, one
  request per ordinary round, no overwhelm action before input, compressed follow-up policy, three-round
  18-second settlement, flee, forfeit, blocked movement, disconnect/reconnect, reload, and deleted enemy.
- [x] 7.13 Run all existing action, combat, overwhelm, behavior, disengage, clock, skip, and CmdCast tests
  unchanged except deliberate requirement updates for the second innate skill.

## 8. Triggerable nonlethal guild examinations

- [x] 8.1 Implement strict GuildExamRecord storage with deterministic attempt IDs, target rank, requester
  audit metadata, opponent/session IDs, state, and terminal reason.
- [x] 8.2 Implement sole-entry `start_guild_exam()` with co-location/component, registration, exact-next-
  rank, true-merit threshold, no-active-session, and duplicate-active-attempt validation.
- [x] 8.3 Spawn the configured adult temporary NPC opponent at the exam spawn point with exact validated
  true traits and known skills, then start a guild-exam CombatSessionRecord.
- [x] 8.4 Extend BattlefieldActionContext damage projection with explicit nonlethal knockout handling
  before EventLog/planners, flooring HP at 1 while retaining ordinary ActionResolver, initiative,
  modifiers, costs, and upkeep.
- [x] 8.5 Suppress ordinary target_defeated, combat-kill XP, loot, DEFEAT progress, and protected-entity
  failure for exam knockout without suppressing exam outcome events.
- [x] 8.6 Implement idempotent PASS/FAIL settlement: PASS atomically promotes one rank; knockout/flee/
  forfeit/invalid recovery/cap FAIL leaves rank and cumulative merit; both delete opponent and close
  session.
- [x] 8.7 Test every rank threshold/profile, below-threshold and skipped-rank rejection, disguised candidate
  invariance, command versus npc_intent authority equality, duplicate active exam, pass/fail/retry, no
  ordinary rewards, and replayed settlement.
- [x] 8.8 Fault-inject opponent spawn, session creation, rank write, exam write, and cleanup to prove no
  orphan opponent/session or double promotion.

## 9. Atomic shop trades

- [x] 9.1 Implement strict merchant-stock parsing and open-status calculation for same-day and overnight
  intervals without a persisted open boolean.
- [x] 9.2 Implement `buy()` preflight and one transaction for exact integer wallet debit, item additions,
  ACQUIRE quest replacement, and finite stock decrement.
- [x] 9.3 Implement `sell()` preflight and one transaction for complete item removals, exact integer wallet
  credit, and stock increment without cap overflow or ACQUIRE reversal.
- [x] 9.4 Restore every Attribute/quest cache after injected wallet, inventory, quest-log, or stock failure.
- [x] 9.5 Test positive integer quantities, exact funds, insufficient funds, missing/full stock, unknown or
  unsellable items, closed shop, multi-quantity repeated keys, no partial/clamped trade, and no floats.

## 10. Shop-hour and caravan clock sources

- [x] 10.1 Implement `shop_hours` boundary arithmetic and JSON-safe open/close ScheduledEvents for every
  crossed same-day or overnight transition, with no per-second iteration.
- [x] 10.2 Implement `caravan_arrivals` daily boundary arithmetic, per-merchant/day catch-up, cap-limited
  stock addition, last-restock day, and exact JSON-safe events.
- [x] 10.3 Isolate malformed merchant data without mutation and continue other hosts with diagnostics.
- [x] 10.4 Register both event sources idempotently in `sync_guild_economy()` after quest synchronization.
- [x] 10.5 Test no/crossed/multiple boundaries, multi-day large skips, one restock per day, cap reporting,
  repeated settlement, malformed isolation, and caravan-before-shop ordering.
- [x] 10.6 Run all existing clock and settlement-order tests and prove quest deadlines/NPC schedules retain
  their documented positions.

## 11. Player commands and startup composition

- [x] 11.1 Add guild register/list/accept/log/abandon/turn-in commands with local service resolution,
  named-error mapping, and Traditional Chinese output.
- [x] 11.2 Add engage, combat-forfeit, and guild-exam commands that invoke only combat-session/exam APIs
  and report EventLogs/session prompts without direct state writes.
- [x] 11.3 Add shop stock/list, buy, and sell commands invoking only deterministic economy APIs.
- [x] 11.4 Register all commands in CharacterCmdSet and test usage parsing, aliases, absent/ambiguous/
  remote services, domain errors, and successful output.
- [x] 11.5 Implement `sync_guild_economy()` catalog validation, service-content sync, event-source
  registration, and combat/exam restoration; call it after quest/map/lore startup in dependency order.
- [x] 11.6 Test fresh/repeated server startup and source-scan that guild/economy/components/commands import
  no `world.ai`, LLM client, or network service.

## 12. Offline Phase-4 milestone

- [x] 12.1 Add a command-level integration fixture with deterministic hand-written Altoria guild, hunt
  monster, merchant stock, compact fixed reward/merit thresholds, and fixed dice; do not bypass
  production APIs.
- [x] 12.2 With every LLM profile unavailable, walk the player through guild registration, board listing,
  quest acceptance, hostile engagement, at least one selected combat round, automatic completion,
  return, turn-in, and exact reward assertion.
- [x] 12.3 Continue the same path through purchase, closed/open boundary, caravan restock, sufficient
  cumulative merit, examination trigger, nonlethal examiner defeat, and F-to-E promotion.
- [x] 12.4 Assert the integration path emits no network call, uses true combat stats despite registration
  disguise, advances world time, and leaves no active session/opponent/orphan transaction.
- [x] 12.5 Add a future-intent contract test proving `requested_by="npc_intent"` reaches the same exam
  validation but no Phase-4 module parses dialogue or imports AI.

## 13. Authoritative design and contract consistency

- [x] 13.1 Amend the engine design's entity/economy, combat, clock, guild Phase-4, and testing sections
  with the accepted registration, rewards, player session, exam, finite stock, and restock contracts.
- [x] 13.2 Add `request_guild_exam` with `target_rank` to §7.4's future NPC intent whitelist and document
  deterministic validation, no elevated intent authority, and illegal-intent speech preservation.
- [x] 13.3 Reconcile every guild-economy artifact with quest-runtime boundaries and future changes 19/20;
  remove placeholders, contradictory ownership, and claims that AI applies state.
- [x] 13.4 Map every delta-spec scenario to one or more deterministic tests before marking implementation
  complete.

## 14. Verification

- [x] 14.1 Run focused guild, quest, inventory, combat-session, exam, economy, clock, map, component,
  command, and startup tests while implementing each task group.
- [x] 14.2 Run `uv run --locked evennia test --settings settings.py .`.
- [x] 14.3 Run `uv run --locked python -m compileall -q world typeclasses commands server`.
- [x] 14.4 Run `openspec validate guild-economy --strict` and `openspec validate --all --strict`.
- [x] 14.5 Run `git diff --check`, review all changed files against this proposal, and confirm no migration,
  backward-compatibility layer, AI state writer, floating-point money, or live-object persisted record.
