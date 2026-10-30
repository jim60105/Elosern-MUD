# Proposal

## Why

Publish commit-qualified structured travel notices and render the travel band log without parsing room prose. This delivers the approved browser travel interface without duplicating the sight/reveal rules batch.

## What Changes

- Publish commit-qualified structured travel notices and render the travel band log without parsing room prose.
- Add the focused behavior, production fixture/story and browser/server evidence specified in design.md and tasks.md.
- **BREAKING** Any schema cutover described in design.md replaces its prior prerelease form, with no migration or compatibility path.

## Capabilities

### New Capabilities
- `webclient-travel-log`: Publish commit-qualified structured travel notices and render the travel band log without parsing room prose.

### Modified Capabilities
- `webclient-contextual-hud`: Amend existing exact contracts for this travel slice.

## Impact

world/rules/movement_settlement.py::settle_movement and map_discovery.py::publish_traversal_narrative already preserve ordinary traversal prose after commit. world/rules/presentation_events.py owns publication_group/on_publication_commit; web/webclient/presentation/{alignment,push,coordinator,registry}.py fan out committed presentation. Existing raw narrative is retained for FullLogOverlay. No active sub-project1 change owns a structured travel log or travel card.

## Non-goals

No new server travel mode, client-side rules/routing, authored geography, new art, camping rules/cards, dialogue/combat redesign, compatibility or database migrations. Visual style, copy and prototype fidelity are human-reviewed against the approved interface design rather than tested as normative qualities.

## Batch:
depends-on: wilderness-travel-interface

Code-conflict notes: use this change's design.md matrix. Only direct prerequisites are machine dependencies; shared AppClient/store/protocol/docs and shard-manifest edits require serialized integration. Base adapter-path changes1-5 can ship before sub-project1; changes6-8 consume its protocols. A Batch without depends-on lines is an independent root.
