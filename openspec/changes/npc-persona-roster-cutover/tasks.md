Apply on branch `feat/npc-persona-roster-cutover` in worktree `.worktrees/npc-persona-roster-cutover`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file. All fixtures are synthetic; no live model.

## 1. Writer suspension

- [ ] 1.1 Add `suspended_writes()` and `NpcPersonaWritesSuspended` to `world/rules/npc_persona.py` per design D3 (no editor-adapter edit: the step runs during `at_server_start` before any session is served), and verify tests: initializer, update, an NPC import, and a scene spawn each reject while suspended; re-entry raises immediately.

## 2. Plan

- [ ] 2.1 Implement `plan_cutover()` with the raw-JSON payload rewrite of design D1a (frozen pre-change payload fixture captured with `git show` from the commit before `npc-persona-generated-quest-cards`; keys unchanged; strict-codec validation of the result) and the six classification rules of design D2 and full validation before any write; verify `world/rules/tests/test_npc_persona_cutover.py` per rule: host profile, exam opponent via record, bound companion re-derived from its partner preset with owner line and preset greeting in the offline-greeting field, unbound companion with unique declaring owner, companion without owner → bundle plus warn event, materialized occupant sharing its payload baseline, template-derived payload using the template card, non-template payload using the tier bundle seeded by `definition:issuer:stage:position`, imported beastfolk via race pool seeded by id; no old prose in any planned card; a plan failure names the source/entity and writes nothing.

## 3. Apply

- [ ] 3.1 Implement `apply_cutover()` per design D1 (single transaction, versions, marker, cache snapshots/restore, failure event, re-raise); verify an injected mid-apply failure leaves DB rows, attribute caches, and the store unchanged and names the entity; a successful run changes only persona, metadata, and occupant characterization (full attribute snapshot comparison of every NPC and the store per design D5); conversation memory and dialogue sessions untouched.
- [ ] 3.2 Verify idempotence: a second run writes nothing and emits `npc_persona_cutover_skipped`; after a run, clearing `social_connection` and editing `habit` survive a simulated restart (rerun + `sync_guild_economy` + `restore_generated_quests`); restore decodes rewritten payloads.

## 4. Boot step

- [ ] 4.1 Insert the fail-loud `npc_persona_cutover` step immediately before `sync_quest_runtime` in `at_server_start` and `STARTUP_STEP_ORDER` per design D4; verify the startup-order guard tests (expected order updated), a test that a cutover failure aborts before `sync_quest_runtime`, a test that the step returns a plain value (never a Deferred, design D3a), and a test that a pre-cutover template payload and a post-cutover recompiled template quest both register without conflict.

## 5. Gates

- [ ] 5.1 Add the three events to the observability catalog and run `uv run --locked python -m tools.observability_lint check` with the focused labels; `tools/observability_freeze.json` unchanged.
- [ ] 5.2 Register `world.rules.tests.test_npc_persona_cutover` in exactly one rules shard and verify `tests.test_evennia_test_optimization_contract`; sync the new `npc-persona-cutover` capability into `openspec/specs/` and annotate with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `tools.test_data_lint check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-roster-cutover --strict`.
- [ ] 5.3 Exercise the boot path once on a retained developer database copy (not the shared CI database): start the server, confirm `startup_step` events for roster validation and the cutover, `talk` to two shipped hosts with all LLM profiles disabled (authored greeting and profile misunderstanding reply), and restart to confirm `npc_persona_cutover_skipped`; record observations, stating clearly if no retained database was available.
