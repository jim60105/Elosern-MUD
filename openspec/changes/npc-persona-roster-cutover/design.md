## Context

See proposal.md for motivation. Facts the plan relies on: hosts carry a component `service_id` mapped to a place with a mandatory `host_profile_key`; exam records (`actor.db.guild_exams`) carry `opponent_id` and `target_rank`, and ranks carry `examiner_profile_key`; companions carry `db.creation_preset_key` and, when bound, `db.party_member` naming the owner; scene occupants carry `db.npc_tier_key` and appear in active quest records' `objective_target_ids` for a definition whose durable payload declares the stage occupants; the durable generated-quest store holds JSON payloads whose pre-change occupants have optional `background`/three-field `persona`; the offline bundle selector is pure; `world/rules/surfaces.py` restores attribute caches; boot steps run sequentially before the server serves sessions.

## Goals / Non-Goals

**Goals:** every existing NPC-family instance and durable occupant ends with a complete new card and metadata in one atomic step; gameplay state untouched; idempotent; edits never overwritten; restore succeeds afterwards.

**Non-Goals:** rewriting conversation transcripts or memory; deleting/respawning NPCs; `Monster` instances; player characters or presets; any reusable migration framework; a runtime old-payload decoder.

## Decisions

### D1. Plan, then one apply transaction

`plan_cutover()` builds an in-memory list of `(target, new_card, provenance, version)` and `(payload_identity, rewritten_payload)` with no writes, validating every card through the contract and every rewritten payload through the strict codec from `npc-persona-generated-quest-cards`. Any plan failure raises `NpcPersonaCutoverError` naming the source (`kind:key`) or entity (`#dbref`) before a single write. `apply_cutover(plan)` snapshots `persona`/`npc_persona_meta` attribute caches for every target and the store's payload list, then in one `transaction.atomic()` writes each card and meta (`generation = NPC_PERSONA_CONTENT_GENERATION`; `persona_version = previous + 1` when meta exists, else `1`; provenance per D2), replaces the store payload list once, and sets the persistent marker (`ServerConfig` `npc_persona_cutover_generation`). On exception: rollback, restore every snapshot, emit `npc_persona_cutover_failed` with `exc=`, re-raise. Alternative rejected: batching per NPC (explicitly forbidden partial completion).

### D2. Provenance classification order

1. Service host (has a service component whose `service_id` is in the roster) → `profile` provenance, the place's profile card.
2. Exam opponent (its id appears as `opponent_id` in any stored exam record) → the record's rank examiner profile.
3. Starting companion (`LLMNPC` with `creation_preset_key` matching a declaration partner) → `companion` provenance; owner = `party_member` when bound, else the unique player character whose preset declares that partner and holds an affinity record toward the NPC; owner line recomputed exactly as the companion builder composes it. No unique owner → treated as rule 6 with a `warn` event naming the NPC (never a fabricated owner).
4. Scene occupant (id in an active quest record's `objective_target_ids`) → the replacement card computed for that durable occupant (rule 5), `generated_quest` provenance — so a materialized occupant and its declaration share one baseline.
5. Durable payload occupant: if the payload's definition was compiled from a shipped template (same quest name, stage index, occupant position, display name, and title as a `QUEST_TEMPLATE_POOL` occupant) → the template card; else the offline bundle for the occupant's tier with seed `"{definition_key}:{issuer_key}:{stage}:{position}"`. The rewritten occupant drops `background` and the old `persona` and stores the new card.
6. Everything else in the NPC family (imported, dynamic, unresolvable) → `offline_pool_for(db.npc_tier_key, race)` with seed `str(npc.id)`, `offline_bundle` provenance.

Every rule writes a complete new card; no rule copies old prose.

### D3. Exclusivity

`npc_persona.py` gains `_WRITES_SUSPENDED` and a `suspended_writes()` context manager used only by the cutover. While set, `initialize_npc_persona` and `update_npc_persona` raise `NpcPersonaWritesSuspended` (import and spawn fail their all-or-nothing transactions; an editor request cannot occur because no session is served during `at_server_start`, and any in-process caller gets the exception through its normal failure path). Entering the context while already set raises `NpcPersonaCutoverError("cutover already running")`; there is no wait or retry. The cutover's own writes go through a private writer that bypasses the guard. Because the step runs during `at_server_start`, no session is served concurrently; the guard covers re-entrancy and any in-process caller.

### D4. Boot placement and idempotence

Step `npc_persona_cutover` is inserted immediately before `sync_quest_runtime` (after `sync_service_interiors`, so instance rooms exist, and after `npc_persona_roster_validation`). A run with nothing to plan emits `npc_persona_cutover_skipped` and writes nothing. Marked instances are never re-planned, so player edits — including optional leaves cleared to empty strings — survive every restart. `sync_guild_economy` then initializes only newly created hosts (producer rule), and restore decodes only valid payloads.

### D5. What is preserved

Only `db.persona`, `db.npc_persona_meta`, and the occupant characterization fields inside stored payloads change. Object ids, keys, titles, location, components, traits, inventory, party bindings, quest records and bindings, schedules, affinity, chat memory, dialogue sessions, and every other payload field are untouched; tests compare full attribute snapshots before and after.

## Risks / Trade-offs

- [A large retained world makes one transaction big] → pre-release, single-player scale; acceptable and required by the design.
- [A misclassified instance gets a bundle voice instead of its profile] → classification order is explicit and tested per rule; the `warn` event names any companion without a resolvable owner.
- [A failed cutover blocks boot] → intended fail-closed behavior; the event names the source/entity to fix; the prior state is intact.
