# Proposal

## Why

The shipped range has three traversable passes and an unforked northern crest. The authored world requires an unbroken southern range and a north-opening valley around `village_eolas`, with east/west travel going through the walkable deep forest around inland northern tips.

The owner clarified that the existing regular curve is a simplified implementation. This change replaces the physical stem's periodic curve with an arbitrary authored nonstraight polyline and adds independently authored fork arms. Determinism means repeatable rasterization, with no required periodic bend or geological-quality test.

## What Changes

- Permit `terrain.ridge.passes: []` without removing the field or editor pass commands; ship none.
- **BREAKING** Add a required physical stem route and optional paired west/east arm routes. Join all physical crests at the authored crotch without a gap; stop the stem there and keep the arm tips inland in forest.
- Separate physical crest geometry from the existing region/political reference axis. Keep classifier inputs, nominal claims, corridor, forest edge and displayed political lines unchanged; they must never gain arm segments.
- Feed complete physical walls into validity, component indexing, preview/capture and partition; raise elevation from the maximum of active authored crest profiles.
- Retain hand authoring for crest routes, with editor display and lossless serialization. Add no crest-route commands; preserve existing scalar and pass controls.
- Replace obsolete periodic-stem/pass assertions with authored-route, fork, barrier, clearance and forest-detour mechanisms. Regenerate partition/elevation and update existing technical geography references.

## Capabilities

### New Capabilities

None. Authored physical routes extend existing terrain behavior.

### Modified Capabilities

- `map-authoring-documents`: required physical stem, optional paired arm schema, empty passes and round trips.
- `wilderness-terrain`: arbitrary continuous forked physical crests with unchanged region/political reference derivation.
- `wilderness-map-provider`: complete physical wall impassability with bounded lookup and forest detours.
- `map-editor-geography`: zero-pass editing and display/preservation of hand-authored crest routes.
- `wilderness-elevation-generation`: maximum rise over active authored stem and arms.
- `map-district-partition`: complete physical crests block walkability; political propagation boundaries remain unchanged.

## Impact

Implementation touches map-core schema/documents/terrain/composition/elevation, game geography/component composition, the continent's ridge block, existing synthetic/data-contract tests and two geography references, plus regenerated `world/maps/data/district_partition.json` and `content/maps/wilderness_elevation.json`. Every constructor/fixture adopts the required stem route; there is no algorithmic physical fallback, compatibility layer, migration or new dependency.

Non-goals remain coastline, waterways/fords, forest edge, region declarations, harbours, locations, districts, footprints, movement/gameplay and generative services. The original unchanged region/political constraints require retaining the existing reference-axis parameters for those consumers only. Their regularity is not a physical-world requirement. This is one bounded engineer-day map-core cutover with one final serial verification batch.

Every requirement is a discoverable-test mechanism or geographic relationship, never a copied coordinate/count/wording table. Naturalness, geological plausibility and visual/narrative quality are human-reviewed against `docs/development/continental-geography.md`; they are not automated requirements. Clearance, continuity, no-crossing and connectivity are tested.

## Batch:

No predecessor change is required.

Serialize against changes to map-core terrain/schema/documents/authoring/elevation/partition and their constructors, game geography/reachability, the continent or generated artifacts, or the affected main specs/tests/docs. The planning commits touch only this change directory on master; os-apply cuts the implementation branch later.
