# Proposal

## Why

Execute locked plans through the commit/dwell queue, consume every server interrupt and present landmark arrival cards. This delivers the approved browser travel interface without duplicating the sight/reveal rules batch.

## What Changes

- Execute locked plans through the commit/dwell queue, consume every server interrupt and present landmark arrival cards.
- Add the focused behavior, production fixture/story and browser/server evidence specified in design.md and tasks.md.
- Include the lifecycle/privacy/terminal-state corrections recorded in design.md under Blocking review disposition; they remain inside this slice's declared mechanisms.
- **BREAKING** Any schema cutover described in design.md replaces its prior prerelease form, with no migration or compatibility path.

## Capabilities

### New Capabilities
- `webclient-travel-route-walking`: Execute locked plans through the commit/dwell queue, consume every server interrupt and present landmark arrival cards.

### Modified Capabilities
None.

## Impact

wilderness-travel-interrupts exclusively owns the exact optional walk payload, committed interrupt flags, before/after comparison and movement collector. planning-ui owns the exact query and preview; walking-ui owns one pending step and commit/dwell timing. travel_events owns typed notices, while window-ui enriches their canonical observation inputs. Existing AppClient choices ordering already prioritizes sleep handoff/dream/dialogue/combat; landmark cards must join that host without replacing higher-priority flows.

## Non-goals

No new server travel mode, client-side rules/routing, authored geography, new art, camping rules/cards, dialogue/combat redesign, compatibility or database migrations. Visual style, copy and prototype fidelity are human-reviewed against the approved interface design rather than tested as normative qualities.

## Batch:
depends-on: wilderness-travel-planning-ui
depends-on: wilderness-travel-interrupts

Code-conflict notes: use this change's design.md matrix. Only direct prerequisites are machine dependencies; shared AppClient/store/protocol/docs and shard-manifest edits require serialized integration. Base adapter-path changes1-5 can ship before sub-project1; changes6-8 consume its protocols. A Batch without depends-on lines is an independent root.
