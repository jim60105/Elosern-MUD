# Proposal

## Why

Every shipped rite option declares `watch: null`, so only the player's own character can perform a rite. The settlement, the action, the panel and the stage's performer picking all support a companion performer once an option declares a watch scene. This change authors the watch scenes, which makes companion rites and performer picking reachable in the live game.

It is a content-only change: it adds authored data to the shipped rite document and changes no mechanism, so it carries no specification delta.

## What Changes

- Every shipped option whose ritual can be performed by a companion gains a `watch` scene: third person, naming the companion only through the `{name}` placeholder, using neither 她 nor 他.
- An option that stays solo-only keeps `watch: null`, with its reason recorded in the review document.
- The human-reviewed authoring review `docs/lore/landmark-rites-review.md` gains a watch-perspective section. That review is human judgement; no test asserts tone, wording, pronouns or counts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- Edits: `world/lore/rites/content/landmark_rites.yaml`, `docs/lore/landmark-rites-review.md`.
- No code, wire, test or specification change. The existing data-contract test `world.lore.tests.test_rite_content_document` keeps proving the document validates.

## Batch:

- depends-on: landmark-rite-performer-picking
- conflicts: `landmark-rite-third-option` edits the same two files; it runs after this change.
- parallel with: `landmark-rite-lighting`, `landmark-rite-arrival-signal-removal`, `landmark-rite-art`.
