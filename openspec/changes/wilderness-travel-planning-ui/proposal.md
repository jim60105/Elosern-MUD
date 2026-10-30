# Proposal

## Why

Add destination input, debounced current-only route queries and server-authored route/gauge previews. This delivers the approved browser travel interface without duplicating the sight/reveal rules batch.

## What Changes

- Add destination input, debounced current-only route queries and server-authored route/gauge previews.
- Add the focused behavior, production fixture/story and browser/server evidence specified in design.md and tasks.md.
- **BREAKING** Any schema cutover described in design.md replaces its prior prerelease form, with no migration or compatibility path.

## Capabilities

### New Capabilities
- `webclient-travel-route-preview`: Add destination input, debounced current-only route queries and server-authored route/gauge previews.

### Modified Capabilities
None.

## Impact

wilderness-travel-planning exclusively owns travel.plan registration, read-only routing, durations/stages, domain errors and result schema. It returns result-only no_presentation outcomes through existing dispatcher support. This slice owns browser request lifecycle and preview only. Route departure is enabled by route-ui after interrupts; no premature multi-step execution is introduced. LegPanel and shared grid/camera are already usable after their prerequisites.

## Non-goals

No new server travel mode, client-side rules/routing, authored geography, new art, camping rules/cards, dialogue/combat redesign, compatibility or database migrations. Visual style, copy and prototype fidelity are human-reviewed against the approved interface design rather than tested as normative qualities.

## Batch:
depends-on: wilderness-travel-leg-ui
depends-on: wilderness-travel-window-ui
depends-on: wilderness-travel-planning

Code-conflict notes: use this change's design.md matrix. Only direct prerequisites are machine dependencies; shared AppClient/store/protocol/docs and shard-manifest edits require serialized integration. Base adapter-path changes1-5 can ship before sub-project1; changes6-8 consume its protocols. A Batch without depends-on lines is an independent root.
