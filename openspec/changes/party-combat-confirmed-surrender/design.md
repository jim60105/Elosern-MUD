# Design: Revision-bound exit confirmation and surrender settlement

## Context

See proposal.md for motivation and `../combat-ratio-mitigation/batch.md` for complete coverage, order and conflicts. `combat forfeit` currently calls forfeit immediately; settled markers/defeat aftermath and guild-exam restoration already belong to session settlement.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns revision-bound exit confirmation and surrender settlement, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Introduce deterministic `request_party_exit(commander, session_id, round_revision, operation)` with operation retreat|surrender, and `confirm_party_exit(..., confirmation_token)`. The request returns party scope/consequences and a bounded server-issued token bound to commander, session, round and operation; it runs no action and does not alter draft entries. Use the existing confirmation mechanism where possible; tokens are validated at the rules boundary, not a truthy confirmed flag. Cancel is discarding the pending prompt; no mutation/time. Confirm admission serializes on the same session/revision as normal rounds and records an operation receipt, so round-vs-exit and exit-vs-exit races admit only one. Surrender clears the draft and calls existing hostile defeat or exam FAIL settlement with zero extra rounds, no roll or enemy attacks. Preserve aftermath, restoration policy and already accumulated time exactly once, including restart and cache rollback. All public `combat forfeit`, aliases and allied innate-flee paths must refuse mutation without the same confirmation; expose a text prompt on existing routes in this slice, before the expanded text syntax in party-combat-text-commands. Enemy disengage remains untouched. Retreat confirmation dispatch becomes live in change 10; no placeholder gameplay handler is shipped.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
