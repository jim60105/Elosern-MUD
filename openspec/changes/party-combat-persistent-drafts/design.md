# Design: Persistent editable party draft and authoritative completeness

## Context

See proposal.md for motivation and `../combat-ratio-mitigation/batch.md` for complete coverage, order and conflicts. The persistent session record stores identity dbrefs rather than live objects, and startup restores sessions before wilderness reconciliation.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns persistent editable party draft and authoritative completeness, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Extend the JSON-safe session record with `round_revision` (monotonic per completed/consumed round), `draft_version` (monotonic per accepted edit/revalidation), and one draft map keyed by actor ID. Entries store closed kind plus canonical payload data (skill key/scale/target IDs or shorthand; item key/optional target ID; tactical key/optional enemy ID), never entities or live requests. Expose `confirm_actor_command(commander, session_id, round_revision, draft_version, actor_id, command)` and a side-effect-free complete-draft preflight shared with change 5. Save edits transactionally under the deterministic session writer; stale edit versions reject with canonical progress. Every edit reevaluates required membership and removes invalid entries while retaining valid entries. A changed required set returns needs-selection, even if removing a member makes old entries numerically complete; require a fresh confirmation. Equipment changes invalidate affected previews and mark corresponding entries for authoritative revalidation. Persist only confirmed choices, never client hover state. Restart restores progress without an automatic round. Change 5 attaches final-confirm execution to the same facade, so no second submit API is exposed.

If the required actor set is empty, collection stays paused with an explicit no-eligible-actors reason and only party-operation paths. It never treats all([]) as permission for enemy actions/upkeep. Confirmed surrender remains available; confirmed retreat takes its approved no-acting-ally defeat branch. No invented wait/skip action or editing-triggered time advance is added.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
