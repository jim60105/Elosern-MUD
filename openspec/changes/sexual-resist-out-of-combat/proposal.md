## Why

`sexual-resist-turn-cost` (`B6b`) wired the affinity consequence of a forced sexual act — `-sexual_forced_penalty`
via `AffinitySource.SEXUAL_FORCED`, and the existing party auto-leave rule — into live combat rounds through
`world/rules/combat_session.py::_scan_sexual_coercion`. That proposal's own design.md (Decision 5) explicitly
deferred, rather than silently dropped, the identical consequence at the out-of-combat cast path: every
resistible sexual act is declared `usable_out_of_combat=True` (`world/skills/sexual_acts/_builder.py`), and
`world/rules/action.py::_step4b_sexual_resist_gate` already rolls the same contest and emits the same
`EventEntry(kind="sexual_resist", ...)` regardless of whether the cast runs through `ActionResolver.resolve`
in combat or through `world/rules/cast_settlement.py::settle_out_of_combat_cast` out of combat. Today only the
in-combat caller (`submit_player_action`) scans that entry for a forced outcome; `settle_out_of_combat_cast`
has no equivalent scan, so a player who forces a resistible sexual act on an NPC out of combat pays no
affinity cost at all, while the identical act performed one turn into a fight does. The approved design
(`docs/superpowers/specs/2026-08-15-sexual-act-resolution-design.md` §5) states the out-of-combat and
in-combat consequences are "otherwise identical" — that symmetry does not currently hold.

This proposal closes that gap by adding the out-of-combat half of the mechanism, mirroring
`_scan_sexual_coercion`'s already-shipped, already-tested pattern.

## What Changes

- Add `world/rules/cast_settlement.py::_scan_out_of_combat_sexual_coercion(actor, targets, event_log) ->
  tuple[tuple[str, ...], _CoercionRestoreState | None]`, structurally mirroring `_scan_sexual_coercion`
  exactly: scans one resolved cast's
  `EventLog.entries` for `kind == "sexual_resist"` records where `resisted is False and auto_comply is False`
  (a forced outcome), resolves each entry's `target` key against the cast's own explicit `request.targets`
  (no `Battlefield`/roster exists out of combat — the request's target list is already the complete,
  correctly-scoped candidate set, so no roster-widening decision is needed), and applies
  `-sexual_forced_penalty` through the existing sole writer `apply_affinity_change(target, actor,
  AffinitySource.SEXUAL_FORCED, ...)` for every resolved `NPC` target. A compliance (rolled or automatic)
  or a successful resistance applies no penalty, exactly as in combat.
- Wire that scan into `settle_out_of_combat_cast`, running inside the same outer `transaction.atomic()`
  immediately after a successful `ActionResolver.resolve`, so a penalty-application failure rolls back the
  entire cast (resolution, practice, planner writes, and clock advance together) rather than leaving a
  half-applied cast.
- The new scan owns its own before-the-fact snapshot of the touched NPCs' `relations_data` (and, when the
  auto-leave rule fires, the actor's party membership surfaces) and its own on-failure restore, reusing the
  existing `restore_relations_surfaces` / `restore_membership_surfaces` helpers exactly as
  `_scan_sexual_coercion`'s own except-block already does. The scan returns its snapshot as a
  `_CoercionRestoreState`, which `settle_out_of_combat_cast` also restores from its outer `except` block
  when a *later* step of the transaction (the clock advance) fails after the scan's penalty block
  succeeded — the idmapper cache is not transaction-aware, and unlike the in-combat round's
  `_restore_round_touched`, the settlement's generic restore covers no relations surface, so without this
  a post-scan failure would leave a rolled-back penalty readable in-process. This keeps the change
  entirely additive: the cast-settlement outer snapshot (`_snapshot_settlement_state` /
  `_restore_settlement_state`) and its existing `_ENTITY_SURFACES` list are untouched, so
  `cast-settlement-atomicity`'s existing behavior and spec are unaffected.
- Add a `notifications: tuple[str, ...]` field to `cast_settlement.CastSettlement` (default `()`), populated
  from the new scan's auto-leave notification lines, and update `commands/action.py::CmdCast._cast_out_of_combat`
  to send those lines to the caller after a successful cast — mirroring how the in-combat session path already
  delivers `_scan_friendly_fire`/`_scan_sexual_coercion`'s notifications via `settle_to_messages`. Without this,
  a companion NPC could silently auto-leave the party from an out-of-combat forced act with no player-visible
  message, unlike the in-combat case.

No backward compatibility or migration concerns: the project has no released users, `CastSettlement` gains an
optional field with a default, and every affected symbol (`AffinitySource.SEXUAL_FORCED`,
`sexual_forced_penalty`, `apply_affinity_change`, `restore_relations_surfaces`, `restore_membership_surfaces`)
already exists and ships unchanged.

## Capabilities

### New Capabilities
- `sexual-resist-out-of-combat`: the affinity consequence of a resisted or forced sexual act cast outside
  combat — the out-of-combat sibling of `sexual-resist-turn-cost`, reusing its penalty constant and affinity
  source, scoped to the cast's own explicit target list, with its own rollback-safe relations/party snapshot
  and player-visible auto-leave notification delivery.

### Modified Capabilities
(none — `cast-settlement-atomicity`'s existing requirements, snapshot surfaces, and restore behavior are
unchanged; this proposal adds a new, self-contained post-resolution step rather than altering any of them)

## Impact

- **New capability spec:** `openspec/specs/sexual-resist-out-of-combat/` (this change).
- **Modified files:** `world/rules/cast_settlement.py` (`_scan_out_of_combat_sexual_coercion`, its wiring
  into `settle_out_of_combat_cast`, and the new `CastSettlement.notifications` field),
  `commands/action.py` (`CmdCast._cast_out_of_combat` delivers the returned notification lines).
- **Reads (no changes) from:** `world/rules/affinity.py` (`AffinitySource.SEXUAL_FORCED`,
  `apply_affinity_change`, `restore_relations_surfaces`), `world/rules/affinity_config.py`
  (`get_config().sexual_forced_penalty`), `world/rules/party.py` (`restore_membership_surfaces`,
  `is_companion`, `leave_party`, `AUTO_LEAVE_MESSAGE` — all reached transitively through
  `apply_affinity_change`), `world/rules/action.py` (the `sexual_resist` `EventEntry` contract
  `_step4b_sexual_resist_gate` already emits), `world/rules/event_log.py` (`EventLog`, `EventEntry`).
- **Dependencies:** `sexual-resist-turn-cost` (already archived — supplies `AffinitySource.SEXUAL_FORCED`,
  `sexual_forced_penalty`, and the `_scan_sexual_coercion` pattern this proposal mirrors),
  `sexual-resist-cast-wiring` (already archived — the actual emitter of the `sexual_resist` `EventEntry`
  this proposal's scan consumes), `cast-settlement-atomicity` (already archived — the outer transaction this
  proposal's scan runs inside).
