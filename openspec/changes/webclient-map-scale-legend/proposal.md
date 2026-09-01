# Proposal: webclient-map-scale-legend

## Why

A wilderness cell is 10 km (`WILDERNESS_KM_PER_CELL = 10`), but no player-facing surface ever says
so: with Model A footprints (change `wilderness-anchor-footprint`) the world finally has honest
distances — the city is 50 km wide, a day's march is a handful of cells — yet the expanded
full-map overlay still presents the lattice as unscaled decoration. The user explicitly asked the
expanded map to show the 10 km/cell wilderness scale.

## What Changes

- The server's `local_map` wilderness-layer payload gains one extra `legend` entry stating the
  scale, derived from `world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL` at build time (no
  constant duplicated in the client or in another module): e.g. `每格約 10 公里`. Grid, instance,
  and interior layers keep their current legend exactly (their cells are not 10 km).
- The shared lattice renderer (`MapLattice.vue`) stops style-cycling legend entries beyond the
  four visibility states: entries past the state list render with a neutral info chip treatment
  (design-token colors, text as the primary carrier), so the scale line reads as a note, not as
  a fifth visibility state. This generalizes the already-permitted "extra entries cycle" behavior
  of the legend contract.
- The scale entry appears wherever the payload legend renders — by the existing contract that is
  the full-map overlay only (the minimap island mounts no legend), which is exactly the surface
  the user named.

No payload schema field is added: the legend is already a bounded list of text entries shared by
both validators, so the wire format, the Python validator, and the JS validator are unchanged.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-local-map`: the wilderness-layer payload's legend states the km-per-cell scale from
  the provider constant; the browser legend renders non-state entries with a neutral treatment.

## Impact

- Affected code: `web/webclient/presentation/local_map.py` (wilderness legend assembly),
  `web/webclient-app/components/MapLattice.vue` (legend chip treatment), their Vitest/browser
  tests, Storybook fixtures if a story pins legend content, and `.github/evennia-shards.json`
  only if a Python test module is added (expected: none — extend existing modules).
- **Dependency:** serialize AFTER `wilderness-anchor-footprint-local-map` (which itself
  serializes after `wilderness-anchor-footprint`) — all three touch the wilderness presentation
  in the same file (`local_map.py`) and the same delta capability; landing them in parallel
  guarantees merge conflicts and conflicting legend scenarios.
- No player-command surface change; no new dependencies.
