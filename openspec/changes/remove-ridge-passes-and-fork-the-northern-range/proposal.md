# Proposal

## Why

The shipped ridge has three traversable passes and an unforked northern crest. The authored world requires an unbroken southern range and a north-opening valley around `village_eolas`, with travel between east and west going through the physically walkable deep forest around the northern tips.

## What Changes

- Permit `terrain.ridge.passes: []` without removing the field or its editor commands; ship no passes.
- **BREAKING** Extend the ridge model with optional paired west/east crest routes. End the physical stem at their shared crotch, join both impassable arms without a gap, and keep their tips inland inside the forest.
- Feed the complete physical crest into validity, component indexing, preview/capture, elevation and partition. Keep region classification, nominal claims and displayed political polylines stem-derived.
- Retain hand authoring for branches, with editor display and lossless serialization. Add no branch-editing commands.
- Replace obsolete pass assertions with barrier, fork, valley-clearance and forest-detour contracts. Regenerate the partition and elevation, and update technical geography documentation.

## Capabilities

### New Capabilities

None. The fork extends the existing terrain capability.

### Modified Capabilities

- `map-authoring-documents`: legal empty passes and paired branch route schema/round trips.
- `wilderness-terrain`: continuous forked physical crest, unchanged region/claim derivation and reachable hidden valley.
- `wilderness-map-provider`: complete crest impassability with bounded lookup and forest detours.
- `map-editor-geography`: usable empty-pass editing and display/preservation of hand-authored branches.
- `wilderness-elevation-generation`: maximum physical ridge rise over active stem and arms.
- `map-district-partition`: arms block the input walkability raster; political traversal boundaries stay unchanged.

## Impact

Implementation touches map-core schema/documents/terrain/composition/elevation, game geography composition and component indexing, the continent's ridge block, existing tests, two geography references and regenerated `world/maps/data/district_partition.json` and `content/maps/wilderness_elevation.json`. No new dependencies or migrations are needed. The existing reference-context artifact is unchanged unless its existing freshness checker requires regeneration; it must never be hand edited.

Non-goals are coastline, waterways/fords, forest edge, region declarations, harbours, locations, districts, footprints, movement rules, gameplay and generative services. Existing identifiers stay fixed. This is one engineer-day change with one model cutover and one final verification batch.

All requirements describe mechanisms or geographic relationships established by discoverable tests, never copied data tables or raster snapshots. Visual resemblance and the narrative quality of the hidden valley are human-reviewed against `docs/development/continental-geography.md`; they are not automated requirements. The precise wall, clearance and connectivity mechanisms are tested.

## Batch:

No predecessor change is required.

Serialize against any change touching map-core terrain/schema/documents/authoring/elevation/partition, game geography or wilderness reachability, the continent source, either generated artifact, the affected main specs or their tests/docs. The planning commit touches only this change directory. Implementation is cut later by os-apply.
