# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md` §3, §5.3, §5.4 (compass part), §7, §8 (compass part). The prototype `docs/design/scene-overview-redesign/compass-model.js` is the reference implementation of the §3.1 and §3.5 rules; where the spec and prototype disagree, the spec wins. `web/webclient-app/AGENTS.md` governs: desktop 16:9 only, ship through OpenSpec, grep `styles/app-shell.css` for `.elosern-root` duplicates when restyling, verify geometry in the live client.

Observed today:
- `ExplorationMenu.overviewMenu(panel, {currentNode, suggestions})` flattens 出口 (from `moveItems`), 人物, 物件, and the footer into one menu with `geometry: "sections"`; `frame-resolvers.js` serves it as `exploration.root`; `SceneOverview.vue` renders it as chips; activation is `onDockActivate` -> `store.focusConfirm("pointer")` after `store.focusItemByKey(key)`.
- `moveItems` already disables every exit while `current_node` is missing (reason `地圖資料尚未同步。`) and carries the unchanged `explore.move` payload `{exit_ref, current_node}`.
- `dock-exits.js` holds `directionGlyph`, `exitLabel`, and `DIRECTION_ALIASES`-based normalization (`ExplorationMenu.normalizeDirection`).
- `LocalMap.remoteDirection` is the minimap's bearing formula.
- `ActionDock.vue` renders a permanent `action-dock__legend` key hint in every non-creation mode.

## Goals / Non-Goals

**Goals:**
- Exits are chosen on a compass by bearing; the payload and the server's gate are untouched.
- The model is pure and exhaustively unit-tested; the component is thin.
- The client is fully working after this change alone.

**Non-Goals:**
- Presence rail, `ChoiceCard`, place-card buttons, wait and suggestions cards, the 建議 pill relocation, removal of `SceneOverview`: changes 2 and 3.

## Decisions

### D1. Pure model, copied from the prototype and re-verified

`compass-model.js` exports `resolveTargets`, `snapAngled`, `snapPortal`, `aimFromPointer`, `aimFromKeys`, `nextStep`, and `SNAP_TOLERANCE = 30`, `DEAD_ZONE = 0.2`, `HOLD_MS = 400`, `STEP_DWELL_MS = 350`. The input is the already-built exit rows (`moveItems` output) plus the committed `localMapModel`; the output carries, per exit, `{item, kind: "angled"|"portal", angle|slot, glyph, label, enabled, reason}`. Direction normalization reuses `ExplorationMenu.normalizeDirection` (up and down are excluded from angled). The bearing formula is shared with `LocalMap.remoteDirection` by extracting it to one helper (or importing it) so the two can never drift; a test asserts equality over a coordinate grid.

### D2. Exit rows leave the router root; the compass submits through the store gate

Alternative A (rejected): keep exit items in the router root and make `SceneOverview` skip them. It leaves invisible focusable items and sections whose counts disagree with what is rendered.
Chosen: `overviewMenu` no longer adds the exits section (so `sections` is people, objects, footer and `geometry: "sections"` stays valid for the interim rows), and a new builder returns the `moveItems` rows for the compass. Activation calls one new store method that runs the same submission gate as `focusConfirm` (in-flight, awaiting presentation revision, connection lock, disabled item) with the row re-resolved at the moment of activation, so stale or duplicate input cannot submit. The worker locates the gate the store uses behind `focusConfirm` and factors it; no second gate is written. The compass is a separate tab stop outside the router's root menu; its key handler consumes its keys so the router never sees them. If the plugin-level router binding requires the dock element to hold DOM focus, the compass lives inside the dock element and stops propagation of the keys it owns.

### D3. Continuous movement is driven by commits

`ExitCompass` keeps the live aim angle and a `walking` flag. It subscribes to the committed exploration panel identity (the same watcher key the dock uses to close child frames on a location change). After an arrival commit it schedules the next step no sooner than `STEP_DWELL_MS` after the previous send, calls `nextStep(targets, aimAngle)`, and either sends or stops with a reason. One move in flight is enforced by the store gate, and the compass additionally ignores timers while the gate reports in-flight. A rejection is observed through the store's existing action feedback (the rejection message used by the toast); the walk stops and the readout shows that message.

### D4. Readout is a small shared component

`ExplorationReadout.vue` takes `{lead, text, tone}` and a `flash` prop; the pane owns a tiny local state (`aim` from the compass, `flash` from a blocked move) and computes the final content by priority: flash, aim, idle. Changes 2 and 3 extend the same component with rail, place-card, and pill sources; the priority function lives in one pure helper so they only add sources. This change implements flash, compass aim, and idle.

### D5. Layout in the 1/3 command panel

The compass fills the panel height on the left (pad about 198 px at 1451×790 with `--ui-scale`). The right column stacks the readout, then the interim `SceneOverview` (人物 / 物件 / footer chips) below it, scrolling inside the column exactly as the overview scrolls inside the pane today. The panel's box does not change, so the message window never jumps. The permanent legend is dropped in exploration only; dialogue and combat keep theirs.

### D6. Minimap aim highlight is optional-prop plumbing

`LocalMap.vue` gains an optional `aimedNode` prop that adds a highlight class to the matching node. The aim lives in a small store-free ref owned by the pane and passed to the minimap host in `AppClient.vue`. It is presentation only and absent when no aim.

### D9. The dialogue exits list gets its own source

`DialogueChoices`' `↦ 移動…` view is fed by `dialogueExits`, which slices the `exits` section out of the router root (`overviewExits(store.view.rootMenu)`). Removing exits from `overviewMenu` would silently empty it, and change 3 empties the whole root. Dialogue therefore reads the `moveItems` rows through a dedicated store view field that does not depend on the router root, with the payload and echo descriptor unchanged (design doc §9 keeps this list as it is).

### D10. Press, key, and stop rules

A discrete move is sent on pointer release (or on keydown for Enter) only when the press was shorter than `HOLD_MS`; a held press or key never also produces a discrete move, so release after a walk sends nothing. Additional stop reasons: the gate suppressed the step (in-flight or awaiting revision at the arrival commit: wait for the next commit, stop after a bounded wait), a move result arrives with no panel change (stop with the result message), Escape (clears the aim and stops), and any drawer or card opening. The compass element stops propagation of the arrow, Enter, Space, `[`, and `]` keys; digits, Escape-with-no-aim, and `/` still bubble to the router. A Vitest check asserts the consumed keys never reach the document-level keyboard bridge.

### D7. Styling

Tokens from `styles/tokens.css`, sizes `calc(<n>px * var(--ui-scale))`, nothing below `--text-xs`. Before restyling `.action-dock*` or `.scene-overview*` classes, grep `styles/app-shell.css` for `.elosern-root` duplicates and update them in the same commit.

## Risks / Trade-offs

- **Hold and keyboard focus.** The compass is a second tab stop beside the dock listbox. Mitigation: entering exploration focuses the compass (spec §5.4), Tab reaches the overview rows, and a Vitest plus a browser journey cover both.
- **Test and spec drift.** Several Vitest files and browser helpers activate `exit-<exit_ref>` chips. Mitigation: the tasks list them; browser helper `activate first exit` becomes a compass keyboard activation.
- **Requirement text spread across capabilities.** `webclient-desktop-shell` (the dock-surface, keyboard-routing, and action-dock row-region requirements) and `webclient-pointer-activation` mention the scene overview, exit chips, and the key-hint legend. This delta modifies the `webclient-exploration-menu` root requirement; task 6.2 authors the remaining MODIFIED deltas for those requirements with `openspec validate` as the guard, because they must copy whole requirement blocks.
- **Aim feel in a headless environment.** Pointer geometry is tested with synthetic events in Vitest, but the feel (hover, hold) is only judged in the live client; task 7 requires screenshots at both viewports.

## Open Questions

None blocking. The exact location of the store's submission gate is resolved by reading `stores/elosern*.js` at the start of task 3.1.
