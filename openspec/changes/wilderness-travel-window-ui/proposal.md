# Proposal

## Why

Replace the temporary node adapter with the shared run-length decoder and display live sight, phase tint and disclosed annotations. This delivers the approved browser travel interface without duplicating the sight/reveal rules batch.

## What Changes

- Replace the temporary node adapter with the shared run-length decoder and display live sight, phase tint and disclosed annotations.
- Add the focused behavior, production fixture/story and browser/server evidence specified in design.md and tasks.md.
- **BREAKING** Any schema cutover described in design.md replaces its prior prerelease form, with no migration or compatibility path.

## Capabilities

### New Capabilities
- `webclient-travel-window`: Replace the temporary node adapter with the shared run-length decoder and display live sight, phase tint and disclosed annotations.

### Modified Capabilities
- `webclient-map-panel-protocol`: Amend existing exact contracts for this travel slice.

## Impact

wilderness-area-map-reveal owns schema2 rows, unknown runs, sparse nodes, bounded transport, the shared lib/area_map_view.js decoder and existing AreaMapView cutover. wilderness-sight-rules/ground-reveal/map-disclosure own all visibility and disclosure decisions. This slice consumes those results; it does not redefine radii, permanent reveal, distant ranges, hidden entries or population. The base temporary adapter must be removed, not retained as a second wire version.

## Non-goals

No new server travel mode, client-side rules/routing, authored geography, new art, camping rules/cards, dialogue/combat redesign, compatibility or database migrations. Visual style, copy and prototype fidelity are human-reviewed against the approved interface design rather than tested as normative qualities.

## Batch:
depends-on: wilderness-travel-map-ui
depends-on: wilderness-travel-log-ui
depends-on: wilderness-area-map-reveal

Code-conflict notes: use this change's design.md matrix. Only direct prerequisites are machine dependencies; shared AppClient/store/protocol/docs and shard-manifest edits require serialized integration. Base adapter-path changes1-5 can ship before sub-project1; changes6-8 consume its protocols. A Batch without depends-on lines is an independent root.
