# Design: Playable text-client party commands and explicit exit parity

## Context

See proposal.md for motivation and `../combat-ratio-mitigation/batch.md` for complete coverage, order and conflicts. Existing text combat actions/cast/use/forfeit are commander-bound; session target tokens and both command-doc paths already exist.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns playable text-client party commands and explicit exit parity, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Use stable session-local `aN` actor tokens independently from `aN/eN` target tokens; retain their persisted participant binding. Add `combat command <actor-token> skill <skill_key>[@<scale>][=<targets>]`, `combat command <actor-token> item <item_key>[=<target-token>]` and `combat command <actor-token> defend|dodge|taunt[=<enemy-token>]`. `combat actions [actor-token]` shows that actor's skill categories/scales/costs, usable own items, tactics/targets/disabled reasons and full draft progress; default actor is commander. Selecting via combat command is the explicit member confirmation, replaces an entry and auto-runs the final valid selection without a separate submit command. Existing `cast` and `use` inside combat route the commander actor through the same draft facade, keeping their own target syntax/scale semantics; they cannot resolve a partial party round. `cast flee`, retreat and existing surrender/forfeit aliases request the same party-scoped prompt. Add `combat retreat` and retain `combat forfeit`; explicit execution syntax is `<command> confirm <token>`; any other continuation cancels with no draft/time mutation. Prompt shows party scope, consequences, session and round, and new state invalidates its token. No `confirmed=True` bypass or direct personal flee. Display pending counts, per-actor rejection, resolved logs, terminal aftermath and next required choices through existing message rendering. No companion equipment-management or item-transfer commands.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 7 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
