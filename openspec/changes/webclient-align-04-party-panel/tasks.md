# Tasks: webclient-align-04-party-panel

## 1. Presenter + validator

- [ ] 1.1 New `web/webclient/presentation/party.py`: build the version-1 available form from
  `world/rules/party.py::live_companions()` in party-list order (≤4 rows) — `identity`,
  `npc_display_name()` truncated to the shared bound, `portrait_ref: None`, true-trait
  `hp_current`/`hp_maximum` (never `disguised_stats`), `bond_stage` from
  `npc.relations.stage_for(player).name`; empty party → `slots: []`; shared unavailable builder
  otherwise.
- [ ] 1.2 Exact-shape validator mirroring the row key set, string bounds, and non-negative
  integers; reject numeric/blank `bond_stage`, fifth row, extra/missing keys.
- [ ] 1.3 Register the panel in the presentation registry; verify snapshot/update routing picks
  it up for exploration and combat puppets.

## 2. Push timing

- [ ] 2.1 Confirm `join_party`/`leave_party`/`purge_npc_memberships` and combat settlement
  re-push presentation; widen the coordinator invalidation to name `party` wherever the write
  seams currently mark only status/context panels.
- [ ] 2.2 Observability: boundary `log_info` events on push-path failures only where the
  facade catalog requires; run the observability lint if logging paths change.

## 3. Client protocol mirrors

- [ ] 3.1 Add `party` to the UMD allowlist (`web/static/webclient/js/elosern/protocol.js`) and
  the Vue store `PANEL_ALLOWLIST`; extend the contract test asserting server-registry ∪ UMD ∪
  Vue allowlists agree (the three-list agreement scenario).

## 4. Tests + traceability

- [ ] 4.1 New Evennia test module under `web/webclient/presentation/tests/`: two-companion
  shape/order/bond-name payload, empty-party available form, stale-dbid omission, validator
  rejection rows, creation-pending unavailable form, membership-change re-push, settlement HP
  refresh, identity-join token recovery (against the combat panel payload). Land
  `covers_requirement` literal IDs at the archive/sync commit (IDs unknown to the checker
  before sync; magic-xp P1 precedent).
- [ ] 4.2 Register the new module in exactly one shard of `.github/evennia-shards.json`.
- [ ] 4.3 Node gate + Vitest store test updated for the allowlist entries.

## 5. Verification

- [ ] 5.1 Focused Evennia label for the new module + `tools.spec_traceability check`.
- [ ] 5.2 Live container check: with `party` registered, snapshot JSON shows the exact version-1
  form for the bound test party (manual or scripted WS probe).
