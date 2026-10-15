# Design: Party-scope browser retreat/surrender confirmation and cutover

## Context

See proposal.md for motivation and `../combat-ratio-mitigation/batch.md` for complete coverage, order and conflicts. The active warning proposal already uses QuestionCard with No initial focus and an inert background; party confirmation reuses that behavior.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns party-scope browser retreat/surrender confirmation and cutover, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Expose Retreat and Surrender from every member root and actor-selection frame, using one existing party-operation submenu if needed within the card; neither operation requires the selected member to be commandable. Request server prompt data before mutation. Reuse QuestionCard in choices with initial focus No, explicit whole-party scope and consequences (failed retreat consumes all allied turns; surrender has existing defeat/exam consequences), and the server-bound token/session/round. Yes dispatches combat.exit_confirm once; No, close and Escape discard only local prompt data and restore prior actor/menu/selection and server draft unchanged. Make dock/stage controls inert during the dialog, preserve existing cross-side warning ordering, cancel pending cast warning before opening an exit prompt. Invalidate stale tokens on session/round/mode/epoch replacement, disconnect or playback; unrelated same-round resync retains safe prompt state only when token still valid. Apply canonical failure/new-round and terminal snapshots; no invented relocation/heal. Migrate every retired combat.flee/forfeit producer and allied skill-list route to these operations, with no compatibility transport. Confirmed surrender and retreat share server receipt semantics; never retry a stored Yes after reconnect.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 5.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
