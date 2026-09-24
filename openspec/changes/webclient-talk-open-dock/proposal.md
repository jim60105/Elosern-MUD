## Why

After `explore-talk-open-action` (C9a), 交談 in the verb popover dispatches `explore.talk_open` and the conversation opens with one press (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §2 item 6, §8.1). C9a changed only the one client branch that the v3 wire forced. It left three things behind in the dock:
- Dead code. The keyword frame (`keywordMenuFor`, `scriptedAffordanceFor`, the `exploration.keywords` source), the popover freeform borrow (the `openKeywords` and `freeform` branches of `handleExplorationItem`), and the `nav` pane kind whose last producer was the keyword frame. The validator now rejects every payload that could feed them.
- An orphan. The `affordance` pane kind of `DockMenu` has had no producer since C8b (`webclient-scene-overview-swap`) moved target menus into `DockVerbPopover`, and no change in the series deletes it.
- A flow gap. The verb popover stays open over the conversation after a successful open, because dialogue mode keeps the exploration form.

This change (C9b) deletes the dead code and both pane kinds, returns the dock to the overview when a conversation opens, and restates the dock's specs so 交談 is one step and the dock offers no keyword list and no borrow. The project is unreleased, so the old paths are removed, not kept.

**Implementation profile:** logic — client deletions and one frame-stack rule; Node, Vitest, and browser tests fully decide correctness, and no layout or styling is designed.

## What Changes

- **Exploration menu.** `web/static/webclient/js/elosern/exploration_menu.js` deletes `keywordMenuFor`, `scriptedAffordanceFor`, and both exports, and rewrites the header comment (no "scripted keyword buttons, free-form dialogue").
- **Frames and store.**
  - `web/webclient-app/stores/frame-resolvers.js` deletes the `exploration.keywords` source. It becomes an unregistered source, so a stray push pops, as in C8c D2.
  - `stores/elosern/frames.js` drops `exploration.keywords` from the `gridCols = 1` list. `settleFrameStack` gains one more rule: when the committed mode turns `dialogue`, the stack resets to the overview (design D1).
  - `stores/elosern/interaction.js` `handleExplorationItem` deletes the `openKeywords` and `freeform` branches. The dialogue variant's free row keeps `borrowDialogueCommand`.
  - `stores/elosern/combat.js` `fillDisplayFor` adds `explore.talk_open` to its `npcLabel` family, so a dispatch without a row descriptor still echoes `talk <NPC>` (C9a added the resolver).
  - `stores/dialogue-view.js`: the header comment stops citing `keywordMenuFor`.
- **Dock panes.** `web/webclient-app/components/dock-panes.js` `classifyPane` deletes the `nav` kind (the `kw-*`, all-look, and `target-*` clauses) and the `affordance` kind (the `explore.engage` / `explore.party_invite` / `explore.talk_freeform` test). `components/DockMenu.vue` deletes:
  - the `nav` template, its `dock-menu__nav*` CSS, the `nav` `sizeFn` branch, and the `openKeywords` chevron clause
  - the `affordance` template (`dock-menu__aff*` markup and CSS) and the `targetName` prop, whose only reader was the affordance head
  - the header comment's two pane kinds

  `web/webclient-app/AppClient.vue` drops the `:target-name` binding on `DockMenu`.
- **Stories.** `web/webclient-app/stories/Action/DockMenu.stories.js`: delete or re-point any story whose rows classify as `nav` or `affordance`. No component is added or deleted, so the manifest is unchanged.
- **Tests.**
  - Node: delete the `keywordMenuFor` / `scriptedAffordanceFor` cases; rename the synthetic `exploration.keywords` source in `keyboard_router_declarative.test.js`.
  - Vitest: resolvers (the keyword source is unregistered), panes (no `nav`, no `affordance`), DockMenu, the D1 reset, the dialogue store and dock (the popover closed), and the echo surfaces (the popover row and the central fill).
  - Browser: a new one-step keyboard journey, the dock-at-overview assertions in the dialogue journeys, the services docstring, and the contextual-hud dock journey's nav-row assertions.

Out of scope:
- The server action, exploration panel v3, the client protocol mirror, the echo resolver, and the `targetMenuFor` talk branch: `explore-talk-open-action` (C9a).
- The dialogue stage layout, the dock collapse in dialogue mode, and paging the dialogue line: C10b (`webclient-dialogue-stage-actors`) and C10c (`webclient-dialogue-choices-overlay`).
- The fixed-column sizing of the combat panes (see design Risks).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-exploration-menu`:
  - REMOVED "The exploration dock is keyboard-first and roots at the scene overview" (C8b's text).
  - ADDED "The keyboard-first exploration dock roots at the scene overview and opens dialogue directly".
- `webclient-contextual-hud`, both on C8c's text:
  - MODIFIED "Dock panes render a per-kind vocabulary from backed fields only": no keyword navigation rows.
  - MODIFIED "A fixed-column dock pane sizes its columns to content": the scenario names the combat panes instead of a nav pane.
- `webclient-pointer-activation`: MODIFIED, on C8c's text, "Every action-dock surface renders exactly the keyboard router's current menu frame". The form list loses the navigation row and the affordance row.

## Impact

- Client source:
  - `web/static/webclient/js/elosern/exploration_menu.js`
  - `web/webclient-app/stores/frame-resolvers.js`, `stores/elosern/{frames,interaction,combat}.js`, `stores/dialogue-view.js` (comment)
  - `web/webclient-app/components/dock-panes.js`, `components/DockMenu.vue`, `AppClient.vue` (one binding)
  - `web/webclient-app/stories/Action/DockMenu.stories.js`
- Node tests: `web/static/webclient/js/tests/{exploration_menu,keyboard_router_declarative}.test.js`.
- Vitest (under `web/webclient-app/`): `tests/frame-resolvers.test.js`, `tests/components/dock_panes.test.js`, `tests/action/{dock_menu,dock_menu_panes}.test.js`, `tests/store/{declarative_frames,command_echo_surfaces}.test.js`, `tests/{dialogue_store,dialogue_dock}.test.js`.
- Browser: `web/tests/browser/test_browser_exploration_dialogue.py`, `test_browser_exploration_nav.py`, `test_browser_exploration_state.py`, `test_browser_exploration_tiles.py`, `test_browser_exploration_actions.py` (re-anchor only), `test_browser_services_base.py`, `test_browser_contextual_hud_dock.py`.
- Spec traceability: the C8b exploration-dock ID moves to the new dock ID in the files C8b, C8c, and C9a anchored to it (including `web/webclient/tests/test_node_suite_evidence.py`).
- Dependencies: archive order C8c (`webclient-retire-exploration-submenus`) → C9a (`explore-talk-open-action`) → C9b (this change) → C10a (`dialogue-panel-host-portrait`). The contextual-hud and pointer-activation blocks are written on C8c's text, and the dock requirement replaces C8b's.
