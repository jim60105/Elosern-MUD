# Proposal

## Why

`landmark-rite-content` ships five of the ten ritual archetypes and assigns the districts of the other five landmark families provisionally. This change authors the remaining five archetypes and gives every district its final archetype, before any player can reach a rite.

It is a content-only change: it adds authored data to the shipped rite document and changes no mechanism, so it carries no specification delta.

## What Changes

- The shipped rite document gains the archetypes `grave`, `mine`, `gate`, `cliff` and `plaza`, two options each, one `self` scene per option, `watch: null`.
- Every provisional district assignment is replaced by its final archetype; the one city landmark takes `plaza`.
- The human-reviewed authoring review `docs/lore/landmark-rites-review.md` gains the five archetypes' sections. That review is human judgement; no test asserts tone, wording or counts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- Edits: `world/lore/rites/content/landmark_rites.yaml`, `docs/lore/landmark-rites-review.md`.
- No code, wire, test or specification change. The existing data-contract test `world.lore.tests.test_rite_content_document` keeps proving the document validates.

## Batch:

- depends-on: landmark-rite-content
- conflicts: `landmark-rite-watch-perspectives` and `landmark-rite-third-option` edit the same two files; they run after this change.
- parallel with: `landmark-rite-settlement`.
