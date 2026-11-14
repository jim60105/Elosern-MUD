# Tasks

Run only the focused commands named below, from the repository root. Vitest: `pnpm test -- <file>`. Node gate: `node --test <file>`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not edit `AppClient.vue`, `AppShell.vue`, any store, or anything under `docs/design/`.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-panel` is merged: `node -e "const p=require('./web/static/webclient/js/elosern/protocol/panels/rite.js'); if(typeof p.validateRitePanel!=='function') process.exit(1)"` exits 0. If not, stop and report.

## 2. ChoiceCard header slot

- [x] 2.1 Apply design D1 to `ChoiceCard.vue`, add the `WithHeader` story and the header test. Verify: `pnpm test -- web/webclient-app/tests/components/choice_card.test.js` passes and `pnpm test -- web/webclient-app/tests/dialogue_choices.test.js` passes.

## 3. Components

- [x] 3.1 Create `components/rite/rite-model.js` per design D2 and `stories/fixtures/rite.js` per design D6; create `tests/rite/surfaces.test.js` with the model tests of design D7. Verify: `pnpm test -- web/webclient-app/tests/rite/surfaces.test.js` passes; one of its tests passes the fixture's panel through `validateRitePanel` of `web/static/webclient/js/elosern/protocol/panels/rite.js` so the fixture can never drift from the wire shape.
- [x] 3.2 Create `RiteArrivalCard.vue` per design D3 with its tests of design D7. Verify: the same Vitest file passes.
- [x] 3.3 Create `RitePanel.vue` per design D4 with its tests of design D7. Verify: the same Vitest file passes and `pnpm test -- web/webclient-app/tests/components/choice_card.test.js` still passes.
- [ ] 3.4 Create `RiteBackdrop.vue` per design D5 with its tests of design D7. Verify: the same Vitest file passes.

## 4. Stories and guide

- [ ] 4.1 Create `stories/World/LandmarkRite.stories.js` per design D6 and add the manifest entry. Verify: `pnpm run build-storybook` succeeds and `pnpm run showcase-coverage` exits 0.
- [ ] 4.2 With Storybook running (`pnpm exec storybook dev -p 6006 --no-open`, or the instance already on port 6006), open the stories `World/LandmarkRite` `ArrivalCard`, `PanelCompanion` and `Backdrop` in a throwaway headless browser at 1451x790 and at 2560x1440 and compare each with the matching `Design/LandmarkRites` story. Verify: no text below 16px, no clipped button or row, and the layout matches the approved prototype except for the differences design D3 to D5 name; attach the six screenshots' paths to the hand-off.
- [ ] 4.3 Add the paragraph of design D8 to `web/webclient-app/AGENTS.md`. Verify: `grep -c RiteArrivalCard web/webclient-app/AGENTS.md` prints at least 1.

## 5. Gates

- [ ] 5.1 Run `pnpm test -- web/webclient-app/tests/rite web/webclient-app/tests/components`, `uv run --locked python -m unittest tests.test_webclient_frozen_contract`, `uv run --locked python -m tools.contract_gate --change landmark-rite-surfaces` and `openspec validate landmark-rite-surfaces --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the five ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
