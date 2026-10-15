# Design: Shared ratio damage and independent arithmetic evidence

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. `scalars.strike_amount` currently subtracts defense and shares its expression with estimation; combat.yaml currently has hit/damage/heal/initiative/round constants.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns shared ratio damage and independent arithmetic evidence, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Keep `strike_amount` as the shared pure scalar boundary used by settlement and estimation. Load finite positive `damage.mitigation_k`, initially 40, at the existing combat rulebook load boundary; reject bool/non-number/nonfinite/zero/negative values. Use `round(attack * roll_multiplier * coefficient * matched_multiplier)` then `int(max(attack_part * K / (K + max(0, defense)) + rider, floor))`, then existing half-up `scaled_magnitude` and floor. Explicit bypass supplies zero defense. Preserve conditional policy matching, rider, divert, nonlethal projection and cost ordering. Do not duplicate arithmetic in AI. Weapon factor and Defend are later consumers of this ordering; they are deliberately absent here. Amend the engine design §6.3 by reference to approved 2026-10-15 design.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 5.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
