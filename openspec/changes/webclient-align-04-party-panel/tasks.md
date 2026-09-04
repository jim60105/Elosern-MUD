# Tasks: webclient-align-04-party-panel

## 1. Presenter + validator

- [x] 1.1 New `web/webclient/presentation/party.py`: build the version-1 available form from
  `world/rules/party.py::live_companions()` in party-list order (≤4 rows) — `identity`,
  `npc_display_name()` truncated to the shared bound, `portrait_ref: None`, true-trait
  `hp_current`/`hp_maximum` (never `disguised_stats`), `bond_stage` from
  `npc.relations.stage_for(player).name`; empty party → `slots: []`; shared unavailable builder
  otherwise.
- [x] 1.2 Exact-shape validator mirroring the row key set, string bounds, and non-negative
  integers; reject numeric/blank `bond_stage`, fifth row, extra/missing keys, duplicate
  identities; closes with the shared `MAX_CANONICAL_JSON_BYTES` envelope guard. The HP
  companion read goes through the new public `world.rules.action.stored_gauge_pair` helper
  (`combat_view._stored_hp` now delegates to it — one stored-trait source).
- [x] 1.3 Register the panel in the presentation registry; verify snapshot/update routing picks
  it up for exploration and combat puppets.

## 2. Push timing

- [x] 2.1 Confirm `join_party`/`leave_party`/`purge_npc_memberships` and combat settlement
  re-push presentation; widen the coordinator invalidation to name `party` wherever the write
  seams currently mark only status/context panels. Verified: the WS invite/leave/move adapters
  and text-command settlement already publish full snapshots (which render every registered
  panel); the only partial publishers were `combat.cast/flee/forfeit` via
  `world.rules.combat_result.AFFECTED_PANELS`, widened there (and mirrored on the three
  `ActionSpec.affected_panels` declarations). Purge had no push path at all → 2.3.
- [x] 2.2 Observability: boundary `log_info` events on push-path failures only where the
  facade catalog requires; run the observability lint if logging paths change. (New
  `party_push_*` warn events follow the established `presentation_push_failed` idiom; lint
  clean.)
- [x] 2.3 Rubber-duck amendment: membership purge (`NPC.at_object_delete`) has no session
  context, so add `web/webclient/presentation/party_push.py` — a `watchers_for` +
  epoch-guarded `publish_panel_update({"party": …})` fan-out (the `art_push` pattern) —
  hooked from the delete seam after the purge commits; tested live-watcher and no-watcher.

## 3. Client protocol mirrors

- [x] 3.1 Add `party` to the UMD allowlist (`web/static/webclient/js/elosern/protocol.js`) and
  the Vue store `PANEL_ALLOWLIST`; extend the contract test asserting server-registry ∪ UMD ∪
  Vue allowlists agree (the three-list agreement scenario). The registry-driven coverage test
  exposed pre-existing Vue drift — `lineage` and `title_codex` were missing from the store
  mirror — completed in the same change.

## 4. Tests + traceability

- [x] 4.1 New Evennia test module under `web/webclient/presentation/tests/`: two-companion
  shape/order/bond-name payload, empty-party available form, stale-dbid omission, validator
  rejection rows, creation-pending unavailable form, membership-change re-push, settlement HP
  refresh, identity-join token recovery (against the combat panel payload). Land
  `covers_requirement` literal IDs at the archive/sync commit (IDs unknown to the checker
  before sync; magic-xp P1 precedent).
- [x] 4.2 Register the new module in exactly one shard of `.github/evennia-shards.json`.
  Verified no manifest edit needed: shard 5's whole-package `web.webclient` label owns the new
  module — `tests.test_evennia_test_optimization_contract` green. Also updated the frozen
  registry enumerations the panel addition pins: `test_combat_panel` 11→12-name set and
  `world/rules/tests/test_combat_result` panel tuple.
- [x] 4.3 Node gate + Vitest store test updated for the allowlist entries (Node count test
  11→12 + `validatePartyPanel` mirror suites; Vitest store allowlist copies).

## 5. Verification

- [x] 5.1 Focused Evennia label for the new module + `tools.spec_traceability check`
  (937-test adjacent batch green; traceability 1231/1231; observability lint clean).
- [x] 5.2 Snapshot JSON shows the exact version-1 form for the bound test party — scripted
  probe evidence: the dispatcher leave test validates the published `ui_snapshot` envelope
  through `validate_ui_snapshot` with the registered `known_panels`, and the UMD mirror
  accepts the same shapes through `Protocol.validateSnapshot` in the Node suite (container
  rebuild parity lands with the branch merge).
