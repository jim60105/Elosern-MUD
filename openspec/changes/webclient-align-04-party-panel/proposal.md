# Proposal: webclient-align-04-party-panel

## Why

The design draft's left-HUD companion quickbar (`.comps`) and 同伴 · 隊伍 drawer render party
members with HP and the seven-stage bond name, and the combat variant tags each companion with
its `aN` token. No committed panel carries any of this — the showcase contract defers both
surfaces precisely because there is no `party` read model. This change lands the server-side
read model so the HUD (change 05) can be built and un-deferred.

## What Changes

- New `party` presentation panel (schema version 1): an available form carrying `slots` (0..4
  rows), each row `{identity, display_name, portrait_ref, hp_current, hp_maximum, bond_stage}`
  — reusing the existing NPC wire vocabulary (exploration interact-target rows and combat
  participant rows), flat HP field names, and the draft's bond contract (canonical stage NAME
  only; the raw affinity number never ships). `portrait_ref` is `null` this version, matching
  the current portrait-catalog seam.
- Presenter reads `world/rules/party.py::live_companions()` (stale dbids never reach the wire),
  each companion's true current HP traits, and the affinity rulebook's stage name via
  `npc.relations.stage_for(player)`. An empty party is an available panel with `slots: []`.
- Server validation mirrors the client mirror's exact-shape gates (row count 0..4, key sets,
  code-point bounds, positive HP integers with `hp_current <= hp_maximum` never asserted as a
  rule — traits are truth, bounds only).
- Registry registration + coordinator dirty-flag push on the existing party mutation seams
  (join/leave/purge already exist in `world/rules/party.py`).
- No `token` field: combat HUD joins `party.slots` to `combat.participants` by `identity`; the
  `aN` numbering owner stays `combat_view` alone.

## Capabilities

### New Capabilities

- `webclient-party-panel`: the `party` read model — shape, vocabulary reuse, stage-name-only
  bond disclosure, staleness filtering, push timing, and read-only presenter isolation.

### Modified Capabilities

(None — panel registration rides the existing `webclient-oob-protocol` registration contract
without changing it.)

## Impact

- New presenter + validator module under `web/webclient/presentation/`; registration in the
  presentation registry; snapshot/update routing picks it up for exploration AND combat puppets
  (the combat quickbar needs it).
- New focused Evennia test module; `.github/evennia-shards.json` updated in the same change;
  `covers_requirement` annotations against the new requirement IDs.
- Client mirror + `webclient-vue-application` protocol mirror table gains the `party` panel
  entry so a stale client rejects rather than renders it.
