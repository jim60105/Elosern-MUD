# Design: One command card for actor switching and skill draft progress

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. Current frame-resolvers keep one CombatMenu model; active card/stage/cross-side proposals own the future presentation and warning contracts.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns one command card for actor switching and skill draft progress, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Use one `combat.actor` frame within the mounted centered card and retain its 264px*S width/anchor/formation clearance. Actor rows use server allied order, display name/token, commandable reason and confirmed/needs-selection text. A compact current-actor/progress line and a Change member/back path occupy existing card rows/detail slots; do not resize/reposition the shell or alter stage geometry. Choosing an actor queries combat.actor_choices with session/revision/actor, then opens the same root/category/group/scale/target flow from canonical choices; do not optimistically show the previous actor catalog. Commanded actor ID, focused target ID and account puppet ID are separate state. SELF lighting/confirmation binds commanded actor including a companion, never the controlled portrait. Actor switch drops unconfirmed local skill/scale/target selection and cancels local warnings without deleting confirmed server entries. Revisiting an entry selects its actor and permits replacement. After a nonfinal accepted selection, choose the first required actor still needing a command; keep all actors reachable, including already selected. The last confirmation dispatches the same combat.command and server determines resolution, with no whole-party submit screen. Preserve actor-bound cross-side warnings and all target checks/digits/pointer paths. During playback keep existing lock and never replay pending intent. On invalidation show member reasons and retain valid progress; reconnect reconstructs server-confirmed entries and starts at first missing actor, never auto-fills or resubmits. This change owns actor and skill UI; item/tactical rows become live through webclient-party-items-tactics, which is required for assembled acceptance. Add keyboard/pointer and screen-reader status coverage without introducing visual redesign.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 7 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
