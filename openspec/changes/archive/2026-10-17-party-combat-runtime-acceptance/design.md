# Design: Real assembled browser/text party-combat acceptance

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. The managed browser harness and exact browser/evennia shard manifests already own isolated deterministic runtime acceptance and canonical-store polling.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns real assembled browser/text party-combat acceptance, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Add small deterministic actual-runtime acceptance methods to the existing managed localhost harness, not a replacement mock UI. One journey commands multiple actors using a companion-owned skill and item in successive rounds, replaces an earlier confirmed choice before final completion, observes automatic last-confirm resolution and a fresh next draft, disconnects/reconnects an unfinished draft, and proves no missing actions were filled or replayed. Isolated encounters exercise retreat/surrender cancel and committed outcomes, carried downed allies, failed-retreat enemy/upkeep behavior and ordinary hostile/exam consequences. Add an exercised text command path for actor choices and explicit token confirmations. Assert server canonical snapshots, inventory/resource owners, logs and accumulated time, plus same centered card and actor-versus-target SELF behavior. Keep 1451x790 and 2560x1440 focused geometry assertions inherited from the active UI contracts. Register each added/renamed browser method and nonbrowser module exactly once in shard manifests and use canonical traceability IDs. Save concise runtime evidence in existing development docs. This is the batch acceptance owner: no assembled release with missing companion items/tactics, uncalibrated real weapon values, no text parity or a client unable to complete a party round. Full managed browser execution and tools.spec_traceability verify --evidence stay CI-owned.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
