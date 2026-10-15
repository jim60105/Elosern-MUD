# Design: Exactly-once complete-draft ordinary rounds and rollback

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. The enclosing transaction in combat_session/rounds.py already spans resources/effects, session metadata and terminal settlement, with item journals and Evennia cache snapshots.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns exactly-once complete-draft ordinary rounds and rollback, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Use the existing single deterministic writer with an authoritative session/revision compare-and-consume inside `transaction.atomic`; serialize competing confirmations before re-reading durable state. Do not rely on a process-local used flag, preflight snapshot or browser in-flight lock for concurrency safety on SQLite. The final edit is persisted before entering round resolution so a failed round keeps the accepted complete draft recoverable. Re-read and preflight all commands within the serialized round transaction; invalid entries return reselection without AI/upkeep. Store a durable consumed-revision receipt tied to session and revision, including terminal completion, outside the soon-cleared active session as needed in the commander-owned session outcome record. Duplicate/stale requests return a safe prior-committed/stale result without executing effects. Supply each allied selected request once; enemy provider remains unchanged. Compute initiative once. Preserve capability gates and authored in-round order operations; command entry order has no priority. Normal final target invalidation consumes the opportunity with no retarget, costs or item consumption; valid miss retains ordinary costs. All effects, resources, mirrors, quest/practice/affinity changes, metadata, revision/draft consumption, clock and terminal aftermath belong to the outer transaction and existing cache journals. Extend restoration to drafts, tactical state and any new receipt. Keep ordinary six-second accounting once and post-commit notifications/events only.

Interactive allied action slots are capped at one selected command even when a positive actions_per_turn modifier grants more slots; the extra slot cannot repeat a skill/item, request a missing command or invoke allied AI. Zero-action locks, including chance gates, still suppress execution. Enemy and noninteractive combatants retain their existing multiple-slot count, liveness checks and fuse unchanged. The combat-resolution delta makes this explicit rather than altering the generic meaning of positive modifiers everywhere.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 7.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
