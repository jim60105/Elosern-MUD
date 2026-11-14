# Tasks

Run only the focused commands named below, from the repository root. Vitest: `pnpm test -- <file>`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not edit `CompanionLineup.vue`, `ChoiceCard.vue` or any server file. Tests use synthetic panels.

## 1. Preconditions

- [ ] 1.1 Confirm `landmark-rite-stage` is merged: `ls web/webclient-app/stores/elosern/rite.js web/webclient-app/composables/use-rite-stage.js web/webclient-app/tests/app_client_rite.test.js` lists three files. If not, stop and report.

## 2. Store and panel

- [ ] 2.1 Apply design D1 to `stores/elosern/rite.js` with the store tests of design D6. Verify: `pnpm test -- web/webclient-app/tests/rite/store.test.js` passes.
- [ ] 2.2 Apply design D4 to `RitePanel.vue` and design D5 to the stories, with the surface tests of design D6. Verify: `pnpm test -- web/webclient-app/tests/rite/surfaces.test.js` passes.

## 3. Stage

- [ ] 3.1 Apply design D2 to `use-rite-stage.js` and design D3 to `AppClient.vue`, with the app tests of design D6. Verify: `pnpm test -- web/webclient-app/tests/app_client_rite.test.js` passes.
- [ ] 3.2 Run, one command each: `pnpm test -- web/webclient-app/tests/core/companion_lineup.test.js`, `pnpm test -- web/webclient-app/tests/app_client_stage_actor.test.js`, and the Vitest file found by `grep -ln stageTargetPointer web/webclient-app/tests/*.test.js web/webclient-app/tests/*/*.test.js` that mounts the client in combat (run each found file, at most three). Verify: each passes.
- [ ] 3.3 Add the sentences of design D7 to `web/webclient-app/AGENTS.md`. Verify: `grep -c "performer" web/webclient-app/AGENTS.md` prints at least 1.

## 4. Gates

- [ ] 4.1 Run `pnpm run build-storybook` then `pnpm run showcase-coverage`, `uv run --locked python -m unittest tests.test_webclient_frozen_contract`, `uv run --locked python -m tools.contract_gate --change landmark-rite-performer-picking` and `openspec validate landmark-rite-performer-picking --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
