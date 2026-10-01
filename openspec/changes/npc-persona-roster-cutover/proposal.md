## Why

Every content, producer, and consumer change gives new NPCs complete cards, but existing persisted NPCs — service hosts, built companions carrying copied preset personas, exam opponents, materialized scene occupants, imported NPCs — and the durable generated-quest payloads still hold provisional or no characterization. The user explicitly authorized a one-time full replacement of that provisional data (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §6.2, §11.1 case 4, §13): one bounded, deterministic, exclusive boot operation that rewrites every unmarked NPC-family instance and every pre-change durable occupant characterization in a single transaction, preserves all gameplay state, is idempotent, and never overwrites a player's later edits. It must run after the roster is proven complete and before generated-quest restore reads the old payloads.

## What Changes

- Add `world/rules/npc_persona_cutover.py`: a plan phase (no writes) that enumerates every NPC-family instance without the current content-generation marker and every stored generated-quest payload whose occupant characterization is not a valid card, classifies each by known provenance, and computes and validates the complete replacement card — host profile by service id; examiner profile through the exam record naming the opponent; companion profile plus an owner line recomputed from the party binding or the unique declaring owner; scene occupant from its durable declaration's replacement; shipped-template occupants from the template card; everything else (imported, dynamic, unresolvable) from an offline bundle chosen by stable identity. Old prose is never carried forward.
- An apply phase that writes all instance cards, metadata (generation, version, provenance), rewritten payloads, and a persistent cutover marker in one `transaction.atomic()`; on any failure it rolls back, restores every touched attribute cache, logs the failing source/entity, and re-raises so boot aborts instead of admitting players to a partly rewritten world.
- Exclusivity: while the cutover runs, every NPC persona writer (initializer, editor update, import, spawn) is suspended and rejects with a stable reason; a re-entrant or concurrent attempt is refused. No network-style retry, no SQLite-lock reliance.
- Boot step `npc_persona_cutover` (fail-loud) after `npc_persona_roster_validation`/world syncs that create rooms and before `sync_quest_runtime`, so restore reads only rewritten payloads; reruns skip marked instances and valid payloads, so a routine restart is a no-op and edits (including deliberately cleared optional fields) survive.
- Commit-bound events `npc_persona_cutover_applied` / `npc_persona_cutover_skipped` (counts by provenance kind) and `npc_persona_cutover_failed` (source/entity, exception); no prose.

## Capabilities

### New Capabilities

- `npc-persona-cutover`: the one-time, exclusive, transactional replacement of provisional NPC personas and durable generated-quest characterizations, with idempotent reruns.

### Modified Capabilities

None (writer suspension is specified as part of the new capability; the foundation's writer contract is unchanged for normal operation).

## Impact

- Code: `world/rules/npc_persona_cutover.py` (new), `world/rules/npc_persona.py` (writer suspension guard), `server/conf/at_server_startstop.py` (boot step and order), `world/quests/generated_quest_store.py` read/write use only (no format change).
- Tests: `world/rules/tests/test_npc_persona_cutover.py` (rules shard registration), startup-order guard tests in `server/conf/tests/`.
- Observability catalog rows for the three events.
- Data: this is the design's single authorized data replacement; no general migration framework, no runtime legacy decoder, no reset-on-upgrade policy.

## Batch:

depends-on: npc-persona-roster-validation
depends-on: npc-persona-offline-bundles
depends-on: npc-persona-generated-quest-cards
depends-on: npc-persona-companion-profiles
depends-on: npc-persona-host-examiner-producers
depends-on: npc-persona-import-cards

Code-conflict notes: last editor of `world/rules/npc_persona.py` (adds the suspension guard beside the dialogue and editor read helpers; distinct functions) and of `server/conf/at_server_startstop.py` (after roster validation). Must land after `npc-persona-generated-quest-cards` (whose strict decoder makes retained pre-change payloads fail restore until this change rewrites them) — apply these two close together. Independent of `npc-persona-editor-window`; the editor is gated per NPC on an initialized card, so editability of shipped NPCs completes exactly when this change runs.
