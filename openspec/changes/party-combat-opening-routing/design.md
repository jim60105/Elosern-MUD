# Design: Opening selections seed interactive party rounds without compression

## Context

See proposal.md for motivation and `../combat-ratio-mitigation/batch.md` for complete coverage, order and conflicts. `submit_opening_action` currently picks compression and first_actor; `combat_initiation` validates an unpersisted candidate battlefield and snapshots engagement caches.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns opening selections seed interactive party rounds without compression, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

All player-interactive sessions use complete drafts, including overwhelming and solo sessions; no selected interactive command is replaced by compressed basic attacks. `submit_opening_action` becomes the canonical opening seed path rather than a compatibility alias. Candidate battlefield validation, skill out-of-combat availability, explicit opening target conversion and session-creation rollback/cache cleanup remain. Persist engagement plus validated initiating actor entry in one atomic unit; missing companions cause no effects/time. Keep existing encounter-specific first_actor opening policy as explicit durable opening metadata, consumed once by the first complete round; ordinary subsequent rounds have no override. Remove interactive references to _overwhelm_provider/resolve_overwhelm and obsolete dispatcher policy, leaving independent noninteractive overwhelm mechanics untouched. Propagate pending-draft result through text and browser exploration casts. Update both command docs in this slice because opening cast behavior changes now.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 4.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
