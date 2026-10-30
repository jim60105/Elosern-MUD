# Proposal

## Why

Supply server-authored foot capacity and neighbour duration facts, then present the leg gauge and persisted travel preferences. This delivers the approved browser travel interface without duplicating the sight/reveal rules batch.

## What Changes

- Supply server-authored foot capacity and neighbour duration facts, then present the leg gauge and persisted travel preferences.
- Add the focused behavior, production fixture/story and browser/server evidence specified in design.md and tasks.md.
- **BREAKING** Any schema cutover described in design.md replaces its prior prerelease form, with no migration or compatibility path.

## Capabilities

### New Capabilities
- `webclient-travel-leg`: Supply server-authored foot capacity and neighbour duration facts, then present the leg gauge and persisted travel preferences.

### Modified Capabilities
- `webclient-status-presentation`: Amend existing exact contracts for this travel slice.

## Impact

Status currently supplies resources/fatigue, with schema5 asleep facts from the base slice. No active planner proposal supplies a status capacity gauge or adjacent duration quotes. travel_cost.py owns plan_traversal, source_present_members and actual rounded foot durations; fatigue.py owns detached prediction. TravelWalkControls is the working intermediate command surface. preferences.js and layout_store.js own persisted view preferences.

## Non-goals

No new server travel mode, client-side rules/routing, authored geography, new art, camping rules/cards, dialogue/combat redesign, compatibility or database migrations. Visual style, copy and prototype fidelity are human-reviewed against the approved interface design rather than tested as normative qualities.

## Batch:
depends-on: wilderness-travel-walking-ui
depends-on: wilderness-travel-log-ui

Code-conflict notes: use this change's design.md matrix. Only direct prerequisites are machine dependencies; shared AppClient/store/protocol/docs and shard-manifest edits require serialized integration. Base adapter-path changes1-5 can ship before sub-project1; changes6-8 consume its protocols. A Batch without depends-on lines is an independent root.
