# Design: Exact v7 actor draft read models and mirrored panel schemas

## Context

See proposal.md for motivation and `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` §11 for complete coverage, order and conflicts. Current context_actions is v5; active panel-v6 adds conditions and polarity only. Exact server/client field validators and the parity test require a new version for mandatory party fields.

Observed starting points are separate from proposed behavior below; no runtime result is claimed. The approved 2026-10-15 document explicitly amends engine §6.3 subtraction, allied autonomy and individual allied flee.

## Goals / Non-Goals

This slice owns exact v7 actor draft read models and mirrored panel schemas, using existing deterministic state owners and exact protocol conventions. Its delta files define acceptance. No compatibility path, data migration, shared bag, companion equipment-management UI or proficiency-based physical growth is added. Stage geometry stays with the existing active UI batch.

## Decisions

Bump `context_actions` from active v6 to v7 with no compatibility parsing. The combat available form is exactly `schema_version, available, kind, session, participants, root_actions, secondary_actions, actors, choices, draft, suggestions`; retain v6 participant conditions and every skill polarity/scale fact inside the requested actor choices. Remove puppet-level `skills`. `actors` is ordered by allied participant order with at most five entries, each exactly `identity, commandable, reason`. Reason is null or the existing bounded code/message shape; `choices` is exactly `actor_id,skills,items,tactics`, for one requested authorized actor only; a noncommandable actor has no enabled choices. Skill descriptors reuse v6 grouped shape, max 192 for that actor. Item rows are exactly `item_key,label,summary,quantity,enabled,reason,target_spec,targets,hostile,beneficial`; quantity is a nonnegative safe integer, targets reference up to 16 current participants, and target_spec is none|self|single for the caller-supplied target while registry effects still own full item reach. `summary` is server-authored effect prose of 0..512 code points. Bound item rows to 128 distinct usable item keys with explicit fail-closed overflow, never truncate owned usable choices. Derive polarity from typed effects using the authoritative classification, including mixed item effects. Tactics are exactly `key,label,enabled,reason,targets`, key defend|dodge|taunt, targets only for Taunt. `draft` is exactly `round_revision,draft_version,required_actor_ids,entries,needs_selection_ids,reselection_reasons`; entries are exactly `actor_id,command` with closed request union described below. IDs are unique positive safe integers and references must join current party/participants; all subset, count, revision and reason/enabled invariants are mirrored. Session/labels/keys reuse existing bounds, token max 128 codepoints, actors max 5 and participants max 16. Invalid forms fail closed in both validators.

Exact action keys are root_actions `attack,skills,items,defend,dodge,taunt,retreat` in that order and secondary_actions `surrender`. Bag is a client-local free row, never a gameplay descriptor. Recovery has root_actions=[], secondary_actions=[surrender], actors=[], choices=null and draft=null. Ready combat has one choices object; choose the first required actor missing a command, otherwise commander. `reselection_reasons` is a list of at most five exact `{actor_id,reason}` rows for currently required actors whose previously selected command failed validation; reason is the existing exact `{code,message}` shape, code 1..64 lowercase identifier characters and message 1..512 code points. Each actor appears at most once; every actor with such a reason appears in needs_selection_ids. Ordinary missing entries need no error row. Noncommandable actors have a nonnull reason; commandable actors have null reason.

Labels are 1..64 code points, item/skill keys 1..64 nonwhitespace characters, summaries 0..512 code points, target lists at most16 unique current participant IDs, actor/draft lists at most5 unique party IDs, skill flattened bound192, item rows128, and tactics3. Quantities/revisions are 0..9007199254740991 integers excluding bool; identities are 1..9007199254740991. Tactic rows have exactly key,label,enabled,reason,targets, with no targets for defend/dodge and current enemy candidates for taunt. Nested skill facts reuse v6 exact bounds and flags; skill/item/tactic enabled=true requires reason=null, disabled requires bounded reason. The canonical whole publication retains MAX_CANONICAL_JSON_BYTES=65536, MAX_DEPTH=12, MAX_FIELDS=64 and MAX_LIST_ITEMS=320. Test a maximal obtainable catalog plus real usable items, five actor summaries, draft and 16 participants; never truncate choices or send five full catalogs. Actor-choice transport requests and command/result schemas are owned by party-combat-command-transport and must use this same schema; this slice introduces no adapters or gameplay path.


## Session revision in recovery

The v7 session object contains exactly session_id, mode, round, round_revision, state and reason. Its always-present round_revision uses the same safe-integer bound as the draft and equals draft.round_revision whenever draft is nonnull. Recovery can therefore request and confirm surrender against the authoritative revision even though choices and draft are null. A malformed record with no trustworthy revision remains unavailable under the existing recovery rules; the client never invents a revision.

## Risks / Trade-offs

- [Shared integration seams] -> Respect direct prerequisites and the complete conflict matrix, preserving earlier delta additions. No obsolete adapter or duplicate formula remains after the coordinated cutover.
- [State changes after selection] -> Repeat authoritative validation; invalid drafts and normal mid-round invalidation have different explicit semantics.
- [Unproven results] -> Run the focused independent evidence owned in tasks. A chosen constant alone is not measured balance and a mocked client is not actual runtime acceptance.
- [Bounded effort] -> 6.5 hours includes implementation, focused evidence, docs and integration. Required adjacent behavior has a named owner in the20-change batch and is required for assembled acceptance.

## Migration Plan

Pre-release clean cutover. Implement affected code/callers/fixtures/annotations together in this slice; no old/new parser or data migration. An ordinary revert of an implementation commit is the rollback mechanism. Proposal authoring performs no implementation, apply, archive, merge or worktree operations. The assembled feature is accepted only after party-combat-runtime-acceptance.

## Verification and documentation ownership

Use synthetic fixtures for behavioral expectations and the existing real-data calibration boundary for authored roster evidence. Added/moved Evennia test modules and browser methods must have exactly one shard owner. Use canonical `<capability>.<requirement-slug>` IDs from project traceability tooling, migrating all affected annotations. Update existing affected docs and both player command documents for command syntax/context changes. Focused implementation checks include `uv run --locked python -m tools.contract_gate`; changed logging also requires observability lint and focused event tests. Complete managed browser and traceability-evidence runs stay CI-owned.
