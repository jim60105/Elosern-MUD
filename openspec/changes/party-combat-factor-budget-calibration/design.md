# Design: Finite combined damage factor budget evidence

## Context

See proposal.md for motivation and `../combat-ratio-mitigation/batch.md` for complete coverage, order and conflicts. Prior real equipment calibration already supplies selected gear values and committed-reload evidence; shared scalars are the independent factor boundary.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns finite combined damage factor budget evidence, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Create a fixed finite matrix at the existing human-combat calibration boundary, using synthetic independent arithmetic plus real equipped resolver actors from the preceding equipment-growth evidence. No encounter loop or balance tuning is owned here. Run each listed case with actor sides exchanged (player attacker/enemy attacker), for 24 base cases total: (1) physical basic coefficient1/base roll/weapon1, (2) physical weapon1.5, (3) magic weapon1.5 neutral control, (4) explicit bypass at defense60, (5) matched conditional multiplier2, (6) max-HP rider0.1 on HP100, (7) authored scale0.5 with the rider, (8) coefficient2 × critical2 × weapon1.5 × two existing strikes, (9) Defend0.35 after scale, (10) Dodge threshold25 changes a landing margin to miss, (11) raw100 with insufficient margin still misses, (12) combined conditional2/coefficient2/weapon1.5/critical2/rider/scale2/two strikes. Use attack60, K40 and defense20 unless the case explicitly changes it, with fixed raw roll80 or100 for critical controls. Independently assert the computed floor/round/scale order; estimator and settlement must agree for every applicable case.

Add six invariant controls once: unchecked direct damage receives no Dodge roll; per-recipient AREA Dodge differs by declaration; upkeep damage ignores Defend; explicit bypass ignores Defend; existing divert/nonlethal projection follows final direct amount; literal base traits, proficiency access, practice affinity and strike count remain unchanged. Thus the bounded set is 30 base/control cases, not arbitrary combinations. Report the complete coefficient×critical×weapon×strike budget for the two compound cases and the initial/selected authored weapon factors from the preceding slice. Diagnose shared arithmetic/consumer mismatches without inventing registry damage constants or tuning encounters. All probes use simulation markers and no reward/growth drift. Full encounter outcome selection belongs to party-combat-encounter-calibration.


## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 5.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
