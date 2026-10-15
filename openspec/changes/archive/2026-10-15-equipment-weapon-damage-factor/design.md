# Design: Validated weapon factor and physical consumers

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. Equipment effects are a closed loader with existing per-rarity flat/percent/gauge ceilings; equipment.py only reads per-entity stored slots.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns validated weapon factor and physical consumers, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Add optional finite numeric `weapon_damage_multiplier >= 1.0` only to weapon entries and a per-rarity `weapon_multiplier` ceiling column. This loader cutover authors a valid initial weapon_multiplier ceiling of 1.0 for every existing rarity budget, so the shipped rulebook loads immediately. Synthetic nonneutral test rulebooks explicitly author adequate ceiling cells. The later real calibration owns selected revised ceilings and actual weapon bonuses; runtime never infers them. The accessor returns the declared main-hand weapon factor, or off-hand only when main-hand is empty, else 1.0. Invalid storage never grants a bonus. A non-weapon in occupied main hand blocks fallback. Return this nonadditive factor separately from additive equipment adjustments through the existing accessor boundary. Extend `strike_amount` with factor 1.0 by default; apply it inside attack_part rounding for physical school only, independent of element. Multi-strike uses the same factor on each existing strike; no extra strikes. Expose the factor in the existing deterministic equipment prose. This change proves a live consumer with synthetic nonneutral gear; shipped values and actual growth evidence have an explicit owner in equipment-growth-runtime-calibration and block batch acceptance.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
