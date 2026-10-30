# Proposal

## Why

Provide persistent neighbour aim and commit-paced held walking through the existing guarded movement path. This delivers the approved browser travel interface without duplicating the sight/reveal rules batch.

## What Changes

- Provide persistent neighbour aim and commit-paced held walking through the existing guarded movement path.
- Add the focused behavior, production fixture/story and browser/server evidence specified in design.md and tasks.md.
- **BREAKING** Any schema cutover described in design.md replaces its prior prerelease form, with no migration or compatibility path.

## Capabilities

### New Capabilities
- `webclient-travel-walking`: Provide persistent neighbour aim and commit-paced held walking through the existing guarded movement path.

### Modified Capabilities
- `webclient-exit-compass`: Amend existing exact contracts for this travel slice.

## Impact

ExitCompass.vue currently owns hold timers and a component-local walk loop. components/compass-model.js owns aimFromKeys and resolveTargets; stores/elosern/interaction.js::activateExit re-resolves exit_ref and current_node through the common guarded activation. stores/elosern/transport.js::dispatchAction is single-flight and lastActionResult is not proof that its declared revision committed. The base change owns current map freshness.

## Non-goals

No new server travel mode, client-side rules/routing, authored geography, new art, camping rules/cards, dialogue/combat redesign, compatibility or database migrations. Visual style, copy and prototype fidelity are human-reviewed against the approved interface design rather than tested as normative qualities.

## Batch:
depends-on: wilderness-travel-interface

Code-conflict notes: use this change's design.md matrix. Only direct prerequisites are machine dependencies; shared AppClient/store/protocol/docs and shard-manifest edits require serialized integration. Base adapter-path changes1-5 can ship before sub-project1; changes6-8 consume its protocols. A Batch without depends-on lines is an independent root.
