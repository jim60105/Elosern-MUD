# Proposal

## Why

Each ritual archetype ships two options. The rite document, the panel and the surfaces already support three. A third story gives the player a reason to return to a landmark, where a third distinct interaction with that landmark object exists. This change authors those third options.

It is a content-only change: it adds authored data to the shipped rite document and changes no mechanism, so it carries no specification delta.

## What Changes

- Archetypes that support a third distinct story gain a third option with its cost, its `self` scene and, where it can be shared, its `watch` scene. An archetype with no third story worth telling keeps two options; the review records why.
- The human-reviewed authoring review `docs/lore/landmark-rites-review.md` gains a section for the third options. That review is human judgement; no test asserts tone, wording or how many archetypes gained an option.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- Edits: `world/lore/rites/content/landmark_rites.yaml`, `docs/lore/landmark-rites-review.md`.
- No code, wire, test or specification change. The existing data-contract test `world.lore.tests.test_rite_content_document` keeps proving the document validates.

## Batch:

- depends-on: landmark-rite-watch-perspectives
- conflicts: none after `landmark-rite-watch-perspectives`.
