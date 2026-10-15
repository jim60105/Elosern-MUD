# Design: Combined player/enemy encounter and skill-budget calibration

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. Existing human calibration records actual seeds0-3/200-round probes separately from historical projected tables and forbids unsupported universal encounter claims.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns combined player/enemy encounter and skill-budget calibration, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Use exactly eight existing human-only encounter cells, grounded in the prior real calibration report: F early ordinary monster with F creation kit; E restricted senior versus E ordinary monster; three-member D restricted party versus D ordinary monster; C restricted senior versus C ordinary monster with its real flee policy; B restricted senior versus B ordinary monster; B restricted senior versus existing high-lower calibration-only probe; B restricted senior versus existing high-upper calibration-only probe; S restricted senior versus that same high-upper probe. Keep the high probes unshipped. Each cell runs seeds0-3, with full pools, actual registered gear/restrictions and a 200-round bound, so a pass is exactly32 encounter trials. No new species, elf/beastfolk target or calamity cell is added. Use the prior factor-budget evidence rather than repeat the full matrix here.

Every allied actor receives an explicit bounded policy script that submits real selected commands through the draft facade; no autonomous allied provider fallback is allowed. Default choice is a legal basic attack; the D party alternates one supporter-owned skill and own-inventory item with its other explicit attacks, and uses Defend/Dodge/Taunt on fixed rounds2/3/4 when eligible, retaining the existing enemy choice freedom. Scripts record rejected commands and do not silently replace invalid actions. Simulation markers prevent growth/unlocks/ordinary reward drift. Preserve enemy defensive/evasive skills.

The eligible tuning surface is finite: K, defend_reduction, dodge_threshold_bonus; the real weapon multipliers and ceilings selected in equipment-growth-runtime-calibration; and at most the two existing physical skill definitions used as the conditional and multi-strike probe cases in factor-budget evidence. Choose those two registry keys from the actual preceding evidence before a tuning run and record them, never an unnamed new attack. No global skill weakening, stat/proficiency growth or unrelated magic/heal/armor redesign. Compare the32 baseline trials with the same32 selected-value trials once; values may be retained if evidence supports them. Any implicated further probe reuses this finite set, never drops a required cell. Record baseline/selected values, outcomes, rejects, elapsed rounds, medians, restrictions, backend/revision and diagnoses. A failed real-kit match blocks acceptance. Historical projected evidence and sampled higher-tier limitations remain qualified; no universal balance guarantee is made.


## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
