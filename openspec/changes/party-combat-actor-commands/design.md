# Design: Commander authorization and complete actor-scoped skill/item requests

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. `build_combat_view` currently builds puppet-bound skills and `_round_provider` supplies policy actions for every nonplayer entity; item use already has preflight and rollback journals.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns commander authorization and complete actor-scoped skill/item requests, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Separate authenticated commander from command actor in the session API. Authorize actor ID by current session player_ids, bound party ownership, same recorded room, present/alive/nonfled/nonknocked-out and existing ability-to-act rules. Do not puppet, possess or invoke possession lifecycle. Build one immutable actor choice read model through the existing shared skill preview and item preflight. Retain skill TargetSpec, faction, scale, time and context rules, disabled reasons and deterministic order. SELF binds actor; costs, inventory and mirror consumption belong to actor. Preserve per-effect item effectiveness and every existing usable scope, including no-effective-effect rejection. Object references are resolved from authorized identities at use, never trusted from the client. Free equipment operations remain free; change 4 marks affected draft choices for revalidation.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
