# Tasks

Run only the focused commands named below, from the repository root. Vitest: `pnpm test -- <file>`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not edit any component, composable or `AppClient.vue`.

## 1. Preconditions

- [ ] 1.1 Confirm `landmark-rite-surfaces` is merged: `ls web/webclient-app/components/rite/rite-model.js web/webclient-app/stories/fixtures/rite.js` lists two files. If not, stop and report.

## 2. Store group

- [ ] 2.1 Create `stores/elosern/rite.js` per design D1 and compose it in `stores/elosern.js`. Create `tests/rite/store.test.js` with the arrival, transition and reset tests of design D2. Verify: `pnpm test -- web/webclient-app/tests/rite/store.test.js` passes.
- [ ] 2.2 Add the perform, adoption and centred-card tests of design D2. Verify: the same Vitest file passes.

## 3. Existing flows and gates

- [ ] 3.1 Run `pnpm test -- web/webclient-app/tests/travel` and `pnpm test -- web/webclient-app/tests/app_client_presence_rail.test.js` (two commands). Verify: each passes.
- [ ] 3.2 Run `uv run --locked python -m tools.contract_gate --change landmark-rite-store` and `openspec validate landmark-rite-store --strict`. Verify: both exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
