# Design: Guarded command adapters results and canonical publication

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. The exact v7 read-model/panel contract is a prerequisite. Existing dispatcher authentication, result-data and canonical publication rules remain the integration boundary.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns guarded command adapters results and canonical publication, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Use the exact v7 panel/read-model contract from party-combat-protocol-v7; this slice owns adapters, guarded payloads, result semantics and publication. Register only combat.actor_choices, combat.command, combat.exit_prompt and combat.exit_confirm as the combat adapter group. The outer dispatcher still passes the authenticated puppet as commander; actor_id is a subordinate session participant reference authorized inside the rules API, never account identity. Allow session_id and actor_id only in these exact guarded schemas; account/puppet/session spoofing fields elsewhere remain rejected.

Exact payloads: actor_choices is {session_id,round_revision,actor_id}; command is {session_id,round_revision,draft_version,actor_id,command}; exit_prompt is {session_id,round_revision,operation}; exit_confirm adds confirmation_token. Session IDs are 1..128 code points, tokens 1..128 URL-safe ASCII characters, operation is retreat|surrender and all IDs/revisions use the schema safe-integer bounds. Command is {kind,payload}, where kind skill uses exactly skill_key plus its existing TargetSpec target_ids or target_shorthand and optional scale (0.25|0.5|1|2|4, absent=1); item uses item_key with optional single target_id; tactic uses key defend|dodge with no target_id, or taunt with exactly one target_id. Unknown fields and reserved skill flee reject. Validation repeats current actor capability, item ownership and targets; exact shape alone never authorizes the actor.

Actor-choice selection lives in transport-owned presentation context and clears on session/epoch/puppet change; it cannot mutate the draft or invoke possession. Keep default actor selection from schema11 on reconnect. Active-combat inventory.use rejects, while exploration inventory.use and free commander inventory.toggle_equip keep exact old schemas. Remove combat.cast/flee/forfeit registrations entirely; dependent client/text slices migrate every producer before assembled release.

Keep the existing exact seven-field ui_action_result envelope and success-only optional data slot, its eight-field/global byte/depth bounds and reserved-key protections unchanged. Result variants: actor query is outcome success/code actor_choices with no data; a nonfinal edit is success/draft_saved with no data; accepted operation retry is success/already_committed with no data; a committed ordinary round is success/round_committed with no data; terminal settlement is success/combat_terminal with no data. Current-state preflight needing reselection is rejected/needs_selection with no data, and stale session/round/edit version is stale/stale_command with no data. Stable capability rejection uses rejected plus existing bounded reason code and no data. All member-specific progress/reasons come from canonical v7 draft, never error data.

Only exit_prompt uses outcome success/code party_exit_prompt with data exactly {operation,confirmation_token,scope,consequence}; scope is literal party, operation/token use request bounds, and consequence is server-authored 1..512 code-point text reflecting hostile/exam and failed-retreat behavior. Session/round are bound to the stored initiating request and token, never inserted as forbidden result-data state keys. Unexpected/missing/extra fields reject at the adapter-specific result validator/mirror; no global result validator weakening is allowed. Cancel discards local prompt data, not server draft entries. The backend token remains commander/session/round/operation bound.

Publish canonical progress and all affected panels at the new presentation revision before the matching action result. Only a final confirmation or accepted retreat that actually commits a round may publish that round record as beats; edits/queries/prompts/reselection/reconnect do not. Terminal outcomes refresh every mode-dependent panel. Read-only actor queries and exit prompts must not emit fake gameplay or round events. Update dispatcher registry and scale canonical requirements with complete preserved noncombat groups. This and the dependent client changes are one unreleased cutover; no compatibility adapter is retained.


## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
