## Why

`npc-persona-editor-actions` provides the server transport and the 編輯人物設定 navigation descriptor, but nothing in the browser renders the entry or the editor. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §9, §11.1 case 10, §11.3, as amended by §13a) specifies the flow interaction target → 編輯人物設定 → editor window → save or cancel → original interaction context, with target/epoch binding, explicit state transitions, correlation, conflict and departure handling, dirty-close confirmation, accessibility, focused real-browser evidence, and user documentation. §13a adds that the NPC's per-instance offline greeting (`db.npc_offline_greeting`, owned by `npc-persona-companion-profiles`) is author-editable state like the card — an LLM-offline NPC's first line should follow the card the author edits — so this change extends the archived editor transport and ships the field in the editor.

## What Changes

- Route the `npc_persona` navigation affordance from the verb popover (`ExplorationMenu.verbMenuFor`, `use-dock.js`) to a new editor surface bound to the target identity and presentation epoch.
- **Server delta on the archived `npc-persona-editor` transport** (the actions change is already implemented; this is its single successor edit): `npc.persona.read` success data gains `offline_greeting` (the instance field verbatim, `""` when unset) and `default_greeting` (the read-only presentation default — the scripted table greeting when the NPC has one, else the authored profile greeting its provenance names, `""` otherwise, i.e. exactly what the resolver answers once the field is empty; never copied into the editable field, so table edits by content changes still reach NPCs whose field is empty). `npc.persona.update` accepts one additional optional `offline_greeting` string (≤300 code points, single paragraph after normalization; absent-or-empty clears the override). A non-empty field overrides every authored greeting source for no-keyword and degraded paths (`npc-persona-dialogue-consumption` specifies the routing); keyword responses and misunderstanding replies stay authored and are unaffected. The card and the greeting are one atomic version-checked submission: any changed component advances `persona_version`, so the archived version gate and the stale-persona exchange gate cover the field with no second counter. The browser mirror (server module + JS twin) gains the bounded-greeting rule through a shared greeting boundary fixture beside the card fixture, and the JS twin's rendering labels are corrected to the server's exact labels so the editor's capacity figures match what the server counts (the card fixture gains rendered-total parity cases).
- Add `Overlays/NpcPersonaEditor` (Vue SFC on the existing drawer frame and focus trap) and a `use-npc-persona-editor` composable implementing the loading / ready-clean / ready-dirty / saving / rejected-unavailable / conflict state machine, request correlation, reconnect re-read, target-departure and session-change handling, dirty-close confirmation, and focus return; budgets come from the browser card-contract mirror.
- Exclude `npc.persona.*` from action echo and narrative output (including the generic non-success narrative error line — the editor presents its own rejection); keep editor state out of persistent browser storage.
- Storybook story with deterministic args for every state, manifest entry, Vitest component tests, and the component-showcase governance amendment for an action-result-backed component.
- Focused browser journeys (registered in `.github/browser-shards.json`): open/save/reopen persistence on a real NPC, keyboard-only operation, dirty-close confirmation, and field-error retention; correlation, departure, puppet-change, and conflict behavior are proven here with Vitest and in the real browser by `npc-persona-editor-browser-edges`.
- Player documentation `docs/game/npc-persona-editor.md` (Traditional Chinese) and its sidebar entry.

## Capabilities

### New Capabilities

- `webclient-npc-persona-editor`: the browser NPC author editor's entry, binding, presentation, state machine, conflict/departure/session behavior, and accessibility.

### Modified Capabilities

- `npc-persona-editor` (implemented by the archived `npc-persona-editor-actions`): the read/update result gains the bounded `offline_greeting` field, the update carries it atomically with the card under the existing version check, and the contract mirror covers it.
- `webclient-component-showcase`: the frozen-set growth rule admits a component backed by a committed action-result read model, naming `Overlays/NpcPersonaEditor`.

## Impact

- Code: server — `webclient/actions/npc_persona_actions.py` (payload validators and read/update data builders), `world/rules/npc_persona.py` (the versioned update path writes card + greeting in one transaction), `world/lore/npc_card.py` (bounded single-paragraph greeting validator), the shared boundary fixture. Browser — `web/webclient-app/components/NpcPersonaEditor.vue` (new), `web/webclient-app/composables/use-npc-persona-editor.js` (new), `web/webclient-app/lib/npc_persona_card.js` (wrapper over the static mirror), `web/static/webclient/js/elosern/npc_persona_card.js` (mirror twin), `web/webclient-app/composables/use-dock.js`, `web/webclient-app/composables/use-drawers.js`, `web/webclient-app/AppClient.vue`, `web/webclient-app/stores/elosern*`, `web/static/webclient/js/elosern/exploration_menu.js`, `web/static/webclient/js/elosern/command_echo.js`, `web/webclient-app/styles/app-shell.css` (only if `.elosern-root` overrides apply), `web/webclient-app/component-manifest.json`, `web/webclient-app/stories/Overlays/`.
- Tests: Vitest under `web/webclient-app/tests/`, Node tests for `exploration_menu.js` routing and the mirror, focused Python labels on the editor-actions tests, one new browser module under `web/tests/browser/` with `.github/browser-shards.json` registration, browser fixture support for an NPC with an initialized card.
- Docs: `docs/game/npc-persona-editor.md`, `docs/_sidebar.md`.

## Batch:

depends-on: npc-persona-editor-actions
depends-on: npc-persona-companion-profiles
depends-on: npc-persona-dialogue-consumption

Code-conflict notes: sole editor in this batch of the UI router and shell files (`AppClient.vue`, `use-dock.js`, `use-drawers.js`, `exploration_menu.js`, `command_echo.js`, stores) and of `component-manifest.json` / `.github/browser-shards.json` within this batch. It is also the only active change editing the archived editor transport (`webclient/actions/npc_persona_actions.py`, the service in `world/rules/npc_persona.py`, the contract module's validator surface in `world/lore/npc_card.py`, the boundary fixture, and the JS mirror twin); `npc-persona-roster-cutover` adds a separate function to `world/rules/npc_persona.py` and never touches these transport paths. The new `depends-on` edges exist because the field contract and the offline read routing must be specified before the editor writes them; the browser fixture seeds the card and field through the persona service directly, so it does not wait for producers or the cutover. Prerequisite of `npc-persona-editor-browser-edges`.
