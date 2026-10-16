# Design: Round-start Defend and Dodge with shared estimator arithmetic

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. The shared scalar hit_margin and strike_amount are the estimator/settlement boundary; existing round loop computes initiative and applies execution gates/upkeep.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns round-start defend and dodge with shared estimator arithmetic, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Add validated `tactics.defend_reduction=0.35` in [0,1) and finite `tactics.dodge_threshold_bonus=25` >=0 at the existing rulebook load boundary. Accepted declarations consume one selected action and activate only after complete preflight and one initiative calculation, before ordinary actions. Hold effects in the round execution context, never long-duration buff storage. Defend applies `max(floor(scaled_amount * (1-reduction)), damage_floor)` after ordinary mitigation, riders and scale, before existing downstream divert/nonlethal projection. Explicit bypass and upkeep ticks skip it; low/zero defense does not. Dodge passes defender threshold adjustment into shared hit_margin; margin drives solid-hit band; natural-100 critical still requires a landed attack. No-check attacks get no roll; per-target AREA checks get individual adjustments. No initiative/flee bonus. AI reads the same round context and scalar pipeline. Clear declarations in round-finally and restore pre-round caches on technical failure; a recovered draft carries the choice, not an activated effect. Enemies receive no new basic tactics.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 7 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
