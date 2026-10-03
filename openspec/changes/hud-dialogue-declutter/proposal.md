# hud-dialogue-declutter

## Why

During dialogue, the player's attention is entirely on the conversation: reading lines, choosing responses, and watching the host's portrait. The vitals dock (HP/MP/SP bars and condition icons), the place card, and the minimap are cockpit and navigation surfaces that carry no information relevant to the dialogue flow. Keeping them visible adds clutter and weakens the AVG visual focus the stage design aims for.

## What Changes

- **Dialogue mode hides the vitals dock.** The `[data-anchor="vitals"]` anchor (the bottom-left dock carrying condition icons and HP/MP/SP bars) is hidden when the committed mode is `dialogue`, using the same hide mechanism the creation mode uses (the HIDDEN_BY_MODE selector set). If the vitals dock is visible when the mode changes to dialogue, it exits with its reveal transition; if a vital or condition needs attention during dialogue, the dock does NOT appear. This is a deliberate choice: the dialogue's message window can announce combat-relevant events if needed, and the player re-enters exploration (where the dock appears) when the dialogue ends.
- **Dialogue mode hides the map anchor.** The `[data-anchor="map"]` anchor (the right-side column carrying the place card above the minimap, the objective line, and any mounted islands) is hidden when the committed mode is `dialogue`, using the same hide mechanism. The location is narratively conveyed in the dialogue text; the minimap is navigation-only.
- **Standing portraits stay visible.** The player's portrait, companion lineup, and dialogue host portrait are NOT hidden — they are core AVG visual elements during dialogue, not cockpit data surfaces.
- **Existing dialogue surfaces are unchanged.** The message window (full band width, name plate, paged), the choice list (centred over the stage after the last page), the command-line toggle, the log control, and the scene backdrop all keep their current dialogue visibility.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `webclient-contextual-hud`: the visibility-matrix requirement updates the dialogue column for the vitals dock row (hidden instead of "by the vitals rule"), the place card row (hidden instead of visible), and the minimap row (hidden instead of visible). The map anchor's mode-hide CSS rule is amended to include dialogue alongside creation.

## Impact

- `web/webclient-app/components/HudFrame.vue`: dialogue-mode hide rule for `[data-anchor="vitals"]` and `[data-anchor="map"]` (CSS: `.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="vitals"], .elosern-stage[data-elosern-mode="dialogue"] [data-anchor="map"] { display: none !important; }`).
- `web/webclient-app/styles/app-shell.css`: mirrored hide rule if the file repeats anchor mode hides.
- `web/webclient-app/components/AppShell.vue`: extend the existing pre-flush dialogue focus-rescue selector to both outgoing anchors.
- `web/webclient-app/AppClient.vue`: forward mode-gated effective visibility to the dock so its existing reveal is suppressed during dialogue and restored on exit.
- Tests: update `scene_transitions.test.js` or `mode_visibility.test.js` assertions for the dialogue mode's hidden anchors; update any browser journey that expects the vitals dock or minimap during dialogue.
