# Tasks

Run only the focused commands named below, from the repository root. Vitest: `pnpm test -- <file>`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not edit `AppShell.vue`, `HudFrame.vue`, `MessageWindow.vue`, `CompanionLineup.vue`, `LandmarkCard.vue` or `stores/elosern/rite.js`.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-store` is merged: `ls web/webclient-app/stores/elosern/rite.js web/webclient-app/tests/rite/store.test.js web/webclient-app/components/rite/RitePanel.vue` lists three files. If not, stop and report.

## 2. Composable and entry

- [x] 2.1 Create `composables/use-rite-stage.js` per design D2 and `components/rite/RiteEntry.vue` with its story per design D4. Verify: `pnpm test -- web/webclient-app/tests/rite` passes.

## 3. Shell

- [x] 3.1 Apply the card, entry and R-key bindings of design D3 and D4 (`landmarkCardOpen`, `:card-open`, the `RiteArrivalCard` branch, `RiteEntry`, the arrival dismissal watch, the hotkey). Create `tests/app_client_rite.test.js` with the arrival, leave, return-entry and priority tests of design D5. Verify: `pnpm test -- web/webclient-app/tests/app_client_rite.test.js` passes.
- [x] 3.2 Apply the stage bindings of design D3 (`:mode` and the other `AppShell` props, `#backdrop`, `#actor-left`, the `RitePanel` branch, the `ActionDock` condition, focus on leave) and add the stage, dispatch, playback and withdrawal tests of design D5. Verify: the same Vitest file passes.
- [x] 3.3 Run, one command each: `pnpm test -- web/webclient-app/tests/travel`, `pnpm test -- web/webclient-app/tests/app_client_dialogue_choices.test.js`, `pnpm test -- web/webclient-app/tests/app_client_sleep_handoff.test.js`, `pnpm test -- web/webclient-app/tests/app_client_stage_actor.test.js`, `pnpm test -- web/webclient-app/tests/mode_transitions.test.js`. Verify: each passes.
- [x] 3.4 Extend `web/webclient-app/AGENTS.md` per design D6. Verify: `grep -c use-rite-stage web/webclient-app/AGENTS.md` prints at least 1.

## 4. Gates

- [x] 4.1 Run `pnpm run build-storybook` then `pnpm run showcase-coverage`, `uv run --locked python -m tools.contract_gate --change landmark-rite-stage` and `openspec validate landmark-rite-stage --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the six ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
