# Design: Initiative-priority Taunt and legal enemy decision constraints

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. The existing legal-candidates contract applies seal/displacement restrictions before utility; active v6 owns the exhaustive typed hostility classifier.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns initiative-priority taunt and legal enemy decision constraints, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Reuse the typed effect hostility classifier owned by active panel-v6, including non-damage hostile effects; do not infer hostility from skill names or physical/magic school. A Taunt request picks one living eligible enemy and no success roll. Rank accepted taunts with the already-computed initiative sequence. Store one winner per enemy for this round; no runner-up promotion. Determine ordinary legal target candidates first, including presence/range/faction, seal and displacement restrictions; when the winner is legal for this single-target hostile action restrict candidates to that identity. A seal or range rule that excludes the taunter stays authoritative; Taunt grants no exception. Apply the same constrained candidates to fallback/profile and utility/rollout estimation plus final execution revalidation, never silently rewrite a resolved target. AREA, self/allied benefits and flee remain legal ordinary alternatives. Recheck winner presence/eligibility before each later enemy decision; if down/dead/absent/fled, remove restriction permanently for that round. Losing taunts remain spent actions. Enemies gain no basic Taunt.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 7 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
