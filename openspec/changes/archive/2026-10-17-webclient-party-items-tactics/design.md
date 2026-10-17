# Design: Complete companion item use and tactical menus in the shared card

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. Items and Defend remain not_implemented in the canonical keyboard contract, while the independent bag supports inventory.use and free equipment toggle.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns complete companion item use and tactical menus in the shared card, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Feed Items from selected actor's server `items`, never global commander inventory or a shared party bag. Reuse menu/detail and existing target controls for none/self/single item targeting. For items whose registry effects reach groups, server candidates and scope own that reach; client never manufactures shorthands or magnitudes. Display current actor quantity, effect summary and disabled reason; confirm one member choice and allow replacement until full draft. Keep existing item review confirmation where present and actor-bound cross-side warnings for hostile/beneficial item use. Defend and Dodge select a zero-MP/SP round action, Taunt reuses the stage single-target selector with enemy candidates. No placeholder rows remain. Root retains Attack, Skills, Items, Bag, Defend and adds Dodge/Taunt beside Defend; Retreat and Surrender are party-level entries wired by webclient-party-exit-confirmation. Bag inspection remains free, but any active-combat use from the drawer goes through selected actor combat.command and same target/review flow; actorless inventory.use rejects. Existing equipment toggles stay commander-scoped and free; the drawer never becomes companion equipment/transfer management. Equipment results invalidate and refresh affected previews/drafts. No optimistic consumption or tactical effect before a committed round. Maintain centered-card geometry, existing warning/focus behavior and keyboard/pointer parity.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 7 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
