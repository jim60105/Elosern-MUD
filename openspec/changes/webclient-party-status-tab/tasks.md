# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration.

## 1. Status tab (3h)

- [ ] 1.1 Implement `PartyStatusTab.vue` (hero with `GradeGem`, gauges from the party row, traits, waterfall, conditions, disguise footer) and route every drawer opener to the window's 狀態 tab; verify Vitest first-layered-trait selection, waterfall order and labels, signed values, no gem without rank, condition detail, disguise with true values, combat and possession-identical rendering.

## 2. Deletion and stories (1.5h)

- [ ] 2.1 Delete `CharacterStatusDrawer.vue` and its CSS, composables, story, manifest title, tests and duplicate `.elosern-root` rules; add status stories (trait breakdown, no guild) at both sizes; run `pnpm run build-storybook` and `pnpm run showcase-coverage`.

## 3. Integration (1.5h)

- [ ] 3.1 Update `web/webclient-app/AGENTS.md`, annotate canonical IDs for the added/modified requirements, run the touched Vitest files, `tests.test_webclient_frozen_contract`, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-party-status-tab --strict`.
