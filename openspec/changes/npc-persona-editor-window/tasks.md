Apply on branch `feat/npc-persona-editor-window` in worktree `.worktrees/npc-persona-editor-window`. Browser tests: run ONE selected method per command with `uv run --locked python -m web.tests.browser.unittest_driver <module>.<Class>.<test>`, output captured to a scratch file; never chain whole files. JS: `pnpm test -- <file>`, `node --test <file>`.

## 1. Entry routing

- [ ] 1.1 Map the `npc_persona` navigation surface in `exploration_menu.js::verbMenuFor` and `use-dock.js` to open the editor bound to the target (design D1), add `npc_persona` to the store's drawer-name set and the open-surface registry; verify Node tests for the verb-menu row (label, enabled/disabled reason) and a Vitest that activation opens the editor and dispatches exactly one read for the bound id.
- [ ] 1.2 Register `npc.persona.read`/`npc.persona.update` as silent in `command_echo.js` (design D6); verify a Node test that no echo line is produced.

## 2. Component and state machine

- [ ] 2.1 Create `web/webclient-app/lib/npc_persona_card.js` (wrapper) and `use-npc-persona-editor.js` implementing design D2/D3; verify Vitest cases: late read for a closed/other editor ignored, double save dispatches once, rejected save keeps draft and focuses the field, conflict keeps draft and reload re-reads, transport loss makes no claim and resync re-reads, departure enters unavailable with save disabled and recovers, puppet change clears, snapshot refresh never replaces the draft, no persistent storage writes.
- [ ] 2.2 Create `NpcPersonaEditor.vue` on `HudDrawer`/`DrawerHeader` and `lib/focus-trap.js` (design D4/D5): heading with name/title, two notices, seven labeled controls with public/hidden identity split, required/optional marks, per-control and total budgets, live region, dirty-close confirmation, focus return; verify Vitest accessibility assertions (dialog name, labels, focus containment, announced errors) and that text renders as plain text.
- [ ] 2.3 Mount the editor in `AppClient.vue` via `use-drawers.js` only after task 3.1's story exists; grep `web/webclient-app/styles/app-shell.css` for every reused class and update `.elosern-root` duplicates; verify `pnpm run build`.

## 3. Showcase

- [ ] 3.1 Add `Overlays/NpcPersonaEditor` stories with deterministic offline args for every state in design D7 and the manifest title; verify `pnpm run build-storybook` and `pnpm run showcase-coverage`.

## 4. Browser evidence

- [ ] 4.1 Add a seed fixture placing the browser actor beside an NPC with a card initialized through the persona service; verify the seed runs through the existing seed runner.
- [ ] 4.2 Write `web/tests/browser/test_browser_npc_persona_editor.py` per design D7 and register every new method in `.github/browser-shards.json`; run each method once locally in its own command; verify `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` (with `MUD_TEST_SETTINGS=1` via the Bash tool's `env` input) and `tests.test_webclient_frozen_contract` pass.

## 5. Docs and gates

- [ ] 5.1 Write `docs/game/npc-persona-editor.md` in Traditional Chinese (how to open 編輯人物設定, what each field means, required vs optional, budgets, the spoiler notice, that scripted lines and portraits are not regenerated, conflicts and why an entry can be disabled) and add it to `docs/_sidebar.md`.
- [ ] 5.2 Run `pnpm test`, `node --test web/static/webclient/js/tests/*.test.js`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage`; sync the deltas (new `webclient-npc-persona-editor`, MODIFIED `webclient-component-showcase`) into `openspec/specs/`, annotate browser/Vitest-evidence tests with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-editor-window --strict`.
