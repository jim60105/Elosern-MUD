# Proposal

## Why

The shipped range has three traversable passes and an unforked northern crest. The authored world requires an unbroken southern range, a north-opening hidden valley around `village_eolas`, and east/west travel through the walkable deep forest around inland northern tips.

The owner ruled that the periodic curve was a simplified implementation. The entire ridge becomes an arbitrary authored nonstraight crest. Its authored stem is the single source for physical walls, mountain corridor, nominal nation split, displayed political lines and elevation; no separate reference axis survives.

## What Changes

- Permit required `terrain.ridge.passes: []`, keep existing editor pass commands and ship no passes.
- **BREAKING** Replace periodic ridge parameters with a required authored stem route and optional paired west/east arm routes. Derive endpoints/extents from the routes, join the crotch without gaps and keep tips inland in deep forest.
- Derive corridor, claims, borders, validity, component indexing, preview/capture, elevation and partition from those same routes. Numerical boundaries can change; geographic outcomes stay within their declared contracts. Arms are forest barriers, with no arm mountain corridors or political lines.
- Extend existing editor move/insert/remove control-point features to stem and arms, with one-document history and shared-crotch editing; retain zero-pass editing and generic round trips.
- Replace obsolete periodic/pass/old-coordinate tests with authored derivation, continuity, clearance, share and connectivity mechanisms. Regenerate partition/elevation and update existing geography documentation.

## Capabilities

### New Capabilities

None. Authored ridge routes extend the existing terrain capability.

### Modified Capabilities

- `map-authoring-documents`: required stem, optional paired arm schema, empty passes and round trips.
- `wilderness-terrain`: single authored crest authority for terrain, claims and political derivation; continuous Y and reachable hidden valley.
- `wilderness-map-provider`: complete crest blocking and bounded local lookup with forest detours.
- `map-editor-geography`: crest control-point move/insert/remove, shared-crotch history and usable zero-pass editing.
- `wilderness-elevation-generation`: maximum rise over active authored stem and arm profiles.
- `map-district-partition`: complete authored crests block input walkability and crest-derived political boundaries block propagation.

## Impact

Implementation touches map-core schema/documents/terrain/composition/elevation, game geography/reachability, editor backend/snapshot and existing frontend control-point paths, the continent's ridge block, existing tests, geography references and editor command documentation, plus regenerated `world/maps/data/district_partition.json` and `content/maps/wilderness_elevation.json`.

Remove obsolete `base_x`, `period`, `step`, `min_x`, `max_x`, `north_limit_y` fields and their typed projections/controls. Route endpoints, frame validation and derived row tables own their remaining purposes. Keep `mountain_corridor_half_width` and `passes`. No physical fallback, separate axis, migration, compatibility alias or dependency is introduced.

Coastline, waterways/fords, forest edge, region declarations, harbours, locations, districts, footprints, movement/gameplay/AI and effective demographic targets remain unchanged. The owner explicitly superseded freezing derived region/political coordinates; preserve the 5,000,000 km² area, protected land points, share tolerances, Eolas identity/forest membership and one walkable anchor/harbour component. This remains one bounded engineer-day model/editor cutover using existing control-point infrastructure.

Requirements describe discoverable-test mechanisms and geographic relationships. Geological plausibility and visual/narrative quality are human-reviewed against `docs/development/continental-geography.md`, never tested by copied coordinates, counts or visual assertions. Deterministic interpolation does not require a periodic or equidistant physical curve.

## Batch:

No predecessor change is required.

Serialize against map-core terrain/schema/documents/authoring/elevation/partition and their constructors, game geography/reachability, editor geography/snapshot/control-point UI, the continent/derived artifacts and affected specs/tests/docs. Planning commits touch only this directory on master; os-apply cuts implementation later.
