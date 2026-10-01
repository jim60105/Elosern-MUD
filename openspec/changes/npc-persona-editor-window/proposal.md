## Why

`npc-persona-editor-actions` provides the server transport and the 編輯人物設定 navigation descriptor, but nothing in the browser renders the entry or the editor. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §9, §11.1 case 10, §11.3) specifies the flow interaction target → 編輯人物設定 → editor window → save or cancel → original interaction context, with target/epoch binding, explicit state transitions, correlation, conflict and departure handling, dirty-close confirmation, accessibility, focused real-browser evidence, and user documentation.

## What Changes

- Route the `npc_persona` navigation affordance from the verb popover (`ExplorationMenu.verbMenuFor`, `use-dock.js`) to a new editor surface bound to the target identity and presentation epoch.
- Add `Overlays/NpcPersonaEditor` (Vue SFC on the existing drawer frame and focus trap) and a `use-npc-persona-editor` composable implementing the loading / ready-clean / ready-dirty / saving / rejected-unavailable / conflict state machine, request correlation, reconnect re-read, target-departure and session-change handling, dirty-close confirmation, and focus return; budgets come from the browser card-contract mirror.
- Exclude `npc.persona.*` from action echo and narrative output; keep editor state out of persistent browser storage.
- Storybook story with deterministic args for every state, manifest entry, Vitest component tests, and the component-showcase governance amendment for an action-result-backed component.
- Focused browser journeys (registered in `.github/browser-shards.json`): open/save/reopen persistence on a real NPC, keyboard-only operation, dirty-close confirmation, and field-error retention; correlation, departure, puppet-change, and conflict behavior are proven here with Vitest and in the real browser by `npc-persona-editor-browser-edges`.
- Player documentation `docs/game/npc-persona-editor.md` (Traditional Chinese) and its sidebar entry.

## Capabilities

### New Capabilities

- `webclient-npc-persona-editor`: the browser NPC author editor's entry, binding, presentation, state machine, conflict/departure/session behavior, and accessibility.

### Modified Capabilities

- `webclient-component-showcase`: the frozen-set growth rule admits a component backed by a committed action-result read model, naming `Overlays/NpcPersonaEditor`.

## Impact

- Code: `web/webclient-app/components/NpcPersonaEditor.vue` (new), `web/webclient-app/composables/use-npc-persona-editor.js` (new), `web/webclient-app/lib/npc_persona_card.js` (wrapper over the static mirror), `web/webclient-app/composables/use-dock.js`, `web/webclient-app/composables/use-drawers.js`, `web/webclient-app/AppClient.vue`, `web/webclient-app/stores/elosern*`, `web/static/webclient/js/elosern/exploration_menu.js`, `web/static/webclient/js/elosern/command_echo.js`, `web/webclient-app/styles/app-shell.css` (only if `.elosern-root` overrides apply), `web/webclient-app/component-manifest.json`, `web/webclient-app/stories/Overlays/`.
- Tests: Vitest under `web/webclient-app/tests/`, Node tests for `exploration_menu.js` routing, one new browser module under `web/tests/browser/` with `.github/browser-shards.json` registration, browser fixture support for an NPC with an initialized card.
- Docs: `docs/game/npc-persona-editor.md`, `docs/_sidebar.md`.

## Batch:

depends-on: npc-persona-editor-actions

Code-conflict notes: sole editor in this batch of the UI router and shell files (`AppClient.vue`, `use-dock.js`, `use-drawers.js`, `exploration_menu.js`, `command_echo.js`, stores) and of `component-manifest.json` / `.github/browser-shards.json` within this batch. No other NPC persona change edits webclient-app files, so it can run in parallel with every content, producer, and cutover change once the actions change is applied. Prerequisite of `npc-persona-editor-browser-edges`. Its browser fixture initializes a card through the persona service directly, so it does not wait for producers or the cutover; shipped NPCs become editable as soon as their cards exist.
