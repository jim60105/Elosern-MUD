# Proposal

## Why

The landmark rite interface was approved on 2026-11-14 from the Storybook prototype `Design/LandmarkRites` (`docs/design/landmark-rites/`; design `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.2). It adds two new surfaces to the webclient: the rite arrival card and the rite panel on the AVG stage, plus the stage's backdrop. The prototype uses mock data and imports from `docs/`. This change turns its three presentational pieces into production components that read the committed `rite` panel shape, so the shell integration that follows composes tested components and does not design anything.

No player-visible change: the components are mounted nowhere yet.

## What Changes

- `ChoiceCard` gains a `header` slot inside its frame, above its rows.
- New `RiteArrivalCard`: the archetype art band, the kicker, the landmark, the district's lit state, the guardian's name and form, the experienced count, and the two buttons 退開 (Escape) and 走近 (Enter). It renders no scene prose and sends nothing.
- New `RitePanel`: the shared `ChoiceCard` with one digit row per option, a not-yet-experienced mark, 退開 under the hairline, and a header naming the performer. An option that does not admit a companion is disabled with its reason while a companion performs.
- New `RiteBackdrop`: the archetype art full-bleed under an ink wash with a plate naming the landmark and guardian; quiet ink without art.
- Storybook stories and Vitest component tests for all four.

## Capabilities

### New Capabilities

- `webclient-landmark-rite`: the webclient's landmark rite surfaces and their behaviour.

### Modified Capabilities

- `webclient-presence-rail`: `ChoiceCard` (owned by this capability) gains a header slot.

## Impact

- New: `web/webclient-app/components/rite/RiteArrivalCard.vue`, `RitePanel.vue`, `RiteBackdrop.vue`, `rite-model.js`; `web/webclient-app/stories/World/LandmarkRite.stories.js`; `web/webclient-app/stories/fixtures/rite.js`; `web/webclient-app/tests/rite/surfaces.test.js`.
- Edits: `web/webclient-app/components/ChoiceCard.vue` (slot), `web/webclient-app/tests/components/choice_card.test.js`, `web/webclient-app/stories/Core/ChoiceCard.stories.js`, `web/webclient-app/component-manifest.json`, `web/webclient-app/AGENTS.md` (one paragraph on the rite surfaces).
- The prototype under `docs/design/landmark-rites/` stays as the approved reference and is not edited.

## Batch:

- depends-on: landmark-rite-panel
- conflicts: `landmark-rite-stage` and `landmark-rite-performer-picking` edit `RitePanel.vue` and the story file; they run after this change and serially.
- parallel with: `landmark-rite-art` (no shared file).
