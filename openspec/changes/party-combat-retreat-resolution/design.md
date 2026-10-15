# Design: All-party retreat success/failure and exactly-once time

## Context

See proposal.md for motivation and `../combat-ratio-mitigation/batch.md` for complete coverage, order and conflicts. Enemy individual flee uses the adjusted-agility contest and Battlefield.fled mechanism; allied party exit must not modify that AI ownership.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns all-party retreat success/failure and exactly-once time, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Consume the confirmed retreat at the same serialized revision boundary as a normal round. Discard pending personal commands only on accepted confirmation. Before ordinary actions, compute minimum adjusted agility among present allied members able to act and maximum among living present nonfled pursuers; reuse the existing adjusted-agility query and defender_constant source (51), ignoring accuracy and Dodge. With pursuers use one d100 roll, with none escape without a roll, with no acting ally take ordinary defeat. Success marks the entire present party escaped, including carried knocked-out companions, and settles one added elapsed round without enemy action or ordinary combat upkeep; terminal recovery remains existing policy and the operation adds no heal/revive/relocation. Failure gives all allies zero opportunities, runs eligible enemies in ordinary initiative order and ordinary upkeep once; no draft attack or tactical declaration activates. Clear selections/declarations, increment revision once and begin an empty draft after a nonterminal failure. Share the existing atomic unit and journals with settlement; enemy individual flee retains the ordinary resolver and AI policy.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 7 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
