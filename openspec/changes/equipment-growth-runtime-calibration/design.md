# Design: Authored shipped weapon values and committed-reload growth evidence

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. Equipment_effects.yaml contains real military and other weapon/armor entries with flat adjustments but no selected weapon factor; existing runtime calibration evidence uses real kit.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns authored shipped weapon values and committed-reload growth evidence, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Author an explicit initial and selected multiplier for every registered weapon plus per-rarity ceilings in equipment_effects.yaml, with neutral declarations justified for weapons that receive no physical bonus. At least representative real physical weapon upgrades must be nonneutral and demonstrate growth; runtime never computes rarity scaling. Inspect the actual complete registry rather than assume only military swords exist. Use real Evennia construction, ordinary grant/equip rules, committed persistence, cache eviction and fresh reload to compare unarmed/upgrade/armor states. Record engine revision, backend, registry item keys, true stats, chosen factor/defense, fixed roll, baseline and selected output. Prove independent K=40 cases (60→40 at defense20, Defend→26, physical factor1.5→60, magic unaffected). Cover armor monotonicity, occupied nonweapon main hand, offhand fallback/dual wield, below-old-threshold positive marginal growth for an adequate upgrade, magic/healing controls and base-trait/proficiency/affinity invariance. Full encounter balancing and any evidence-supported coefficient changes belong to party-combat-encounter-calibration; record these as measurements, never assert K40 is balanced. Amend the historical no-tuning scenario narrowly to permit approved evidence-driven equipment authoring, leaving historical evidence qualified.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
