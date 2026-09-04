# Design: webclient-align-04-party-panel

## Context

`world/rules/party.py` owns membership (`player.db.party` dbid list, cap 4, `live_companions()`
filters stale dbids, `join_party`/`leave_party`/`purge_npc_memberships` are the write seams).
Bond stage resolves via `npc.relations.stage_for(player).name` (rulebook-configured seven-stage
table, canonical zh-TW names). Combat participants already carry `{identity, token, …}` with a
session-stable `aN` numbering owned by `combat_view`. Presentation panels register through
`PresentationRegistry.register(PresenterSpec)`; snapshot/update routing iterates the registry,
so registration alone routes the panel. The client enforces a panel allowlist mirrored in three
places: the server registry, the UMD `web/static/webclient/js/elosern/protocol.js`, and the Vue
store's `PANEL_ALLOWLIST`.

## Goals / Non-Goals

**Goals:**
- One new `party` panel, schema version 1, vocabulary identical to existing NPC rows
  (`identity`, `display_name`, `portrait_ref`, flat `hp_current`/`hp_maximum`).
- Bond disclosure is stage NAME only (design: 數值隱藏七階羈絆). Raw affinity never ships.
- Empty party = available `slots: []` (the client renders the dashed invite slot from it).
- Push on party mutations rides the coordinator's existing dirty/push rhythm.

**Non-Goals:**
- No `token` field (combat HUD joins by `identity`); no portrait catalog work (`portrait_ref:
  null` this version, same contract as exploration rows); no client HUD (change 05).

## Decisions

- **Row shape:** `{identity, display_name, portrait_ref, hp_current, hp_maximum, bond_stage}`
  — exact key set, validator-strict. `bond_stage` is a non-empty bounded string from the
  rulebook stage table, never a number. HP from the companion's true traits (not
  `disguised_stats` — display disguise must not leak into party truth, per AGENTS invariant).
- **Ordering:** party list order (`party_ids` sequence) is the slot order — stable, no
  re-sorting client-side.
- **Availability:** common unavailable form for creation-pending/no-location puppets, reusing
  the shared builder (no new reason strings invented beyond the standard set the registry
  enforces).
- **Push timing:** the three write seams already funnel through `party.py`; each already marks
  the owning player's presentation dirty for status/context panels — the party push rides the
  same coordinator invalidation (verify in implementation; if `join/leave` currently mark a
  narrower set, widen to include `party` in the same change).
- **Mirrors:** add `party` to the UMD protocol allowlist and the Vue `PANEL_ALLOWLIST` (both
  are protocol mirrors, not frozen surfaces); extend the Node `ui_contract` expectations and
  the Vue store mirror test so all three lists provably agree.

## Risks / Trade-offs

- A companion's HP only changes through combat settlement (companions are battlefield state);
  if a settlement path forgets to re-push, HP can lag one commit — mitigated by the snapshot
  rebuild on every mode change and by a focused test asserting update-after-settlement shape.
- Row cap 4 mirrors the rules cap; raising either later is a coordinated change, pinned in the
  spec so drift fails loudly.
